import wargaming, sys, traceback, time, json, logging, os, pickle

from pymongo import MongoClient
from itertools import count
from math import inf
from enum import IntEnum, auto
from scripts.constants import nation_dictionary, hull_classification_converter

game_data = {}
ship_list = {}
skill_list = {}
module_list = {}
upgrade_list = {}
camo_list = {}
cmdr_list = {}
flag_list = {}
upgrade_abbr_list = {}

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

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-5s %(message)s')

stream_handler.setFormatter(formatter)
stream_handler.addFilter(LogFilterBlacklist("RESUME", "RESUMED"))

logger = logging.getLogger("mackbot_data_loader")
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


# load config
with open(os.path.join(os.getcwd(), "data", "config.json")) as f:
	data = json.load(f)

mongodb_host = data['mongodb_host']

# get weegee's wows encyclopedia
WG = wargaming.WoWS(data['wg_token'], region='na', language='en')
wows_encyclopedia = WG.encyclopedia
ship_types = wows_encyclopedia.info()['ship_types']
ship_types["Aircraft Carrier"] = "Aircraft Carrier"

# define database stuff
database_client = None
try:
	database_client = MongoClient(mongodb_host)
except ConnectionError:
	logger.warning("MongoDB cannot be connected.")


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
		with open(os.path.join("./data", "skill_list.json")) as f:
			skill_list = json.load(f)

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
		return []

def load_module_list():
	global module_list
	# get modules (i.e. guns, hulls, planes)
	logger.info("Fetching Module List")
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
					logger.info(type(e), e)
			else:
				logger.info(type(e), e)
			break

def load_ship_list():
	logger.info("Fetching Ship List")
	global ship_list
	ship_list_file_name = 'ship_list'
	ship_list_file_dir = os.path.join(os.getcwd(), "data", ship_list_file_name)

	fetch_ship_list_from_wg = False
	# fetching from local
	if os.path.isfile(ship_list_file_dir):
		with open(ship_list_file_dir, 'rb') as f:
			ship_list = pickle.load(f)

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
		print("Cache complete")
	del ship_list_file_dir, ship_list_file_name, ship_list['ships_updated_at']


def load_upgrade_list():
	logger.info("Fetching Camo, Flags and Modification List")
	if len(ship_list) == 0:
		logger.info("Ship list is empty.")
		load_ship_list()

	if len(game_data) == 0:
		logger.info("No game data")
		load_game_params()

	global camo_list, flag_list, upgrade_list, legendary_upgrades
	for page_num in count(1):
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
				upgrade_list[uid]['tier_restriction'] = [str(t) for t in upgrade['shiplevel']]

				upgrade_list[uid]['tags'] += upgrade_list[uid]['type_restriction']
				upgrade_list[uid]['tags'] += upgrade_list[uid]['tier_restriction']

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
		logger.info("Game data is empty.")
		load_game_params()
	if len(ship_list) == 0:
		logger.info("Ship list is empty.")
		load_ship_list()
	# load_ship_params()
	if len(module_list) == 0:
		logger.info("Module list is empty.")
		load_module_list()

	ship_count = 0
	for s in ship_list:
		ship = ship_list[s]
		ship_count += 1
		if (ship_count % 50 == 0 and ship_count > 0) or (ship_count == len(ship_list)):
			logger.info(f"	{ship_count}/{len(ship_list)} ships")
		try:
			module_full_id_str = find_game_data_item(ship['ship_id_str'])[0]
			module_data = game_data[module_full_id_str]

			# grab consumables
			ship_list[s]['consumables'] = module_data['ShipAbilities'].copy()

			ship_upgrade_info = module_data['ShipUpgradeInfo']  # get upgradable modules

			# get credit and xp cost for ship research
			ship_list[s]['price_credit'] = ship_upgrade_info['costCR']
			ship_list[s]['price_xp'] = ship_upgrade_info['costXP']

			# is this a test boat?
			ship_list[s]['is_test_ship'] = module_data['group'] == 'demoWithoutStats'

			for _info in ship_upgrade_info:  # for each warship modules (e.g. hull, guns, fire-control)
				if type(ship_upgrade_info[_info]) == dict:  # if there are data
					try:
						module_id = find_module_by_tag(_info)
						if ship_upgrade_info[_info]['ucType'] == "_SkipBomber":
							module = module_data[ship_upgrade_info[_info]['components']['skipBomber'][0]]['planes'][0]
							module_id = str(game_data[module]['id'])
							del module
					except IndexError as e:
						# we did an oopsie
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Hull':
						# get secondary information
						hull = module_data[ship_upgrade_info[_info]['components']['hull'][0]]
						module_list[module_id]['profile']['hull']['rudderTime'] = hull['rudderTime']
						module_list[module_id]['profile']['hull']['turnRadius'] = hull['turningRadius']
						module_list[module_id]['profile']['hull']['detect_distance_by_ship'] = hull['visibilityFactor']
						module_list[module_id]['profile']['hull']['detect_distance_by_plane'] = hull['visibilityFactorByPlane']

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
							near_damage = module_list[module_id]['profile']['anti_air']['near']['damage'] * module_list[module_id]['profile']['anti_air']['near']['hitChance']
							mid_damage = module_list[module_id]['profile']['anti_air']['medium']['damage'] * module_list[module_id]['profile']['anti_air']['medium']['hitChance'] * 1.5
							far_damage = module_list[module_id]['profile']['anti_air']['far']['damage'] * module_list[module_id]['profile']['anti_air']['far']['hitChance'] * 2
							combined_aa_damage = near_damage + mid_damage + far_damage
							aa_rating = 0

							# aa rating scaling with range
							if combined_aa_damage > 0:
								aa_range_scaling = max(1, module_list[module_id]['profile']['anti_air']['max_range'] / 5800)  # why 5800m? because thats the range of most ships' aa
								if aa_range_scaling > 1:
									aa_range_scaling = aa_range_scaling ** 3
								aa_rating += (combined_aa_damage / (int(ship['tier']) * 9)) * aa_range_scaling

							# aa rating scaling with flak
							if module_list[module_id]['profile']['anti_air']['flak']['damage'] > 0:
								flak_data = module_list[module_id]['profile']['anti_air']['flak']
								aa_rating += flak_data['count'] * flak_data['hitChance'] * 2

							# aa rating scaling with tier
							aa_rating = (combined_aa_damage / (int(ship['tier']) * 10))
							module_list[module_id]['profile']['anti_air']['rating'] = int(aa_rating * 10)

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
						new_turret_data = {
							'shotDelay': 0,
							'caliber': 0,
							'numBarrels': 0,
							'burn_probability': 0,
							'pen_HE': 0,
							'pen_SAP': 0,
							'max_damage_he': 0,
							'max_damage_ap': 0,
							'max_damage_sap': 0,
							'sigma': 0,
							'range': 0,
							'dispersion_h': 0,
							'dispersion_v': 0,
							'transverse_speed': 0,
							'gun_dpm': {'he': 0, 'ap': 0, 'cs': 0},
							'speed': {'he': 0, 'ap': 0, 'cs': 0},
							'krupp': {'he': 0, 'ap': 0, 'cs': 0},
							'mass': {'he': 0, 'ap': 0, 'cs': 0},
							'drag': {'he': 0, 'ap': 0, 'cs': 0},
							'turrets': {}
						}

						gun = ship_upgrade_info[_info]['components']['artillery'][0]
						new_turret_data['sigma'] = module_data[gun]['sigmaCount']
						new_turret_data['range'] = module_data[gun]['maxDist']

						gun = [module_data[gun][turret] for turret in [g for g in module_data[gun] if 'HP' in g]]
						for turret_data in gun:  # for each turret
							# add turret type and count
							turret_name = game_data[turret_data['name']]['name']
							if turret_name not in new_turret_data['turrets']:
								new_turret_data['turrets'][turret_name] = {
									'numBarrels': int(turret_data['numBarrels']),
									'count': 1,
								}
							else:
								new_turret_data['turrets'][turret_name]['count'] += 1

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
									new_turret_data['pen_HE'] = int(ammo['alphaPiercingHE'])
									new_turret_data['max_damage_he'] = int(ammo['alphaDamage'])
									new_turret_data['gun_dpm']['he'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
									new_turret_data['speed']['he'] = ammo['bulletSpeed']
									new_turret_data['krupp']['he'] = ammo['bulletKrupp']
									new_turret_data['mass']['he'] = ammo['bulletMass']
									new_turret_data['drag']['he'] = ammo['bulletAirDrag']
								if ammo['ammoType'] == 'CS':  # SAP rounds
									new_turret_data['pen_SAP'] = int(ammo['alphaPiercingCS'])
									new_turret_data['max_damage_sap'] = int(ammo['alphaDamage'])
									new_turret_data['gun_dpm']['cs'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
									new_turret_data['speed']['cs'] = ammo['bulletSpeed']
									new_turret_data['krupp']['cs'] = ammo['bulletKrupp']
									new_turret_data['mass']['cs'] = ammo['bulletMass']
									new_turret_data['drag']['cs'] = ammo['bulletAirDrag']
								if ammo['ammoType'] == 'AP':
									new_turret_data['max_damage_ap'] = int(ammo['alphaDamage'])
									new_turret_data['gun_dpm']['ap'] += int(ammo['alphaDamage'] * turret_data['numBarrels'] * 60 / turret_data['shotDelay'])
									new_turret_data['speed']['ap'] = ammo['bulletSpeed']
									new_turret_data['krupp']['ap'] = ammo['bulletKrupp']
									new_turret_data['mass']['ap'] = ammo['bulletMass']
									new_turret_data['drag']['ap'] = ammo['bulletAirDrag']

							module_list[module_id]['profile']['artillery'] = new_turret_data.copy()
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Torpedoes':  # torpedooes
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

						module_list[module_id]['profile']['torpedoes'] = new_turret_data.copy()
						continue

					if ship_upgrade_info[_info]['ucType'] == '_Fighter':  # rawkets
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
								'bomb_type': projectile['ammoType'],
								'bomb_pen': int(projectile['alphaPiercingHE']),
								'profile': {
									"dive_bomber": {
										'cruise_speed': int(plane['speedMoveWithBomb']),
										'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
										'max_damage': projectile['alphaDamage'],
										'burn_probability': projectile['burnProb'] * 100,
										'max_health': int(plane['maxHealth']),
										'payload': int(plane['attackCount']),
										'payload_name': projectile['name']
									}
								}
							}
						continue

					if ship_upgrade_info[_info]['ucType'] == '_SkipBomber':
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
								'bomb_type': projectile['ammoType'],
								'bomb_pen': int(projectile['alphaPiercingHE']),
								'module_id': module_id,
								'module_id_str': plane['index'],
								'profile': {
									"skip_bomber": {
										'cruise_speed': int(plane['speedMoveWithBomb']),
										'max_speed': int(plane['speedMoveWithBomb'] * plane['speedMax']),
										'max_damage': int(projectile['alphaDamage']),
										'burn_probability': projectile['burnProb'] * 100,
										'max_health': int(plane['maxHealth']),
										'payload': int(plane['attackCount']),
										'payload_name': projectile['name']
									}
								}
							}
						continue
		except Exception as e:
			if not type(e) == KeyError:
				logger.error("at ship id " + s)
				logger.error("Ship " + s + " is not known to GameParams.data or accessing incorrect key in GameParams.json")
				logger.error("Update your GameParams JSON file(s)")
			traceback.print_exc()
	del ship_count


def create_ship_tags():
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
			nat = nation_dictionary[ship_list[s]['nation']]
			tags = []
			t = ship_list[s]['type']
			hull_class = hull_classification_converter[t]
			if t == 'AirCarrier':
				t = 'Aircraft Carrier'
			tier = ship_list[s]['tier']  # add tier to search
			prem = ship_list[s]['is_premium']  # is bote premium
			ship_speed = 0
			for e in ship_list[s]['modules']['engine']:
				max_speed = module_list[str(e)]['profile']['engine']['max_speed']
				ship_speed = max(ship_speed, max_speed)
			# add tags based on speed
			if ship_speed <= ship_tags[SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD]]['max_threshold']:
				tags += [SHIP_TAG_LIST[SHIP_TAG.SLOW_SPD]]
			if ship_speed >= ship_tags[SHIP_TAG_LIST[SHIP_TAG.FAST_SPD]]['min_threshold']:
				tags += [SHIP_TAG_LIST[SHIP_TAG.FAST_SPD]]
			concealment = {
				'detect_distance_by_plane': 0,
				'detect_distance_by_ship': 0,
			}
			for e in ship_list[s]['modules']['hull']:
				c = module_list[str(e)]['profile']['hull']
				concealment['detect_distance_by_ship'] = max(concealment['detect_distance_by_ship'], c['detect_distance_by_ship'])
				concealment['detect_distance_by_plane'] = max(concealment['detect_distance_by_plane'], c['detect_distance_by_plane'])
			# add tags based on detection range
			if concealment['detect_distance_by_plane'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG.STEALTH]]['min_air_spot_range'] or concealment['detect_distance_by_ship'] < ship_tags[SHIP_TAG_LIST[SHIP_TAG.STEALTH]]['min_sea_spot_range']:
				tags += [SHIP_TAG_LIST[SHIP_TAG.STEALTH]]
			# add tags based on gun firerate
			try:
				# some ships have main battery guns
				fireRate = inf
				for g in ship_list[s]['modules']['artillery']:
					fireRate = min(fireRate, module_list[str(g)]['profile']['artillery']['shotDelay'])
			except TypeError:
				# some dont *ahemCVsahem*
				fireRate = inf
			if fireRate <= ship_tags[SHIP_TAG_LIST[SHIP_TAG.FAST_GUN]]['max_threshold'] and not t == 'Aircraft Carrier':
				tags += [SHIP_TAG_LIST[SHIP_TAG.FAST_GUN], 'dakka']
			# add tags based on a
			for h in ship_list[s]['modules']['hull']:
				if 'anti_air' in module_list[str(h)]['profile']:
					aa = module_list[str(h)]['profile']['anti_air']
					if aa['rating'] > 50 or aa['max_range'] > ship_tags[SHIP_TAG_LIST[SHIP_TAG.AA]]['min_aa_range']:
						if SHIP_TAG_LIST[SHIP_TAG.AA] not in tags:
							tags += [SHIP_TAG_LIST[SHIP_TAG.AA]]

			tags += [nat, f't{tier}', t, t + 's', hull_class]
			ship_list[s]['tags'] = tags
			if prem:
				ship_list[s]['tags'] += ['premium']
		except Exception as e:
			logger.warning(f"{type(e)} {e} at ship id {s}")
			traceback.print_exc(type(e), e, None)

def create_upgrade_abbr():
	logger.info("Creating abbreviation for upgrades")
	global upgrade_abbr_list

	if len(upgrade_list) == 0:
		logger.info("Upgrade list is empty.")
		load_upgrade_list()

	for u in upgrade_list:
		upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(160), chr(32))  # replace weird 0-width character with a space
		upgrade_list[u]['name'] = upgrade_list[u]['name'].replace(chr(10), chr(32))  # replace random ass newline character with a space
		key = ''.join([i[0] for i in upgrade_list[u]['name'].split()]).lower()
		if key in upgrade_abbr_list:  # if the abbreviation of this upgrade is in the list already
			key = ''.join([i[:2].title() for i in upgrade_list[u]['name'].split()]).lower()[:-1]  # create a new abbreviation by using the first 2 characters
	# add this abbreviation
		upgrade_abbr_list[key] = {
			"upgrade": upgrade_list[u]['name'].lower(),
			"abbr": key,
			"upgrade_id": int(u)
		}

def load_cmdr_list():
	global cmdr_list
	logger.info("Fetching Commander List")
	cmdr_list = wows_encyclopedia.crews()

def load():
	load_game_params()
	load_skill_list()
	load_module_list()
	load_ship_list()
	load_upgrade_list()
	update_ship_modules()
	create_ship_tags()

if __name__ == "__main__":
	load()