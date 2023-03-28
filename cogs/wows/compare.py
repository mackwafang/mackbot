import traceback, re, asyncio

from discord import app_commands, Embed, SelectOption
from discord.ext import commands
from itertools import zip_longest

from mackbot.utilities.discord.formatting import number_separator
from .bot_help import BotHelp
from mackbot.constants import ship_types, ROMAN_NUMERAL, nation_dictionary, ICONS_EMOJI, hull_classification_converter, DEGREE_SYMBOL, SIGMA_SYMBOL, EMPTY_LENGTH_CHAR
from mackbot.exceptions import *
from mackbot.utilities.logger import logger
from mackbot.utilities.game_data.game_data_finder import get_ship_data, get_module_data
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.get_aa_rating_descriptor import get_aa_rating_descriptor
from mackbot.utilities.discord.drop_down_menu import UserSelection, get_user_response_with_drop_down

class Compare(commands.Cog):
	def __init__(self, client):
		self.client = client

	@app_commands.command(name='compare', description='Compare combat parameters of two warships')
	@app_commands.describe(
		value="Two ships to compare. Add the word \"and\" between ship names",
	)
	async def compare(self, context: commands.Context, value: str):
		# check if *not* slash command,
		if context.clean_prefix != '/':
			args = ' '.join(context.message.content.split()[2:])
		else:
			args = value
		# args = ' '.join(args) # join arguments to split token
		# user_input_ships = args.replace("and", "&").split("&")
		compare_separator = ("and", "vs", "v")
		user_input_ships = re.sub(f"\\s{'|'.join(compare_separator)}\s", " & ", args, flags=re.I).split("&")
		if len(user_input_ships) != 2:
			await BotHelp.custom_help(BotHelp, context, "compare")
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
				embed = Embed(title=f"Ship {s} is not understood.\n", description="")
				if len(closest_match) > 0:
					embed.description += f'\nDid you mean **{closest_match_string}**?'
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expires in 10 seconds")
					await context.send(embed=embed)
					try:
						msg = await self.client.wait_for("message", timeout=10, check=user_correction_check)
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
		response_embed = Embed(title="Which parameter would you like to compare?", description="")
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
			embed = Embed(title=f"Comparing the {user_options[user_selection].lower()} of {ships_to_compare[0]['name']} and {ships_to_compare[1]['name']}")
			ship_module = [{}, {}]
			logger.info(f"returning comparison for {user_options[user_selection]}")
			m = "**Tier**\n"
			m += "**Type**\n"
			m += "**Nation**\n"
			embed.add_field(name="__Ship__", value=m)
			for i in range(2):
				m = f"{list(ROMAN_NUMERAL)[ships_to_compare[i]['tier'] - 1].upper() if ships_to_compare[i]['tier'] < 11 else ':star:'}\n"
				m += f"{ICONS_EMOJI[hull_classification_converter[ships_to_compare[i]['type']].lower()]}\n"
				m += f"{nation_dictionary[ships_to_compare[i]['nation']]}\n"
				embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m)

			if user_selection == 0:
				# main battery
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
						m += "**HE Detail**\n"
						m += "**AP Shell**\n"
						m += "**AP DPM**\n"
						m += "**AP Detail**\n"
						m += "**SAP Shell**\n"
						m += "**SAP DPM**\n"
						m += "**SAP Detail**\n"
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
									m += f"{number_separator(artillery['max_damage']['he'])}\n"
									m += f"{number_separator(artillery['gun_dpm']['he'])}\n"
									m += f"{ICONS_EMOJI['penetration']} {artillery['pen']['he']}mm | :fire: {artillery['burn_probability']}% | {artillery['speed']['he']:0.0f}m/s\n"
								else:
									m += "-\n"
									m += "-\n"
									m += "-\n"

								if artillery['max_damage']['ap']:
									m += f"{number_separator(artillery['max_damage']['ap'])}\n"
									m += f"{number_separator(artillery['gun_dpm']['ap'])}\n"
									m += f"{artillery['ricochet']['ap']}{DEGREE_SYMBOL}-{artillery['ricochet_always']['ap']}{DEGREE_SYMBOL} | {artillery['speed']['ap']:0.0f}m/s\n"
								else:
									m += "-\n"
									m += "-\n"
									m += "-\n"

								if artillery['max_damage']['cs']:
									m += f"{number_separator(artillery['max_damage']['cs'])} ({ICONS_EMOJI['penetration']} {artillery['pen']['cs']}mm)\n"
									m += f"{number_separator(artillery['gun_dpm']['cs'])}\n"
									m += f"{artillery['ricochet']['cs']}{DEGREE_SYMBOL}-{artillery['ricochet_always']['cs']}{DEGREE_SYMBOL} | {artillery['speed']['cs']:0.0f}m/s\n"
								else:
									m += "-\n"
									m += "-\n"
									m += "-\n"
								m += f"{sum(v['numBarrels'] * v['count'] for k, v in artillery['turrets'].items()):1.0f} shells\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have main battery guns")

			if user_selection == 1:
				# secondary
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
								m += f"{number_separator(sum([module['profile']['atba'][t]['gun_dpm'] for t in module['profile']['atba'] if type(module['profile']['atba'][t]) == dict]), '.0f')}\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have secondary battery guns")

			if user_selection == 2:
				# torpedo
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
						m += "**Launchers**\n"
						if ships_to_compare[0]['type'] == 'Submarine' or ships_to_compare[1]['type'] == 'Submarine':
							m += "**Loaders**\n"
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
								m += f"{number_separator(torp['max_damage'], '.0f')}\n"
								m += f"{torp['shotDelay']:1.1f}s\n"
								m += f"{torp['torpedo_speed']:1.0f} kts.\n"
								m += f"{sum([torp['turrets'][launcher]['count'] for launcher in torp['turrets']])} launchers\n"
								if ships_to_compare[0]['type'] == 'Submarine' or ships_to_compare[1]['type'] == 'Submarine':
									m += f"{', '.join(str(t) for t in torp['loaders']['0'])} bow, {', '.join(str(t) for t in torp['loaders']['1'])} aft\n"
								else:
									m += "-"
								m += f"{torp['numBarrels']} torpedoes\n"
								m += f"{'Yes' if torp['is_deep_water'] else 'No'}\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
				else:
					embed.add_field(name="Error", value="One of these ships does not have torpedo launchers")
			if user_selection == 3:
				# hull
				ship_module[0]['hull'] = ships_to_compare[0]['modules']['hull']
				ship_module[1]['hull'] = ships_to_compare[1]['modules']['hull']
				l = zip_longest(ship_module[0]['hull'], ship_module[1]['hull'])
				if ship_module[0]['hull'] and ship_module[1]['hull']:
					for pair in l:
						# set up title axis
						m = f"**Hull**\n"
						m += f"**Health**\n"
						if ships_to_compare[0]['type'] == 'Submarine' or ships_to_compare[1]['type'] == 'Submarine':
							m += "**Battery**\n"
							m += "**Regen on Surface**\n"
						m += f"**Turn Radius**\n"
						m += f"**Rudder Time**\n"
						m += f"**{ICONS_EMOJI['concealment']} by Sea**\n"
						m += f"**{ICONS_EMOJI['concealment']} by Air**\n"
						embed.add_field(name="__Concealment__", value=m, inline=True)

						for i, mid in enumerate(pair):
							if mid is not None:
								module = get_module_data(mid)
								hull = module['profile']['hull']
								m = f"{module['name']}\n"
								m += f"{number_separator(hull['health'], '.0f')} HP\n"
								if ships_to_compare[0]['type'] == 'Submarine' or ships_to_compare[1]['type'] == 'Submarine':
									m += f"{hull['battery']['capacity']:1.0f} units\n"
									m += f"{hull['battery']['regenRate']:1.1f} units/s\n"
								else:
									m += "-"
								m += f"{hull['turnRadius']:1.0f}m\n"
								m += f"{hull['rudderTime']:1.1f}s\n"
								m += f"{hull['detect_distance_by_ship']:1.1f} km\n"
								m += f"{hull['detect_distance_by_plane']:1.1f} km\n"
								embed.add_field(name=f"__{ships_to_compare[i]['name']}__", value=m, inline=True)
							else:
								embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=True)
			if user_selection == 4:
				# aa
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
								m += f"{number_separator(plane['max_health'] * module['squad_size'], '.0f')}\n"
								m += f"{plane['payload'] * module['attack_size']:1.0f} {projectile_type}\n"
								m += f"{number_separator(plane['max_damage'], '.0f')}\n"
								m += f"{module['squad_size'] // module['attack_size']:1.0f} flight(s)\n"
								m += f"{module['attack_size']:1.0f} aircraft\n"
								m += f"{number_separator(plane['max_damage'] * plane['payload'] * module['attack_size'], '.0f')}\n"
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
			logger.info("Response expired")
		del user_correction_check