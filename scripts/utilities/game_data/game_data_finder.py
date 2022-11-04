import pymongo, os

from string import ascii_letters
from typing import Union
from scripts.utilities.bot_data import command_list
from scripts.utilities.game_data.warships_data import *
from scripts.mackbot_exceptions import *
from scripts.mackbot_enums import SHIP_BUILD_FETCH_FROM
from scripts.mackbot_constants import cmdr_name_to_ascii

with open(os.path.join(os.getcwd(), "data", "ship_name_dict.json"), encoding='utf-8') as f:
	import json
	ship_name_to_ascii = json.load(f)
	del json

def get_ship_data(ship: str) -> dict:
	"""
	returns name, nation, images, ship type, tier of requested warship name along with recommended build.

	Arguments:
	 ship_list (dict): Local dictionary of ships. Should be set if database_client is None
	 database_client (pymongo.MongoClient):
	 ship (str): Name of ship data to be returned

	Returns:
		object: dict containing ship information

	Raises:
		InvalidShipName
		NoBuildFound
	"""
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside printable ?
			ship = ship_name_to_ascii[ship.lower()]  # convert to the appropriate name

		if database_client is not None:
			# connection to db
			query_result = database_client.mackbot_db.ship_list.find_one({
				"name": {"$regex": f"^{ship.lower()}$", "$options": "i"}
			})
			if query_result is None:
				# query returns no result
				raise NoShipFound
			else:
				return query_result
		else:
			# cannot connect to db
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

def get_consumable_data(consumable_index: str, consumable_variation: str) -> dict:
	"""
	returns information about a ship/aircraft consumable.

	Args:
		consumable_index (int): consumable index
		consumable_variation (str): variation of the consumable

	Returns:
		dict

	Raises:
		ConsumableNotFound
	"""
	if database_client is not None:
		query_result = database_client.mackbot_db.consumable_list.find_one({
			"index": consumable_index
		})
		if query_result is None:
			raise ConsumableNotFound
		else:
			del query_result['_id']
			d = {
				"name": query_result['name'],
				"description": query_result['description']
			}
			d.update(query_result[consumable_variation])
			return d
	else:
		consumable = consumable_list[consumable_index]
		d = {
			"name": consumable['name'],
			"description": consumable['description']
		}
		d.update(consumable[consumable_variation])
		return d

# find game data items by tags
def find_game_data_item(item: str) -> list:
	return [i for i in game_data if item in i]

def find_module_by_tag(x: str) -> Union[dict, None]:
	l = []
	for i in module_list:
		if 'tag' in module_list[i]:
			if x == module_list[i]['tag']:
				l += [i]
	if l:
		return l[0]
	else:
		return None

def load_ship_builds() -> None:
	# load ship builds from a local file
	if database_client is None:
		# database connection successful, we don't need to fetch from local cache
		return None

	logger.info('Fetching ship build file...')
	global ship_build, ship_build_competitive, ship_build_casual
	extract_from_web_failed = False
	ship_build_file_dir = os.path.join("data", "ship_builds.json")
	build_extract_from_cache = os.path.isfile(ship_build_file_dir)

	ship_build = {}
	# fetch ship builds and additional upgrade information
	if command_list['build']:
		if not build_extract_from_cache:
			# no build file found, retrieve from google sheets
			try:
				# extract_build_from_google_sheets(ship_build_file_dir, True)
				pass
			except:
				extract_from_web_failed = True

		if build_extract_from_cache or extract_from_web_failed:
			# local cache is found, open from local cache
			with open(ship_build_file_dir) as f:
				ship_build = json.load(f)


def get_ship_data(ship: str) -> dict:
	"""
	returns name, nation, images, ship type, tier of requested warship name along with recommended build.

	Arguments:
		ship : Name of ship data to be returned

	Returns:
		object: dict containing ship information

	Raises:
		InvalidShipName
		NoBuildFound
	"""
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii:  # does name includes non-ascii character (outside printable ?
			ship = ship_name_to_ascii[ship.lower()]  # convert to the appropriate name

		if database_client is not None:
			# connection to db
			query_result = database_client.mackbot_db.ship_list.find_one({
				"name": {"$regex": f"^{ship.lower()}$", "$options": "i"}
			})
			if query_result is None:
				# query returns no result
				raise NoShipFound
			else:
				return query_result
		else:
			# cannot connect to db
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
		NoBuildFound
	"""
	if fetch_from is not SHIP_BUILD_FETCH_FROM.LOCAL:
		if database_client is None:
			fetch_from = SHIP_BUILD_FETCH_FROM.LOCAL

	try:
		if fetch_from is SHIP_BUILD_FETCH_FROM.LOCAL:
			result = [ship_build[b] for b in ship_build if ship_build[b]['ship'] == ship]
			if not result:
				raise NoBuildFound
			return result
		if fetch_from is SHIP_BUILD_FETCH_FROM.MONGO_DB:
			return list(database_client.mackbot_db.ship_build.find({"ship": ship}))
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

	Raises:
		ValueError
		IndexError
	"""
	try:
		ship = get_ship_data(ship)
	except NoShipFound:
		return None

	if database_client is not None:
		query_result = database_client.mackbot_db.upgrade_list.find_one({
			"is_special": "Unique",
			"ship_restriction": {"$in": [ship['name']]}
		}, {"_id": 0})
		if query_result:
			return query_result
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

	Raises:
		ValueError
		IndexError
	"""
	skill = skill.lower()
	try:
		# filter skills by tree
		ship_class_lookup = [i.lower() for i in hull_classification_converter.keys()] + [i.lower() for i in hull_classification_converter.values()]
		hull_class_lower = dict([(i.lower(), hull_classification_converter[i].lower()) for i in hull_classification_converter])

		if tree not in ship_class_lookup:
			# requested type is not in
			raise SkillTreeInvalid(f"Expected {', '.join(i for i in ship_class_lookup)}. Got {tree}.")
		else:
			# convert from hull classification to word

			if tree not in hull_class_lower:
				for h in hull_class_lower:
					if hull_class_lower[h].lower() == tree:
						tree = h.lower()
						break

			if database_client is not None:
				# connection to db
				query_result = database_client.mackbot_db.skill_list.find_one({
					"name": {"$regex": f"^{skill.lower()}$", "$options": "i"},
					"tree": {"$regex": f"^{tree.lower()}$", "$options": "i"}
				})
				if query_result is None:
					# query returns no result
					raise NoSkillFound
				else:
					return query_result
			else:
				# looking for skill based on full name
				filtered_skill_list = dict([(s, skill_list[s]) for s in skill_list if skill_list[s]['tree'].lower() == tree])
				for f_s in filtered_skill_list:
					for lookup_type in ['name', 'abbr']:
						if filtered_skill_list[f_s]['name'].lower() == skill:
							s = filtered_skill_list[f_s].copy()
							if s['tree'] == 'AirCarrier':
								s['tree'] = "Aircraft Carrier"
							return s
				raise NoSkillFound

	except Exception as e:
		if skill == "*":
			return {
				'category': 'Any',
				'description': 'Any skill',
				'effect': '',
				'skill_id': -1,
				'name': 'Any',
				'tree': 'Any',
				'x': -1,
				'y': -1,
			}
		# oops, probably not found
		logger.info(f"Exception in get_skill_data {type(e)}: {e}")
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

	Raises:
		ValueError
		IndexError
		NoUpgradeFound
	"""
	upgrade = upgrade.lower()
	try:
		upgrade_found = False

		if database_client is not None:
			# connection to db
			query_result = database_client.mackbot_db.upgrade_list.find_one({
				"name": {"$regex": f"^{upgrade.lower()}$", "$options": "i"}
			})
			if query_result is None:
				# query returns no result
				# maybe an abbreviation?
				abbr_query_result = database_client.mackbot_db.upgrade_abbr_list.find_one({
					"abbr": {"$regex": f"^{upgrade.lower()}$", "$options": "i"}
				})
				if abbr_query_result is not None:
					# it is an abbreviation, grab it
					query_result = database_client.mackbot_db.upgrade_list.find_one({
						"name": {"$regex": f"^{abbr_query_result['upgrade']}$", "$options": "i"}
					})
				else:
					# not an abbreviation, user error
					raise NoUpgradeFound
			return query_result
		else:
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
		logger.info(f"Exception in get_upgrade_data {type(e)}: {e}")
		raise e

def get_module_data(module_id: int) -> dict:
	"""
	Return a ship's module data based on its id

	Args:
		module_id (int): Module's ID

	Returns:
		dict: Data containing information about the requested module

	Raises:
		IndexError
	"""
	if database_client is not None:
		query_result = database_client.mackbot_db.module_list.find_one({
			"module_id": module_id
		})
		if query_result is None:
			raise IndexError
		else:
			del query_result['_id']
			return query_result.copy()
	else:
		return module_list[str(module_id)]

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

	Raises:
		ValueError
		IndexError
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
		logger.error(f"Exception {type(e)} {e}")
		raise e

def get_ship_data_by_id(ship_id: int) -> dict:
	"""
	get_ship_build's version of getting ship data, but with ID instead. Useful in finding ship that is no
	longer exists

	Args:
		ship_id (int): Ship ID

	Returns:
		dict: Containing ship data

	Raise:
		NoShipFound
	"""
	ship_data = {
		"name": "",
		"tier": -1,
		"nation": "",
		"type": "",
		"is_prem": False,
		"emoji": '',
	}
	if database_client is not None:
		# database fetch
		query_result = database_client.mackbot_db.ship_list.find_one({
			"ship_id": ship_id
		})
		if query_result is not None:
			ship_data['name'] = query_result['name']
			ship_data['tier'] = query_result['tier']
			ship_data['nation'] = query_result['nation']
			ship_data['type'] = query_result['type']
			ship_data['is_prem'] = query_result['is_premium']
		else:
			# some ships are not available in wg api
			query_result = [i for i in game_data if game_data[i]['id'] == ship_id]
			if len(query_result) > 0:
				data = game_data[query_result[0]]
				ship_name = data['name']
				ship_name = ship_name.replace(str(data['index']), '')[1:]
				ship_name = ''.join(i for i in ship_name if i in ascii_letters or i == '_').split()
				ship_name = ''.join(ship_name)
				ship_name = ship_name.replace("_", " ")

				ship_data['name'] = ship_name + " (old)"
				ship_data['tier'] = data['level']
				ship_data['nation'] = data['navalFlag']
				ship_data['type'] = data['typeinfo']['species']
			else:
				raise NoShipFound
	else:
		# local fetch
		try:
			ship_data['name'] = ship_list[str(ship_id)]['name']
			ship_data['tier'] = ship_list[str(ship_id)]['tier']
			ship_data['nation'] = ship_list[str(ship_id)]['nation']
			ship_data['type'] = ship_list[str(ship_id)]['type']
			ship_data['is_prem'] = ship_list[str(ship_id)]['is_premium']
		except KeyError:
			# some ships are not available in wg api
			query_result = [i for i in game_data if game_data[i]['id'] == ship_id]
			if len(query_result) > 0:
				data = game_data[query_result[0]]
				ship_name = data['name']
				ship_name = ship_name.replace(str(data['index']), '')[1:]
				ship_name = ''.join(i for i in ship_name if i in ascii_letters or i == '_').split()
				ship_name = ''.join(ship_name)
				ship_name = ship_name.replace("_", " ")

				ship_data['name'] = ship_name + " (old)"
				ship_data['tier'] = data['level']
				ship_data['nation'] = data['navalFlag']
				ship_data['type'] = data['typeinfo']['species']
			else:
				raise NoShipFound
	ship_data['emoji'] = icons_emoji[hull_classification_converter[ship_data['type']].lower() + ('_prem' if ship_data['is_prem'] else '')]
	return ship_data
