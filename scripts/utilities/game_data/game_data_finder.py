import pymongo, os
from scripts.mackbot_exceptions import *
from scripts.utilities.game_data.warships_data import *

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