
from pymongo import MongoClient

from mackbot.utilities.bot_data import mongodb_host
from mackbot.utilities.logger import logger

from mackbot.constants import ICONS_EMOJI, hull_classification_converter
from mackbot.data_prep import load_game_params, game_data

ship_list = {}
skill_list = {}
module_list = {}
upgrade_list = {}
camo_list = {}
cmdr_list = {}
flag_list = {}
upgrade_abbr_list = {}
consumable_list = {}

# simple list only containing name
ship_list_simple = {}
upgrade_list_simple = {}
skill_list_simple = {}

# define database stuff
database_client = None
try:
	logger.info("MongoDB connection successful.")
	database_client = MongoClient(mongodb_host)

	load_game_params()
	game_data = game_data.copy()
	# this exists because of the player function to quickly fetch some ship data locally
	db_ship_list = database_client.mackbot_db.ship_list.find({}, {"_id": 0})
	for ship in db_ship_list:
		ship_list_simple[str(ship['ship_id'])] = {
			"name": ship['name'],
			"tier": ship['tier'],
			"nation": ship['nation'],
			"type": ship['type'],
			"emoji": ICONS_EMOJI[hull_classification_converter[ship['type']].lower() + ('_prem' if ship['is_premium'] else '')]
		}

	db_upgrade_list = database_client.mackbot_db.upgrade_list.find({}, {"_id": 0})
	for upgrade in db_upgrade_list:
		upgrade_list_simple[str(upgrade['consumable_id'])] = {
			'name': upgrade['name'],
		}

	db_skill_list = database_client.mackbot_db.skill_list.find({}, {"_id": 0})
	for skill in db_skill_list:
		skill_list_simple[str(skill['skill_id'])] = {
			'name': skill['name'],
		}
	skill_list_simple = dict((i, 0) for i in set(list([j['name'] for j in skill_list_simple.values()])))

except ConnectionError:
	from mackbot.data_prep import (
		load,
		ship_list,
		skill_list,
		module_list,
		upgrade_list,
		camo_list,
		cmdr_list,
		flag_list,
		upgrade_abbr_list,
		consumable_list,
		game_data
	)
	logger.warning("MongoDB cannot be connected. Loading data from local")
	load()
	ship_list = ship_list.copy()
	skill_list = skill_list.copy()
	module_list = module_list.copy()
	upgrade_list = upgrade_list.copy()
	camo_list = camo_list.copy()
	cmdr_list = cmdr_list.copy()
	flag_list = flag_list.copy()
	upgrade_abbr_list = upgrade_abbr_list.copy()
	consumable_list = consumable_list.copy()
	game_data = game_data.copy()

	# this exists because of the player function to quickly fetch some ship data
	for i in ship_list:
		ship = ship_list[i]
		ship_list_simple[i] = {
			"name": ship['name'],
			"tier": ship['tier'],
			"nation": ship['nation'],
			"type": ship['type'],
			"emoji": ICONS_EMOJI[hull_classification_converter[ship['type']].lower() + ('_prem' if ship['is_premium'] else '')]
		}
