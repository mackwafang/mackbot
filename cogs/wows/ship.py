import re, traceback
from typing import Optional

import discord
from discord import app_commands, Embed
from discord.ext import commands

from mackbot.constants import ship_types, ROMAN_NUMERAL, nation_dictionary, ICONS_EMOJI, DEGREE_SYMBOL, SIGMA_SYMBOL, MM_WITH_CV_TIER, ARMOR_ID_TO_STRING, AMMO_TYPE_STRING
from mackbot.enums import COMMAND_INPUT_TYPE
from mackbot.exceptions import *
from mackbot.utilities.logger import logger
from mackbot.utilities.regex import ship_param_filter_regex
from mackbot.utilities.get_aa_rating_descriptor import get_aa_rating_descriptor
from mackbot.utilities.game_data.warships_data import database_client, module_list, upgrade_list, ship_list_simple
from mackbot.utilities.game_data.game_data_finder import get_ship_data, get_consumable_data
from mackbot.utilities.correct_user_mispell import correct_user_misspell
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.to_plural import to_plural
from mackbot.utilities.discord.formatting import number_separator
from mackbot.utilities.discord.items_autocomplete import auto_complete_ship_name

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
	ARMOR = auto()
	SONAR = auto()

class Ship(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name='ship', description='Get combat parameters of a warship')
	@app_commands.describe(
		ship_name="Ship name",
		parameters="Ship parameters for detailed report",
	)
	@app_commands.autocomplete(ship_name=auto_complete_ship_name)
	async def ship(self, interaction: discord.Interaction, ship_name: str, parameters: Optional[str]=""):
		"""
			Outputs an embeded message to the channel (or DM) that contains information about a queried warship

			Discord usage:
				mackbot ship [ship_name] [-p/--parameters parameters]
					ship_name 		- name of requested warship
					-p/--parameters - Optional. Filters only specific warship parameters
										Parameters may include, but not limited to: guns, secondary, torpedoes, hull
		"""
		param_filter = parameters

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
			next_ships = list(ship_data['next_ships'].keys())
			prev_ship = ship_data['prev_ship'] if 'prev_ship' in ship_data else None
			price_gold = ship_data['price_gold']
			price_credit = ship_data['price_credit']
			price_special = ship_data['price_special']
			price_special_type = ship_data['price_special_type']
			price_xp = ship_data['price_xp']
			ship_type = ship_types[ship_type]

			logger.info(f"Ship {name} ({ship_data['ship_id']}) found")
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

			tier_string = ROMAN_NUMERAL[tier - 1]
			if tier < 11:
				tier_string = tier_string.upper()
			embed.description += f'**Tier {tier_string} {"Premium " if is_prem else ""}{nation_dictionary[nation]} {ship_type}**\n'
			if prev_ship is not None:
				prev_ship_data = ship_list_simple[prev_ship]
				embed.description += f"\nRequires **{ICONS_EMOJI[prev_ship_data['type']]} {ROMAN_NUMERAL[prev_ship_data['tier'] - 1]} {prev_ship_data['name']}**"

			if price_credit > 0 and price_xp > 0:
				embed.description += f'\n{number_separator(price_xp)} XP and {number_separator(price_credit)} Credits'
			if price_gold > 0 and is_prem:
				embed.description += f'\n{number_separator(price_gold)} Doubloons'
			if price_special_type:
				price_special_type_string = {
						'coal': "Units of Coal",
						'paragon_xp': "Research Bureau Points",
						'steel': "Units of Steel",
				}[price_special_type]
				embed.description += f'\n{number_separator(price_special)} {price_special_type_string}'

			if next_ships:
				embed.description += "\n\nSuccessor: "
				for _next_ship in next_ships:
					next_ship_data = ship_list_simple[_next_ship]
					embed.description += f"**{ICONS_EMOJI[next_ship_data['type']]} {ROMAN_NUMERAL[next_ship_data['tier'] - 1]} {next_ship_data['name']}** or "
				embed.description = embed.description[:-4]

			if images['small'] is not None:
				embed.set_thumbnail(url=images['small'])

			# defines ship params filtering

			ship_filter = 0b111111111111111  # assuming no filter is provided, display all
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

				if True:
					ship_filter_debug_string = "filter: "
					for i in SHIP_COMBAT_PARAM_FILTER:
						ship_filter_debug_string += f"{i.name}: {(ship_filter >> i.value) & 1}, "
					logger.info(ship_filter_debug_string)

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

			# General hull info
			if len(modules['hull']) and is_filtered(SHIP_COMBAT_PARAM_FILTER.HULL):
				m = ""
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['hull']}
					}).sort("name", 1)
					query_result = list(query_result)
				else:
					query_result = [module_list[str(m)] for m in sorted(modules['hull'], key=lambda x: module_list[str(x)]['name'])]

				m = ""
				for module in query_result:
					hull = module['profile']['hull']
					m += f"**{module['name']}:** **{number_separator(hull['health'], '.0f')} HP**\n"
					# if hull['artillery_barrels'] > 0:
					# 	m += f"{hull['artillery_barrels']} Main Turret{'s' if hull['artillery_barrels'] > 1 else ''}\n"
					# if hull['torpedoes_barrels'] > 0:
					# 	m += f"{hull['torpedoes_barrels']} Torpedoes Launcher{'s' if hull['torpedoes_barrels'] > 1 else ''}\n"
					# if hull['atba_barrels'] > 0:
					# 	m += f"{hull['atba_barrels']} Secondary Turret{'s' if hull['atba_barrels'] > 1 else ''}\n"
					# if hull['anti_aircraft_barrels'] > 0:
					# 	m += f"{hull['anti_aircraft_barrels']} AA Gun{'s' if hull['anti_aircraft_barrels'] > 1 else ''}\n"
					# if hull['planes_amount'] is not None and ship_type == "Aircraft Carrier":
					# 	m += f"{hull['planes_amount']} Aircraft\n"

					if ship_type == 'Submarine':
						m += f"{hull['battery']['capacity']} battery unit\n"
					if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.HULL:
						if ship_type == 'Submarine':
							m += f"+{hull['battery']['regenRate']} battery unit per second while surfaced\n"
							m += f"{hull['oilLeakDuration']}s oil leak duration\n\n"
						m += f"{hull['rudderTime']}s rudder shift time\n"
						m += f"{hull['turnRadius']}m turn radius\n\n"
					m += '\n'
				embed.add_field(name="__**Hull**__", value=m, inline=True)

				# air support info
				m = ''
				for module in query_result:
					if 'airSupport' in module['profile']:
						airsup_info = module['profile']['airSupport']
						m += f"**{module['name']}**\n"
						airsup_reload_m = int(airsup_info['reloadTime'] // 60)
						airsup_reload_s = int(airsup_info['reloadTime'] % 60)

						m += f"**Has {airsup_info['chargesNum']} charge(s)**\n"
						m += f"**Reload**: {str(airsup_reload_m) + 'm' if airsup_reload_m > 0 else ''} {str(airsup_reload_s) + 's' if airsup_reload_s > 0 else ''}\n"
						m += f"**Range**: {airsup_info['range']/1000:1.1f} km\n"

						if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.HULL:
							# detailed air support filter
							m += f"**Aircraft**: {airsup_info['payload']} bombs\n"
							if nation == 'netherlands':
								m += f"**Squadron**: {airsup_info['squad_size']} aircraft\n"
								m += f"**HE Bomb**: :boom:{number_separator(airsup_info['max_damage'])} (:fire:{airsup_info['burn_probability']}%, {ICONS_EMOJI['penetration']} {airsup_info['bomb_pen']}mm)\n"
							else:
								m += f"**Squadron**: {airsup_info['squad_size']} aircraft\n"
								m += f"**Depth Charge**: :boom:{number_separator(airsup_info['max_damage'])}\n"
						m += '\n'
				if m:
					embed.add_field(name="__**Air Support**__", value=m, inline=True)

				m = ''
				for module in query_result:
					if 'asw' in module['profile']:
						asw_info = module['profile']['asw']
						m += f"**{module['name']}**\n"
						asw_reload_m = int(asw_info['reloadTime'] // 60)
						asw_reload_s = int(asw_info['reloadTime'] % 60)

						m += f"**Has {asw_info['chargesNum']} charge(s)**\n"
						m += f"**Reload**: {str(asw_reload_m) + 'm' if asw_reload_m > 0 else ''} {str(asw_reload_s) + 's' if asw_reload_s > 0 else ''}\n"

						if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.HULL:
							# detailed air support filter
							m += f"**Depth charges per salvo**: {asw_info['payload']} bombs\n"
							m += f"**Depth charge**: :boom: {number_separator(asw_info['max_damage'])}\n"

						m += '\n'
				if m:
					embed.add_field(name="__**ASW**__", value=m, inline=True)

			# guns info
			if len(modules['artillery']) and is_filtered(SHIP_COMBAT_PARAM_FILTER.GUNS):
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['artillery']}
					}).sort("name", 1)

					fire_control_range = list(database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['fire_control']}
					}).sort("profile.fire_control.distance", 1))
					# fire_control_range = sorted([fc['profile']['fire_control']['distance'] for fc in fire_control_range])
				else:
					query_result = [module_list[str(m)] for m in sorted(modules['artillery'], key=lambda x: module_list[str(x)]['name'])]
					fire_control_range = sorted(modules['fire_control'], key=lambda x: module_list[str(x)]['profile']['fire_control']['distance'])

				for module in query_result:
					m = ""
					guns = module['profile']['artillery']
					turret_data = module['profile']['artillery']['turrets']
					for turret_name in turret_data:
						turret = turret_data[turret_name]
						m += f"**{turret['count']} x {turret_name} ({to_plural('barrel', turret['numBarrels'])})**\n"
					gun_ranges_with_fc = sorted([guns['range'] * fc['profile']['fire_control']['max_range_coef'] / 1000 for fc in fire_control_range])
					gun_ranges_with_fc = [f"{i:0.1f}" for i in gun_ranges_with_fc]

					m += f"**Rotation: ** {guns['transverse_speed']}{DEGREE_SYMBOL}/s ({180/guns['transverse_speed']:0.1f}s for 180{DEGREE_SYMBOL} turn)\n"
					m += f"**Range: ** {' km - '.join(gun_ranges_with_fc)} km\n"
					m += f"**Reload:** {guns['shotDelay']:0.1f}s\n"
					if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.GUNS:
						m += f"**Precision:** {guns['sigma']:1.2f}{SIGMA_SYMBOL}\n"
						m += '-------------------\n'
						m += "__**Dispersion:**__\n"
						ranges = tuple(guns['dispersion_h'].keys())
						h_dispersions = tuple(guns['dispersion_h'].values())
						v_dispersions = tuple(guns['dispersion_v'].values())
						for r, h, v in zip(ranges, h_dispersions, v_dispersions):
							m += f"**{float(r)/1000:1.1f} km :** {h:1.0f}m x {v:1.0f}m\n"
					else:
						m += f"**Dispersion @ Max Range:** {guns['dispersion_h'][str(int(guns['range']))]:1.0f}m x {guns['dispersion_v'][str(int(guns['range']))]:1.0f}m\n"
					m += '-------------------\n'

					for ammo_type in ['he', 'ap', 'cs']:
						if guns['max_damage'][ammo_type]:
							ammo_type_string = AMMO_TYPE_STRING[ammo_type]
							m += f"__**{ammo_type_string}: {guns['ammo_name'][ammo_type]}**__\n"
							m += f"**{ammo_type_string} Shell:** :boom:{number_separator(guns['max_damage'][ammo_type])}"
							if ammo_type == 'he':
								m += f" ("
								m += f"{ICONS_EMOJI['penetration']} {guns['pen'][ammo_type]} mm"
								if ammo_type == 'he':
									m += f", :fire: {guns['burn_probability']} %"
								m += ")"
							else:
								m += f" (Ricochet at {guns['ricochet'][ammo_type]}{DEGREE_SYMBOL}~{guns['ricochet_always'][ammo_type]}{DEGREE_SYMBOL})"

							if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.GUNS:
								m += f"\n**DPM:** {number_separator(guns['gun_dpm'][ammo_type])} DPM\n"
								m += f"**Shell Velocity:** {guns['speed'][ammo_type]:1.0f} m/s\n"
								m += '-------------------'
							m += "\n"

					m += '\n'
					embed.add_field(name=f"{ICONS_EMOJI['gun']} __**Main Battery**__", value=m, inline=False)

			# secondary armaments
			if len(modules['hull']) is not None and is_filtered(SHIP_COMBAT_PARAM_FILTER.ATBAS):
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['hull']}
					}).sort("name", 1)
				else:
					query_result = [module_list[str(i)] for i in modules["hull"]]

				for hull in query_result:
					m = ""
					if 'atba' in hull['profile']:
						atba = hull['profile']['atba']
						hull_name = hull['name']

						gun_dpm = int(sum([atba[t]['gun_dpm'] for t in atba if type(atba[t]) == dict]))
						gun_count = int(sum([atba[t]['count'] for t in atba if type(atba[t]) == dict]))

						m += f"**{hull_name}**\n"
						m += f"**Range:** {atba['range'] / 1000:1.1f} km\n"
						m += f"**{gun_count}** turret{'s' if gun_count > 1 else ''}\n"
						m += f'**DPM:** {number_separator(gun_dpm)}\n'

						if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.ATBAS:
							m += '\n'
							for t in atba:
								turret = atba[t]
								if type(atba[t]) == dict:
									# detail secondary
									m += f"**{turret['count']} x {atba[t]['name']} ({turret['numBarrels']:1.0f} barrel{'s' if turret['numBarrels'] > 1 else ''})**\n"
									m += f"**{'SAP' if turret['ammoType'] == 'CS' else turret['ammoType']}**: {int(turret['max_damage'])}"
									m += ' ('
									if turret['burn_probability'] > 0:
										m += f":fire: {turret['burn_probability'] * 100}%, "
									m += f"{ICONS_EMOJI['penetration']} {turret['pen']}mm"
									m += ')\n'
									m += f"**Reload**: {turret['shotDelay']}s\n"
						# if len(modules['hull']) > 1:
						# 	m += '-------------------\n'

						embed.add_field(name=f"{ICONS_EMOJI['gun']} __**Secondary Battery**__", value=m, inline=True)

			# anti air
			if len(modules['hull']) and is_filtered(SHIP_COMBAT_PARAM_FILTER.AA):
				m = ""
				if database_client is not None:
					query_result = list(database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['hull']}
					}).sort("name", 1))
				else:
					query_result = [module_list[str(i)] for i in modules["hull"]]

				if query_result:
					if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.AA:
						# detailed aa
						for hull in query_result:
							if "anti_air" in hull['profile']:
								aa = hull['profile']['anti_air']
								m += f"**{name} ({aa['hull']}) Hull**\n"

								cv_mm_tier = MM_WITH_CV_TIER[tier - 1]
								if tier >= 10 and ship_type == 'Aircraft Carrier':
									cv_mm_tier = [10]
								elif tier == 8 and ship_type == 'Aircraft Carrier':
									cv_mm_tier = [6, 8]

								for tier_range in cv_mm_tier:
									if 0 < tier_range <= 10:
										rating_descriptor = get_aa_rating_descriptor(aa['rating'][tier_range - 1])
										m += f"**AA Rating vs. T{tier_range}:** {int(aa['rating'][tier_range - 1])} ({rating_descriptor})\n"
										if 'dfaa_stat' in aa:
											rating_descriptor_with_dfaa = get_aa_rating_descriptor(aa['rating_with_dfaa'][tier_range - 1])
											m += f"**AA Rating vs. T{tier_range} with DFAA:** {int(aa['rating_with_dfaa'][tier_range - 1])} ({rating_descriptor_with_dfaa})\n"

								m += f"**Range:** {aa['max_range'] / 1000:0.1f} km"
								# provide more AA detail
								flak = aa['flak']
								near = aa['near']
								medium = aa['medium']
								far = aa['far']
								if flak['damage'] > 0:
									m += f" (Flak from {flak['min_range'] / 1000: 0.1f} km)\n"
									m += f"**Flak:** {flak['damage']}:boom:, {to_plural('burst', int(flak['count']))}, {flak['hitChance']:2.0%}"
								m += "\n"

								if near['damage'] > 0:
									m += f"**Short Range:** {near['damage']:0.1f} (up to {near['range'] / 1000:0.1f} km, {int(near['hitChance'] * 100)}%)\n"
								if medium['damage'] > 0:
									m += f"**Mid Range:** {medium['damage']:0.1f} (up to {medium['range'] / 1000:0.1f} km, {int(medium['hitChance'] * 100)}%)\n"
								if far['damage'] > 0:
									m += f"**Long Range:** {far['damage']:0.1f} (up to {aa['max_range'] / 1000:0.1f} km, {int(far['hitChance'] * 100)}%)\n"
								m += '\n'
					else:
						# compact detail
						if "anti_air" in query_result[0]['profile']:
							aa = query_result[0]['profile']['anti_air']
							average_rating = sum([hull['profile']['anti_air']['rating'][tier - 1] for hull in query_result]) / len(modules['hull'])

							rating_descriptor = get_aa_rating_descriptor(aa['rating'][tier - 1])
							m += f"**Average AA Rating:** {int(average_rating)} ({rating_descriptor})\n"
							m += f"**Range:** {aa['max_range'] / 1000:0.1f} km\n"
					if "anti_air" in query_result[0]['profile']:
						embed.add_field(name=f"{ICONS_EMOJI['aa']} __**Anti-Air**__", value=m, inline=False)

			# torpedoes
			if len(modules['torpedoes']) and is_filtered(SHIP_COMBAT_PARAM_FILTER.TORPS):
				m = ""
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['torpedoes']}
					}).sort("name", 1)
				else:
					query_result = [module_list[str(m)] for m in sorted(modules['torpedoes'], key=lambda x: module_list[str(x)]['name'])]

				for module in query_result:
					torps = module['profile']['torpedoes']
					projectile_name = module['name'].replace(chr(10), ' ')
					turret_name = list(torps['turrets'].keys())[0]
					m += f"**{torps['turrets'][turret_name]['count']} x {turret_name} ({torps['range']:0.1f} km, {to_plural('barrel', torps['numBarrels'])})"
					if torps['is_deep_water']:
						m += " [DW]"
					m += '**\n'
					if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.TORPS:
						reload_minute = int(torps['shotDelay'] // 60)
						reload_second = int(torps['shotDelay'] % 60)
						m += f"**Torpedo:** {projectile_name}\n"
						m += f"**Reload:** {'' if reload_minute == 0 else str(reload_minute) + 'm'} {reload_second}s\n"
						m += f"**Damage:** {number_separator(torps['max_damage'])}\n"
						m += f"**Speed:** {torps['torpedo_speed']} kts.\n"
						m += f"**Spotting Range:** {torps['spotting_range']} km\n"
						m += f"**Reaction Time:** {torps['spotting_range'] / (torps['torpedo_speed'] * 2.6) * 1000:1.1f}s\n"
						if ship_type == 'Submarine':
							m += f"**Loaders:** {', '.join(str(t) for t in torps['loaders']['0'])} bow, {', '.join(str(t) for t in torps['loaders']['1'])} aft\n"
							m += f"**Stop homing at:** {', '.join(f'{ICONS_EMOJI[t]}: {d[0]:1.0f}m/{d[1]:1.0f}m' for t, d in torps['shutoff_distance'].items() if t != 'default')}\n"
						m += '-------------------\n'
				embed.add_field(name=f"{ICONS_EMOJI['torp']} __**Torpedoes**__", value=m)

			# aircraft squadrons
			if any(aircraft_module_filtered):
				# one or more aircraft module is requested
				selected_modules = [list(aircraft_modules.keys())[i] for i, filtered in enumerate(aircraft_module_filtered) if filtered]
				detailed_filter = ship_filter in [2 ** SHIP_COMBAT_PARAM_FILTER.ROCKETS, 2 ** SHIP_COMBAT_PARAM_FILTER.TORP_BOMBER, 2 ** SHIP_COMBAT_PARAM_FILTER.BOMBER]

				for module_type in selected_modules:
					if len(modules[module_type]):
						if database_client is not None:
							query_result = database_client.mackbot_db.module_list.find({
								"module_id": {"$in": modules[module_type]}
							}).sort(f"squadron.profile.{module_type}.max_health", 1)
							query_result = [(document['module_id'], document) for document in query_result]
						else:
							query_result = [(i, list(module_list[str(i)].values())[0]['profile'][module_type]['max_health']) for i in modules[module_type]]

						m = ""
						for _, module in query_result:
							aircraft_module = module["squadron"]
							for squadron in aircraft_module:
								aircraft = squadron['profile'][module_type]
								n_attacks = squadron['squad_size'] // squadron['attack_size']
								m += f"**{squadron['name'].replace(chr(10), ' ')}**\n"
								aircraft_icon_emoji = None
								if module_type == 'fighter':
									aircraft_icon_emoji = ICONS_EMOJI['plane_rocket']
								if module_type == 'torpedo_bomber':
									aircraft_icon_emoji = ICONS_EMOJI['plane_torp']
								if module_type == 'dive_bomber' or module_type == 'skip_bomber':
									aircraft_icon_emoji = ICONS_EMOJI['plane_bomb']

								if detailed_filter:
									m = ""
									m += f"**Hangar:** {squadron['hangarSettings']['startValue']} aircraft (Restore {squadron['hangarSettings']['restoreAmount']} aircraft every {squadron['hangarSettings']['timeToRestore']:0.0f}s)\n"
									m += f"**Squadron:** {squadron['squad_size']} aircraft ({to_plural('flight', n_attacks)}), {number_separator(aircraft['max_health'] * squadron['squad_size'], '.0f')} HP, {aircraft['cruise_speed']} kts. (up to {aircraft['max_speed']} kts.)\n"
									m += f"**Attacking Flight:** {squadron['attack_size']} aircraft\n"
									m += f"**Payload:** {squadron['attack_size'] * aircraft['payload']} x {aircraft['payload_name']} ({aircraft['payload']} per aircraft)\n"
									if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.ROCKETS:
										m += f"**Firing Delay:** {aircraft['aiming_time']:0.1f}s\n"
										m += f"**{aircraft['rocket_type']} Rocket:** :boom:{number_separator(aircraft['max_damage'], '.0f')} " \
										     f"{'(:fire:' + str(aircraft['burn_probability']) + '%, ' + ICONS_EMOJI['penetration'] + ' ' + str(aircraft['rocket_pen']) + 'mm)' if aircraft['burn_probability'] > 0 else ''}\n"
									if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.TORP_BOMBER:
										m += f"**Torpedo:** :boom:{number_separator(aircraft['max_damage'], '.0f')}, {aircraft['torpedo_speed']} kts\n"
										m += f"**Arming Range:** {aircraft['arming_range']:0.1f}m\n"
									if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.BOMBER:
										m += f"**{aircraft['bomb_type']} Bomb:** :boom:{number_separator(aircraft['max_damage'], '.0f')} " \
										     f"{'(:fire:' + str(aircraft['burn_probability']) + '%, ' + ICONS_EMOJI['penetration'] + ' ' + str(aircraft['bomb_pen']) + 'mm)' if aircraft['burn_probability'] > 0 else ''}\n"
									m += f"**Attack Cooldown:** {squadron['attack_cooldown']:0.1f}s\n"

									squadron_consumables = squadron['consumables']
									for slot_index, slot in enumerate(squadron_consumables):
										for consumable_index, consumable_type in squadron_consumables[slot]['abils']:
											consumable_data = get_consumable_data(consumable_index.split("_")[0], consumable_type)
											consumable_type = consumable_data['consumableType']

											m += f"**Consumable {slot_index+1}:** {consumable_data['numConsumables']} x {consumable_data['name']} ("
											m += f"{consumable_data['workTime']:1.0f}s duration, "
											# if consumable_type == "healForsage":
											if consumable_type == "callFighters":
												m += f"{to_plural('fighter', consumable_data['fightersNum'])}, "
											if consumable_type == "regenerateHealth":
												m += f"+{consumable_data['regenerationRate']:1.0%} of max HP per second, "
											m += f"{consumable_data['reloadTime']:1.0f}s cooldown"
											m += ")\n"
									m += '\n'
									embed.add_field(name=f"__**{squadron['name'].replace(chr(10), ' ')}**__", value=m, inline=False)
						if not detailed_filter:
							embed.add_field(name=f"{aircraft_icon_emoji} __**{aircraft_modules[module_type]}**__", value=m, inline=True)

			# engine
			if len(modules['engine']) and is_filtered(SHIP_COMBAT_PARAM_FILTER.ENGINE):
				m = ""
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['engine']}
					}).sort("name", 1)
				else:
					query_result = sorted(modules['engine'], key=lambda x: module_list[str(x)]['name'])

				for module in query_result:
					engine = module['profile']['engine']
					m += f"**{module['name']}**: {engine['max_speed']} kts\n"
					m += '\n'
				embed.add_field(name="__**Engine**__", value=m, inline=False)

			# concealment
			if len(modules['hull']) is not None and is_filtered(SHIP_COMBAT_PARAM_FILTER.CONCEAL):
				m = ""
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['hull']}
					}).sort("name", 1)
				else:
					query_result = sorted(modules['hull'], key=lambda x: module_list[str(x)]['name'])

				for module in query_result:
					hull = module['profile']['hull']
					m += f"**{module['name']}**\n"
					m += f"**By Sea**: {hull['detect_distance_by_ship']:0.1f} km\n"
					m += f"**By Air**: {hull['detect_distance_by_plane']:0.1f} km\n"
					m += "\n"
				embed.add_field(name=f"{ICONS_EMOJI['concealment']} __**Concealment**__", value=m, inline=True)

			# upgrades
			if ship_filter == (1 << SHIP_COMBAT_PARAM_FILTER.UPGRADES):
				m = ""
				for slot in upgrades:
					m += f"**Slot {slot + 1}**\n"
					if len(upgrades[slot]) > 0:
						for u in upgrades[slot]:
							m += f"{upgrade_list[u]['name']}\n"
					m += "\n"

				embed.add_field(name="__**Upgrades**__", value=m, inline=True)

			# armor
			if ship_filter == (1 << SHIP_COMBAT_PARAM_FILTER.ARMOR): #is_filtered(SHIP_COMBAT_PARAM_FILTER.ARMOR):
				m = ""
				if database_client is not None:
					hull_armor_query_result = list(database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['hull']}
					}).sort("name", 1))
					gun_armor_query_result = list(database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['artillery']}
					}).sort("name", 1))
				else:
					logger.error("Cannot establish a connection to MongoDB")
					raise ConnectionError

				if hull_armor_query_result:
					for module in hull_armor_query_result:
						armor_data = module['profile']['hull']['armor']
						for armor_location, armor_location_data in ARMOR_ID_TO_STRING.items():
							m += f"__**{armor_location.title()}**__\n"
							for armor_id, armor_string in armor_location_data.items():
								if armor_id in armor_data: # only select armor values that are identified in ARMOR_ID_TO_STRING
									armor_value = armor_data[armor_id]
									m += f"{armor_string} ({armor_id}): {armor_value:1.0f}mm\n"
							m += "\n"
						embed.add_field(name=f"__**{module['name'].title()}'s Armor**__", value=m, inline=True)
						m = ""

			# consumables
			if len(consumables) > 0 and is_filtered(SHIP_COMBAT_PARAM_FILTER.CONSUMABLE):
				m = ""
				for consumable_slot in consumables:
					if len(consumables[consumable_slot]['abils']) > 0:
						m += f"__**Slot {consumables[consumable_slot]['slot'] + 1}:**__ "
						for c_index, c in enumerate(consumables[consumable_slot]['abils']):
							consumable_index, consumable_type = c
							consumable = get_consumable_data(consumable_index.split("_")[0], consumable_type)
							consumable_name = consumable['name']
							consumable_description = consumable['description']
							consumable_type = consumable["consumableType"]

							charges = 'Infinite' if consumable['numConsumables'] < 0 else consumable['numConsumables']
							action_time = consumable['workTime']
							cd_time = consumable['reloadTime']

							if ship_filter != (1 << SHIP_COMBAT_PARAM_FILTER.CONSUMABLE) and charges != 'Infinite':
								m += f"**{charges} x ** "
							if ship_filter != (1 << SHIP_COMBAT_PARAM_FILTER.CONSUMABLE):
								m += f"**{consumable_name}**"

							if ship_filter == (1 << SHIP_COMBAT_PARAM_FILTER.CONSUMABLE):  # shows detail of consumable
								m = f"\n{consumable_description}\n"
								m += "\n"
								consumable_detail = ""
								if consumable_type == 'airDefenseDisp':
									consumable_detail = f'Continuous AA damage: +{consumable["areaDamageMultiplier"] * 100:0.0f}%\nFlak damage: +{consumable["bubbleDamageMultiplier"] * 100:0.0f}%'
								if consumable_type == 'artilleryBoosters':
									consumable_detail = f'Reload Time: -{consumable["boostCoeff"]:2.0f}'
								if consumable_type == 'fighter':
									consumable_detail = f'{to_plural("fighter", consumable["fightersNum"])}, {consumable["distanceToKill"]/10:0.1f} km action radius'
								if consumable_type == 'regenCrew':
									consumable_detail = f'Repairs {consumable["regenerationHPSpeed"] * 100}% of max HP / sec.\n'
									if database_client is not None:
										query_result = database_client.mackbot_db.module_list.find({
											"module_id": {"$in": modules['hull']}
										}).sort("name", 1)
									else:
										query_result = sorted(modules['hull'], key=lambda x: module_list[str(x)]['name'])

									for module in query_result:
										hull = module['profile']['hull']
										consumable_detail += f"{module['name']} ({hull['health']} HP): {int(hull['health'] * consumable['regenerationHPSpeed'])} HP / sec., {int(hull['health'] * consumable['regenerationHPSpeed'] * consumable['workTime'])} HP per use\n"
									consumable_detail = consumable_detail[:-1]
								if consumable_type == 'rls':
									consumable_detail = f'Range: {round(consumable["distShip"] * 30) / 1000:0.1f} km'
								if consumable_type == 'scout':
									consumable_detail = f'Main Battery firing range: +{(consumable["artilleryDistCoeff"] - 1) * 100:0.0f}%'
								if consumable_type == 'smokeGenerator':
									consumable_detail = f'Smoke lasts {str(int(consumable["lifeTime"] // 60)) + "m" if consumable["lifeTime"] >= 60 else ""} {str(int(consumable["lifeTime"] % 60)) + "s" if consumable["lifeTime"] % 60 > 0 else ""}\nSmoke radius: {consumable["radius"] * 10} meters\nConceal user up to {consumable["speedLimit"]} knots while active.'
								if consumable_type == 'sonar':
									consumable_detail = f'Assured Ship Range: {round(consumable["distShip"] * 30) / 1000:0.1f}km\nAssured Torp. Range: {round(consumable["distTorpedo"] * 30) / 1000:0.1f} km'
								if consumable_type == 'speedBoosters':
									consumable_detail = f'Max Speed: +{consumable["boostCoeff"] * 100:0.0f}%'
								if consumable_type == 'torpedoReloader':
									consumable_detail = f'Torpedo Reload Time lowered to {consumable["torpedoReloadTime"]:1.0f}s'
								if consumable_type == 'hydrophone':
									consumable_detail = f'Reveal ships and terrain within {consumable["hydrophoneWaveRadius"] / 1000:0.1f}km every {consumable["hydrophoneUpdateFrequency"]}s'
								if consumable_type == 'submarineLocator':
									consumable_detail = f'On cooldown for {consumable["preparationTime"] // 60:0.0f}m {consumable["preparationTime"] % 60:0.0f}s after the battle starts\n'
									consumable_detail += f'Reveal submarines within {consumable["distShip"] * 30 / 1000:0.1f} km.'
								if consumable_type == "subsEnergyFreeze":
									consumable_detail = f""
								if consumable_type == "fastRudders":
									consumable_detail = f"Submarine plane shift: -{1 - consumable['buoyancyRudderTimeCoeff']:1.0%}\n"
									consumable_detail += f"Dive and ascend speed: +{consumable['maxBuoyancySpeedCoeff'] - 1:1.0%}"

								m += f"{charges} charge{'s' if charges != 1 else ''}, "
								m += f"{f'{action_time // 60:1.0f}m ' if action_time >= 60 else ''} {str(int(action_time % 60)) + 's' if action_time % 60 > 0 else ''} duration, "
								m += f"{f'{cd_time // 60:1.0f}m ' if cd_time >= 60 else ''} {str(int(cd_time % 60)) + 's' if cd_time % 60 > 0 else ''} cooldown.\n"
								if len(consumable_detail) > 0:
									m += consumable_detail
									m += '\n'
								embed.add_field(name=f"__**Slot {consumables[consumable_slot]['slot'] + 1}{'-'+str(c_index + 1) if len(consumables[consumable_slot]['abils']) > 1 else ''}: {consumable_name}**__", value=m, inline=False)
							else:
								if len(consumables[consumable_slot]['abils']) > 1 and c_index != len(consumables[consumable_slot]['abils']) - 1:
									m += ' or '
						m += '\n'
				if ship_filter != (1 << SHIP_COMBAT_PARAM_FILTER.CONSUMABLE):
					embed.add_field(name="__**Consumables**__", value=m, inline=False)

			# submarines pinger
			if ship_type == 'Submarine' and len(modules['sonar']) and is_filtered(SHIP_COMBAT_PARAM_FILTER.SONAR):
				m = ""
				if database_client is not None:
					query_result = database_client.mackbot_db.module_list.find({
						"module_id": {"$in": modules['sonar']}
					}).sort("name", 1)
				else:
					query_result = sorted(modules['sonar'], key=lambda x: module_list[str(x)]['name'])

				for module in query_result:
					pinger = module['profile']['sonar']
					m += f"__**{module['name']}**__\n"
					m += f"**Range**: {pinger['range']/1000:0.1f} km\n"
					m += f"**Duration**: {pinger['ping_effect_duration'][0]}s ({pinger['ping_effect_duration'][1]}s for 2)\n"
					if ship_filter == 2 ** SHIP_COMBAT_PARAM_FILTER.SONAR:
						m += f"**Width**: {pinger['ping_effect_width'][0]}m ({pinger['ping_effect_width'][1]}m for 2)\n"
					m += '\n'
				embed.add_field(name="__**Sonar**__", value=m, inline=False)

			footer_message = "Parameters does not take into account upgrades or commander skills\n"
			footer_message += f"For details specific parameters, use [/ship {ship_name} -p parameters]\n"
			footer_message += f"For {ship_name.title()} builds, use [/build {ship_name}]\n\n"
			footer_message += f"Tags: "
			tags = []
			for tag in ship_data['tags'].values():
				tags += [str(i) for i in tag]
			footer_message += ', '.join(tags)
			if is_test_ship:
				footer_message += f"\n* Test ship is subject to change before her release\n"
			embed.set_footer(text=footer_message)
			await interaction.response.send_message(embed=embed)
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
					await correct_user_misspell(self.bot, interaction, Ship, "ship", closest_match[0], param_filter)
					await msg.delete()
				else:
					await interaction.response.send_message(embed=embed)

			else:
				# we dun goofed
				await interaction.response.send_message(f"An internal error has occured.")
				traceback.print_exc()
