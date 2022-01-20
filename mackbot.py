import wargaming, os, re, sys, pickle, json, discord, time, logging, difflib, traceback, asyncio
import pandas as pd

from pymongo import MongoClient
from enum import IntEnum, auto
from math import inf, ceil
from itertools import count
from random import randint
from discord.ext import commands
from datetime import date
from string import ascii_letters
from PIL import Image, ImageDraw, ImageFont
from pprint import pprint

class NoShipFound(Exception):
	pass

class NoBuildFound(Exception):
	pass

class NoUpgradeFound(Exception):
	pass

class NoSkillFound(Exception):
	pass

class BUILD_BATTLE_TYPE(IntEnum):
	CLAN = auto()
	CASUAL = auto()

class SHIP_TAG(IntEnum):
	SLOW_SPD = auto()
	FAST_SPD = auto()
	FAST_GUN = auto()
	STEALTH = auto()
	AA = auto()

class SHIP_BUILD_FETCH_FROM(IntEnum):
	LOCAL = auto()
	MONGO_DB = auto()


pd.set_option('display.max_columns', None)

with open("command_list.json") as f:
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
	'Aircraft Carrier': 'CV',
	'Battleship': 'BB',
	'Cruiser': 'C',
	'Submarine': 'SS'
}
# dictionary to convert user inputted ship name to non-ascii ship name
# TODO: find an automatic method, maybe
with open("data/ship_name_dict.json", 'r', encoding='utf-8') as f:
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
	'I': 1,
	'II': 2,
	'III': 3,
	'IV': 4,
	'V': 5,
	'VI': 6,
	'VII': 7,
	'VIII': 8,
	'IX': 9,
	'X': 10,
	':star:': 11,
}

# actual stuff
logging.info("Fetching WoWS Encyclopedia")
# load important stuff
if "sheets_credential" in os.environ:
	wg_token = os.environ['wg_token']
	bot_token = os.environ['bot_token']
	sheet_id = os.environ['sheet_id']
else:
	with open("config.json") as f:
		data = json.load(f)
		wg_token = data['wg_token']
		bot_token = data['bot_token']
		sheet_id = data['sheet_id']
		bot_invite_url = data['bot_invite_url']
		mongodb_host = data['mongodb_host']

# define bot stuff
cmd_sep = ' '
command_prefix = 'mackbot '
mackbot = commands.Bot(command_prefix=commands.when_mentioned_or(command_prefix))

# define database stuff
database_client = None
try:
	database_client = MongoClient(mongodb_host)
except ConnectionError:
	logging.warning("MongoDB cannot be connected.")

# get weegee's wows encyclopedia
WG = wargaming.WoWS(wg_token, region='na', language='en')
wows_encyclopedia = WG.encyclopedia
ship_types = wows_encyclopedia.info()['ship_types']
ship_types["Aircraft Carrier"] = "Aircraft Carrier"

icons_emoji = {
	"torp": "<:torp:917573129579151392>",
	"dd": "<:destroyer:917573129658859573>",
	"gun": "<:gun:917573129730146325>",
	"bb_prem": "<:battleship_premium:917573129801449563>",
	"plane_torp": "<:plane_torpedo:917573129847590993>",
	"ss_prem": "<:submarine_premium:917573129851764776>",
	"ss": "<:submarine:917573129876955147>",
	"bb": "<:battleship:917573129876959232>",
	"c": "<:cruiser:917573129885323374>",
	"cv": "<:carrier:917573129931477053>",
	"dd_prem": "<:destroyer_premium:917573129944059965>",
	"plane_rocket": "<:plane_projectile:917573129956638750>",
	"c_prem": "<:cruiser_premium:917573129965027398>",
	"cv_prem": "<:carrier_premium:917573130019557416>",
	"plane_bomb": "<:plane_bomb:917573130023759893>",
	"penetration": "<:penetration:917583397122084864>",
	"ap": "<:ap:917585790765252608>",
	"he": "<:he:917585790773653536>",
	"sap": "<:sap:917585790811402270>",
	"reload": "<:reload:917585790815584326>",
	"range": "<:range:917589573415088178>",
	"aa": "<:aa:917590394806599780>",
	"plane": "<:plane:917601379235815524>",
	"concealment": "<:concealment:917605435278782474>",
}


game_data = {}
ship_list = {}
ship_info = {}
skill_list = {}
module_list = {}
upgrade_list = {}
camo_list = {}
cmdr_list = {}
flag_list = {}
legendary_upgrades = {}
upgrade_abbr_list = {}
ship_build = {}
ship_build_competitive = None
ship_build_casual = None

build_battle_type = {
	BUILD_BATTLE_TYPE.CLAN: "competitive",
	BUILD_BATTLE_TYPE.CASUAL: "casual",
}
build_battle_type_value = {
	"competitive": BUILD_BATTLE_TYPE.CLAN,
	"casual": BUILD_BATTLE_TYPE.CASUAL,
}


logging.info("Fetching Maps")
map_list = wows_encyclopedia.battlearenas()

AA_RATING_DESCRIPTOR = {
	"Non-Existence": [0, 1],
	"Very Weak": [1, 20],
	"Weak": [20, 40],
	"Moderate": [40, 50],
	"High": [50, 70],
	"Dangerous": [70, 90],
	"Very Dangerous": [90, inf],
}

EXCHANGE_RATE_DOUB_TO_DOLLAR = 250

ship_list_regex = re.compile('((tier )(\d{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|((page )(\d{1,2}))|(([aA]ircraft [cC]arrier[sS]?)|((\w|-)*))')
skill_list_regex = re.compile('((?:battleship|[bB]{2})|(?:carrier|[cC][vV])|(?:cruiser|[cC][aAlL]?)|(?:destroyer|[dD]{2})|(?:submarine|[sS]{2}))|page (\d{1,2})|tier (\d{1,2})')
equip_regex = re.compile('(slot (\d))|(tier ([0-9]{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|(page (\d{1,2}))|((defensive aa fire)|(main battery)|(aircraft carrier[sS]?)|(\w|-)*)')
ship_param_filter_regex = re.compile('((hull|health|hp)|(guns?|artiller(?:y|ies))|(secondar(?:y|ies))|(torp(?:s|edo)? bombers?)|(torp(?:s|edo(?:es)?)?)|((?:dive )?bombers?)|(rockets?|attackers?)|(speed)|(aa|anti-air)|(concealment|dectection)|(consumables?)|(upgrades?))*')
player_arg_filter_regex = re.compile('(solo|div2|div3)|(ship (.*))|(ships (.*))')

good_bot_messages = (
	'Thank you!',
	'Mackbot tattara kekkō ganbatta poii? Homete hometei!',
	':3',
	':heart:',
)

with open(os.path.join(".", "data", "hottakes.txt")) as f:
	hottake_strings = f.read().split('\n')

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

def hex_64bit(val):
	return hex((val + (1 << 64)) % (1 << 64))[2:]

def load_game_params():
	global game_data
	# creating GameParams json from GameParams.data
	logging.info(f"Loading GameParams")
	for file_count in count(0):
		try:
			with open(os.path.join(".", "data", f'GameParamsPruned_{file_count}.json')) as f:
				data = json.load(f)

			game_data.update(data)
			del data
		except FileNotFoundError:
			break

def load_skill_list():
	global skill_list
	# loading skills list
	logging.info("Fetching Skill List")
	try:
		with open(os.path.join("data", "skill_list.json")) as f:
			skill_list = json.load(f)

		# dictionary that stores skill abbreviation
		skill_name_abbr = {}
		for skill in skill_list:
			# generate abbreviation
			abbr_name = ''.join([i[0] for i in skill_list[skill]['name'].lower().split()])
			skill_list[skill]['abbr'] = abbr_name
			skill_list[skill]['id'] = skill
	except FileNotFoundError:
		logging.error("skill_list.json is not found")

def load_module_list():
	global module_list
	logging.info("Fetching Module List")
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
def find_game_data_item(item):
	return [i for i in game_data if item in i]

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

def load_cmdr_list():
	global cmdr_list
	logging.info("Fetching Commander List")
	cmdr_list = wows_encyclopedia.crews()

def load_ship_list():
	logging.info("Fetching Ship List")
	global ship_list
	ship_list_file_name = 'ship_list'
	ship_list_file_dir = os.path.join(".", "data", ship_list_file_name)

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
		print("Cache complete")
	del ship_list_file_dir, ship_list_file_name, ship_list['ships_updated_at']

def load_upgrade_list():
	logging.info("Fetching Camo, Flags and Modification List")
	if len(ship_list) == 0:
		logging.info("Ship list is empty.")
		load_ship_list()

	if len(game_data) == 0:
		logging.info("No game data")
		load_game_params()

	global camo_list, flag_list, upgrade_list, legendary_upgrades
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
				# obsolete upgrade
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
				upgrade_list[uid]['slot'] = int(upgrade['slot']) + 1
				upgrade_list[uid]['ship_restriction'] = [ship_list[str(game_data[s]['id'])]['name'] for s in upgrade['ships'] if s in game_data and str(game_data[s]['id']) in ship_list]
				if upgrade['type'] == 3:
					# add ship specific restriction if upgrade is unique
					ship_id = str(game_data[upgrade['ships'][0]]['id'])
					upgrade_list[uid]['ship_restriction'] = ship_list[ship_id]
				upgrade_list[uid]['type_restriction'] = ['Aircraft Carrier' if t == 'AirCarrier' else t for t in upgrade['shiptype']]
				upgrade_list[uid]['nation_restriction'] = [t for t in upgrade['nation']]
				upgrade_list[uid]['tier_restriction'] = [t for t in upgrade['shiplevel']]

				upgrade_list[uid]['tags'] += upgrade_list[uid]['type_restriction']
				upgrade_list[uid]['tags'] += upgrade_list[uid]['tier_restriction']

	legendary_upgrades = {u: upgrade_list[u] for u in upgrade_list if upgrade_list[u]['is_special'] == 'Unique'}

	logging.info('Removing obsolete upgrades')
	for i in obsolete_upgrade:
		del upgrade_list[i]

	# changes to ship_list's ship upgrade structure to index slots,
	for sid in ship_list:
		ship = ship_list[sid]
		ship_upgrades = ship['upgrades']  # get a copy of ship's possible upgrades
		ship['upgrades'] = dict((i, []) for i in range(6))  # restructure
		for s_upgrade in ship_upgrades:
			# put ship upgrades in the appropiate slots
			upgrade = upgrade_list[str(s_upgrade)]
			ship['upgrades'][upgrade['slot'] - 1] += [str(s_upgrade)]

	create_upgrade_abbr()

def load_ship_params():
	global ship_info
	logging.info("Fetching Ship Parameters")
	if len(ship_list) == 0:
		logging.info("Ship list is empty.")
		load_ship_list()

	ship_param_file_name = 'ship_param'
	ship_param_file_dir = os.path.join(".", "data", ship_param_file_name)
	logging.info("	Checking cached ship_param file...")
	fetch_ship_params_from_wg = False
	if os.path.isfile(ship_param_file_dir):
		# check ship_params exists
		logging.info("	File found. Loading file")
		with open(ship_param_file_dir, 'rb') as f:
			ship_info = pickle.load(f)

		if ship_info['ships_updated_at'] != wows_encyclopedia.info()['ships_updated_at']:
			logging.info("	Ship params outdated, fetching new list")
			fetch_ship_params_from_wg = True
			ship_info = {}
	else:
		fetch_ship_params_from_wg = True

	if fetch_ship_params_from_wg:
		logging.info("Fetching new ship params from weegee")
		i = 0
		ship_info = {'ships_updated_at': wows_encyclopedia.info()['ships_updated_at']}
		for s in ship_list:
			ship = wows_encyclopedia.shipprofile(ship_id=int(s), language='en')
			ship_info[s] = ship[s]
			ship_info[s]['skip_bomber'] = None
			i += 1
			if (i % 50 == 0 and i > 0) or (i == len(ship_list)):
				logging.info(f"{i}/{len(ship_list)} ships found")
		logging.info("Done")
		logging.info("Creating ship_params cache")
		with open(ship_param_file_dir, 'wb') as f:
			pickle.dump(ship_info, f)
		logging.info("ship_params cache created")

def update_ship_modules():
	logging.info("Generating information about modules")
	if len(game_data) == 0:
		logging.info("Game data is empty.")
		load_game_params()
	if len(ship_list) == 0:
		logging.info("Ship list is empty.")
		load_ship_list()
		load_ship_params()
	if len(module_list) == 0:
		logging.info("Module list is empty.")
		load_module_list()

	ship_count = 0
	for s in ship_list:
		ship = ship_list[s]
		ship_count += 1
		if (ship_count % 50 == 0 and ship_count > 0) or (ship_count == len(ship_list)):
			logging.info(f"	{ship_count}/{len(ship_list)} ships")
		try:
			module_full_id_str = find_game_data_item(ship['ship_id_str'])[0]
			module_data = game_data[module_full_id_str]

			# grab consumables
			ship_list[s]['consumables'] = module_data['ShipAbilities'].copy()

			ship_upgrade_info = module_data['ShipUpgradeInfo']  # get upgradable modules

			# get credit and xp cost for ship research
			ship_list[s]['price_credit'] = ship_upgrade_info['costCR']
			ship_list[s]['price_xp'] = ship_upgrade_info['costXP']

			# is this a test bote?
			ship_list[s]['is_test_ship'] = module_data['group'] == 'demoWithoutStats'

			for _info in ship_upgrade_info:  # for each warship modules (e.g. hull, guns, fire-control)
				if type(ship_upgrade_info[_info]) == dict:  # if there are data

					try:
						if ship_upgrade_info[_info]['ucType'] != "_SkipBomber":
							module_id = find_module_by_tag(_info)
						else:
							module = module_data[ship_upgrade_info[_info]['components']['skipBomber'][0]]['planeType']
							module_id = str(game_data[module]['id'])
							del module
					except IndexError as e:
						# we did an oopsie
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Hull':
						# get secondary information
						if len(ship_upgrade_info[_info]['components']['atba']) > 0:
							module_list[module_id]['profile']['atba'] = {
								'hull': ship_upgrade_info[_info]['components']['atba'][0][0],
							}

							atba = ship_upgrade_info[_info]['components']['atba'][0]
							atba = module_data[atba]
							atba_guns = {'turret': {}}
							for t in [i for i in atba if 'HP' in i]:
								# gather all known secondary turrets
								turret = atba[t]
								if turret['name'] in atba_guns['turret']:
									atba_guns['turret'][turret['name']] += [turret]
								else:
									atba_guns['turret'][turret['name']] = [turret]
							else:
								# compile the secondary guns data
								for t in atba_guns['turret']:
									turret_data = atba_guns['turret'][t][0]
									atba_guns[t] = {
										'name': turret_data['name'],
										'shotDelay': turret_data['shotDelay'],
										'numBarrels': turret_data['numBarrels'],
										'caliber': turret_data['barrelDiameter'],
										'count': len(atba_guns['turret'][t]),
										'gun_dpm': 0,
										'max_damage_sap': 0,
										'burn_probability': 0,
									}
									for a in turret_data['ammoList']:
										ammo = game_data[a]
										atba_guns[t]['gun_dpm'] += ammo['alphaDamage'] * len(atba_guns['turret'][t]) * turret_data['numBarrels'] * (60 / turret_data['shotDelay'])
										atba_guns[t]['ammoType'] = ammo['ammoType']
										atba_guns[t]['max_damage'] = ammo['alphaDamage']
										if ammo['ammoType'] == 'HE':
											atba_guns[t]['burn_probability'] = ammo['burnProb']
											atba_guns[t]['pen'] = int(ammo['alphaPiercingHE'])
										if ammo['ammoType'] == 'CS':
											atba_guns[t]['pen'] = int(ammo['alphaPiercingCS'])
							del atba_guns['turret']
							module_list[module_id]['profile']['atba'] = atba_guns

						# getting aa information and calculate mbAA
						if len(ship_upgrade_info[_info]['components']['airDefense']) > 0:
							module_list[module_id]['profile']['anti_air'] = {
								'hull': ship_upgrade_info[_info]['components']['airDefense'][0][0],
								'near': {'damage': 0, 'hitChance': 0},
								'medium': {'damage': 0, 'hitChance': 0},
								'far': {'damage': 0, 'hitChance': 0},
								'flak': {'damage': 0, },
							}

							min_aa_range = inf
							max_aa_range = -inf

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
							aa_defense_far = []
							for item in ['atba', 'artillery']:
								try:
									aa_defense_far += [module_data[ship_upgrade_info[_info]['components'][item][0]]]
								except IndexError:
									pass

							for aa_component in aa_defense_far:
								for a in [a for a in aa_component if 'Far' in a]:
									aa_data = aa_component[a]
									if 'Bubbles' not in a:
										# long range passive AA
										module_list[module_id]['profile']['anti_air']['far']['damage'] += aa_data['areaDamage'] / aa_data['areaDamagePeriod']
										module_list[module_id]['profile']['anti_air']['far']['hitChance'] = aa_data['hitChance']
									else:
										# flaks
										module_list[module_id]['profile']['anti_air']['flak']['count'] = aa_data['innerBubbleCount'] + aa_data['outerBubbleCount']
										module_list[module_id]['profile']['anti_air']['flak']['damage'] += int(aa_data['bubbleDamage'] * (aa_data['bubbleDuration'] * 2 + 1))  # but why though
										module_list[module_id]['profile']['anti_air']['flak']['min_range'] = aa_data['minDistance']
										module_list[module_id]['profile']['anti_air']['flak']['max_range'] = aa_data['maxDistance']
										module_list[module_id]['profile']['anti_air']['flak']['hitChance'] = int(aa_data['hitChance'])

									min_aa_range = min(min_aa_range, aa_data['minDistance'])
									max_aa_range = max(max_aa_range, aa_data['maxDistance'])

							module_list[module_id]['profile']['anti_air']['min_range'] = min_aa_range
							module_list[module_id]['profile']['anti_air']['max_range'] = max_aa_range

							# calculate mbAA rating
							near_damage = module_list[module_id]['profile']['anti_air']['near']['damage'] * module_list[module_id]['profile']['anti_air']['near']['hitChance'] * 1.25
							mid_damage = module_list[module_id]['profile']['anti_air']['medium']['damage'] * module_list[module_id]['profile']['anti_air']['medium']['hitChance']
							far_damage = module_list[module_id]['profile']['anti_air']['far']['damage'] * module_list[module_id]['profile']['anti_air']['far']['hitChance']
							combined_aa_damage = near_damage + mid_damage + far_damage
							aa_rating = 0

							# aa rating scaling with range
							if combined_aa_damage > 0:
								aa_range_scaling = max(1, module_list[module_id]['profile']['anti_air']['max_range'] / 5800) # why 5800m? because thats the range of most ships' aa
								if aa_range_scaling > 1:
									aa_range_scaling = aa_range_scaling ** 3
								aa_rating += (combined_aa_damage / (int(ship['tier']) * 9)) * aa_range_scaling

							# aa rating scaling with flak
							if module_list[module_id]['profile']['anti_air']['flak']['damage'] > 0:
								flak_data = module_list[module_id]['profile']['anti_air']['flak']
								aa_rating += flak_data['count'] * flak_data['hitChance'] * 1.5

							# aa rating scaling with tier
							aa_rating = (combined_aa_damage / (int(ship['tier']) * 9))
							module_list[module_id]['profile']['anti_air']['rating'] = int(aa_rating * 10)

							if ship_info[s]['anti_aircraft'] is None:
								ship_info[s]['anti_aircraft'] = {}
							ship_info[s]['anti_aircraft'][module_list[module_id]['profile']['anti_air']['hull']] = module_list[module_id]['profile']['anti_air'].copy()

						# add airstrike information for ships with airstrikes (dutch cruisers, heavy cruisers, battleships)
						if 'airSupport' in ship_upgrade_info[_info]['components']:
							if len(ship_upgrade_info[_info]['components']['airSupport']) > 0:
								airsup_info = module_data[ship_upgrade_info[_info]['components']['airSupport'][0]]
								plane = game_data[airsup_info['planeName']]
								projectile = game_data[plane['bombName']]
								module_list[module_id]['profile']['airSupport'] = {
									'chargesNum': airsup_info['chargesNum'],
									'reloadTime': int(airsup_info['reloadTime']),
									'maxDist': airsup_info['maxDist'],
									'max_damage': int(projectile['alphaDamage']),
									'burn_probability': int(projectile['burnProb'] * 100),
									'bomb_pen': int(projectile['alphaPiercingHE']),
									'squad_size': int(plane['numPlanesInSquadron']),
									'payload': int(plane['attackCount']),
								}

						# depth charges armaments
						if 'depthCharges' in ship_upgrade_info[_info]['components']:
							if ship_upgrade_info[_info]['components']['depthCharges']:
								asw_info = module_data[ship_upgrade_info[_info]['components']['depthCharges'][0]]
								asw_data = {
									'chargesNum': asw_info['maxPacks'],
									'payload': 0,
									'max_damage': 0,
									'reloadTime': asw_info['reloadTime'],
								}
								# for each available launchers
								for asw_launcher in [i for i in asw_info.keys() if 'HP' in i]:
									asw_launcher_data = asw_info[asw_launcher]
									asw_data['payload'] += asw_launcher_data['numBombs']
									# look at depth charge data
									for depth_charge in asw_launcher_data['ammoList']:
										depth_charge_data = game_data[depth_charge]
										asw_data['max_damage'] = int(depth_charge_data['alphaDamage'])
									module_list[module_id]['profile']['asw'] = asw_data.copy()
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Artillery':  # guns, guns, guns!
						# get turret parameter
						gun = ship_upgrade_info[_info]['components']['artillery'][0]
						gun = [module_data[gun][turret] for turret in [g for g in module_data[gun] if 'HP' in g]]
						module_list[module_id]['profile']['artillery'] = {
							'shotDelay': 0,
							'caliber': 0,
							'numBarrels': 0,
							'max_damage_sap': 0,
							'burn_probability': 0,
							'pen_HE': 0,
							'pen_SAP': 0,
							'max_damage_HE': 0,
							'max_damage_AP': 0,
							'max_damage_SAP': 0,
							'gun_dpm': {'HE': 0, 'AP': 0, 'CS': 0},
						}
						for g in gun:  # for each turret
							turret_data = g
							# get caliber, reload, and number of guns per turret
							module_list[module_id]['profile']['artillery']['caliber'] = turret_data['barrelDiameter']
							module_list[module_id]['profile']['artillery']['shotDelay'] = turret_data['shotDelay']
							module_list[module_id]['profile']['artillery']['numBarrels'] = int(turret_data['numBarrels'])

							# get some information about the shells fired by the turret
							for a in turret_data['ammoList']:
								ammo = game_data[a]
								if ammo['ammoType'] == 'HE':
									module_list[module_id]['profile']['artillery']['burn_probability'] = int(ammo['burnProb'] * 100)
									module_list[module_id]['profile']['artillery']['pen_HE'] = int(ammo['alphaPiercingHE'])
									module_list[module_id]['profile']['artillery']['max_damage_HE'] = int(ammo['alphaDamage'])
									module_list[module_id]['profile']['artillery']['gun_dpm']['HE'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
								if ammo['ammoType'] == 'CS':  # SAP rounds
									module_list[module_id]['profile']['artillery']['pen_SAP'] = int(ammo['alphaPiercingCS'])
									module_list[module_id]['profile']['artillery']['max_damage_SAP'] = int(ammo['alphaDamage'])
									module_list[module_id]['profile']['artillery']['gun_dpm']['CS'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
								if ammo['ammoType'] == 'AP':
									module_list[module_id]['profile']['artillery']['max_damage_AP'] = int(ammo['alphaDamage'])
									module_list[module_id]['profile']['artillery']['gun_dpm']['AP'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])

							# check for belfast and belfast '43, for some reason
							if 'Belfast' in ship['name']:
								module_list[module_id]['profile']['artillery']['burn_probability'] = int(ship_info[str(s)]['artillery']['shells']['HE']['burn_probability'])
								module_list[module_id]['profile']['artillery']['pen_HE'] = 0

						continue

					if ship_upgrade_info[_info]['ucType'] == '_Torpedoes':  # torpedooes
						# get torps parameter
						gun = ship_upgrade_info[_info]['components']['torpedoes'][0]
						gun = module_data[gun]
						for g in [turret for turret in [g for g in gun if 'HP' in g]]:  # for each launcher
							turret_data = gun[g]
							projectile = game_data[turret_data['ammoList'][0]]
							module_list[module_id]['profile']['torpedoes'] = {
								'numBarrels': int(turret_data['numBarrels']),
								'shotDelay': turret_data['shotDelay'],
								'max_damage': int(projectile['alphaDamage'] / 3) + projectile['damage'],
								'torpedo_speed': projectile['speed'],
								'is_deep_water': projectile['isDeepWater'],
								'distance': projectile['maxDist'] * 30 / 1000,
							}
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Fighter':  # rawkets
						# get fighter parameter
						planes = ship_upgrade_info[_info]['components']['fighter'][0]
						planes = module_data[planes].values()
						for p in planes:
							plane = game_data[p]  # get rocket params
							projectile = game_data[plane['bombName']]
							module_list[module_id]['attack_size'] = plane['attackerSize']
							module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
							module_list[module_id]['speed_multiplier'] = plane['speedMax']  # squadron max speed, in multiplier
							module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
							module_list[module_id]['attack_cooldown'] = plane['attackCooldown']
							module_list[module_id]['profile'] = {
								"fighter": {
									'max_damage': int(projectile['alphaDamage']),
									'rocket_type': projectile['ammoType'],
									'burn_probability': int(projectile['burnProb'] * 100),
									'rocket_pen': int(projectile['alphaPiercingHE']),
									'max_health': int(plane['maxHealth']),
									'cruise_speed': int(plane['speedMoveWithBomb']),
									'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
									'payload': int(plane['attackCount']),
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
							module_list[module_id]['attack_size'] = plane['attackerSize']
							module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
							module_list[module_id]['speed_multiplier'] = plane['speedMax']  # squadron max speed, in multiplier
							module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
							module_list[module_id]['attack_cooldown'] = plane['attackCooldown']

							module_list[module_id]['profile'] = {
								"torpedo_bomber": {
									'cruise_speed': int(plane['speedMoveWithBomb']),
									'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
									'max_damage': int(projectile['alphaDamage'] / 3) + projectile['damage'],
									'max_health': int(plane['maxHealth']),
									'torpedo_speed': projectile['speed'],
									'is_deep_water': projectile['isDeepWater'],
									'distance': projectile['maxDist'] * 30 / 1000,
									'payload': int(plane['projectilesPerAttack']),
								}
							}
						continue

					if ship_upgrade_info[_info]['ucType'] == '_DiveBomber':
						# get bomber parameter
						planes = ship_upgrade_info[_info]['components']['diveBomber'][0]
						planes = module_data[planes].values()
						for p in planes:
							plane = game_data[p]
							projectile = game_data[plane['bombName']]
							module_list[module_id]['attack_size'] = int(plane['attackerSize'])
							module_list[module_id]['squad_size'] = int(plane['numPlanesInSquadron'])
							module_list[module_id]['speed_multiplier'] = plane['speedMax']  # squadron max speed, in multiplier
							module_list[module_id]['hangarSettings'] = plane['hangarSettings'].copy()
							module_list[module_id]['attack_cooldown'] = plane['attackCooldown']
							module_list[module_id]['bomb_type'] = projectile['ammoType']
							module_list[module_id]['bomb_pen'] = int(projectile['alphaPiercingHE'])
							module_list[module_id]['profile'] = {
								"dive_bomber": {
									'cruise_speed': int(plane['speedMoveWithBomb']),
									'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
									'max_damage': projectile['alphaDamage'],
									'burn_probability': projectile['burnProb'] * 100,
									'max_health': int(plane['maxHealth']),
									'payload': int(plane['attackCount']),
								}
							}
						continue

					# skip bomber
					if ship_upgrade_info[_info]['ucType'] == '_SkipBomber':
						# get bomber parameter
						planes = ship_upgrade_info[_info]['components']['skipBomber'][0]
						planes = module_data[planes].values()
						for p in planes:
							plane = game_data[p]
							projectile = game_data[plane['bombName']]
							ship_list[s]['modules']['skip_bomber'] += [plane['id']]
							if plane['id'] not in module_list:
								module_list[module_id] = {}
							# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
							module_list[module_id]['attack_size'] = int(plane['attackerSize'])
							module_list[module_id]['squad_size'] = int(plane['numPlanesInSquadron'])
							module_list[module_id]['speed_multiplier'] = plane['speedMax']  # squadron max speed, in multiplier
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
									'cruise_speed': int(plane['speedMoveWithBomb']),
									'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
									'max_damage': int(projectile['alphaDamage']),
									'burn_probability': projectile['burnProb'] * 100,
									'max_health': int(plane['maxHealth']),
									'payload': int(plane['attackCount']),
								}
							}
							ship_info[s]['skip_bomber'] = {'skip_bomber_id': module_id}
						continue
		except Exception as e:
			if not type(e) == KeyError:
				logging.error("at ship id " + s)
				logging.error("Ship " + s + " is not known to GameParams.data or accessing incorrect key in GameParams.json")
				logging.error("Update your GameParams JSON file(s)")
			traceback.print_exc()
	del ship_count

def create_upgrade_abbr():
	logging.info("Creating abbreviation for upgrades")
	global upgrade_abbr_list

	if len(upgrade_list) == 0:
		logging.info("Upgrade list is empty.")
		load_upgrade_list()

	for u in upgrade_list:
		upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(160), chr(32))  # replace weird 0-width character with a space
		upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(10), chr(32))  # replace random ass newline character with a space
		key = ''.join([i[0] for i in upgrade_list[u]['name'].split()]).lower()
		if key in upgrade_abbr_list:  # if the abbreviation of this upgrade is in the list already
			key = ''.join([i[:2].title() for i in upgrade_list[u]['name'].split()]).lower()[:-1]  # create a new abbreviation by using the first 2 characters
		upgrade_abbr_list[key] = upgrade_list[u]['name'].lower()  # add this abbreviation


def extract_build_from_google_sheets(dest_build_file_dir, write_cache):
	global ship_build

	# extracting build from google sheets
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
		with open('cmd_sep.pickle', 'rb') as sep:
			creds = pickle.load(sep)

	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('cmd_sep.pickle', 'wb') as sep:
			pickle.dump(creds, sep)

	service = build('sheets', 'v4', credentials=creds)

	# Call the Sheets API
	sheet = service.spreadsheets()
	# fetch build
	result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range='ship_builds!B2:Z1000').execute()
	values = result.get('values', [])

	if not values:
		logging.warning('No ship build data found.')
		raise Error
	else:
		logging.info(f"Found {len(values)} ship builds")
		for row in values:
			build_name = row[1]
			ship_name = row[0]
			if ship_name.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside printable) ?
				ship_name = ship_name_to_ascii[ship_name.lower()]  # convert to the appropriate name

			raw_id = []
			try:
				ship = get_ship_data(ship_name)
			except NoShipFound:
				logging.warning(f'Ship {ship_name} is not found')
				continue
			raw_id.append(ship['ship_id'])
			raw_upgrades = (i for i in row[2:8] if len(i) > 0)
			upgrades = []
			for u in raw_upgrades:
				try:
					upgrade_data = get_upgrade_data(u)
					uid = upgrade_data['consumable_id']
					raw_id.append(uid)
					upgrades.append(uid)
				except Exception as e:
					if type(e) is NoUpgradeFound:
						logging.warning(f"Upgrade {u} in build for ship {ship['name']} is not found")
					else:
						logging.error("Other Exception found")
					pass
			upgrades = tuple(upgrades)

			raw_skills = (i for i in row[8:-2] if len(i) > 0)
			skills = []
			skill_pts = 0
			for s in raw_skills:
				try:
					skill_data = get_skill_data(hull_classification_converter[ship['type']].lower(), s)
					sid = skill_data['id']
					skill_pts += skill_data['y']
					raw_id.append(int(sid))
					skills.append(sid)
				except Exception as e:
					if type(e) is NoSkillFound:
						logging.warning(f"Skill {s} in build for ship {ship['name']} is not found")
					else:
						logging.error("Other Exception found")
					pass
			if skill_pts > 21:
				logging.warning(f"Build for ship {ship['name']} exceeds 21 points!")
			skills = tuple(skills)
			cmdr = row[-1]

			build_id = hex_64bit(hash(tuple(raw_id)))
			if build_id not in ship_build:
				ship_build[build_id] = {"name": build_name, "ship": ship_name, "upgrades": upgrades, "skills": skills, "cmdr": cmdr}
			else:
				logging.error(f"build for ship {ship_name} with id {build_id} collides with build of ship {ship_name}")

		if len(ship_build) > 0 and write_cache:
			with open(dest_build_file_dir, 'w') as f:
				# file_check_sum = hex_64bit(hash(tuple(ship_build.keys())))
				# ship_build['checksum'] = file_check_sum

				logging.info("Creating ship build cache")
				json.dump(ship_build, f)
		logging.info("Ship build data fetching done")

def load_ship_builds():
	if database_client is None:
		# database connection successful, we don't need to fetch from local cache
		return None

	logging.info('Fetching ship build file...')
	global ship_build, ship_build_competitive, ship_build_casual
	extract_from_web_failed = False
	ship_build_file_dir = os.path.join("data", "ship_builds.json")
	build_extract_from_cache = os.path.isfile(ship_build_file_dir)

	if len(ship_list) == 0:
		logging.info("Ship list is empty.")
		load_ship_list()

	if len(upgrade_list) == 0:
		logging.info("Upgrade list is empty.")
		load_upgrade_list()

	if len(skill_list) == 0:
		logging.info("Skill list is empty.")
		load_skill_list()


	ship_build = {}
	# fetch ship builds and additional upgrade information
	if command_list['build']:
		if not build_extract_from_cache:
			# no build file found, retrieve from google sheets
			try:
				extract_build_from_google_sheets(ship_build_file_dir, True)
			except:
				extract_from_web_failed = True

		if build_extract_from_cache or extract_from_web_failed:
			# local cache is found, open from local cache
			with open(ship_build_file_dir) as f:
				ship_build = json.load(f)


def create_ship_build_images(build_name, build_ship_name, build_skills, build_upgrades, build_cmdr):

	# create dictionary for upgrade gamedata index to image name
	image_file_dict = {}
	image_folder_dir = os.path.join("data", "modernization_icons")
	for file in os.listdir(image_folder_dir):
		image_file = os.path.join(image_folder_dir, file)
		upgrade_index = file.split("_")[2] # get index
		image_file_dict[upgrade_index] = image_file

	font = ImageFont.truetype("./arialbd.ttf", encoding='unic', size=20)

	# create build image
	image_size = (400, 400)

	ship = get_ship_data(build_ship_name)

	# get ship type image
	ship_type_image_filename = ""
	if ship['type'] == 'AirCarrier':
		ship_type_image_filename = 'carrier'
	else:
		ship_type_image_filename = ship['type'].lower()
	if ship['is_premium']:
		ship_type_image_filename += "_premium"
	ship_type_image_filename += '.png'

	ship_type_image_dir = os.path.join("data", "icons", ship_type_image_filename)
	ship_tier_string = list(roman_numeral.keys())[ship['tier'] - 1]

	image = Image.new("RGBA", image_size, (0, 0, 0, 255)) # initialize new image
	draw = ImageDraw.Draw(image) # get drawing context

	# draw ship name and ship type
	with Image.open(ship_type_image_dir).convert("RGBA") as ship_type_image:
		ship_type_image = ship_type_image.resize((ship_type_image.width * 2, ship_type_image.height * 2), Image.NEAREST)
		image.paste(ship_type_image, (0, 0), ship_type_image)
	draw.text((56, 27), f"{ship_tier_string} {ship['name']}", fill=(255, 255, 255, 255), font=font, anchor='lm') # add ship name
	draw.text((image.width - 8, 27), f"{build_name.title()} build", fill=(255, 255, 255, 255), font=font, anchor='rm') # add build name

	# get skills from this ship's tree
	skill_list_filtererd_by_ship_type = {k: v for k, v in skill_list.items() if v['tree'] == ship['type']}
	# draw skills
	for skill_id in skill_list_filtererd_by_ship_type:
		skill = skill_list_filtererd_by_ship_type[skill_id]
		skill_image_filename = os.path.join("data", "cmdr_skills_images", skill['image'] + ".png")
		if os.path.isfile(skill_image_filename):
			with Image.open(skill_image_filename).convert("RGBA") as skill_image:

				coord = (4 + (skill['x'] * 64), 50 + (skill['y'] * 64))
				green = Image.new("RGBA", (60, 60), (0, 255, 0, 255))

				if skill_id in build_skills:
					# indicate user should take this skill
					skill_image = Image.composite(green, skill_image, skill_image)
					# add number to indicate order should user take this skill
					skill_acquired_order = build_skills.index(skill_id) + 1
					image.paste(skill_image, coord, skill_image)
					draw.text((coord[0], coord[1] + 40), str(skill_acquired_order), fill=(255, 255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0, 255))
				else:
					# fade out unneeded skills
					skill_image = Image.blend(skill_image, Image.new("RGBA", skill_image.size, (0, 0, 0, 0)), 0.5)
					image.paste(skill_image, coord, skill_image)

	# draw upgrades
	for slot, u in enumerate(build_upgrades):
		if u != -1:
			# specific upgrade
			upgrade_index = [game_data[i]['index'] for i in game_data if game_data[i]['id'] == u][0]
			upgrade_image_dir = image_file_dict[upgrade_index]
		else:
			# any upgrade
			upgrade_image_dir = image_file_dict['any.png']

		with Image.open(upgrade_image_dir).convert("RGBA") as upgrade_image:
			coord = (4 + (slot * 64), image.height - 60)
			image.paste(upgrade_image, coord, upgrade_image)

	return image

def create_ship_tags():
	logging.info("Generating ship search tags")
	if len(ship_list) == 0:
		logging.info("Ship list is empty.")
		load_ship_list()

	SHIP_TAG_LIST = (
		'',
		'slow',
		'fast',
		'fast-firing',
		'stealth',
		'anti-air',
	)
	ship_tags = {
		SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD]: {
			'min_threshold': 0,
			'max_threshold': 30,
			'description': f"Any ships in this category have a **base speed** of **30 knots or slower**",
		},
		SHIP_TAG_LIST[SHIP_TAG.FAST_SPD]: {
			'min_threshold': 30,
			'max_threshold': 99,
			'description': "Any ships in this category have a **base speed** of **30 knots or faster**",
		},
		SHIP_TAG_LIST[SHIP_TAG.FAST_GUN]: {
			'min_threshold': 0,
			'max_threshold': 6,
			'description': "Any ships in this category have main battery guns that **reload** in **6 seconds or less**",
		},
		SHIP_TAG_LIST[SHIP_TAG.STEALTH]: {
			'min_air_spot_range': 4,
			'min_sea_spot_range': 6,
			'description': "Any ships in this category have a **base air detection range** of **4 km or less** or a **base sea detection range** of **6 km or less**",
		},
		SHIP_TAG_LIST[SHIP_TAG.AA]: {
			'min_aa_range': 5.8,
			'damage_threshold_multiplier': 75,
			'description': "Any ships in this category has **anti-air gun range** larger than **5.8 km** or the ship's **mbAA rating of at least 50**",
		},
	}

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
			if ship_speed <= ship_tags[SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD]]['max_threshold']:
				tags += [SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD]]
			if ship_speed >= ship_tags[SHIP_TAG_LIST[SHIP_TAG.FAST_SPD]]['min_threshold']:
				tags += [SHIP_TAG_LIST[SHIP_TAG.FAST_SPD]]
			concealment = ship_info[s]['concealment']
			# add tags based on detection range
			if concealment['detect_distance_by_plane'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG.STEALTH]]['min_air_spot_range'] or concealment['detect_distance_by_ship'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG.STEALTH]]['min_sea_spot_range']:
				tags += [SHIP_TAG_LIST[SHIP_TAG.STEALTH]]
			# add tags based on gun firerate
			try:
				# some ships have main battery guns
				fireRate = ship_info[s]['artillery']['shot_delay']
			except TypeError:
				# some dont *ahemCVsahem*
				fireRate = inf
			if fireRate <= ship_tags[SHIP_TAG_LIST[SHIP_TAG.FAST_GUN]]['max_threshold'] and not t == 'Aircraft Carrier':
				tags += [SHIP_TAG_LIST[SHIP_TAG.FAST_GUN], 'dakka']
			# add tags based on aa
			if ship_info[s]['anti_aircraft'] is not None:
				for hull in ship_info[s]['anti_aircraft']:
					if hull not in ['defense', 'slots']:
						aa_rating = ship_info[s]['anti_aircraft'][hull]['rating']
						aa_max_range = ship_info[s]['anti_aircraft'][hull]['max_range']
						if aa_rating > 50 or aa_max_range > ship_tags[SHIP_TAG_LIST[SHIP_TAG.AA]]['min_aa_range']:
							if SHIP_TAG_LIST[SHIP_TAG.AA] not in tags:
								tags += [SHIP_TAG_LIST[SHIP_TAG.AA]]

			tags += [nat, f't{tier}', t, t + 's', hull_class]
			ship_list[s]['tags'] = tags
			if prem:
				ship_list[s]['tags'] += ['premium']
		except Exception as e:
			if type(e) == KeyError:
				logging.warning(f"Ship Tags Generator: Ship {s} not found")
			else:
				logging.warning("%s %s at ship id %s" % (type(e), e, s))
				traceback.print_exc(type(e), e, None)

def get_ship_data(ship: str) -> dict:
	"""
		returns name, nation, images, ship type, tier of requested warship name along with recommended build.

		Arguments:
			ship : Ship name of build to be returned

		Returns:
			object: dict containing ship information
		
		raise InvalidShipName exception if name provided is incorrect
		or
		NoBuildFound exception if no build is found
	"""
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside printable ?
			ship = ship_name_to_ascii[ship.lower()]  # convert to the appropriate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			if ship.lower() == ship_name_in_dict.lower():  # find ship based on name
				ship_found = True
				break
		if ship_found:
			return ship_list[i]
		else:
			raise NoShipFound
	except Exception as e:
		raise e

def get_ship_builds_by_name(ship: str, fetch_from: SHIP_BUILD_FETCH_FROM) -> list:
	"""
	Returns a ship build given the ship name

	Args:
	    fetch_from: source of ship build
		ship: ship name

	Returns:
		object: list of builds for ship with name "ship"

	Raises:
		NoBuildFound exception
	"""
	if fetch_from is not SHIP_BUILD_FETCH_FROM.LOCAL:
		if database_client is None:
			fetch_from = SHIP_BUILD_FETCH_FROM.LOCAL

	try:
		if fetch_from is SHIP_BUILD_FETCH_FROM.LOCAL:
			result = [ship_build[b] for b in ship_build if ship_build[b]['ship'] == ship.lower()]
			if not result:
				raise NoBuildFound
			return result
		if fetch_from is SHIP_BUILD_FETCH_FROM.MONGO_DB:
			return list(database_client.mackbot_db.ship_build.find({"ship": ship.lower()}))
	except Exception as e:
		raise e

def get_ship_param(ship: str) -> dict:
	"""
		returns combat parameters of requested warship name

		Arguments:
			ship: ship name

		Returns:
			object: dictionary containing ship's combat parameter

		raise exceptions for dictionary
	"""
	try:
		if ship.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()]  # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			if ship.lower() == ship_name_in_dict.lower():  # find ship based on name
				if i in ship_info:
					return ship_info[i]
				else:
					raise NoShipFound
	except Exception as e:
		raise e

def get_legendary_upgrade_by_ship_name(ship: str) -> dict:
	"""
		returns information of a requested legendary warship upgrade

		Arguments:
			ship: Ship name

		Returns:
			object: dict
			profile: (dict) upgrade's bonuses
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
	# convert ship names with utf-8 chars to ascii
	if ship in ship_name_to_ascii:
		ship = ship_name_to_ascii[ship]
	for u in legendary_upgrades:
		upgrade = legendary_upgrades[u]
		if upgrade['ship_restriction']['name'].lower() == ship:
			return upgrade
	return None

def get_skill_data(tree: str, skill: str) -> dict:
	"""
		returns information of a requested commander skill

		Examples:
			get_skill_data("Battleship", "Fire Prevention Expert")
				- get data on the battleship's skill fire prevention expert

		Arguments:
			tree: (string) Which tree to extract data from
			skill: (string) Skill's full name

		Returns:
			object: tuple (name, tree, description, effect, x, y, category)

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
				for lookup_type in ['name', 'abbr']:
					if filtered_skill_list[f_s]['name'].lower() == skill:
						s = filtered_skill_list[f_s].copy()
						if s['tree'] == 'AirCarrier':
							s['tree'] = "Aircraft Carrier"
						return s #s['name'], s['tree'], s['description'], s['effect'], s['x'] + 1, s['y'] + 1, s['category']
			raise NoSkillFound

	except Exception as e:
		if skill == "*":
			return {
				'category': 'Any',
				'description': 'Any skill',
				'effect': '',
				'id': -1,
				'name': 'Any',
				'tree': 'Any',
				'x': -1,
				'y': -1,
			}
		# oops, probably not found
		logging.info(f"Exception {type(e)}: ", e)
		raise e

def get_upgrade_data(upgrade: str) -> dict:
	"""
		returns information of a requested warship upgrade

		Arguments:
			upgrade : Upgrade's full name or abbreviation

		Returns:
			object: dict (profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction,
			nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships)

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
		return upgrade_list[i]
	except Exception as e:
		if upgrade == '*':
			return {
				'additional_restriction': '',
				'consumable_id': -1,
				'description': 'Any',
				'image': '',
				'is_special': '',
				'local_image': '',
				'name': 'Any',
				'nation_restriction': [],
				'price_credit': 0,
				'price_gold': 0,
				'profile': {}
			}
		logging.info(f"Exception {type(e)}: ", e)
		raise e

def get_commander_data(cmdr: str) -> tuple:
	"""
		returns information of a requested warship upgrade

		Arguments:
			cmdr : Commander's full name

		Returns:
			object: tuple

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

def get_flag_data(flag: str) -> tuple:
	"""
		returns information of a requested warship upgrade

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

def get_map_data(map: str) -> tuple:
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

async def correct_user_misspell(context, command, *args):
	author = context.author
	def check(message):
		return author == message.author and message.content.lower() in ['y', 'yes']

	message = await mackbot.wait_for('message', timeout=10, check=check)
	try:
		await globals()[command](context, ' '.join(i for i in args))
	except Exception as e:
		pass

def get_ship_data_by_id(ship_id: int) -> dict:
	ship_data = {
		"name": "",
		"tier": -1,
		"nation": "",
		"type": "",
		"is_prem": False,
		"emoji": '',
	}
	try:
		ship_data['name'] = ship_list[str(ship_id)]['name']
		ship_data['tier'] = ship_list[str(ship_id)]['tier']
		ship_data['nation'] = ship_list[str(ship_id)]['nation']
		ship_data['type'] = ship_list[str(ship_id)]['type']
		ship_data['is_prem'] = ship_list[str(ship_id)]['is_premium']
	except KeyError:
		# some ships are not available in wg api
		data = game_data[[i for i in game_data if game_data[i]['id'] == ship_id][0]]
		ship_name = data['name']
		ship_name = ship_name.replace(str(data['index']), '')[1:]
		ship_name = ''.join(i for i in ship_name if i in ascii_letters or i == '_').split()
		ship_name = ''.join(ship_name)
		ship_name = ship_name.replace("_", " ")

		ship_data['name'] = ship_name + " (old)"
		ship_data['tier'] = data['level']
		ship_data['nation'] = data['navalFlag']
		ship_data['type'] = data['typeinfo']['species']
	ship_data['emoji'] = icons_emoji[hull_classification_converter[ship_data['type']].lower() + ('_prem' if ship_data['is_prem'] else '')]
	return ship_data

def escape_discord_format(s):
	return ''.join('\\'+i if i in ['*', '_'] else i for i in s)

# *** END OF NON-COMMAND METHODS ***
# *** START OF BOT COMMANDS METHODS ***

@mackbot.event
async def on_ready():
	await mackbot.change_presence(activity=discord.Game(command_prefix + cmd_sep + 'help'))
	logging.info("Logged on")

@mackbot.event
async def on_command(context):
	if context.author != mackbot.user:  # this prevent bot from responding to itself
		query = ''.join([i + ' ' for i in context.message.content.split()[1:]])
		from_server = context.guild if context.guild else "DM"
		logging.info("User {} via {} queried {}".format(context.author, from_server, query))

@mackbot.command()
async def whoami(context):
	async with context.typing():
		m = "I'm a bot made by mackwafang#2071 to help players with clan build. I also includes the WoWS Encyclopedia!"
	await context.send(m)

@mackbot.command()
async def goodbot(context):
	# good bot
	r = randint(0, len(good_bot_messages) - 1)
	logging.info(f"send reply message for goodbot")
	await context.send(good_bot_messages[r])  # block until message is sent

@mackbot.command()
async def feedback(context):
	logging.info("send feedback link")
	await context.send(f"Need to rage at mack because he ~~fucks up~~ did goofed on a feature? Submit a feedback form here!\nhttps://forms.gle/Lqm9bU5wbtNkpKSn7")

@mackbot.command()
async def build(context, *args):
	# get voted ship build
	# message parse
	ship_found = False
	if len(args) == 0:
		await context.send_help("ship")
	else:
		send_image_build = args[0] in ["--image", "-i"]
		if send_image_build:
			args = args[1:]
		usr_ship_name = ''.join([i + ' ' for i in args])[:-1]
		name, images = "", None
		try:
			async with context.typing():
				output = get_ship_data(usr_ship_name)
				name = output['name']
				nation = output['nation']
				images = output['images']
				ship_type = output['type']
				tier = output['tier']
				is_prem = output['is_premium']

				# find ship build
				builds = get_ship_builds_by_name(name, fetch_from=SHIP_BUILD_FETCH_FROM.MONGO_DB)
				user_selected_build_id = 0

				# get user selection for multiple ship builds
				if len(builds) > 1:
					embed = discord.Embed(title=f"Build for {name}", description='')
					embed.set_thumbnail(url=images['small'])

					embed.description = f"**Tier {list(roman_numeral.keys())[tier - 1]} {nation_dictionary[nation]} {ship_types[ship_type].title()}**"

					m = ""
					for i, bid in enumerate(builds):
						build_name = builds[i]['name']
						m += f"[{i + 1}] {build_name}\n"
					embed.add_field(name="mackbot found multiple builds for this ship", value=m, inline=False)

					embed.set_footer(text="Please enter the number you would like the build for.")
					await context.send(embed=embed)

					def get_user_selected_build_id(message):
						return context.author == message.author
					user_selected_build_id = await mackbot.wait_for('message', timeout=10, check=get_user_selected_build_id)
					user_selected_build_id = user_selected_build_id.content.split(' ')[0]
					try:
						user_selected_build_id = int(user_selected_build_id) - 1
					except ValueError:
						await context.send(f"Input {user_selected_build_id} is invalid")
						raise ValueError

				if not builds:
					raise NoBuildFound
				else:
					build = builds[user_selected_build_id]
					build_name = build['name']
					upgrades = build['upgrades']
					skills = build['skills']
					cmdr = build['cmdr']

				if not send_image_build:

					embed = discord.Embed(title=f"{build_name.title()} Build for {name}", description='')
					embed.set_thumbnail(url=images['small'])

					logging.info(f"returning build information for <{name}> in embeded format")

					tier_string = list(roman_numeral.keys())[tier - 1]

					embed.description += f'**Tier {tier_string} {"Premium" if is_prem else ""} {nation_dictionary[nation]} {ship_types[ship_type]}**\n'

					footer_message = ""
					error_value_found = False
					if len(upgrades) and len(skills) and len(cmdr):
						# suggested upgrades
						if len(upgrades) > 0:
							m = ""
							i = 1
							for upgrade in upgrades:
								upgrade_name = "[Missing]"
								if upgrade == -1:
									# any thing
									upgrade_name = "Any"
								else:
									try:  # ew, nested try/catch
										upgrade_name = upgrade_list[str(upgrade)]['name']
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
							for s in skills:
								skill_name = "[Missing]"
								try:  # ew, nested try/catch
									skill = skill_list[s]
									skill_name = skill['name']
									col = skill['x'] + 1
									tier = skill['y'] + 1
								except Exception as e:
									logging.info(f"Exception {type(e)}", e, f"in ship, listing skill {i}")
									error_value_found = True
									skill_name = skill + ":warning:"
								m += f'(Col. {col}, Row {tier}) **' + skill_name + '**\n'
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
						footer_message += "mackbot ship build should be used as a base for your builds. Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.\n"
						footer_message += f"For image variant of this message, use [mackbot build [-i/--image] {ship}]\n"
					else:
						m = "mackbot does not know any build for this ship :("
						embed.add_field(name=f'No known build', value=m, inline=False)
					error_footer_message = ""
					if error_value_found:
						error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact mackwafang#2071.\n"
					embed.set_footer(text=error_footer_message + footer_message)

			if not send_image_build:
				await context.send(embed=embed)
			else:
				# send image
				if database_client is None:
					build_image = builds[user_selected_build_id]['image']
				else:
					build_image = create_ship_build_images(build_name, name, skills, upgrades, cmdr)
				build_image.save("temp.png")
				await context.send(file=discord.File('temp.png'))
				await context.send("__Note: mackbot ship build should be used as a base for your builds. Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.__")

		except Exception as e:
			if type(e) == NoShipFound:
				# ship with specified name is not found, user might mistype ship name?
				ship_name_list = [ship_list[i]['name'].lower() for i in ship_list]
				closest_match = difflib.get_close_matches(usr_ship_name, ship_name_list)
				closest_match_string = closest_match[0].title()
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match_string}**?'
				embed = discord.Embed(title=f"Ship {ship} is not understood.\n", description=closest_match_string)
				embed.description += "\n\nType \"y\" or \"yes\" to confirm."
				embed.set_footer(text="Response expire in 10 seconds")
				await context.send(embed=embed)
				await correct_user_misspell(context, 'build', closest_match[0])
			elif type(e) == NoBuildFound:
				embed = discord.Embed(title=f"Build for {name}", description='')
				embed.set_thumbnail(url=images['small'])
				m = "mackbot does not know any build for this ship :("
				embed.add_field(name=f'No known build', value=m, inline=False)

				await context.send(embed=embed)
			else:
				logging.error(f"{type(e)}")
				traceback.print_exc()

@mackbot.command(help="")
async def ship(context, *args):
	"""
		Outputs an embeded message to the channel (or DM) that contains information about a queried warship
		
		Discord usage:
			mackbot ship [ship_name] (parameters)
				ship_name 		- name of requested warship
				(parameters)	- Optional. Must include pair of parenthesis when used.
								  Filters only specific warship parameters
								  Parameters may include, but not limited to: guns, secondary, torpedoes, hull
	"""

	# message parse
	if len(args) == 0:
		await context.send_help("ship")
	else:
		send_compact = args[0] in ['compact', '-c']
		if send_compact:
			args = args[1:]
		args = ' '.join(i for i in args)  # fuse back together to check filter
		has_filter = '(' in args and ')' in args  # find a better check
		param_filter = ''
		if has_filter:
			param_filter = args[args.find('(') + 1: args.rfind(')')]
			args = args[:args.find('(') - 1]
		args = args.split(' ')
		ship = ' '.join(i for i in args)  # grab ship name
		# if not param_filter:
		# 	ship = ship[:-1]

		try:
			if send_compact:
				ship_param = get_ship_param(ship)
				ship_data = get_ship_data(ship)
				await ship_compact(context, ship_data, ship_param)
			else:
				async with context.typing():
					ship_param = get_ship_param(ship)
					ship_data = get_ship_data(ship)
					if ship_data is None:
						raise NoShipFound

					name = ship_data['name']
					nation = ship_data['nation']
					images = ship_data['images']
					ship_type = ship_data['type']
					tier = ship_data['tier']
					consumables = ship_data['consumables']
					modules = ship_data['modules']
					upgrades = ship_data['upgrades']
					is_prem = ship_data['is_premium']
					is_test_ship = ship_data['is_test_ship']
					price_gold = ship_data['price_gold']
					price_credit = ship_data['price_credit']
					price_xp = ship_data['price_xp']
					logging.info(f"returning ship information for <{name}> in embeded format")
					ship_type = ship_types[ship_type]

					if ship_type == 'Cruiser':
						# reclassify cruisers to their correct classification based on the washington naval treaty

						# check for the highest main battery caliber found on this warship
						highest_caliber = sorted(modules['artillery'],
						                         key=lambda x: module_list[str(x)]['profile']['artillery']['caliber'],
						                         reverse=True)
						highest_caliber = [module_list[str(i)]['profile']['artillery']['caliber'] for i in highest_caliber][0] * 1000

						if highest_caliber <= 155:
							# if caliber less than or equal to 155mm
							ship_type = "Light Cruiser"
						elif highest_caliber <= 203:
							# if caliber between 155mm and up to 203mm
							ship_type = "Heavy Cruiser"
						else:
							ship_type = "Battlecruiser"
					test_ship_status_string = '[TEST SHIP] * ' if is_test_ship else ''
					embed = discord.Embed(title=f"{ship_type} {name} {test_ship_status_string}", description='')

					tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
					embed.description += f'**Tier {tier_string} {"Premium" if is_prem else ""} {nation_dictionary[nation]} {ship_type}**\n'
					embed.set_thumbnail(url=images['small'])

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
					upgrades_filter = 11

					ship_filter = 0b111111111111  # assuming no filter is provided, display all
					# grab filters
					if len(param_filter) > 0:
						ship_filter = 0  # filter is requested, disable all
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
						ship_filter |= is_filter_requested(13) << upgrades_filter

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
							if hull['planes_amount'] is not None and ship_type == "Aircraft Carrier":
								m += f"{hull['planes_amount']} Aircraft{'s' if hull['planes_amount'] > 1 else ''}\n"
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

								m += f"**Has {airsup_info['chargesNum']} charge(s)**\n"
								m += f"**Reload**: {str(airsup_reload_m) + 'm' if airsup_reload_m > 0 else ''} {str(airsup_reload_s) + 's' if airsup_reload_s > 0 else ''}\n"

								if ship_filter == 2 ** hull_filter:
									# detailed air support filter
									m += f"**Aircraft**: {airsup_info['payload']} bombs\n"
									if nation == 'netherlands':
										m += f"**Squadron**: {airsup_info['squad_size']} aircrafts\n"
										m += f"**HE Bomb**: :boom:{airsup_info['max_damage']} (:fire:{airsup_info['burn_probability']}%, Pen. {airsup_info['bomb_pen']}mm)\n"
									else:
										m += f"**Squadron**: 2 aircrafts\n"
										m += f"**Depth Charge**: :boom:{airsup_info['max_damage']}\n"
								m += '\n'

							embed.add_field(name="__**Air Support**__", value=m, inline=False)
						if 'asw' in module_list[str(h)]['profile']:
							# depth charges info
							m = ''
							for h in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name']):
								hull = module_list[str(h)]['profile']['hull']
								m += f"**{module_list[str(h)]['name']}**\n"
								asw_info = module_list[str(h)]['profile']['asw']

								asw_reload_m = int(asw_info['reloadTime'] // 60)
								asw_reload_s = int(asw_info['reloadTime'] % 60)

								m += f"**Has {asw_info['chargesNum']} charge(s)**\n"
								m += f"**Reload**: {str(asw_reload_m) + 'm' if asw_reload_m > 0 else ''} {str(asw_reload_s) + 's' if asw_reload_s > 0 else ''}\n"

								if ship_filter == 2 ** hull_filter:
									# detailed air support filter
									m += f"**Depth charges per salvo**: {asw_info['payload']} bombs\n"
									m += f"**Depth charge**: :boom: {asw_info['max_damage']}\n"

								m += '\n'
							embed.add_field(name="__**ASW**__", value=m, inline=False)

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
							m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')} ({guns['numBarrels']} barrel{'s' if guns['numBarrels'] > 1 else ''}):**\n"

							if guns['max_damage_HE']:
								m += f"**HE:** {guns['max_damage_HE']} (:fire: {guns['burn_probability']}%, {guns['gun_dpm']['HE']:,} DPM"
								if guns['pen_HE'] > 0:
									m += f", Pen {guns['pen_HE']} mm)\n"
								else:
									m += f")\n"
							if guns['max_damage_SAP'] > 0:
								m += f"**SAP:** {guns['max_damage_SAP']} (Pen {guns['pen_SAP']} mm, {guns['gun_dpm']['CS']:,} DPM)\n"
							if guns['max_damage_AP'] > 0:
								m += f"**AP:** {guns['max_damage_AP']} ({guns['gun_dpm']['AP']:,} DPM)\n"
							m += f"**Reload:** {guns['shotDelay']:0.1f}s\n"

							m += '\n'
						embed.add_field(name="__**Main Battery**__", value=m)

					# secondary armaments
					if ship_param['atbas'] is not None and is_filtered(atbas_filter):
						m = ""
						m += f"**Range:** {ship_param['atbas']['distance']} km\n"
						for hull in modules['hull']:
							atba = module_list[str(hull)]['profile']['atba']
							hull_name = module_list[str(hull)]['name']

							gun_dpm = int(sum([atba[t]['gun_dpm'] for t in atba]))
							gun_count = int(sum([atba[t]['count'] for t in atba]))

							m += f"**{hull_name}**\n"
							m += f"**{gun_count}** turret{'s' if gun_count > 1 else ''}\n"
							m += f'**DPM:** {gun_dpm:,}\n'

							if ship_filter == 2 ** atbas_filter:
								m += '\n'
								for t in atba:
									turret = atba[t]
									# detail secondary
									m += f"**{t} ({turret['numBarrels']} barrel{'s' if turret['numBarrels'] > 1 else ''})**\n"
									m += f"**{turret['count']}** turret{'s' if turret['count'] > 1 else ''}\n"
									m += f"**{'SAP' if turret['ammoType'] == 'CS' else turret['ammoType']}**: {int(turret['max_damage'])}"
									m += '('
									if turret['burn_probability'] > 0:
										m += f":fire:{turret['burn_probability'] * 100}%, "
									m += f"Pen. {turret['pen']}mm"
									m += ')\n'
									m += f"**Reload**: {turret['shotDelay']}s\n"
							if len(modules['hull']) > 1:
								m += '---------------------\n'

						embed.add_field(name="__**Secondary Battery**__", value=m)

					# anti air
					if len(modules['hull']) > 0 and is_filtered(aa_filter):
						m = ""

						if ship_filter == 2 ** aa_filter:
							# detailed aa
							for hull in modules['hull']:
								aa = module_list[str(hull)]['profile']['anti_air']
								m += f"**{name} ({aa['hull']})**\n"

								rating_descriptor = ""
								for d in AA_RATING_DESCRIPTOR:
									low, high = AA_RATING_DESCRIPTOR[d]
									if low <= aa['rating'] <= high:
										rating_descriptor = d
										break
								m += f"**AA Rating (vs. T{tier}):** {int(aa['rating'])} ({rating_descriptor})\n"

								m += f"**Range:** {aa['min_range'] / 1000:0.1f}-{aa['max_range'] / 1000:0.1f} km\n"
								# provide more AA detail
								flak = aa['flak']
								near = aa['near']
								medium = aa['medium']
								far = aa['far']
								if flak['damage'] > 0:
									m += f"**Flak:** {flak['min_range'] / 1000:0.1f}-{flak['max_range'] / 1000:0.1f} km, {flak['count']} burst{'s' if flak['count'] > 0 else ''}, {flak['damage']}:boom:\n"
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

							rating_descriptor = ""
							for d in AA_RATING_DESCRIPTOR:
								low, high = AA_RATING_DESCRIPTOR[d]
								if low <= average_rating <= high:
									rating_descriptor = d
									break
							m += f"**Average AA Rating:** {int(average_rating)} ({rating_descriptor})\n"
							m += f"**Range:** {aa['max_range'] / 1000:0.1f} km\n"

						embed.add_field(name="__**Anti-Air**__", value=m)

					# torpedoes
					if len(modules['torpedoes']) > 0 and is_filtered(torps_filter):
						m = ""
						for h in sorted(modules['torpedoes'], key=lambda x: module_list[str(x)]['name']):
							torps = module_list[str(h)]['profile']['torpedoes']

							m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')} ({torps['distance']} km, {torps['numBarrels']} tube{'s' if torps['numBarrels'] > 1 else ''}):**\n"
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
								m += f"**Aircraft:** {fighter['cruise_speed']} kts. (up to {fighter['max_speed']} kts), {fighter['max_health']} HP, {fighter['payload']} rocket{'s' if fighter['payload'] > 1 else ''}\n"
								m += f"**Squadron:** {fighter_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {fighter_module['attack_size']})\n"
								m += f"**Hangar:** {fighter_module['hangarSettings']['startValue']} aircrafts (Restore {fighter_module['hangarSettings']['restoreAmount']} aircraft every {fighter_module['hangarSettings']['timeToRestore']}s)\n"
								m += f"**{fighter_module['profile']['fighter']['rocket_type']} Rocket:** :boom:{fighter['max_damage']} {'(:fire:' + str(fighter['burn_probability']) + '%, Pen. ' + str(fighter['rocket_pen']) + 'mm)' if fighter['burn_probability'] > 0 else ''}\n"
								m += '\n'
						embed.add_field(name="__**Attackers**__", value=m, inline=False)

					# torpedo bomber
					if len(modules['torpedo_bomber']) > 0 and is_filtered(torpbomber_filter):
						m = ""
						for h in sorted(modules['torpedo_bomber'], key=lambda x: module_list[str(x)]['profile']['torpedo_bomber']['max_health']):
							bomber_module = module_list[str(h)]
							bomber = module_list[str(h)]['profile']['torpedo_bomber']
							n_attacks = bomber_module['squad_size'] // bomber_module['attack_size']
							m += f"**{module_list[str(h)]['name'].replace(chr(10), ' ')}**\n"
							if ship_filter == 2 ** torpbomber_filter:
								m += f"**Aircraft:** {bomber['cruise_speed']} kts. (up to {bomber['max_speed']} kts), {bomber['max_health']} HP, {bomber['payload']} torpedo{'es' if bomber['payload'] > 1 else ''}\n"
								m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
								m += f"**Hangar:** {bomber_module['hangarSettings']['startValue']} aircrafts (Restore {bomber_module['hangarSettings']['restoreAmount']} aircraft every {bomber_module['hangarSettings']['timeToRestore']}s)\n"
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
								m += f"**Aircraft:** {bomber['cruise_speed']} kts. (up to {bomber['max_speed']} kts), {bomber['max_health']} HP, {bomber['payload']} bomb{'s' if bomber['payload'] > 1 else ''}\n"
								m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
								m += f"**Hangar:** {bomber_module['hangarSettings']['startValue']} aircrafts (Restore {bomber_module['hangarSettings']['restoreAmount']} aircraft every {bomber_module['hangarSettings']['timeToRestore']}s)\n"
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
								m += f"**Aircraft:** {bomber['cruise_speed']} kts. (up to {bomber['max_speed']} kts), {bomber['max_health']} HP, {bomber['payload']} bomb{'s' if bomber['payload'] > 1 else ''}\n"
								m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
								m += f"**Hangar:** {bomber_module['hangarSettings']['startValue']} aircrafts (Restore {bomber_module['hangarSettings']['restoreAmount']} aircraft every {bomber_module['hangarSettings']['timeToRestore']}s)\n"
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

					# upgrades
					if ship_filter == (1 << upgrades_filter):
						m = ""
						for slot in upgrades:
							m += f"**Slot {slot + 1}**\n"
							if len(upgrades[slot]) > 0:
								for u in upgrades[slot]:
									m += f"{upgrade_list[u]['name']}\n"
							m += "\n"

						embed.add_field(name="__**Upgrades**__", value=m, inline=True)

					# consumables
					if len(consumables) > 0 and is_filtered(consumable_filter):
						m = ""
						for consumable_slot in consumables:
							if len(consumables[consumable_slot]['abils']) > 0:
								m += f"__**Slot {consumables[consumable_slot]['slot'] + 1}:**__ "
								if ship_filter == (1 << consumable_filter):
									m += '\n'
								for c_index, c in enumerate(consumables[consumable_slot]['abils']):
									consumable_id, consumable_type = c
									consumable = game_data[find_game_data_item(consumable_id)[0]][consumable_type]
									consumable_name = consumable_descriptor[consumable['consumableType']]['name']
									# consumable_description = consumable_descriptor[consumable['consumableType']]['description']
									consumable_type = consumable["consumableType"]

									charges = 'Infinite' if consumable['numConsumables'] < 0 else consumable['numConsumables']
									action_time = consumable['workTime']
									cd_time = consumable['reloadTime']

									m += f"**{consumable_name}** "
									if ship_filter == (1 << consumable_filter):  # shows detail of consumable
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
										if len(consumables[consumable_slot]['abils']) > 1 and c_index != len(consumables[consumable_slot]['abils']) - 1:
											m += 'or '
								m += '\n'

						embed.add_field(name="__**Consumables**__", value=m, inline=False)
					footer_message = "Parameters does not take into account upgrades or commander skills\n"
					footer_message += f"For details specific parameters, use [mackbot ship {ship} (parameters)]\n"
					footer_message += f"For {ship.title()} builds, use [mackbot build {ship}]\n"
					if is_test_ship:
						footer_message += f"*Test ship is subject to change before her release\n"
					embed.set_footer(text=footer_message)
				await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}", e)
			# error, ship name not understood
			if type(e) == NoShipFound:
				# ship with specified name is not found, user might mistype ship name?
				ship_name_list = [ship_list[i]['name'].lower() for i in ship_list]
				closest_match = difflib.get_close_matches(ship, ship_name_list)
				closest_match_string = closest_match[0].title()
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match_string}**?'
				embed = discord.Embed(title=f"Ship {ship} is not understood.\n", description=closest_match_string)
				embed.description += "\n\nType \"y\" or \"yes\" to confirm."
				embed.set_footer(text="Response expire in 10 seconds")
				await context.send(embed=embed)
				await correct_user_misspell(context, 'ship', closest_match[0])

			else:
				# we dun goofed
				await context.send(f"An internal error has occured.")

async def ship_compact(context, ship_data, ship_param):
	"""
	Send a compact version of the build command.

	Args:
		context: A discord.ext.commands.Context object
		ship_data: ship data gathered from the get_ship_data() function
		ship_param: ship parameter from the get_ship_param() function

	Returns: None

	"""
	name = ship_data['name']
	nation = ship_data['nation']
	images = ship_data['images']
	ship_type = ship_data['type']
	tier = list(roman_numeral.keys())[ship_data['tier'] - 1]
	modules = ship_data['modules']
	is_prem = ship_data['is_premium']
	is_test_ship = ship_data['is_test_ship']
	logging.info(f"returning ship information for <{name}> in embeded format")
	ship_type = ship_types[ship_type]
	ship_type_emoji = icons_emoji[hull_classification_converter[ship_type].lower() + ("_prem" if is_prem else "")]

	embed = discord.Embed(title=f"{ship_type_emoji} {tier} {name} {'' if not is_test_ship else '[TEST SHIP]'}", description="")
	embed.set_thumbnail(url=images['small'])

	# hull info
	if len(modules['hull']):
		m = ""
		for h in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name']):
			hull = module_list[str(h)]['profile']['hull']
			hull_name = module_list[str(h)]['name']
			aa = module_list[str(h)]['profile']['anti_air']
			rating_descriptor = ""
			for d in AA_RATING_DESCRIPTOR:
				low, high = AA_RATING_DESCRIPTOR[d]
				if low <= aa['rating'] <= high:
					rating_descriptor = d
					break

			m += f"{ship_type_emoji} __**{hull_name}**__ \n"
			m += f"{hull['health']:1.0f} HP\n"
			m += f"{icons_emoji['aa']} {aa['max_range']/1000:0.1f} km | {rating_descriptor} AA\n"
		m += "\n"
		embed.add_field(name="\u200b", value=m, inline=False)
	# gun info
	if len(modules['artillery']):
		m = ""
		for mb in sorted(modules['artillery'], key=lambda x: module_list[str(x)]['profile']['artillery']['caliber'], reverse=True):
			mb_name = module_list[str(mb)]['name']
			mb_range = ""
			for fc in sorted(modules['fire_control'], key=lambda x: module_list[str(x)]['profile']['fire_control']['distance']):
				mb_range += f"{module_list[str(fc)]['profile']['fire_control']['distance']} - "
			mb_range = mb_range[:-2]
			mb = module_list[str(mb)]['profile']['artillery']
			m += f"{icons_emoji['gun']} __**{mb_name}**__\n"
			m += f"{icons_emoji['reload']} {mb['shotDelay']:0.1f}s | {icons_emoji['range']} {mb_range} km\n"
			if mb['max_damage_HE']:
				m += f"{icons_emoji['he']} {mb['max_damage_HE']} :boom: | :fire: {mb['burn_probability']:2.0f}% | {icons_emoji['penetration']} {mb['pen_HE']:2.0f} mm\n"
			if mb['max_damage_SAP']:
				m += f"{icons_emoji['sap']} {mb['max_damage_SAP']} :boom: | {icons_emoji['penetration']} {mb['pen_SAP']:2.0f} mm\n"
			if mb['max_damage_AP']:
				m += f"{icons_emoji['ap']} {mb['max_damage_AP']} :boom:\n"
			m += '\n'

		embed.add_field(name="\u200b", value=m, inline=False)
	# torp info
	if len(modules['torpedoes']):
		m = ""
		for t in sorted(modules['torpedoes'], key=lambda x: module_list[str(x)]['name']):
			torps = module_list[str(t)]['profile']['torpedoes']
			torps_name = module_list[str(t)]['name'].replace(chr(10), ' ')
			reload_minute = int(torps['shotDelay'] // 60)
			reload_second = int(torps['shotDelay'] % 60)

			m += f"{icons_emoji['torp']} __**{torps_name}**__\n"
			m += f"{icons_emoji['reload']} {'' if reload_minute == 0 else str(reload_minute) + 'm'} {reload_second}s | {icons_emoji['range']} {torps['distance']:0.1f} km\n"
			m += f"{icons_emoji['plane_torp']} {torps['max_damage']:2.0f} :boom: | {icons_emoji['plane_torp']} x {torps['numBarrels']} | {torps['torpedo_speed']:0.1f} kts.\n"
			m += '\n'
		embed.add_field(name="\u200b", value=m, inline=False)
	# rockets
	if len(modules['fighter']):
		m = ""
		for h in sorted(modules['fighter'], key=lambda x: module_list[str(x)]['profile']['fighter']['max_health']):
			fighter_module = module_list[str(h)]
			fighter = module_list[str(h)]['profile']['fighter']
			fighter_name = module_list[str(h)]['name'].replace(chr(10), ' ')

			m += f"{icons_emoji['plane_rocket']} __**{fighter_name}**__\n"
			m += f"{icons_emoji['plane']} x {fighter_module['squad_size']} | {fighter['cruise_speed']} kts.\n"
			m += f":boom: {fighter['max_damage']:1.0f} x {fighter['payload']} x {fighter_module['attack_size']} {icons_emoji['plane']}\n"
			m += f"{icons_emoji['reload']} {fighter_module['hangarSettings']['timeToRestore']:1.0f}s\n"

		embed.add_field(name="\u200b", value=m, inline=True)

	# torp bomber
	if len(modules['torpedo_bomber']):
		m = ""
		for h in sorted(modules['torpedo_bomber'], key=lambda x: module_list[str(x)]['profile']['torpedo_bomber']['max_health']):
			torpedo_bomber_module = module_list[str(h)]
			torpedo_bomber = module_list[str(h)]['profile']['torpedo_bomber']
			torpedo_bomber_name = module_list[str(h)]['name'].replace(chr(10), ' ')

			m += f"{icons_emoji['plane_torp']} __**{torpedo_bomber_name}**__\n"
			m += f"{icons_emoji['plane']} x {torpedo_bomber_module['squad_size']} | {torpedo_bomber['cruise_speed']} kts.\n"
			m += f":boom: {torpedo_bomber['max_damage']:1.0f} x {torpedo_bomber['payload']} {icons_emoji['plane_torp']} x {torpedo_bomber_module['attack_size']} {icons_emoji['plane']}\n"
			m += f"{icons_emoji['reload']} {torpedo_bomber_module['hangarSettings']['timeToRestore']:1.0f}s\n"

		embed.add_field(name="\u200b", value=m, inline=True)
	# bomber
	if len(modules['dive_bomber']):
		m = ""
		for h in sorted(modules['dive_bomber'], key=lambda x: module_list[str(x)]['profile']['dive_bomber']['max_health']):
			dive_bomber_module = module_list[str(h)]
			dive_bomber = module_list[str(h)]['profile']['dive_bomber']
			dive_bomber_name = module_list[str(h)]['name'].replace(chr(10), ' ')

			m += f"{icons_emoji['plane_bomb']} __**{dive_bomber_name}**__\n"
			m += f"{icons_emoji['plane']} x {dive_bomber_module['squad_size']} | {dive_bomber['cruise_speed']} kts.\n"
			m += f":boom: {dive_bomber['max_damage']:1.0f} x {dive_bomber['payload']} {icons_emoji['plane_torp']} x {dive_bomber_module['attack_size']} {icons_emoji['plane']}\n"
			m += f"{icons_emoji['reload']} {dive_bomber_module['hangarSettings']['timeToRestore']:1.0f}s\n"

		embed.add_field(name="\u200b", value=m, inline=True)
	# skip
	if len(modules['skip_bomber']):
		m = ""
		for h in sorted(modules['skip_bomber'], key=lambda x: module_list[str(x)]['profile']['skip_bomber']['max_health']):
			skip_bomber_module = module_list[str(h)]
			skip_bomber = module_list[str(h)]['profile']['skip_bomber']
			skip_bomber_name = module_list[str(h)]['name'].replace(chr(10), ' ')

			m += f"{icons_emoji['plane_bomb']} __**{skip_bomber_name}**__\n"
			m += f"{icons_emoji['plane']} x {skip_bomber_module['squad_size']} | {skip_bomber['cruise_speed']} kts.\n"
			m += f":boom: {skip_bomber['max_damage']:1.0f} x {skip_bomber['payload']} {icons_emoji['plane_torp']} x {skip_bomber_module['attack_size']} {icons_emoji['plane']}\n"
			m += f"{icons_emoji['reload']} {skip_bomber_module['hangarSettings']['timeToRestore']:1.0f}s\n"

		embed.add_field(name="\u200b", value=m, inline=True)
	# concealment
	if ship_param['concealment']:
		m = ""
		m += f"{icons_emoji['concealment']}{ship_type_emoji}: {ship_param['concealment']['detect_distance_by_ship']:0.1f} km\n"
		m += f"{icons_emoji['concealment']}{icons_emoji['plane']}: {ship_param['concealment']['detect_distance_by_plane']:0.1f} km\n"
		embed.add_field(name="\u200b", value=m, inline=False)

	footer_message = "Parameters does not take into account upgrades or commander skills\n"
	footer_message += f"For details specific parameters, use [mackbot ship {name} (parameters)]\n"
	footer_message += f"For {name.title()} builds, use [mackbot build {name}]\n"
	if is_test_ship:
		footer_message += f"*Test ship is subject to change before her release\n"
	embed.set_footer(text=footer_message)
	await context.send(embed=embed)

@mackbot.command()
async def skill(context, *args):
	# get information on requested skill
	# message parse
	if len(args) == 0:
		await context.send_help("skill")
	else:
		skill = ''
		try:
			ship_class = args[0].lower()
			skill = ''.join([i + ' ' for i in args[1:]])[:-1]  # message_string[message_string.rfind('-')+1:]

			logging.info(f'sending message for skill <{skill}>')
			async with context.typing():
				skill_data = get_skill_data(ship_class, skill)
				name = skill_data['name']
				tree = skill_data['tree']
				description = skill_data['description']
				effect = skill_data['effect']
				column = skill_data['x'] + 1
				tier = skill_data['y']
				category = skill_data['category']
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
async def show(context, *args):
	# list command
	if context.invoked_subcommand is None:
		await context.invoke(mackbot.get_command('help'), 'show')
	# TODO: send help command if subcommand is wrong

@show.command()
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
	page = int(page[0]) if len(page) > 0 else 0

	# generate list of skills
	m = [
		f"**({hull_classification_converter[filtered_skill_list[s]['tree']]} T{filtered_skill_list[s]['y'] + 1})** {filtered_skill_list[s]['name']}" for s in filtered_skill_list
	]

	# splitting list into pages
	num_items = len(m)
	m.sort()
	items_per_page = 24
	num_pages = ceil(len(m) / items_per_page)
	m = [m[i:i + items_per_page] for i in range(0, len(m), items_per_page)]

	embed = discord.Embed(title="Commander Skill (%i/%i)" % (min(1, page+1), min(1, num_pages)))
	m = m[page]  # select page
	# spliting selected page into columns
	m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]
	for i in m:
		embed.add_field(name="(Type, tier) Skill", value=''.join([v + '\n' for v in i]))
	embed.set_footer(text=f"{num_items} skills found.\nFor more information on a skill, use [{command_prefix} skill [ship_class] [skill_name]]")

	await context.send(embed=embed)

@show.command()
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
		except ValueError:
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
			if all([k in tags for k in key]):
				result += [u]
		logging.info("parsing complete")
		logging.info("compiling message")
		if len(result) > 0:
			m = []
			for u in result:
				upgrade = upgrade_list[u]
				name = get_upgrade_data(upgrade['name'])['name']
				for u_b in upgrade_abbr_list:
					if upgrade_abbr_list[u_b] == name.lower():
						m += [f"**{name}** ({u_b.upper()})"]
						break

			num_items = len(m)
			m.sort()
			items_per_page = 30
			num_pages = ceil(len(m) / items_per_page)
			m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

			embed = discord.Embed(title=embed_title + f"({page + 1}/{num_pages})")
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
			logging.info(f"Upgrade listing argument <{args[3]}> is invalid.")
			error_message = f"Value {args[3]} is not understood"
		else:
			logging.info(f"Exception {type(e)}", e)
	await context.send(embed=embed)

@show.command()
async def maps(context, *args):
	# list all maps
	try:
		logging.info("sending list of maps")
		try:
			page = int(args[3]) - 1
		except ValueError:
			page = 0
		m = [f"{map_list[i]['name']}" for i in map_list]
		m.sort()
		items_per_page = 20
		num_pages = ceil(len(map_list) / items_per_page)

		m = [m[i:i + items_per_page] for i in range(0, len(map_list), items_per_page)]  # splitting into pages
		embed = discord.Embed(title="Map List " + f"({page + 1}/{num_pages})")
		m = m[page]  # select page
		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
		for i in m:
			embed.add_field(name="Map", value=''.join([v + '\n' for v in i]))
	except Exception as e:
		if type(e) == IndexError:
			embed = None
			error_message = f"Page {page + 1} does not exists"
		elif type(e) == ValueError:
			logging.info(f"Upgrade listing argument <{args[3]}> is invalid.")
			error_message = f"Value {args[3]} is not understood"
		else:
			logging.info(f"Exception {type(e)}", e)
	await context.send(embed=embed)

@show.command()
async def ships(context, *args):
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
			if all([k.lower() in tags for k in key]):
				result += [s]
		except:
			pass
	logging.info("parsing complete")
	logging.info("compiling message")
	m = []
	logging.info(f"found {len(m)} items matching criteria {''.join(key)}")
	if len(result) > 0:
		# return the list of ships with fitting criteria
		for ship in result:
			ship_data = get_ship_data(ship_list[ship]['name'])
			if ship_data is None:
				continue
			name = ship_data['name']
			ship_type = ship_data['type']
			tier = ship_data['tier']
			is_prem = ship_data['is_premium']

			tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0]
			type_icon = icons_emoji[hull_classification_converter[ship_type].lower() + ("_prem" if is_prem else "")]
			# m += [f"**{tier_string:<6} {type_icon}** {name}"]
			m += [[tier, tier_string, type_icon, name]]

		num_items = len(m)
		m.sort(key=lambda x: (x[0], x[2], x[-1]))
		# m_mod = []
		# for i, v in enumerate(m):
		# 	if v[0] != m[i - 1][0]:
		# 		m_mod += [[-1, '', '', '']]
		# 	m_mod += [v]
		# m = m_mod
		#
		# m = [f"**{tier_string:<6} {type_icon}** {name}" if tier != -1 else "-------------" for tier, tier_string, type_icon, name in m]
		m = [f"**{(tier_string + ' '+ type_icon).ljust(16, chr(160))}** {name}" for tier, tier_string, type_icon, name in m]

		items_per_page = 30
		num_pages = ceil(len(m) / items_per_page)
		m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

		embed = discord.Embed(title=embed_title + f"({max(1, page + 1)}/{max(1, num_pages)})")
		m = m[page]  # select page
		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
		embed.set_footer(text=f"{num_items} ships found\nTo get ship build, use [{command_prefix} build [ship_name]]")
		for i in m:
			embed.add_field(name="(Tier) Ship", value=''.join([v + '\n' for v in i]))
	else:
		# no ships found
		embed = discord.Embed(title=embed_title, description="")
		embed.description = "**No ships found**"
	await context.send(embed=embed)

@mackbot.command()
async def upgrade(context, *args):
	# get information on requested upgrade
	upgrade_found = False
	# message parse
	upgrade = ''.join([i + ' ' for i in args])[:-1]  # message_string[message_string.rfind('-')+1:]
	if len(args) == 0:
		# argument is empty, send help message
		await context.send_help("upgrade")
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
			# does user provide ship name, probably?
			get_legendary_upgrade_by_ship_name(upgrade)
			search_func = get_legendary_upgrade_by_ship_name
			logging.info("user requested an legendary upgrade")

		try:
			# assuming that user provided the correct upgrade
			logging.info(f'sending message for upgrade <{upgrade}>')
			output = search_func(upgrade)
			profile = output['profile']
			name = output['name']
			image = output['image']
			price_credit = output['price_credit']
			description = output['description']
			is_special = output['is_special']
			ship_restriction = output['ship_restriction']
			nation_restriction = output['nation_restriction']
			tier_restriction = output['tier_restriction']
			type_restriction = output['type_restriction']
			slot = output['slot']
			special_restriction = output['additional_restriction']

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
					m = ''.join([i + ', ' for i in sorted(ship_restriction[:10])])[:-2]
					if len(ship_restriction) > 10:
						m += "...and more"
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
					logging.warning("Additional requirements field empty")
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
async def player(context, *args):
	user_input = args[0][:24]

	async with context.typing():
		player_id_results = WG.account.list(search=user_input, type='exact', language='en')
		player_id = str(player_id_results[0]['account_id']) if len(player_id_results) > 0 else ""
		battle_type = 'pvp'
		battle_type_string = 'Random'

		# grab optional args
		optional_args = player_arg_filter_regex.findall(''.join([i + ' ' for i in args[1:]]))
		battle_type = [option[0] for option in optional_args if len(option[0])] # get stats by battle division/solo
		ship_filter = ''.join(option[2] for option in optional_args if len(option[2]))[:-1] # get filter type by ship name
		ship_type_filter = [option[4] for option in optional_args if len(option[4])] # filter ship listing, same rule as list ships
		ship_type_filter = ship_list_regex.findall(''.join(i + ' ' for i in ship_type_filter))
		try:
			ship_tier_filter = int(''.join([i[2] for i in ship_type_filter]))
		except ValueError:
			ship_tier_filter = ''
		ship_search_key = [i[7] for i in ship_type_filter if len(i[7]) > 1]
		try:
			# convert user specified specific stat to wg values
			battle_type = {
				"solo": "pvp_solo",
				"div2": "pvp_div2",
				"div3": "pvp_div3",
			}[battle_type[0]]

			battle_type_string = {
				"pvp_solo": "Solo Random",
				"pvp_div2": "2-man Division",
				"pvp_div3": "3-man Division",
			}[battle_type]
		except IndexError:
			battle_type = 'pvp'

		embed = discord.Embed(title=f"Search result for player {escape_discord_format(user_input)}")
		if player_id:
			player_name = player_id_results[0]['nickname']
			if battle_type == 'pvp':
				player_general_stats = WG.account.info(account_id=player_id, language='en')[player_id]
			else:
				player_general_stats = WG.account.info(account_id=player_id, extra="statistics."+battle_type, language='en')[player_id]
			player_account_hidden = player_general_stats['hidden_profile']

			if player_account_hidden:
				# account hidden, don't show any more status
				embed.add_field(name='Information not available', value="Account hidden", inline=False)
			else:
				# account not hidden, show info
				player_created_at_string = date.fromtimestamp(player_general_stats['created_at']).strftime("%b %d, %Y")
				player_last_battle_string = date.fromtimestamp(player_general_stats['last_battle_time']).strftime("%b %d, %Y")
				player_last_battle_days = (date.today() - date.fromtimestamp(player_general_stats['last_battle_time'])).days
				player_last_battle_months = int(player_last_battle_days // 30)
				player_clan_id = WG.clans.accountinfo(account_id=player_id, language='en')[player_id]['clan_id']
				player_clan = None
				player_clan_str = ""
				if player_clan_id is not None:
					player_clan = WG.clans.info(clan_id=player_clan_id, language='en')[player_clan_id]
					player_clan_str = f"**[{player_clan['tag']}]** {player_clan['name']}"
				else:
					player_clan_str = "No clan"

				m = f"**Created at**: {player_created_at_string}\n"
				m += f"**Last battle**: {player_last_battle_string} "
				if player_last_battle_days > 0:
					if player_last_battle_months > 0:
						m += f"({player_last_battle_months} months {player_last_battle_days // 30} day{'s' if player_last_battle_days > 1 else ''} ago)\n"
					else:
						m += f"({player_last_battle_days} day{'s' if player_last_battle_days > 1 else ''} ago)\n"
				else:
					m += " (Today)\n"
				m += f"**Clan**: {player_clan_str}"
				embed.add_field(name='__**Account**__', value=m, inline=False)

				player_battle_stat = player_general_stats['statistics'][battle_type]
				player_stat_wr = player_battle_stat['wins'] / player_battle_stat['battles']
				player_stat_sr = player_battle_stat['survived_battles'] / player_battle_stat['battles']
				player_stat_max_kills = player_battle_stat['max_frags_battle']

				ship_data = get_ship_data_by_id(player_battle_stat['max_frags_ship_id'])
				player_stat_max_kills_ship = ship_data['name']
				player_stat_max_kills_ship_type = ship_data['emoji']
				player_stat_max_kills_ship_tier = list(roman_numeral.keys())[ship_data['tier'] - 1]
				player_stat_max_damage = player_battle_stat['max_damage_dealt']

				ship_data = get_ship_data_by_id(player_battle_stat['max_damage_dealt_ship_id'])
				player_stat_max_damage_ship = ship_data['name']
				player_stat_max_damage_ship_type = ship_data['emoji']
				player_stat_max_damage_ship_tier = list(roman_numeral.keys())[ship_data['tier'] - 1]

				player_stat_avg_kills = player_battle_stat['frags'] / player_battle_stat['battles']
				player_stat_avg_dmg = player_battle_stat['damage_dealt'] / player_battle_stat['battles']
				player_stat_avg_xp = player_battle_stat['xp'] / player_battle_stat['battles']

				m = f"**{player_battle_stat['battles']:,} battles**\n"
				m += f"**Win Rate**: {player_stat_wr:0.2%} ({player_battle_stat['wins']} W / {player_battle_stat['losses']} L / {player_battle_stat['draws']} D)\n"
				m += f"**Survival Rate**: {player_stat_sr:0.2%} ({player_battle_stat['survived_battles']} battles)\n"
				m += f"**Average Kills**: {player_stat_avg_kills:0.2f}\n"
				m += f"**Average Damage**: {player_stat_avg_dmg:2.0f}\n"
				m += f"**Average XP**: {player_stat_avg_xp:0.0f} XP\n"
				m += f"**Highest kill**: {player_stat_max_kills} kill{'s' if player_stat_max_kills > 0 else ''} with {player_stat_max_kills_ship_type} **{player_stat_max_kills_ship_tier} {player_stat_max_kills_ship}**\n"
				m += f"**Highest Damage**: {player_stat_max_damage} with {player_stat_max_damage_ship_type} **{player_stat_max_damage_ship_tier} {player_stat_max_damage_ship}**\n"
				embed.add_field(name=f"__**{battle_type_string} Battle**__", value=m, inline=True)

				# add listing for player owned ships and of requested battle type
				player_ships = WG.ships.stats(account_id=player_id, language='en', extra='' if battle_type == 'pvp' else battle_type)[player_id]
				player_ship_stats = {}
				# calculate stats for each ships
				for s in player_ships:
					ship_id = s['ship_id']
					ship_stat = s[battle_type]
					ship_name, ship_tier, ship_nation, ship_type, _, emoji = get_ship_data_by_id(ship_id).values()
					stats = {
						"name"      : ship_name.lower(),
						"tier"      : ship_tier,
						"emoji"     : emoji,
						"nation"    : ship_nation,
						"type"      : ship_type,
						"battles"   : ship_stat['battles'],
						'wins'      : ship_stat['wins'],
						'losses'    : ship_stat['losses'],
						'kills'     : ship_stat['frags'],
						'damage'    : ship_stat['damage_dealt'],
						"wr"        : 0 if ship_stat['battles'] == 0 else ship_stat['wins'] / ship_stat['battles'],
						"sr"        : 0 if ship_stat['battles'] == 0 else ship_stat['survived_battles'] / ship_stat['battles'],
						"avg_dmg"   : 0 if ship_stat['battles'] == 0 else ship_stat['damage_dealt'] / ship_stat['battles'],
						"avg_kills" : 0 if ship_stat['battles'] == 0 else ship_stat['frags'] / ship_stat['battles'],
						"avg_xp"    : 0 if ship_stat['battles'] == 0 else ship_stat['xp'] / ship_stat['battles'],
						"max_kills" : ship_stat['max_frags_battle'],
						"max_dmg"   : ship_stat['max_damage_dealt']
					}
					player_ship_stats[ship_id] = stats.copy()
				# sort player owned ships by battle count
				player_ship_stats = {k: v for k, v in sorted(player_ship_stats.items(), key=lambda x: x[1]['battles'], reverse=True)}

				m = ""
				for i in range(10):
					try:
						s = player_ship_stats[list(player_ship_stats)[i]] # get ith ship
						m += f"**{s['emoji']} {list(roman_numeral)[s['tier'] - 1]} {s['name'].title()}** ({s['battles']} / {s['wr']:0.2%} WR)\n"
					except IndexError:
						pass
				embed.add_field(name=f"__**Top 10 {battle_type_string} Ships (by battles)**__", value=m, inline=True)
				player_ship_stats_df = pd.DataFrame.from_dict(player_ship_stats, orient='index')

				embed.add_field(name='\u200b', value='\u200b', inline=False)
				if ship_tier_filter:
					# list ships that the player has at this tier
					player_ship_stats_df = player_ship_stats_df[player_ship_stats_df['tier'] == ship_tier_filter]
					top_n = 10
					items_per_col = 5
					if len(player_ship_stats_df) > 0:
						r = 1
						for i in range(top_n // items_per_col):
							m = ""
							if i <= len(player_ship_stats_df) // items_per_col:
								for s in player_ship_stats_df.index[(items_per_col * i) : (items_per_col * (i+1))]:
									ship = player_ship_stats_df.loc[s] # get ith ship of filtered ship list by tier
									m += f"{r}) **{ship['emoji']} {ship['name'].title()}**\n"
									m += f"({ship['battles']} battles / {ship['wr']:0.2%} WR / {ship['sr']:2.2%} SR)\n"
									m += f"Avg. Kills: {ship['avg_kills']:0.2f} | Avg. Damage: {ship['avg_dmg']:2.0f}\n\n"
									r += 1
								embed.add_field(name=f"__**Top {top_n} Tier {ship_tier_filter} Ships (by battles)**__", value=m, inline=True)
					else:
						embed.add_field(name=f"__**Top {top_n} Tier {ship_tier_filter} Ships (by battles)**__", value="Player have no ships of this tier", inline=True)
				elif ship_filter:
					# display player's ship stat
					m = ""
					try:
						ship_data = get_ship_data(ship_filter)
						ship_filter = ship_data['name'].lower()
						ship_id = ship_data['ship_id']
						player_ship_stats_df = player_ship_stats_df[player_ship_stats_df['name'] == ship_filter].to_dict(orient='index')[ship_id]
						ship_battles_draw = player_ship_stats_df['battles'] - (player_ship_stats_df['wins'] + player_ship_stats_df['losses'])
						m += f"**{list(roman_numeral.keys())[player_ship_stats_df['tier'] - 1]} {player_ship_stats_df['emoji']} {player_ship_stats_df['name'].title()}**\n"
						m += f"**{player_ship_stats_df['battles']} Battles**\n"
						m += f"**Win Rate:** {player_ship_stats_df['wr']:2.2%} ({player_ship_stats_df['wins']} W / {player_ship_stats_df['losses']} L / {ship_battles_draw} D)\n"
						m += f"**Survival Rate: ** {player_ship_stats_df['sr']:2.2%} ({player_ship_stats_df['sr'] * player_ship_stats_df['battles']:1.0f} battles)\n"
						m += f"**Average Damage: ** {player_ship_stats_df['avg_dmg']:1.0f}\n"
						m += f"**Average Kills: ** {player_ship_stats_df['avg_kills']:0.2f}\n"
						m += f"**Average XP: ** {player_ship_stats_df['avg_xp']:1.0f}\n"
						m += f"**Max Damage: ** {player_ship_stats_df['max_dmg']}\n"
						m += f"**Max Kills: ** {player_ship_stats_df['max_kills']}\n"
					except Exception as e:
						if type(e) == NoShipFound:
							m += f"Ship with name {ship_filter} is not found\n"
						else:
							m += "An internal error has occurred.\n"
							traceback.print_exc()
					embed.add_field(name="__Ship Specific Stat__", value=m)

				else:
					# add battle distribution by ship types
					player_ship_stats_df = player_ship_stats_df.groupby(['type']).sum()
					m = ""
					for s_t in sorted([i for i in ship_types if i != "Aircraft Carrier"]):
						try:
							type_stat = player_ship_stats_df.loc[s_t]
							if type_stat['battles'] > 0:
								m += f"**{ship_types[s_t]}s**\n"

								type_average_kills = type_stat['kills'] / max(1, type_stat['battles'])
								type_average_dmg = type_stat['damage'] / max(1, type_stat['battles'])
								type_average_wr = type_stat['wins'] / max(1, type_stat['battles'])
								m += f"{int(type_stat['battles'])} battle{'s' if type_stat['battles'] else ''} ({type_stat['battles'] / player_battle_stat['battles']:2.1%})\n"
								m += f"{type_average_wr:0.2%} WR | {type_average_kills:0.2f} Kills | {type_average_dmg:2.0f} DMG\n\n"
						except KeyError:
							pass
					embed.add_field(name=f"__**Stat by Ship Types**__", value=m)

					# average stats by tier
					player_ship_stats_df = pd.DataFrame.from_dict(player_ship_stats, orient='index')
					player_ship_stats_df = player_ship_stats_df.groupby(['tier']).sum()
					m = ""
					for tier in range(1, 11):
						try:
							tier_stat = player_ship_stats_df.loc[tier]
							tier_average_kills = tier_stat['kills'] / max(1, tier_stat['battles'])
							tier_average_dmg = tier_stat['damage'] / max(1, tier_stat['battles'])
							tier_average_wr = tier_stat['wins'] / max(1, tier_stat['battles'])

							m += f"**{list(roman_numeral.keys())[tier - 1]}: {int(tier_stat['battles'])} battles ({tier_stat['battles'] / player_battle_stat['battles']:2.1%})**\n"
							m += f"{tier_average_wr:0.2%} WR | {tier_average_kills:0.2f} Kills | {tier_average_dmg:2.0f} DMG\n"
						except KeyError:
							m += f"**{list(roman_numeral.keys())[tier - 1]}**: No battles\n"
					embed.add_field(name=f"__**Average by Tier**__", value=m)

				embed.set_footer(text=f"Last updated at {date.fromtimestamp(player_general_stats['stats_updated_at']).strftime('%b %d, %Y')}")
		else:
			embed.add_field(name='Information not available', value=f"mackbot cannot find player with name {escape_discord_format(user_input)}", inline=True)
	await context.send(embed=embed)

@mackbot.command()
async def commander(context, *args):
	# get information on requested commander
	# message parse
	cmdr = ''.join([i + ' ' for i in args])[:-1]  # message_string[message_string.rfind('-')+1:]
	if len(args) == 0:
		await context.send_help("commander")
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
async def map(context, *args):
	# get information on requested map
	# message parse
	map = ''.join([i + ' ' for i in args])[:-1]  # message_string[message_string.rfind('-')+1:]
	if len(args) == 0:
		await context.send_help("map")
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
async def doubloons(context, *args):
	# get conversion between doubloons and usd and vice versa
	if len(args) == 0:
		await context.send_help("doubloons")
	else:
		# user provided an argument
		doub = 0
		try:
			# message parse
			doub = args[0]  # message_string[message_string.rfind('-')+1:]
			if len(args) == 2:
				# check reverse conversion
				# dollars to doubloons
				if args[1].lower() in ['dollars', '$']:
					dollar = float(doub)

					def dollar_formula(x):
						return x * EXCHANGE_RATE_DOUB_TO_DOLLAR

					logging.info(f"converting {dollar} dollars -> doubloons")
					embed = discord.Embed(title="Doubloon Conversion (Dollars -> Doubloons)")
					embed.add_field(name=f"Requested Dollars", value=f"{dollar:0.2f}$")
					embed.add_field(name=f"Doubloons", value=f"Approx. {dollar_formula(dollar):0.0f} Doubloons")

			else:
				# doubloon to dollars
				doub = int(doub)
				value_exceed = not (500 <= doub <= 100000)

				def doub_formula(x):
					return x / EXCHANGE_RATE_DOUB_TO_DOLLAR

				logging.info(f"converting {doub} doubloons -> dollars")
				embed = discord.Embed(title="Doubloon Conversion (Doubloons -> Dollars)")
				embed.add_field(name=f"Requested Doubloons", value=f"{doub} Doubloons")
				embed.add_field(name=f"Price: ", value=f"{doub_formula(doub):0.2f}$")
				footer_message = f"Current exchange rate: {EXCHANGE_RATE_DOUB_TO_DOLLAR} Doubloons : 1 USD"
				if value_exceed:
					footer_message += "\n:warning: You cannot buy the requested doubloons."
				embed.set_footer(text=footer_message)

			await context.send(embed=embed)
		except Exception as e:
			logging.info(f"Exception {type(e)}", e)
			if type(e) == TypeError:
				await context.send(f"Value **{doub}** is not a number.")
			else:
				await context.send(f"An internal error has occured.")

@mackbot.command()
async def code(context, *args):
	if len(args) == 0:
		await context.send_help("code")
	else:
		for code in args:
			s = f"**{code.upper()}** https://na.wargaming.net/shop/redeem/?bonus_mode= {+ code.upper()}"
			logging.info(f"returned a wargaming bonus code link with code {code}")
			await context.send(s)

@mackbot.command()
async def hottake(context):
	logging.info("sending a hottake")
	await context.send('I tell people that ' + hottake_strings[randint(0, len(hottake_strings)-1)])
	if randint(0, 9) == 0:
		await asyncio.sleep(2)
		await purpose(context)

async def purpose(context):
	author = context.author
	await context.send(f"{author.mention}, what is my purpose?")
	def check(message):
		return author == message.author and message.content.lower().startswith("you") and len(message.content[3:]) > 0

	message = await mackbot.wait_for('message', timeout=30, check=check)
	await context.send("Oh my god...")

@mackbot.command()
async def invite(context):
	await context.send(bot_invite_url)

if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--fetch_new_build', action='store_true', required=False, help="Remove local ship_builds.json file so that new builds can be fetched. mackbot will try to connect first before removing local ship build file.")
	args = arg_parser.parse_args()

	# pre processing botes
	load_game_params()
	load_skill_list()
	load_module_list()
	load_cmdr_list()
	load_ship_list()
	load_upgrade_list()
	load_ship_params()
	update_ship_modules()
	create_upgrade_abbr()

	# retrieve new build from google sheets
	if args.fetch_new_build:
		try:
			ship_build_file_dir = os.path.join(".", "data", "ship_builds.json")
			extract_build_from_google_sheets(ship_build_file_dir, True)
			os.remove(os.path.join(ship_build_file_dir))
		except:
			pass

	if database_client is None:
		load_ship_builds()
	create_ship_tags()

	# post processing for bot commands
	logging.info("Post-processing bot commands")
	with open(os.path.join(".", "help_command_strings.json")) as f:
		help_command_strings = json.load(f)
	for c in help_command_strings:
		try:
			command = mackbot.get_command(c)

			command.help = help_command_strings[c]['help']
			command.brief = help_command_strings[c]['brief']
			command.usage = "usage: " + help_command_strings[c]['usage']
			command.description = ''.join([i + '\n' for i in help_command_strings[c]['description']])

		except:
			pass
	del help_command_strings
	mackbot.run(bot_token)
