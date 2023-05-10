from typing import List

import discord
from discord import app_commands

from mackbot.utilities.game_data.warships_data import ship_list_simple, upgrade_list_simple, skill_list_simple

async def auto_complete_ship_name(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	"""

	Args:
		interaction (discord.Interaction): A discord interaction object
		current (str): the current typing string

	Returns:
		list
	"""

	choices = [app_commands.Choice(name=ship['name'] , value=ship['name']) for _, ship in ship_list_simple.items() if current in ship['name'].lower()]
	return choices[:25]


async def auto_complete_upgrades_name(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	"""

	Args:
		interaction (discord.Interaction): A discord interaction object
		current (str): the current typing string

	Returns:
		list
	"""

	choices = [app_commands.Choice(name=upgrade['name'] , value=upgrade['name']) for _, upgrade in upgrade_list_simple.items() if current in upgrade['name'].lower()]
	return choices[:25]

async def auto_complete_skill_name(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	"""

	Args:
		interaction (discord.Interaction): A discord interaction object
		current (str): the current typing string

	Returns:
		list
	"""

	choices = [app_commands.Choice(name=skill, value=skill) for skill, _ in skill_list_simple.items() if current in skill.lower()]
	return choices[:25]