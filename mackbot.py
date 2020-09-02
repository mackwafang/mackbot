DEBUG_IS_MAINTANCE = False

# loading cheats
import wargaming, os, re, sys, pickle, discord, time, logging, json, difflib, pprint
import xml.etree.ElementTree as et
import pandas as pd
import numpy as np
import cv2 as cv
from PIL import ImageFont, ImageDraw, Image
from itertools import count
from numpy.random import randint

# dont remeber why this is here. DO NOT REMOVE
cwd = sys.path[0]
if cwd == '':
	cwd = '.'

# logging shenanigans
# logging.basicConfig(filename=f'{time.strftime("%Y_%b_%d", time.localtime())}_mackbot.log')
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
	'pan_america': 'Pan-American'
}
# convert weegee ship type to usn hull classifications
ship_type_to_hull_class = {
	'Destroyer': 'DD',
	'AirCarrier': 'CV',
	'Battleship': 'BB',
	'Cruiser': 'C',
	'Submarine': 'SS'
}
# dictionary to convert user inputted ship name to non-ascii ship name
# TODO: find an automatic method, maybe
ship_name_to_ascii ={
	'[zao]':'[zaō]',
	'arp myoko':'arp myōkō',
	'arp myoukou':'arp myōkō',
	'smaland':'småland',
	'arp kongo':'arp kongō',
	'arp kongou':'arp kongō',
	'[grober kurfurst]':'[großer kurfürst]',
	'l\'effronte':'l\'effronte',
	'blyskawica':'błyskawica',
	'yudachi':'yūdachi',
	'yuudachi':'yūdachi',
	'yugumo':'yūgumo',
	'yuugumo':'yūgumo',
	'kleber':'kléber',
	'hakuryu':'hakuryū',
	'hakuryuu':'hakuryū',
	'haku':'hakuryū',
	'hak':'hakuryū',
	'kagero':'kagerō',
	'kagerou':'kagerō',
	'konig albert':'könig albert',
	'grosser kurfurst':'großer kurfürst',
	'grober kurfurst':'großer kurfürst',
	'kurfurst':'großer kurfürst',
	'republique':'république',
	'konig':'könig',
	'ryuujou':'ryūjō',
	'ryujo':'ryūjō',
	'guepard':'guépard',
	'ostergotland':'östergötland',
	'shoukaku':'shōkaku',
	'shokaku':'shōkaku',
	'skane':'skåne',
	'vasteras':'västerås',
	'la galissonniere':'la galissonnière',
	'algerie':'algérie',
	'oland':'öland',
	'konigsberg':'königsberg',
	'hosho':'hōshō',
	'houshou':'hōshō',
	'emile bertin':'émile bertin',
	'nurnberg':'nürnberg',
	'friedrich der grobe':'friedrich der große',
	'fdg':'friedrich der große',
	'tatra':'tátra',
	'myoko':'myōkō',
	'myoukou':'myōkō',
	'kongo':'kongō',
	'kongou':'kongō',
	'fujin':'fūjin',
	'yubari':'yūbari',
	'yuubari':'yūbari',
	'zao':'zaō',
	'fuso':'fusō',
	'fusou':'fusō',
	'tenryu':'tenryū',
	'tenryuu':'tenryū',
	'st. louis':'st. louis',
	'myogi':'myōgi',
	'myougi':'myōgi',
	'jurien de la graviere':'jurien de la gravière',
	'khaba':'khabarovsk',
	'fdr':'franklin d. roosevelt',
	'shima':'shimakaze',
	'nevsky':'alexander nevsky',
	'al nevsky':'alexander nevsky',
	'erich': 'erich loewenhardt',
	'parseval': 'august von parseval',
	'richthofen': 'manfred von richthofen',
	'makarov': 'admiral makarov',
	'graf spee': 'admiral graf spee',
	'hsf graf spee': 'hsf admiral graf spee',
	'muchen': 'münchen',
	'hipper': 'admiral hipper',
	'eugen': 'prinz eugen',
	'donskoi': 'dmitri donskoi',
	'petro': 'petropavlovsk',
	'henri': 'henri iv',
	'loewenhardt': 'erich loewenhardt',
}
# see the ship name conversion dictionary comment
cmdr_name_to_ascii = {
	'jean-jacques honore':'jean-jacques honoré',
	'paul kastner':'paul kästner',
	'quon rong':'quán róng',
	'myoko':'myōkō',
	'myoukou':'myōkō',
	'reinhard von jutland':'reinhard von jütland',
	'matsuji ijuin':'matsuji ijūin',
	'kongo':'kongō',
	'kongou':'kongō',
	'tao ji':'tāo ji',
	'gunther lutjens':'günther lütjens',
	'franz von jutland':'franz von jütland',
	'da rong':'dà róng',
	'rattenkonig':'rattenkönig',
	'leon terraux':'léon terraux',
	'charles-henri honore':'charles-henri honoré',
	'jerzy swirski':'Jerzy Świrski',
	'swirski':'Jerzy Świrski',
	'halsey':'william f. Halsey jr.',
}
# here because of lazy
roman_numeral = {
	'i': 	1,
	'ii': 	2,
	'iii': 	3,
	'iv': 	4,
	'v': 	5,
	'vi': 	6,
	'vii': 	7,
	'viii': 8,
	'ix': 	9,
	'x': 	10,
}

# actual stuff
logging.info("Fetching WoWS Encyclopedia")
# load important stuff
with open(cwd+"/.env") as f:
	s = f.read().split('\n')[:-1]
	wg_token = s[0][s[0].find('=')+1:]
	bot_token = s[1][s[1].find('=')+1:]
	sheet_id = s[2][s[2].find('=')+1:]

# get weegee's wows encyclopedia
wows_encyclopedia = wargaming.WoWS(wg_token,region='na',language='en').encyclopedia
ship_types = wows_encyclopedia.info()['ship_types'] 

logging.info("Fetching Skill List")
skill_list = wows_encyclopedia.crewskills()
# dictionary that stores skill abbreviation
skill_name_abbr = {}
for skill in skill_list:
	# generate abbreviation
	abbr_name = ''.join([i[0] for i in skill_list[skill]['name'].lower().split()])
	skill_name_abbr[abbr_name] = skill_list[skill]['name'].lower()
	# get local image location
	url = skill_list[skill]['icon']
	url = url[:url.rfind('_')]
	url = url[url.rfind('/')+1:]
	skill_list[skill]['local_icon'] = f'./skill_images/{url}.png'
# additional abbreviation
with open('skill_name_abbr.csv') as f:
	s = f.read().split('\n')
	for i in s:
		k, v = i.split(',')
		skill_name_abbr[k] = v

# putting missing values
skill_list['19']['perks'] = [{'perk_id':0, 'description':'A warning about a salvo fired at your ship from a distance of more than 4.5 km'}]
skill_list['20']['perks'] = [{'perk_id':0, 'description':'When the engine or steering gears are incapacitated, they continue to operate but with a penalty'}]
skill_list['28']['perks'] = [
	{'perk_id':0, 'description':'The detection indicator will show the number of opponents currently aiming at your ship with thier main battery guns'},
	{'perk_id':1, 'description':'For an aircraft carrier\'s squadron, the detection indicator will show the numbers of ships whose AA defenses are current firing at your planes.'}
]
skill_list['32']['perks'] = [{'perk_id':0, 'description':'Completely restores the engine boost for the last attacking flight of the aircraft carrier\'s squadron'}]
skill_list['34']['perks'] = [
	{'perk_id':0, 'description':'Shows the direction of the nearest enemy ship'},
	{'perk_id':1, 'description':'The enemy player will be alerted that a bearing was taken on their ship'},
	{'perk_id':2, 'description':'Does not work on aircraft carriers'},
]
logging.info("Fetching Module List")
module_list = {}
for page in count(1):
	try:
		m = wows_encyclopedia.modules(language='en',page_no=page)
		for i in m:
			module_list[i] = m[i]
			module_list[i]['fetch_new_data_from_sheets'] = False
			if module_list[i]['type'] not in ['Artillery', 'Torpedoes', 'Fighters', 'TorpedoBomber', 'DiveBomber', 'Engine', 'Armor']:
				module_list[i]['fetch_new_data_from_sheets'] = True
	except Exception as e:
		if type(e) == wargaming.exceptions.RequestError:
			if e.args[0] == "PAGE_NO_NOT_FOUND":
				break
			else:
				logging.info(type(e), e)
		else:
			logging.info(type(e), e)
		break
		
logging.info("Loading Game Params json")
with open('GameParams.json') as f:
	game_data = json.load(f)

# find game data items by tags
find_game_data_item = lambda x: [i for i in game_data if x in i]
find_module_by_tag = lambda x: [i for i in module_list if x == module_list[i]['tag']][0]

logging.info("Fetching Commander List")
cmdr_list = wows_encyclopedia.crews()
cmdr_skill_descriptor = {
	'AIGunsEfficiencyModifier': {
		 'nearAuraDamageCoefficientDescriptor': 'Continuous damage by AA mounts',
		 'smallGunReloadCoefficientDescriptor': 'Reload time of main battery guns with a caliber up to and including 139 mm, and secondary battery guns',
	},
	'AIGunsRangeModifier': {
		 'advancedOuterAuraDamageCoefficientDescriptor': 'Damage from AA shell explosions:',
		 'smallGunRangeCoefficientDescriptor': ' Firing range of main battery guns with a caliber up to and including 139 mm, and secondary battery guns:',
	},
	'AccuracyIncreaseRateModifier': {
		 'diveBomberDescriptor': 'Bomber aiming speed:',
		 'fighterDescriptor': 'Attack aircraft aiming speed:',
		 'torpedoBomberDescriptor': 'Torpedo bomber aiming speed:',
	},
	'AdditionalSmokescreensModifier': {
		 'radiusCoefficientDescriptor': 'Radius of the smoke screen:',
	},
	'AimingFightersPointModifier': {
		 'extraFighterCountDescriptor': 'Number of aircraft:',
		 'fighterLifeTimeCoefficientDescriptor': 'Fighter action time',
	},
	'AirSupremacyModifier': {
		 'hangarSizeBonusDescriptor': 'Aircraft hanger size:',
		 'planeSpawnTimeCoefficientDescriptor': 'Aircraft restoreation time:',
	},
	'AllSkillsCooldownModifier': {
		 'reloadCoefficientDescriptor': 'Consumable reload time:',
	},
	'ArtilleryAlertModifier': {
		 'alertMinDistanceDescriptor': 'Warning about a salvo fired at your ship from a distance of more than ',
	},
	'AutoRepairModifier': {
		 'critTimeCoefficientDescriptor': 'Time of repair, fire extinguishing, and recovery from flooding:',
	},
	'CentralATBAModifier': {
		 'atbaIdealRadiusHiDescriptor': 'Maximum dispersion of shells for the secondary armament of Tier VII–X ships:',
		 'atbaIdealRadiusLoDescriptor': 'Maximum dispersion of shells for the secondary armament of Tier I–VI ships:',
	},
	'CentralAirDefenceModifier': {
		 'prioSectorCooldownCoefficientDescriptor': 'Priority AA sector preparation time:',
		 'prioSectorPhaseDurationCoefficientDescriptor': '',
		 'prioSectorStartPhaseStrengthCoefficientDescriptor': 'Instantaneous Damage:',
		 'prioSectorStrengthCoefficientDescriptor': '',
	},
	'EmergencyTeamCooldownModifier': {
		 'reloadCoefficientDescriptor': 'Reload time of the Damage Control Party consumable:',
	},
	'FireProbabilityModifier': {
		 'bombProbabilityBonusDescriptor': 'Bombs fire chance:',
		 'probabilityBonusDescriptor': 'HE shells fire chance:',
		 'rocketProbabilityBonusDescriptor': 'HE rockets fire chance:',
	},
	'FireResistanceModifier': {
		 'probabilityCoefficientDescriptor': 'Risk of catching fire:',
	},
	'FlightSpeedModifier': {
		 'flightSpeedCoefficientDescriptor': 'Aircraft cruising speed:',
	},
	'ForsageDurationModifier': {
		 'forsageDurationCoefficientDescriptor': 'Engine boost time:',
	},
	'ForsageRestorationModifier': {
	},
	'IntuitionModifier': {
		 'switchAmmoReloadCoefDescriptor': 'Time taken to switch shell type:',
	},
	'LandmineExploderModifier': {
		 'chanceToSetOnFireBonusBigDescriptor': 'Chances of fire:',
		 'chanceToSetOnFireBonusSmallDescriptor': 'Chances of fire:',
		 'thresholdPenetrationCoefficientBigDescriptor': 'HE armor penetration:',
		 'thresholdPenetrationCoefficientSmallDescriptor': 'HE armor penetration:',
	},
	'LastChanceModifier': {
		 'hpStepDescriptor': 'Ship lost health per bonus:',
		 'squadronHealthStepDescriptor': 'Squadron lost health per bonus:',
		 'squadronSpeedStepDescriptor': 'Ship squadron speed increase:',
		 'timeStepDescriptor': 'Consumable increase per bonus:',
	},
	'LastEffortModifier': {
		 'critRudderTimeCoefficientDescriptor': 'Engine/Steering gear penalty:',
	},
	'MainGunsRotationModifier': {
		 'bigGunBonusDescriptor': 'Tranvese speed of guns > 139mm:',
		 'smallGunBonusDescriptor': 'Tranvese speed of guns <= 139mm:',
	},
	'MeticulousPreventionModifier': {
		 'critProbCoefficientDescriptor': 'Risk of modules becoming incapacitated:',
	},
	'NearAuraDamageTakenModifier': {
		 'nearAuraDamageTakenCoefficientDescriptor': 'Continuous damage from AA mounts:',
	},
	'NearEnemyIntuitionModifier': {
	},
	'PriorityTargetModifier': {
	},
	'SuperintendentModifier': {
		 'additionalConsumablesDescriptor': 'Additional consumable:',
	},
	'SurvivalModifier': {
		 'healthPerLevelDescriptor': 'Ship HP per tier:',
		 'planeHealthPerLevelDescriptor': 'Aircraft HP per tier',
	},
	'TorpedoAcceleratorModifier': {
		 'planeTorpedoRangeCoefficientDescriptor': 'Aircraft torpedo range:',
		 'planeTorpedoSpeedBonusDescriptor': 'Aircraft torpedo speed:',
		 'torpedoRangeCoefficientDescriptor': 'Ship-launched torpedo range:',
		 'torpedoSpeedBonusDescriptor': 'Ship-launched torpedo speed:',
	},
	'TorpedoAlertnessModifier': {
		 'planeRangeCoefficientDescriptor': 'Torpedo acquisition range by air:',
		 'rangeCoefficientDescriptor': 'Torpedo acquisition range by sea:',
	},
	'TorpedoReloadModifier': {
		 'launcherCoefficientDescriptor': 'Torpedo reload speed:',
	},
	'VisibilityModifier': {
		 'aircraftCarrierCoefficientDescriptor': 'Detectability of aircraft carriers:',
		 'battleshipCoefficientDescriptor': 'Detectability of battleships:',
		 'cruiserCoefficientDescriptor': 'Detectability of cruisers:',
		 'destroyerCoefficientDescriptor': 'Detectability of destroyers:',
		 'squadronCoefficientDescriptor': 'Detectability of squadrons:',
		 'submarineCoefficientDescriptor': 'Detectability of submarines:',
	},
}
consumable_descriptor = {
	'airDefenseDisp' : {
		'name': 'Defensive Anti-Air Fire',
		'description': 'Increase continuous AA damage and damage from flak bursts.',
	},
	'artilleryBoosters' : {
		'name': 'Main Battery Reload Booster',
		'description': 'Greatly decreases the reload time of main battery guns',
	},
	'callFighters' : {
		'name': '',
		'description': ''
	},
	'crashCrew' : {
		'name': 'Damage Control Party',
		'description': 'Immediately extinguish fires, stops flooding, and repair incapacitated modules. Also provides the ship with immunity to fires, floodings, and modules incapacitation for the active duration.',
	},
	'depthCharges' : {},
	'fighter' : {
		'name': 'Fighters',
		'description': 'Deploy fighters to protect your ship from enemy aircrafts.'
	},
	'healForsage' : {
		'name': '',
		'description': ''
	},
	'invulnerable' : {
		'name': '',
		'description': ''
	},
	'regenCrew' : {
		'name': 'Repair Party',
		'description': 'Restore ship\'s HP.'
	},
	'regenerateHealth' : {
		'name': '',
		'description': ''
	},
	'rls' : {
		'name': 'Surveillance Radar',
		'description': 'Automatically detects any ships within the radar\'s range. Have longer range but lower duration than Hydroacoustic Search.',
	},
	'scout' : {
		'name': 'Spotting Aircraft',
		'description': 'Deploy spotter plane to increase firing range.',
	},
	'smokeGenerator' : {
		'name': 'Smoke Generator',
		'description': 'Deploys a smoke screen to obsure enemy\'s vision.',
	},
	'sonar' : {
		'name': 'Hydroacoustic Search',
		'description': 'Automatically detects any ships and torpedoes within certain range with shorter range but higher duration than Surveillance Radar',
	},
	'speedBoosters' : {
		'name': 'Engine Boost',
		'description': 'Temporary increase ship\'s maximum speed and engine power.',
	},
	'subsFourthState' : {},
	'torpedoReloader' : {
		'name': 'Torpedo Reload Booster',
		'description': 'Significantly reduces the reload time of torpedoes.',
	},
}

logging.info("Fetching Ship List")
ship_list = {}
for page in count(1): #range(1,6):
	try:
		l = wows_encyclopedia.ships(language='en',page_no=page)
		for i in l:
			ship_list[i] = l[i]
	except Exception as e:
		if type(e) == wargaming.exceptions.RequestError:
			if e.args[0] == "PAGE_NO_NOT_FOUND":
				break
			else:
				logging.info(type(e), e)
		else:
			logging.info(type(e), e)
		break
del ship_list['3445503440'], ship_list['3340744656'], ship_list['3335501808']
logging.info("Fetching Camo, Flags and Modification List")
camo_list, flag_list, upgrade_list, flag_list = {}, {}, {}, {}
for page_num in count(1):
	# continuously count, because weegee don't list howmany pages there are
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
				url = url[url.rfind('/')+1:]
				
				# initializing stuff for excluding obsolete upgrades
				upgrade_list[consumable]['local_image'] = f'./modernization_icons/{url}.png'
				upgrade_list[consumable]['is_special'] = ''
				upgrade_list[consumable]['ship_restriction'] = []
				upgrade_list[consumable]['nation_restriction'] = []
				upgrade_list[consumable]['tier_restriction'] = []
				upgrade_list[consumable]['type_restriction'] = []
				upgrade_list[consumable]['slot'] = ''
				upgrade_list[consumable]['additional_restriction'] = ''
				upgrade_list[consumable]['on_other_ships'] = []
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
logging.info('Fetching build file...')
BUILD_EXTRACT_FROM_CACHE = False
extract_from_web_failed = False
BUILD_BATTLE_TYPE_CLAN = 0
BUILD_BATTLE_TYPE_CASUAL = 1
BUILD_CREATE_BUILD_IMAGES = True
# dunno why this exists, keep it
build_battle_type = {
	BUILD_BATTLE_TYPE_CLAN   : "competitive",
	BUILD_BATTLE_TYPE_CASUAL : "casual",
}
build_battle_type_value = {
	"competitive"	: BUILD_BATTLE_TYPE_CLAN,
	"casual" 		: BUILD_BATTLE_TYPE_CASUAL,
}
ship_build = {build_battle_type[BUILD_BATTLE_TYPE_CLAN]:{}, build_battle_type[BUILD_BATTLE_TYPE_CASUAL]:{}}
# fetch ship builds and additional upgrade information
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
	# The file token.pickle stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)
	# If there are no (valid) credentials available, let the user log in.
	try:
		if not creds or not creds.valid:
			if creds and creds.expired and creds.refresh_token:
				creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(
					'credentials.json', SCOPES)
				creds = flow.run_local_server(port=0)
			# Save the credentials for the next run
			with open('token.pickle', 'wb') as token:
				pickle.dump(creds, token)
				
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
				if ship_name.lower() in ship_name_to_ascii: #does name includes non-ascii character (outside prinable ?
					ship_name = ship_name_to_ascii[ship_name.lower()] # convert to the appropiate name
				upgrades = [i for i in row[2:8] if len(i) > 0]
				skills = [i for i in row[8:-2] if len(i) > 0]
				cmdr = row[-1]
				ship_build[build_type][ship_name] = {"upgrades":upgrades, "skills":skills, "cmdr":cmdr}
		logging.info("Build data fetching done")
	except Exception as e:
		extract_from_web_failed = True
		logging.info(f"Exception raised while fetching builds: {e}")
	# fetch upgrade exclusion list
	logging.info("Excluding Equipments...")
	result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
								range='upgrade_list!A2:S200').execute()
	values = result.get('values', [])
	values = [[i[0]] + i[-9:] for i in values]

	if not values:
		print('No data found.')
		raise Error
	else:
		for row in values:
			try:
				row = ['' if i == '_' else i for i in row]
				upgrade_id = row[0]
				upgrade_type = row[1]
				usable_dictionary = {'yes':False, 'no':True}
				upgrade_usable = usable_dictionary[row[2].lower()]
				# grabbing columns
				upgrade_slot = row[3]
				upgrade_ship_restrict = [] if len(row[4]) == 0 else row[4].split(', ')
				upgrade_tier_restrict = [] if len(row[5]) == 0 else [int(i) for i in row[5].split(', ')]
				upgrade_type_restrict = [] if len(row[6]) == 0 else row[6].split(', ')
				upgrade_nation_restrict = [] if len(row[7]) == 0 else row[7].split(', ')
				upgrade_special_restrict = [] if len(row[8]) == 0 else row[8].split('_')
				upgrade_tags = [] if len(row[9]) == 0 else row[9].split(', ')
			except Exception as e:
				# oops
				logging.info("Equipments parsing exception with value: ")
				logging.info(row)
				continue
			# acutally checking for obsolete and filing new data
			u = upgrade_id
			upgrade = upgrade_list[u]
			if u == upgrade_id:
				if not upgrade_usable:
					# upgrade obsolete, remove
					del upgrade_list[u]
					pass
				else:
					try:
						upgrade_list[u]['is_special'] = upgrade_type
						if len(upgrade_type) > 0:
							upgrade_list[u]['tags'] += [upgrade_type.lower()]
							if upgrade_list[u]['is_special'].lower() == 'legendary':
								upgrade_list[u]['tags'] += ['unique']
						upgrade_list[u]['ship_restriction'] = upgrade_ship_restrict
						if len(upgrade_ship_restrict) > 0:
							upgrade_list[u]['tags'] += upgrade_ship_restrict
						upgrade_list[u]['nation_restriction'] = upgrade_nation_restrict
						if len(upgrade_nation_restrict) > 0:
							upgrade_list[u]['tags'] += upgrade_nation_restrict
						upgrade_list[u]['tier_restriction'] = upgrade_tier_restrict
						if len(upgrade_tier_restrict) > 0:
							upgrade_list[u]['tags'] += [f"tier {i}" for i in upgrade_tier_restrict]
						upgrade_list[u]['type_restriction'] = upgrade_type_restrict
						if len(upgrade_type_restrict) > 0:
							upgrade_list[u]['tags'] += upgrade_type_restrict
						upgrade_list[u]['slot'] = upgrade_slot
						upgrade_list[u]['tags'] += [f"slot {upgrade_slot}"]
						upgrade_list[u]['tags'] += upgrade_tags
						if len(upgrade_special_restrict) > 0:
							for s in upgrade_special_restrict:
								if len(s) > 0:
									s = s[1:-1].split(', ', maxsplit=2)
									if s[0].lower() == 'None':
										s[0] = None
									else:
										upgrade_list[u]['tags'] += [s[0]]
									upgrade_list[u]['on_other_ships'] += [(s[0],s[1])]
									upgrade_list[u]['additional_restriction'] = '' if s[2].lower() == 'None' else s[2]
					except Exception as e:
						# oops, skip this
						logging.info(f"Equipments exclusion exception {e} at upgrade id {u}")

if BUILD_EXTRACT_FROM_CACHE or extract_from_web_failed:
	if extract_from_web_failed:
		logging.info("Get builds from sheets failed")
	root = et.parse(cwd+"/ship_builds.xml").getroot()
	logging.info('Making build dictionary from cache')
	for ship in root:
		upgrades = []
		skills = []
		build_type = int(ship.find('type').text)
		for upgrade in ship.find('upgrades'):
			upgrades.append(upgrade.text)
		for skill in ship.find('skills'):
			skills.append(skill.text)
		cmdr = ship.find('commander').text
		ship_build[build_battle_type[build_type]][ship.attrib['name']] = {"upgrades":upgrades, "skills":skills, "cmdr":cmdr}
	logging.info("build dictionary complete")

logging.info("Filling missing informations of modules")
for s in ship_list:
	ship = ship_list[s]
	module_full_id_str = find_game_data_item(ship['ship_id_str'])
	for i in module_full_id_str:
		module_data = game_data[i]
		
		# grab consumables
		ship_list[s]['consumables'] = module_data['ShipAbilities'].copy()
		
		ship_upgrade_info = module_data['ShipUpgradeInfo'] # get upgradable modules
		for _info in ship_upgrade_info: # for each upgradable modules
			if type(ship_upgrade_info[_info]) == dict: # if there are data
				try:
					module_id = find_module_by_tag(_info) # what is this module?
				except:
					logging.critical(f"Module with tag {_info} is not found")
					exit(1)
				if ship_upgrade_info[_info]['ucType'] == '_Artillery': # guns, guns, guns!
					#get turret parameter
					gun = ship_upgrade_info[_info]['components']['artillery'][0]
					gun = module_data[gun]
					gun = np.unique([gun[turret]['name'] for turret in [g for g in gun if 'HP' in g]])
					for g in gun: # for each turret
						turret_data = game_data[g]
						module_list[module_id]['profile']['artillery']['caliber'] = turret_data['barrelDiameter']
						for a in turret_data['ammoList']:
							ammo = game_data[a]
							# print(ammo['alphaDamage'], ammo['ammoType'], f"{ammo['burnProb']} fire %")
							module_list[module_id]['profile']['artillery']['numBarrels'] = turret_data['numBarrels']
							if ammo['ammoType'] == 'HE':
								module_list[module_id]['profile']['artillery']['burn_probability'] = int(ammo['burnProb']*100)
							if ammo['ammoType'] == 'CS':
								module_list[module_id]['profile']['artillery']['max_damage_SAP'] = int(ammo['alphaDamage'])
					continue
				if ship_upgrade_info[_info]['ucType'] == '_Torpedoes': # torpedooes
					#get torps parameter
					gun = ship_upgrade_info[_info]['components']['torpedoes'][0]
					gun = module_data[gun]
					gun = np.unique([gun[turret]['name'] for turret in [g for g in gun if 'HP' in g]])
					for g in gun: # for each turret
						turret_data = game_data[g]
						module_list[module_id]['profile']['torpedoes']['numBarrels'] = turret_data['numBarrels']
					continue
				if ship_upgrade_info[_info]['ucType'] == '_Fighter': # useless spotter
					#get fighter parameter
					planes = ship_upgrade_info[_info]['components']['fighter'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']] # get rocket params
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['payload'] = plane['attackCount']
						module_list[module_id]['profile']['fighter']['max_damage'] = int(projectile['alphaDamage'])
						module_list[module_id]['profile']['fighter']['rocket_burn_probability'] = int(projectile['burnProb']*100)
					continue
				if ship_upgrade_info[_info]['ucType'] == '_TorpedoBomber':
					#get torp bomber parameter
					planes = ship_upgrade_info[_info]['components']['torpedoBomber'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']]
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['payload'] = plane['attackCount']
					continue
				if ship_upgrade_info[_info]['ucType'] == '_DiveBomber':
					#get turret parameter
					planes = ship_upgrade_info[_info]['components']['diveBomber'][0]
					planes = module_data[planes].values()
					for p in planes:
						plane = game_data[p]
						projectile = game_data[plane['bombName']]
						# print(plane['numPlanesInSquadron'], plane['attackerSize'], plane['attackCount'], projectile['alphaDamage'], projectile['ammoType'], projectile['burnProb'])
						module_list[module_id]['attack_size'] = plane['attackerSize']
						module_list[module_id]['squad_size'] = plane['numPlanesInSquadron']
						module_list[module_id]['payload'] = plane['attackCount']
					continue

logging.info("Creating Modification Abbreviation")
upgrade_abbr_list = {}
for u in upgrade_list:
	# print("'"+''.join([i[0] for i in mod_list[i].split()])+"':'"+f'{mod_list[i]}\',')
	upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(160),chr(32)) # replace weird 0-width character with a space
	key = ''.join([i[0] for i in upgrade_list[u]['name'].split()]).lower()
	if key in upgrade_abbr_list: # if the abbreviation of this upgrade is in the list already
		key = ''.join([i[:2].title() for i in upgrade_list[u]['name'].split()]).lower()[:-1] # create a new abbreviation
	upgrade_abbr_list[key] = upgrade_list[u]['name'].lower() # add this abbreviation
legendary_upgrades = {u: upgrade_list[u] for u in upgrade_list if upgrade_list[u]['is_special'].lower() == 'legendary'}

logging.info("Fetching Ship Parameters")
ship_param_file_name = 'ship_param'
logging.info("Checking cached ship_param file...")
if os.path.isfile('./'+ship_param_file_name):
	logging.info("File found. Loading file")
	with open('./'+ship_param_file_name, 'rb') as f:
		ship_info = pickle.load(f)
else:
	logging.info("File not found, fetching from weegee")
	i = 0
	ship_info = {}
	for s in ship_list:
		ship = wows_encyclopedia.shipprofile(ship_id=int(s), language='en')
		ship_info[s] = ship[s]
		i += 1
		logging.info(f"Fetching ship parameters. {i}/{len(ship_list)} ships found\r")
	logging.info("Creating cache")
	with open('./'+ship_param_file_name,'wb') as f:
		pickle.dump(ship_info, f)
	logging.info("Cache creation complete")
logging.info("Generating ship search tags")
SHIP_TAG_SLOW_SPD = 0
SHIP_TAG_FAST_SPD = 1
SHIP_TAG_FAST_GUN = 2
SHIP_TAG_STEALTH = 3

SHIP_TAG_LIST = (
	'slow',
	'fast',
	'fast-firing',
	'stealth',
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
		'description': "Any ships in this category have a **base speed** of **35 knots or faster**",
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
	}
}
ship_list_regex = re.compile('((tier )(\d{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|((page )(\d{1,2}))|(([aA]ircraft [cC]arrier[sS]?)|((\w|-)*))')
equip_regex = re.compile('(slot (\d))|(tier ([0-9]{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|(page (\d{1,2}))|((defensive aa fire)|(main battery)|(aircraft carrier[sS]?)|(\w|-)*)')
ship_param_filter_regex = re.compile('((hull|health|hp)|(guns?|artiller(?:y|ies))|(secondar(?:y|ies))|(torp(?:s|edo(?:es)?)?( bombers?)?)|((?:dive )?bombers?)|((?:rockets?)|(?:attackers?))|(speed)|((?:concealment)|(?:dectection))|((?:aa)|(?:anti-air))|(consumables?))*')
for s in ship_list:
	nat = nation_dictionary[ship_list[s]['nation']]
	tags = []
	t = ship_list[s]['type']
	hull_class = ship_type_to_hull_class[t]
	if t == 'AirCarrier':
		t = 'Aircraft Carrier'
	tier = ship_list[s]['tier'] # add tier to search 
	prem = ship_list[s]['is_premium'] # is bote premium
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
	
	tags += [nat, f't{tier}',t ,t+'s', hull_class]
	ship_list[s]['tags'] = tags
	if prem:
		ship_list[s]['tags'] += ['premium']
		
logging.info("Filtering Ships and Categories")
del ship_list['3749623248']
# filter data tyoe
ship_list_frame = pd.DataFrame(ship_list)
ship_list_frame = ship_list_frame.filter(items=['name', 'nation', 'images', 'type', 'tier', 'consumables', 'modules', 'upgrades', 'is_premium', 'price_gold', 'tags'],axis=0)
ship_list = ship_list_frame.to_dict()

logging.info("Fetching Maps")
map_list = wows_encyclopedia.battlearenas()
# del game_data # free up memory
logging.info("Preprocessing Done")

command_header = 'mackbot'
token = ' '

good_bot_messages = (
	'Thank you!',
	'Yūdachi tattara kekkō ganbatta poii? Teitoku-san homete hometei!',
	':3',
	':heart:',
)
command_list = (
	'help',
	'goodbot',
	'build',
	'skill',
	'whoami',
	'list',
	'upgrade',
	'commander',
	'flag',
	'feedback',
	'map',
	'ship',
	'doubloons',
)
def check_build():
	'''
		checks ship_build for in incorrectly inputted values and outputs to stdout, and write build images
	'''
	skill_use_image = cv.imread("./skill_images/icon_perk_use.png", cv.IMREAD_UNCHANGED)
	skill_use_image_channel = [i for i in cv.split(skill_use_image)]
	for t in build_battle_type:
		for s in ship_build[build_battle_type[t]]:
			image = np.zeros((520,660,4))
			logging.info(f"Checking {build_battle_type[t]} battle build for ship {s}...")
			
			name, nation, _, ship_type, tier, _, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_build_data(s, battle_type=build_battle_type[t])
			font = ImageFont.truetype('arialbd.ttf', 20)
			image_pil = Image.fromarray(image, mode='RGBA')
			draw = ImageDraw.Draw(image_pil)
			draw.text((0,0), f"{build_battle_type[t].title()} {name.title()}", font=font, fill=(255,255,255,255))
			category_title = ['Endurance', 'Attack', 'Support', 'Versatility']
			for s in range(len(category_title)):
				draw.text((s*180,30), category_title[s], font=font, fill=(255,255,255,255))
			draw.text((0,330), "Upgrades", font=font, fill=(255,255,255,255))
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
			draw.text((0,440), "Commander", font=font, fill=(255,255,255,255))
			draw.text((0,460), "Any" if cmdr == "*" else cmdr, font=font, fill=(255,255,255,255))
			
			image = np.array(image_pil)
			for skill in skill_list:
				x = skill_list[skill]['type_id']
				y = skill_list[skill]['tier']
				img = cv.imread(skill_list[skill]['local_icon'], cv.IMREAD_UNCHANGED)
				h,w,_ = img.shape
				image[y*h : (y+1)*h, (x + (x // 2))*w: (x+(x // 2)+1)*h] = img
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
								img = cv.imread('./modernization_icons/icon_modernization_missing.png', cv.IMREAD_UNCHANGED)
						except Exception as e:
							logging.info(f"Upgrade check: Exception {type(e)}", e, f"in check_build, listing upgrade {upgrade}")
					img = np.array(img)
					y = 6
					x = upgrade_index
					h, w, _ = img.shape
					img = [i for i in cv.split(img)]
					for i in range(3):
						image[y*h : (y+1)*h, x*w: (x+1)*w, i] = img[i]
					image[y*h : (y+1)*h, x*w: (x+1)*w, 3] += img[3]
					upgrade_index += 1 
			else:
				logging.info("Upgrade check: No upgrades found")
			# suggested skills
			if len(skills) > 0:
				for skill in skills:
					try:
						_, id, _, _, tier, _= get_skill_data(skill)
						x = id
						y = tier
						h,w,_ = skill_use_image.shape
						for i in range(3):
							image[y*h : (y+1)*h, (x + (x // 2))*w : (x+(x // 2)+1)*h, i] = skill_use_image_channel[i]
						image[y*h : (y+1)*h, (x + (x // 2))*w : (x+(x // 2)+1)*h, 3] += skill_use_image_channel[3]
						
					except Exception as e: 
						logging.info(f"Skill check: Exception {type(e)}", e, f"in check_build, listing skill {skill}")
			else:
				logging.info("Skill check: No skills found in build")
			cv.imwrite(f"{name.lower()}_{build_battle_type[t]}_build.png", image)
def get_build_data(ship, battle_type='casual'):
	"""
		returns name, nation, images, ship type, tier of requested warship name
		
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
		raise exceptions for dictionary
	"""
	
	original_arg = ship
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii: #does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()] # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			# print(ship.lower(),ship_name_in_dict.lower())
			if ship.lower() == ship_name_in_dict.lower(): # find ship based on name
				ship_found = True
				break
		if ship_found:
			name, nation, images, ship_type, tier, consumables, modules, equip_upgrades, is_prem, price_gold, _ = ship_list[i].values()
			upgrades, skills, cmdr = {}, {}, ""
			if name.lower() in ship_build[battle_type]:
				upgrades, skills, cmdr = ship_build[battle_type][name.lower()].values()
			return name, nation, images, ship_type, tier, consumables, modules, equip_upgrades, is_prem, price_gold, upgrades, skills, cmdr, battle_type
	except Exception as e:
		raise e
def get_ship_data(ship):
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
		if ship.lower() in ship_name_to_ascii: #does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()] # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			# print(ship.lower(),ship_name_in_dict.lower())
			if ship.lower() == ship_name_in_dict.lower(): # find ship based on name
				ship_found = True
				break
		if ship_found:
			return ship_info[i]
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
			profile, name, price_gold, image, _, price_credit, _, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships, tags = upgrade.values()
			return profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships
	return None
def get_skill_data(skill):
	"""
		returns informations of a requested commander skill
		
		Arguments:
		-------
			- skill : (string)
				Skill's full name or abbreviation
		
		Returns:
		-------
		tuple:
			name		- (str) name of skill
			id			- (int) horizontal location (0-7)
			skill_type	- (str) category
			perk		- (dict) bonuses
			tier		- (int) tier (1-4)
			icon		- (dict) image url
			
		raise exceptions for dictionary
	"""
	skill = skill.lower()
	try:
		skill_found = False
		# assuming input is full skill name
		for i in skill_list:
			if skill.lower() == skill_list[i]['name'].lower():
				skill_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not skill_found:
			skill = skill_name_abbr[skill.lower()]
			for i in skill_list:
				if skill.lower() == skill_list[i]['name'].lower():
					skill_found = True
					break
		# found it!
		name, column, skill_type, perk, tier, icon, _ = skill_list[i].values()
		return name, column, skill_type, perk, tier, icon
	except Exception as e:
		# oops, probably not found
		logging.info(f"Exception {type(e)}: ",e)
		raise e
def get_skill_data_by_grid(column, tier):
	"""
		returns informations of a requested commander skill by column and tier

		Arguments:
		-------
			- column : (int)
				which column to search (0-7)
			- tier : (int)
				which skill tier to look for (1-4)

		Returns:
		-------
		tuple:
			name		- (str) name of skill
			id			- (int) horizontal location (0-7)
			skill_type	- (str) category
			perk		- (dict) bonuses
			tier		- (int) tier (1-4)
			icon		- (dict) image url

		raise exceptions for dictionary
	"""
	try:
		skill_found = False
		# assuming input is full skill name
		for i in skill_list:
			if column == skill_list[i]['type_id'] and tier == skill_list[i]['tier']:
				skill_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not skill_found:
			skill = skill_name_abbr[skill.lower()]
			for i in skill_list:
				if skill.lower() == skill_list[i]['name'].lower():
					skill_found = True
					break
		# found it!
		name, column, skill_type, perk, tier, icon, _ = skill_list[i].values()
		return name, column, skill_type, perk, tier, icon
	except Exception as e:
		# oops, probably not found
		logging.info(f"Exception {type(e)}: ",e)
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
		profile, name, price_gold, image, _, price_credit, _, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships, _ = upgrade_list[i].values()
		
		return profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships
	except Exception as e:
		raise e
		logging.info(f"Exception {type(e)}: ",e)
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
			if cmdr_list[i]['last_names'] == []:
				# get special commaders
				name = cmdr_list[i]['first_names'][0]
				icons = cmdr_list[i]['icons'][0]['1']
				nation = cmdr_list[i]['nation']
				
				return name, icons, nation, i
	except Exception as e:
		logging.error(f"Exception {type(e)}",e)
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
		raise e
		logging.info(f"Exception {type(e)}: ",e)
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
		raise e
		logging.info("Exception {type(e): ", e)
		
class Client(discord.Client):
	"""
		the discord client
	"""
	async def on_ready(self):
		await self.change_presence(activity=discord.Game(command_header+token+command_list[0]))
		logging.info("Logged on")
	def help_message(self,message):
		# help message
		arg = message.split(token)
		embed = discord.Embed(title=f"Command Help")
		try:
			command = arg[2]
			embed.add_field(name='Command',value=f"{''.join([i+' ' for i in arg[2:]])}")
		except Exception as e:
			if arg[1].lower() == "help" and type(e) == IndexError:
				# invoking help message
				command = "help"
				embed.add_field(name='Command',value="help")
		if command in command_list:
			if command == 'help':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[command]',inline=False)
				embed.add_field(name='Description',value='List proper usage for [command]. Omit -[command] to list all possible commands',inline=False)
				m = [i+'\n' for i in command_list]
				m.sort()
				m = ''.join(m)
				embed.add_field(name='All Commands',value=m)
			elif command == 'goodbot':
				embed.add_field(name='Usage',value=command_header+token+command,inline=False)
				embed.add_field(name='Description',value='Praise the bot for being a good bot',inline=False)
			elif command == 'build':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[type]'+token+'build'+token+'[image]',inline=False)
				embed.add_field(name='Description',value='List name, nationality, type, tier, recommended build of the requested warships\n'+
					'**ship**: Required. Desired ship to request a build.\n\n'+
					f'**[type]**: Optional. Indicates should {command_header} returns a competitive or a casual build. Acceptable values: **[competitive, casual]**. Default value is **casual**\n\n'+
					'**[image]**: Optional. If the word **image** is present, then return an image format instead of an embedded message format. If a build does not exists, it return an embedded message instead.',inline=False)
			elif command == 'ship':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[ship]'+token+'(parameters)',inline=False)
				embed.add_field(name='Description',value='List the combat parameters of the requested warships\n\n'+
					'**ship**: Required. Desired ship to get combat information.\n\n'+
					'**(parameters)**: Optional. Surround keywords with parenthesis to filter ship parameters.\n',inline=False)
			elif command == 'skill':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[skill/abbr]',inline=False)
				embed.add_field(name='Description',value='List name, type, tier and effect of the requested commander skill',inline=False)
			elif command == 'map':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[map_name]',inline=False)
				embed.add_field(name='Description',value='List name and display the map of the requested map',inline=False)
			elif command == 'whoami':
				embed.add_field(name='Usage',value=command_header+token+command,inline=False)
				embed.add_field(name='Description',value='Who\'s this bot?',inline=False)
			elif command == 'list':
				if len(arg) == 3:
					embed.add_field(name='Usage',value=command_header+token+command+token+"[skills/upgrades/commanders/flags]",inline=False)
					embed.add_field(name='Description',value=f'Select a category to list all items of the requested category. type **{command_header+token+command+token} [skills/upgrades/commanders]** for help on the category.{chr(10)}'+
						'**skills**: List all skills.\n'+
						'**upgrades**: List all upgrades.\n'+
						'**commanders**: List all commanders.\n'+
						'**flags**: List all non-special flags.\n',inline=False)
				else:
					if arg[3] == 'skills':
						embed.add_field(name='Usage',value=command_header+token+command+token+"skills"+token+"[type/tier] [type_name/tier_number]",inline=False)
						embed.add_field(name='Description',value='List name and the abbreviation of all commander skills.\n'+
						'**type [type_name]**: Optional. Returns all skills of indicated skill type. Acceptable values: **[Attack, Endurance, Support, Versatility]**\n'+
						'**tier [tier_number]**: Optional. Returns all skills of the indicated tier. Acceptable values: **[1,2,3,4]**',inline=False)
					elif arg[3] == 'upgrades':
						embed.add_field(name='Usage',value=command_header+token+command+token+"upgrades"+token+"[queries]",inline=False)
						embed.add_field(name='Description',value='List name and the abbreviation of all upgrades.\n'+
							f'**[queries]**: Search queries for upgrades (Examples: secondary, torpedoes, slot 4',inline=False)
					elif arg[3] == 'commanders':
						embed.add_field(name='Usage',value=command_header+token+command+token+"commanders"+token+"[page_number/nation]",inline=False)
						embed.add_field(name='Description',value='List names of all unique commanders.\n'+
							f'**[page_number]** Required. Select a page number to list commanders.\n'+
							f'**[nation]** Required. Select a nation to filter. Acceptable values: **[{"".join([nation_dictionary[i]+", " for i in nation_dictionary][:-3])}]**',inline=False)
					elif arg[3] == 'flags':
						embed.add_field(name='Usage',value=command_header+token+command+token+"flags",inline=False)
						embed.add_field(name='Description',value='List names of all signal flags.\n',inline=False)
					elif arg[3] == 'maps':
						embed.add_field(name='Usage',value=command_header+token+command+token+"maps"+token+"[page_num]",inline=False)
						embed.add_field(name='Description',value='List names of all maps.\n'+
							f'**[page_number]** Required. Select a page number to list maps.\n',inline=False)
					elif arg[3] == 'ships':
						tag_helps = set(arg[4:]) & set(SHIP_TAG_LIST)
						add_help_string = ""
						if len(tag_helps) == 0:
							help_desc = [i for i in SHIP_TAG_LIST]
							help_desc += ['tier', 'battleships', 'cruisers', 'destroyers', 'aircraft carriers']
							add_help_string += "Tags available: " + ''.join([i+', ' for i in help_desc])[:-2]
						else:
							help_desc = [f"**{i}**: {ship_tags[i]['description']}" for i in tag_helps]
							add_help_string += "Requested tags:\n" + ''.join([i+'\n' for i in help_desc])[:-1]
						
						embed.add_field(name='Usage',value=command_header+token+command+token+"ships"+token+"[search tags]\n",inline=False)
						embed.add_field(name='Description',value='List all available ships with the tags provided.\n' + add_help_string,inline=False)
					else:
						embed.add_field(name='Error',value="Invalid command.",inline=False)
						 
			elif command == 'upgrade':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[upgrade/abbr/ship_name]',inline=False)
				embed.add_field(name='Description',value='List the name and description of the requested warship upgrade'+
					'**[upgrade/abbr/ship_name]**: Required.\n*upgrade/abbr*: Provide the name or the abbreviation name of the upgrade to get information on it.\n'
					'*ship_name*. Provide the ship name to return the legendary upgrade for that ship.',inline=False)
			elif command == 'commander':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[cmdr_name]',inline=False)
				embed.add_field(name='Description',value='List the nationality of the requested commander',inline=False)
			elif command == 'flag':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[flag_name]',inline=False)
				embed.add_field(name='Description',value='List the name and description of the requested signal flag',inline=False)
			elif command == 'feedback':
				embed.add_field(name='Usage',value=command_header+token+command,inline=False)
				embed.add_field(name='Description',value='Send a feedback form link for mackbot.',inline=False)
			elif command == 'doubloons':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[doubloons]'+token+'[dollar/$]',inline=False)
				embed.add_field(name='Description',value='Returns the price in dollars of now much of the requested number of doubloons\n'+
					"**[dollars/$]**: Optional. Reverse the conversion to dollars to doublons.",inline=False)
		else:
			embed.add_field(name='Error',value="Invalid command.",inline=False)
		return embed
	async def help(self, message, arg):
		# send help message
		channel = message.channel
		embed = self.help_message(message.content)
		if not embed is None:
			logging.info(f"sending help message for command <{command_list[0]}>")
			await channel.send(embed=embed)
	async def whoami(self,message, arg):
		channel = message.channel
		async with channel.typing():
			m = "I'm a bot made by mackwafang#2071 to help players with clan build. I also includes the WoWS Encyclopedia!"
		await channel.send(m)
	async def goodbot(self, message, arg):
		channel = message.channel
		# good bot
		r = randint(len(good_bot_messages))
		logging.info(f"send reply message for {command_list[1]}")
		await channel.send(good_bot_messages[r]) # block until message is sent
	async def feedback(self, message, arg):
		channel = message.channel
		logging.info("send feedback link")
		await channel.send(f"Need to rage at mack because he ~~fucks up~~ did goofed on a feature? Submit a feedback form here!\nhttps://forms.gle/Lqm9bU5wbtNkpKSn7")
	async def build(self, message, arg):
		channel = message.channel
		# get voted ship build
		# message parse
		ship_found = False
		if len(arg) <= 2:
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			requested_image = arg[-1].lower() == 'image'
			if requested_image:
				arg = arg[:-1]
			battle_type = arg[2] # assuming build battle type is provided
			if battle_type.lower() in build_battle_type_value:
				# 2nd argument provided is a known argument
				ship = ''.join([i+' ' for i in arg[3:]])[:-1] # grab ship name
			else:
				battle_type = 'casual'
				ship = ''.join([i+' ' for i in arg[2:]])[:-1] # grab ship name
			if requested_image:
				# try to get image format for this build
				async with channel.typing():
					try:
						name, nation, images, ship_type, tier, _, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_build_data(ship, battle_type=battle_type)
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
							await channel.send(m, file=discord.File(filename))
						else:
							# does not exists
							await channel.send(f"An Image build for {name} does not exists. Sending normal message.")
							await self.build(message, arg)
						
					except Exception as e:
						logging.info(f"Exception {type(e)}", e)
						if type(e) == discord.errors.Forbidden:
							await channel.send(f"I need the **Attach Files Permission** to use this feature!")
							await self.build(message, arg)
						else:
							await channel.send(f"Ship **{ship}** is not understood")
			else:
				# get text-based format build
				try:
					async with channel.typing():
						name, nation, images, ship_type, tier, _, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_build_data(ship, battle_type=battle_type)
						logging.info(f"returning build information for <{name}> in embeded format")
						ship_type = ship_types[ship_type] #convert weegee ship type to hull classifications
						embed = discord.Embed(title=f"{battle_type.title()} Build for {name}", description='')
						embed.set_thumbnail(url=images['small'])
						# get server emoji
						if message.guild is not None:
							server_emojis = message.guild.emojis
						else:
							server_emojis = []
						
						tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
						
						embed.description += f'**Tier {tier_string} {nation_dictionary[nation]} {"Premium "+ship_type if is_prem else ship_type}**'
						
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
										try: # ew, nested try/catch
											upgrade_name = get_upgrade_data(upgrade)[1]
										except Exception as e: 
											logging.info(f"Exception {type(e)}", e, f"in ship, listing upgrade {i}")
											error_value_found = True
											upgrade_name = upgrade+":warning:"
									m += f'(Slot {i}) **'+upgrade_name+'**\n'
									i += 1
								footer_message += "**use mackbot list [upgrade] for desired info on upgrade**\n"
								embed.add_field(name='Suggested Upgrades', value=m,inline=False)
							else:
								embed.add_field(name='Suggested Upgrades', value="Coming Soon:tm:",inline=False)
							# suggested skills
							if len(skills) > 0:
								m = ""
								i = 1
								for skill in skills:
									skill_name = "[Missing]"
									try: # ew, nested try/catch
										skill_name, id, skill_type, perk, tier, icon = get_skill_data(skill)
									except Exception as e: 
										logging.info(f"Exception {type(e)}", e, f"in ship, listing skill {i}")
										error_value_found = True
										skill_name = skill+":warning:"
									m += f'(Tier {tier}) **'+skill_name+'**\n'
									i += 1
								footer_message += "**use mackbot skill [skill] for desired info on desired skill**\n"
								embed.add_field(name='Suggested Cmdr. Skills', value=m,inline=False)
							else:
								embed.add_field(name='Suggested Cmdr. Skills', value="Coming Soon:tm:",inline=False)
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
								embed.add_field(name='Suggested Cmdr.', value="Coming Soon:tm:",inline=False)
							footer_message += f"For {'casual' if battle_type == 'competitive' else 'competitive'} builds, use [mackbot build {'casual' if battle_type == 'competitive' else 'competitive'} {ship}]\n"
						else:
							m = "mackbot does not know any build for this ship :("
							u, c, s = get_build_data(ship, battle_type='casual' if battle_type == 'competitive' else 'competitive')[-4:-1]
							if len(u) > 0 and len(c) > 0 and len(s) > 0:
								m += '\n\n'
								m += f"But, There is a {'casual' if battle_type == 'competitive' else 'competitive'} build for this ship!\n"
								m += f"Use [**mackbot build {'casual' if battle_type == 'competitive' else 'competitive'} {ship}**]"
							embed.add_field(name=f'No known {battle_type} build', value=m,inline=False)
					error_footer_message = ""
					if error_value_found:
						error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact mackwafang#2071.\n"
					embed.set_footer(text=error_footer_message+footer_message)
					await channel.send(embed=embed)
				except Exception as e:
					logging.info(f"Exception {type(e)}", e)
					# error, ship name not understood
					ship_name_list = [ship_list[i]['name'] for i in ship_list]
					closest_match = difflib.get_close_matches(ship, ship_name_list)
					closest_match_string = ""
					if len(closest_match) > 0:
						closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
					
					await channel.send(f"Ship **{ship}** is not understood" + closest_match_string)
	async def ship(self, message, arg):
		channel = message.channel
		# message parse
		ship_found = False
		if len(arg) <= 2:
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			arg = ''.join([i+' ' for i in arg]) # fuse back together to check filter
			has_filter = '(' in arg and ')' in arg # find a better check
			param_filter = ''
			if has_filter:
				param_filter = arg[arg.find('(')+1 : arg.rfind(')')]
				arg = arg[:arg.find('(')-1]
			arg = arg.split(' ')
			ship = ''.join([i+' ' for i in arg[2:]])[:-1] # grab ship name
			if not param_filter:
				ship = ship[:-1]

			try:
				async with channel.typing():
					ship_param = get_ship_data(ship)
					name, nation, images, ship_type, tier, consumables, modules, _, is_prem, _, _, _, _, _ = get_build_data(ship)
					logging.info(f"returning ship information for <{name}> in embeded format")
					ship_type = ship_types[ship_type]
					
					if ship_type == 'Cruiser':
						highest_caliber = sorted(modules['artillery'], key=lambda x : module_list[str(x)]['profile']['artillery']['caliber'], reverse=True)
						highest_caliber = [module_list[str(i)]['profile']['artillery']['caliber'] for i in highest_caliber][0] * 1000
						
						print(highest_caliber)
						if (highest_caliber <= 155):
							ship_type = "Light Cruiser"
						elif (highest_caliber <= 203):
							ship_type = "Heavy Cruiser"
						else:
							ship_type = "Battlecruiser"
					embed = discord.Embed(title=f"{ship_type} {name}", description='')
					embed.set_thumbnail(url=images['small'])
					# get server emoji
					if message.guild is not None:
						server_emojis = message.guild.emojis
					else:
						server_emojis = []
					
					# emoji exists!
					tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
					
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
					
					ship_filter = 0b11111111111 # assuming no filter is provided, display all
					# grab filters
					if len(param_filter) > 0:
						ship_filter = 0b00000000000 # filter is requested, set disable all
						# s = ship_param_filter_regex.findall(''.join([i + ' ' for i in param_filter]))
						s = ship_param_filter_regex.findall(param_filter) # what am i looking for?
						is_filter_requested = lambda x: 1 if len([i[x] for i in s if len(i[x]) > 0]) > 0 else 0 # lambda function. check length of regex capture groups. if len > 0, request is valid
						# slot = ''.join([i[1] for i in s]) # wtf is this. too scared to remove
						# enables proper filter
						ship_filter |= is_filter_requested(1) << hull_filter
						ship_filter |= is_filter_requested(2) << guns_filter
						ship_filter |= is_filter_requested(3) << atbas_filter
						ship_filter |= is_filter_requested(4) << torps_filter
						ship_filter |= (is_filter_requested(4) & is_filter_requested(5)) << torpbomber_filter
						ship_filter |= is_filter_requested(6) << bomber_filter
						ship_filter |= is_filter_requested(7) << rockets_filter
						ship_filter |= is_filter_requested(8) << engine_filter
						ship_filter |= is_filter_requested(9) << aa_filter
						ship_filter |= is_filter_requested(10) << conceal_filter
						ship_filter |= is_filter_requested(11) << consumable_filter
						del is_filter_requested
						
					embed.description += f'**Tier {tier_string} {nation_dictionary[nation]} {"Premium "+ship_type if is_prem else ship_type}**\n'
					
					footer_message = ""
					embed.description += f"Matchmaking tier {ship_param['battle_level_range_min']} - {ship_param['battle_level_range_max']}"
					
					is_filtered = lambda x: (ship_filter >> x) & 1 == 1
					
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
							if ship_param['armour']['flood_damage'] > 0 or ship_param['armour']['flood_prob'] > 0:
								m += '\n'
								if ship_param['armour']['flood_damage'] > 0:
									m += f"**Torp. Damage**: -{ship_param['armour']['flood_damage']}%\n"
								if ship_param['armour']['flood_prob'] > 0:
									m += f"**Flood Chance**: -{ship_param['armour']['flood_prob']}%\n"
							
							m += '\n'
						embed.add_field(name="__**Hull**__", value=m, inline=False)
						
					if len(modules['artillery']) > 0 and is_filtered(guns_filter):
						m = ""
						m += f"**Range: **"
						for fc in sorted(modules['fire_control'], key=lambda x: module_list[str(x)]['profile']['fire_control']['distance']):
							m += f"{module_list[str(fc)]['profile']['fire_control']['distance']} - "
						m = m[:-2]
						m += "km\n"
						for h in sorted(modules['artillery'], key=lambda x: module_list[str(x)]['name']):
							guns = module_list[str(h)]['profile']['artillery']
							m += f"**{module_list[str(h)]['name'].replace(chr(10),' ')} ({int(guns['numBarrels'])} barrel{'s' if guns['numBarrels'] > 1 else ''}):**\n"
							if guns['max_damage_HE']:
								m += f"**HE:** {guns['max_damage_HE']} (:fire: {guns['burn_probability']}%)\n"
							if 'max_damage_SAP' in guns:
								m += f"**SAP:** {guns['max_damage_SAP']}\n"
							if guns['max_damage_AP']:
								m += f"**AP:** {guns['max_damage_AP']}\n"
							m += f"**Reload:** {60/guns['gun_rate']:0.1f}s\n"
							
							m += '\n'
						embed.add_field(name="__**Main Battery**__", value=m, inline=False)
					if ship_param['atbas'] is not None and is_filtered(atbas_filter):
						m = ""
						m += f"**Range:** {ship_param['atbas']['distance']} km\n"
						for slot in ship_param['atbas']['slots']:
							guns = ship_param['atbas']['slots'][slot]
							m += f"**{guns['name'].replace(chr(10),' ')} :**\n"
							if guns['damage'] > 0:
								m += f"**HE:** {guns['damage']}\n"
							m += f"**Reload:** {guns['shot_delay']}s\n"
							
							m += '\n'
						embed.add_field(name="__**Secondary Battery**__", value=m, inline=False)
					if len(modules['torpedoes']) > 0 and is_filtered(torps_filter):
						m = ""
						for h in sorted(modules['torpedoes'], key=lambda x: module_list[str(x)]['name']):
							torps = module_list[str(h)]['profile']['torpedoes']
							m += f"**{module_list[str(h)]['name'].replace(chr(10),' ')} ({torps['distance']} km, {int(torps['numBarrels'])} tube{'s' if torps['numBarrels'] > 1 else ''}):**\n"
							m += f"**Damage:** {torps['max_damage']}, "
							m += f"{torps['torpedo_speed']} kts.\n"
							
							m += '\n'
						embed.add_field(name="__**Torpedoes**__", value=m, inline=False)
					if len(modules['fighter']) > 0 and is_filtered(rockets_filter):
						m = ""
						for h in sorted(modules['fighter'], key=lambda x: module_list[str(x)]['profile']['fighter']['max_health']):
							fighter_module = module_list[str(h)]
							fighter = module_list[str(h)]['profile']['fighter']
							n_attacks = fighter_module['squad_size']//fighter_module['attack_size']
							m += f"**{module_list[str(h)]['name'].replace(chr(10),' ')} ({fighter['max_health']} HP)**\n"
							m += f"**Aircraft:** {fighter['cruise_speed']} kts, {fighter_module['payload']} rocket{'s' if fighter_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {fighter_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {fighter_module['attack_size']})\n"
							m += f"**Rocket:** :boom:{fighter['max_damage']} {'(:fire:'+str(fighter['rocket_burn_probability'])+'%)' if fighter['rocket_burn_probability'] > 0 else ''}\n"
							
							m += '\n'
						embed.add_field(name="__**Attackers**__", value=m, inline=False)
					if len(modules['torpedo_bomber']) > 0 and is_filtered(torpbomber_filter):
						m = ""
						for h in sorted(modules['torpedo_bomber'], key=lambda x: module_list[str(x)]['profile']['torpedo_bomber']['max_health']):
							bomber_module = module_list[str(h)]
							bomber = module_list[str(h)]['profile']['torpedo_bomber']
							n_attacks = bomber_module['squad_size']//bomber_module['attack_size']
							m += f"**{module_list[str(h)]['name'].replace(chr(10),' ')} ({bomber['max_health']} HP)**\n"
							m += f"**Aircraft:** {bomber['cruise_speed']} kts, {bomber_module['payload']} torpedo{'es' if bomber_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
							m += f"**Torpedo:** :boom:{bomber['max_damage']}, {bomber['torpedo_max_speed']} kts\n"
							
							m += '\n'
						embed.add_field(name="__**Torpedo Bomber**__", value=m, inline=False)
					if len(modules['dive_bomber']) > 0 and is_filtered(bomber_filter):
						m = ""
						for h in sorted(modules['dive_bomber'], key=lambda x: module_list[str(x)]['profile']['dive_bomber']['max_health']):
							bomber_module = module_list[str(h)]
							bomber = module_list[str(h)]['profile']['dive_bomber']
							n_attacks = bomber_module['squad_size']//bomber_module['attack_size']
							m += f"**{module_list[str(h)]['name'].replace(chr(10),' ')} ({bomber['max_health']} HP)**\n"
							m += f"**Aircraft:** {bomber['cruise_speed']} kts, {bomber_module['payload']} bomb{'s' if bomber_module['payload'] > 1 else ''}\n"
							m += f"**Squadron:** {bomber_module['squad_size']} aircrafts ({n_attacks} flight{'s' if n_attacks > 1 else ''} of {bomber_module['attack_size']})\n"
							m += f"**Bomb:** :boom:{bomber['max_damage']} {'(:fire:'+str(bomber['bomb_burn_probability'])+'%)' if bomber['bomb_burn_probability'] > 0 else ''}\n"
							
							m += '\n'
						embed.add_field(name="__**Bombers**__", value=m, inline=False)
					if len(modules['engine']) > 0 and is_filtered(engine_filter):
						m = ""
						for e in sorted(modules['engine'], key=lambda x: module_list[str(x)]['name']):
							engine = module_list[str(e)]['profile']['engine']
							m += f"**{module_list[str(e)]['name']}**: {engine['max_speed']} kts\n"
							m += '\n'
						embed.add_field(name="__**Engine**__", value=m, inline=True)
					if ship_param['concealment'] is not None and is_filtered(conceal_filter):
						m = ""
						m += f"**By Sea**: {ship_param['concealment']['detect_distance_by_ship']} km\n"
						m += f"**By Air**: {ship_param['concealment']['detect_distance_by_plane']} km\n"
						embed.add_field(name="__**Concealment**__", value=m, inline=True)
					if len(consumables) > 0 and is_filtered(consumable_filter):
						m = ""
						for consumable_slot in consumables:
							if (len(consumables[consumable_slot]['abils']) > 0):
								m += f"**Slot {consumables[consumable_slot]['slot']+1}:**"
								if len(consumables[consumable_slot]['abils']) > 1:
									m += " (Choose one)"
								m += '\n'
								for c in consumables[consumable_slot]['abils']:
									consumable_id, consumable_type = c
									consumable = game_data[find_game_data_item(consumable_id)[0]][consumable_type]
									consumable_name = consumable_descriptor[consumable['consumableType']]['name']
									consumable_description = consumable_descriptor[consumable['consumableType']]['description']
									consumable_type = consumable["consumableType"]
									
									charges = 'Infinite' if consumable['numConsumables'] < 0 else consumable['numConsumables'] 
									action_time = consumable['workTime']
									cd_time = consumable['reloadTime']
									consumable_detail = ""
									if consumable_type == 'airDefenseDisp':
										consumable_detail = f'Continous AA damage: +{consumable["areaDamageMultiplier"]*100:0.0f}%\nFlak damage: +{consumable["bubbleDamageMultiplier"]*100:0.0f}%'
									if consumable_type == 'artilleryBoosters':
										consumable_detail = f'Reload Time: -50%'
									if consumable_type == 'regenCrew':
										consumable_detail = f'Repairs {consumable["regenerationHPSpeed"]*100}% of max HP / sec.\n'
										for h in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name']):
											hull = module_list[str(h)]['profile']['hull']
											consumable_detail += f"{module_list[str(h)]['name']} ({hull['health']} HP): {int(hull['health'] * consumable['regenerationHPSpeed'])} HP / sec., {int(hull['health'] * consumable['regenerationHPSpeed'] * consumable['workTime'])} HP\n"
									if consumable_type == 'rls':
										consumable_detail = f'Range: {round(consumable["distShip"] / 3) / 10:0.1f} km'
									if consumable_type == 'scout':
										consumable_detail = f'Main Battery firing range: +{(consumable["artilleryDistCoeff"] - 1) * 100:0.0f}%'
									if consumable_type == 'smokeGenerator':
										consumable_detail = f'Smoke lasts {str(int(consumable["lifeTime"] // 60))+"m" if consumable["lifeTime"] >= 60 else ""} {str(int(consumable["lifeTime"] % 60))+"s" if consumable["lifeTime"] % 60 > 0 else ""}\nSmoke radius: {consumable["radius"] * 10} meters\nConceal user up to {consumable["speedLimit"]} knots while active.'
									if consumable_type == 'sonar':
										consumable_detail = f'Assured Ship Range: {round(consumable["distShip"] / 3) / 10:0.1f}km\nAssured Torp. Range: {round(consumable["distTorpedo"] / 3) / 10:0.1f} km'
									if consumable_type == 'speedBoosters':
										consumable_detail = f'Max Speed: +{consumable["boostCoeff"]*100:0.0f}%'
									if consumable_type == 'torpedoReloader':
										consumable_detail = f'Torpedo Reload Time lowered to {consumable["torpedoReloadTime"]:1.0f}s'
									
									m += f"**{consumable_name}**\n"
									if ship_filter == 2 ** (consumable_filter):
										m += f"{charges} charge{'s' if charges != 1 else ''}, "
										m += f"{f'{action_time // 60:1.0f}m ' if action_time >= 60 else ''} {str(int(action_time % 60))+'s' if action_time % 60 > 0 else ''} duration, "
										m += f"{f'{cd_time // 60:1.0f}m ' if cd_time >= 60 else ''} {str(int(cd_time % 60))+'s' if cd_time % 60 > 0 else ''} cooldown.\n"
										if len(consumable_detail) > 0:
											m += consumable_detail
											m += '\n'
								m += '\n'
						embed.add_field(name="__**Consumables**__", value=m, inline=False)
					embed.set_footer(text="Parameters does not take into account upgrades and commander skills\n"+
						f"For specific parameters, use [mackbot ship {ship} (parameters)]\n"+
						f"For detailed information for this ship's consumables, use [mackbot ship {ship} (consumables)]")
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				# error, ship name not understood
				ship_name_list = [ship_list[i]['name'] for i in ship_list]
				closest_match = difflib.get_close_matches(ship, ship_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
				
				await channel.send(f"Ship **{ship}** is not understood" + closest_match_string)
	async def skill(self, message, arg):
		channel = message.channel
		# get information on requested skill
		message_string = message.content
		skill_found = False
		# message parse
		skill = ''.join([i+' ' for i in arg[2:]])[:-1] #message_string[message_string.rfind('-')+1:]
		if len(arg) <= 2:
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			try:
				logging.info(f'sending message for skill <{skill}>')
				async with channel.typing():
					name, id, skill_type, perk, tier, icon = get_skill_data(skill)
					embed = discord.Embed(title="Commander Skill", description="")
					embed.set_thumbnail(url=icon)
					embed.description += f"**{name}**\n"
					embed.description += f"**Tier {tier} {skill_type} Skill**"
					embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk) if len(perk) != 0 else '')
				await channel.send(embed=embed)
			except Exception as e:
				logging.info("Exception", type(e), ":", e)
				# error, ship name not understood
				skill_name_list = [skill_list[i]['name'] for i in skill_list]
				closest_match = difflib.get_close_matches(skill, skill_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
				
				await channel.send(f"Skill **{skill}** is not understood." + closest_match_string)
	async def list(self, message, arg):
		channel = message.channel
		# list command
		m = []
		embed = discord.Embed()
		send_help_message = False
		error_message = ""
		async with channel.typing():
			if len(arg) > 2:
				if arg[2] == 'skills':
					# list all skills
					if len(arg) == 3:
						# did not provide a filter, send all skills
						embed = discord.Embed(name="Commander Skill")
						m = ["**"+skill_list[i]['name']+'** ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list]
						m.sort()
						m = [m[i:i+10] for i in range(0,len(m),10)]
						for i in m:
							embed.add_field(name="Skill (Abbr.)",value=''.join([v for v in i]))
					elif len(arg) > 3:
						# asking for specific category
						if arg[3] == 'type':
							# get all skills of this type
							try:
								skill_type = arg[4] # get type
								embed = discord.Embed(name=f"{skill_type} Commander Skill")
								m = [f"(Tier {skill_list[i]['tier']}) **"+skill_list[i]['name']+'** ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['type_name'].lower() == skill_type.lower()]
								m.sort()
								m = ''.join([i for i in m])
								embed.add_field(name="(Tier) Skill (Abbr.)",value=m)
								message_success = True
							except Exception as e:
								embed = None
								logging.info(e, end='')
								if type(e) == IndexError:
									error_message = f"Please specify a skill type! Acceptable values: [Attack, Endurance, Support, Versatility]"
								else:
									logging.info(f"Skill listing argument <{arg[4]}> is invalid.")
									error_message = f"Value {arg[4]} is not understood"
						elif arg[3] == 'tier':
							# get all skills of this tier
							try:
								tier = int(arg[4]) # get tier number
								embed = discord.Embed(name=f"Tier {tier} Commander Skill")
								m = [f"({skill_list[i]['type_name']}) **"+skill_list[i]['name']+'** ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['tier'] == tier]
								m.sort()
								m = ''.join([i for i in m])
								embed.add_field(name="(Category) Skill (Abbr.)",value=m)
								message_success = True
							except Exception as e:
								embed = None
								if type(e) == IndexError:
									error_message = f"Please specify a skill tier! Acceptable values: [1,2,3,4]"
								else:
									logging.info(f"Skill listing argument <{arg[4]}> is invalid.")
									error_message = f"Value {arg[4]} is not understood"
						else:
							# not a known argument
							logging.info(f"{arg[3]} is not a known argument for command {arg[2]}.")
							embed = None
							error_message = f"Argument **{arg[3]}** is not a valid argument."
							return

				elif arg[2] == 'upgrades':
					# list all upgrades
					if len(arg) == 3:
						embed = self.help_message(command_header+token+"help"+token+arg[1]+token+"upgrades")
						send_help_message = True
					elif len(arg) > 3:
						# list upgrades
						try:
							# parsing search parameters
							logging.info("starting parameters parsing")
							search_param = arg[3:]
							s = equip_regex.findall(''.join([i + ' ' for i in search_param]))
							
							slot = ''.join([i[1] for i in s])
							key = [i[7] for i in s if len(i[7]) > 1]
							page = [i[6] for i in s if len(i[6]) > 1]
							tier = [i[3] for i in s if len(i[3]) > 1]
							embed_title = "Search result for: "
							
							try:
								page = int(page[0])-1
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
							embed_title += f"{''.join([i.title()+' ' for i in key])}"
							# look up
							result = []
							for u in upgrade_list:
								tags = [i.lower() for i in upgrade_list[u]['tags']]
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
								m = [m[i:i+items_per_page] for i in range(0,len(result),items_per_page)] # splitting into pages
								
								
								embed = discord.Embed(title=embed_title+f"({page+1}/{num_pages+1})")
								m = m[page] # select page
								m = [m[i:i+items_per_page//2] for i in range(0,len(m),items_per_page//2)] # spliting into columns
								embed.set_footer(text=f"{num_items} upgrades found.\nFor more information on an upgrade, use [{command_header} upgrade [name/abbreviation]]")
								for i in m:
									embed.add_field(name="Upgrade (abbr.)", value=''.join([v+'\n' for v in i]))
							else:
								embed = discord.Embed(title=embed_title, description="")
								embed.description = "No upgrades found"
						except Exception as e:
							if type(e) == IndexError:
									embed = None
									error_message = f"Page {page+1} does not exists"
							elif type(e) == ValueError:
								logging.info(f"Upgrade listing argument <{arg[3]}> is invalid.")
								error_message = f"Value {arg[3]} is not understood"
							else:
								logging.info(f"Exception {type(e)}", e)
				
				elif arg[2] == 'maps':
					# list all maps
					if len(arg) == 3:
						embed = self.help_message(command_header+token+"help"+token+arg[1]+token+"maps")
						send_help_message = True
					elif len(arg) > 3:
						# list upgrades
						try:
							logging.info("sending list of maps")
							page = int(arg[3])-1
							m = [f"{map_list[i]['name']}" for i in map_list]
							m.sort()
							items_per_page = 20
							num_pages = (len(map_list) // items_per_page)
							
							m = [m[i:i+items_per_page] for i in range(0,len(map_list),items_per_page)] # splitting into pages
							embed = discord.Embed(title="Map List "+f"({page+1}/{num_pages+1})")
							m = m[page] # select page
							m = [m[i:i+items_per_page//2] for i in range(0,len(m),items_per_page//2)] # spliting into columns
							for i in m:
								embed.add_field(name="Map", value=''.join([v+'\n' for v in i]))
						except Exception as e:
							if type(e) == IndexError:
									embed = None
									error_message = f"Page {page+1} does not exists"
							elif type(e) == ValueError:
								logging.info(f"Upgrade listing argument <{arg[3]}> is invalid.")
								error_message = f"Value {arg[3]} is not understood"
							else:
								logging.info(f"Exception {type(e)}", e)
				
				elif arg[2] == 'ships':
					if message.guild is not None:
						server_emojis = message.guild.emojis
					else:
						server_emojis = []
					message_success = False
					if len(arg) == 3:
						embed = self.help_message(command_header+token+"help"+token+arg[1]+token+"ships")
						send_help_message = True
					elif len(arg) > 3:
						# parsing search parameters
						logging.info("starting parameters parsing")
						search_param = arg[3:]
						s = ship_list_regex.findall(''.join([str(i) + ' ' for i in search_param])[:-1])
						
						tier = ''.join([i[2] for i in s])
						key = [i[7] for i in s if len(i[7]) > 1]
						page = [i[6] for i in s if len(i[6]) > 0]
						embed_title = "Search result for: "
						
						try:
							page = int(page[0])-1
						except:
							page = 0
							
						if len(tier) > 0:
							if tier in roman_numeral:
								tier = roman_numeral[tier]
							tier = f't{tier}'
							key += [tier]
						key = [i for i in key if not 'page' in i]
						embed_title += f"{''.join([i.title()+' ' for i in key])}"
						# look up
						result = []
						for s in ship_list:
							tags = [i.lower() for i in ship_list[s]['tags']]
							if np.all([k.lower() in tags for k in key]):
								result += [s]
						logging.info("parsing complete")
						logging.info("compiling message")
						m = []
						if len(result) > 0:
							for ship in result:
								name, _, _, ship_type, tier, _, _,  _, is_prem, _, _, _, _, _ = get_build_data(ship_list[ship]['name'])
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
								if len(type_icon) == 0:
									type_icon = "["+ship_type_to_hull_class[ship_type]+"]"
								m += [f"**{tier_string:<4} {type_icon}** {name}"]
								
							num_items = len(m)
							m.sort()
							items_per_page = 30
							num_pages = (len(m) // items_per_page)
							m = [m[i:i+items_per_page] for i in range(0,len(result),items_per_page)] # splitting into pages
							
							
							embed = discord.Embed(title=embed_title+f"({page+1}/{num_pages+1})")
							m = m[page] # select page
							m = [m[i:i+items_per_page//2] for i in range(0,len(m),items_per_page//2)] # spliting into columns
							embed.set_footer(text=f"{num_items} ships found\nTo get ship build, use [{command_header} build [ship_name]]")
							for i in m:
								embed.add_field(name="(Tier) Ship", value=''.join([v+'\n' for v in i]))
						else:
							embed = discord.Embed(title=embed_title, description="")
							embed.description = "**No ships found**"
								
				elif arg[2] == 'commanders':
					# list all unique commanders
					message_success = False
					if len(arg) == 3:
						embed = self.help_message(command_header+token+"help"+token+arg[1]+token+"commanders")
						send_help_message = True
					elif len(arg) > 3:
						# list commanders by page
						try:
							logging.info("sending list of commanders")
							page = int(arg[3])-1
							m = [f"({nation_dictionary[cmdr_list[cmdr]['nation']]}) **{cmdr_list[cmdr]['first_names'][0]}**" for cmdr in cmdr_list if cmdr_list[cmdr]['last_names'] == []]
							num_items = len(m)
							m.sort()
							items_per_page = 20
							num_pages = (len(cmdr_list) // items_per_page)
							m = [m[i:i+items_per_page] for i in range(0,len(cmdr_list),items_per_page)] # splits into pages
							embed = discord.Embed(title=f"Commanders ({page+1}/{num_pages})")
							m = m[page] #grab desired page
							m = [m[i:i+items_per_page//2] for i in range(0,len(m),items_per_page//2)] # spliting into columns
							
							embed.set_footer(text=f"{num_items} commanders found")
							for i in m:
								embed.add_field(name="(Nation) Name",value=''.join([v+'\n' for v in i]))
							if 0 > page and page > num_pages:
								embed = None
								error_message = f"Page {page+1} does not exists"
							else:
								message_success = True
						except Exception as e:
							if type(e) == ValueError:
								pass
							else:
								logging.info(f"Exception {type(e)}",e)
						# list commanders by nationality
						if not message_success and error_message == "": #page not listed
							try:
								nation = ''.join([i+' ' for i in arg[3:]])[:-1]
								embed = discord.Embed(title=f"{nation.title() if nation.lower() != 'us' else 'US'} Commanders")
								m = [cmdr_list[cmdr]['first_names'][0] for cmdr in cmdr_list if nation_dictionary[cmdr_list[cmdr]['nation']].lower() == nation.lower()] 
								num_items = len(m)
								m.sort()
								m = [m[i:i+10] for i in range(0,len(m),10)] # splits into columns of 10 items each
								embed.set_footer(text=f"{num_items} commanders found")
								for i in m:
									embed.add_field(name="Name",value=''.join([v+'\n' for v in i]))
								
							except Exception as e:
								logging.info(f"Exception {type(e)}", e)
								
				elif arg[2] == 'flags':
					# list all flags
					if len(arg) == 3:
						# list upgrades
						try:
							embed = discord.Embed(title="Signal Flags")
							output_list = [flag_list[i]['name']+'\n' for i in flag_list]
							output_list.sort()
							items_per_page = 10
							m = output_list
							embed.add_field(name="Flag",value=''.join([i for i in m]))
						except Exception as e:
							# print(f"Flag listing argument <{arg[3]}> is invalid.")
							error_message = f"Internal Exception {type(e)} (X_X)"
				
				else:
					# something else detected
					logging.info(f"{arg[2]} is not a known argument for command {arg[1]}.")
					embed = None
					error_message = f"Argument **{arg[2]}** is not a valid argument."
			else:
				# no arugments listed, show help message
				send_help_message = True
				embed = self.help_message(command_header+token+"help"+token+arg[1])
		if not embed == None:
			# if not send_help_message:
				# m.sort()
				# m = ''.join(m)
				# embed.add_field(name='_',value=m,inline=True)
			await channel.send(embed=embed)
		else:
			if error_message == "":
				error_message = f"Embed message for command {arg[1]} is empty! arg list: {arg}"
			await channel.send(error_message)
	async def upgrade(self, message, arg):
		channel = message.channel
		# get information on requested upgrade
		message_string = message.content
		upgrade_found = False
		# message parse
		upgrade = ''.join([i+' ' for i in arg[2:]])[:-1]  # message_string[message_string.rfind('-')+1:]
		if len(arg) <= 2:
			# argument is empty, send help message
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			# user provided an argument
			
			search_func = None
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
				profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships = search_func(upgrade)
				embed_title = 'Ship Upgrade'
				if 'legendary' in is_special:
					embed_title = "Legendary Ship Upgrade"
				elif 'coal' in is_special:
					embed_title = "Coal Ship Upgrade"
				embed = discord.Embed(title=embed_title, description="")
				embed.set_thumbnail(url=image)
				#embed.add_field(name='Name', value=name)
				if len(name) > 0:
					embed.description += f"**{name}**\n"
				else:
					logging.info("name is empty")
				if len(slot) > 0:
					embed.description += f"**Slot {slot}**\n"
				else:
					logging.info("slot is empty")
				if len(description) > 0:
					embed.add_field(name='Description',value=description, inline=False)
				else:
					logging.info("description field empty")
				if len(profile) > 0:
					embed.add_field(name='Effect',value=''.join([profile[detail]['description']+'\n' for detail in profile]), inline=False)
				else:
					logging.info("effect field empty")
				if len(ship_restriction) > 0:
					m = ''.join([i+', ' for i in sorted(ship_restriction)])[:-2]
					if len(m) > 0:
						embed.add_field(name="Ships",value=m)
					else:
						logging.warning('Ships field is empty')
				print(on_other_ships)
				if len(on_other_ships) > 0 and 'legendary' in is_special:
					m = ""
					for s, sl in on_other_ships:
						if s is not None:
							if s not in ship_restriction:
								m += f'{s} (Slot {sl})\n'
					m = m[:-1]
					if len(m) > 0:
						embed.add_field(name="Also found on:",value=m)
					else:
						logging.warning('Other ships field is empty')
				if len(type_restriction) > 0:
					m =  ''.join([i.title()+', ' for i in sorted(type_restriction)])[:-2]
				else:
					m = "All types"
				embed.add_field(name="Ship Type",value=m)

				if len(tier_restriction) > 0:
					m = ''.join([str(i)+', ' for i in sorted(tier_restriction)])[:-2]
				else:
					m = "All tiers"
				embed.add_field(name="Tier",value=m)
				
				if len(nation_restriction) > 0:
					m = ''.join([i+', ' for i in sorted(nation_restriction)])[:-2]
				else:
					m = 'All nations'
				embed.add_field(name="Nation",value=m)
				
				if len(special_restriction) > 0:
					m = special_restriction
					if len(m) > 0:
						embed.add_field(name="Additonal Requirements",value=m)		
					else:
						logging.log("Additional requirements field empty")
				if price_credit > 0 and len(is_special) == 0:
					embed.add_field(name='Price (Credit)', value=f'{price_credit:,}')
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				# error, ship name not understood
				upgrade_name_list = [upgrade_list[i]['name'] for i in upgrade_list]
				closest_match = difflib.get_close_matches(upgrade, upgrade_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
				
				await channel.send(f"Upgrade **{upgrade}** is not understood." + closest_match_string)
	async def commander(self, message, arg):
		channel = message.channel
		# get information on requested commander
		message_string = message.content
		cmdr_found = False
		# message parse
		cmdr = ''.join([i+' ' for i in arg[2:]])[:-1] #message_string[message_string.rfind('-')+1:]
		if len(arg) <= 2:
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			try:
				async with channel.typing():
					logging.info(f'sending message for commander <{cmdr}>')
					name, icon, nation, cmdr_id = get_commander_data(cmdr)
					embed = discord.Embed(title="Commander")
					embed.set_thumbnail(url=icon)
					embed.add_field(name='Name',value=name, inline=False)
					embed.add_field(name='Nation',value=nation_dictionary[nation], inline=False)
					
					cmdr_data = None
					for i in game_data:
						if game_data[i]['typeinfo']['type'] == 'Crew':
							if cmdr_id == str(game_data[i]['id']):
								cmdr_data = game_data[i]
								
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
									skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor+'Descriptor']} {'+' if skill[descriptor] > 0 else ''}{skill[descriptor]:0.0f}\n"
									if c == 'MainGunsRotationModifier':
										skill_bonus_string += ' °/sec.'
							else:
								for descriptor in skill:
									if c == 'TorpedoAcceleratorModifier':
										if descriptor in ['planeTorpedoSpeedBonus', 'torpedoSpeedBonus']:
											skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor+'Descriptor']} {'+' if skill[descriptor] > 0 else ''}{skill[descriptor]:0.0f} kts.\n"
										else:
											skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor+'Descriptor']} {'+' if skill[descriptor]-1 > 0 else ''}{int(round((skill[descriptor]-1)*100))}%\n"
									else:
										if abs(skill[descriptor]-1) > 0:
											skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor+'Descriptor']} {'+' if skill[descriptor]-1 > 0 else ''}{int(round((skill[descriptor]-1)*100))}%\n"
							skill_bonus_string += '\n'
					if len(skill_bonus_string) > 0:
						embed.add_field(name='Skill Bonuses', value=skill_bonus_string, inline=False)
						embed.set_footer(text="For default skill bonuses, use [mackbot skill [skill name]]")
					else:
						embed.add_field(name='Skill Bonuses', value="None", inline=False)
					
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}: ", e)
				# error, ship name not understood
				cmdr_name_list = [cmdr_list[i]['name'] for i in cmdr_list]
				closest_match = difflib.get_close_matches(cmdr, cmdr_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
				
				await channel.send(f"Commander **{cmdr}** is not understood.")
	async def map(self, message, arg):
		channel = message.channel
		# get information on requested map
		message_string = message.content
		map_found = False
		# message parse
		map = ''.join([i+' ' for i in arg[2:]])[:-1] #message_string[message_string.rfind('-')+1:]
		if len(arg) <= 2:
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			try:
				async with channel.typing():
					logging.info(f'sending message for map <{map}>')
					description, image, id, name = get_map_data(map)
					embed = discord.Embed(title="Map")
					embed.set_image(url=image)
					embed.add_field(name='Name',value=name)
					embed.add_field(name='Description',value=description)
					
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}: ", e)
				# error, ship name not understood
				map_name_list = [map_list[i]['name'] for i in map_list]
				closest_match = difflib.get_close_matches(map, map_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
				
				await channel.send(f"Map **{map}** is not understood.")
	async def flag(self, message, arg):
		channel = message.channel
		# get information on requested flag
		message_string = message.content
		upgrade_found = False
		# message parse
		flag = ''.join([i+' ' for i in arg[2:]])[:-1]  # message_string[message_string.rfind('-')+1:]
		if len(arg) <= 2:
			# argument is empty, send help message
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			# user provided an argument
			try:
				logging.info(f'sending message for flag <{flag}>')
				profile, name, price_gold, image, price_credit, description = get_flag_data(flag)
				embed = discord.Embed(title="Flag Information")
				embed.set_thumbnail(url=image)
				embed.add_field(name='Name', value=name)
				embed.add_field(name='Description',value=description)
				embed.add_field(name='Effect',value=''.join([profile[detail]['description']+'\n' for detail in profile]))
				if price_credit > 0:
					embed.add_field(name='Price (Credit)', value=f"{price_credit:,}")
				if price_gold > 0:
					embed.add_field(name='Price (Doub.)', value=price_gold)
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				# error, ship name not understood
				flag_name_list = [flag_list[i]['name'] for i in flag_list]
				closest_match = difflib.get_close_matches(flag, flag_name_list)
				closest_match_string = ""
				if len(closest_match) > 0:
					closest_match_string = f'\nDid you meant **{closest_match[0]}**?'
				
				await channel.send(f"Flag **{flag}** is not understood.")
	async def doubloons(self, message, arg):
		channel = message.channel
		# get information on requested flag
		message_string = message.content
		upgrade_found = False
		# message parse
		doub = arg[2]  # message_string[message_string.rfind('-')+1:]
		if len(arg) <= 2:
			# argument is empty, send help message
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			# user provided an argument
			try:
				if len(arg) == 4:
					# check reverse conversion
					if arg[3].lower() in ['dollars', '$']:
						dollar = float(doub)
						dollar_formula = lambda x: (x ** (1/0.9)) / 0.0067 
						embed = discord.Embed(title="Doubloon Conversion (Dollars -> Doubloons)")
						embed.add_field(name=f"Requested Dollars", value=f"{dollar:0.2f}$")
						embed.add_field(name=f"Doubloons", value=f"Approx. {dollar_formula(dollar):0.0f} Doubloons")
						
				else:
					doub = int(doub)
					value_exceed = not (500 <= doub and doub <= 25000)
					doub_formula = lambda x: (0.0067 * doub)**(0.9)
					
					embed = discord.Embed(title="Doubloon Conversion (Doubloons -> Dollars)")
					embed.add_field(name=f"Requested Doubloons", value=f"{doub} Doubloons")
					embed.add_field(name=f"Price: ", value=f"{doub_formula(doub):0.2f}$")
					if value_exceed:
						embed.set_footer(text=":warning: You are unable to buy the requested doubloons")
						
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				await channel.send(f"Value **{doub}** is not a number (or an internal error has occured).")
	async def on_message(self,message):
		channel = message.channel
		arg = message.content.split(token)
		if message.author != self.user:
			if message.content.startswith("<@!"+str(self.user.id)+">"):
				if len(arg) == 1:
					# no additional arguments, send help
					logging.info(f"User {message.author} requested my help.")
					embed = self.help_message(command_header+token+"help"+token+"help")
					if not embed is None:
						logging.info(f"sending help message")
						await channel.send("はい、サラはここに。", embed=embed)
				else:
					# with arguments, change arg[0] and perform its normal task
					arg[0] = command_header
			if arg[0].lower()+token == command_header+token: # message starts with mackbot
				if DEBUG_IS_MAINTANCE and message.author != self.user and not message.author.name == 'mackwafang':
					# maintanance message
					await channel.send(self.user.display_name+" is under maintanance. Please wait until maintanance is over. Or contact Mack if he ~~fucks up~~ did an oopsie.")
					return
				request_type = arg[1:]
				logging.info(f'User <{message.author}> in <{message.guild}, {message.channel}> requested command "<{request_type}>"')
				
				if hasattr(self,arg[1]):
					await getattr(self,arg[1])(message, arg)
				else:
					# hidden command
					if arg[1] == 'waifu':
						await channel.send("Mack's waifu: Saratoga\nhttps://kancolle.fandom.com/wiki/Saratoga")
					if arg[1] == 'raifu':
						await channel.send("Mack's raifu: M1918 BAR https://en.gfwiki.com/wiki/M1918")
				# if not arg[1] in command_list:
					# await channel.send(f"I don't know command **{arg[1]}**. Please check the help page by tagging me or use **{command_header+token+command_list[0]}**")
	
if __name__ == "__main__":
	client = Client()
	check_build()
	try:
		client.run(bot_token)
	except Exception as e:
		print(f"{type(e)}",e)