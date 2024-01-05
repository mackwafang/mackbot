from hashlib import sha256

import pymongo, os

from pymongo import MongoClient
from typing import List

from mackbot.constants import UPGRADE_SLOTS_AT_TIER
from mackbot.exceptions import BuildError, NoUpgradeFound
from mackbot.utilities.game_data.game_data_finder import ship_name_to_ascii, get_ship_data, get_skill_data, get_upgrade_data
from mackbot.utilities.game_data.warships_data import *

database_client = MongoClient(mongodb_host)

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
	data = {
		"name": build_name,
		"ship": build_ship_name,
		"build_id": "",
		"upgrades": [],
		"skills": [],
		"cmdr": build_cmdr,
		"errors": [],
		"private": set_private,             # used to differentiate clan builds and public builds
		"str_errors": [],
	}
	# converting upgrades
	for s, u in enumerate(build_upgrades):
		try:
			# blank slot
			if not len(u):
				continue

			# any upgrade
			if u == '*':
				data['upgrades'].append(-1)
				continue

			# specified upgrade
			upgrade_data = get_upgrade_data(u)
			if upgrade_data['slot'] != s + 1:
				data['errors'].append(BuildError.UPGRADE_IN_WRONG_SLOT)
			data['upgrades'].append(upgrade_data['consumable_id'])

		except NoUpgradeFound:
			data['str_errors'].append(f"- Upgrade [{u}] is not an upgrade.")
			data['errors'].append(BuildError.UPGRADE_NOT_FOUND)

	if len(data['upgrades']) > UPGRADE_SLOTS_AT_TIER[ship_data['tier'] - 1]:
		data['errors'].append(BuildError.UPGRADE_EXCEED_MAX_ALLOWED_SLOTS)

	# converting skills
	total_skill_pts = 0
	skill_list_filtered = dict((s, skill_list_simple[s]) for s in skill_list_simple if skill_list_simple[s]['tree'] == ship_data['type'])
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
			data['str_errors'].append(f"- Skill [{s}] is not an skill")
			data['errors'].append(BuildError.SKILLS_INCORRECT)

	skill_order_valid, skill_order_incorrect_at = _check_skill_order_valid(data['skills'])
	if not skill_order_valid:
		data['errors'].append(BuildError.SKILLS_ORDER_INVALID)
	if total_skill_pts > 21:
		data['errors'].append(BuildError.SKILL_POINTS_EXCEED)
	elif total_skill_pts < 21:
		data['errors'].append(BuildError.SKILLS_POTENTIALLY_MISSING)

	# compiling errors
	data['errors'] = list(set(data['errors']))
	if data['errors']:
		build_error_strings = ', '.join(' '.join(i.name.split("_")).title() for i in data['errors'])
		logger.warning(f"Build for ship [{build_ship_name} | {build_name}] has the following errors: {build_error_strings}")

		# for e in data['errors']:
		# 	data['str_errors'].append(' '.join(e.name.split("_")).title())
		if not skill_order_valid:
			data['str_errors'].append(f"- Skills not proper order in skill #{skill_order_incorrect_at}. ")

		if BuildError.SKILLS_POTENTIALLY_MISSING in data['errors']:
			data['str_errors'].append(f"- Total skill points in this build: {total_skill_pts}")
			m = "- Skills potentially missing. Points in this builds are: "
			for skill in data["skills"]:
				skill_data = dict(database_client.mackbot_db.skill_list.find_one({"skill_id": skill}))
				# data['str_errors'].append(f"  - {skill_data['name']:<32} ({skill_data['y'] + 1})")
				m += f"{skill_data['y'] + 1}, "
			data['str_errors'].append(m[:-2])

		if BuildError.UPGRADE_EXCEED_MAX_ALLOWED_SLOTS in data['errors']:
			data['str_errors'].append(f"- Found {len(build_upgrades)} upgrades. Expects {UPGRADE_SLOTS_AT_TIER[ship_data['tier']-1]} upgrades.")

		if BuildError.UPGRADE_IN_WRONG_SLOT in data['errors']:
			for s, upgrade_id in enumerate(data['upgrades']):
				if upgrade_id == -1:
					continue

				upgrade_data = upgrade_list[str(upgrade_id)]
				if upgrade_data['slot'] != s + 1:
					data['str_errors'].append(f"- Upgrade {upgrade_data['name']} ({upgrade_data['consumable_id']}) expects slot {upgrade_data['slot']}, currently in slot {s + 1}")

	build_id = sha256(str(data).encode()).hexdigest()
	data['build_id'] = build_id

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
			"build_limits": 30,
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