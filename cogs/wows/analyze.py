import re, traceback
from typing import Optional

from hashlib import sha256

import discord
from discord import app_commands, Embed, File
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.pyplot import figure

from mackbot.constants import SHIP_TYPES, ROMAN_NUMERAL, DEGREE_SYMBOL, nation_dictionary
from mackbot.exceptions import *
from mackbot.ballistics.ballistics import build_trajectory, get_impact_time_at_max_range, get_trajectory_at_range
from mackbot.utilities.discord.formatting import number_separator
from mackbot.utilities.discord.items_autocomplete import auto_complete_ship_name, auto_complete_ship_parameters
from mackbot.utilities.logger import logger
from mackbot.utilities.regex import ship_param_filter_regex
from mackbot.utilities.game_data.warships_data import database_client, module_list
from mackbot.utilities.game_data.game_data_finder import get_ship_data
from mackbot.utilities.correct_user_mispell import correct_user_misspell
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.to_plural import to_plural

class SHIP_COMBAT_PARAM_FILTER(IntEnum):
	HULL = 0
	GUNS = auto()
	ATBAS = auto()
	TORPS = auto()
	ROCKETS = auto()
	TORP_BOMBER = auto()
	BOMBER = auto()
	ENGINE = auto()
	AA = auto()
	CONCEAL = auto()
	CONSUMABLE = auto()
	UPGRADES = auto()

SHELL_COLOR = {
	'ap': 'gray',
	'he': 'yellow',
	'sap': 'orange',
	'cs': 'orange'
}

LINE_STYLES = (
	'solid',
	'dotted',
	'dashed',
	'dashdot'
)

class Analyze(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name='analyze', description='Get combat parameters of a warship')
	@app_commands.describe(
		ship_name="Ship name",
		parameters="Ship parameters for detailed report",
	)
	@app_commands.autocomplete(
		ship_name=auto_complete_ship_name,
		parameters=auto_complete_ship_parameters
	)
	async def analyze(self, interaction: discord.Interaction, ship_name: str, parameters: Optional[str]=""):
		"""
			Outputs an embeded message to the channel (or DM) that contains information about a queried warship

		"""

		param_filter = parameters.lower()

		try:
			ship_data = get_ship_data(ship_name)
			if ship_data is None:
				raise NoShipFound

			name = ship_data['name']
			nation = ship_data['nation']
			images = ship_data['images']
			ship_type = ship_data['type']
			tier = ship_data['tier']
			consumables = ship_data['consumables']
			modules = ship_data['modules']
			upgrades = ship_data['upgrades']
			is_prem = ship_data['is_premium']
			is_test_ship = ship_data['is_test_ship']
			price_gold = ship_data['price_gold']
			price_credit = ship_data['price_credit']
			price_xp = ship_data['price_xp']
			logger.info(f"[ship] returning ship information for <{name}> in embeded format")
			ship_type = SHIP_TYPES[ship_type]

			if ship_type == 'Cruiser':
				# reclassify cruisers to their correct classification based on the washington naval treaty

				# check for the highest main battery caliber found on this warship
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['artillery']}
					}).sort(
						"profile.artillery.caliber", -1
					)
					highest_caliber = list(query_result)[0]['profile']['artillery']['caliber'] * 1000
				else:
					highest_caliber = sorted(modules['artillery'], key=lambda x: module_list[str(x)]['profile']['artillery']['caliber'],reverse=True)
					highest_caliber = [module_list[str(i)]['profile']['artillery']['caliber'] for i in highest_caliber][0] * 1000

				if highest_caliber <= 155:
					# if caliber less than or equal to 155mm
					ship_type = "Light Cruiser"
				elif highest_caliber <= 203:
					# if caliber between 155mm and up to 203mm
					ship_type = "Heavy Cruiser"
				else:
					ship_type = "Battlecruiser"
			test_ship_status_string = '[TEST SHIP] * ' if is_test_ship else ''
			embed = Embed(title=f"{ship_type} {name} {test_ship_status_string}", description='')
			image_embeds = []

			tier_string = ROMAN_NUMERAL[tier - 1]
			if tier < 11:
				tier_string = tier_string.upper()
			embed.description += f'**Tier {tier_string} {"Premium" if is_prem else ""} {nation_dictionary[nation]} {ship_type}**\n'
			if price_credit > 0 and price_xp > 0:
				embed.description += f'\n{number_separator(price_xp)} XP\n{number_separator(price_credit)} Credits'
			if price_gold > 0 and is_prem:
				embed.description += f'\n{number_separator(price_gold)} Doubloons'

			embed.set_thumbnail(url=images['small'])

			# defines ship params filtering

			ship_filter = 0b111111111111  # assuming no filter is provided, display all
			# grab filters
			if len(param_filter) > 0:
				ship_filter = 0  # filter is requested, disable all
				s = ship_param_filter_regex.findall(param_filter)  # what am i looking for?

				def is_filter_requested(x):
					# check length of regex capture groups. if len > 0, request is valid
					return 1 if len([i[x - 1] for i in s if len(i[x - 1]) > 0]) > 0 else 0

				# enables proper filter
				ship_filter |= is_filter_requested(2) << SHIP_COMBAT_PARAM_FILTER.HULL
				ship_filter |= is_filter_requested(3) << SHIP_COMBAT_PARAM_FILTER.GUNS
				ship_filter |= is_filter_requested(4) << SHIP_COMBAT_PARAM_FILTER.ATBAS
				ship_filter |= is_filter_requested(6) << SHIP_COMBAT_PARAM_FILTER.TORPS
				ship_filter |= is_filter_requested(8) << SHIP_COMBAT_PARAM_FILTER.ROCKETS
				ship_filter |= is_filter_requested(5) << SHIP_COMBAT_PARAM_FILTER.TORP_BOMBER
				ship_filter |= is_filter_requested(7) << SHIP_COMBAT_PARAM_FILTER.BOMBER
				ship_filter |= is_filter_requested(9) << SHIP_COMBAT_PARAM_FILTER.ENGINE
				ship_filter |= is_filter_requested(10) << SHIP_COMBAT_PARAM_FILTER.AA
				ship_filter |= is_filter_requested(11) << SHIP_COMBAT_PARAM_FILTER.CONCEAL
				ship_filter |= is_filter_requested(12) << SHIP_COMBAT_PARAM_FILTER.CONSUMABLE
				ship_filter |= is_filter_requested(13) << SHIP_COMBAT_PARAM_FILTER.UPGRADES
				ship_filter |= is_filter_requested(14) << SHIP_COMBAT_PARAM_FILTER.ARMOR
				ship_filter |= is_filter_requested(15) << SHIP_COMBAT_PARAM_FILTER.SONAR

			def is_filtered(x):
				return (ship_filter >> x) & 1 == 1

			aircraft_modules = {
				'fighter': "Fighters",
				'torpedo_bomber': "Torpedo Bombers",
				'dive_bomber': "Bombers",
				'skip_bomber': "Skip Bombers"
			}
			aircraft_module_filtered = [
				is_filtered(SHIP_COMBAT_PARAM_FILTER.ROCKETS),
				is_filtered(SHIP_COMBAT_PARAM_FILTER.TORP_BOMBER),
				is_filtered(SHIP_COMBAT_PARAM_FILTER.BOMBER),
				is_filtered(SHIP_COMBAT_PARAM_FILTER.BOMBER),
			]

			# do guns analysis
			if modules['artillery']:
				if database_client is not None:
					query_result = list(database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['artillery']}
					}).sort("name", 1))

					fire_control_range = list(database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['fire_control']}
					}).sort("profile.fire_control.distance", 1))
				# fire_control_range = sorted([fc['profile']['fire_control']['distance'] for fc in fire_control_range])
				else:
					query_result = [module_list[str(m)] for m in sorted(modules['artillery'], key=lambda x: module_list[str(x)]['name'])]
					fire_control_range = sorted(modules['fire_control'], key=lambda x: module_list[str(x)]['profile']['fire_control']['distance'])

				fig, ax = plt.subplots(1, figsize=(8, 3))
				ax.set_facecolor('black')
				plt.xlabel("Distance (m)")
				plt.ylabel("Height (m)")
				plt.title(f"{name}'s Main Battery Trajectory")
				plt.grid()

				for index, module in enumerate(query_result):
					m = ""

					guns = module['profile']['artillery']
					turret_data = module['profile']['artillery']['turrets']
					for turret_name in turret_data:
						turret = turret_data[turret_name]
						m += f"**{turret_name}**\n"
						m += f"**Salvo**: {to_plural('shells', turret['count'] * turret['numBarrels'])}\n"
						m += "\n"

					for ammo_type in guns['max_damage']:
						if guns['max_damage'][ammo_type] > 0:
							shell = build_trajectory(module, ammo_type)
							impact_data = shell.getImpact()
							traj_dist, traj_height, _ = get_trajectory_at_range(shell, guns['range'])
							# time_to_impact = get_impact_time_at_range(impact_data, guns['range'])
							time_to_impact = get_impact_time_at_max_range(impact_data, module)

							m += f"__**{ammo_type.upper() if ammo_type != 'cs' else 'AP'}**__\n"
							m += f"**Velocity**: {guns['speed'][ammo_type]:0.0f} m/s\n"
							m += f"**Krupp**: {guns['krupp'][ammo_type]:0.0f}\n"
							m += f"**Mass**: {guns['mass'][ammo_type]:0.0f} kg\n"
							m += f"**Drag**: {guns['drag'][ammo_type]:0.0f}\n"
							m += f"**Fuse Time**: {guns['fuse_time'][ammo_type]}s\n"
							m += f"**Ricochet**: {guns['ricochet'][ammo_type]}{DEGREE_SYMBOL}-{guns['ricochet_always'][ammo_type]}{DEGREE_SYMBOL}\n"
							m += f"**Dispersion @ {guns['range']/1000:0.1f} km**: {guns['dispersion_h'][str(int(guns['range']))]}m x {guns['dispersion_v'][str(int(guns['range']))]}m\n"
							m += f"**Time to impact @ {guns['range']/1000:0.1f} km**: {time_to_impact:0.1f}s\n"
							m += "\n"

							plt.plot(
								traj_dist,
								traj_height,
								color=SHELL_COLOR[ammo_type],
								label=f"{module['name']} {ammo_type.upper()}",
								linestyle=LINE_STYLES[index]
							)

					embed.add_field(name="__**Artillery**__", value=m, inline=False)
					plt.legend()
				# create hash
				h = sha256(f'{name}'.encode()).hexdigest()

				filename = f'./tmp/analysis_{h}.png'
				plt.savefig(filename)

				image_file = File(filename, filename=f"analysis_{h}.png")
				embed.set_image(url=f'attachment://analysis_{h}.png')

			footer_message = "Ballistics Tools are provided by jcw780: https://github.com/jcw780/wows_shell"

			if is_test_ship:
				footer_message += f"*Test ship is subject to change before her release\n"
			embed.set_footer(text=footer_message)
			await interaction.response.send_message(embed=embed, file=image_file)
		except Exception as e:
			logger.info(f"Exception {type(e)} {e}")
			traceback.print_exc()
			# error, ship name not understood
			if type(e) == NoShipFound:
				# ship with specified name is not found, user might mistype ship name?
				closest_match = find_close_match_item(ship_name.lower(), "ship_list")
				embed = Embed(title=f"Ship {ship_name} is not understood.\n", description="")
				if closest_match:
					closest_match_string = closest_match[0].title()
					closest_match_string = f'\nDid you mean **{closest_match_string}**?'

					embed.description = closest_match_string
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expire in 10 seconds")
					msg = await interaction.channel.send(embed=embed)
					await correct_user_misspell(self.bot, interaction, Analyze, "analyze", closest_match[0], param_filter)
					await msg.delete()
				else:
					await interaction.response.send_message(embed=embed)

			else:
				# we dun goofed
				await interaction.response.send_message(f"An internal error has occured.")
				traceback.print_exc()