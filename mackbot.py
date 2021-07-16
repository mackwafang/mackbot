DEBUG_IS_MAINTANCE = False

# loading cheats
import wargaming, os, re, sys, pickle, discord, time, logging, json, difflib, traceback
import pandas as pd
import numpy as np
import cv2 as cv

# from PIL import ImageFont, ImageDraw, Image
from itertools import count
from numpy.random import randint
from pprint import pprint
from discord.ext import commands

with open("./command_list.json") as f:
	command_list = json.load(f)

print("commands usable:")
for c in command_list:
	print(f"{c:<10}: {'Yes' if command_list[c] else 'No':<3}")

# dont remeber why this is here. DO NOT REMOVE
cwd = sys.path[0]
if cwd == '':
	cwd = '.'

# logging shenanigans
# logging.basicConfig(filename=f'{time.strftime("%Y_%b_%d", time.localtime())}_mackbot.log')
# adding this so that shows no traceback during discord client is on

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-5s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# dictionary to convert user input to output nations
nation_dictionary = {
	'usa': 'US',
	'us': 'US',
	'pan_asia': 'Pan-Asian',
	'ussr': 'Russian',
	'russian': 'Russian',
	'europe': 'European',
	'japan': 'Japanese',
	'uk': 'British',
	'british': 'British',
	'france': 'France',
	'french': 'France',
	'germany': 'German',
	'italy': 'Italian',
	'commonwealth': 'Commonwealth',
	'pan_america': 'Pan-American',
	'netherlands': "Dutch",
}
# convert weegee ship type to usn hull classifications
hull_classification_converter = {
	'Destroyer': 'DD',
	'AirCarrier': 'CV',
	'Battleship': 'BB',
	'Cruiser': 'C',
	'Submarine': 'SS'
}
# dictionary to convert user inputted ship name to non-ascii ship name
# TODO: find an automatic method, maybe
with open("ship_name_dict.json", 'r', encoding='utf-8') as f:
	ship_name_to_ascii = json.load(f)

# see the ship name conversion dictionary comment
cmdr_name_to_ascii = {
	'jean-jacques honore': 'jean-jacques honoré',
	'paul kastner': 'paul kästner',
	'quon rong': 'quán róng',
	'myoko': 'myōkō',
	'myoukou': 'myōkō',
	'reinhard von jutland': 'reinhard von jütland',
	'matsuji ijuin': 'matsuji ijūin',
	'kongo': 'kongō',
	'kongou': 'kongō',
	'tao ji': 'tāo ji',
	'gunther lutjens': 'günther lütjens',
	'franz von jutland': 'franz von jütland',
	'da rong': 'dà róng',
	'rattenkonig': 'rattenkönig',
	'leon terraux': 'léon terraux',
	'charles-henri honore': 'charles-henri honoré',
	'jerzy swirski': 'Jerzy Świrski',
	'swirski': 'Jerzy Świrski',
	'halsey': 'william f. Halsey jr.',
}
# here because of lazy
roman_numeral = {
	'i': 1,
	'ii': 2,
	'iii': 3,
	'iv': 4,
	'v': 5,
	'vi': 6,
	'vii': 7,
	'viii': 8,
	'ix': 9,
	'x': 10,
}

# actual stuff
logging.info("Fetching WoWS Encyclopedia")
# load important stuff
if "sheets_credential" in os.environ:
	wg_token = os.environ['wg_token']
	bot_token = os.environ['bot_token']
	sheet_id = os.environ['sheet_id']
else:
	with open(cwd + "/config.json") as f:
		data = json.load(f)
		wg_token = data['wg_token']
		bot_token = data['bot_token']
		sheet_id = data['sheet_id']

cmd_sep = ' '
command_prefix = 'mackbot '
mackbot = commands.Bot(command_prefix=commands.when_mentioned_or(command_prefix))		

# get weegee's wows encyclopedia
wows_encyclopedia = wargaming.WoWS(wg_token, region='na', language='en').encyclopedia
ship_types = wows_encyclopedia.info()['ship_types']


# creating GameParams json from GameParams.data
logging.info(f"Loading GameParams")
game_data = {}
for file_count in count(0):
	try:
		with open(f'GameParamsPruned_{file_count}.json') as f:
			data = json.load(f)
		
		game_data.update(data)
		del data
	except FileNotFoundError:
		break

# loading skills list
logging.info("Fetching Skill List")
skill_list = {}
try:
	with open("skill_list.json") as f:
		skill_list = json.load(f)
		skill_list = dict([(s['id'], s) for s in skill_list])
	# dictionary that stores skill abbreviation
	skill_name_abbr = {}
	for skill in skill_list:
		# generate abbreviation
		abbr_name = ''.join([i[0] for i in skill_list[skill]['name'].lower().split()])
		skill_list[skill]['abbr'] = abbr_name
		# skill_name_abbr[abbr_name] = skill_list[skill]['name'].lower()
		# get local image location
		# url = skill_list[skill]['icon']
		# url = url[:url.rfind('_')]
		# url = url[url.rfind('/') + 1:]
		# skill_list[skill]['local_icon'] = f'./skill_images/{url}.png'
except:
	pass

logging.info("Fetching Module List")
module_list = {}
for page in count(1):
	try:
		m = wows_encyclopedia.modules(language='en', page_no=page)
		for i in m:
			module_list[i] = m[i]
	except Exception as e:
		if type(e) == wargaming.exceptions.RequestError:
			if e.args[0] == "PAGE_NO_NOT_FOUND":
				break
			else:
				logging.info(type(e), e)
		else:
			logging.info(type(e), e)
		break

# find game data items by tags
find_game_data_item = lambda x: [i for i in game_data if x in i]
def find_module_by_tag(x):
	l = []
	for i in module_list:
		if 'tag' in module_list[i]:
			if x == module_list[i]['tag']:
				l += [i]
	if len(l) > 0:
		return l[0]
	else:
		return []


logging.info("Fetching Commander List")
cmdr_list = wows_encyclopedia.crews()

consumable_descriptor = {
	'airDefenseDisp': {
		'name': 'Defensive Anti-Air Fire',
		'description': 'Increase continuous AA damage and damage from flak bursts.',
	},
	'artilleryBoosters': {
		'name': 'Main Battery Reload Booster',
		'description': 'Greatly decreases the reload time of main battery guns',
	},
	'callFighters': {
		'name': '',
		'description': ''
	},
	'crashCrew': {
		'name': 'Damage Control Party',
		'description': 'Immediately extinguish fires, stops flooding, and repair incapacitated modules. Also provides the ship with immunity to fires, floodings, and modules incapacitation for the active duration.',
	},
	'depthCharges': {},
	'fighter': {
		'name': 'Fighters',
		'description': 'Deploy fighters to protect your ship from enemy aircrafts.'
	},
	'healForsage': {
		'name': '',
		'description': ''
	},
	'invulnerable': {
		'name': '',
		'description': ''
	},
	'regenCrew': {
		'name': 'Repair Party',
		'description': 'Restore ship\'s HP.'
	},
	'regenerateHealth': {
		'name': '',
		'description': ''
	},
	'rls': {
		'name': 'Surveillance Radar',
		'description': 'Automatically detects any ships within the radar\'s range. Have longer range but lower duration than Hydroacoustic Search.',
	},
	'scout': {
		'name': 'Spotting Aircraft',
		'description': 'Deploy spotter plane to increase firing range.',
	},
	'smokeGenerator': {
		'name': 'Smoke Generator',
		'description': 'Deploys a smoke screen to obsure enemy\'s vision.',
	},
	'sonar': {
		'name': 'Hydroacoustic Search',
		'description': 'Automatically detects any ships and torpedoes within certain range with shorter range but higher duration than Surveillance Radar',
	},
	'speedBoosters': {
		'name': 'Engine Boost',
		'description': 'Temporary increase ship\'s maximum speed and engine power.',
	},
	'subsFourthState': {},
	'torpedoReloader': {
		'name': 'Torpedo Reload Booster',
		'description': 'Significantly reduces the reload time of torpedoes.',
	},
}

logging.info("Fetching Ship List")
ship_list = {}
ship_list_file_name = 'ship_list'
ship_list_file_dir = os.path.join(".", ship_list_file_name)

fetch_ship_list_from_wg = False
# fetching from local
if os.path.isfile(ship_list_file_dir):
	with open(ship_list_file_dir, 'rb') as f:
		ship_list = pickle.load(f)
		
	# check to see if it is out of date
	if ship_list['ships_updated_at'] != wows_encyclopedia.info()['ships_updated_at']:
		logging.info("Ship list outdated, fetching new list")
		fetch_ship_list_from_wg = True
		ship_list = {}
else:
	logging.info("No ship list file, fetching new")
	fetch_ship_list_from_wg = True

if fetch_ship_list_from_wg:
	for page in count(1):
		try:
			l = wows_encyclopedia.ships(language='en', page_no=page)
			for i in l:
				ship_list[i] = l[i]
				# add skip bomber field to list's modules listing
				ship_list[i]['modules']['skip_bomber'] = []
		except Exception as e:
			if type(e) == wargaming.exceptions.RequestError:
				if e.args[0] == "PAGE_NO_NOT_FOUND":
					break
				else:
					logging.info(type(e), e)
			else:
				logging.info(type(e), e)
			break
	with open(ship_list_file_dir, 'wb') as f:
		ship_list['ships_updated_at'] = wows_encyclopedia.info()['ships_updated_at']
		pickle.dump(ship_list, f)
del ship_list_file_dir, ship_list_file_name, ship_list['ships_updated_at']

logging.info("Fetching Camo, Flags and Modification List")
camo_list, flag_list, upgrade_list = {}, {}, {}
for page_num in count(1):
	# continuously count, because weegee don't list how many pages there are
	try:
		consumable_list = wows_encyclopedia.consumables(page_no=page_num)
		# consumables of some page page_num
		for consumable in consumable_list:
			c_type = consumable_list[consumable]['type']
			if c_type == 'Camouflage' or c_type == 'Permoflage' or c_type == 'Skin':
				# grab camouflages and stores
				camo_list[consumable] = consumable_list[consumable]
			if c_type == 'Modernization':
				# grab upgrades and store
				upgrade_list[consumable] = consumable_list[consumable]

				url = upgrade_list[consumable]['image']
				url = url[:url.rfind('_')]
				url = url[url.rfind('/') + 1:]

				# initializing stuff for excluding obsolete upgrades
				upgrade_list[consumable]['local_image'] = f'./modernization_icons/{url}.png'
				upgrade_list[consumable]['is_special'] = ''
				upgrade_list[consumable]['ship_restriction'] = []
				upgrade_list[consumable]['nation_restriction'] = []
				upgrade_list[consumable]['tier_restriction'] = []
				upgrade_list[consumable]['type_restriction'] = []
				upgrade_list[consumable]['slot'] = ''
				upgrade_list[consumable]['additional_restriction'] = ''
				upgrade_list[consumable]['tags'] = []

			if c_type == 'Flags':
				# grab flags
				flag_list[consumable] = consumable_list[consumable]
	except Exception as e:
		if type(e) == wargaming.exceptions.RequestError:
			if e.args[0] == "PAGE_NO_NOT_FOUND":
				# counter went outside of max number of pages.
				# expected behavior, done
				break
			else:
				# something else came up that is not a "exceed max number of pages"
				logging.info(type(e), e)
		else:
			# we done goof now
			logging.info(type(e), e)
		break
		
logging.info('Adding upgrade information')
obsolete_upgrade = []
for i in game_data:
	value = game_data[i]
	if value['typeinfo']['type'] == 'Modernization':
		upgrade = value
		if upgrade['slot'] == -1:
			# upgrade obsolete
			obsolete_upgrade += [str(upgrade['id'])]
			pass
		else:
			# upgrade usable
			uid = str(upgrade['id'])

			upgrade_list[uid]['is_special'] = {
				0: '',
				1: 'Coal',
				3: 'Unique'
			}[upgrade['type']]
			upgrade_list[uid]['slot'] = upgrade['slot'] + 1
			upgrade_list[uid]['ship_restriction'] = [ship_list[str(game_data[s]['id'])]['name'] for s in
													 upgrade['ships'] if
													 s in game_data and str(game_data[s]['id']) in ship_list]
			upgrade_list[uid]['type_restriction'] = ['Aircraft Carrier' if t == 'AirCarrier' else t for t in
													 upgrade['shiptype']]
			upgrade_list[uid]['nation_restriction'] = [t for t in upgrade['nation']]
			upgrade_list[uid]['tier_restriction'] = [t for t in upgrade['shiplevel']]

			upgrade_list[uid]['tags'] += upgrade_list[uid]['type_restriction']
			upgrade_list[uid]['tags'] += upgrade_list[uid]['tier_restriction']
logging.info('Removing obsolete upgrades')
for i in obsolete_upgrade:
	del upgrade_list[i]

logging.info('Fetching build file...')
BUILD_EXTRACT_FROM_CACHE = False
extract_from_web_failed = False
BUILD_BATTLE_TYPE_CLAN = 0
BUILD_BATTLE_TYPE_CASUAL = 1
BUILD_CREATE_BUILD_IMAGES = True
# dunno why this exists, keep it
build_battle_type = {
	BUILD_BATTLE_TYPE_CLAN: "competitive",
	BUILD_BATTLE_TYPE_CASUAL: "casual",
}
build_battle_type_value = {
	"competitive": BUILD_BATTLE_TYPE_CLAN,
	"casual": BUILD_BATTLE_TYPE_CASUAL,
}
ship_build = {build_battle_type[BUILD_BATTLE_TYPE_CLAN]: {}, build_battle_type[BUILD_BATTLE_TYPE_CASUAL]: {}}
# fetch ship builds and additional upgrade information
if command_list['build']:
	if not BUILD_EXTRACT_FROM_CACHE:
		# extracting build and upgrade exclusion data from google sheets
		from googleapiclient.errors import Error
		from googleapiclient.discovery import build
		from google_auth_oauthlib.flow import InstalledAppFlow
		from google.auth.transport.requests import Request

		# silence file_cache_warning
		logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)

		logging.info("Attempting to fetch from sheets")
		SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

		# The ID and range of a sample spreadsheet.
		SAMPLE_SPREADSHEET_ID = sheet_id

		creds = None
		# The file cmd_sep.pickle stores the user's access and refresh cmd_seps, and is
		# created automatically when the authorization flow completes for the first
		# time.
		if os.path.exists('cmd_sep.pickle'):
			with open('cmd_sep.pickle', 'rb') as cmd_sep:
				creds = pickle.load(cmd_sep)
		# If there are no (valid) credentials available, let the user log in.
		try:
			if not creds or not creds.valid:
				if creds and creds.expired and creds.refresh_cmd_sep:
					creds.refresh(Request())
				else:
					flow = InstalledAppFlow.from_client_secrets_file(
						'credentials.json', SCOPES)
					creds = flow.run_local_server(port=0)
				# Save the credentials for the next run
				with open('cmd_sep.pickle', 'wb') as cmd_sep:
					pickle.dump(creds, cmd_sep)

			service = build('sheets', 'v4', credentials=creds)

			# Call the Sheets API
			sheet = service.spreadsheets()
			# fetch build
			result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
										range='ship_builds!B2:W1000').execute()
			values = result.get('values', [])

			if not values:
				print('No data found.')
				raise Error
			else:
				for row in values:
					build_type = row[1]
					ship_name = row[0]
					if ship_name.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside prinable ?
						ship_name = ship_name_to_ascii[ship_name.lower()]  # convert to the appropiate name
					upgrades = [i for i in row[2:8] if len(i) > 0]
					skills = [i for i in row[8:-2] if len(i) > 0]
					cmdr = row[-1]
					ship_build[build_type][ship_name] = {"upgrades": upgrades, "skills": skills, "cmdr": cmdr}
			logging.info("Build data fetching done")
		except Exception as e:
			extract_from_web_failed = True
			logging.info(f"Exception raised while fetching builds: {e}")

	if BUILD_EXTRACT_FROM_CACHE or extract_from_web_failed:
		if extract_from_web_failed:
			logging.info("Get builds from sheets failed")
		with open("ship_builds.json") as f:
			builds = json.load(f)
		logging.info('Making build dictionary from cache')
		for i in builds:
			build = builds[i]

			ship_name = build['ship']
			if ship_name in ship_name_to_ascii:
				ship_name = ship_name_to_ascii[ship_name]

			build_type = build['type']

			upgrades = [u for u in build['upgrades'] if len(u) > 0]
			skills = [s for s in build['skills'] if len(s) > 0]
			cmdr = build['cmdr']
			ship_build[build_type][ship_name] = {"upgrades": upgrades, "skills": skills, "cmdr": cmdr}
		logging.info("build dictionary complete")

logging.info("Fetching Ship Parameters")
ship_param_file_name = 'ship_param'
logging.info("Checking cached ship_param file...")
fetch_ship_params_from_wg = False
if os.path.isfile('./' + ship_param_file_name):
	# check ship_params exists
	logging.info("File found. Loading file")
	with open('./' + ship_param_file_name, 'rb') as f:
		ship_info = pickle.load(f)
		
	if ship_info['ships_updated_at'] != wows_encyclopedia.info()['ships_updated_at']:
		logging.info("Ship params outdated, fetching new list")
		fetch_ship_params_from_wg = True
		ship_info = {}
else:
	fetch_ship_params_from_wg = True

if fetch_ship_params_from_wg:
	logging.info("Fetching new ship params from weegee")
	i = 0
	ship_info = {}
	ship_info['ships_updated_at'] = wows_encyclopedia.info()['ships_updated_at']
	for s in ship_list:
		ship = wows_encyclopedia.shipprofile(ship_id=int(s), language='en')
		ship_info[s] = ship[s]
		ship_info[s]['skip_bomber'] = None
		i += 1
		print(f"Fetching ship parameters. {i}/{len(ship_list)} ships found", end='\r')
	print()
	logging.info("Fetch complete")
	logging.info("Creating cache")
	with open('./' + ship_param_file_name, 'wb') as f:
		pickle.dump(ship_info, f)
	logging.info("Cache creation complete")

logging.info("Filling missing informations of modules")
for s in ship_list:
	ship = ship_list[s]
	
	try:
		module_full_id_str = find_game_data_item(ship['ship_id_str'])[0]
		module_data = game_data[module_full_id_str]

		# grab consumables
		ship_list[s]['consumables'] = module_data['ShipAbilities'].copy()

		ship_upgrade_info = module_data['ShipUpgradeInfo']  # get upgradable modules
		
		# get credit and xp cost for ship research
		ship_list[s]['price_credit'] = ship_upgrade_info['costCR']
		ship_list[s]['price_xp'] = ship_upgrade_info['costXP']
		
		for _info in ship_upgrade_info:  # for each upgradable modules
			if type(ship_upgrade_info[_info]) == dict:  # if there are data
				
				try:
					if ship_upgrade_info[_info]['ucType'] != "_SkipBomber":
						module_id = find_module_by_tag(_info)
					else:
						module = module_data[ship_upgrade_info[_info]['components']['skipBomber'][0]]['planeType']
						module_id = str(game_data[module]['id'])
						del module
				except IndexError as e:
					continue

				if ship_upgrade_info[_info]['ucType'] == '_Hull':
					# initialize AA dictionary
					if len(ship_upgrade_info[_info]['components']['airDefense']) > 0:
						module_list[module_id]['profile']['anti_air'] = {
							'hull': ship_upgrade_info[_info]['components']['airDefense'][0][0],
							'near': {'damage': 0, 'hitChance': 0},
							'medium': {'damage': 0, 'hitChance': 0},
							'far': {'damage': 0, 'hitChance': 0},
							'flak': {'damage': 0, },
						}

						min_aa_range = np.Inf
						max_aa_range = -np.Inf

						# grab anti-air guns information
						aa_defense = ship_upgrade_info[_info]['components']['airDefense'][0]
						aa_defense = module_data[aa_defense]

						# finding details of passive AA
						for a in [a for a in aa_defense if 'med' in a.lower() or 'near' in a.lower()]:
							aa_data = aa_defense[a]
							if aa_data['type'] == 'near':
								module_list[module_id]['profile']['anti_air']['near']['damage'] += aa_data['areaDamage'] / aa_data['areaDamagePeriod']
								module_list[module_id]['profile']['anti_air']['near']['range'] = aa_data['maxDistance']
								module_list[module_id]['profile']['anti_air']['near']['hitChance'] = aa_data['hitChance']
							if aa_data['type'] == 'medium':
								module_list[module_id]['profile']['anti_air']['medium']['damage'] += aa_data['areaDamage'] / aa_data['areaDamagePeriod']
								module_list[module_id]['profile']['anti_air']['medium']['range'] = aa_data['maxDistance']
								module_list[module_id]['profile']['anti_air']['medium']['hitChance'] = aa_data['hitChance']
							min_aa_range = min(min_aa_range, aa_data['minDistance'])
							max_aa_range = max(max_aa_range, aa_data['maxDistance'])
						# getting flak guns info
						try:
							if len(ship_upgrade_info[_info]['components']['atba']) > 0:
								# none found from primary guns get far AA armament from secondary
								aa_defense_far = module_data[ship_upgrade_info[_info]['components']['atba'][0]]
							else:
								# AA armament from primary guns
								aa_defense_far = module_data[ship_upgrade_info[_info]['components']['artillery'][0]]
						except:
							aa_defense_far = []
						for a in [a for a in aa_defense_far if 'Far' in a]:
							aa_data = aa_defense_far[a]
							if 'Bubbles' not in a:
								# long range passive AA
								module_list[module_id]['profile']['anti_air']['far']['damage'] += aa_data['areaDamage'] / aa_data['areaDamagePeriod']
								module_list[module_id]['profile']['anti_air']['far']['hitChance'] = aa_data['hitChance']
							else:
								# flaks
								module_list[module_id]['profile']['anti_air']['flak']['count'] = aa_data['innerBubbleCount'] + aa_data['outerBubbleCount']
								module_list[module_id]['profile']['anti_air']['flak']['damage'] += aa_data['bubbleDamage']
								module_list[module_id]['profile']['anti_air']['flak']['min_range'] = aa_data['minDistance']
								module_list[module_id]['profile']['anti_air']['flak']['max_range'] = aa_data['maxDistance']

							min_aa_range = min(min_aa_range, aa_data['minDistance'])
							max_aa_range = max(max_aa_range, aa_data['maxDistance'])

						module_list[module_id]['profile']['anti_air']['min_range'] = min_aa_range
						module_list[module_id]['profile']['anti_air']['max_range'] = max_aa_range

						# calculate aa rating
						near_damage = module_list[module_id]['profile']['anti_air']['near']['damage'] * module_list[module_id]['profile']['anti_air']['near']['hitChance'] * 0.8
						mid_damage = module_list[module_id]['profile']['anti_air']['medium']['damage'] * module_list[module_id]['profile']['anti_air']['medium']['hitChance']
						far_damage = module_list[module_id]['profile']['anti_air']['far']['damage'] * module_list[module_id]['profile']['anti_air']['far']['hitChance'] * 2.25
						combined_aa_damage = near_damage + mid_damage + far_damage
						aa_rating = 0
						
						# if combined_aa_damage > 0:
							# aa_range_scaling = module_list[module_id]['profile']['anti_air']['max_range'] / 5800
							# if aa_range_scaling > 1:
								# aa_range_scaling = aa_range_scaling ** 2
							# aa_rating = (combined_aa_damage / (int(ship['tier']) * 9)) * aa_range_scaling
						aa_rating = (combined_aa_damage / (int(ship['tier']) * 9))
						module_list[module_id]['profile']['anti_air']['rating'] = int(aa_rating * 10)
						
						if ship_info[s]['anti_aircraft'] is None:
							ship_info[s]['anti_aircraft'] = {}
						ship_info[s]['anti_aircraft'][module_list[module_id]['profile']['anti_air']['hull']] = module_list[module_id]['profile']['anti_air'].copy()
					
					if 'airSupport' in ship_upgrade_info[_info]['components']:
						if len(ship_upgrade_info[_info]['components']['airSupport']) > 0:
							airsup_info = module_data[ship_upgrade_info[_info]['components']['airSupport'][0]]
							plane = game_data[airsup_info['planeName']]
							projectile = game_data[plane['bombName']]
							module_list[module_id]['profile']['airSupport'] = {
								'chargesNum': airsup_info['chargesNum'],
								'reloadTime': airsup_info['reloadTime'],
								'maxDist': airsup_info['maxDist'],
								'max_damage': int(projectile['alphaDamage']),
								'burn_probability': int(projectile['burnProb'] * 100),
								'bomb_pen': int(projectile['alphaPiercingHE']),
								'squad_size': plane['numPlanesInSquadron'],
								'payload': plane['attackCount'],
							}
					continue
					

				if ship_upgrade_info[_info]['ucType'] == '_Artillery':  # guns, guns, guns!
					# get turret parameter
					gun = ship_upgrade_info[_info]['components']['artillery'][0]
					gun = module_data[gun]
					gun = np.unique([gun[turret]['name'] for turret in [g for g in gun if 'HP' in g]])
					for g in gun:  # for each turret
						turret_data = game_data[g]
						
						module_list[module_id]['profile']['artillery'] = {
							'gun_rate': 0,
							'caliber': 0,
							'numBarrels': 0,
							'max_damage_sap': 0,
							'burn_probability': 0,
							'pen_HE': 0,
							'pen_SAP': 0,
							'max_damage_HE': 0,
							'max_damage_AP': 0,
							'max_damage_SAP': 0,
						}
						
						module_list[module_id]['profile']['artillery']['caliber'] = turret_data['barrelDiameter']
						for a in turret_data['ammoList']:
							ammo = game_data[a]
							# print(ammo['alphaDamage'], ammo['ammoType'], f"{ammo['burnProb']} fire %")
							
							module_list[module_id]['profile']['artillery']['gun_rate'] = turret_data['shotDelay']
							module_list[module_id]['profile']['artillery']['numBarrels'] = int(turret_data['numBarrels'])
							if ammo['ammoType'] == 'HE':
								module_list[module_id]['profile']['artillery']['burn_probability'] = int(ammo['burnProb'] * 100)
								module_list[module_id]['profile']['artillery']['pen_HE'] = int(ammo['alphaPiercingHE'])
								module_list[module_id]['profile']['artillery']['max_damage_HE'] = int(ammo['alphaDamage'])
							if ammo['ammoType'] == 'CS':
								module_list[module_id]['profile']['artillery']['pen_SAP'] = int(ammo['alphaPiercingCS'])
								module_list[module_id]['profile']['artillery']['max_damage_SAP'] = int(ammo['alphaDamage'])
							if ammo['ammoType'] == 'AP':
								module_list[module_id]['profile']['artillery']['max_damage_AP'] = int(ammo['alphaDamage'])

						# check for belfast and belfast '43
						if 'Belfast' in ship['name']:
							module_list[module_id]['profile']['artillery']['burn_probability'] = int(
								ship_info[str(s)]['artillery']['shells']['HE']['burn_probability'])
							module_list[module_id]['profile']['artillery']['pen_HE'] = 0
					continue

				if ship_upgrade_info[_info]['ucType'] == '_Torpedoes':  # torpedooes
					# get torps parameter
					gun = ship_upgrade_info[_info]['components']['torpedoes'][0]
					gun = module_data[gun]
					# gun = np.unique([gun[turret]['name'] for turret in [g for g in gun if 'HP' in g]])
					for g in [turret for turret in [g for g in gun if 'HP' in g]]:  # for each turret
						turret_data = gun[g]
						projectile = game_data[turret_data['ammoList'][0]]
						module_list[module_id]['profile']['torpedoes'] = {
							'numBarrels': turret_data['numBarrels'],
							'shotDelay': turret_data['shotDelay'], 
							'max_damage': int(projectile['alphaDamage'] / 3) + projectile['damage'],
							'torpedo_speed': projectile['speed'],
							'is_deep_water': projectile['isDeepWater'],
							'distance': projectile['maxDist'] * 30 / 1000,
						}
					continue

				if ship_upgrade_info[_info]['ucType'] == '_Fighter':  # useless spotter
					# get fighter parameter
					planes = ship_upgrade_info[_info]['components']['fighter'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']]  # get rocket params
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['speed_max'] = plane['speedMax']  # squadron max speed, in multiplier
						module_list[module_id]['payload'] = plane['attackCount']
						module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
						module_list[module_id]['attack_cooldown'] = plane['attackCooldown']
						module_list[module_id]['profile'] = {
							"fighter": {
								'max_damage': int(projectile['alphaDamage']),
								'rocket_type':  projectile['ammoType'],
								'burn_probability': int(projectile['burnProb'] * 100),
								'rocket_pen': int(projectile['alphaPiercingHE']),
								'max_health': plane['maxHealth'],
								'cruise_speed' : plane['speedMoveWithBomb'],
							}
						}
					continue

				if ship_upgrade_info[_info]['ucType'] == '_TorpedoBomber':
					# get torp bomber parameter
					planes = ship_upgrade_info[_info]['components']['torpedoBomber'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']]
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['speed_max'] = plane['speedMax']  # squadron max speed, in multiplier
						module_list[module_id]['payload'] = plane['projectilesPerAttack']
						module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
						module_list[module_id]['attack_cooldown'] = plane['attackCooldown']
						
						module_list[module_id]['profile'] = {
							"torpedo_bomber": {
								'cruise_speed' : plane['speedMoveWithBomb'],
								'max_damage': int(projectile['alphaDamage'] / 3) + projectile['damage'],
								'max_health': plane['maxHealth'],
								'torpedo_speed': projectile['speed'],
								'is_deep_water': projectile['isDeepWater'],
								'distance': projectile['maxDist'] * 30 / 1000,
							}
						}
					continue

				if ship_upgrade_info[_info]['ucType'] == '_DiveBomber':
					# get turret parameter
					planes = ship_upgrade_info[_info]['components']['diveBomber'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']]
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['speed_max'] = plane['speedMax']  # squadron max speed, in multiplier
						module_list[module_id]['payload'] = plane['attackCount']
						module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
						module_list[module_id]['attack_cooldown'] = plane['attackCooldown']
						module_list[module_id]['bomb_type'] = projectile['ammoType']
						module_list[module_id]['bomb_pen'] = int(projectile['alphaPiercingHE'])
						module_list[module_id]['profile'] = {
							"dive_bomber": {
								'cruise_speed' : plane['speedMoveWithBomb'],
								'max_damage': projectile['alphaDamage'],
								'burn_probability': projectile['burnProb'] * 100,
								'max_health': plane['maxHealth'],
							}
						}
					continue
					
				# skip bomber
				if ship_upgrade_info[_info]['ucType'] == '_SkipBomber':
					# get turret parameter
					planes = ship_upgrade_info[_info]['components']['skipBomber'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']]
						ship_list[s]['modules']['skip_bomber'] += [plane['id']]
						if plane['id'] not in module_list:
							module_list[module_id] = {}
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['speed_max'] = plane['speedMax']  # squadron max speed, in multiplier
						module_list[module_id]['payload'] = plane['attackCount']
						module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
						module_list[module_id]['attack_cooldown'] = plane['attackCooldown']
						module_list[module_id]['bomb_type'] = projectile['ammoType']
						module_list[module_id]['bomb_pen'] = int(projectile['alphaPiercingHE'])
						
						
						# fill missing skip bomber info 
						module_list[module_id]['name'] = plane['name']
						module_list[module_id]['module_id'] = module_id
						module_list[module_id]['module_id_str'] = plane['index']
						module_list[module_id]['profile'] = {
							"skip_bomber": {
								'cruise_speed' : plane['speedMoveWithBomb'],
								'max_damage': projectile['alphaDamage'],
								'burn_probability': projectile['burnProb'] * 100,
								'max_health': plane['maxHealth'],
							}
						}
						ship_info[s]['skip_bomber'] = {'skip_bomber_id': module_id}
					continue
	except Exception as e:
		if not type(e) == KeyError:
			logging.error("at ship id " + s)
			logging.info("Ship", s, "is not known to GameParams.data")
			# traceback.print_exc(type(e), e, None)
			print(__name__)
			if __name__ == '__main__':
				@mackbot.event
				async def on_ready():
					user = await mackbot.fetch_user("164545158572933121")
					await user.send("shit fucked up, fam")
					await user.send("GameParams.json is outdated")
					await user.send("Exception {} {}".format(type(e), e))
					
					await mackbot.close()
					
				mackbot.run(bot_token)
		else:
			traceback.print_exc(type(e), e, None)
			
		if mackbot.is_closed():
			time.sleep(10)
			exit(1)

logging.info("Creating Modification Abbreviation")
upgrade_abbr_list = {}
for u in upgrade_list:
	# print("'"+''.join([i[0] for i in mod_list[i].split()])+"':'"+f'{mod_list[i]}\',')
	upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(160), chr(32))  # replace weird 0-width character with a space
	key = ''.join([i[0] for i in upgrade_list[u]['name'].split()]).lower()
	if key in upgrade_abbr_list:  # if the abbreviation of this upgrade is in the list already
		key = ''.join([i[:2].title() for i in upgrade_list[u]['name'].split()]).lower()[:-1]  # create a new abbreviation
	upgrade_abbr_list[key] = upgrade_list[u]['name'].lower()  # add this abbreviation
legendary_upgrades = {u: upgrade_list[u] for u in upgrade_list if upgrade_list[u]['is_special'] == 'Unique'}

logging.info("Generating ship search tags")
SHIP_TAG_SLOW_SPD = 0
SHIP_TAG_FAST_SPD = 1
SHIP_TAG_FAST_GUN = 2
SHIP_TAG_STEALTH = 3
SHIP_TAG_AA = 4

SHIP_TAG_LIST = (
	'slow',
	'fast',
	'fast-firing',
	'stealth',
	'anti-air',
)
ship_tags = {
	SHIP_TAG_LIST[SHIP_TAG_SLOW_SPD]: {
		'min_threshold': 0,
		'max_threshold': 30,
		'description': f"Any ships in this category have a **base speed** of **30 knots or slower**",
	},
	SHIP_TAG_LIST[SHIP_TAG_FAST_SPD]: {
		'min_threshold': 30,
		'max_threshold': 99,
		'description': "Any ships in this category have a **base speed** of **30 knots or faster**",
	},
	SHIP_TAG_LIST[SHIP_TAG_FAST_GUN]: {
		'min_threshold': 0,
		'max_threshold': 6,
		'description': "Any ships in this category have main battery guns that **reload** in **6 seconds or less**",
	},
	SHIP_TAG_LIST[SHIP_TAG_STEALTH]: {
		'min_air_spot_range': 4,
		'min_sea_spot_range': 6,
		'description': "Any ships in this category have a **base air detection range** of **4 km or less** or a **base sea detection range** of **6 km or less**",
	},
	SHIP_TAG_LIST[SHIP_TAG_AA]: {
		'min_aa_range': 5.8,
		'damage_threshold_multiplier': 75,
		'description': "Any ships in this category have an **anti-air gun range** larger than **5.8 km** or the ship's **AA rating (according to mackbot) is at least 50**",
	},
}
ship_list_regex = re.compile('((tier )(\d{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|((page )(\d{1,2}))|(([aA]ircraft [cC]arrier[sS]?)|((\w|-)*))')
skill_list_regex = re.compile('((?:battleship|[bB]{2})|(?:carrier|[cC][vV])|(?:cruiser|[cC][aAlL]?)|(?:destroyer|[dD]{2})|(?:submarine|[sS]{2}))|(?:page (\d{1,2}))|(?:tier (\d{1,2}))')
equip_regex = re.compile('(slot (\d))|(tier ([0-9]{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|(page (\d{1,2}))|((defensive aa fire)|(main battery)|(aircraft carrier[sS]?)|(\w|-)*)')
ship_param_filter_regex = re.compile('((hull|health|hp)|(guns?|artiller(?:y|ies))|(secondar(?:y|ies))|((?:torp(?:s|edo)?) bombers?)|(torp(?:s|edo(?:es)?)?)|((?:dive )?bombers?)|((?:rockets?)|(?:attackers?))|(speed)|((?:aa)|(?:anti-air))|((?:concealment)|(?:dectection))|(consumables?))*')
for s in ship_list:
	try:
		nat = nation_dictionary[ship_list[s]['nation']]
		tags = []
		t = ship_list[s]['type']
		hull_class = hull_classification_converter[t]
		if t == 'AirCarrier':
			t = 'Aircraft Carrier'
		tier = ship_list[s]['tier']  # add tier to search
		prem = ship_list[s]['is_premium']  # is bote premium
		ship_speed = ship_info[s]['mobility']['max_speed']
		# add tags based on speed
		if ship_speed <= ship_tags[SHIP_TAG_LIST[SHIP_TAG_SLOW_SPD]]['max_threshold']:
			tags += [SHIP_TAG_LIST[SHIP_TAG_SLOW_SPD]]
		if ship_speed >= ship_tags[SHIP_TAG_LIST[SHIP_TAG_FAST_SPD]]['min_threshold']:
			tags += [SHIP_TAG_LIST[SHIP_TAG_FAST_SPD]]
		concealment = ship_info[s]['concealment']
		# add tags based on detection range
		if concealment['detect_distance_by_plane'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG_STEALTH]]['min_air_spot_range'] or concealment['detect_distance_by_ship'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG_STEALTH]]['min_sea_spot_range']:
			tags += [SHIP_TAG_LIST[SHIP_TAG_STEALTH]]
		# add tags based on gun firerate
		try:
			# some ships have main battery guns
			fireRate = ship_info[s]['artillery']['shot_delay']
		except:
			# some dont
			fireRate = np.inf
		if fireRate <= ship_tags[SHIP_TAG_LIST[SHIP_TAG_FAST_GUN]]['max_threshold'] and not t == 'Aircraft Carrier':
			tags += [SHIP_TAG_LIST[SHIP_TAG_FAST_GUN], 'dakka']
		# add tags based on aa
		if ship_info[s]['anti_aircraft'] is not None:
			for hull in ship_info[s]['anti_aircraft']:
				if hull not in ['defense', 'slots']:
					aa_rating = ship_info[s]['anti_aircraft'][hull]['rating']
					aa_max_range = ship_info[s]['anti_aircraft'][hull]['max_range']
					if aa_rating > 50 or aa_max_range > ship_tags[SHIP_TAG_LIST[SHIP_TAG_AA]]['min_aa_range']:
						if SHIP_TAG_LIST[SHIP_TAG_AA] not in tags:
							tags += [SHIP_TAG_LIST[SHIP_TAG_AA]]

		tags += [nat, f't{tier}', t, t + 's', hull_class]
		ship_list[s]['tags'] = tags
		if prem:
			ship_list[s]['tags'] += ['premium']
	except Exception as e:
		if type(e) == KeyError:
			logging.warning(f"Ship Tags Generator: Ship {s} not found")
		else:
			logging.warning("%s %s at ship id %s" % (type(e), e, s))
			traceback.print_exception(type(e), e, None)

AA_RATING_DESCRIPTOR = {
	"Non-Existence": [0, 1],
	"Very Weak": [1, 20],
	"Weak": [20, 40],
	"Moderate": [40, 50],
	"High": [50, 70],
	"Dangerous": [70, 90],
	"Very Dangerous": [90, np.inf],
}

logging.info("Filtering Ships and Categories")
del ship_list['3749623248']
# filter data tyoe
ship_list_frame = pd.DataFrame(ship_list)
ship_list_frame = ship_list_frame.filter(items=['name', 'nation', 'images', 'type', 'tier', 'consumables', 'modules', 'upgrades', 'is_premium', 'price_gold', 'price_credit', 'price_xp', 'tags'], axis=0)
ship_list = ship_list_frame.to_dict()

logging.info("Fetching Maps")
map_list = wows_encyclopedia.battlearenas()
# del game_data # free up memory
logging.info("Preprocessing Done")

good_bot_messages = (
	'Thank you!',
	'Mackbot tattara kekkō ganbatta poii? Homete hometei!',
	':3',
	':heart:',
)

def check_build():
	"""
		checks ship_build for in incorrectly inputted values and outputs to stdout, and write build images
	"""
	if not command_list['build']:
		logging.info("Build check passed due to build command is disabled.")
		return
	skill_use_image = cv.imread("./skill_images/icon_perk_use.png", cv.IMREAD_UNCHANGED)
	skill_use_image_channel = [i for i in cv.split(skill_use_image)]
	for t in build_battle_type:
		for s in ship_build[build_battle_type[t]]:
			image = np.zeros((520, 660, 4))
			logging.info(f"Checking {build_battle_type[t]} build for {s}...")

			name, nation, _, ship_type, tier, _, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_ship_data(
				s, battle_type=build_battle_type[t])
			font = ImageFont.truetype('arialbd.ttf', 20)
			image_pil = Image.fromarray(image, mode='RGBA')
			draw = ImageDraw.Draw(image_pil)
			draw.text((0, 0), f"{build_battle_type[t].title()} {name.title()}", font=font, fill=(255, 255, 255, 255))
			category_title = ['Endurance', 'Attack', 'Support', 'Versatility']
			for s in range(len(category_title)):
				draw.text((s * 180, 30), category_title[s], font=font, fill=(255, 255, 255, 255))
			draw.text((0, 330), "Upgrades", font=font, fill=(255, 255, 255, 255))
			# suggested commander
			if cmdr != "":
				# print("\tChecking commander...", end='')
				if cmdr == "*":
					pass
				else:
					try:
						get_commander_data(cmdr)
					except Exception as e:
						logging.info(f"Cmdr check: Exception {type(e)}", e, "in check_build, listing commander")
			else:
				logging.info("Cmdr check: No Commander found")
			draw.text((0, 440), "Commander", font=font, fill=(255, 255, 255, 255))
			draw.text((0, 460), "Any" if cmdr == "*" else cmdr, font=font, fill=(255, 255, 255, 255))

			image = np.array(image_pil)
			for skill in skill_list:
				x = skill_list[skill]['type_id']
				y = skill_list[skill]['tier']
				img = cv.imread(skill_list[skill]['local_icon'], cv.IMREAD_UNCHANGED)
				h, w, _ = img.shape
				image[y * h: (y + 1) * h, (x + (x // 2)) * w: (x + (x // 2) + 1) * h] = img
			# suggested upgrades
			if len(upgrades) > 0:
				upgrade_index = 0
				for upgrade in upgrades:
					if upgrade == '*':
						# any thing
						img = cv.imread('./modernization_icons/icon_modernization_any.png', cv.IMREAD_UNCHANGED)
					else:
						try:
							local_image = get_upgrade_data(upgrade)[6]
							img = cv.imread(local_image, cv.IMREAD_UNCHANGED)
							if img is None:
								img = cv.imread('./modernization_icons/icon_modernization_missing.png',
												cv.IMREAD_UNCHANGED)
						except Exception as e:
							logging.info(f"Upgrade check: Exception {type(e)}", e, f"in check_build, listing upgrade {upgrade}")
					img = np.array(img)
					y = 6
					x = upgrade_index
					h, w, _ = img.shape
					img = [i for i in cv.split(img)]
					for i in range(3):
						image[y * h: (y + 1) * h, x * w: (x + 1) * w, i] = img[i]
					image[y * h: (y + 1) * h, x * w: (x + 1) * w, 3] += img[3]
					upgrade_index += 1
			else:
				logging.info("Upgrade check: No upgrades found")
			# suggested skills
			if len(skills) > 0:
				for skill in skills:
					try:
						_, id, _, _, tier, _ = get_skill_data(skill)
						x = id
						y = tier
						h, w, _ = skill_use_image.shape
						for i in range(3):
							image[y * h: (y + 1) * h, (x + (x // 2)) * w: (x + (x // 2) + 1) * h, i] = \
								skill_use_image_channel[i]
						image[y * h: (y + 1) * h, (x + (x // 2)) * w: (x + (x // 2) + 1) * h, 3] += \
							skill_use_image_channel[3]

					except Exception as e:
						logging.info(f"Skill check: Exception {type(e)}", e, f"in check_build, listing skill {skill}")
			else:
				logging.info("Skill check: No skills found in build")
			cv.imwrite(f"{name.lower()}_{build_battle_type[t]}_build.png", image)

def get_ship_data(ship, battle_type='casual'):
	"""
		returns name, nation, images, ship type, tier of requested warship name along with recommended build.

		Arguments:
		-------
			- ship : (string)
				Ship name of build to be returned

			- battle_type : (string), optional
				type of enviornemnt should this build be used in
				acceptable values:
					casual
					competitive

		Returns:
		-------
		tuple:
			name			- (str) name of warship
			nation			- (str) nation of warship
			images			- (dict) images of warship on WG's server
			ship_type		- (str) warship type
			tier			- (int) warship tier
			modules			- (list) list of researchable modules
			equip_upgrades	- (list) list of equipable upgrades
			is_prem			- (bool) is warships premium?
			price_gold		- (int) price in doubloons
			upgrades		- (list) list of suggested upgrades
			skills			- (list) list of suggested commander skill
			cmdr			- (str) suggested cmdr. this value may be '*', which indicates "any commander"
			battle_type		- (str) build enviornment (casual or competitive)
		or
			None, if no build exists
		raise InvalidShipName exception if name provided is incorrect
		or
		NoBuildFound exception if no build is found
	"""

	original_arg = ship
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()]  # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			# print(ship.lower(),ship_name_in_dict.lower())
			if ship.lower() == ship_name_in_dict.lower():  # find ship based on name
				ship_found = True
				break
		if ship_found:
			name, nation, images, ship_type, tier, consumables, modules, equip_upgrades, is_prem, price_gold, price_credit, price_xp, _ = \
				ship_list[i].values()
			upgrades, skills, cmdr = {}, {}, ""
			if name.lower() in ship_build[battle_type]:
				upgrades, skills, cmdr = ship_build[battle_type][name.lower()].values()
			return name, nation, images, ship_type, tier, consumables, modules, equip_upgrades, is_prem, price_gold, price_credit, price_xp, upgrades, skills, cmdr, battle_type
	except Exception as e:
		raise e

def get_ship_param(ship):
	"""
		returns combat parameters of requested warship name

		Arguments:
		-------
			- ship : (string)
				Ship name of combat parameter to be returned

		Returns:
		-------
		dictionary containing ship data

		raise exceptions for dictionary
	"""
	original_arg = ship
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()]  # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			# print(ship.lower(),ship_name_in_dict.lower())
			if ship.lower() == ship_name_in_dict.lower():  # find ship based on name
				if i in ship_info:
					return ship_info[i]
				else:
					raise IndexError("Ship not found in ship_params")
	except Exception as e:
		raise e

def get_legendary_upgrade_by_ship_name(ship):
	"""
		returns informations of a requested legendary warship upgrade

		Arguments:
		-------
			- ship : (string)
				ship name

		Returns:
		-------
		tuple:
			profile					- (dict) upgrade's bonuses
			name					- (str) upgrade name
			price_gold				- (int) upgrade price in doubloons
			image					- (str) image url
			price_credit			- (int) price in credits
			description				- (str) summary of upgrade
			local_image				- (str) local location of upgrade
			is_special				- (bool) is upgrade a legendary upgrade?
			ship_restriction		- (list) list of ships that can only equip this
			nation_restriction		- (list) list of nations that this upgrade can be found
			tier_restriction		- (list) list of tiers that this upgrade can be found
			type_restriction		- (list) which ship types can this upgrade be found on
			slot					- (int) which slot can this upgrade be equiped on
			special_restriction		- (list) addition restrictions on this upgrade. Each items follows the following format:
										[Ship, Slot, Comments]
			on_other_ships			- (list) what other ships can this upgrade be found on beside its normal places

		otherwise:
			None - if legendary upgrade does not exists

		raise exceptions for dictionary
	"""
	# convert ship names with utf-8 chars to ascii
	if ship in ship_name_to_ascii:
		ship = ship_name_to_ascii[ship]
	for u in legendary_upgrades:
		upgrade = legendary_upgrades[u]
		if upgrade['ship_restriction'][0].lower() == ship:
			profile, name, price_gold, image, _, price_credit, _, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, tags = upgrade.values()
			return profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction
	return None

def get_skill_data(tree, skill):
	"""
		returns informations of a requested commander skill

		Arguments:
		-------
			- skill : (string)
				Skill's full name

		Returns:
		-------
		tuple:
			name		- (str) name of skill
			tree		- (str) skill belong to this ship type. found in hull_classification_converter
			description	- (str) skill's desctiption
			effect		- (str) skill's effect
			x			- (int) skill's column
			y			- (int) skill's tier (cost)
			category	- (str) skill's category

		raise exceptions for dictionary
	"""
	skill = skill.lower()
	try:
		# filter skills by tree
		ship_class_lookup = [i.lower() for i in hull_classification_converter.keys()] + [i.lower() for i in hull_classification_converter.values()]
		hull_class_lower = dict([(i.lower(), hull_classification_converter[i].lower()) for i in hull_classification_converter])

		if tree not in ship_class_lookup:
			# requested type is not in
			raise ValueError(f"Expected {[i for i in ship_class_lookup]}. Got {tree}.")
		else:
			# convert from hull classification to word

			if tree not in hull_class_lower:
				for h in hull_class_lower:
					if hull_class_lower[h].lower() == tree:
						tree = h.lower()
						break

			# looking for skill based on full name
			filtered_skill_list = dict([(s, skill_list[s]) for s in skill_list if skill_list[s]['tree'].lower() == tree])
			for f_s in filtered_skill_list:
				if filtered_skill_list[f_s]['name'].lower() == skill:
					s = filtered_skill_list[f_s].copy()
					if s['tree'] == 'AirCarrier':
						s['tree'] = "Aircraft Carrier"
					return s['name'], s['tree'], s['description'], s['effect'], s['x'] + 1, s['y'] + 1, s['category']
			# looking for skill based on abbreviation
			filtered_skill_list = dict([(s, skill_list[s]) for s in skill_list if skill_list[s]['tree'].lower() == tree])
			for f_s in filtered_skill_list:
				if filtered_skill_list[f_s]['abbr'].lower() == skill:
					s = filtered_skill_list[f_s].copy()
					if s['tree'] == 'AirCarrier':
						s['tree'] = "Aircraft Carrier"
					return s['name'], s['tree'], s['description'], s['effect'], s['x'] + 1, s['y'] + 1, s['category']
			return None

	except Exception as e:
		# oops, probably not found
		logging.info(f"Exception {type(e)}: ", e)
		raise e

def get_upgrade_data(upgrade):
	"""
		returns informations of a requested warship upgrade

		Arguments:
		-------
			- upgrade : (string)
				Upgrade's full name or abbreviation

		Returns:
		-------
		tuple:
			profile					- (dict) upgrade's bonuses
			name					- (str) upgrade name
			price_gold				- (int) upgrade price in doubloons
			image					- (str) image url
			price_credit			- (int) price in credits
			description				- (str) summary of upgrade
			local_image				- (str) local location of upgrade
			is_special				- (bool) is upgrade a legendary upgrade?
			ship_restriction		- (list) list of ships that can only equip this
			nation_restriction		- (list) list of nations that this upgrade can be found
			tier_restriction		- (list) list of tiers that this upgrade can be found
			type_restriction		- (list) which ship types can this upgrade be found on
			slot					- (int) which slot can this upgrade be equiped on
			special_restriction		- (list) addition restrictions on this upgrade. Each items follows the following format:
										[Ship, Slot, Comments]
			on_other_ships			- (list) what other ships can this upgrade be found on beside its normal places

		raise exceptions for dictionary
	"""
	upgrade = upgrade.lower()
	try:
		upgrade_found = False
		# assuming input is full upgrade name
		for i in upgrade_list:
			if upgrade.lower() == upgrade_list[i]['name'].lower():
				upgrade_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not upgrade_found:
			upgrade = upgrade_abbr_list[upgrade]
			for i in upgrade_list:
				if upgrade.lower() == upgrade_list[i]['name'].lower():
					upgrade_found = True
					break
		profile, name, price_gold, image, _, price_credit, _, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, _ = \
			upgrade_list[i].values()

		return profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction
	except Exception as e:
		logging.info(f"Exception {type(e)}: ", e)
		raise e

def get_commander_data(cmdr):
	"""
		returns informations of a requested warship upgrade

		Arguments:
		-------
			- cmdr : (string)
				Commander's full name

		Returns:
		-------
		tuple:
			name	- (str) commander's name
			icons	- (str) image url on WG's server
			nation	- (str) Commander's nationality

		raise exceptions for dictionary
	"""

	cmdr = cmdr.lower()
	try:
		cmdr_found = False
		if cmdr.lower() in cmdr_name_to_ascii:
			cmdr = cmdr_name_to_ascii[cmdr.lower()]
		for i in cmdr_list:
			if cmdr.lower() == cmdr_list[i]['first_names'][0].lower():
				cmdr_found = True
				break
		if cmdr_found:
			if not cmdr_list[i]['last_names']:
				# get special commaders
				name = cmdr_list[i]['first_names'][0]
				icons = cmdr_list[i]['icons'][0]['1']
				nation = cmdr_list[i]['nation']

				return name, icons, nation, i
	except Exception as e:
		logging.error(f"Exception {type(e)}", e)
		raise e

def get_flag_data(flag):
	"""
		returns informations of a requested warship upgrade

		Arguments:
		-------
			- cmdr : (string)
				Commander's full name

		Returns:
		-------
		tuple:
			profile			- (dict) flag's bonuses
			name			- (str) flag name
			price_gold		- (int) flag's price in doubloons
			image			- (str) image url on WG's server
			price_credit	- (int) flag's price in credits
			description		- (str) flag's summary

		raise exceptions for dictionary
	"""

	flag = flag.lower()
	try:
		flag_found = False
		# assuming input is full flag name
		for i in flag_list:
			if flag == flag_list[i]['name'].lower():
				flag_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not flag_found:
			for i in flag_list:
				if flag.lower() == flag_list[i]['name'].lower():
					flag_found = True
					break
		profile, name, price_gold, image, _, price_credit, _, description = flag_list[i].values()
		return profile, name, price_gold, image, price_credit, description

	except Exception as e:
		logging.info(f"Exception {type(e)}: ", e)
		raise e

def get_map_data(map):
	"""
		returns informations of a requested warship upgrade

		Arguments:
		-------
			- map : (string)
				map's name

		Returns:
		-------
		tuple:
			description	- (str) map's description
			image		- (str) image url on WG's server
			id			- (str) map id
			name		- (str) map's name

		raise exceptions for dictionary
	"""

	map = map.lower()
	try:
		for m in map_list:
			if map == map_list[m]['name'].lower():
				description, image, id, name = map_list[m].values()
				return description, image, id, name
	except Exception as e:
		logging.info("Exception {type(e): ", e)
		raise e


	
@mackbot.event
async def on_ready():
	await mackbot.change_presence(activity=discord.Game(command_prefix + cmd_sep + 'help'))
	logging.info("Logged on")

@mackbot.command()
async def whoami(context):
	
	async with context.typing():
		m = "I'm a bot made by mackwafang#2071 to help players with clan build. I also includes the WoWS Encyclopedia!"
	await context.send(m)

@mackbot.command()
async def goodbot(context):
	# good bot
	r = randint(len(good_bot_messages))
	logging.info(f"send reply message for goodbot")
	await context.send(good_bot_messages[r])  # block until message is sent

@mackbot.command()
async def feedback(context):
	logging.info("send feedback link")
	await context.send(
		f"Need to rage at mack because he ~~fucks up~~ did goofed on a feature? Submit a feedback form here!\nhttps://forms.gle/Lqm9bU5wbtNkpKSn7")

async def build(context, arg):
	# get voted ship build
	# message parse
	ship_found = False
	if len(arg) <= 2:
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if embed is not None:
			await context.send(embed=embed)
	else:
		requested_image = arg[-1].lower() == 'image'
		if requested_image:
			arg = arg[:-1]
		battle_type = arg[2].lower()  # assuming build battle type is provided
		additional_comp_keywords = ['comp']
		if battle_type in build_battle_type_value or battle_type in additional_comp_keywords:
			# 2nd argument provided is a known argument
			battle_type = 'competitive'
			ship = ''.join([i + ' ' for i in arg[3:]])[:-1]  # grab ship name
		else:
			battle_type = 'casual'
			ship = ''.join([i + ' ' for i in arg[2:]])[:-1]  # grab ship name
		if requested_image:
			# try to get image format for this build
			try:
				async with context.typing():
					output = get_ship_data(ship, battle_type=battle_type)
					if output is None:
						raise NameError("NoBuildFound")
					name, nation, images, ship_type, tier, _, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = output
					logging.info(f"returning build information for <{name}> in image format")
					filename = f'./{name.lower()}_{battle_type}_build.png'
					if os.path.isfile(filename):
						# get server emoji
						if message.guild is not None:
							server_emojis = message.guild.emojis
						else:
							server_emojis = []

						# image exists!
						tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
						type_icon = f':{ship_type.lower()}:' if ship_type != "AirCarrier" else f':carrier:'
						if is_prem:
							type_icon = type_icon[:-1] + '_premium:'
						# find the server emoji id for this emoji id
						if len(server_emojis) == 0:
							type_icon = ""
						else:
							if type_icon[1:-1] in [i.name for i in server_emojis]:
								for i in server_emojis:
									if type_icon[1:-1] == i.name:
										type_icon = str(i)
										break
							else:
								type_icon = ""
						m = f'**{tier_string:<4}** {type_icon} {name} {battle_type.title()} Build'
						await context.send(m, file=discord.File(filename))
					else:
						# does not exists
						await context.send(f"An Image build for {name} does not exists. Sending normal message.")
						await self.build(message, arg)

			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				if type(e) == discord.errors.Forbidden:
					await context.send(f"I need the **Attach Files Permission** to use this feature!")
					await self.build(message, arg)
				else:
					ship_name_list = [ship_list[i]['name'] for i in ship_list]
					closest_match = difflib.get_close_matches(ship, ship_name_list)
					closest_match_string = ""
					if len(closest_match) > 0:
						closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

					await context.send(f"Ship **{ship}** is not understood.{closest_match_string}")
		else:
			# get text-based format build
			try:
				async with context.typing():
					output = get_ship_data(ship, battle_type=battle_type)
					if output is None:
						raise NameError("NoBuildFound")
					name, nation, images, ship_type, tier, _, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = output
					logging.info(f"returning build information for <{name}> in embeded format")
					ship_type = ship_types[ship_type]  # convert weegee ship type to hull classifications
					embed = discord.Embed(title=f"{battle_type.title()} Build for {name}", description='')
					embed.set_thumbnail(url=images['small'])
					# get server emoji
					if message.guild is not None:
						server_emojis = message.guild.emojis
					else:
						server_emojis = []

					tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()

					embed.description += f'**Tier {tier_string} {nation_dictionary[nation]} {"Premium " + ship_type if is_prem else ship_type}**'

					footer_message = ""
					error_value_found = False
					if len(upgrades) > 0 and len(skills) > 0 and len(cmdr) > 0:
						# suggested upgrades
						if len(upgrades) > 0:
							m = ""
							i = 1
							for upgrade in upgrades:
								upgrade_name = "[Missing]"
								if upgrade == '*':
									# any thing
									upgrade_name = "Any"
								else:
									try:  # ew, nested try/catch
										upgrade_name = get_upgrade_data(upgrade)[1]
									except Exception as e:
										logging.info(f"Exception {type(e)}", e, f"in ship, listing upgrade {i}")
										error_value_found = True
										upgrade_name = upgrade + ":warning:"
								m += f'(Slot {i}) **' + upgrade_name + '**\n'
								i += 1
							embed.add_field(name='Suggested Upgrades', value=m, inline=False)
						else:
							embed.add_field(name='Suggested Upgrades', value="Coming Soon:tm:", inline=False)
						# suggested skills
						if len(skills) > 0:
							m = ""
							i = 1
							for skill in skills:
								skill_name = "[Missing]"
								try:  # ew, nested try/catch
									skill_name, id, skill_type, perk, tier, icon = get_skill_data(skill)
								except Exception as e:
									logging.info(f"Exception {type(e)}", e, f"in ship, listing skill {i}")
									error_value_found = True
									skill_name = skill + ":warning:"
								m += f'(Tier {tier}) **' + skill_name + '**\n'
								i += 1
							embed.add_field(name='Suggested Cmdr. Skills', value=m, inline=False)
						else:
							embed.add_field(name='Suggested Cmdr. Skills', value="Coming Soon:tm:", inline=False)
						# suggested commander
						if cmdr != "":
							m = ""
							if cmdr == "*":
								m = "Any"
							else:
								try:
									m = get_commander_data(cmdr)[0]
								except Exception as e:
									logging.info(f"Exception {type(e)}", e, "in ship, listing commander")
									error_value_found = True
									m = f"{cmdr}:warning:"
							# footer_message += "Suggested skills are listed in ascending acquiring order.\n"
							embed.add_field(name='Suggested Cmdr.', value=m)
						else:
							embed.add_field(name='Suggested Cmdr.', value="Coming Soon:tm:", inline=False)
						footer_message += f"For {'casual' if battle_type == 'competitive' else 'competitive'} builds, use [mackbot build {'casual' if battle_type == 'competitive' else 'competitive'} {ship}]\n"
						footer_message += f"For image variant of this message, use [mackbot build {battle_type} {ship} image]\n"
					else:
						m = "mackbot does not know any build for this ship :("
						u, c, s = get_ship_data(ship,
												 battle_type='casual' if battle_type == 'competitive' else 'competitive')[
								  -4:-1]
						if len(u) > 0 and len(c) > 0 and len(s) > 0:
							m += '\n\n'
							m += f"But, There is a {'casual' if battle_type == 'competitive' else 'competitive'} build for this ship!\n"
							m += f"Use [**mackbot build {'casual' if battle_type == 'competitive' else 'competitive'} {ship}**]"
						embed.add_field(name=f'No known {battle_type} build', value=m, inline=False)
				error_footer_message = ""
				if error_value_found:
					error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact mackwafang#2071.\n"
				embed.set_footer(text=error_footer_message + footer_message)
				await context.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				# error, ship name not understood
				ship_name_list = [ship_list[i]['name'] for i in ship_list]
				closest_match = difflib.get_close_matches(ship, ship_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

				await context.send(f"Ship **{ship}** is not understood" + closest_match_string)

@mackbot.command(help="")
async def ship(context, *arg):
	print(arg)
	# message parse
	if len(arg) == 0:
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if not embed is None:
			await context.send(embed=embed)
	else:
		arg = ''.join([i + ' ' for i in arg])  # fuse back together to check filter
		has_filter = '(' in arg and ')' in arg  # find a better check
		param_filter = ''
		if has_filter:
			param_filter = arg[arg.find('(') + 1: arg.rfind(')')]
			arg = arg[:arg.find('(') - 1]
		arg = arg.split(' ')
		ship = ''.join([i + ' ' for i in arg])[:-1]  # grab ship name
		if not param_filter:
			ship = ship[:-1]

		try:
			async with context.typing():
				ship_param = get_ship_param(ship)
				output = get_ship_data(ship)
				if output is None:
					raise NameError("NoShipFound")
				name, nation, images, ship_type, tier, consumables, modules, _, is_prem, price_gold, price_credit, price_xp, _, _, _, _ = output
				logging.info(f"returning ship information for <{name}> in embeded format")
				ship_type = ship_types[ship_type]

				if ship_type == 'Cruiser':
					# reclassify cruisers to their correct classification based on the washington naval treaty

					# check for the highest caliber
					highest_caliber = sorted(modules['artillery'],
											 key=lambda x: module_list[str(x)]['profile']['artillery']['caliber'],
											 reverse=True)
					highest_caliber = \
						[module_list[str(i)]['profile']['artillery']['caliber'] for i in highest_caliber][0] * 1000

					if highest_caliber <= 155:
						# if caliber less than or equal to 155mm
						ship_type = "Light Cruiser"
					elif highest_caliber <= 203:
						# if caliber between 155mm and up to 203mm
						ship_type = "Heavy Cruiser"
					else:
						ship_type = "Battlecruiser"
				embed = discord.Embed(title=f"{ship_type} {name}", description='')
				embed.set_thumbnail(url=images['small'])
				# get server emoji
				if context.guild is not None:
					server_emojis = context.guild.emojis
				else:
					server_emojis = []

				# emoji exists!
				tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()

				# defines ship params filtering
				hull_filter = 0
				guns_filter = 1
				atbas_filter = 2
				torps_filter = 3
				rockets_filter = 4
				torpbomber_filter = 5
				bomber_filter = 6
				engine_filter = 7
				aa_filter = 8
				conceal_filter = 9
				consumable_filter = 10

				ship_filter = 0b11111111111  # assuming no filter is provided, display all
				# grab filters
				if len(param_filter) > 0:
					ship_filter = 0b00000000000  # filter is requested, disable all
					# s = ship_param_filter_regex.findall(''.join([i + ' ' for i in param_filter]))
					s = ship_param_filter_regex.findall(param_filter)  # what am i looking for?

					def is_filter_requested(x):
						# check length of regex capture groups. if len > 0, request is valid
						return 1 if len([i[x - 1] for i in s if len(i[x - 1]) > 0]) > 0 else 0

					# enables proper filter
					ship_filter |= is_filter_requested(2) << hull_filter
					ship_filter |= is_filter_requested(3) << guns_filter
					ship_filter |= is_filter_requested(4) << atbas_filter
					ship_filter |= is_filter_requested(6) << torps_filter
					ship_filter |= is_filter_requested(8) << rockets_filter
					ship_filter |= is_filter_requested(5) << torpbomber_filter
					ship_filter |= is_filter_requested(7) << bomber_filter
					ship_filter |= is_filter_requested(9) << engine_filter
					ship_filter |= is_filter_requested(10) << aa_filter
					ship_filter |= is_filter_requested(11) << conceal_filter
					ship_filter |= is_filter_requested(12) << consumable_filter

				embed.description += f'**Tier {tier_string} {nation_dictionary[nation]} {"Premium " + ship_type if is_prem else ship_type}**\n'

				def is_filtered(x):
					return (ship_filter >> x) & 1 == 1
				if price_credit > 0 and price_xp > 0:
					embed.description += '\n{:,} XP\n{:,} Credits'.format(price_xp, price_credit)
				if price_gold > 0 and is_prem:
					embed.description += '\n{:,} Doubloons'.format(price_gold)

				# General hull info
				if len(modules['hull']) > 0 and is_filtered(hull_filter):
					m = ""
					for h in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name']):
						hull = module_list[str(h)]['profile']['hull']
						m += f"**{module_list[str(h)]['name']}:** **{hull['health']} HP**\n"
						if hull['artillery_barrels'] > 0:
							m += f"{hull['artillery_barrels']} Main Turret{'s' if hull['artillery_barrels'] > 1 else ''}\n"
						if hull['torpedoes_barrels'] > 0:
							m += f"{hull['torpedoes_barrels']} Torpedoes Launcher{'s' if hull['torpedoes_barrels'] > 1 else ''}\n"
						if hull['atba_barrels'] > 0:
							m += f"{hull['atba_barrels']} Secondary Turret{'s' if hull['atba_barrels'] > 1 else ''}\n"
						if hull['planes_amount'] > 0:
							m += f"{hull['planes_amount']} Aircraft{'s' if hull['planes_amount'] > 1 else ''}\n"
						# if ship_param['armour']['flood_damage'] > 0 or ship_param['armour']['flood_prob'] > 0:
						# m += '\n'
						# if ship_param['armour']['flood_damage'] > 0:
						# m += f"**Torp. Damage**: -{ship_param['armour']['flood_damage']}%\n"
						# if ship_param['armour']['flood_prob'] > 0:
						# m += f"**Flood Chance**: -{ship_param['armour']['flood_prob']}%\n"
						m += '\n'
					embed.add_field(name="__**Hull**__", value=m, inline=False)
					
					
					if 'airSupport' in module_list[str(h)]['profile']:
					# air support info
						m = ''
						for h in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name']):
							hull = module_list[str(h)]['profile']['hull']
							m += f"**{module_list[str(h)]['name']}**\n"
							airsup_info = module_list[str(h)]['profile']['airSupport']
							
							airsup_reload_m = int(airsup_info['reloadTime'] // 60)
							airsup_reload_s = int(airsup_info['reloadTime'] % 60)
							
							m += f"{airsup_info['chargesNum']} charge(s)\n"
							m += f"Reload: {str(airsup_reload_m)+'m' if airsup_reload_m > 0 else ''} {str(airsup_reload_s)+'s' if airsup_reload_s > 0 else ''}\n"
							
							if ship_filter == 2 ** hull_filter:
								# detailed air support filter
								m += f"**Aircraft**: {airsup_info['payload']} bombs\n"
								m += f"**Squadron**: {airsup_info['squad_size']} aircrafts\n"
								m += f"**HE Bomb**: :boom:{airsup_info['max_damage']} (:fire:{airsup_info['burn_probability']}%, Pen. {int(airsup_info['bomb_pen'])}mm)\n"
							
							m += '\n'
						embed.add_field(name="__**Air Support**__", value=m, inline=False)

				# guns info
				if len(modules['artillery']) > 0 and is_filtered(guns_filter):
					m = ""
					m += f"**Range: **"
					for fc in sorted(modules['fire_control'],
									 key=lambda x: module_list[str(x)]['profile']['fire_control']['distance']):
						m += f"{module_list[str(fc)]['profile']['fire_control']['distance']} - "
					m = m[:-2]
					m += "km\n"
					for h in sorted(modules['artillery'], key=lambda x: module_list[str(x)]['name']):
						guns = module_list[str(h)]['profile']['artillery']
						m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')} ({int(guns['numBarrels'])} barrel{'s' if guns['numBarrels'] > 1 else ''}):**\n"
						
						dpm_multiplier = 60 / guns['gun_rate'] * guns['numBarrels']
						
						if guns['max_damage_HE']:
							m += f"**HE:** {guns['max_damage_HE']} (:fire: {guns['burn_probability']}%"
							if guns['pen_HE'] > 0:
								m += f", Pen {guns['pen_HE']} mm, {int(guns['max_damage_HE'] * dpm_multiplier)} DPM)\n"
							else:
								m += f")\n"
						if guns['max_damage_SAP'] > 0:
							m += f"**SAP:** {guns['max_damage_SAP']} (Pen {guns['pen_SAP']} mm, {int(guns['max_damage_SAP'] * dpm_multiplier)} DPM)\n"
						if guns['max_damage_AP'] > 0:
							m += f"**AP:** {guns['max_damage_AP']}, ({int(guns['max_damage_AP'] * dpm_multiplier)} DPM)\n"
						m += f"**Reload:** {guns['gun_rate']:0.1f}s\n"

						m += '\n'
					embed.add_field(name="__**Main Battery**__", value=m)

				# secondary armaments
				if ship_param['atbas'] is not None and is_filtered(atbas_filter):
					m = ""
					m += f"**Range:** {ship_param['atbas']['distance']} km\n"
					for slot in ship_param['atbas']['slots']:
						guns = ship_param['atbas']['slots'][slot]
						m += f"**{guns['name'].replace(chr(10), ' ')} :**\n"
						if guns['damage'] > 0:
							m += f"**HE:** {guns['damage']}\n"
						m += f"**Reload:** {guns['shot_delay']}s\n"

						m += '\n'
					embed.add_field(name="__**Secondary Battery**__", value=m)

				# anti air
				if len(modules['hull']) > 0 and is_filtered(aa_filter):
					m = ""

					if ship_filter == 2 ** aa_filter:
						# detailed aa
						for hull in modules['hull']:
							aa = module_list[str(hull)]['profile']['anti_air']
							m += f"**{name} ({aa['hull']})**\n"
							m += f"**Range:** {aa['min_range'] / 1000:0.1f}-{aa['max_range'] / 1000:0.1f} km\n"

							rating_descriptor = ""
							for d in AA_RATING_DESCRIPTOR:
								low, high = AA_RATING_DESCRIPTOR[d]
								if low <= aa['rating'] <= high:
									rating_descriptor = d
									break
							m += f"**AA Rating (vs. T{tier}):** {int(aa['rating'])} ({rating_descriptor})\n"
							# provide more AA detail
							flak = aa['flak']
							near = aa['near']
							medium = aa['medium']
							far = aa['far']
							if flak['damage'] > 0:
								m += f"**Flak:** {flak['min_range'] / 1000:0.1f}-{flak['max_range'] / 1000:0.1f} km, {int(flak['count'])} burst{'s' if flak['count'] > 0 else ''}, {int(flak['count'] * flak['damage'])}:boom:\n"
							if near['damage'] > 0:
								m += f"**Short Range:** {near['damage']:0.1f} (up to {near['range'] / 1000:0.1f} km, {int(near['hitChance'] * 100)}%)\n"
							if medium['damage'] > 0:
								m += f"**Mid Range:** {medium['damage']:0.1f} (up to {medium['range'] / 1000:0.1f} km, {int(medium['hitChance'] * 100)}%)\n"
							if far['damage'] > 0:
								m += f"**Long Range:** {far['damage']:0.1f} (up to {aa['max_range'] / 1000:0.1f} km, {int(far['hitChance'] * 100)}%)\n"
							m += '\n'
					else:
						# compact detail
						aa = module_list[str(modules['hull'][0])]['profile']['anti_air']
						average_rating = sum([module_list[str(hull)]['profile']['anti_air']['rating'] for hull in
											  modules['hull']]) / len(modules['hull'])
						m += f"**Range:** {aa['min_range'] / 1000:0.1f}-{aa['max_range'] / 1000:0.1f} km\n"

						rating_descriptor = ""
						for d in AA_RATING_DESCRIPTOR:
							low, high = AA_RATING_DESCRIPTOR[d]
							if low <= average_rating <= high:
								rating_descriptor = d
								break
						m += f"**Average AA Rating:** {int(average_rating)} ({rating_descriptor})\n"

					embed.add_field(name="__**Anti-Air**__", value=m)

				# torpedoes
				if len(modules['torpedoes']) > 0 and is_filtered(torps_filter):
					m = ""
					for h in sorted(modules['torpedoes'], key=lambda x: module_list[str(x)]['name']):
						torps = module_list[str(h)]['profile']['torpedoes']
						
						m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')} ({torps['distance']} km, {int(torps['numBarrels'])} tube{'s' if torps['numBarrels'] > 1 else ''}):**\n"
						reload_minute = int(torps['shotDelay'] // 60)
						reload_second = int(torps['shotDelay'] % 60)
						m += f"**Reload:** {'' if reload_minute == 0 else str(reload_minute) + 'm'} {reload_second}s\n"
						m += f"**Damage:** {torps['max_damage']}\n"
						m += f"**Speed:** {torps['torpedo_speed']} kts.\n"
						m += '\n'
					embed.add_field(name="__**Torpedoes**__", value=m)

				# attackers
				if len(modules['fighter']) > 0 and is_filtered(rockets_filter):
					m = ""
					for h in sorted(modules['fighter'],
									key=lambda x: module_list[str(x)]['profile']['fighter']['max_health']):
						fighter_module = module_list[str(h)]
						fighter = module_list[str(h)]['profile']['fighter']
						n_attacks = fighter_module['squad_size'] // fighter_module['attack_size']
						m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')}**\n"
						if ship_filter == 2 ** rockets_filter:
							m += f"**Aircraft:** {fighter['cruise_speed']:0.0f} kts. (up to {fighter['cruise_speed'] * fighter_module['speed_max']:0.0f} kts), {fighter['max_health']} HP, {fighter_module['payload']} rocket{'s' if fighter_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {fighter_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {fighter_module['attack_size']})\n"
							m += f"**Hangar:** {fighter_module['hangarSettings']['startValue']} aircrafts (Restore {fighter_module['hangarSettings']['restoreAmount']} aircraft every {int(fighter_module['hangarSettings']['timeToRestore'])}s)\n"
							m += f"**{fighter_module['profile']['fighter']['rocket_type']} Rocket:** :boom:{fighter['max_damage']} {'(:fire:' + str(fighter['burn_probability']) + '%, Pen. ' + str(fighter['rocket_pen']) + 'mm)' if fighter['burn_probability'] > 0 else ''}\n"
							m += '\n'
					embed.add_field(name="__**Attackers**__", value=m, inline=False)

				# torpedo bomber
				if len(modules['torpedo_bomber']) > 0 and is_filtered(torpbomber_filter):
					m = ""
					for h in sorted(modules['torpedo_bomber'],key=lambda x: module_list[str(x)]['profile']['torpedo_bomber']['max_health']):
						bomber_module = module_list[str(h)]
						bomber = module_list[str(h)]['profile']['torpedo_bomber']
						n_attacks = bomber_module['squad_size'] // bomber_module['attack_size']
						m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')}**\n"
						if ship_filter == 2 ** torpbomber_filter:
							m += f"**Aircraft:** {bomber['cruise_speed']:0.0f} kts. (up to {bomber['cruise_speed'] * bomber_module['speed_max']:0.0f} kts), {bomber['max_health']} HP, {bomber_module['payload']} torpedo{'es' if bomber_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
							m += f"**Hangar:** {bomber_module['hangarSettings']['startValue']} aircrafts (Restore {bomber_module['hangarSettings']['restoreAmount']} aircraft every {int(bomber_module['hangarSettings']['timeToRestore'])}s)\n"
							m += f"**Torpedo:** :boom:{bomber['max_damage']:0.0f}, {bomber['torpedo_speed']} kts\n"
							m += '\n'
					embed.add_field(name="__**Torpedo Bomber**__", value=m, inline=len(modules['fighter']) > 0)

				# dive bombers
				if len(modules['dive_bomber']) > 0 and is_filtered(bomber_filter):
					m = ""
					for h in sorted(modules['dive_bomber'], key=lambda x: module_list[str(x)]['profile']['dive_bomber']['max_health']):
						bomber_module = module_list[str(h)]
						bomber = module_list[str(h)]['profile']['dive_bomber']
						n_attacks = bomber_module['squad_size'] // bomber_module['attack_size']
						m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')}**\n"
						if ship_filter == 2 ** bomber_filter:
							m += f"**Aircraft:** {bomber['cruise_speed']:0.0f} kts. (up to {bomber['cruise_speed'] * bomber_module['speed_max']:0.0f} kts), {bomber['max_health']} HP, {bomber_module['payload']} bomb{'s' if bomber_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
							m += f"**Hangar:** {bomber_module['hangarSettings']['startValue']} aircrafts (Restore {bomber_module['hangarSettings']['restoreAmount']} aircraft every {int(bomber_module['hangarSettings']['timeToRestore'])}s)\n"
							m += f"**{bomber_module['bomb_type']} Bomb:** :boom:{bomber['max_damage']:0.0f} {'(:fire:' + str(bomber['burn_probability']) + '%, Pen. ' + str(bomber_module['bomb_pen']) + 'mm)' if bomber['burn_probability'] > 0 else ''}\n"
							m += '\n'
					embed.add_field(name="__**Bombers**__", value=m, inline=len(modules['torpedo_bomber']) > 0)
				
				if len(modules['skip_bomber']) > 0 and is_filtered(bomber_filter):
					m = ""
					for h in sorted(modules['skip_bomber'], key=lambda x: module_list[str(x)]['profile']['skip_bomber']['max_health']):
						bomber_module = module_list[str(h)]
						bomber = module_list[str(h)]['profile']['skip_bomber']
						n_attacks = bomber_module['squad_size'] // bomber_module['attack_size']
						m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')}**\n"
						if ship_filter == 2 ** bomber_filter:
							m += f"**Aircraft:** {bomber['cruise_speed']:0.0f} kts. (up to {bomber['cruise_speed'] * bomber_module['speed_max']:0.0f} kts), {bomber['max_health']} HP, {bomber_module['payload']} bomb{'s' if bomber_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
							m += f"**Hangar:** {bomber_module['hangarSettings']['startValue']} aircrafts (Restore {bomber_module['hangarSettings']['restoreAmount']} aircraft every {int(bomber_module['hangarSettings']['timeToRestore'])}s)\n"
							m += f"**{bomber_module['bomb_type']} Bomb:** :boom:{bomber['max_damage']:0.0f} {'(:fire:' + str(bomber['burn_probability']) + '%, Pen. ' + str(bomber_module['bomb_pen']) + 'mm)' if bomber['burn_probability'] > 0 else ''}\n"
							m += '\n'
					embed.add_field(name="__**Bombers**__", value=m, inline=len(modules['dive_bomber']) > 0)

				# engine
				if len(modules['engine']) > 0 and is_filtered(engine_filter):
					m = ""
					for e in sorted(modules['engine'], key=lambda x: module_list[str(x)]['name']):
						engine = module_list[str(e)]['profile']['engine']
						m += f"**{module_list[str(e)]['name']}**: {engine['max_speed']} kts\n"
						m += '\n'
					embed.add_field(name="__**Engine**__", value=m, inline=False)

				# concealment
				if ship_param['concealment'] is not None and is_filtered(conceal_filter):
					m = ""
					m += f"**By Sea**: {ship_param['concealment']['detect_distance_by_ship']} km\n"
					m += f"**By Air**: {ship_param['concealment']['detect_distance_by_plane']} km\n"
					embed.add_field(name="__**Concealment**__", value=m, inline=True)

				# consumables
				if len(consumables) > 0 and is_filtered(consumable_filter):
					m = ""
					for consumable_slot in consumables:
						if len(consumables[consumable_slot]['abils']) > 0:
							m += f"__**Slot {consumables[consumable_slot]['slot'] + 1}:**__ "
							if ship_filter == (1 << consumable_filter):
								m += '\n'
							for c in consumables[consumable_slot]['abils']:
								consumable_id, consumable_type = c
								consumable = game_data[find_game_data_item(consumable_id)[0]][consumable_type]
								consumable_name = consumable_descriptor[consumable['consumableType']]['name']
								# consumable_description = consumable_descriptor[consumable['consumableType']]['description']
								consumable_type = consumable["consumableType"]

								charges = 'Infinite' if consumable['numConsumables'] < 0 else consumable['numConsumables']
								action_time = consumable['workTime']
								cd_time = consumable['reloadTime']

								m += f"**{consumable_name}** "
								if ship_filter == (1 << consumable_filter): # shows detail of consumable
									consumable_detail = ""
									if consumable_type == 'airDefenseDisp':
										consumable_detail = f'Continous AA damage: +{consumable["areaDamageMultiplier"] * 100:0.0f}%\nFlak damage: +{consumable["bubbleDamageMultiplier"] * 100:0.0f}%'
									if consumable_type == 'artilleryBoosters':
										consumable_detail = f'Reload Time: -50%'
									if consumable_type == 'regenCrew':
										consumable_detail = f'Repairs {consumable["regenerationHPSpeed"] * 100}% of max HP / sec.\n'
										for h in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name']):
											hull = module_list[str(h)]['profile']['hull']
											consumable_detail += f"{module_list[str(h)]['name']} ({hull['health']} HP): {int(hull['health'] * consumable['regenerationHPSpeed'])} HP / sec., {int(hull['health'] * consumable['regenerationHPSpeed'] * consumable['workTime'])} HP per use\n"
										consumable_detail = consumable_detail[:-1]
									if consumable_type == 'rls':
										consumable_detail = f'Range: {round(consumable["distShip"] / 3) / 10:0.1f} km'
									if consumable_type == 'scout':
										consumable_detail = f'Main Battery firing range: +{(consumable["artilleryDistCoeff"] - 1) * 100:0.0f}%'
									if consumable_type == 'smokeGenerator':
										consumable_detail = f'Smoke lasts {str(int(consumable["lifeTime"] // 60)) + "m" if consumable["lifeTime"] >= 60 else ""} {str(int(consumable["lifeTime"] % 60)) + "s" if consumable["lifeTime"] % 60 > 0 else ""}\nSmoke radius: {consumable["radius"] * 10} meters\nConceal user up to {consumable["speedLimit"]} knots while active.'
									if consumable_type == 'sonar':
										consumable_detail = f'Assured Ship Range: {round(consumable["distShip"] / 3) / 10:0.1f}km\nAssured Torp. Range: {round(consumable["distTorpedo"] / 3) / 10:0.1f} km'
									if consumable_type == 'speedBoosters':
										consumable_detail = f'Max Speed: +{consumable["boostCoeff"] * 100:0.0f}%'
									if consumable_type == 'torpedoReloader':
										consumable_detail = f'Torpedo Reload Time lowered to {consumable["torpedoReloadTime"]:1.0f}s'
										
									m += '\n'
									m += f"{charges} charge{'s' if charges != 1 else ''}, "
									m += f"{f'{action_time // 60:1.0f}m ' if action_time >= 60 else ''} {str(int(action_time % 60)) + 's' if action_time % 60 > 0 else ''} duration, "
									m += f"{f'{cd_time // 60:1.0f}m ' if cd_time >= 60 else ''} {str(int(cd_time % 60)) + 's' if cd_time % 60 > 0 else ''} cooldown.\n"
									if len(consumable_detail) > 0:
										m += consumable_detail
										m += '\n'
								else:
									if len(consumables[consumable_slot]['abils']) > 1:
										m += 'or '
							m += '\n'
					embed.add_field(name="__**Consumables**__", value=m, inline=False)
				embed.set_footer(text="Parameters does not take into account upgrades and commander skills\n" +
									  f"For details specific parameters, use [mackbot ship {ship} (parameters)]\n" +
									  f"DPM refers to damage per minute for a single turret.")
			await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}", e)
			# error, ship name not understood
			if e == IndexError:
				await context.send(f"Ship **{ship}** is not known")
			else:
				ship_name_list = [ship_list[i]['name'] for i in ship_list]
				closest_match = difflib.get_close_matches(ship, ship_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

				await context.send(f"Ship **{ship}** is not understood" + closest_match_string)

@mackbot.command()
async def skill(context, *arg):
	# get information on requested skill
	# message parse
	if len(arg) == 0:
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if embed is not None:
			await context.send(embed=embed)
	else:
		try:
			ship_class = arg[0].lower()
			skill = ''.join([i + ' ' for i in arg[1:]])[:-1]  # message_string[message_string.rfind('-')+1:]

			logging.info(f'sending message for skill <{skill}>')
			async with context.typing():
				name, tree, description, effect, column, tier, category = get_skill_data(ship_class, skill)
				embed = discord.Embed(title=f"{name}", description="")
				# embed.set_thumbnail(url=icon)
				embed.description += f"**{tree} Skill**\n"
				embed.description += f"**Tier {tier} {category} Skill**, "
				embed.description += f"**Column {column}**"
				embed.add_field(name='Description', value=description, inline=False)
				embed.add_field(name='Effect', value=effect, inline=False)
			await context.send(embed=embed)
		except Exception as e:
			logging.info("Exception", type(e), ":", e)
			# error, skill name not understood
			skill_name_list = [skill_list[i]['name'] for i in skill_list]
			closest_match = difflib.get_close_matches(skill, skill_name_list)
			closest_match_string = ""
			if len(closest_match) > 0:
				closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

			await context.send(f"Skill **{skill}** is not understood." + closest_match_string)

@mackbot.group(pass_context=True, invoke_without_command=True)
async def list(context, *args):
	# list command
	if context.invoked_subcommand is None:
		await context.invoke(mackbot.get_command('help'), 'list')

@list.command()
async def skills(context, *args):
	# list all skills
	embed = discord.Embed(name="Commander Skill")

	search_param = args
	search_param = skill_list_regex.findall(''.join([i + ' ' for i in search_param]))

	filtered_skill_list = skill_list.copy()

	# filter by ship class
	ship_class = [i[0] for i in search_param if len(i[0]) > 0]
	# convert hull classification to ship type full name
	ship_class = ship_class[0] if len(ship_class) >= 1 else ''
	if len(ship_class) > 0:
		if len(ship_class) <= 2:
			for h in hull_classification_converter:
				if ship_class == hull_classification_converter[h].lower():
					ship_class = h.lower()
					break
		if ship_class.lower() in ['cv', 'carrier']:
			ship_class = 'aircarrier'
		filtered_skill_list = dict([(s, filtered_skill_list[s]) for s in filtered_skill_list if filtered_skill_list[s]['tree'].lower() == ship_class])
	# filter by skill tier
	tier = [i[2] for i in search_param if len(i[2]) > 0]
	tier = int(tier[0]) if len(tier) >= 1 else 0
	if tier != 0:
		filtered_skill_list = dict([(s, filtered_skill_list[s]) for s in filtered_skill_list if filtered_skill_list[s]['y'] + 1 == tier])

	# select page
	page = [i[1] for i in search_param if len(i[1]) > 0]
	page = int(page[0]) if len(page) > 1 else 0

	# generate list of skills
	m = [
		f"**({hull_classification_converter[filtered_skill_list[s]['tree']]} T{filtered_skill_list[s]['y']+1})** {filtered_skill_list[s]['name']}" for s in filtered_skill_list
	]

	# splitting list into pages
	num_items = len(m)
	m.sort()
	items_per_page = 24
	num_pages = (len(m) // items_per_page)
	m = [m[i:i + items_per_page] for i in range(0, len(m), items_per_page)]

	embed = discord.Embed(title="Commander Skill (%i/%i)" % (page + 1, num_pages))
	m = m[page]  # select page
	# spliting selected page into columns
	m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]
	for i in m:
		embed.add_field(name="Upgrade", value=''.join([v + '\n' for v in i]))
	embed.set_footer(text=f"{num_items} skills found.\nFor more information on a skill, use [{command_prefix} skill [ship_class] [skill_name]]")
	
	await context.send(embed=embed)

@list.command()
async def upgrades(context, *args):
	# list upgrades
	embed = None
	try:
		# parsing search parameters
		logging.info("starting parameters parsing")
		search_param = args
		s = equip_regex.findall(''.join([i + ' ' for i in search_param]))

		slot = ''.join([i[1] for i in s])
		key = [i[7] for i in s if len(i[7]) > 1]
		page = [i[6] for i in s if len(i[6]) > 1]
		tier = [i[3] for i in s if len(i[3]) > 1]
		embed_title = "Search result for: "

		try:
			page = int(page[0]) - 1
		except:
			page = 0

		if len(tier) > 0:
			for t in tier:
				if t in roman_numeral:
					t = roman_numeral[t]
				tier = f't{t}'
				key += [t]
		if len(slot) > 0:
			key += [slot]
		key = [i.lower() for i in key if not 'page' in i]
		embed_title += f"{''.join([i.title() + ' ' for i in key])}"
		# look up
		result = []
		for u in upgrade_list:
			tags = [str(i).lower() for i in upgrade_list[u]['tags']]
			if np.all([k in tags for k in key]):
				result += [u]
		logging.info("parsing complete")
		logging.info("compiling message")
		if len(result) > 0:
			m = []
			for u in result:
				upgrade = upgrade_list[u]
				name = get_upgrade_data(upgrade['name'])[1]
				for u_b in upgrade_abbr_list:
					if upgrade_abbr_list[u_b] == name.lower():
						m += [f"**{name}** ({u_b.upper()})"]
						break

			num_items = len(m)
			m.sort()
			items_per_page = 30
			num_pages = (len(m) // items_per_page)
			m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

			embed = discord.Embed(title=embed_title + f"({page + 1}/{num_pages + 1})")
			m = m[page]  # select page
			m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
			embed.set_footer(text=f"{num_items} upgrades found.\nFor more information on an upgrade, use [{command_prefix} upgrade [name/abbreviation]]")
			for i in m:
				embed.add_field(name="Upgrade (abbr.)", value=''.join([v + '\n' for v in i]))
		else:
			embed = discord.Embed(title=embed_title, description="")
			embed.description = "No upgrades found"
	except Exception as e:
		if type(e) == IndexError:
			error_message = f"Page {page + 1} does not exists"
		elif type(e) == ValueError:
			logging.info(f"Upgrade listing argument <{arg[3]}> is invalid.")
			error_message = f"Value {arg[3]} is not understood"
		else:
			logging.info(f"Exception {type(e)}", e)
	await context.send(embed=embed)

@list.command()
async def maps(context, *args):
	# list all maps
	try:
		logging.info("sending list of maps")
		try:
			page = int(arg[3]) - 1
		except:
			page = 0
		m = [f"{map_list[i]['name']}" for i in map_list]
		m.sort()
		items_per_page = 20
		num_pages = (len(map_list) // items_per_page)

		m = [m[i:i + items_per_page] for i in range(0, len(map_list), items_per_page)]  # splitting into pages
		embed = discord.Embed(title="Map List " + f"({page + 1}/{num_pages + 1})")
		m = m[page]  # select page
		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
		for i in m:
			embed.add_field(name="Map", value=''.join([v + '\n' for v in i]))
	except Exception as e:
		if type(e) == IndexError:
			embed = None
			error_message = f"Page {page + 1} does not exists"
		elif type(e) == ValueError:
			logging.info(f"Upgrade listing argument <{arg[3]}> is invalid.")
			error_message = f"Value {arg[3]} is not understood"
		else:
			logging.info(f"Exception {type(e)}", e)
	await context.send(embed=embed)

@list.command()
async def ships(context, *args):
	if context.guild is not None:
		server_emojis = context.guild.emojis
	else:
		server_emojis = []
	message_success = False
	
	# parsing search parameters
	logging.info("starting parameters parsing")
	search_param = args
	s = ship_list_regex.findall(''.join([str(i) + ' ' for i in search_param])[:-1])
	
	tier = ''.join([i[2] for i in s])
	key = [i[7] for i in s if len(i[7]) > 1]
	page = [i[6] for i in s if len(i[6]) > 0]
	embed_title = "Search result for: "

	try:
		page = int(page[0]) - 1
	except:
		page = 0

	if len(tier) > 0:
		if tier in roman_numeral:
			tier = roman_numeral[tier]
		tier = f't{tier}'
		key += [tier]
	key = [i for i in key if not 'page' in i]
	embed_title += f"{''.join([i.title() + ' ' for i in key])}"
	# look up
	result = []
	for s in ship_list:
		try:
			tags = [i.lower() for i in ship_list[s]['tags']]
			if np.all([k.lower() in tags for k in key]):
				result += [s]
		except:
			pass
	logging.info("parsing complete")
	logging.info("compiling message")
	m = []
	if len(result) > 0:
		# return some infomration about the ships of the requested tags
		for ship in result:
			output = get_ship_data(ship_list[ship]['name'])
			if output is None:
				continue
			name, _, _, ship_type, tier, _, _, _, is_prem, _, _, _, _, _, _, _ = output
			tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
			type_icon = f':{ship_type.lower()}:' if ship_type != "AirCarrier" else f':carrier:'
			if is_prem:
				type_icon = type_icon[:-1] + '_premium:'
			# find the server emoji id for this emoji id
			if len(server_emojis) == 0:
				type_icon = ""
			else:
				if type_icon[1:-1] in [i.name for i in server_emojis]:
					for i in server_emojis:
						if type_icon[1:-1] == i.name:
							type_icon = str(i)
							break
				else:
					type_icon = ""
			# no emoji, returns ship hull classification value
			if len(type_icon) == 0:
				type_icon = "[" + hull_classification_converter[ship_type] + "]"
			# m += [f"**{tier_string:<6} {type_icon}** {name}"]
			m += [[tier, tier_string, type_icon, name]]

		num_items = len(m)
		m.sort(key=lambda x: (x[0], x[2], x[-1]))
		m_mod = []
		for i, v in enumerate(m):
			if v[0] != m[i - 1][0]:
				m_mod += [[-1, '', '', '']]
			m_mod += [v]
		m = m_mod
			
		m = [f"**{tier_string:<6} {type_icon}** {name}" if tier != -1 else "-------------" for tier, tier_string, type_icon, name in m]
		
		items_per_page = 30
		num_pages = (len(m) // items_per_page)
		m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

		embed = discord.Embed(title=embed_title + f"({page + 1}/{num_pages + 1})")
		m = m[page]  # select page
		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
		embed.set_footer(text=f"{num_items} ships found\nTo get ship build, use [{command_prefix} build [ship_name]]")
		for i in m:
			embed.add_field(name="(Tier) Ship", value=''.join([v + '\n' for v in i]))
	else:
		embed = discord.Embed(title=embed_title, description="")
		embed.description = "**No ships found**"
	await context.send(embed=embed)


@mackbot.command()
async def upgrade(context, *arg):
	# get information on requested upgrade
	upgrade_found = False
	# message parse
	upgrade = ''.join([i + ' ' for i in arg])[:-1]  # message_string[message_string.rfind('-')+1:]
	if len(arg) == 0:
		# argument is empty, send help message
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if embed is not None:
			await context.send(embed=embed)
	else:
		# user provided an argument

		search_func = None
		# getting appropriate search function
		try:
			# does user provide upgrade name?
			get_upgrade_data(upgrade)
			search_func = get_upgrade_data
			logging.info("user requested an upgrade name")
		except:
			# does user provide ship name?
			get_legendary_upgrade_by_ship_name(upgrade)
			search_func = get_legendary_upgrade_by_ship_name
			logging.info("user requested an legendary upgrade")

		try:
			logging.info(f'sending message for upgrade <{upgrade}>')
			profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction = search_func(
				upgrade)

			embed_title = 'Ship Upgrade'
			if is_special == 'Unique':
				embed_title = "Legendary Ship Upgrade"
			elif is_special == 'Coal':
				embed_title = "Coal Ship Upgrade"

			embed = discord.Embed(title=embed_title, description="")
			embed.set_thumbnail(url=image)
			# get server emoji
			if context.guild is not None:
				server_emojis = context.guild.emojis
			else:
				server_emojis = []

			if len(name) > 0:
				embed.description += f"**{name}**\n"
			else:
				logging.info("name is empty")
			embed.description += f"**Slot {slot}**\n"
			if len(description) > 0:
				embed.add_field(name='Description', value=description, inline=False)
			else:
				logging.info("description field empty")
			if len(profile) > 0:
				embed.add_field(name='Effect',
								value=''.join([profile[detail]['description'] + '\n' for detail in profile]),
								inline=False)
			else:
				logging.info("effect field empty")
			if not is_special == 'Unique':
				if len(type_restriction) > 0:
					# find the server emoji id for this emoji id
					if len(server_emojis) == 0:
						m = ''.join([i.title() + ', ' for i in sorted(type_restriction)])[:-2]
					else:
						m = ''
						for t in type_restriction:
							t = 'carrier' if t == 'Aircraft Carrier' else t
							for e in server_emojis:
								if t.lower() == e.name:
									m += str(e) + ' '
									break
						else:
							type_icon = ""
				else:
					m = "All types"
				embed.add_field(name="Ship Type", value=m)

				if len(tier_restriction) > 0:
					m = ''.join([str(i) + ', ' for i in sorted(tier_restriction)])[:-2]
				else:
					m = "All tiers"
				embed.add_field(name="Tier", value=m)

				if len(nation_restriction) > 0:
					m = ''.join([i + ', ' for i in sorted(nation_restriction)])[:-2]
				else:
					m = 'All nations'
				embed.add_field(name="Nation", value=m)

				if len(ship_restriction) > 0:
					m = ''.join([i + ', ' for i in sorted(ship_restriction)])[:-2]
					if len(m) > 0:
						ship_restrict_title = {
							'': "Also Found On",
							'Coal': "Also Found On",
						}[is_special]
						embed.add_field(name=ship_restrict_title, value=m)
					else:
						logging.warning('Ships field is empty')
			if len(special_restriction) > 0:
				m = special_restriction
				if len(m) > 0:
					embed.add_field(name="Additonal Requirements", value=m)
				else:
					logging.log("Additional requirements field empty")
			if price_credit > 0 and len(is_special) == 0:
				embed.add_field(name='Price (Credit)', value=f'{price_credit:,}')
			await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}", e)
			# error, ship name not understood
			upgrade_name_list = [upgrade_list[i]['name'] for i in upgrade_list]
			closest_match = difflib.get_close_matches(upgrade, upgrade_name_list)
			closest_match_string = ""
			if len(closest_match) > 0:
				closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

			await context.send(f"Upgrade **{upgrade}** is not understood." + closest_match_string)

@mackbot.command()
async def commander(context, *arg):
	# get information on requested commander
	# message parse
	cmdr = ''.join([i + ' ' for i in arg])[:-1]  # message_string[message_string.rfind('-')+1:]
	if len(arg) == 0:
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if embed is not None:
			await context.send(embed=embed)
	else:
		try:
			async with context.typing():
				logging.info(f'sending message for commander <{cmdr}>')

				output = get_commander_data(cmdr)
				if output is None:
					raise NameError("NoCommanderFound")
				name, icon, nation, cmdr_id = output
				embed = discord.Embed(title="Commander")
				embed.set_thumbnail(url=icon)
				embed.add_field(name='Name', value=name, inline=False)
				embed.add_field(name='Nation', value=nation_dictionary[nation], inline=False)

				cmdr_data = None
				for i in game_data:
					if game_data[i]['typeinfo']['type'] == 'Crew':
						if cmdr_id == str(game_data[i]['id']):
							cmdr_data = game_data[i]

				'''
				skill_bonus_string = ''

				for c in cmdr_data['Skills']:
					skill = cmdr_data['Skills'][c].copy()
					if skill['isEpic']:
						skill_name, _, skill_type, _, _, _ = get_skill_data_by_grid(skill['column'], skill['tier'])
						skill_bonus_string += f'**{skill_name}** ({skill_type}, Tier {skill["tier"]}):\n'
						for v in ['column', 'skillType', 'tier', 'isEpic', 'turnOffOnRetraining']:
							del skill[v]
						if c in ['SurvivalModifier', 'MainGunsRotationModifier']:
							for descriptor in skill:
								skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] > 0 else ''}{skill[descriptor]:0.0f}\n"
								if c == 'MainGunsRotationModifier':
									skill_bonus_string += ' °/sec.'
						else:
							for descriptor in skill:
								if c == 'TorpedoAcceleratorModifier':
									if descriptor in ['planeTorpedoSpeedBonus', 'torpedoSpeedBonus']:
										skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] > 0 else ''}{skill[descriptor]:0.0f} kts.\n"
									else:
										skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] - 1 > 0 else ''}{int(round((skill[descriptor] - 1) * 100))}%\n"
								else:
									if abs(skill[descriptor] - 1) > 0:
										skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] - 1 > 0 else ''}{int(round((skill[descriptor] - 1) * 100))}%\n"
						skill_bonus_string += '\n'
				
				if len(skill_bonus_string) > 0:
					embed.add_field(name='Skill Bonuses', value=skill_bonus_string, inline=False)
					embed.set_footer(text="For default skill bonuses, use [mackbot skill [skill name]]")
				else:
					embed.add_field(name='Skill Bonuses', value="None", inline=False)
				'''
			await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}: ", e)
			# error, ship name not understood
			cmdr_name_list = [cmdr_list[i]['first_names'] for i in cmdr_list]
			closest_match = difflib.get_close_matches(cmdr, cmdr_name_list)
			closest_match_string = ""
			if len(closest_match) > 0:
				closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

			await context.send(f"Commander **{cmdr}** is not understood.")

@mackbot.command()
async def map(context, *arg):
	# get information on requested map
	# message parse
	map = ''.join([i + ' ' for i in arg])[:-1]  # message_string[message_string.rfind('-')+1:]
	if len(arg) == 0:
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if embed is not None:
			await context.send(embed=embed)
	else:
		try:
			async with context.typing():
				logging.info(f'sending message for map <{map}>')
				description, image, id, name = get_map_data(map)
				embed = discord.Embed(title="Map")
				embed.set_image(url=image)
				embed.add_field(name='Name', value=name)
				embed.add_field(name='Description', value=description)

			await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}: ", e)
			# error, ship name not understood
			map_name_list = [map_list[i]['name'] for i in map_list]
			closest_match = difflib.get_close_matches(map, map_name_list)
			closest_match_string = ""
			if len(closest_match) > 0:
				closest_match_string = f'\nDid you meant **{closest_match[0]}**?'

			await context.send(f"Map **{map}** is not understood.")

@mackbot.command()
async def doubloons(context, *arg):
	# get information on requested flag
	if len(arg) == 0:
		# argument is empty, send help message
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg[1])
		if embed is not None:
			await context.send(embed=embed)
	else:
		# user provided an argument
		try:
			# message parse
			doub = arg[0]  # message_string[message_string.rfind('-')+1:]
			if len(arg) == 2:
				# check reverse conversion
				# dollars to doubloons
				if arg[1].lower() in ['dollars', '$']:
					dollar = float(doub)

					def dollar_formula(x):
						return x * 250

					embed = discord.Embed(title="Doubloon Conversion (Dollars -> Doubloons)")
					embed.add_field(name=f"Requested Dollars", value=f"{dollar:0.2f}$")
					embed.add_field(name=f"Doubloons", value=f"Approx. {dollar_formula(dollar):0.0f} Doubloons")

			else:
				# doubloon to dollars
				doub = int(doub)
				value_exceed = not (500 <= doub <= 100000)

				def doub_formula(x):
					return x / 250

				embed = discord.Embed(title="Doubloon Conversion (Doubloons -> Dollars)")
				embed.add_field(name=f"Requested Doubloons", value=f"{doub} Doubloons")
				embed.add_field(name=f"Price: ", value=f"{doub_formula(doub):0.2f}$")
				if value_exceed:
					embed.set_footer(text=":warning: You are unable to buy the requested doubloons")

			await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}", e)
			await context.send(f"Value **{doub}** is not a number (or an internal error has occured).")

@mackbot.command()
async def code(context, arg):
	if len(arg) == 0:
		# argument is empty, send help message
		embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + arg)
		if embed is not None:
			await context.send(embed=embed)
	else:
		s = "https://na.wargaming.net/shop/redeem/?bonus_mode=" + arg.upper()
		await context.send(s)

# async def on_message(self, message):
	# 
	# arg = [i for i in message.content.split(cmd_sep) if len(i) > 0]
	# if message.author != self.user:
		# if message.content.startswith("<@!" + str(self.user.id) + ">"):
			# if len(arg) == 1:
				# # no additional arguments, send help
				# logging.info(f"User {message.author} requested my help.")
				# embed = self.help_message(command_prefix + cmd_sep + "help" + cmd_sep + "help")
				# if not embed is None:
					# logging.info(f"sending help message")
					# await context.send("はい、サラはここに。", embed=embed)
			# else:
				# # with arguments, change arg[0] and perform its normal task
				# arg[0] = command_prefix
				
		# if arg[0].lower() + cmd_sep == command_prefix + cmd_sep:  # message starts with mackbot
			# if DEBUG_IS_MAINTANCE and message.author != self.user and not message.author.name == 'mackwafang':
				# # maintanance message
				# await context.send(
					# self.user.display_name + " is under maintanance. Please wait until maintanance is over. Or contact Mack if he ~~fucks up~~ did an oopsie.")
				# return
			# request_type = arg[1:]
			# logging.info(
				# f'User <{message.author}> in <{message.guild}, {message.context}> requested command "<{request_type}>"')

			# if hasattr(self, arg[1]):
				# if command_list[arg[1]]:
					# await getattr(self, arg[1])(message, arg)
				# else:
					# await context.send("Command is temporary disabled.")
			# else:
				# # hidden command
				# if arg[1] == 'waifu':
					# await context.send("Mack's waifu: Saratoga\nhttps://kancolle.fandom.com/wiki/Saratoga")
				# if arg[1] == 'raifu':
					# await context.send("Mack's raifu: M1918 BAR https://en.gfwiki.com/wiki/M1918")
					

if __name__ == '__main__':
	# post processing for bot commands
	logging.info("Post-processing bot commands")
	with open("help_command_strings.json") as f:
		help_command_strings = json.load(f)
	for c in help_command_strings:
		try:
			command = mackbot.get_command(c)
			command.help = help_command_strings[c]['help']
			command.brief = help_command_strings[c]['brief']
			command.usage = help_command_strings[c]['usage']
			command.description = ''.join([i + '\n' for i in help_command_strings[c]['description']])
			
		except:
			pass
	del help_command_strings
	mackbot.run(bot_token)