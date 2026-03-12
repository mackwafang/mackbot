from hashlib import sha256

import pymongo, os

from pymongo import MongoClient
from typing import List

from mackbot.constants import UPGRADE_SLOTS_AT_TIER
from mackbot.exceptions import BuildError, NoUpgradeFound
from mackbot.data_prep import parse_ship_build
from mackbot.utilities.game_data.game_data_finder import ship_name_to_ascii, get_ship_data, get_skill_data, get_upgrade_data
from mackbot.utilities.game_data.warships_data import *

database_client = MongoClient(mongodb_host)

CLAN_BUILDS_LIMIT = 120

def _check_skill_order_valid(skills: list) -> bool:
	"""
	Check to see if order of skills are valid (i.e., difference between skills are no greater than 1 tier)
	The first skill must be a tier 1 skill
	Args:
		skills (list): list of skill id

	Returns:
		(bool, index)
	"""
	if not skills:
		# no skills is a valid configuration
		return True, 0
	is_first_skill_valid = database_client.mackbot_db.skill_list.find_one({"skill_id": skills[0]}) is not None
	if not is_first_skill_valid:
		return False, 1

	max_tier_so_far = -1
	for i, s in enumerate(skills):
		skill_data = database_client.mackbot_db.skill_list.find_one({"skill_id": s})
		if skill_data['y'] > max_tier_so_far + 1:
			return False, i+1
		max_tier_so_far = max(max_tier_so_far, skill_data['y'])
	return True, 0

def _parse_ship_build(build_ship_name, build_name, build_upgrades, build_skills, build_cmdr, ship_data, set_private=False):
	"""
	check a ship build to see if it is valid
	Args:
		build_ship_name (string):           name of ship
		build_name (string):                name of build
		build_upgrades (List[string]):      list of upgrades (e.g. csm1, concealment system modification 1)
		build_skills (List[string]):        list of skills (e.g. surviviability expert
		build_cmdr (string):                commander name or * for any
		ship_data (dict):                   ship data
		set_private (bool):                 Optional - set to private
	Returns:
		dict - build data in a container
	"""
	data = parse_ship_build(
		build_ship_name,
		build_name,
		build_upgrades,
		build_skills,
		build_cmdr,
		ship_data,
		set_private
	)

	data_copy = data.copy()
	del data_copy['str_errors']
	data['hash'] = sha256(str(data_copy).encode()).hexdigest()

	return data

def _init_guild_data(guild_id: int):
	"""
	Create a clan's entry in the database. Return MongoDB's id if a new entry is created, None otherwise
	Args:
		guild_id (int): Discord server ID

	Returns:
		pymongo.ObjectId or None
	"""
	if not database_client.mackbot_db.clan_build.find_one({"guild_id": guild_id}):
		new_entry = database_client.mackbot_db.clan_build.insert_one({
			"guild_id": guild_id,
			"builds": [],
			"build_limits": CLAN_BUILDS_LIMIT,
			"build_count": 0,
		})

		return new_entry.inserted_id
	return None

def clan_build_upload(build_list: List[List], guild_id: int):
	"""
	Parse and upload clan builds
	Args:
		build_list (list of list):  Builds list
		guild_id (int):             Discord server id

	Returns:
		(List, List) - List of build IDs, list of errors
	"""
	guild_data = database_client.mackbot_db.clan_build.find_one({"guild_id": guild_id})
	guild_data_id = ""
	db_builds = []
	if guild_data is None:
		# guild not in database, create entry
		guild_data_id = _init_guild_data(guild_id)
		guild_data = database_client.mackbot_db.clan_build.find_one({"_id": guild_data_id})
	else:
		guild_data_id = guild_data['_id']

	# parsing and (partial) uploading
	errors = []
	for build_index, build in enumerate(build_list):
		m = f"Build #{build_index + 1}:\n"
		has_error = False

		build_ship_name, build_name, build_upgrades, build_skills, build_cmdr = build

		# add to clan list of builds
		if len(db_builds) < guild_data['build_limits']:
			# check user inputed ship name
			ship_data = get_ship_data(build_ship_name)
			build_data = _parse_ship_build(ship_data['name'], build_name, build_upgrades, build_skills, build_cmdr, ship_data, set_private=True)
			if not database_client.mackbot_db.ship_build.find_one({"build_id": build_data['build_id']}):
				# build does not exist in database, we add
				new_build = database_client.mackbot_db.ship_build.insert_one(build_data)
			else:
				m += f"This build already exists\n"
				has_error = True

			if build_data['errors']:
				m += f"{chr(10).join(build_data['str_errors'])}"
				has_error = True
			else:
				del build_data['str_errors']
				db_builds.append(build_data['build_id'])

		else:
			m += f"Build limit reached ({guild_data['build_limits']}). Skipped."
			has_error = True

		if has_error:
			errors.append(m)

	# update entry
	database_client.mackbot_db.clan_build.update_one({
		"_id": guild_data_id,
	}, {
		"$set": {
			"builds": db_builds,
			"build_count": len(db_builds),
		}
	})

	return db_builds, errors