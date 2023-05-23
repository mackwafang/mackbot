from typing import List

import discord
from discord import app_commands

from mackbot.utilities.game_data.warships_data import ship_list_simple, upgrade_list_simple, skill_list_simple
from mackbot.constants import ROMAN_NUMERAL
from mackbot.enums import SHIP_COMBAT_PARAM_FILTER

INTERNAL_PARAMS_NAME_TO_READABLE = {
	SHIP_COMBAT_PARAM_FILTER.HULL: "Hull",
	SHIP_COMBAT_PARAM_FILTER.GUNS: "Main Battery",
	SHIP_COMBAT_PARAM_FILTER.ATBAS: "Secondary Battery",
	SHIP_COMBAT_PARAM_FILTER.TORPS: "Torpedoes",
	SHIP_COMBAT_PARAM_FILTER.ROCKETS: "Attackers",
	SHIP_COMBAT_PARAM_FILTER.TORP_BOMBER: "Torpedo Bombers",
	SHIP_COMBAT_PARAM_FILTER.BOMBER: "Bombers",
	SHIP_COMBAT_PARAM_FILTER.ENGINE: "Engine",
	SHIP_COMBAT_PARAM_FILTER.AA: "Anti-Air",
	SHIP_COMBAT_PARAM_FILTER.CONCEAL: "Concealment",
	SHIP_COMBAT_PARAM_FILTER.CONSUMABLE: "Consumables",
	SHIP_COMBAT_PARAM_FILTER.UPGRADES: "Upgrades",
	SHIP_COMBAT_PARAM_FILTER.ARMOR: "Armor",
	SHIP_COMBAT_PARAM_FILTER.SONAR: "Sonar",
}

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

async def auto_complete_region(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	return [app_commands.Choice(name=region, value=region) for region in ['NA', 'EU', 'ASIA']]

async def auto_complete_tier(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	return [app_commands.Choice(name=ROMAN_NUMERAL[region], value=region+1) for region in range(0, 11)]

async def auto_complete_battle_type(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	return [app_commands.Choice(name=region, value=region) for region in ['pvp', 'solo', 'div2', 'div3']]

async def auto_complete_ship_parameters(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
	params = [INTERNAL_PARAMS_NAME_TO_READABLE[i] for i in SHIP_COMBAT_PARAM_FILTER]
	return [app_commands.Choice(name=region, value=region) for region in params]