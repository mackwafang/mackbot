
from pymongo import MongoClient

from mackbot.utilities.bot_data import mongodb_host
from mackbot.utilities.logger import logger

from mackbot.constants import icons_emoji, hull_classification_converter
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
ship_list_simple = {}

# define database stuff
database_client = None
try:
	logger.info("MongoDB connection successful.")
	database_client = MongoClient(mongodb_host)

	load_game_params()
	game_data = game_data.copy()
	# this exists because of the player function to quickly fetch some ship data
	db_ship_list = database_client.mackbot_db.ship_list.find({}, {"_id": 0})
	for ship in db_ship_list:
		ship_list_simple[str(ship['ship_id'])] = {
			"name": ship['name'],
			"tier": ship['tier'],
			"nation": ship['nation'],
			"type": ship['type'],
			"emoji": icons_emoji[hull_classification_converter[ship['type']].lower() + ('_prem' if ship['is_premium'] else '')]
		}

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
			"emoji": icons_emoji[hull_classification_converter[ship['type']].lower() + ('_prem' if ship['is_premium'] else '')]
		}
