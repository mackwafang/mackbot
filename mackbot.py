DEBUG_IS_MAINTANCE = False

import wargaming, os, nilsimsa, re, sys, pickle, discord, time, logging
import xml.etree.ElementTree as et
import pandas as pd
import numpy as np
import cv2 as cv
from PIL import ImageFont, ImageDraw, Image
from itertools import count
from numpy.random import randint
from bitstring import BitString

cwd = sys.path[0]
if cwd == '':
	cwd = '.'

logging.basicConfig(filename=f'{time.strftime("%Y_%b_%d", time.localtime())}_mackbot.log')
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-5s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


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
ship_type_to_hull_class = {
	'Destroyer': 'DD',
	'AirCarrier': 'CV',
	'Battleship': 'BB',
	'Cruiser': 'C',
	'Submarine': 'SS'
}
ship_name_to_ascii ={
	'[zao]':'[zaō]',
	'arp myoko':'arp myōkō',
	'arp myoukou':'arp myōkō',
	'smaland':'småland',
	'arp kongo':'arp kongō',
	'arp kongou':'arp kongō',
	'[grober kurfurst]':'[großer kurfürst]',
	'l\'effronte':'l\'effronte',
	'błyskawica':'błyskawica',
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
}
# dictionary that stores skill abbreviation
skill_name_abbr = {
	'bft':'basic firing training',
	'bs':'basics of survivability',
	'em':'expert marksman',
	'tae':'torpedo armament expertise',
	'ha':'high alert',
	'v':'vigilance',
	'de':'demolition expert',
	'aft':'advanced firing training',
	'aa':'aircraft armor',
	'ieb':'improved engine boost',
	'ce':'concealment expert',
	'jat':'jack of all trades',
	'fp':'fire prevention',
	'ss':'sight stabilization',
	'ie':'improved engines',
	's':'superintendent',
	'pm':'preventive maintenance',
	'ifa':'incoming fire alert',
	'ls':'last stand',
	'el':'expert loader',
	'ar':'adrenaline rush',
	'ta':'torpedo acceleration',
	'se':'survivability expert',
	'mfcsa':'manual fire control for secondary armament',
	'maaf':'massive aa fire',
	'pt':'priority target',
	'as':'air supremacy',
	'sse':'smoke screen expert',
	'dcf':'direction center for fighters',
	'lg':'last gasp',
	'ifhe':'inertia fuse for he shells',
	'ifhes':'inertia fuse for he shells',
	'rl':'radio location',
	'rpf':'radio location',
}
cmdr_name_to_ascii ={
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
}
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

logging.info("Fetching WoWS Encyclopedia")
with open(cwd+"/.env") as f:
	s = f.read().split('\n')[:-1]
	wg_token = s[0][s[0].find('=')+1:]
	bot_token = s[1][s[1].find('=')+1:]
	sheet_id = s[2][s[2].find('=')+1:]

wows_encyclopedia = wargaming.WoWS(wg_token,region='na',language='en').encyclopedia
ship_types = wows_encyclopedia.info()['ship_types']

logging.info("Fetching Skill List")
skill_list = wows_encyclopedia.crewskills()
for skill in skill_list:
	h = "0x"+nilsimsa.Nilsimsa(skill_list[skill]['name'].lower()).hexdigest() # hash using nilsimsa
	h = BitString(h).bin# convert to bits
	skill_list[skill]['name_hash'] = h
	
	# get local image location
	url = skill_list[skill]['icon']
	url = url[:url.rfind('_')]
	url = url[url.rfind('/')+1:]
	skill_list[skill]['local_icon'] = f'./skill_images/{url}.png'
	
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
	except Exception as e:
		if type(e) == wargaming.exceptions.RequestError:
			if e.args[0] == "PAGE_NO_NOT_FOUND":
				break
			else:
				logging.info(type(e), e)
		else:
			logging.info(type(e), e)
		break
logging.info("Fetching Commander List")
cmdr_list = wows_encyclopedia.crews()
for cmdr in cmdr_list:
	h = "0x"+nilsimsa.Nilsimsa(cmdr_list[cmdr]['first_names'][0].lower()).hexdigest() # hash using nilsimsa
	h = BitString(h).bin# convert to bits
	cmdr_list[cmdr]['name_hash'] = h
logging.info("Fetching Ship List")
ship_list = {}
for page in count(1): #range(1,6):
	try:
		l = wows_encyclopedia.ships(language='en',page_no=page)
		for i in l:
			h = "0x"+nilsimsa.Nilsimsa(l[i]['name'].lower()).hexdigest() # hash using nilsimsa
			h = BitString(h).bin# convert to bits
			l[i]['name_hash'] = h
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
logging.info("Fetching Camo, Flags and Modification List")
camo_list, flag_list, upgrade_list, flag_list = {}, {}, {}, {}
for page_num in count(1): #range(1,3):
	try:
		consumable_list = wows_encyclopedia.consumables(page_no=page_num)
		for consumable in consumable_list:
			c_type = consumable_list[consumable]['type']
			h = "0x"+nilsimsa.Nilsimsa(consumable_list[consumable]['name'].lower()).hexdigest() # hash using nilsimsa
			h = BitString(h).bin# convert to bits
			if c_type == 'Camouflage' or c_type == 'Permoflage' or c_type == 'Skin':
				camo_list[consumable] = consumable_list[consumable]
				camo_list[consumable]['name_hash'] = h
			if c_type == 'Modernization':
				upgrade_list[consumable] = consumable_list[consumable]
				upgrade_list[consumable]['name_hash'] = h
				
				url = upgrade_list[consumable]['image']
				url = url[:url.rfind('_')]
				url = url[url.rfind('/')+1:]
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
				flag_list[consumable] = consumable_list[consumable]
				flag_list[consumable]['name_hash'] = h
	except Exception as e:
		if type(e) == wargaming.exceptions.RequestError:
			if e.args[0] == "PAGE_NO_NOT_FOUND":
				break
			else:
				logging.info(type(e), e)
		else:
			logging.info(type(e), e)
		break
logging.info('Fetching build file...')
BUILD_EXTRACT_FROM_CACHE = False
extract_from_web_failed = False
BUILD_BATTLE_TYPE_CLAN = 0
BUILD_BATTLE_TYPE_CASUAL = 1
BUILD_CREATE_BUILD_IMAGES = True
build_battle_type = {
	BUILD_BATTLE_TYPE_CLAN   : "competitive",
	BUILD_BATTLE_TYPE_CASUAL : "casual",
}
build_battle_type_value = {
	"competitive"	: BUILD_BATTLE_TYPE_CLAN,
	"casual" 		: BUILD_BATTLE_TYPE_CASUAL,
}
ship_build = {build_battle_type[BUILD_BATTLE_TYPE_CLAN]:{}, build_battle_type[BUILD_BATTLE_TYPE_CASUAL]:{}}
if not BUILD_EXTRACT_FROM_CACHE:
	from googleapiclient.errors import Error
	from googleapiclient.discovery import build
	from google_auth_oauthlib.flow import InstalledAppFlow
	from google.auth.transport.requests import Request
	
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
				upgrade_slot = row[3]
				upgrade_ship_restrict = [] if len(row[4]) == 0 else row[4].split(', ')
				upgrade_tier_restrict = [] if len(row[5]) == 0 else [int(i) for i in row[5].split(', ')]
				upgrade_type_restrict = [] if len(row[6]) == 0 else row[6].split(', ')
				upgrade_nation_restrict = [] if len(row[7]) == 0 else row[7].split(', ')
				upgrade_special_restrict = [] if len(row[8]) == 0 else row[8].split('_')
				upgrade_tags = [] if len(row[9]) == 0 else row[9].split(', ')
			except Exception as e:
				# oops, skip this
				logging.info("Equipments parsing exception")
				continue
			
			for u in list(np.array([i for i in upgrade_list.keys()]).copy()):
				upgrade = upgrade_list[u]
				if u == upgrade_id:
					if not upgrade_usable:
						del upgrade_list[u]
						pass
					else:
						try:
							upgrade_list[u]['is_special'] = upgrade_type
							if len(upgrade_type) > 0:
								upgrade_list[u]['tags'] += [upgrade_type.lower()]
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
							logging.info("Equipments exclusion exception")
							break
	logging.info("Excluding upgrades done")

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


logging.info("Auto build Modification Abbreviation")
upgrade_abbr_list = {}
for u in upgrade_list:
	# print("'"+''.join([i[0] for i in mod_list[i].split()])+"':'"+f'{mod_list[i]}\',')
	upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(160),chr(32))
	key = ''.join([i[0] for i in upgrade_list[u]['name'].split()]).lower()
	if key in upgrade_abbr_list:
		key = ''.join([i[:2].title() for i in upgrade_list[u]['name'].split()]).lower()[:-1]
	upgrade_abbr_list[key] = upgrade_list[u]['name'].lower()

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
		logging.info(f"Fetching ship parameters. {i}/{len(ship_list)} ships found.", end='\r')
	logging.info("Creating cache")
	with open('./'+ship_param_file_name,'wb') as f:
		pickle.dump(ship_info, f)
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
		'min_threshold': 4,
		'max_threshold': 6,
		'description': "Any ships in this category have a **base air detection range** of **4 km or less** or a **base sea detection range** of **6 km or less**",
	}
}
regex = re.compile('((tier )(\d{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|((page )(\d{1,2}))|(([aA]ircraft [cC]arrier[sS]?)|((\w|-)*))')
equip_regex = re.compile('(slot (\d))|(tier ([0-9]{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|(page \d{1,2})|((defensive aa fire)|(main battery)|(aircraft carrier[sS]?)|(\w|-)*)')
for s in ship_list:
	nat = nation_dictionary[ship_list[s]['nation']]
	tags = []
	t = ship_list[s]['type']
	hull_class = ship_type_to_hull_class[t]
	if t == 'AirCarrier':
		t = 'Aircraft Carrier'
	tier = ship_list[s]['tier']
	prem = ship_list[s]['is_premium']
	ship_speed = ship_info[s]['mobility']['max_speed']
	if ship_speed <= ship_tags[SHIP_TAG_LIST[SHIP_TAG_SLOW_SPD]]['max_threshold']:
		tags += [SHIP_TAG_LIST[SHIP_TAG_SLOW_SPD]]
	if ship_speed >= ship_tags[SHIP_TAG_LIST[SHIP_TAG_FAST_SPD]]['min_threshold']:
		tags += [SHIP_TAG_LIST[SHIP_TAG_FAST_SPD]]
	concealment = ship_info[s]['concealment']
	if concealment['detect_distance_by_plane'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG_STEALTH]]['min_threshold'] or concealment['detect_distance_by_ship'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG_STEALTH]]['max_threshold']:
		tags += [SHIP_TAG_LIST[SHIP_TAG_STEALTH]]
	try:
		fireRate = ship_info[s]['artillery']['shot_delay']
	except:
		fireRate = np.inf
	if fireRate <= ship_tags[SHIP_TAG_LIST[SHIP_TAG_FAST_GUN]]['max_threshold'] and not t == 'Aircraft Carrier':
		tags += [SHIP_TAG_LIST[SHIP_TAG_FAST_GUN], 'dakka']
	
	tags += [nat, f't{tier}', t+'s', hull_class]
	ship_list[s]['tags'] = tags
	if prem:
		ship_list[s]['tags'] += ['premium']
		
logging.info("Filtering Ships and Categories")
del ship_list['3749623248']
ship_list_frame = pd.DataFrame(ship_list)
ship_list_frame = ship_list_frame.filter(items=['name','nation','images','type','tier','modules', 'upgrades', 'is_premium', 'price_gold', 'name_hash', 'tags'],axis=0)
ship_list = ship_list_frame.to_dict()

logging.info("Fetching Maps")
map_list = wows_encyclopedia.battlearenas()
for m in map_list:
	h = "0x"+nilsimsa.Nilsimsa(map_list[m]['name'].lower()).hexdigest() # hash using nilsimsa
	h = BitString(h).bin# convert to bits
	map_list[m]['name_hash'] = h
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
)
def hamming(s1, s2):
	dist = 0
	for n in range(len(s1)):
		if s1[n] != s2[n]:
			dist += 1
	return dist
def find_closest(s, dictionary):
	h = BitString("0x"+nilsimsa.Nilsimsa(s.lower()).hexdigest()).bin
	min_collision = np.inf
	name = ""
	lowest_match = []
	for i in dictionary:
		ham = hamming(h, dictionary[i]['name_hash'])
		if ham < min_collision:
			name = dictionary[i]['name']
			min_collision = ham
			lowest_match = [name]
		elif ham == min_collision:
			lowest_match += [dictionary[i]['name']]
	if len(lowest_match) > 1:
		for i in lowest_match:
			if len(s) == len(i):
				name = i
	else:
		name = lowest_match[0]
	return name
def check_build():
	'''
		checks ship_build for in incorrectly inputted values and outputs build images
	'''
	skill_use_image = cv.imread("./skill_images/icon_perk_use.png", cv.IMREAD_UNCHANGED)
	skill_use_image_channel = [i for i in cv.split(skill_use_image)]
	for t in build_battle_type:
		for s in ship_build[build_battle_type[t]]:
			image = np.zeros((520,660,4))
			logging.info(f"Checking {build_battle_type[t]} battle build for ship {s}...")
			
			name, nation, _, ship_type, tier, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_build_data(s, battle_type=build_battle_type[t])
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
							image[y*h : (y+1)*h, (x + (x // 2))*w: (x+(x // 2)+1)*h, i] = skill_use_image_channel[i]
						image[y*h : (y+1)*h, (x + (x // 2))*w: (x+(x // 2)+1)*h, 3] += skill_use_image_channel[3]
						
					except Exception as e: 
						logging.info(f"Skill check: Exception {type(e)}", e, f"in check_build, listing skill {skill}")
			else:
				logging.info("Skill check: No skills found in build")
			cv.imwrite(f"{name.lower()}_{build_battle_type[t]}_build.png", image)
def get_build_data(ship, battle_type='casual'):
	'''
		returns name, nation, images, ship type, tier of requested warship name
		
		raise exceptions for dictionary
	'''
	
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
			name, nation, images, ship_type, tier, modules, equip_upgrades, is_prem, price_gold, _, _ = ship_list[i].values()
			upgrades, skills, cmdr = {}, {}, ""
			if name.lower() in ship_build[battle_type]:
				upgrades, skills, cmdr = ship_build[battle_type][name.lower()].values()
			return name, nation, images, ship_type, tier, modules, equip_upgrades, is_prem, price_gold, upgrades, skills, cmdr, battle_type
	except Exception as e:
		raise e
def get_ship_data(ship):
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
def get_skill_data(skill):
	'''
		returns name, id, skill type, perk, tier, and icon for the requested skill
		
		raises exception from dictionary
	'''
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
		name, id, skill_type, perk, tier, icon, _, _ = skill_list[i].values()
		return name, id, skill_type, perk, tier, icon
	except Exception as e:
		# oops, probably not found
		logging.info(f"Exception {type(e)}: ",e)
		raise e
def get_upgrade_data(upgrade):
	'''
		returns name for the requested upgrade 
		
		raises exception from dictionary
	'''
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
		profile, name, price_gold, image, _, price_credit, _, description, _, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships, _ = upgrade_list[i].values()
		
		return profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships
	except Exception as e:
		raise e
		logging.info(f"Exception {type(e)}: ",e)
def get_commander_data(cmdr):
	'''
		returns name, icon and nation requested special commander 
		
		raise exceptions for dictionary
	'''
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
				
				return name, icons, nation
	except Exception as e:
		logging.erro(f"Exception {type(e)}",e)
		raise e
def get_flag_data(flag):
	'''
		returns information for the requested flag
		
		raises exception from dictionary
	'''
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
		profile, name, price_gold, image, _, price_credit, upgrade_type, description, _ = flag_list[i].values()
		return profile, name, price_gold, image, price_credit, upgrade_type, description
		
	except Exception as e:
		raise e
		logging.info(f"Exception {type(e)}: ",e)
def get_map_data(map):
	'''
		returns information for the requested map
	'''
	map = map.lower()
	try:
		for m in map_list:
			if map == map_list[m]['name'].lower():
				description, image, id, name, _ = map_list[m].values()
				return description, image, id, name
	except Exception as e:
		raise e
		logging.info("Exception {type(e): ", e)
		
class Client(discord.Client):
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
				embed.add_field(name='Usage',value=command_header+token+command+token+'[command]')
				embed.add_field(name='Description',value='List proper usage for [command]. Omit -[command] to list all possible commands')
				m = [i+'\n' for i in command_list]
				m.sort()
				m = ''.join(m)
				embed.add_field(name='All Commands',value=m)
			if command == 'goodbot':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='Praise the bot for being a good bot')
			if command == 'build':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[type]'+token+'build'+token+'[image]')
				embed.add_field(name='Description',value='List name, nationality, type, tier, recommended build of the requested warships\n'+
					f'**[type]**: Optional. Indicates should {command_header} returns a competitive or a casual build. Acceptable values: **[competitive, casual]**. Default value is **casual**\n'+
					'**ship**: Required. Desired ship to output information on.\n'+
					'**image**: Optional. If the word **image** is presence, then return an image format instead of an embedded message format. If a build does not exists, it return an embedded message instead.')
			if command == 'ship':
				embed.add_field(name='Usage',value=command_header+token+command+token+'ship'+token+'')
				embed.add_field(name='Description',value='List the combat parameters of the requested warships\n'+
					'**This function is WIP. ~~Because WG API is a mess~~')
			if command == 'skill':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[skill/abbr]')
				embed.add_field(name='Description',value='List name, type, tier and effect of the requested commander skill')
			if command == 'map':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[map_name]')
				embed.add_field(name='Description',value='List name and display the map of the requested map')
			if command == 'whoami':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='Who\'s this bot?')
			if command == 'list':
				if len(arg) == 3:
					embed.add_field(name='Usage',value=command_header+token+command+token+"[skills/upgrades/commanders/flags]")
					embed.add_field(name='Description',value=f'Select a category to list all items of the requested category. type **{command_header+token+command+token} [skills/upgrades/commanders]** for help on the category.{chr(10)}'+
						'**skills**: List all skills.\n'+
						'**upgrades**: List all upgrades.\n'+
						'**commanders**: List all commanders.\n'+
						'**flags**: List all non-special flags.\n')
				else:
					if arg[3] == 'skills':
						embed.add_field(name='Usage',value=command_header+token+command+token+"skills"+token+"[type/tier] [type_name/tier_number]")
						embed.add_field(name='Description',value='List name and the abbreviation of all commander skills.\n'+
						'**type [type_name]**: Optional. Returns all skills of indicated skill type. Acceptable values: **[Attack, Endurance, Support, Versatility]**\n'+
						'**tier [tier_number]**: Optional. Returns all skills of the indicated tier. Acceptable values: **[1,2,3,4]**')
					elif arg[3] == 'upgrades':
						embed.add_field(name='Usage',value=command_header+token+command+token+"upgrades"+token+"[queries]")
						embed.add_field(name='Description',value='List name and the abbreviation of all upgrades.\n'+
							f'**[queries]**: Search queries for upgrades (Examples: secondary, torpedoes, slot 4')
					elif arg[3] == 'commanders':
						embed.add_field(name='Usage',value=command_header+token+command+token+"commanders"+token+"[page_number/nation]")
						embed.add_field(name='Description',value='List names of all unique commanders.\n'+
							f'**[page_number]** Required. Select a page number to list commanders.\n'+
							f'**[nation]** Required. Select a nation to filter. Acceptable values: **[{"".join([nation_dictionary[i]+", " for i in nation_dictionary][:-3])}]**')
					elif arg[3] == 'flags':
						embed.add_field(name='Usage',value=command_header+token+command+token+"flags")
						embed.add_field(name='Description',value='List names of all signal flags.\n')
					elif arg[3] == 'maps':
						embed.add_field(name='Usage',value=command_header+token+command+token+"maps"+token+"[page_num]")
						embed.add_field(name='Description',value='List names of all maps.\n'+
							f'**[page_number]** Required. Select a page number to list maps.\n')
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
						
						embed.add_field(name='Usage',value=command_header+token+command+token+"ships"+token+"[search tags]\n")
						embed.add_field(name='Description',value='List all available ships with the tags provided.\n' + add_help_string)
					else:
						embed.add_field(name='Error',value="Invalid command.")
						 
			if command == 'upgrade':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[upgrade/abbr]')
				embed.add_field(name='Description',value='List the name and description of the requested warship upgrade')
			if command == 'commander':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[cmdr_name]')
				embed.add_field(name='Description',value='List the nationality of the requested commander')
			if command == 'flag':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[flag_name]')
				embed.add_field(name='Description',value='List the name and description of the requested signal flag')
			if command == 'feedback':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='Send a feedback form link for mackbot.')
		else:
			embed.add_field(name='Error',value="Invalid command.")
		return embed
	async def help(self, message, arg):
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
				async with channel.typing():
					try:
						name, nation, images, ship_type, tier, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_build_data(ship, battle_type=battle_type)
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
						else:
							await channel.send(f"Ship **{ship}** is not understood")
			else:
				try:
					async with channel.typing():
						name, nation, images, ship_type, tier, _, _, is_prem, price_gold, upgrades, skills, cmdr, battle_type = get_build_data(ship, battle_type=battle_type)
						logging.info(f"returning build information for <{name}> in embeded format")
						ship_type = ship_types[ship_type]
						embed = discord.Embed(title=f"{battle_type.title()} Build for {name}", description='')
						embed.set_thumbnail(url=images['small'])
						# get server emoji
						if message.guild is not None:
							server_emojis = message.guild.emojis
						else:
							server_emojis = []
						
						# image exists!
						tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
						
						embed.description += f'**Tier {tier_string} {nation_dictionary[nation]} {"Premium "+ship_type if is_prem else ship_type}**'
						
						footer_message = ""
						error_value_found = False
						
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
							footer_message += "Suggested skills are listed in ascending acquiring order.\n"
							embed.add_field(name='Suggested Cmdr.', value=m)
						else:
							embed.add_field(name='Suggested Cmdr.', value="Coming Soon:tm:",inline=False)
					error_footer_message = ""
					if error_value_found:
						error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact mackwafang#2071.\n"
					footer_message += f"For {'casual' if battle_type == 'competitive' else 'competitive'} builds, use [mackbot build {'casual' if battle_type == 'competitive' else 'competitive'} [ship_name]]\n"
					embed.set_footer(text=error_footer_message+footer_message)
					await channel.send(embed=embed)
				except Exception as e:
					logging.info(f"Exception {type(e)}", e)
					await channel.send(f"Ship **{ship}** is not understood")
	async def ship(self, message, arg):
		channel = message.channel
		# get voted ship build
		# message parse
		ship_found = False
		if len(arg) <= 2:
			embed = self.help_message(command_header+token+"help"+token+arg[1])
			if not embed is None:
				await channel.send(embed=embed)
		else:
			ship = ''.join([i+' ' for i in arg[2:]])[:-1] # grab ship name
			try:
				async with channel.typing():
					ship_param = get_ship_data(ship)
					name, nation, images, ship_type, tier, modules, _, is_prem, _, _, _, _, _ = get_build_data(ship)
					logging.info(f"returning ship information for <{name}> in embeded format")
					
					ship_type = ship_types[ship_type]
					embed = discord.Embed(title=f"{ship_type} {name}", description='')
					embed.set_thumbnail(url=images['small'])
					# get server emoji
					if message.guild is not None:
						server_emojis = message.guild.emojis
					else:
						server_emojis = []
					
					# image exists!
					tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0].upper()
					
					embed.description += f'**Tier {tier_string} {nation_dictionary[nation]} {"Premium "+ship_type if is_prem else ship_type}**\n'
					
					footer_message = ""
					embed.description += f"Matchmaking tier {ship_param['battle_level_range_min']} - {ship_param['battle_level_range_max']}"
					
					if len(modules['hull']) > 0:
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
							
						embed.add_field(name="**Hull**", value=m, inline=False)
					if len(modules['artillery']) > 0:
						m = ""
						m += f"**Range: **"
						for fc in sorted(modules['fire_control'], key=lambda x: module_list[str(x)]['profile']['fire_control']['distance']):
							m += f"{module_list[str(fc)]['profile']['fire_control']['distance']} - "
						m = m[:-2]
						m += "k.m.\n"
						for h in sorted(modules['artillery'], key=lambda x: module_list[str(x)]['name']):
							guns = module_list[str(h)]['profile']['artillery']
							m += f"**{module_list[str(h)]['name']}:**\n"
							if guns['max_damage_HE'] > 0:
								m += f"**HE:** {guns['max_damage_HE']}\n"
							if guns['max_damage_AP'] > 0:
								m += f"**AP:** {guns['max_damage_AP']}\n"
							m += f"**Reload:** {60/guns['gun_rate']:0.1f}s\n"
						embed.add_field(name="**Main Battery**", value=m, inline=False)
					if ship_param['atbas'] is not None:
						m = ""
						
						m += f"**Range:** {ship_param['atbas']['distance']} k.m.\n"
						for slot in ship_param['atbas']['slots']:
							guns = ship_param['atbas']['slots'][slot]
							m += f"**{guns['name']}:**\n"
							if guns['damage'] > 0:
								m += f"**HE:** {guns['damage']}\n"
							m += f"**Reload:** {guns['shot_delay']}s\n"
						embed.add_field(name="**Secondary Battery**", value=m, inline=False)
					if len(modules['torpedoes']) > 0:
						m = ""
						for h in sorted(modules['torpedoes'], key=lambda x: module_list[str(x)]['name']):
							torps = module_list[str(h)]['profile']['torpedoes']
							m += f"**{module_list[str(h)]['name']} ({torps['distance']} k.m.):**\n"
							if torps['max_damage'] > 0:
								m += f"**Damage:** {torps['max_damage']}, "
							if torps['torpedo_speed'] > 0:
								m += f"{torps['torpedo_speed']} kts.\n"
						embed.add_field(name="**Torpedoes**", value=m, inline=False)
					
					embed.set_footer(text="Parameters does not take into account upgrades and commander skills")
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				await channel.send(f"Ship **{ship}** is not understood")

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
					embed = discord.Embed(title="Commander Skill")
					embed.set_thumbnail(url=icon)
					embed.add_field(name='Skill Name', value=name)
					embed.add_field(name='Tier', value=tier)
					embed.add_field(name='Category', value=skill_type)
					embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk) if len(perk) != 0 else '')
				await channel.send(embed=embed)
			except Exception as e:
				logging.info("Exception", type(e), ":", e)
				await channel.send(f"Skill **{skill}** is not understood.")
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
							
							slot = ''.join([i[0] for i in s])
							key = [i[6] for i in s if len(i[6]) > 1]
							page = [i[5] for i in s if len(i[5]) > 1]
							tier = [i[2] for i in s if len(i[2]) > 1]
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
						s = regex.findall(''.join([str(i) + ' ' for i in search_param])[:-1])
						
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
								name, _, _, ship_type, tier, _,  _, is_prem, _, _, _, _, _ = get_build_data(ship_list[ship]['name'])
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
									type_icon = ship_type_to_hull_class[ship_type]
								m += [f"**{tier_string:<4} [{type_icon}]** {name}"]
								
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
			try:
				logging.info(f'sending message for upgrade <{upgrade}>')
				profile, name, price_gold, image, price_credit, description, local_image, is_special, ship_restriction, nation_restriction, tier_restriction, type_restriction, slot, special_restriction, on_other_ships = get_upgrade_data(upgrade)
				embed_title = 'Ship Upgrade'
				if is_special.lower() == 'legendary':
					embed_title = "Legendary Ship Upgrade"
				elif is_special.lower() == 'coal':
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
				if len(on_other_ships) > 0 and is_special.lower() != 'legendary':
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
				if price_credit > 0 and is_special == '':
					embed.add_field(name='Price (Credit)', value=f'{price_credit:,}')
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}", e)
				await channel.send(f"Upgrade **{upgrade}** is not understood.")
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
					name, icon, nation = get_commander_data(cmdr)
					embed = discord.Embed(title="Commander")
					embed.set_thumbnail(url=icon)
					embed.add_field(name='Name',value=name)
					embed.add_field(name='Nation',value=nation_dictionary[nation])
					
				await channel.send(embed=embed)
			except Exception as e:
				logging.info(f"Exception {type(e)}: ", e)
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
				profile, name, price_gold, image, price_credit, _, description = get_flag_data(flag)
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
				await channel.send(f"Flag **{flag}** is not understood.")
	
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