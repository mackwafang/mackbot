import difflib
from scripts.utilities.game_data.warships_data import database_client, ship_list, upgrade_list, skill_list

def find_close_match_item(name: str, database: str) -> list:
	"""
	Returns a list of closest matches for the indicated item in the database
	Args:
		name (str): A ship name
		database (str): which database to use

	Returns:
		List of closest ship names
	"""

	db_selection = ['ship_list', 'upgrade_list', 'skill_list']
	try:
		assert database in db_selection
	except AssertionError:
		raise ValueError(f"{database} is not in {db_selection}")
	names_list = []
	if database_client is not None:
		query_result = database_client.mackbot_db[database].find({}, {
			"name": 1
		})
		names_list = [i['name'].lower() for i in query_result]
	else:
		if database == "ship_list":
			names_list = [ship_list[i]['name'].lower() for i in ship_list]
		if database == "upgrade_list":
			names_list = [upgrade_list[i]['name'].lower() for i in upgrade_list]
		if database == "skill_list":
			names_list = [skill_list[i]['name'].lower() for i in skill_list]
	return difflib.get_close_matches(name, names_list)