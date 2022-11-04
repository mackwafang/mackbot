import wargaming, pickle, discord, logging, difflib, traceback, asyncio
import pandas as pd

from PIL import Image, ImageDraw, ImageFont
from datetime import date
from discord import Interaction, SelectOption, app_commands
from discord.ext import commands
from discord.ui import View, Select
from itertools import zip_longest
from math import ceil
from random import randint
from scripts.mackbot_constants import *
from scripts.mackbot_exceptions import *
from scripts.utilities import logger
from scripts.utilities.game_data.warships_data import *
from scripts.utilities.utils import *
from scripts.utilities.regex import *
from scripts.utilities.compile_bot_help import compile_help_strings, help_dictionary
from scripts.utilities.get_aa_rating_descriptor import get_aa_rating_descriptor
from cogs import *
from string import ascii_letters
from typing import Union, Optional

class SHIP_BUILD_FETCH_FROM(IntEnum):
	LOCAL = auto()
	MONGO_DB = auto()


# drop down menu from discord 2.0
class UserSelection(View):
	def __init__(self, author: discord.Message.author, timeout: int, placeholder: str, options: list[discord.ui.select]):
		self.select_menu = self.DropDownSelect(placeholder, options)
		self.response = -1
		self.author = author
		super().__init__(timeout=timeout)
		super().add_item(self.select_menu)

	async def disable_component(self) -> None:
		for child in self.children:
			child.disabled = True
		await self.message.edit(view=self)

	async def on_timeout(self) -> None:
		self.select_menu.placeholder = "Response Expired"
		await self.disable_component()

	async def interaction_check(self, interaction: Interaction) -> bool:
		if interaction.user.id == self.author.id:
			await self.disable_component()
			return True
		return False

	class DropDownSelect(Select):
		def __init__(self, placeholder: str, options: list[discord.ui.select]):
			super().__init__(placeholder=placeholder, options=options)

		async def callback(self, interaction: Interaction) -> None:
			self.view.response = self.values[0]
			await interaction.response.defer()
			await self.view.disable_component()
			self.view.stop()

class Mackbot(commands.Bot):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	async def setup_hook(self) -> None:
		await self.tree.sync()

# icons for prettifying outputs
icons_emoji = {
	"torp": "<:torp:917573129579151392>",
	"dd": "<:destroyer:917573129658859573>",
	"gun": "<:gun:917573129730146325>",
	"bb_prem": "<:battleship_premium:917573129801449563>",
	"plane_torp": "<:plane_torpedo:917573129847590993>",
	"ss_prem": "<:submarine_premium:917573129851764776>",
	"ss": "<:submarine:917573129876955147>",
	"bb": "<:battleship:917573129876959232>",
	"cv": "<:carrier:917573129931477053>",
	"c": "<:cruiser:917573129885323374>",
	"dd_prem": "<:destroyer_premium:917573129944059965>",
	"plane_rocket": "<:plane_projectile:917573129956638750>",
	"c_prem": "<:cruiser_premium:917573129965027398>",
	"cv_prem": "<:carrier_premium:917573130019557416>",
	"plane_bomb": "<:plane_bomb:917573130023759893>",
	"penetration": "<:penetration:917583397122084864>",
	"ap": "<:ap:917585790765252608>",
	"he": "<:he:917585790773653536>",
	"sap": "<:sap:917585790811402270>",
	"reload": "<:reload:917585790815584326>",
	"range": "<:range:917589573415088178>",
	"aa": "<:aa:917590394806599780>",
	"plane": "<:plane:917601379235815524>",
	"concealment": "<:concealment:917605435278782474>",
	"clan_in": "<:clan_in:952757125225021450>",
	"clan_out": "<:clan_out:952757125237575690>",
	"green_plus": "<:green_plus:979497350869450812>",
	"red_dash": "<:red_dash:979497350911385620>",
}

# dictionary to convert user inputted ship name to non-ascii ship name
with open(os.path.join(os.getcwd(), "data", "ship_name_dict.json"), 'r', encoding='utf-8') as f:
	ship_name_to_ascii = json.load(f)

# define database stuff

# define bot stuff
cmd_sep = ' '
command_prefix += cmd_sep
bot_intents = discord.Intents().default()
bot_intents.members = True
bot_intents.typing = True
bot_intents.message_content = True

mackbot = Mackbot(command_prefix=command_prefix, intents=bot_intents, help_command=None)

# get weegee's wows encyclopedia
WG = {
	'na': wargaming.WoWS(wg_token, region='na', language='en'),
	'asia': wargaming.WoWS(wg_token, region='asia', language='en'),
	'eu': wargaming.WoWS(wg_token, region='eu', language='en'),
	'ru': wargaming.WoWS(wg_token, region='ru', language='en'),
}
wows_encyclopedia = WG['na'].encyclopedia

clan_roles = WG['na'].clans.glossary()['clans_roles']
clan_history = {}
clan_history_file_path = os.path.join(os.getcwd(), "data", "clan_history")
if os.path.exists(clan_history_file_path):
	with open(clan_history_file_path, 'rb') as f:
		clan_history = pickle.load(f)

logger.info("Fetching Maps")
map_list = wows_encyclopedia.battlearenas()


WOWS_REALMS = ('na', 'ru', 'eu', 'asia')


good_bot_messages = (
	'Thank you!',
	'Mackbot tattara kekkō ganbatta poii? Homete hometei!',
	':3',
	':heart:',
)

with open(os.path.join(os.getcwd(), "data", "hottakes.txt")) as f:
	hottake_strings = f.read().split('\n')

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


def create_ship_build_images(
		build_name: str,
		build_ship_name: str,
		build_skills: list,
		build_upgrades: list,
		build_cmdr: str
	) -> Image:
	# create dictionary for upgrade gamedata index to image name
	image_file_dict = {}
	image_folder_dir = os.path.join("data", "modernization_icons")
	for file in os.listdir(image_folder_dir):
		image_file = os.path.join(image_folder_dir, file)
		upgrade_index = file.split("_")[2] # get index
		image_file_dict[upgrade_index] = image_file

	font = ImageFont.truetype("./data/arialbd.ttf", encoding='unic', size=20)

	# create build image
	image_size = (400, 400)

	ship = get_ship_data(build_ship_name)

	# get ship type image
	ship_type_image_filename = ""
	if ship['type'] == 'AirCarrier':
		ship_type_image_filename = 'carrier'
	else:
		ship_type_image_filename = ship['type'].lower()
	if ship['is_premium']:
		ship_type_image_filename += "_premium"
	ship_type_image_filename += '.png'

	ship_type_image_dir = os.path.join("data", "icons", ship_type_image_filename)
	ship_tier_string = list(roman_numeral.keys())[ship['tier'] - 1]

	image = Image.new("RGBA", image_size, (0, 0, 0, 255)) # initialize new image
	draw = ImageDraw.Draw(image) # get drawing context

	# draw ship name and ship type
	with Image.open(ship_type_image_dir).convert("RGBA") as ship_type_image:
		ship_type_image = ship_type_image.resize((ship_type_image.width * 2, ship_type_image.height * 2), Image.NEAREST)
		image.paste(ship_type_image, (0, 0), ship_type_image)
	draw.text((56, 27), f"{ship_tier_string} {ship['name']}", fill=(255, 255, 255, 255), font=font, anchor='lm') # add ship name
	draw.text((image.width - 8, 27), f"{build_name.title()} build", fill=(255, 255, 255, 255), font=font, anchor='rm') # add build name

	# get skills from this ship's tree
	if database_client is not None:
		query_result = database_client.mackbot_db.skill_list.find({"tree": ship['type']}, {"_id": 0})
		skill_list_filtered_by_ship_type = {i['skill_id']: i for i in query_result}
	else:
		skill_list_filtered_by_ship_type = {k: v for k, v in skill_list.items() if v['tree'] == ship['type']}
	# draw skills
	for skill_id in skill_list_filtered_by_ship_type:
		skill = skill_list_filtered_by_ship_type[skill_id]
		skill_image_filename = os.path.join("data", "cmdr_skills_images", skill['image'] + ".png")
		if os.path.isfile(skill_image_filename):
			with Image.open(skill_image_filename).convert("RGBA") as skill_image:

				coord = (4 + (skill['x'] * 64), 50 + (skill['y'] * 64))
				green = Image.new("RGBA", (60, 60), (0, 255, 0, 255))

				if int(skill_id) in build_skills:
					# indicate user should take this skill
					skill_image = Image.composite(green, skill_image, skill_image)
					# add number to indicate order should user take this skill
					skill_acquired_order = build_skills.index(int(skill_id)) + 1
					image.paste(skill_image, coord, skill_image)
					draw.text((coord[0], coord[1] + 40), str(skill_acquired_order), fill=(255, 255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0, 255))
				else:
					# fade out unneeded skills
					skill_image = Image.blend(skill_image, Image.new("RGBA", skill_image.size, (0, 0, 0, 0)), 0.5)
					image.paste(skill_image, coord, skill_image)

	# draw upgrades
	for slot, u in enumerate(build_upgrades):
		if u != -1:
			# specific upgrade
			upgrade_index = [game_data[i]['index'] for i in game_data if game_data[i]['id'] == u][0]
			upgrade_image_dir = image_file_dict[upgrade_index]
		else:
			# any upgrade
			upgrade_image_dir = image_file_dict['any.png']

		with Image.open(upgrade_image_dir).convert("RGBA") as upgrade_image:
			coord = (4 + (slot * 64), image.height - 60)
			image.paste(upgrade_image, coord, upgrade_image)

	return image

async def get_user_response_with_drop_down(view: discord.ui.View) -> int:
	"""
		Wait for a user message or if user selected an item from the drop-down menu
		Args:
			view : A Discord UI View object

		Returns:
			int: The value of the user selected item. Returns -1 if: A message is not attached to the view object or if view timed out.
	"""
	await view.wait()
	if view.message is None:
		return -1
	else:
		return int(view.response)

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

def get_map_data(map: str) -> tuple:
	"""
	returns informations of a requested warship upgrade

	Arguments:
	-------
		- map : (string)
			map's name

	Returns:
	-------
	tuple:
		description	- (str) map's description
		image		- (str) image url on WG's server
		id			- (str) map id
		name		- (str) map's name

	Raises:
		ValueError
		IndexError
	"""

	map = map.lower()
	try:
		for m in map_list:
			if map == map_list[m]['name'].lower():
				description, image, id, name = map_list[m].values()
				return description, image, id, name
	except Exception as e:
		logger.info("Exception {type(e): ", e)
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

def escape_discord_format(s: str) -> str:
	return ''.join('\\'+i if i in ['*', '_'] else i for i in s)


def post_process() -> None:
	compile_help_strings()

def to_plural(str: str, count: int) -> str:
	if str[-1].lower() == 'y':
		return f"{count} {str[:-1] + 'ies'}"
	elif str[-1].lower() == 'o':
		return f"{count} {str[:-1] + 'es'}"
	else:
		return f"{count} {str + 's'}"


# *** END OF NON-COMMAND METHODS ***
# *** START OF BOT COMMANDS METHODS ***


async def bot_help(context):
	# TODO: REMOVE WHEN DONE
	pass

@mackbot.hybrid_command(name="about", description="About mackbot")
async def about_bot(context: commands.Context):
	query = list(database_client.mackbot_db.mackbot_info.find({}).sort("VERSION_TIME", -1))
	embed = discord.Embed(title="About mackbot")
	if query:
		m = ""
		m += f"mackbot v{query[0]['MACKBOT_VERSION']}\n"
		m += f"mackbot web v{query[0]['MACKBOT_WEB_VERSION']}\n"
		embed.add_field(name="Version", value=m, inline=False)

	m = ""
	m += f"Please visit the **mackbot's testing ground** server {discord_invite_url}"
	embed.add_field(name="Support", value=m, inline=False)

	m = ""
	m += "All copyrighted materials owned by Wargaming.net. All rights reserved.\n"
	m += "All other contents are available under the MIT license.\n"
	embed.add_field(name="Legal", value=m, inline=False)
	await context.send(embed=embed)

@mackbot.hybrid_command(name="faq", description="What is a mackbot?")
async def faq(context: commands.Context):
	async with context.typing():
		m = ""

		m += "**mackbot**, a WoWS encyclopedia and basic warship build bot.\n"
		m += f"Currently deployed in {to_plural('server', len(mackbot.guilds))}.\n\n"
		m += "mackbot is a Discord bot for sharing warship configuration and showing ship details for the game World of Warships.\n"
		m += "Originally built for as a clan specific tool to share builds and set base builds for ships, now it is a bot that contains basic warships build information and a warships encyclopedia.\n"
		m += "\nQnA\n"
		m += "**[Who created mackbot?]** mackbot is created by mackwafang#2071, he plays way too much CV.\n"
		m += "**[Why is it *mackbot* called *mackbot*?]** Originally, mackbot was called buildbot. Until a clan member suggested that I (mackwafang#2071) should name it mackbot because I was its sole creator.\n"
		m += "**[What can mackbot do?]** Mackbot can:\n"
		m += "\t\t- Gives basic warship builds (via the **build** command)\n"
		m += "\t\t- Gives warship information (via the **ship** command)\n"
		m += "\t\t- Gives hot takes (via the **hottake** command)\n"
		m += "\t\t- And more!\n"
	await context.send(m)

@mackbot.hybrid_command(name="goodbot", description="Compliment mackbot")
async def goodbot(context: commands.Context):
	# good bot
	r = randint(0, len(good_bot_messages) - 1)
	logger.info(f"send reply message for goodbot")
	await context.send(good_bot_messages[r])  # block until message is sent

@mackbot.hybrid_command(name="feedback", description="Provide feedback to the developer")
async def feedback(context: commands.Context):
	logger.info("send feedback link")
	await context.send(f"Need to rage at mack because he ~~fucks up~~ did goofed on a feature? Submit a feedback form here!\nhttps://forms.gle/Lqm9bU5wbtNkpKSn7")

@mackbot.hybrid_command(name='build', description='Get a basic warship build')
@app_commands.rename(args="value")
@app_commands.describe(
	args="Ship name. Adds -i before ship name to get image variation",
)
async def build(context: commands.Context, args: str):

	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = ' '.join(context.message.content.split()[2:])

	if len(args) == 0:
		await bot_help(context, "build")
	else:
		args = args.split()
		send_image_build = args[0] in ["--image", "-i"]
		if send_image_build:
			args = args[1:]
		user_ship_name = ''.join([i + ' ' for i in args])[:-1]
		name, images = "", None
		try:
			output = get_ship_data(user_ship_name)
			name = output['name']
			nation = output['nation']
			images = output['images']
			ship_type = output['type']
			tier = output['tier']
			is_prem = output['is_premium']

			# find ship build
			builds = get_ship_builds_by_name(name, fetch_from=SHIP_BUILD_FETCH_FROM.MONGO_DB)
			user_selected_build_id = 0
			multi_build_user_response = None

			# get user selection for multiple ship builds
			if len(builds) > 1:
				embed = discord.Embed(title=f"Build for {name}", description='')
				embed.set_thumbnail(url=images['small'])

				embed.description = f"**Tier {list(roman_numeral.keys())[tier - 1]} {nation_dictionary[nation]} {ship_types[ship_type].title()}**"

				m = ""
				for i, bid in enumerate(builds):
					build_name = builds[i]['name']
					m += f"[{i + 1}] {build_name}\n"
				embed.add_field(name="mackbot found multiple builds for this ship", value=m, inline=False)
				embed.set_footer(text="Please select a build.\nResponse expires in 15 seconds.")
				options = [SelectOption(label=f"[{i+1}] {builds[i]['name']}", value=i) for i, b in enumerate(builds)]
				view = UserSelection(
					author=context.message.author,
					timeout=15,
					options=options,
					placeholder="Select a build"
				)
				view.message = await context.send(embed=embed, view=view)
				user_selected_build_id = await get_user_response_with_drop_down(view)
				if 0 <= user_selected_build_id < len(builds):
					pass
				else:
					await context.send(f"Input {user_selected_build_id} is incorrect")


			if not builds:
				raise NoBuildFound
			else:
				build = builds[user_selected_build_id]
				build_name = build['name']
				upgrades = build['upgrades']
				skills = build['skills']
				cmdr = build['cmdr']
				build_errors = build['errors']

			if not send_image_build:
				embed = discord.Embed(title=f"{build_name.title()} Build for {name}", description='')

				embed.set_thumbnail(url=images['small'])

				logger.info(f"returning build information for <{name}> in embeded format")

				tier_string = list(roman_numeral.keys())[tier - 1]

				embed.description += f'**Tier {tier_string} {"Premium" if is_prem else ""} {nation_dictionary[nation]} {ship_types[ship_type]}**\n'

				footer_message = ""
				error_value_found = False
				if len(upgrades) and len(skills) and len(cmdr):
					# suggested upgrades
					if len(upgrades) > 0:
						m = ""
						i = 1
						for upgrade in upgrades:
							upgrade_name = "[Missing]"
							if upgrade == -1:
								# any thing
								upgrade_name = "Any"
							else:
								try:  # ew, nested try/catch
									if database_client is not None:
										query_result = database_client.mackbot_db.upgrade_list.find_one({"consumable_id": upgrade})
										if query_result is None:
											raise IndexError
										else:
											upgrade_name = query_result['name']
									else:
										upgrade_name = get_upgrade_data(upgrade)['name']
								except Exception as e:
									logger.info(f"Exception {type(e)} {e} in ship, listing upgrade {i}")
									error_value_found = True
									upgrade_name = upgrade + ":warning:"
							m += f'(Slot {i}) **' + upgrade_name + '**\n'
							i += 1
						embed.add_field(name='Suggested Upgrades', value=m, inline=False)
					else:
						embed.add_field(name='Suggested Upgrades', value="Coming Soon:tm:", inline=False)
					# suggested skills
					if len(skills) > 0:
						m = ""
						i = 1
						for s in skills:
							skill_name = "[Missing]"
							try:  # ew, nested try/catch
								if database_client is not None:
									query_result = database_client.mackbot_db.skill_list.find_one({"skill_id":s})
									if query_result is None:
										raise IndexError
									else:
										skill = query_result.copy()
								else:
									skill = skill_list[str(s)]
								skill_name = skill['name']
								col = skill['x'] + 1
								tier = skill['y'] + 1
							except Exception as e:
								logger.info(f"Exception {type(e)} {e} in ship, listing skill {i}")
								error_value_found = True
								skill_name = skill + ":warning:"
							m += f'(Col. {col}, Row {tier}) **' + skill_name + '**\n'
							i += 1
						embed.add_field(name='Suggested Cmdr. Skills', value=m, inline=False)
					else:
						embed.add_field(name='Suggested Cmdr. Skills', value="Coming Soon:tm:", inline=False)
					# suggested commander
					if cmdr != "":
						m = ""
						if cmdr == "*":
							m = "Any"
						else:
							try:
								m = get_commander_data(cmdr)[0]
							except Exception as e:
								logger.info(f"Exception {type(e)} {e} in ship, listing commander")
								error_value_found = True
								m = f"{cmdr}:warning:"
						# footer_message += "Suggested skills are listed in ascending acquiring order.\n"
						embed.add_field(name='Suggested Cmdr.', value=m)
					else:
						embed.add_field(name='Suggested Cmdr.', value="Coming Soon:tm:", inline=False)

					# show user error if there is any that is missed by data prepper
					if build_errors:
						m = "This build has the following errors:\n"
						for error in build_errors:
							error_string = ' '.join(BuildError(error).name.split("_")).title()
							m += f"{error_string}\n"
						embed.add_field(name=":warning: Warning! :warning: ", value=m, inline=False)

					footer_message += "mackbot ship build should be used as a base for your builds. Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.\n"
					footer_message += f"For image variant of this message, use [mackbot build [-i/--image] {user_ship_name}]\n"
					if build_errors:
						footer_message += f"This build has error that may affect this ship's performance. Please contact a mackbot developer.\n"
				else:
					m = "mackbot does not know any build for this ship :("
					embed.add_field(name=f'No known build', value=m, inline=False)
				error_footer_message = ""
				if error_value_found:
					error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact mackwafang#2071.\n"
				embed.set_footer(text=error_footer_message + footer_message)

			if not send_image_build:
				if multi_build_user_response:
					# response to user's selection of drop-down menu
					await multi_build_user_response.respond(embed=embed, ephemeral=False)
				else:
					await context.send(embed=embed)
			else:
				# send image
				if database_client is None:
					# getting from local ship build file
					build_image = builds[user_selected_build_id]['image']
				else:
					# dynamically create
					build_image = create_ship_build_images(build_name, name, skills, upgrades, cmdr)
				build_image.save("temp.png")
				try:
					if multi_build_user_response:
						# response to user's selection of drop-down menu
						await multi_build_user_response.respond(file=discord.File('temp.png'), ephemeral=False)
					else:
						await context.send(file=discord.File('temp.png'))
					await context.send("__Note: mackbot ship build should be used as a base for your builds. Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.__")
				except discord.errors.Forbidden:
					await context.send("mackbot requires the **Send Attachment** feature for this feature.")
		except Exception as e:
			if type(e) == NoShipFound:
				# ship with specified name is not found, user might mistype ship name?
				closest_match = find_close_match_item(user_ship_name.lower(), "ship_list")
				embed = discord.Embed(title=f"Ship {user_ship_name} is not understood.\n", description="")
				if closest_match:
					closest_match_string = closest_match[0].title()
					closest_match_string = f'\nDid you mean **{closest_match_string}**?'
					embed.description = closest_match_string
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expires in 10 seconds")
					await context.send(embed=embed)
					await correct_user_misspell(context, 'build', f"{'-i' if send_image_build else ''} {closest_match[0]}")
				else:
					await context.send(embed=embed)
			elif type(e) == NoBuildFound:
				# no build for this ship is found
				embed = discord.Embed(title=f"Build for {name}", description='')
				embed.description = f"**Tier {list(roman_numeral.keys())[tier - 1]} {nation_dictionary[nation]} {ship_types[ship_type].title()}**"
				embed.set_thumbnail(url=images['small'])
				m = "mackbot does not know any build for this ship :("
				embed.add_field(name=f'No known build', value=m, inline=False)

				await context.send(embed=embed)
			else:
				logger.error(f"{type(e)}")
				traceback.print_exc()

@mackbot.hybrid_command(name='compare', description='Compare combat parameters of two warships')
@app_commands.describe(
	value="Two ships to compare. Add the word \"and\" between ship names",
)
async def compare(context: commands.Context, value: str):
	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = ' '.join(context.message.content.split()[2:])
	else:
		args = value

	if len(args) == 0:
		await bot_help(context, "compare")
	else:
		# args = ' '.join(args) # join arguments to split token
		# user_input_ships = args.replace("and", "&").split("&")
		compare_separator = ("and", "vs", "v")
		user_input_ships = re.sub(f"\\s{'|'.join(compare_separator)}\s", " & ", args, flags=re.I).split("&")
		if len(user_input_ships) != 2:
			await bot_help(context, "compare")
			return
		# parse whitespace
		user_input_ships  = [' '.join(i.split()) for i in user_input_ships]
		ships_to_compare = []

		def user_correction_check(message):
			return context.author == message.author and message.content.lower() in ['y', 'yes']

		# checking ships name and grab ship data
		for s in user_input_ships:
			try:
				ships_to_compare += [get_ship_data(s)]
			except NoShipFound:
				logger.info(f"ship check [{s}] FAILED")
				logger.info(f"sending correction reponse")
				closest_match = find_close_match_item(s.lower(), "ship_list")
				closest_match_string = closest_match[0].title()
				embed = discord.Embed(title=f"Ship {s} is not understood.\n", description="")
				if len(closest_match) > 0:
					embed.description += f'\nDid you mean **{closest_match_string}**?'
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expires in 10 seconds")
					await context.send(embed=embed)
					try:
						msg = await mackbot.wait_for("message", timeout=10, check=user_correction_check)
						if msg:
							ships_to_compare += [get_ship_data(closest_match_string)]
					except asyncio.TimeoutError:
						pass
				else:
					await context.send(embed=embed)
					return
			finally:
				logger.info(f"ship check [{s}] OK")
		# ask for which parameter user would like to compare
		response_embed = discord.Embed(title="Which parameter would you like to compare?", description="")
		user_options = [
			"Main Battery",
			"Secondary Battery",
			"Torpedo",
			"Hull",
			"Anti-Air",
			"Attack Aircraft",
			"Torpedo Bombers",
			"Bombers",
			"Skip Bombers",
		]
		for i, o in enumerate(user_options):
			response_embed.description += f"**[{i+1}]** {o}\n"
		response_embed.set_footer(text="Response expires in 15 seconds")
		options = [SelectOption(label=o, value=i) for i, o in enumerate(user_options)]
		view = UserSelection(
			author=context.message.author,
			timeout=15,
			options=options,
			placeholder="Select an option"
		)
		view.message = await context.send(embed=response_embed, view=view)
		user_selection = await get_user_response_with_drop_down(view)
		if 0 <= user_selection < len(user_options):
			pass
		else:
			await context.send(f"Input {user_selection} is incorrect")

		# compile info
		if user_selection != -1:
			embed = discord.Embed(title=f"Comparing the {user_options[user_selection].lower()} of {ships_to_compare[0]['name']} and {ships_to_compare[1]['name']}")
			ship_module = [{}, {}]
			logger.info(f"returning comparison for {user_options[user_selection]}")
			m = "**Tier**\n"
			m += "**Type**\n"
			m += "**Nation**\n"
			embed.add_field(name="__Ship__", value=m)
			for i in range(2):
				m = f"{list(roman_numeral)[ships_to_compare[i]['tier'] - 1].upper() if ships_to_compare[i]['tier'] < 11 else ':star:'}\n"
				m += f"{icons_emoji[hull_classification_converter[ships_to_compare[i]['type']].lower()]}\n"
				m += f"{nation_dictionary[ships_to_compare[i]['nation']]}\n"
				embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m)

			if user_selection == 0:
				ship_module[0]['artillery'] = ships_to_compare[0]['modules']['artillery']
				ship_module[1]['artillery'] = ships_to_compare[1]['modules']['artillery']
				l = zip_longest(ship_module[0]['artillery'], ship_module[1]['artillery'])
				if ship_module[0]['artillery'] and ship_module[1]['artillery']:
					for pair in l:
						# set up title axis
						m = "**Gun**\n"
						m += "**Caliber**\n"
						m += "**Range**\n"
						m += "**Reload**\n"
						m += "**Transverse**\n"
						m += "**Precision**\n"
						m += "**Dispersion @ 10 km**\n"
						m += "**Dispersion @ max range**\n"
						m += "**HE Shell**\n"
						m += "**HE DPM**\n"
						m += "**AP Shell**\n"
						m += "**AP DPM**\n"
						m += "**SAP Shell**\n"
						m += "**SAP DPM**\n"
						m += "**Salvo\n**"
						embed.add_field(name="__Artillery__", value=m, inline=True)
						for i, mid in enumerate(pair):
							if mid is not None:
								module = get_module_data(mid)
								artillery = module['profile']['artillery']
								m = ""
								m += f"{module['name'][:20]}{'...' if len(module['name']) > 20 else ''}\n"
								m += f"{artillery['caliber'] * 1000:1.0f}mm\n"
								m += f"{artillery['range'] / 1000:1.1f}km\n"
								m += f"{artillery['shotDelay']}s\n"
								m += f"{artillery['transverse_speed']}{DEGREE_SYMBOL}/s\n"
								m += f"{artillery['sigma']}{SIGMA_SYMBOL}\n"
								m += f"{artillery['dispersion_h']['10000']:1.0f}m x {artillery['dispersion_v']['10000']:1.0f}m\n"
								m += f"{artillery['dispersion_h'][str(int(artillery['range']))]:1.0f}m x {artillery['dispersion_v'][str(int(artillery['range']))]:1.0f}m\n"
								if artillery['max_damage']['he']:
									m += f"{artillery['max_damage']['he']} ({icons_emoji['penetration']} {artillery['pen']['he']}mm, :fire: {artillery['burn_probability']}%)\n"
									m += f"{artillery['gun_dpm']['he']}\n"
								else:
									m += "-\n"
									m += "-\n"

								if artillery['max_damage']['ap']:
									m += f"{artillery['max_damage']['ap']}\n"
									m += f"{artillery['gun_dpm']['ap']}\n"
								else:
									m += "-\n"
									m += "-\n"

								if artillery['max_damage']['cs']:
									m += f"{artillery['max_damage']['cs']} ({icons_emoji['penetration']} {artillery['pen']['cs']}mm)\n"
									m += f"{artillery['gun_dpm']['cs']}\n"
								else:
									m += "-\n"
									m += "-\n"
								m += f"{sum(v['numBarrels'] * v['count'] for k, v in artillery['turrets'].items()):1.0f} shells\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have main battery guns")

			if user_selection == 1:
				ship_module[0]['hull'] = ships_to_compare[0]['modules']['hull']
				ship_module[1]['hull'] = ships_to_compare[1]['modules']['hull']
				l = zip_longest(ship_module[0]['hull'], ship_module[1]['hull'])

				if ships_to_compare[0]['default_profile']['atbas'] is not None and ships_to_compare[1]['default_profile']['atbas'] is not None :
					for pair in l:
						# set up title axis
						m = "**Hull**\n"
						m += "**Range**\n"
						m += "**DPM**\n"
						embed.add_field(name="__Secondary Guns__", value=m, inline=True)

						for i, mid in enumerate(pair):
							if mid is not None:
								module = get_module_data(mid)
								m = f"{module['name'][:20]}{'...' if len(module['name']) > 20 else ''}\n"
								m += f"{module['profile']['atba']['range']/1000:1.1f} km\n"
								m += f"{int(sum([module['profile']['atba'][t]['gun_dpm'] for t in module['profile']['atba'] if type(module['profile']['atba'][t]) == dict]))}\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have secondary battery guns")

			if user_selection == 2:
				ship_module[0]['torpedo'] = ships_to_compare[0]['modules']['torpedoes']
				ship_module[1]['torpedo'] = ships_to_compare[1]['modules']['torpedoes']
				l = zip_longest(ship_module[0]['torpedo'], ship_module[1]['torpedo'])
				if ship_module[0]['torpedo'] and ship_module[1]['torpedo']:
					for pair in l:
						# set up title axis
						m = "**Name**\n"
						m += "**Range**\n"
						m += "**Spotting Range**\n"
						m += "**Damage**\n"
						m += "**Reload**\n"
						m += "**Speed**\n"
						m += "**Salvo**\n"
						m += "**Deepwater**\n"
						embed.add_field(name="__Torpedo__", value=m, inline=True)

						for i, mid in enumerate(pair):
							if mid is not None:
								module = get_module_data(mid)
								torp = module['profile']['torpedoes']
								m = f"{module['name'][:20]}{'...' if len(module['name']) > 20 else ''}\n"
								m += f"{torp['range']:1.1f} km\n"
								m += f"{torp['spotting_range']:1.1f} km\n"
								m += f"{torp['max_damage']:1.0f}\n"
								m += f"{torp['shotDelay']:1.1f}s\n"
								m += f"{torp['torpedo_speed']:1.0f} kts.\n"
								m += f"{torp['numBarrels']} torpedoes\n"
								m += f"{'Yes' if torp['is_deep_water'] else 'No'}\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have torpedo launchers")
			if user_selection == 3:
				ship_module[0]['hull'] = ships_to_compare[0]['modules']['hull']
				ship_module[1]['hull'] = ships_to_compare[1]['modules']['hull']
				l = zip_longest(ship_module[0]['hull'], ship_module[1]['hull'])
				if ship_module[0]['hull'] and ship_module[1]['hull']:
					for pair in l:
						# set up title axis
						m = f"**Hull**\n"
						m += f"**Health**\n"
						m += f"**Turn Radius**\n"
						m += f"**Rudder Time**\n"
						m += f"**{icons_emoji['concealment']} by Sea**\n"
						m += f"**{icons_emoji['concealment']} by Air**\n"
						embed.add_field(name="__Concealment__", value=m, inline=True)

						for i, mid in enumerate(pair):
							if mid is not None:
								module = get_module_data(mid)
								hull = module['profile']['hull']
								m = f"{module['name']}\n"
								m += f"{hull['health']:1.0f} HP\n"
								m += f"{hull['turnRadius']:1.0f}m\n"
								m += f"{hull['rudderTime']:1.1f}s\n"
								m += f"{hull['detect_distance_by_ship']:1.1f} km\n"
								m += f"{hull['detect_distance_by_plane']:1.1f} km\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
			if user_selection == 4:
				ship_module[0]['hull'] = ships_to_compare[0]['modules']['hull']
				ship_module[1]['hull'] = ships_to_compare[1]['modules']['hull']
				l = zip_longest(ship_module[0]['hull'], ship_module[1]['hull'])
				if ship_module[0]['hull'] and ship_module[1]['hull']:
					for pair in l:
						# set up title axis
						m = "**Name**\n"
						m += "**Range**\n"
						m += "**Rating vs. same tier**\n"
						m += "**Analysis**\n"
						embed.add_field(name="__Anti-Air__", value=m, inline=True)

						for i, mid in enumerate(pair):
							if mid is not None:
								module = get_module_data(mid)
								aa = module['profile']['anti_air']
								aa_rating = aa['rating'][ships_to_compare[i % 2]['tier'] - 1]
								rating_descriptor = get_aa_rating_descriptor(aa_rating)

								m = f"{module['name'][:20]}{'...' if len(module['name']) > 20 else ''}\n"
								m += f"{aa['max_range'] / 1000:0.1f} km\n"
								m += f"{aa_rating}\n"
								m += f"{rating_descriptor}\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have torpedo launchers")
			if user_selection in [5, 6, 7, 8]:
				module_name = {
					5: 'fighter',
					6: 'torpedo_bomber',
					7: 'dive_bomber',
					8: 'skip_bomber',
				}[user_selection]
				projectile_type = {
					5: 'rocket(s)',
					6: 'torpedo(es)',
					7: 'bomb(s)',
					8: 'bomb(s)',
				}[user_selection]
				for i in range(2):
					mid = ships_to_compare[i]['modules'][module_name]
					ship_module[i][module_name] = []
					# for each aircraft found in this module, pair it with the associated module id
					# so that we can output every modules of each ships in alternating pattern
					# (ie, fighter1, fighter2, fighter1, fighter2...)
					for m in mid:
						ship_module[i][module_name] += get_module_data(m)['squadron']
				l = zip_longest(ship_module[0][module_name], ship_module[1][module_name])
				if ship_module[0][module_name] and ship_module[1][module_name]:
					for pair in l:
						# set up title axis
						m = "**Name**\n"
						m += "**Payload**\n"
						m += "**Speed**\n"
						m += "**Max Speed**\n"
						m += "**Health**\n"
						m += "**Payload/Flight**\n"
						m += "**DMG/Projectile**\n"
						m += "**Flight Count**\n"
						m += "**Attacking Flight**\n"
						m += "**Max DMG/Flight**\n"
						if user_selection == 5:
							m += "**Attack Delay**\n"
						if user_selection == 6:
							m += "**Torpedo Speed**\n"
							m += "**Arming Range**\n"
						embed.add_field(name=f"__{user_options[user_selection - 1]}__", value=m, inline=True)
						for ship_module_index, i in enumerate(pair):
							if i is not None:
								module = i
								plane = module['profile'][module_name]
								m = f"{module['name'][:20]}{'...' if len(module['name']) > 20 else ''}\n"
								m += f"{plane['payload_name']}{'...' if len(plane['payload_name']) > 20 else ''}\n"
								m += f"{plane['cruise_speed']} kts.\n"
								m += f"{plane['max_speed']} kts.\n"
								m += f"{plane['max_health'] * module['squad_size']:1.0f}\n"
								m += f"{plane['payload'] * module['attack_size']:1.0f} {projectile_type}\n"
								m += f"{plane['max_damage']:1.0f}\n"
								m += f"{module['squad_size'] // module['attack_size']:1.0f} flight(s)\n"
								m += f"{module['attack_size']:1.0f} aircraft\n"
								m += f"{plane['max_damage'] * plane['payload'] * module['attack_size']:1.0f}\n"
								if user_selection == 5:
									m += f"{plane['aiming_time']:0.1f}s\n"
								if user_selection == 6:
									m += f"{plane['torpedo_speed']:0.1f} kts\n"
									m += f"{plane['arming_range']:0.1f} m\n"
								embed.add_field(name=f"__{ships_to_compare[ship_module_index]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value=f"One of these ships does not have {user_options[user_selection].lower()}")
			await context.send(embed=embed)
		else:
			logging.info("Response expired")
		del user_correction_check

@mackbot.hybrid_command(name="skill", description="Get information on a commander skill")
@app_commands.describe(
	skill_tree="Skill tree query. Accepts ship hull classification or ship type",
	skill_name="Skill name"
)
async def skill(context: commands.Context, skill_tree: str, skill_name: str):
	# get information on requested skill
	# message parse
	if context.clean_prefix != '/':
		skill_name = ' '.join(context.message.content.split()[3:])

	try:
		# ship_class = args[0].lower()
		# skill_name = ''.join([i + ' ' for i in args[1:]])[:-1]  # message_string[message_string.rfind('-')+1:]

		logger.info(f'sending message for skill <{skill}>')
		# await context.typing()
		skill_data = get_skill_data(skill_tree, skill_name)
		name = skill_data['name']
		tree = skill_data['tree']
		description = skill_data['description']
		effect = skill_data['effect']
		column = skill_data['x'] + 1
		tier = skill_data['y'] + 1
		category = skill_data['category']
		embed = discord.Embed(title=f"{name}", description="")
		# embed.set_thumbnail(url=icon)
		embed.description += f"**{tree} Skill**\n"
		embed.description += f"**Tier {tier} {category} Skill**, "
		embed.description += f"**Column {column}**"
		embed.add_field(name='Description', value=description, inline=False)
		embed.add_field(name='Effect', value=effect, inline=False)
		await context.send(embed=embed)

	except Exception as e:
		logger.info(f"Exception in skill {type(e)}: {e}")
		traceback.print_exc()
		if type(e) == NoSkillFound:
			closest_match = find_close_match_item(skill_name, "skill_list")

			embed = discord.Embed(title=f"Skill {skill_name} is not understood.\n", description="")
			if len(closest_match) > 0:
				embed.description += f'\nDid you mean **{closest_match[0]}**?'
				embed.description += "\n\nType \"y\" or \"yes\" to confirm."
				embed.set_footer(text="Response expires in 10 seconds")
			await context.reply(embed=embed)
			await correct_user_misspell(context, 'skill', skill_tree, closest_match[0])
		if type(e) == SkillTreeInvalid:
			embed = discord.Embed(title=f"Skill tree is not understood.\n", description="")
			embed.description += f'\n{e}'
			await context.send(embed=embed)

#TODO: Find way to fix check function for show's subcommands

@mackbot.hybrid_group(name="show", description="List out all items from a category", pass_context=True, invoke_without_command=True)
# @mackbot.group(pass_context=True, invoke_without_command=True)
async def show(context: commands.Context):
	# list command
	if context.invoked_subcommand is None:
		await context.invoke(mackbot.get_command('help'), 'show')

@show.command(name="skills", description="Show all ships in a query.")
@app_commands.rename(args="query")
@app_commands.describe(args="Query to list items")
async def skills(context: commands.Context, args: Optional[str]=""):
	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = ' '.join(context.message.content.split()[3:])

	# list all skills
	search_param = args.split()
	search_param = skill_list_regex.findall(''.join([i + ' ' for i in search_param]))

	if database_client is not None:
		filtered_skill_list = database_client.mackbot_db.skill_list.find({})
		filtered_skill_list = dict((str(i['skill_id']), i) for i in filtered_skill_list)
	else:
		filtered_skill_list = skill_list.copy()

	# filter by ship class
	ship_class = [i[0] for i in search_param if len(i[0])]
	# convert hull classification to ship type full name
	ship_class = ship_class[0] if len(ship_class) >= 1 else ''
	if len(ship_class) > 0:
		if len(ship_class) <= 2:
			for h in hull_classification_converter:
				if ship_class == hull_classification_converter[h].lower():
					ship_class = h.lower()
					break
		if ship_class.lower() in ['cv', 'carrier']:
			ship_class = 'aircarrier'
		filtered_skill_list = dict([(s, filtered_skill_list[s]) for s in filtered_skill_list if filtered_skill_list[s]['tree'].lower() == ship_class])
	# filter by skill tier
	tier = [i[2] for i in search_param if len(i[2]) > 0]
	tier = int(tier[0]) if len(tier) >= 1 else 0
	if tier != 0:
		filtered_skill_list = dict([(s, filtered_skill_list[s]) for s in filtered_skill_list if filtered_skill_list[s]['y'] + 1 == tier])

	# select page
	page = [i[1] for i in search_param if len(i[1]) > 0]
	page = int(page[0]) if len(page) > 0 else 0

	# generate list of skills
	m = [
		f"**({hull_classification_converter[filtered_skill_list[s]['tree']]} T{filtered_skill_list[s]['y'] + 1})** {filtered_skill_list[s]['name']}" for s in filtered_skill_list
	]
	# splitting list into pages
	num_items = len(m)
	m.sort()
	items_per_page = 24
	num_pages = ceil(len(m) / items_per_page)
	m = [m[i:i + items_per_page] for i in range(0, len(m), items_per_page)]

	logger.info(f"found {num_items} items matching criteria: {args}")
	embed = discord.Embed(title="Commander Skill (%i/%i)" % (min(1, page+1), max(1, num_pages)))
	m = m[page]  # select page
	# spliting selected page into columns
	m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]
	for i in m:
		embed.add_field(name="(Type, tier) Skill", value=''.join([v + '\n' for v in i]))
	embed.set_footer(text=f"{num_items} skills found.\nFor more information on a skill, use [{command_prefix} skill [ship_class] [skill_name]]")

	await context.send(embed=embed)

@show.command(name="upgrades", description="Show all upgrades in a query.")
@app_commands.rename(args="query")
@app_commands.describe(args="Query to list items")
async def upgrades(context: commands.Context, args: Optional[str]=""):
	# list upgrades

	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = ' '.join(context.message.content.split()[3:])

	embed = None
	try:
		# parsing search parameters
		logger.info("starting parameters parsing")
		search_param = args.split()
		s = equip_regex.findall(''.join([i + ' ' for i in search_param]))

		slot = ''.join([i[1] for i in s])
		key = [i[7] for i in s if len(i[7]) > 1]
		page = [i[6] for i in s if len(i[6]) > 1]
		tier = [i[3] for i in s if len(i[3]) > 1]
		embed_title = "Search result for: "

		# select page
		page = int(page[0]) if len(page) > 0 else 1

		if len(tier) > 0:
			for t in tier:
				if t in roman_numeral:
					t = roman_numeral[t]
				tier = f't{t}'
				key += [t]
		if len(slot) > 0:
			key += [slot]
		key = [i.lower() for i in key if not 'page' in i]
		embed_title += f"{''.join([i.title() + ' ' for i in key])}"
		# look up
		result = []
		u_abbr_list = upgrade_abbr_list

		if database_client is not None:
			u_abbr_list = database_client.mackbot_db.upgrade_abbr_list.find({})
			query_result = database_client.mackbot_db.upgrade_list.find({"tags": {"$all": [re.compile(i, re.I) for i in key]}} if key else {})
			result = dict((i['consumable_id'], i) for i in query_result)
			u_abbr_list = dict((i['abbr'], i['upgrade']) for i in u_abbr_list)
		else:
			for u in upgrade_list:
				tags = [str(i).lower() for i in upgrade_list[u]['tags']]
				if all([k in tags for k in key]):
					result += [u]
		logger.info("parsing complete")
		logger.info("compiling message")

		if len(result) > 0:
			m = []
			for u in result:
				upgrade = result[u]
				name = upgrade['name']
				for u_b in u_abbr_list:
					if u_abbr_list[u_b] == name.lower():
						m += [f"**{name}** ({u_b.upper()})"]
						break

			num_items = len(m)
			m.sort()
			items_per_page = 30
			num_pages = ceil(len(m) / items_per_page)
			m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

			embed = discord.Embed(title=embed_title + f"({max(1, page)}/{num_pages})")
			m = m[page]  # select page
			m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
			embed.set_footer(text=f"{num_items} upgrades found.\nFor more information on an upgrade, use [{command_prefix} upgrade [name/abbreviation]]")
			for i in m:
				embed.add_field(name="Upgrade (abbr.)", value=''.join([v + '\n' for v in i]))
		else:
			embed = discord.Embed(title=embed_title, description="")
			embed.description = "No upgrades found"
	except Exception as e:
		if type(e) == IndexError:
			error_message = f"Page {page + 1} does not exists"
		elif type(e) == ValueError:
			logger.info(f"Upgrade listing argument <{args[3]}> is invalid.")
			error_message = f"Value {args[3]} is not understood"
		else:
			logger.info(f"Exception {type(e)} {e}")
	await context.send(embed=embed)

# @show.command()
# async def maps(context, *args):
# 	# list all maps
# 	try:
# 		logger.info("sending list of maps")
# 		try:
# 			page = int(args[3]) - 1
# 		except ValueError:
# 			page = 0
# 		m = [f"{map_list[i]['name']}" for i in map_list]
# 		m.sort()
# 		items_per_page = 20
# 		num_pages = ceil(len(map_list) / items_per_page)
#
# 		m = [m[i:i + items_per_page] for i in range(0, len(map_list), items_per_page)]  # splitting into pages
# 		embed = discord.Embed(title="Map List " + f"({page + 1}/{num_pages})")
# 		m = m[page]  # select page
# 		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
# 		for i in m:
# 			embed.add_field(name="Map", value=''.join([v + '\n' for v in i]))
# 	except Exception as e:
# 		if type(e) == IndexError:
# 			embed = None
# 			error_message = f"Page {page + 1} does not exists"
# 		elif type(e) == ValueError:
# 			logger.info(f"Upgrade listing argument <{args[3]}> is invalid.")
# 			error_message = f"Value {args[3]} is not understood"
# 		else:
# 			logger.info(f"Exception {type(e)} {e}")
# 	await context.send(embed=embed)

@show.command(name="ships", description="Show all ships in a query.")
@app_commands.rename(args="query")
@app_commands.describe(args="Query to list items")
# @show.command()
async def ships(context: commands.Context, args: Optional[str]=""):
	# parsing search parameters
	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = ' '.join(context.message.content.split()[3:])

	search_param = args.split()
	s = ship_list_regex.findall(''.join([str(i) + ' ' for i in search_param])[:-1])

	tier = ''.join([i[2] for i in s])
	key = [i[7] for i in s if len(i[7]) > 1]
	page = [i[6] for i in s if len(i[6]) > 0]

	# select page
	page = int(page[0]) if len(page) > 0 else 1

	if len(tier) > 0:
		if tier in roman_numeral:
			tier = roman_numeral[tier]
		tier = f't{tier}'
		key += [tier]
	key = [i.lower() for i in key if not 'page' in i]
	embed_title = f"Search result for {''.join([i.title() + ' ' for i in key])}"

	# look up
	result = []
	if database_client is not None:
		query_result = database_client.mackbot_db.ship_list.find({"tags": {"$all": [re.compile(f"^{i}$", re.I) for i in key]}} if key else {})
		if query_result is not None:
			result = dict((str(i["ship_id"]), i) for i in query_result)
	else:
		for s in ship_list:
			try:
				tags = [i.lower() for i in ship_list[s]['tags']]
				if all([k in tags for k in key]):
					result += [s]
			except Exception as e:
				traceback.print_exc()
				pass
	m = []
	logger.info(f"found {len(result)} items matching criteria: {' '.join(key)}")
	if len(result) > 0:
		# return the list of ships with fitting criteria
		for ship in result:
			ship_data = result[ship]
			if ship_data is None:
				continue
			name = ship_data['name']
			ship_type = ship_data['type']
			tier = ship_data['tier']
			is_prem = ship_data['is_premium']

			tier_string = [i for i in roman_numeral if roman_numeral[i] == tier][0]
			type_icon = icons_emoji[hull_classification_converter[ship_type].lower() + ("_prem" if is_prem else "")]
			# m += [f"**{tier_string:<6} {type_icon}** {name}"]
			m += [[tier, tier_string, type_icon, name]]

		num_items = len(m)
		m.sort(key=lambda x: (x[0], x[2], x[-1]))
		m = [f"**{(tier_string + ' '+ type_icon).ljust(16, chr(160))}** {name}" for tier, tier_string, type_icon, name in m]

		items_per_page = 30
		num_pages = ceil(len(m) / items_per_page)
		m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

		embed = discord.Embed(title=embed_title + f"({max(1, page)}/{max(1, num_pages)})")
		m = m[page - 1]  # select page
		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
		embed.set_footer(text=f"{num_items} ships found\nTo get ship build, use [{command_prefix} build [ship_name]]")
		for i in m:
			embed.add_field(name="(Tier) Ship", value=''.join([v + '\n' for v in i]))
	else:
		# no ships found
		embed = discord.Embed(title=embed_title, description="")
		embed.description = "**No ships found**"
	await context.send(embed=embed)

@mackbot.hybrid_command(name="upgrade", description="Get information on an upgrade")
@app_commands.describe(
	upgrade_name="Upgrade name, upgrade abbreviation, or ship name (applicable to ships with unique upgrades)."
)
async def upgrade(context: commands.Context, upgrade_name: str):
	logging.info(f"Received {upgrade_name}")
	if context.clean_prefix != '/':
		upgrade_name = ' '.join(context.message.content.split()[2:])

	# get information on requested upgrade
	if not upgrade_name:
		# argument is empty, send help message
		await bot_help(context, "upgrade")
	else:
		# getting appropriate search function
		try:
			# does user provide upgrade name?
			get_upgrade_data(upgrade_name)
			search_func = get_upgrade_data
		except NoUpgradeFound:
			# does user provide ship name, probably?
			get_legendary_upgrade_by_ship_name(upgrade_name)
			search_func = get_legendary_upgrade_by_ship_name

		try:
			# assuming that user provided the correct upgrade
			logger.info(f'sending message for upgrade <{upgrade_name}>')
			output = search_func(upgrade_name)
			profile = output['profile']
			name = output['name']
			image = output['image']
			price_credit = output['price_credit']
			description = output['description']
			is_special = output['is_special']
			ship_restriction = output['ship_restriction']
			nation_restriction = output['nation_restriction']
			tier_restriction = output['tier_restriction']
			type_restriction = output['type_restriction']
			slot = output['slot']
			special_restriction = output['additional_restriction']

			embed_title = 'Ship Upgrade'
			if is_special == 'Unique':
				embed_title = "Legendary Ship Upgrade"
			elif is_special == 'Coal':
				embed_title = "Coal Ship Upgrade"

			embed = discord.Embed(title=embed_title, description="")
			embed.set_thumbnail(url=image)
			# get server emoji
			if context.guild is not None:
				server_emojis = context.guild.emojis
			else:
				server_emojis = []

			embed.description += f"**{name}**\n"
			embed.description += f"**Slot {slot}**\n"
			if len(description.split()) > 0:
				embed.add_field(name='Description', value=description, inline=False)

			if len(profile) > 0:
				embed.add_field(name='Effect',
				                value=''.join([profile[detail]['description'] + '\n' for detail in profile]),
				                inline=False)
			else:
				logger.info("effect field empty")

			if not is_special == 'Unique':
				if len(type_restriction) > 0:
					# find the server emoji id for this emoji id
					if len(server_emojis) == 0:
						m = ''.join([i.title() + ', ' for i in sorted(type_restriction)])[:-2]
					else:
						m = ''
						for t in type_restriction:
							t = 'carrier' if t == 'Aircraft Carrier' else t
							for e in server_emojis:
								if t.lower() == e.name:
									m += str(e) + ' '
									break
						else:
							type_icon = ""
				else:
					m = "All types"
				embed.add_field(name="Ship Type", value=m)

				if len(tier_restriction) > 0:
					m = ''.join([str(i) + ', ' for i in tier_restriction])[:-2]
				else:
					m = "All tiers"
				embed.add_field(name="Tier", value=m)

				if len(nation_restriction) > 0:
					m = ''.join([i + ', ' for i in sorted(nation_restriction)])[:-2]
				else:
					m = 'All nations'
				embed.add_field(name="Nation", value=m)

				if len(ship_restriction) > 0:
					m = ''.join([i + ', ' for i in sorted(ship_restriction[:10])])[:-2]
					if len(ship_restriction) > 10:
						m += "...and more"
					if len(m) > 0:
						ship_restrict_title = {
							'': "Also Found On",
							'Coal': "Also Found On",
						}[is_special]
						embed.add_field(name=ship_restrict_title, value=m)
					else:
						logger.warning('Ships field is empty')
			if len(special_restriction) > 0:
				m = special_restriction
				if len(m) > 0:
					embed.add_field(name="Additonal Requirements", value=m)
				else:
					logger.warning("Additional requirements field empty")
			if price_credit > 0 and len(is_special) == 0:
				embed.add_field(name='Price (Credit)', value=f'{price_credit:,}')
			await context.send(embed=embed)
		except Exception as e:
			logger.info(f"Exception in upgrade: {type(e)} {e}")
			traceback.print_exc()

			closest_match = find_close_match_item(upgrade_name.lower(), "upgrade_list")

			embed = discord.Embed(title=f"Upgrade **{upgrade_name}** is not understood.\n", description="")
			if len(closest_match) > 0:
				embed.description += f'\nDid you mean **{closest_match[0]}**?'
				embed.description += "\n\nType \"y\" or \"yes\" to confirm."
				embed.set_footer(text="Response expires in 10 seconds")
			await context.send(embed=embed)
			await correct_user_misspell(context, 'upgrade', closest_match[0])

@mackbot.hybrid_command(name="player", description="Get information about a player.")
@app_commands.describe(
	value="Player name. For optional arguments, see mackbot help player or /player help"
)
async def player(context: commands.Context, value: str):
	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = context.message.content.split()[2:]
	else:
		args = value.split()

	if args:
		username = args[0][:24]
		async with context.typing():
			try:
				battle_type = 'pvp'
				battle_type_string = 'Random'
				player_region = 'na'

				# grab optional args
				if len(args) > 1:
					optional_args = player_arg_filter_regex.findall(' '.join(args[1:]))

					battle_type = [i[0] for i in optional_args if len(i[0])]
					ship_filter = [i[1] for i in optional_args if len(i[1])]
					if '-' in ship_filter:
						# if some how user adds a --tier, remove this (i sucks at regex)
						ship_filter = ship_filter.split("-")[0][:-1]
					player_region = [i[3] for i in optional_args if len(i[3])]# filter ship listing, same rule as list ships

					battle_type = battle_type[0] if len(battle_type) else ''
					ship_filter = ship_filter[0] if len(ship_filter) else ''
					player_region = player_region[0] if len(player_region) else ''
					if player_region not in WOWS_REALMS:
						player_region = 'na'
				else:
					optional_args = [''] * 5
					ship_filter = ''

				player_id_results = WG[player_region].account.list(search=username, type='exact', language='en')
				player_id = str(player_id_results[0]['account_id']) if len(player_id_results) > 0 else ""

				try:
					ship_tier_filter = int([i[2] for i in optional_args if len(i[2])][0])
				except (ValueError, IndexError):
					ship_tier_filter = 0
				try:
					# convert user specified specific stat to wg values
					battle_type = {
						"pvp": "pvp",
						"solo": "pvp_solo",
						"div2": "pvp_div2",
						"div3": "pvp_div3",
					}[battle_type]

					battle_type_string = {
						"pvp": "Random",
						"pvp_solo": "Solo Random",
						"pvp_div2": "2-man Random Division",
						"pvp_div3": "3-man Random Division",
					}[battle_type]
				except (IndexError, KeyError):
					battle_type = 'pvp'

				embed = discord.Embed(title=f"Search result for player {escape_discord_format(username)}", description='')
				if player_id:
					player_name = player_id_results[0]['nickname']
					if battle_type == 'pvp':
						player_general_stats = WG[player_region].account.info(account_id=player_id, language='en')[player_id]
					else:
						player_general_stats = WG[player_region].account.info(account_id=player_id, language='en', extra="statistics."+battle_type, )[player_id]
					player_account_hidden = player_general_stats['hidden_profile']

					if player_account_hidden:
						# account hidden, don't show any more status
						embed.add_field(name='Information not available', value="Account hidden", inline=False)
					else:
						# account not hidden, show info
						player_created_at_string = date.fromtimestamp(player_general_stats['created_at']).strftime("%b %d, %Y")
						player_last_battle_string = date.fromtimestamp(player_general_stats['last_battle_time']).strftime("%b %d, %Y")
						player_last_battle_days = (date.today() - date.fromtimestamp(player_general_stats['last_battle_time'])).days
						player_last_battle_months = int(player_last_battle_days // 30)
						player_clan_id = WG[player_region].clans.accountinfo(account_id=player_id, language='en')
						player_clan_tag = ""
						if player_clan_id[player_id] is not None: # Check if player has joined a clan yet
							player_clan_id = player_clan_id[player_id]['clan_id']
							if player_clan_id is not None: # check if player is in a clan
								player_clan = WG[player_region].clans.info(clan_id=player_clan_id, language='en')[player_clan_id]
								player_clan_str = f"**[{player_clan['tag']}]** {player_clan['name']}"
								player_clan_tag = f"[{player_clan['tag']}]"
							else:
								player_clan_str = "No clan"
						else:
							player_clan_str = "No clan"

						m = f"**Created at**: {player_created_at_string}\n"
						m += f"**Last battle**: {player_last_battle_string} "
						if player_last_battle_days > 0:
							if player_last_battle_months > 0:
								m += f"({player_last_battle_months} month{'s' if player_last_battle_months > 1 else ''} {player_last_battle_days // 30} day{'s' if player_last_battle_days // 30 > 1 else ''} ago)\n"
							else:
								m += f"({player_last_battle_days} day{'s' if player_last_battle_days > 1 else ''} ago)\n"
						else:
							m += " (Today)\n"
						m += f"**Clan**: {player_clan_str}\n"
						m += f"**Region**: {player_region.upper()}"
						embed.add_field(name=f'__**{player_clan_tag}{" " if player_clan_tag else ""}{player_name}**__', value=m, inline=False)

						# add listing for player owned ships and of requested battle type
						player_ships = WG[player_region].ships.stats(account_id=player_id, language='en', extra='' if battle_type == 'pvp' else battle_type)[player_id]
						player_ship_stats = {}
						# calculate stats for each ships
						for s in player_ships:
							ship_id = s['ship_id']
							ship_stat = s[battle_type]
							try:
								ship_name, ship_tier, ship_nation, ship_type, emoji = ship_list_simple[str(ship_id)].values()
							except KeyError:
								ship_name, ship_tier, ship_nation, ship_type, _, emoji = get_ship_data_by_id(ship_id).values()
							stats = {
								"name"          : ship_name.lower(),
								"tier"          : ship_tier,
								"emoji"         : emoji,
								"nation"        : ship_nation,
								"type"          : ship_type,
								"battles"       : ship_stat['battles'],
								'wins'          : ship_stat['wins'],
								'losses'        : ship_stat['losses'],
								'kills'         : ship_stat['frags'],
								'damage'        : ship_stat['damage_dealt'],
								"wr"            : 0 if ship_stat['battles'] == 0 else ship_stat['wins'] / ship_stat['battles'],
								"sr"            : 0 if ship_stat['battles'] == 0 else ship_stat['survived_battles'] / ship_stat['battles'],
								"avg_dmg"       : 0 if ship_stat['battles'] == 0 else ship_stat['damage_dealt'] / ship_stat['battles'],
								"avg_spot_dmg"  : 0 if ship_stat['battles'] == 0 else ship_stat['damage_scouting'] / ship_stat['battles'],
								"avg_kills"     : 0 if ship_stat['battles'] == 0 else ship_stat['frags'] / ship_stat['battles'],
								"avg_xp"        : 0 if ship_stat['battles'] == 0 else ship_stat['xp'] / ship_stat['battles'],
								"max_kills"     : ship_stat['max_frags_battle'],
								"max_dmg"       : ship_stat['max_damage_dealt'],
								"max_spot_dmg"  : ship_stat['max_damage_scouting'],
								"max_xp"        : ship_stat['max_xp'],
							}
							player_ship_stats[ship_id] = stats.copy()
						# sort player owned ships by battle count
						player_ship_stats = {k: v for k, v in sorted(player_ship_stats.items(), key=lambda x: x[1]['battles'], reverse=True)}
						player_ship_stats_df = pd.DataFrame.from_dict(player_ship_stats, orient='index')
						player_battle_stat = player_general_stats['statistics'][battle_type]

						if not ship_filter and not ship_tier_filter:
							# general information
							player_stat_wr = player_battle_stat['wins'] / player_battle_stat['battles']
							player_stat_sr = player_battle_stat['survived_battles'] / player_battle_stat['battles']
							player_stat_max_kills = player_battle_stat['max_frags_battle']
							player_stat_max_damage = player_battle_stat['max_damage_dealt']
							player_stat_max_spot_dmg = player_battle_stat['max_damage_scouting']

							ship_data = get_ship_data_by_id(player_battle_stat['max_frags_ship_id'])
							player_stat_max_kills_ship = ship_data['name']
							player_stat_max_kills_ship_type = ship_data['emoji']
							player_stat_max_kills_ship_tier = list(roman_numeral.keys())[ship_data['tier'] - 1]

							ship_data = get_ship_data_by_id(player_battle_stat['max_damage_dealt_ship_id'])
							player_stat_max_damage_ship = ship_data['name']
							player_stat_max_damage_ship_type = ship_data['emoji']
							player_stat_max_damage_ship_tier = list(roman_numeral.keys())[ship_data['tier'] - 1]

							ship_data = get_ship_data_by_id(player_battle_stat['max_scouting_damage_ship_id'])
							player_stat_max_spot_dmg_ship = ship_data['name']
							player_stat_max_spot_dmg_ship_type = ship_data['emoji']
							player_stat_max_spot_dmg_ship_tier = list(roman_numeral.keys())[ship_data['tier'] - 1]

							player_stat_avg_kills = player_battle_stat['frags'] / player_battle_stat['battles']
							player_stat_avg_dmg = player_battle_stat['damage_dealt'] / player_battle_stat['battles']
							player_stat_avg_xp = player_battle_stat['xp'] / player_battle_stat['battles']
							player_stat_avg_spot_dmg = player_battle_stat['damage_scouting'] / player_battle_stat['battles']

							m = f"**{player_battle_stat['battles']:,} battles**\n"
							m += f"**Win Rate**: {player_stat_wr:0.2%} ({player_battle_stat['wins']} W / {player_battle_stat['losses']} L / {player_battle_stat['draws']} D)\n"
							m += f"**Survival Rate**: {player_stat_sr:0.2%} ({player_battle_stat['survived_battles']} battles)\n"
							m += f"**Average Kills**: {player_stat_avg_kills:0.2f}\n"
							m += f"**Average Damage**: {player_stat_avg_dmg:,.0f}\n"
							m += f"**Average Spotting**: {player_stat_avg_spot_dmg:,.0f}\n"
							m += f"**Average XP**: {player_stat_avg_xp:,.0f} XP\n"
							m += f"**Highest Kill**: {to_plural('kill', player_stat_max_kills)} with {player_stat_max_kills_ship_type} **{player_stat_max_kills_ship_tier} {player_stat_max_kills_ship}**\n"
							m += f"**Highest Damage**: {player_stat_max_damage:,.0f} with {player_stat_max_damage_ship_type} **{player_stat_max_damage_ship_tier} {player_stat_max_damage_ship}**\n"
							m += f"**Highest Spotting Damage**: {player_stat_max_spot_dmg:,.0f} with {player_stat_max_spot_dmg_ship_type} **{player_stat_max_spot_dmg_ship_tier} {player_stat_max_spot_dmg_ship}**\n"
							embed.add_field(name=f"__**{battle_type_string} Battle**__", value=m, inline=True)

							# top 10 ships by battle count
							m = ""
							for i in range(10):
								try:
									s = player_ship_stats[list(player_ship_stats)[i]] # get ith ship
									m += f"**{s['emoji']} {list(roman_numeral)[s['tier'] - 1]} {s['name'].title()}** ({s['battles']} | {s['wr']:0.2%} WR)\n"
								except IndexError:
									pass
							embed.add_field(name=f"__**Top 10 {battle_type_string} Ships (by battles)**__", value=m, inline=True)

							embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=False)
							# battle distribution by ship types
							player_ship_stats_df = player_ship_stats_df.groupby(['type']).sum()
							m = ""
							for s_t in sorted([i for i in ship_types if i != "Aircraft Carrier"]):
								try:
									type_stat = player_ship_stats_df.loc[s_t]
									if type_stat['battles'] > 0:
										m += f"**{ship_types[s_t]}s**\n"

										type_average_kills = type_stat['kills'] / max(1, type_stat['battles'])
										type_average_dmg = type_stat['damage'] / max(1, type_stat['battles'])
										type_average_wr = type_stat['wins'] / max(1, type_stat['battles'])
										m += f"{int(type_stat['battles'])} battle{'s' if type_stat['battles'] else ''} ({type_stat['battles'] / player_battle_stat['battles']:2.1%})\n"
										m += f"{type_average_wr:0.2%} WR | {type_average_kills:0.2f} Kills | {type_average_dmg:,.0f} DMG\n\n"
								except KeyError:
									pass
							embed.add_field(name=f"__**Stat by Ship Types**__", value=m)

							# average stats by tier
							player_ship_stats_df = pd.DataFrame.from_dict(player_ship_stats, orient='index')
							player_ship_stats_df = player_ship_stats_df.groupby(['tier']).sum()
							m = ""
							for tier in range(1, 11):
								try:
									tier_stat = player_ship_stats_df.loc[tier]
									tier_average_kills = tier_stat['kills'] / max(1, tier_stat['battles'])
									tier_average_dmg = tier_stat['damage'] / max(1, tier_stat['battles'])
									tier_average_wr = tier_stat['wins'] / max(1, tier_stat['battles'])

									m += f"**{list(roman_numeral.keys())[tier - 1]}: {int(tier_stat['battles'])} battles ({tier_stat['battles'] / player_battle_stat['battles']:2.1%})**\n"
									m += f"{tier_average_wr:0.2%} WR | {tier_average_kills:0.2f} Kills | {tier_average_dmg:,.0f} DMG\n"
								except KeyError:
									m += f"**{list(roman_numeral.keys())[tier - 1]}**: No battles\n"
							embed.add_field(name=f"__**Average by Tier**__", value=m)
						elif ship_tier_filter:
							# list ships that the player has at this tier
							player_ship_stats_df = player_ship_stats_df[player_ship_stats_df['tier'] == ship_tier_filter]
							top_n = 10
							items_per_col = 5
							if len(player_ship_stats_df) > 0:
								r = 1
								for i in range(top_n // items_per_col):
									m = ""
									if i <= len(player_ship_stats_df) // items_per_col:
										for s in player_ship_stats_df.index[(items_per_col * i) : (items_per_col * (i+1))]:
											ship = player_ship_stats_df.loc[s] # get ith ship of filtered ship list by tier
											m += f"{r}) **{ship['emoji']} {ship['name'].title()}**\n"
											m += f"({ship['battles']} battles | {ship['wr']:0.2%} WR | {ship['sr']:2.2%} SR)\n"
											m += f"Avg. Kills: {ship['avg_kills']:0.2f} | Avg. Damage: {ship['avg_dmg']:,.0f}\n\n"
											r += 1
										embed.add_field(name=f"__**Top {top_n} Tier {ship_tier_filter} Ships (by battles)**__", value=m, inline=True)
							else:
								embed.add_field(name=f"__**Top {top_n} Tier {ship_tier_filter} Ships (by battles)**__", value="Player have no ships of this tier", inline=True)
						elif ship_filter:
							# display player's specific ship stat
							m = ""
							try:
								ship_data = get_ship_data(ship_filter)
								ship_filter = ship_data['name'].lower()
								ship_id = ship_data['ship_id']
								player_ship_stats_df = player_ship_stats_df[player_ship_stats_df['name'] == ship_filter].to_dict(orient='index')[ship_id]
								ship_battles_draw = player_ship_stats_df['battles'] - (player_ship_stats_df['wins'] + player_ship_stats_df['losses'])
								m += f"**{player_ship_stats_df['emoji']} {list(roman_numeral.keys())[player_ship_stats_df['tier'] - 1]} {player_ship_stats_df['name'].title()}**\n"
								m += f"**{player_ship_stats_df['battles']} Battles**\n"
								m += f"**Win Rate:** {player_ship_stats_df['wr']:2.2%} ({player_ship_stats_df['wins']} W | {player_ship_stats_df['losses']} L | {ship_battles_draw} D)\n"
								m += f"**Survival Rate: ** {player_ship_stats_df['sr']:2.2%} ({player_ship_stats_df['sr'] * player_ship_stats_df['battles']:1.0f} battles)\n"
								m += f"**Average Kills: ** {player_ship_stats_df['avg_kills']:0.2f}\n"
								m += f"**Average Damage: ** {player_ship_stats_df['avg_dmg']:,.0f}\n"
								m += f"**Average Spotting Damage: ** {player_ship_stats_df['avg_spot_dmg']:,.0f}\n"
								m += f"**Average XP: ** {player_ship_stats_df['avg_xp']:,.0f}\n"
								m += f"**Max Damage: ** {player_ship_stats_df['max_dmg']:,.0f}\n"
								m += f"**Max Spotting Damage: ** {player_ship_stats_df['max_spot_dmg']:,.0f}\n"
								m += f"**Max XP: ** {player_ship_stats_df['max_xp']:,.0f}\n"
							except Exception as e:
								if type(e) == NoShipFound:
									m += f"Ship with name {ship_filter} is not found\n"
								if type(e) == KeyError:
									m += f"This player has never played {ship_filter.title()}\n"
								else:
									m += "An internal error has occurred.\n"
									traceback.print_exc()
							embed.add_field(name="__Ship Specific Stat__", value=m)

						embed.set_footer(text=f"Last updated at {date.fromtimestamp(player_general_stats['stats_updated_at']).strftime('%b %d, %Y')}")
				else:
					embed.add_field(name='Information not available', value=f"mackbot cannot find player with name {escape_discord_format(username)} in the {player_region.upper()} region", inline=True)
			except Exception as e:
				logger.warning(f"Exception in player {type(e)}: {e}")
				traceback.print_exc()
		await context.send(embed=embed)
	else:
		await bot_help(context, "player")

@mackbot.hybrid_command(name="clan", description="Get some basic information about a clan")
@app_commands.rename(args="clan")
@app_commands.describe(
	args="Name or tag of clan"
)
async def clan(context: commands.Context, args: str):
	# check if *not* slash command,
	if context.clean_prefix != '/':
		args = context.message.content.split()[2:]
	else:
		args = args.split()

	if args:
		# grab optional args
		optional_args = clan_filter_regex.findall(' '.join(args))[0]

		search_term = optional_args[0]
		clan_region = optional_args[1] # filter ship listing, same rule as list ships

		if clan_region not in WOWS_REALMS:
			clan_region = 'na'

		if not search_term:
			await bot_help(context, "clan")
			return

		clan_search = WG[clan_region].clans.list(search=search_term)
		if clan_search:
			# check for multiple clan
			selected_clan = None
			if len(clan_search) > 1:
				clan_options= [SelectOption(label=f"[{i + 1}] [{escape_discord_format(c['tag'])}] {c['name']}", value=i) for i, c in enumerate(clan_search)][:25]
				view = UserSelection(context.author, 15, "Select a clan", clan_options)

				embed = discord.Embed(title=f"Search result for clan {search_term}", description="")
				embed.description += "**mackbot found the following clans**\n"
				embed.description += '\n'.join(i.label for i in clan_options)
				embed.set_footer(text="Please reply with the number indicating the clan you would like to search\n"+
				                      "Response expires in 15 seconds")
				view.message = await context.send(embed=embed, view=view)
				await view.wait()
				selected_clan_index = await get_user_response_with_drop_down(view)
				if selected_clan_index != -1:
					# user responded
					selected_clan = clan_search[selected_clan_index]
				else:
					# no response
					return
			else:
				selected_clan = clan_search[0]
			# output clan information
			# get clan information

			clan_detail = WG[clan_region].clans.info(clan_id=selected_clan['clan_id'], extra='members')[str(selected_clan['clan_id'])]
			clan_id = clan_detail['clan_id']
			embed = discord.Embed(title=f"Search result for clan {clan_detail['name']}", description="")
			embed.set_footer(text=f"Last updated {date.fromtimestamp(clan_detail['updated_at']).strftime('%b %d, %Y')}")

			clan_age = (date.today() - date.fromtimestamp(clan_detail['created_at'])).days
			clan_age_day = clan_age % 30
			clan_age_month = (clan_age // 30) % 12
			clan_age_year = clan_age // (12 * 30)
			clan_created_at_str = date.fromtimestamp(clan_detail['created_at']).strftime("%b %d, %Y")
			m = f"**Leader: **{clan_detail['leader_name']}\n"
			m += f"**Created at: **{clan_created_at_str} ("
			if clan_age_year:
				m += f"{clan_age_year} year{'' if clan_age_year == 1 else 's'} "
			if clan_age_month:
				m += f"{clan_age_month} month{'' if clan_age_month == 1 else 's'} "
			if clan_age_day:
				m += f"{clan_age_day} day{'' if clan_age_day == 1 else 's'}"
			m += ')\n'
			if clan_detail['old_tag'] and clan_detail['old_name']:
				m += f"**Formerly:** [{clan_detail['old_tag']}] {clan_detail['old_name']}\n"
			m += f"**Members: ** {clan_detail['members_count']}\n"
			m += f"**Region: ** {clan_region.upper()}\n"
			embed.add_field(name=f"__**[{clan_detail['tag']}] {clan_detail['name']}**__", value=m, inline=not clan_detail['description'])

			if clan_detail['description']:
				embed.add_field(name="__**Description**__", value=clan_detail['description'], inline=False)
			# update clan history for member transfer feature
			# check clan in data
			history_output = []
			if clan_id in clan_history:
				# check differences
				new_member_list = clan_detail['members']
				previous_member_list = clan_history[clan_id]['members']
				members_out = set(previous_member_list.keys()) - set(new_member_list.keys())
				members_in = set(new_member_list.keys()) - set(previous_member_list.keys())
				for m in members_out:
					history_output += [(previous_member_list[m]['account_name'], icons_emoji['clan_out'])]
				for m in members_in:
					history_output += [(new_member_list[m]['account_name'], icons_emoji['clan_in'])]

				# check if last update was at least a week ago
				if (date.fromtimestamp(clan_detail['updated_at']) - date.fromtimestamp(clan_history[clan_id]['updated_at'])).days > 7:
					# update history
					clan_history[clan_id] = {'members': clan_detail['members'], 'updated_at': clan_detail['updated_at']}
			else:
				# not in history, add to history
				clan_history[clan_id] = {'members': clan_detail['members'], 'updated_at': clan_detail['updated_at']}

			if history_output:
				embed.add_field(name=f"__**Transfer History**__", value='\n'.join(f"{name}{icon}" for name, icon in history_output), inline=False)

			# output members
			members_per_column = 10
			clan_members_sort_by_alpha = sorted(list([escape_discord_format(clan_detail['members'][m]['account_name']) for m in clan_detail['members']]))
			for i in range(0, 50, members_per_column):
				sliced_member_list = clan_members_sort_by_alpha[i:i+members_per_column]
				if sliced_member_list:
					embed.add_field(name=f"__**Members**__", value='\n'.join(sliced_member_list), inline=True)
			await context.send(embed=embed)
		else:
			# no clan matches search
			embed = discord.Embed(title=f"Search result for clan {search_term}", description="")
			embed.description += "Clan not found"

			await context.send(embed=embed)
	else:
		await bot_help(context, "clan")

@mackbot.command()
async def commander(context, *args):
	pass
	# get information on requested commander
	# message parse
	# cmdr = ''.join([i + ' ' for i in args])[:-1]  # message_string[message_string.rfind('-')+1:]
	# if len(args) == 0:
	# 	await help(context, "commander")
	# else:
	# 	try:
	# 		async with context.typing():
	# 			logger.info(f'sending message for commander <{cmdr}>')
	#
	# 			output = get_commander_data(cmdr)
	# 			if output is None:
	# 				raise NameError("NoCommanderFound")
	# 			name, icon, nation, cmdr_id = output
	# 			embed = discord.Embed(title="Commander")
	# 			embed.set_thumbnail(url=icon)
	# 			embed.add_field(name='Name', value=name, inline=False)
	# 			embed.add_field(name='Nation', value=nation_dictionary[nation], inline=False)
	#
	# 			cmdr_data = None
	# 			for i in game_data:
	# 				if game_data[i]['typeinfo']['type'] == 'Crew':
	# 					if cmdr_id == str(game_data[i]['id']):
	# 						cmdr_data = game_data[i]
	#
	# 			'''
	# 			skill_bonus_string = ''
	#
	# 			for c in cmdr_data['Skills']:
	# 				skill = cmdr_data['Skills'][c].copy()
	# 				if skill['isEpic']:
	# 					skill_name, _, skill_type, _, _, _ = get_skill_data_by_grid(skill['column'], skill['tier'])
	# 					skill_bonus_string += f'**{skill_name}** ({skill_type}, Tier {skill["tier"]}):\n'
	# 					for v in ['column', 'skillType', 'tier', 'isEpic', 'turnOffOnRetraining']:
	# 						del skill[v]
	# 					if c in ['SurvivalModifier', 'MainGunsRotationModifier']:
	# 						for descriptor in skill:
	# 							skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] > 0 else ''}{skill[descriptor]:0.0f}\n"
	# 							if c == 'MainGunsRotationModifier':
	# 								skill_bonus_string += ' °/sec.'
	# 					else:
	# 						for descriptor in skill:
	# 							if c == 'TorpedoAcceleratorModifier':
	# 								if descriptor in ['planeTorpedoSpeedBonus', 'torpedoSpeedBonus']:
	# 									skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] > 0 else ''}{skill[descriptor]:0.0f} kts.\n"
	# 								else:
	# 									skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] - 1 > 0 else ''}{int(round((skill[descriptor] - 1) * 100))}%\n"
	# 							else:
	# 								if abs(skill[descriptor] - 1) > 0:
	# 									skill_bonus_string += f"{cmdr_skill_descriptor[c][descriptor + 'Descriptor']} {'+' if skill[descriptor] - 1 > 0 else ''}{int(round((skill[descriptor] - 1) * 100))}%\n"
	# 					skill_bonus_string += '\n'
	#
	# 			if len(skill_bonus_string) > 0:
	# 				embed.add_field(name='Skill Bonuses', value=skill_bonus_string, inline=False)
	# 				embed.set_footer(text="For default skill bonuses, use [mackbot skill [skill name]]")
	# 			else:
	# 				embed.add_field(name='Skill Bonuses', value="None", inline=False)
	# 			'''
	# 		await context.send(embed=embed)
	# 	except Exception as e:
	# 		logger.info(f"Exception {type(e)}: ", e)
	# 		# error, ship name not understood
	# 		cmdr_name_list = [cmdr_list[i]['first_names'] for i in cmdr_list]
	# 		closest_match = difflib.get_close_matches(cmdr, cmdr_name_list)
	# 		closest_match_string = ""
	# 		if len(closest_match) > 0:
	# 			closest_match_string = f'\nDid you mean **{closest_match[0]}**?'
	#
	# 		await context.send(f"Commander **{cmdr}** is not understood.")

# @mackbot.command()
# async def map(context, *args):
# 	pass
	# # get information on requested map
	# # message parse
	# map = ''.join([i + ' ' for i in args])[:-1]  # message_string[message_string.rfind('-')+1:]
	# if len(args) == 0:
	# 	await help(context, "map")
	# else:
	# 	try:
	# 		async with context.typing():
	# 			logger.info(f'sending message for map <{map}>')
	# 			description, image, id, name = get_map_data(map)
	# 			embed = discord.Embed(title="Map")
	# 			embed.set_image(url=image)
	# 			embed.add_field(name='Name', value=name)
	# 			embed.add_field(name='Description', value=description)
	#
	# 		await context.send(embed=embed)
	# 	except Exception as e:
	# 		logger.info(f"Exception {type(e)}: ", e)
	# 		# error, ship name not understood
	# 		map_name_list = [map_list[i]['name'] for i in map_list]
	# 		closest_match = difflib.get_close_matches(map, map_name_list)
	# 		closest_match_string = ""
	# 		if len(closest_match) > 0:
	# 			closest_match_string = f'\nDid you mean **{closest_match[0]}**?'
	#
	# 		await context.send(f"Map **{map}** is not understood.")

@mackbot.hybrid_command(name="doubloons", description="Converts doubloons to USD, vice versa.")
@app_commands.describe(
	value="The doubloon value for conversion to dollars. If is_dollar is filled, this value is converted to USD instead.",
	is_dollar="Add the word \"dollar\" or \"$\" to convert value into dollar value"
)
async def doubloons(context: commands.Context, value: int, is_dollar: Optional[str] = ""):
	# get conversion between doubloons and usd and vice versa
	doub = 0
	try:
		if is_dollar:
			# check reverse conversion
			# dollars to doubloons
			if is_dollar.lower() in ['dollars', '$']:
				dollar = float(value)

				def dollar_formula(x):
					return x * EXCHANGE_RATE_DOUB_TO_DOLLAR

				logger.info(f"converting {dollar} dollars -> doubloons")
				embed = discord.Embed(title="Doubloon Conversion (Dollars -> Doubloons)")
				embed.add_field(name=f"Requested Dollars", value=f"{dollar:0.2f}$")
				embed.add_field(name=f"Doubloons", value=f"Approx. {dollar_formula(dollar):0.0f} Doubloons")
			else:
				embed = discord.Embed(
					title="Doubloon Conversion Error",
					description=f"Value {is_dollar} is not a value optional argument"
				)
		else:
			# doubloon to dollars
			doub = int(value)
			value_exceed = not (500 <= doub <= 100000)

			def doub_formula(x):
				return x / EXCHANGE_RATE_DOUB_TO_DOLLAR

			logger.info(f"converting {doub} doubloons -> dollars")
			embed = discord.Embed(title="Doubloon Conversion (Doubloons -> Dollars)")
			embed.add_field(name=f"Requested Doubloons", value=f"{doub} Doubloons")
			embed.add_field(name=f"Price: ", value=f"{doub_formula(doub):0.2f}$")
			footer_message = f"Current exchange rate: {EXCHANGE_RATE_DOUB_TO_DOLLAR} Doubloons : 1 USD"
			if value_exceed:
				footer_message += "\n:warning: You cannot buy the requested doubloons."
			embed.set_footer(text=footer_message)

		await context.send(embed=embed)
	except Exception as e:
		logger.info(f"Exception {type(e)} {e}")
		if type(e) == TypeError:
			await context.send(f"Value **{doub}** is not a number.")
		else:
			await context.send(f"An internal error has occured.")
			traceback.print_exc()

@mackbot.hybrid_command(name="code", description="Generate WoWS bonus code links")
@app_commands.rename(args="codes")
@app_commands.describe(args="WoWS codes to generate link")
async def code(context, args: str):
	if context.clean_prefix != '/':
		args = ' '.join(context.message.content.split()[2:])

	# find region
	if args.split()[0].lower() in WOWS_REALMS:
		region = args.split()[0].lower()
		has_region_option = True
	else:
		region = 'na'
		has_region_option = False

	if len(args) == 0 or (has_region_option and len(args) == 1):
		await bot_help(context, "code")
	else:
		s = ""

		for c in args.split()[1:] if has_region_option else args.split():
			s += f"**({region.upper()}) {c.upper()}** https://{region}.wargaming.net/shop/redeem/?bonus_mode={c.upper()}\n"
			logger.info(f"returned a wargaming bonus code link with code {c}")
		await context.send(s)

@mackbot.hybrid_command(name="hottake", description="Give a WoWS hottake")
async def hottake(context: commands.Context):
	logger.info("sending a hottake")
	await context.send('I tell people that ' + hottake_strings[randint(0, len(hottake_strings)-1)])
	if randint(0, 9) == 0:
		await asyncio.sleep(2)
		await purpose(context)

async def purpose(context: commands.Context):
	author = context.author
	await context.send(f"{author.mention}, what is my purpose?")
	def check(message):
		return author == message.author and message.content.lower().startswith("you") and len(message.content[3:]) > 0

	message = await mackbot.wait_for('message', timeout=30, check=check)
	await context.send("Oh my god...")

@mackbot.hybrid_command(name="web", description="Get the link to mackbot's web application")
async def web(context: commands.Context):
	await context.send("**mackbot's web application URL:\nhttps://mackbot-web.herokuapp.com/**")

@mackbot.hybrid_command(name="invite", description="Get a Discord invite link to get mackbot to your server.")
async def invite(context: commands.Context):
	await context.send(bot_invite_url)

@mackbot.hybrid_command(name="commands", description="Get list of commands")
async def cmd(context: commands.Context):
	embed = discord.Embed(title="mackbot commands")

	m = ""
	for command in sorted([c.name for c in mackbot.commands]):
		m += f"**{command}:** {help_dictionary[command]['brief']}\n"
	embed.add_field(name="Command (Description)", value=m)
	embed.set_footer(text="For usage on any commands, use mackbot help <command>")

	await context.send(embed=embed)

@mackbot.hybrid_command(name="support", description="Get mackbot's support Discord server")
async def support(context: commands.Context):
	await context.send(discord_invite_url)


async def main():
	# load some stuff
	post_process()
	if not os.path.isdir("logs"):
		os.mkdir("logs")

	# print("commands usable:")
	# for c in command_list:
	# 	print(f"{c:<10}: {'Yes' if command_list[c] else 'No':<3}")

	if database_client is None:
		load_ship_builds()

	await mackbot.load_extension("scripts.misc_commands.wtn")
	await mackbot.add_cog(Listener(mackbot, command_prefix))
	await mackbot.add_cog(BotHelp(mackbot))
	await mackbot.add_cog(Ship(mackbot))

	# logger.info("kill switch detected")
	# # write clan history file
	# with open(clan_history_file_path, 'wb') as f:
	# 	pickle.dump(clan_history, f)
	# logger.info(f"Wrote {clan_history_file_path}")

if __name__ == '__main__':
	asyncio.run(main())
	mackbot.run(bot_token)