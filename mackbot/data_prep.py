import wargaming, traceback, json, logging, os, pickle, io, requests

from hashlib import sha256
from pymongo import MongoClient
from itertools import count
from math import inf
from enum import IntEnum, auto
from tqdm import tqdm
from pprint import pprint

from mackbot.constants import nation_dictionary, hull_classification_converter, UPGRADE_MODIFIER_DESC
from mackbot.exceptions import BuildError
from mackbot.utilities.ship_consumable_code import consumable_data_to_string, encode, characteristic_rules
from mackbot.wargaming.armory import get_armory_ships

game_data = {}
ship_list = {}
skill_list = {}
module_list = {}
upgrade_list = {}
camo_list = {}
cmdr_list = {}
flag_list = {}
legendary_upgrade_list = {}
upgrade_abbr_list = {}
consumable_list = {}
ship_build = {}

class SHIP_TAG(IntEnum):
	SLOW_SPD = auto()
	FAST_SPD = auto()
	FAST_GUN = auto()
	STEALTH = auto()
	AA = auto()

class LogFilterBlacklist(logging.Filter):
	def __init__(self, *blacklist):
		self.blacklist = [i for i in blacklist]

	def filter(self, record):
		return not any(f in record.getMessage() for f in self.blacklist)

class TqdmToLogger(io.StringIO):
	"""
	Output stream for TQDM which will output to logger module instead of
	the StdOut.
	"""
	logger = None
	level = None
	buf = ''
	def __init__(self,logger,level=None):
		super(TqdmToLogger, self).__init__()
		self.logger = logger
		self.level = level or logging.INFO
	def write(self,buf):
		self.buf = buf.strip('\r\n\t ')
	def flush(self):
		self.logger.log(self.level, self.buf)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] [%(name)-8s] [%(module)s.%(funcName)s] [%(levelname)-5s] %(message)s')

stream_handler.setFormatter(formatter)

logger = logging.getLogger("mackbot_data_loader")
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


# load config
with open(os.path.join("data", "config.json")) as f:
	data = json.load(f)

mongodb_host = data['mongodb_host']
sheet_id = data['sheet_id']

# get weegee's wows encyclopedia
try:
	WG = wargaming.WoWS(data['wg_token'], region='na', language='en')
except Exception as e:
	logger.error("Cannot connect to WG servers")
	exit(1)
wows_encyclopedia = WG.encyclopedia
ship_types = wows_encyclopedia.info()['ship_types']
ship_types["Aircraft Carrier"] = "Aircraft Carrier"

# dictionary to convert user inputted ship name to non-ascii ship name
with open(os.path.join("data", "ship_name_dict.json"), 'r', encoding='utf-8') as f:
	ship_name_to_ascii = json.load(f)

# define database stuff
database_client = None
try:
	database_client = MongoClient(mongodb_host)
except ConnectionError:
	logger.warning("MongoDB cannot be connected.")

def lerp(a, b, t):
	"""
	Returns the linear interpolation between a and b given t
	Args:
		a ():
		b ():
		t ():

	Returns:

	"""
	return ((1 - t) * a) + (t * b)

def check_skill_order_valid(skills: list) -> bool:
	"""
	Check to see if order of skills are valid (i.e., difference between skills are no greater than 1 tier)
	Also, first skill must be a tier 1 skill
	Args:
		skills (list): list of skill id

	Returns:
		bool
	"""
	if not skills:
		# no skills is a valid configuration
		return True
	is_first_skill_valid = skill_list[str(skills[0])]['y'] == 0
	if not is_first_skill_valid:
		return False

	max_tier_so_far = -1
	for s in skills:
		skill_data = skill_list[str(s)]
		if skill_data['y'] > max_tier_so_far + 1:
			return False
		max_tier_so_far = max(max_tier_so_far, skill_data['y'])
	return True

def load_game_params():
	global game_data
	# load the gameparams files
	logger.info(f"Loading GameParams")
	for file_count in count(0):
		try:
			with open(os.path.join(os.getcwd(), "data", f'GameParamsPruned_{file_count}.json')) as f:
				data = json.load(f)

			game_data.update(data)
			del data
		except FileNotFoundError:
			break

def load_skill_list():
	global skill_list
	# loading skills list
	logger.info("Fetching Skill List")
	try:
		with open(os.path.join("data", "skill_list.json")) as f:
			skill_list.update(json.load(f))

		# dictionary that stores skill abbreviation
		for skill in skill_list:
			# generate abbreviation
			abbr_name = ''.join([i[0] for i in skill_list[skill]['name'].lower().split()])
			skill_list[skill]['abbr'] = abbr_name
			skill_list[skill]['skill_id'] = int(skill)
	except FileNotFoundError:
		logger.error("skill_list.json is not found")

# find game data items by tags
def find_game_data_item(item):
	return [i for i in game_data if item in i]

def find_module_by_tag(x):
	l = []
	for i in module_list:
		if 'tag' in module_list[i]:
			if x == module_list[i]['tag']:
				l += [i]
	if l:
		return l[0]
	else:
		return None

def load_module_list():
	global module_list
	# get modules (i.e. guns, hulls, planes)
	logger.info("Fetching Module List")
	for page in count(1):
		try:
			m = wows_encyclopedia.modules(language='en', page_no=page)
			for counter, i in enumerate(m):
				module_list[i] = m[i]
		except Exception as e:
			if type(e) == wargaming.exceptions.RequestError:
				if e.args[0] == "PAGE_NO_NOT_FOUND":
					break
				else:
					logger.info(type(e), e)
			elif type(e) == requests.exceptions.ConnectionError:
				logger.info(type(e), e)
				exit(type(e))
			else:
				logger.info(type(e), e)
			break

def load_ship_list():
	"""
	Get information from wg api about list of ships.
	Note: Some ships may be updated in the update_ship_modules function
	Returns:
		dict - dictionary of ships
	"""
	logger.info("Fetching Ship List")
	global ship_list
	ship_list_file_name = 'ship_list'
	ship_list_file_dir = os.path.join("data", ship_list_file_name)

	fetch_ship_list_from_wg = False
	# fetching from local
	if os.path.isfile(ship_list_file_dir):
		with open(ship_list_file_dir, 'rb') as f:
			ship_list.update(pickle.load(f))

		# check to see if it is out of date
		if ship_list['ships_updated_at'] != wows_encyclopedia.info()['ships_updated_at']:
			logger.info("Ship list outdated, fetching new list")
			fetch_ship_list_from_wg = True
			ship_list = {}

	else:
		logger.info("No ship list file, fetching new")
		fetch_ship_list_from_wg = True

	if fetch_ship_list_from_wg:
		for page in count(1):
			# continuously count, because weegee don't list how many pages there are
			# actually the above is a lie, this page count appears in the "meta" field when getting
			# a response from wg via http request
			try:
				l = wows_encyclopedia.ships(language='en', page_no=page)
				for i in l:
					ship_list[i] = l[i]
					# add skip bomber field to list's modules listing
					ship_list[i]['modules']['skip_bomber'] = []
					if "\xa0" in ship_list[i]['name']:
						ship_list[i]['name'] = ship_list[i]['name'].replace("\xa0", " ")
					if ship_list[i]['ship_id'] == 3741235152:
						ship_list[i]['name'] = "Belfast '43"
			except Exception as e:
				if type(e) == wargaming.exceptions.RequestError:
					if e.args[0] == "PAGE_NO_NOT_FOUND":
						break
					else:
						logger.info(type(e), e)
				else:
					logger.info(type(e), e)
				break
		with open(ship_list_file_dir, 'wb') as f:
			ship_list['ships_updated_at'] = wows_encyclopedia.info()['ships_updated_at']
			pickle.dump(ship_list, f)
		logger.info("Cache complete")
	del ship_list_file_dir, ship_list_file_name, ship_list['ships_updated_at']

def load_upgrade_list():
	global ship_list, game_data, camo_list, flag_list, upgrade_list

	logger.info("Fetching Camo, Flags and Modification List")
	if len(ship_list) == 0:
		logger.warning("Ship list is empty.")
		load_ship_list()

	if len(game_data) == 0:
		logger.warning("No game data")
		load_game_params()


	for page_num in count(1):
		try:
			misc_list = wows_encyclopedia.consumables(page_no=page_num)
			# consumables of some page page_num
			for consumable in misc_list:
				c_type = misc_list[consumable]['type']
				if c_type == 'Camouflage' or c_type == 'Permoflage' or c_type == 'Skin':
					# grab camouflages and stores
					camo_list[consumable] = misc_list[consumable]
				if c_type == 'Modernization':
					# grab upgrades and store
					upgrade_list[consumable] = misc_list[consumable]

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
					flag_list[consumable] = misc_list[consumable]
		except Exception as e:
			if type(e) == wargaming.exceptions.RequestError:
				if e.args[0] == "PAGE_NO_NOT_FOUND":
					# counter went outside of max number of pages.
					# expected behavior, done
					break
				else:
					# something else came up that is not a "exceed max number of pages"
					logger.info(type(e), e)
			else:
				# we done goof now
				logger.info(type(e), e)
			break

	logger.info('Adding upgrade information')
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
				uid = str(upgrade['id'])

				# upgrade usable
				try:
					upgrade_list[uid]
				except KeyError:
					upgrade_name = [game_data[i] for i in game_data if game_data[i]['id'] == int(uid)][0]
					logger.warning(f"Upgrade with id {uid} (name: {upgrade_name['name']})is not known via WG API")
					continue
				upgrade_list[uid]['is_special'] = {
					0: '',
					1: 'Coal',
					3: 'Unique'
				}[upgrade['type']]

				# update upgrade's profile, because wg apparently stop updating them, again
				# for p in upgrade_list[uid]['profile']:
				# 	upgrade[uid]['profile'][p] = game_data[i]['modifier'][p]
				upgrade_list[uid]['profile'] = game_data[i]['modifiers'].copy()

				upgrade_list[uid]['slot'] = int(upgrade['slot']) + 1
				upgrade_list[uid]['ship_restriction'] = [ship_list[str(game_data[s]['id'])]['name'] for s in upgrade['ships'] if s in game_data and str(game_data[s]['id']) in ship_list]

				upgrade_list[uid]['type_restriction'] = ['Aircraft Carrier' if t == 'AirCarrier' else t for t in upgrade['shiptype']]
				upgrade_list[uid]['nation_restriction'] = [t for t in upgrade['nation']]
				upgrade_list[uid]['tier_restriction'] = sorted([t for t in upgrade['shiplevel']])

				upgrade_list[uid]['tags'] += upgrade_list[uid]['type_restriction']
				upgrade_list[uid]['tags'] += upgrade_list[uid]['tier_restriction']

				if upgrade['type'] == 3:
					# add ship specific restriction if upgrade is unique
					ship_id = str(game_data[upgrade['ships'][0]]['id'])
					upgrade_list[uid]['ship_restriction'] = [ship_list[ship_id]['name']]
					legendary_upgrade_list[uid] = upgrade_list[uid].copy()

	legendary_upgrades = {u: upgrade_list[u] for u in upgrade_list if upgrade_list[u]['is_special'] == 'Unique'}

	logger.info('Removing obsolete upgrades')
	for i in obsolete_upgrade:
		del upgrade_list[i]

	# changes to ship_list's ship upgrade structure to index slots,
	for sid in ship_list:
		ship = ship_list[sid]
		ship_upgrades = ship['upgrades']  # get a copy of ship's possible upgrades
		ship['upgrades'] = dict((str(i), []) for i in range(6))  # restructure
		for s_upgrade in ship_upgrades:
			# put ship upgrades in the appropiate slots
			upgrade = upgrade_list[str(s_upgrade)]
			ship['upgrades'][str(upgrade['slot'] - 1)] += [str(s_upgrade)]

	create_upgrade_abbr()

def update_ship_modules():
	# the painstaking method of updating ship modules with useful information
	# why? because the wg api does not provide information such as (but not limited to):
	#   - turret counts
	#   - skip bombers
	#   - torpedo

	logger.info("Generating information about modules")
	if len(game_data) == 0:
		logger.warning("Game data is empty.")
		load_game_params()
	if len(ship_list) == 0:
		logger.warning("Ship list is empty.")
		load_ship_list()
	# load_ship_params()
	if len(module_list) == 0:
		logger.warning("Module list is empty.")
		load_module_list()

	armory_ship_data = get_armory_ships()

	# add missing ships from api to ship list and initialize new ship data for update
	known_ship_id = [i['ship_id'] for i in ship_list.values()]
	missing_ship_index = [i for i in game_data if game_data[i]['typeinfo']['type'] == 'Ship']
	for i in missing_ship_index:
		missing_ship_data = game_data[i]
		# skip known ships
		if missing_ship_data['id'] in known_ship_id:
			continue
		# check if national flag is in flag dictionary
		if missing_ship_data['navalFlag'] not in nation_dictionary:
			continue
		# check if not an normal playable ship
		if missing_ship_data['typeinfo']['species'] not in ship_types:
			continue

		ship_list_data = {
			"description": "",
			"price_gold": 0,
			"ship_id_str": game_data[i]["index"],
			"has_demo_profile": False,
			"images": {
				"small": None,
				"medium": None,
				"large": None,
				"contour": None,
			},
			"modules": {
				'engine': [],
				'torpedo_bomber': [],
				'fighter': [],
				'hull': [],
				'artillery': [],
				'torpedoes': [],
				'fire_control': [],
				'flight_control': [],
				'dive_bomber': [],
				'skip_bomber': [],
				'pinger': [],
			},
			"module_tree": {},
			"nation": 'ussr' if missing_ship_data['navalFlag'].lower() == 'russia' else missing_ship_data['navalFlag'].lower(),
			"is_premium": False,
			"ship_id": game_data[i]["id"],
			"price_credit": 0,
			"default_profile": {},
			"upgrades": [],
			"tier": missing_ship_data['level'],
			"next_ships": {},
			"mod_slots": [1, 1, 2, 2, 3, 4, 4, 5, 6, 6, 6][missing_ship_data['level'] - 1],
			"type": missing_ship_data['typeinfo']['species'],
			"is_special": False,
			"name": missing_ship_data["name"]
		}
		skip_addition_condition = [
			ship_list_data['nation'] == 'events',
			missing_ship_data['group'] in ['disabled', 'preserved']
		]
		if any(skip_addition_condition):
			continue

		ship_list[str(missing_ship_data['id'])] = ship_list_data.copy()
		if ship_list_data['name'] == 'Z-42':
			pass

	for s in tqdm(ship_list):
		ship = ship_list[s]

		try:
			module_full_id_str = find_game_data_item(ship['ship_id_str'])[0]
			module_data = game_data[module_full_id_str]

			# grab consumables
			ship_list[s]['consumables'] = module_data['ShipAbilities'].copy()

			ship_upgrade_info = module_data['ShipUpgradeInfo']  # get upgradable modules

			# get next ship in the researchable lines
			for _k, _data in ship_upgrade_info.items():
				if type(_data) == dict:
					if _data['nextShips']:
						for next_ship in _data['nextShips']:
							next_ship_id = str(game_data[next_ship]['id'])
							ship_list[s]['next_ships'][next_ship_id] = 0
							# add this ship as the predecessor
							if next_ship_id in ship_list:
								ship_list[next_ship_id]['prev_ship'] = s

			del _k, _data

			# get credit and xp cost for ship research
			if s in armory_ship_data:
				ship_list[s]['price_credit'] = ship_upgrade_info['costCR']
				ship_list[s]['price_xp'] = 0
				ship_list[s]['price_special'] = armory_ship_data[s]['value']
				ship_list[s]['price_special_type'] = armory_ship_data[s]['currency_type']
			else:
				ship_list[s]['price_credit'] = ship_upgrade_info['costCR']
				ship_list[s]['price_xp'] = ship_upgrade_info['costXP']
				ship_list[s]['price_special'] = ship_upgrade_info['costGold']
				ship_list[s]['price_special_type'] = ""

			# is this a premium boat?
			ship_list[s]['is_premium'] = module_data['group'] in ('special', 'specialUnsellable')
			# is this a special boat? (i.e. event)
			ship_list[s]['is_special'] = module_data['group'] in ('ultimate', 'clan', 'coopOnly', 'upgradeableExclusive', 'upgradeableUltimate', 'earlyAccess')
			# is this a test boat?
			ship_list[s]['is_test_ship'] = module_data['group'] == 'demoWithoutStats'

			for _info in ship_upgrade_info:  # for each warship modules (e.g. hull, guns, fire-control)
				# tries to get data from module list
				if type(ship_upgrade_info[_info]) == dict:  # if there are data
					try:
						module_id = find_module_by_tag(_info)
						if module_id is not None:
							# module found
							if ship_upgrade_info[_info]['ucType'] == "_SkipBomber":
								module = module_data[ship_upgrade_info[_info]['components']['skipBomber'][0]]['planes'][0]
								module_id = str(game_data[module]['id'])
								del module
						else:
							# module not found add it to module list
							# find module id in game data
							module_info = game_data[_info]
							new_module_list_data = {
								"profile": {},
								"name": module_info['name'],
								"image": None,
								"tag": _info,
								"module_id_str": module_info['index'],
								"module_id": module_info['id'],
								"type": module_info['ucType'],
								"price_credit": module_info['costCR'],
							}
							module_list[str(module_info['id'])] = new_module_list_data.copy()
							module_id = str(module_info['id'])
					except IndexError as e:
						# we did an oopsie
						continue

					# update module list items with more information
					if ship_upgrade_info[_info]['ucType'] == '_Hull':
						# get secondary information
						if int(module_id) not in ship['modules']['hull']:
							ship['modules']['hull'].append(int(module_id))
						hull = module_data[ship_upgrade_info[_info]['components']['hull'][0]]
						if 'hull' not in module_list[module_id]['profile']:
							module_list[module_id]['profile']['hull'] = {
								"rudderTime": 0,
								"turnRadius": 0,
								'detect_distance_by_ship': 0,
								'detect_distance_by_plane': 0,
							}
						# standard information
						module_list[module_id]['profile']['hull']['health'] = hull['health']
						module_list[module_id]['profile']['hull']['rudderTime'] = hull['rudderTime']
						module_list[module_id]['profile']['hull']['turnRadius'] = hull['turningRadius']
						module_list[module_id]['profile']['hull']['detect_distance_by_ship'] = hull['visibilityFactor']
						module_list[module_id]['profile']['hull']['detect_distance_by_plane'] = hull['visibilityFactorByPlane']
						module_list[module_id]['profile']['hull']['armor'] = dict((k,v) for k, v in hull['armor'].items() if v > 0)

						# submarines information
						if ship['type'] == 'Submarine':
							if 'SubmarineBattery' in hull:
								module_list[module_id]['profile']['hull']['battery'] = hull['SubmarineBattery'].copy()
							module_list[module_id]['profile']['hull']['oilLeakDuration'] = hull['oilLeakDuration']


						# secondary battery information
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
										'name': game_data[turret_data['name']]['name'],
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
							module_list[module_id]['profile']['atba']['range'] = atba['maxDist']

						# getting aa information and calculate mbAA
						if len(ship_upgrade_info[_info]['components']['airDefense']) > 0:
							module_list[module_id]['profile']['anti_air'] = {
								'hull': ship_upgrade_info[_info]['components']['airDefense'][0][0],
								'near': {'damage': 0, 'damage_with_dfaa': 0, 'hitChance': 0},
								'medium': {'damage': 0, 'damage_with_dfaa': 0, 'hitChance': 0},
								'far': {'damage': 0, 'damage_with_dfaa': 0, 'hitChance': 0},
								'flak': {'damage': 0, 'damage_with_dfaa': 0, },
							}

							min_aa_range = inf
							max_aa_range = -inf

							# grab anti-air guns information
							aa_defense = ship_upgrade_info[_info]['components']['airDefense'][0]
							aa_defense = module_data[aa_defense]

							has_dfaa = False
							dfaa_stats = {}
							for c in ship_list[s]['consumables']:
								for c_index, c_type in ship_list[s]['consumables'][c]['abils']:
									if "AirDefenseDisp" in c_index:
										has_dfaa = True
										dfaa_stats = game_data[c_index][c_type]
										break

							if has_dfaa:
								module_list[module_id]['profile']['anti_air']['dfaa_stat'] = dfaa_stats.copy()

							# finding details of passive AA
							for a in [a for a in aa_defense if 'med' in a.lower() or 'near' in a.lower()]:
								aa_data = aa_defense[a]
								if aa_data['type'] == 'near':
									module_list[module_id]['profile']['anti_air']['near']['damage'] += aa_data['areaDamage'] / aa_data['areaDamagePeriod']
									module_list[module_id]['profile']['anti_air']['near']['range'] = aa_data['maxDistance']
									module_list[module_id]['profile']['anti_air']['near']['hitChance'] = aa_data['hitChance']
									if has_dfaa:
										module_list[module_id]['profile']['anti_air']['near']['damage_with_dfaa'] += module_list[module_id]['profile']['anti_air']['near']['damage'] * dfaa_stats['areaDamageMultiplier']
								if aa_data['type'] == 'medium':
									module_list[module_id]['profile']['anti_air']['medium']['damage'] += aa_data['areaDamage'] / aa_data['areaDamagePeriod']
									module_list[module_id]['profile']['anti_air']['medium']['range'] = aa_data['maxDistance']
									module_list[module_id]['profile']['anti_air']['medium']['hitChance'] = aa_data['hitChance']
									if has_dfaa:
										module_list[module_id]['profile']['anti_air']['medium']['damage_with_dfaa'] += module_list[module_id]['profile']['anti_air']['medium']['damage'] * dfaa_stats['areaDamageMultiplier']
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
										if has_dfaa:
											module_list[module_id]['profile']['anti_air']['far']['damage_with_dfaa'] += module_list[module_id]['profile']['anti_air']['far']['damage'] * dfaa_stats['areaDamageMultiplier']
									else:
										# flaks
										module_list[module_id]['profile']['anti_air']['flak']['count'] = aa_data['innerBubbleCount'] + aa_data['outerBubbleCount']
										module_list[module_id]['profile']['anti_air']['flak']['damage'] += int(aa_data['bubbleDamage'] * (aa_data['bubbleDuration'] * 2 + 1))  # but why though
										module_list[module_id]['profile']['anti_air']['flak']['min_range'] = aa_data['minDistance']
										module_list[module_id]['profile']['anti_air']['flak']['max_range'] = aa_data['maxDistance']
										module_list[module_id]['profile']['anti_air']['flak']['hitChance'] = aa_data['hitChance']
										if has_dfaa:
											module_list[module_id]['profile']['anti_air']['flak']['damage_with_dfaa'] += module_list[module_id]['profile']['anti_air']['flak']['damage'] * dfaa_stats['bubbleDamageMultiplier']

									min_aa_range = min(min_aa_range, aa_data['minDistance'])
									max_aa_range = max(max_aa_range, aa_data['maxDistance'])

							module_list[module_id]['profile']['anti_air']['min_range'] = min_aa_range
							module_list[module_id]['profile']['anti_air']['max_range'] = max_aa_range

							# calculate mbAA rating
							near_damage = module_list[module_id]['profile']['anti_air']['near']['damage'] * module_list[module_id]['profile']['anti_air']['near']['hitChance']
							mid_damage = module_list[module_id]['profile']['anti_air']['medium']['damage'] * module_list[module_id]['profile']['anti_air']['medium']['hitChance'] * 1.5
							far_damage = module_list[module_id]['profile']['anti_air']['far']['damage'] * module_list[module_id]['profile']['anti_air']['far']['hitChance'] * 2
							combined_aa_damage = near_damage + mid_damage + far_damage


							near_damage_with_dfaa = module_list[module_id]['profile']['anti_air']['near']['damage_with_dfaa'] * module_list[module_id]['profile']['anti_air']['near']['hitChance']
							mid_damage_with_dfaa = module_list[module_id]['profile']['anti_air']['medium']['damage_with_dfaa'] * module_list[module_id]['profile']['anti_air']['medium']['hitChance'] * 1.5
							far_damage_with_dfaa = module_list[module_id]['profile']['anti_air']['far']['damage_with_dfaa'] * module_list[module_id]['profile']['anti_air']['far']['hitChance'] * 2
							combined_aa_damage_with_dfaa = near_damage_with_dfaa + mid_damage_with_dfaa + far_damage_with_dfaa

							aa_rating = 0
							aa_rating_with_dfaa = 0
							# aa rating scaling with range
							if combined_aa_damage > 0:
								aa_range_scaling = max(1, module_list[module_id]['profile']['anti_air']['max_range'] / 5800)  # why 5800m? because thats the range of most ships' aa
								if aa_range_scaling > 1:
									aa_range_scaling = aa_range_scaling ** 2
								aa_rating += combined_aa_damage * aa_range_scaling
								aa_rating_with_dfaa += combined_aa_damage_with_dfaa * aa_range_scaling

							# aa rating scaling with flak
							if module_list[module_id]['profile']['anti_air']['flak']['damage'] > 0:
								flak_data = module_list[module_id]['profile']['anti_air']['flak']
								aa_rating += (flak_data['count'] * flak_data['hitChance']) * 5
								aa_rating_with_dfaa += (flak_data['count'] * flak_data['hitChance']) * 5

							# aa rating scaling with tier
							module_list[module_id]['profile']['anti_air']['rating'] = tuple(int(aa_rating / int(min(10, tier))) for tier in range(1, 12))
							module_list[module_id]['profile']['anti_air']['rating_with_dfaa'] = tuple(int(aa_rating_with_dfaa / int(min(10, tier))) for tier in range(1, 12))

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
									'range': airsup_info['maxDist'],
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
						if int(module_id) not in ship['modules']['artillery']:
							ship['modules']['artillery'].append(int(module_id))

						# get turret parameter
						new_turret_data = {
							'shotDelay': 0,
							'caliber': 0,
							'numBarrels': 0,
							'burn_probability': 0,
							'sigma': 0,
							'range': 0,
							'dispersion_h': {},
							'dispersion_v': {},
							'transverse_speed': 0,
							'pen': {'he': 0, 'ap': 0, 'cs': 0},
							'max_damage': {'he': 0, 'ap': 0, 'cs': 0},
							'gun_dpm': {'he': 0, 'ap': 0, 'cs': 0},
							'speed': {'he': 0, 'ap': 0, 'cs': 0},
							'krupp': {'he': 0, 'ap': 0, 'cs': 0},
							'mass': {'he': 0, 'ap': 0, 'cs': 0},
							'drag': {'he': 0, 'ap': 0, 'cs': 0},
							'ammo_name': {'he': '', 'ap': '', 'cs': ''},
							'normalization': {'he': 0, 'ap': 0, 'cs': 0},
							'fuse_time': {'he': 0, 'ap': 0, 'cs': 0},
							'fuse_time_threshold': {'he': 0, 'ap': 0, 'cs': 0},
							'ricochet': {'he': 0, 'ap': 0, 'cs': 0},
							'ricochet_always': {'he': 0, 'ap': 0, 'cs': 0},
							'turrets': {}
						}
						if 'artillery' not in module_list[module_id]['profile']:
							module_list[module_id]['profile']['artillery'] = {}

						gun = ship_upgrade_info[_info]['components']['artillery'][0]
						new_turret_data['sigma'] = module_data[gun]['sigmaCount']
						new_turret_data['range'] = module_data[gun]['maxDist']
						new_turret_data['taperDist'] = module_data[gun]['taperDist']

						gun = [module_data[gun][turret] for turret in [g for g in module_data[gun] if 'HP' in g]]
						for turret_data in gun:  # for each turret
							# add turret type and count
							# find dispersion
							# see https://forum.worldofwarships.eu/topic/73542-unified-thread-for-accuracy-dispersion-in-wows/
							turret_name = game_data[turret_data['name']]['name']

							if turret_name not in new_turret_data['turrets']:
								new_turret_data['turrets'][turret_name] = {
									'numBarrels': int(turret_data['numBarrels']),
									'count': 1,
									'armor': dict((k,v) for k, v in turret_data['armor'].items() if v > 0),
								}
							else:
								new_turret_data['turrets'][turret_name]['count'] += 1

							h_disp_at_ideal = turret_data['idealRadius'] * 30
							range_for_ideal = turret_data['idealDistance'] * 30
							for r_i in range(5, 35, 5):
								r = min(r_i * 1000, int(new_turret_data['range']))

								if r > new_turret_data['taperDist']:
									h_disp = lerp(turret_data['minRadius'] * 30, h_disp_at_ideal, r / range_for_ideal)
								else:
									h_disp = lerp(0, h_disp_at_ideal, r / range_for_ideal)
								v_disp = h_disp * turret_data['radiusOnMax']

								new_turret_data['dispersion_h'][str(r)] = round(h_disp)
								new_turret_data['dispersion_v'][str(r)] = round(v_disp)

							# get caliber, reload, and number of guns per turret
							new_turret_data['caliber'] = turret_data['barrelDiameter']
							new_turret_data['shotDelay'] = turret_data['shotDelay']
							new_turret_data['numBarrels'] = int(turret_data['numBarrels'])
							new_turret_data['transverse_speed'] = turret_data['rotationSpeed'][0]

							# get some information about the shells fired by the turret
							for a in turret_data['ammoList']:
								ammo = game_data[a]
								if ammo['ammoType'] == 'HE':
									new_turret_data['burn_probability'] = int(ammo['burnProb'] * 100)
									new_turret_data['pen']['he'] = int(ammo['alphaPiercingHE'])
									new_turret_data['max_damage']['he'] = int(ammo['alphaDamage'])
									new_turret_data['gun_dpm']['he'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
									new_turret_data['speed']['he'] = ammo['bulletSpeed']
									new_turret_data['krupp']['he'] = ammo['bulletKrupp']
									new_turret_data['mass']['he'] = ammo['bulletMass']
									new_turret_data['drag']['he'] = ammo['bulletAirDrag']
									new_turret_data['normalization']['he'] = ammo['bulletCapNormalizeMaxAngle']
									new_turret_data['fuse_time']['he'] = ammo['bulletDetonator']
									new_turret_data['fuse_time_threshold']['he'] = ammo['bulletDetonatorThreshold']
									new_turret_data['ricochet']['he'] = ammo['bulletRicochetAt']
									new_turret_data['ricochet_always']['he'] = ammo['bulletAlwaysRicochetAt']
									new_turret_data['ammo_name']['he'] = ammo['name']
								if ammo['ammoType'] == 'CS':  # SAP rounds
									new_turret_data['pen']['cs'] = int(ammo['alphaPiercingCS'])
									new_turret_data['max_damage']['cs'] = int(ammo['alphaDamage'])
									new_turret_data['gun_dpm']['cs'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
									new_turret_data['speed']['cs'] = ammo['bulletSpeed']
									new_turret_data['krupp']['cs'] = ammo['bulletKrupp']
									new_turret_data['mass']['cs'] = ammo['bulletMass']
									new_turret_data['drag']['cs'] = ammo['bulletAirDrag']
									new_turret_data['normalization']['cs'] = ammo['bulletCapNormalizeMaxAngle']
									new_turret_data['fuse_time']['cs'] = ammo['bulletDetonator']
									new_turret_data['fuse_time_threshold']['cs'] = ammo['bulletDetonatorThreshold']
									new_turret_data['ricochet']['cs'] = ammo['bulletRicochetAt']
									new_turret_data['ricochet_always']['cs'] = ammo['bulletAlwaysRicochetAt']
									new_turret_data['ammo_name']['cs'] = ammo['name']
								if ammo['ammoType'] == 'AP':
									new_turret_data['max_damage']['ap'] = int(ammo['alphaDamage'])
									new_turret_data['gun_dpm']['ap'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
									new_turret_data['speed']['ap'] = ammo['bulletSpeed']
									new_turret_data['krupp']['ap'] = ammo['bulletKrupp']
									new_turret_data['mass']['ap'] = ammo['bulletMass']
									new_turret_data['drag']['ap'] = ammo['bulletAirDrag']
									new_turret_data['normalization']['ap'] = ammo['bulletCapNormalizeMaxAngle']
									new_turret_data['fuse_time']['ap'] = ammo['bulletDetonator']
									new_turret_data['fuse_time_threshold']['ap'] = ammo['bulletDetonatorThreshold']
									new_turret_data['ricochet']['ap'] = ammo['bulletRicochetAt']
									new_turret_data['ricochet_always']['ap'] = ammo['bulletAlwaysRicochetAt']
									new_turret_data['ammo_name']['ap'] = ammo['name']

							module_list[module_id]['profile']['artillery'] = new_turret_data.copy()
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Torpedoes':  # torpedooes
						if int(module_id) not in ship['modules']['torpedoes']:
							ship['modules']['torpedoes'].append(int(module_id))
						# get torps parameter
						gun = ship_upgrade_info[_info]['components']['torpedoes'][0]
						gun = module_data[gun]
						new_turret_data = {
							'turrets': {}
						}

						turret_data = None
						for g in [turret for turret in [g for g in gun if 'HP' in g]]:  # for each launcher
							turret_data = gun[g]
							# add turret type and count
							turret_name = game_data[turret_data['name']]['name']
							if turret_name not in new_turret_data['turrets']:
								new_turret_data['turrets'][turret_name] = {
									'numBarrels': int(turret_data['numBarrels']),
									'count': 1,
								}
							else:
								new_turret_data['turrets'][turret_name]['count'] += 1

						projectile = game_data[turret_data['ammoList'][0]]
						new_turret_data['numBarrels'] = int(turret_data['numBarrels'])
						new_turret_data['shotDelay'] = turret_data['shotDelay']
						new_turret_data['max_damage'] = int(projectile['alphaDamage'] / 3 + projectile['damage'])
						new_turret_data['flood_chance'] = int(projectile['uwCritical'] * 100)
						new_turret_data['torpedo_speed'] = projectile['speed']
						new_turret_data['is_deep_water'] = projectile['isDeepWater']
						new_turret_data['range'] = projectile['maxDist'] * 30 / 1000
						new_turret_data['spotting_range'] = projectile['visibilityFactor']
						if ship['type'] == 'Submarine':
							new_turret_data['loaders'] = {}
							if 'loaders' in gun:
								for tubes, location in gun['loaders']:
									for l in location:
										if str(l) not in new_turret_data['loaders']:
											new_turret_data['loaders'][str(l)] = [tubes]
										else:
											new_turret_data['loaders'][str(l)].append(tubes)
							if 'SubmarineTorpedoParams' in projectile:
								new_turret_data['shutoff_distance'] = projectile['SubmarineTorpedoParams']['dropTargetAtDistance']

						module_list[module_id]['profile']['torpedoes'] = new_turret_data.copy()
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Sonar':  # submarine pingers
						if int(module_id) not in ship['modules']['pinger']:
							ship['modules']['pinger'].append(int(module_id))
						# get torps parameter
						gun = ship_upgrade_info[_info]['components']['pinger'][0]
						gun = module_data[gun]
						new_turret_data = {
							"shotDelay": gun['waveReloadTime'],
							"range": gun['waveDistance'],
							"ping_effect_duration": [sector['lifetime'] for sector in gun['sectorParams']],
							"ping_effect_width": [sector['width'] for sector in gun['sectorParams']],
						}
						module_list[module_id]['profile']['pinger'] = new_turret_data.copy()
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Fighter':  # rawkets
						ship['modules']['fighter'].append(int(module_id))
						planes = ship_upgrade_info[_info]['components']['fighter'][0]
						planes = module_data[planes]['planes']
						module_list[module_id] = {}
						module_list[module_id]['module_id'] = int(module_id)
						module_list[module_id]['module_id_str'] = plane['index']
						module_list[module_id]['type'] = 'Fighter'
						module_list[module_id]["squadron"] = [{} for _ in planes]

						for p_i, p in enumerate(planes):
							plane = game_data[p]  # get rocket params
							# adding missing information for tactical squadrons
							projectile = game_data[plane['bombName']]

							module_list[module_id]["squadron"][p_i] = {
								'name': plane['name'],
								'attack_size': plane['attackerSize'],
								'squad_size': plane['numPlanesInSquadron'],
								'speed_multiplier': plane['speedMax'],
								'hangarSettings': plane['hangarSettings'].copy(),
								'attack_cooldown': plane['attackCooldown'],
								'spotting_range': plane['visibilityFactor'],
								'spotting_range_plane': plane['visibilityFactorByPlane'],
								'consumables': plane['PlaneAbilities'],
								'profile': {
									"fighter": {
										'aiming_time': plane['aimingHeight'] / plane['aimingTime'], # time from one click the fire button to when the rocket fires
										'max_damage': int(projectile['alphaDamage']),
										'rocket_type': projectile['ammoType'],
										'burn_probability': int(projectile['burnProb'] * 100),
										'rocket_pen': int(projectile['alphaPiercingHE']),
										'max_health': int(plane['maxHealth']),
										'cruise_speed': int(plane['speedMoveWithBomb']),
										'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
										'payload': int(plane['attackCount']),
										'payload_name': projectile['name']
									}
								}
							}
						continue

					if ship_upgrade_info[_info]['ucType'] == '_TorpedoBomber':
						if int(module_id) not in ship['modules']['torpedo_bomber']:
							ship['modules']['torpedo_bomber'].append(int(module_id))
						planes = ship_upgrade_info[_info]['components']['torpedoBomber'][0]
						planes = module_data[planes]['planes']
						module_list[module_id] = {}
						module_list[module_id]['module_id'] = int(module_id)
						module_list[module_id]['module_id_str'] = plane['index']
						module_list[module_id]['type'] = 'Torpedo Bomber'
						module_list[module_id]["squadron"] = [{} for _ in planes]
						for p_i, p in enumerate(planes):
							plane = game_data[p]  # get params
							# adding missing information for tactical squadrons
							projectile = game_data[plane['bombName']]
							module_list[module_id]["squadron"][p_i] = {
								'name': plane['name'],
								'attack_size': plane['attackerSize'],
								'squad_size': plane['numPlanesInSquadron'],
								'speed_multiplier': plane['speedMax'],
								'hangarSettings': plane['hangarSettings'].copy(),
								'attack_cooldown': plane['attackCooldown'],
								'spotting_range': plane['visibilityFactor'],
								'spotting_range_plane': plane['visibilityFactorByPlane'],
								'consumables': plane['PlaneAbilities'],
								'profile': {
									"torpedo_bomber": {
										'cruise_speed': int(plane['speedMoveWithBomb']),
										'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
										'max_damage': int((projectile['alphaDamage'] / 3) + projectile['damage']),
										'max_health': int(plane['maxHealth']),
										'flood_chance': int(projectile['uwCritical'] * 100),
										'torpedo_speed': projectile['speed'],
										'is_deep_water': projectile['isDeepWater'],
										'range': projectile['maxDist'] * 30 / 1000,
										'payload': int(plane['projectilesPerAttack']),
										'payload_name': projectile['name'],
										'arming_range': int(projectile['speed'] / 1.944) * projectile['armingTime'] * 5.2
									}
								}
							}
						continue

					if ship_upgrade_info[_info]['ucType'] == '_DiveBomber':
						if int(module_id) not in ship['modules']['dive_bomber']:
							ship['modules']['dive_bomber'].append(int(module_id))
						planes = ship_upgrade_info[_info]['components']['diveBomber'][0]
						planes = module_data[planes]['planes']
						module_list[module_id] = {}
						module_list[module_id]['module_id'] = int(module_id)
						module_list[module_id]['module_id_str'] = plane['index']
						module_list[module_id]['type'] = 'Dive Bomber'
						module_list[module_id]["squadron"] = [{} for _ in planes]

						for p_i, p in enumerate(planes):
							plane = game_data[p]  # get params
							# adding missing information for tactical squadrons
							projectile = game_data[plane['bombName']]

							module_list[module_id]["squadron"][p_i] = {
								'name': plane['name'],
								'attack_size': plane['attackerSize'],
								'squad_size': plane['numPlanesInSquadron'],
								'speed_multiplier': plane['speedMax'],
								'hangarSettings': plane['hangarSettings'].copy(),
								'attack_cooldown': plane['attackCooldown'],
								'spotting_range': plane['visibilityFactor'],
								'spotting_range_plane': plane['visibilityFactorByPlane'],
								'consumables': plane['PlaneAbilities'],
								'profile': {
									"dive_bomber": {
										'cruise_speed': int(plane['speedMoveWithBomb']),
										'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
										'max_damage': projectile['alphaDamage'],
										'burn_probability': projectile['burnProb'] * 100,
										'max_health': int(plane['maxHealth']),
										'payload': int(plane['attackCount']),
										'payload_name': projectile['name'],
										'bomb_type': projectile['ammoType'],
										'bomb_pen': int(projectile['alphaPiercingHE']),
									}
								}
							}
						continue

					if ship_upgrade_info[_info]['ucType'] == '_SkipBomber':
						if int(module_id) not in ship['modules']['skip_bomber']:
							ship['modules']['skip_bomber'].append(int(module_id))
						planes = ship_upgrade_info[_info]['components']['skipBomber'][0]
						planes = module_data[planes]['planes']
						module_list[module_id] = {}
						module_list[module_id]['module_id'] = int(module_id)
						module_list[module_id]['module_id_str'] = plane['index']
						module_list[module_id]['type'] = 'Skip Bomber'
						module_list[module_id]["squadron"] = [{} for _ in planes]

						for p_i, p in enumerate(planes):
							plane = game_data[p]  # get params
							# adding missing information for tactical squadrons
							projectile = game_data[plane['bombName']]
							ship_list[s]['modules']['skip_bomber'] += [plane['id']]

							module_list[module_id]["squadron"][p_i] = {
								'name': plane['name'],
								'attack_size': plane['attackerSize'],
								'squad_size': plane['numPlanesInSquadron'],
								'speed_multiplier': plane['speedMax'],
								'hangarSettings': plane['hangarSettings'].copy(),
								'attack_cooldown': plane['attackCooldown'],
								'spotting_range': plane['visibilityFactor'],
								'spotting_range_plane': plane['visibilityFactorByPlane'],
								'module_id': module_id,
								'module_id_str': plane['index'],
								'consumables': plane['PlaneAbilities'],
								'profile': {
									"skip_bomber": {
										'cruise_speed': int(plane['speedMoveWithBomb']),
										'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
										'max_damage': int(projectile['alphaDamage']),
										'burn_probability': projectile['burnProb'] * 100,
										'max_health': int(plane['maxHealth']),
										'payload': int(plane['attackCount']),
										'payload_name': projectile['name'],
										'bomb_pen': int(projectile['alphaPiercingHE']),
										'bomb_type': projectile['ammoType'],
									}
								}
							}
						continue
		except Exception as e:
			logger.error("at ship id " + s)
			if not type(e) == KeyError:
				logger.error("Ship " + s + " is not known to GameParams.data or accessing incorrect key in GameParams.json")
				logger.error("Update your GameParams JSON file(s)")
			traceback.print_exc()


def create_ship_tags():
	global ship_list
	# generate ship tags for searching purpose via the "show ships" command
	logger.info("Generating ship search tags")

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
			ship = ship_list[s]
			nat = nation_dictionary[ship['nation']]
			tags = {
				"ship": [],
				"consumables": [],
				"gun_caliber": [],
			}
			ship_type = ship['type']
			hull_class = hull_classification_converter[ship_type]
			if ship_type == 'AirCarrier':
				ship_type = 'Aircraft Carrier'
			tier = ship['tier']  # add tier to search
			prem = ship['is_premium']  # is bote premium
			ship_speed = 0
			for e in ship['modules']['engine']:
				max_speed = module_list[str(e)]['profile']['engine']['max_speed']
				ship_speed = max(ship_speed, max_speed)
			# add tags based on speed
			if ship_speed <= ship_tags[SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD]]['max_threshold']:
				tags['ship'].append(SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD])
			if ship_speed >= ship_tags[SHIP_TAG_LIST[SHIP_TAG.FAST_SPD]]['min_threshold']:
				tags['ship'].append(SHIP_TAG_LIST[SHIP_TAG.FAST_SPD])
			concealment = {
				'detect_distance_by_plane': 0,
				'detect_distance_by_ship': 0,
			}
			for e in ship['modules']['hull']:
				c = module_list[str(e)]['profile']['hull']
				concealment['detect_distance_by_ship'] = max(concealment['detect_distance_by_ship'], c['detect_distance_by_ship'])
				concealment['detect_distance_by_plane'] = max(concealment['detect_distance_by_plane'], c['detect_distance_by_plane'])
			# add tags based on detection range
			if concealment['detect_distance_by_plane'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG.STEALTH]]['min_air_spot_range'] or concealment['detect_distance_by_ship'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG.STEALTH]]['min_sea_spot_range']:
				tags['ship'].append(SHIP_TAG_LIST[SHIP_TAG.STEALTH])
			# add tags based on gun firerate
			try:
				# some ships have main battery guns
				fireRate = inf
				for g in ship['modules']['artillery']:
					fireRate = min(fireRate, module_list[str(g)]['profile']['artillery']['shotDelay'])
			except TypeError:
				# some dont *ahemCVsahem*
				fireRate = inf
			if fireRate <= ship_tags[SHIP_TAG_LIST[SHIP_TAG.FAST_GUN]]['max_threshold'] and not ship_type == 'Aircraft Carrier':
				tags['ship'].append(SHIP_TAG_LIST[SHIP_TAG.FAST_GUN])
				tags['ship'].append('dakka')

			# add gun caliber tag
			caliber_list = set()
			for g in ship['modules']['artillery']:
				caliber_list = caliber_list | {int(module_list[str(g)]['profile']['artillery']['caliber'] * 1000)}
			tags['gun_caliber'].extend(caliber_list)

			# add tags based on aa
			for h in ship_list[s]['modules']['hull']:
				if 'anti_air' in module_list[str(h)]['profile']:
					aa = module_list[str(h)]['profile']['anti_air']
					if aa['rating'][tier - 1] > 50 or aa['max_range'] > ship_tags[SHIP_TAG_LIST[SHIP_TAG.AA]]['min_aa_range']:
						if SHIP_TAG_LIST[SHIP_TAG.AA] not in tags:
							tags['ship'].append(SHIP_TAG_LIST[SHIP_TAG.AA])

			# add tags based on consumables
			for slot in ship_list[s]['consumables']:
				for consumable_index, consumable_variant in ship_list[s]['consumables'][slot]['abils']:
					consumable_data = game_data[consumable_index][consumable_variant]
					try:
						tags['consumables'].extend(list(consumable_data_to_string(consumable_data)))
					except IndexError:
						pass

			# add tags for non-researchable ships
			if ship['price_special_type']:
				price_special_type_string = {
						'coal': ["coal"],
						'paragon_xp': ["research bureau", "research"],
						'steel': ["steel"],
				}[ship['price_special_type']]
				tags['ship'].extend(price_special_type_string + ['armory'])

			tags['ship'].extend([nat, f't{tier}', ship_type, ship_type + 's', hull_class])
			ship_list[s]['tags'] = tags
			if prem:
				ship_list[s]['tags']['ship'] += ['premium']
		except Exception as e:
			logger.warning(f"{type(e)} {e} at ship id {s}")
			traceback.print_exc(type(e), e, None)

def create_upgrade_abbr():
	logger.info("Creating abbreviation for upgrades")
	global upgrade_abbr_list

	if len(upgrade_list) == 0:
		logger.warning("Upgrade list is empty.")
		load_upgrade_list()

	abbr_added = []
	for u in upgrade_list:
		upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(160), chr(32))  # replace weird 0-width character with a space
		upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(10), chr(32))  # replace random ass newline character with a space
		key = ''.join([i[0] for i in upgrade_list[u]['name'].split()]).lower()
		if key in abbr_added:  # if the abbreviation of this upgrade is in the list already
			key = ''.join([i[:2].title() for i in upgrade_list[u]['name'].split()]).lower()[:-1]  # create a new abbreviation by using the first 2 characters
	# add this abbreviation
		upgrade_abbr_list[u] = {
			"upgrade": upgrade_list[u]['name'].lower(),
			"abbr": key,
			"upgrade_id": int(u)
		}
		abbr_added.append(key)

def load_cmdr_list():
	global cmdr_list

	logger.info("Fetching Commander List")
	cmdr_list.update(wows_encyclopedia.crews())

def load_consumable_list():
	global consumable_list

	logger.info("Creating consumable list")
	consumable_list.update(dict((str(game_data[i]['id']), game_data[i].copy()) for i in game_data if game_data[i]['typeinfo']['type'] == 'Ability'))
	for consumable in consumable_list:
		consumable_list[consumable]['consumable_id'] = consumable_list[consumable]['id']
		del consumable_list[consumable]['id']


def load_ship_builds():
	global ship_build, ship_list, skill_list
	assert sheet_id is not None

	from google.auth.transport.requests import Request
	from google.oauth2.credentials import Credentials
	from google_auth_oauthlib.flow import InstalledAppFlow
	from googleapiclient.discovery import build
	from googleapiclient.errors import HttpError

	# If modifying these scopes, delete the file token.json.
	SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

	creds = None
	# The file token.json stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token.json'):
		creds = Credentials.from_authorized_user_file('token.json', SCOPES)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('token.json', 'w') as token:
			token.write(creds.to_json())

	try:
		service = build('sheets', 'v4', credentials=creds)

		# Call the Sheets API
		sheet = service.spreadsheets()
		result = sheet.values().get(spreadsheetId=sheet_id, range='ship_builds!B:Z').execute()
		values = result.get('values', [])

		if not values:
			print('No data found.')
			return

		for row in values[1:]:
			if len(row) == 0:
				break

			build_ship_name = row[0]
			build_name = row[1]
			build_upgrades = row[2:8]
			build_skills = row[8:-1]
			build_cmdr = row[-1]

			# convert user name to utf8 ship name
			if build_ship_name.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside printable ?
				build_ship_name = ship_name_to_ascii[build_ship_name.lower()]  # convert to the appropriate name

			try:
				for i in ship_name_to_ascii:
					if build_ship_name == i:
						build_ship_name = ship_name_to_ascii[i]
						break
				ship_data = ship_list[[s for s in ship_list if ship_list[s]['name'].lower() == build_ship_name.lower()][0]]
				build_ship_name = ship_data['name']
			except IndexError:
				logger.warning(f"ship with name {build_ship_name} is not found in database. Skip for now.")
				continue
			data = {
				"name": build_name,
				"ship": build_ship_name,
				"build_id": "",
				"upgrades": [],
				"skills": [],
				"cmdr": build_cmdr,
				"errors": [],
			}
			# converting upgrades
			for u in build_upgrades:
				try:
					if u == '*':
						data['upgrades'].append(-1)
						continue

					for k, v in upgrade_abbr_list.items():
						if u.lower() in [v['abbr'].lower(), v['upgrade'].lower()]:
							data['upgrades'].append(v['upgrade_id'])
							break
				except IndexError:
					logger.warning(f"Upgrade [{u}] is not an upgrade!")
					data['errors'].append(BuildError.UPGRADE_INCORRECT)

			# converting skills
			total_skill_pts = 0
			skill_list_filtered = dict((s, skill_list[s]) for s in skill_list if skill_list[s]['tree'] == ship_data['type'])
			for s in build_skills:
				try:
					if not s:
						continue

					if s == '*':
						data['skills'].append(-1)
						continue

					has_no_match = True
					for k, v in skill_list_filtered.items():
						if s.lower() == v['name'].lower():
							data['skills'].append(v['skill_id'])
							total_skill_pts += v['y'] + 1
							has_no_match = False
							break

					if has_no_match:
						raise IndexError
				except IndexError:
					logger.warning(f"skill [{s}] is not an skill!")
					data['errors'].append(BuildError.SKILLS_INCORRECT)

			if not check_skill_order_valid(data['skills']):
				data['errors'].append(BuildError.SKILLS_ORDER_INVALID)
			if total_skill_pts > 21:
				data['errors'].append(BuildError.SKILL_POINTS_EXCEED)
			elif total_skill_pts < 21:
				data['errors'].append(BuildError.SKILLS_POTENTIALLY_MISSING)
			data['errors'] = tuple(set(data['errors']))
			if data['errors']:
				build_error_strings = ', '.join(' '.join(i.name.split("_")).title() for i in data['errors'])
				logger.warning(f"Build for ship [{build_ship_name} | {build_name}] has the following errors: {build_error_strings}")
				for e in data['errors']:
					print(f"Skill orders are:")
					for skill in data["skills"]:
						print(f"{skill_list[str(skill)]['name']:<32} ({skill_list[str(skill)]['y'] + 1})")
					if e == BuildError.SKILLS_POTENTIALLY_MISSING:
						print(f"Total skill points in this build: {total_skill_pts}")

			build_id = sha256(str(data).encode()).hexdigest()
			data['build_id'] = build_id
			if build_id not in ship_build:
				ship_build[build_id] = data.copy()
			else:
				logger.warning(f"Build for ship {build_ship_name} with id {build_id} exists!")
	except HttpError as err:
		print(err)


def post_process():
	logger.info("Creating hash digest")
	dictionaries = (ship_list, skill_list, module_list, upgrade_list, camo_list, cmdr_list, flag_list, legendary_upgrade_list, upgrade_list, consumable_list, upgrade_abbr_list, ship_build)
	for d in dictionaries:
		for k in d:
			d[k]['hash'] = sha256(str(d[k]).encode()).hexdigest()

def get_ship_by_id(value: int) -> dict:
	return [game_data[i] for i in game_data if 'id' in game_data[i] and game_data[i]['id'] == value][0]

def load():
	load_game_params()
	load_skill_list()
	load_module_list()
	load_ship_list()
	load_upgrade_list()
	load_consumable_list()
	update_ship_modules()
	create_ship_tags()
	load_ship_builds()
	post_process()

if __name__ == "__main__":
	load()