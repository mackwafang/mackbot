import os.path

import discord, re, traceback
import numpy as np

from numpy.random import normal, seed
from typing import Optional
from hashlib import sha256

from discord import app_commands, Embed, File
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.patches import Ellipse

from mackbot.constants import SHIP_TYPES, ROMAN_NUMERAL, DEGREE_SYMBOL, nation_dictionary, SUPERSCRIPT_CHAR, SIGMA_SYMBOL
from mackbot.exceptions import *
from mackbot.ballistics.ballistics import Shell, calc_ballistic, calc_dispersion, within_dispersion, total_distance_traveled, TIMESCALE
from mackbot.utilities.discord.formatting import number_separator
from mackbot.utilities.discord.items_autocomplete import auto_complete_ship_name
from mackbot.utilities.discord.views import ConfirmCorrectionView
from mackbot.utilities.logger import logger
from mackbot.utilities.game_data.warships_data import database_client, module_list
from mackbot.utilities.game_data.game_data_finder import get_ship_data
from mackbot.utilities.correct_user_mispell import correct_user_misspell
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.to_plural import to_plural
from mackbot.utilities.game_data.warships_data import BALLISTIC_DATA

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
	'ap': 'white',
	'he': 'yellow',
	'sap': 'orange',
	'cs': 'orange'
}

DISP_MARKERS = (
	'x',
	'o',
	'd',
)

LINE_STYLES = (
	'solid',
	'dotted',
	'dashed',
	'dashdot'
)

class Analyze(commands.GroupCog):
	def __init__(self, bot):
		self.bot = bot
	@app_commands.command(name='artillery', description='Get combat parameters of a warship')
	@app_commands.describe(
		ship_name="Ship name",
		gun_range="Desired gun range in kilometers",
	)
	@app_commands.autocomplete(
		ship_name=auto_complete_ship_name,
	)
	async def artillery(self, interaction: discord.Interaction, ship_name: str, gun_range: Optional[float]=-1.0):

		if not interaction.response.is_done():
			await interaction.response.send_message("Acknowledged", ephemeral=True, delete_after=1)

		try:
			ship_data = get_ship_data(ship_name)
			if ship_data is None:
				raise NoShipFound

			name = ship_data['name']
			nation = ship_data['nation']
			images = ship_data['images']
			ship_type = ship_data['type']
			tier = ship_data['tier']
			modules = ship_data['modules']
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
			embed = Embed(description=f"## {ship_type} {name} {test_ship_status_string}")
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

			# create hash
			h = sha256(f'{name}_{gun_range}'.encode()).hexdigest()
			filename = f'./tmp/analysis_{h}.png'
			image_cached = os.path.exists(filename)

			fig, (ax1, ax2) = plt.subplots(2, figsize=(8, 6))
			ax1.set_facecolor('black')
			ax1.set_xlabel("Distance (m)")
			ax1.set_ylabel("Height (m)")
			ax1.grid()

			ax2.set_facecolor('black')
			ax2.set_xlabel("Horizontal Spread (m)")
			ax2.set_ylabel("Vertical Spread (m)")
			ax2.grid()

			for index, module in enumerate(query_result):
				m = ""

				guns = module['profile']['artillery']
				turret_data = module['profile']['artillery']['turrets']
				total_salvo_count = 0
				fc_bonus = sorted([fc['profile']['fire_control']['max_range_coef'] for fc in fire_control_range])[-1]
				max_gun_range = guns['range'] * fc_bonus
				gun_range = guns['range'] if gun_range == -1 else gun_range * 1000
				dispersion_h, dispersion_v = calc_dispersion(module, gun_range)

				for turret_name in turret_data:
					turret = turret_data[turret_name]
					total_salvo_count += turret['count'] * turret['numBarrels']
					m += f"**{turret_name}**\n"

				m += f"**Salvo**: {to_plural('shell', total_salvo_count)}\n"
				m += f"**Precision**: {guns['sigma']}{SIGMA_SYMBOL}\n"
				m += f"**Dispersion @ {gun_range / 1000:0.1f} km**: {dispersion_h:0.0f}m x {dispersion_v:0.0f}m\n"
				m += "\n"

				for ammo_type in guns['max_damage']:
					if guns['max_damage'][ammo_type] > 0:
						# shell = Shell(module)
						# trajectory_data = calc_ballistic(shell, max_gun_range, ammo_type)

						# uses cached data
						trajectory_data = BALLISTIC_DATA[str(module['module_id'])][ammo_type]['ballistic']
						gun_angle, trajectory_data_at_range = trajectory_data.get_trajectory_at_range(gun_range)

						traj_dist = trajectory_data_at_range.coordinates[:, 0]
						traj_height = trajectory_data_at_range.coordinates[:, 1]
						time_to_impact = trajectory_data_at_range.flight_time
						penetration_at_range = trajectory_data_at_range.penetration

						m += f"__**{ammo_type.upper() if ammo_type != 'cs' else 'AP'} ({guns['ammo_name'][ammo_type]})**__\n"
						m += f"**Velocity**: {guns['speed'][ammo_type]:0.0f} m/s\n"
						m += f"**Krupp**: {guns['krupp'][ammo_type]:0.0f}\n"
						m += f"**Mass**: {guns['mass'][ammo_type]:0.0f} kg\n"
						m += f"**Drag**: {guns['drag'][ammo_type]}\n"
						if ammo_type != 'he':
							m += f"**Fuse Time**: {guns['fuse_time'][ammo_type]}s\n"
							m += f"**Ricochet**: {guns['ricochet'][ammo_type]}{DEGREE_SYMBOL}-{guns['ricochet_always'][ammo_type]}{DEGREE_SYMBOL}\n"
							m += f"**Approx. Penetration @ {gun_range / 1000:0.1f} km{SUPERSCRIPT_CHAR[2]}**: {penetration_at_range:0.0f}mm\n"
						else:
							m += f"**Penetration @ {gun_range / 1000:0.1f} km**:{guns['pen']['he']:0.0f}mm\n"
							m += f"**Prob. for Fires{SUPERSCRIPT_CHAR[1]}**: {', '.join('**{} :fire:** ({:0.1%})'.format(i, (guns['burn_probability'] / 100) ** i) for i in range(1, 5))}\n"
						m += f"**Time to impact @ {gun_range/1000:0.1f} km**: {time_to_impact:0.1f}s\n"
						m += f"**Total Distance Traveled**: {total_distance_traveled(trajectory_data_at_range.coordinates):0.1f} km\n"
						m += "\n"

						if not image_cached:
							plt.tight_layout()
							ax1.plot(
								traj_dist,
								traj_height,
								color=SHELL_COLOR[ammo_type],
								label=f"{module['name']} {ammo_type.upper()}",
								linestyle=LINE_STYLES[index],
								linewidth=2,
							)

							# get shell landing point distributions
							ax1.set_title(f"{name}'s Main Battery Trajectory @ {gun_range/1000:0.1f} km")
							ax2.set_title(f"{name}'s Main Battery Dispersion @ {gun_range/1000:0.1f} km{SUPERSCRIPT_CHAR[3]}")

				if not image_cached:
					# this looks gross
					dispersion = [[], []]
					seed(0)
					for c in range(total_salvo_count * 10):
						x, y = np.inf, np.inf
						while not within_dispersion((x, y), (dispersion_h / 2, dispersion_v / 2)):
							x = normal(0, 1/guns['sigma']) * dispersion_h / 2
							y = normal(0, 1/guns['sigma']) * dispersion_v / 2

						dispersion[0].append(x)
						dispersion[1].append(y)

					ellipse = Ellipse(
						xy=(0,0),
						width=dispersion_h,
						height=dispersion_v,
						angle=0,
						edgecolor='white',
						facecolor='none'
					)
					ax2.add_artist(ellipse)
					ax2.scatter(
						dispersion[0],
						dispersion[1],
						marker=DISP_MARKERS[index],
						color='white',
					)

					# ax1.set_ylim(top=4500)
					# ax2.set_xlim(left=-dispersion_h / 2, right=dispersion_h / 2)
					# ax2.set_ylim(top=-dispersion_v / 2, bottom=dispersion_v / 2)
					ax2.set_xlim(left=-300, right=300)
					ax2.set_ylim(top=-200, bottom=200)
					m += '-' * 15
					m += "\n"

					ax1.legend()
					# ax2.legend()
				embed.add_field(name="__**Artillery**__", value=m, inline=False)

			if not image_cached:
				plt.savefig(filename)

			image_file = File(filename, filename=f"analysis_{h}.png")
			embed.set_image(url=f'attachment://analysis_{h}.png')

			footer_message = "- Ballistics Formulas are from WoWs-ShipBuilder\n" \
			                 f"{SUPERSCRIPT_CHAR[1]} Assuming a shell hit a different location\n" \
			                 f"{SUPERSCRIPT_CHAR[2]} Penetration values may not be very accurate\n" \
			                 f"{SUPERSCRIPT_CHAR[3]} From firing 10 salvos\n" \

			if is_test_ship:
				footer_message += f"*Test ship is subject to change before her release\n"
			embed.set_footer(text=footer_message)
			await interaction.followup.send(embed=embed, file=image_file)
		except Exception as e:
			logger.info(f"Exception {type(e)} {e}")
			traceback.print_exc()
			# error, ship name not understood
			if type(e) == NoShipFound:
				# ship with specified name is not found, user might mistype ship name?
				closest_match = find_close_match_item(ship_name.lower(), "ship_list")
				embed = Embed(title=f"Ship {ship_name} is not understood.\n", description="")
				if closest_match:
					closest_match_ship_name = closest_match[0].title()

					confirm_view = ConfirmCorrectionView(
						closest_match,
					)

					new_line_prefix = "\n-# - "
					embed.description = f'\nDid you mean **{closest_match_ship_name}**?\n-# Other possible matches are: {new_line_prefix}{new_line_prefix.join(i.title() for i in closest_match[1:])}'
					embed.set_footer(text="Response expire in 10 seconds")
					msg = await interaction.channel.send(
						embed=embed,
						view=confirm_view,
						delete_after=10
					)
					await confirm_view.wait()

					if confirm_view.value:
						await correct_user_misspell(self.bot, interaction, Analyze, "artillery", confirm_view.value, gun_range)
					else:
						await msg.delete()

				else:
					await interaction.channel.send(
						embed=embed
					)
			else:
				# we dun goofed
				await interaction.response.send_message(f"An internal error has occured.")
				traceback.print_exc()