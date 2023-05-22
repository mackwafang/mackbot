import asyncio
import traceback
from typing import Optional

import pandas as pd

from datetime import date

from discord import app_commands, Embed, Interaction
from discord.utils import escape_markdown
from discord.ext import commands

from mackbot.utilities.discord.formatting import number_separator
from mackbot.exceptions import NoShipFound
from mackbot.constants import ROMAN_NUMERAL, EMPTY_LENGTH_CHAR, ship_types, ICONS_EMOJI, ITEMS_TO_UPPER
from mackbot.utilities.game_data.game_data_finder import get_ship_data_by_id, get_ship_data
from mackbot.utilities.game_data.warships_data import ship_list_simple
from mackbot.utilities.discord.items_autocomplete import auto_complete_region, auto_complete_ship_name, auto_complete_battle_type, auto_complete_tier
from mackbot.utilities.logger import logger
from mackbot.utilities.to_plural import to_plural
from mackbot.utilities.bot_data import WG
from mackbot.utilities.regex import player_arg_filter_regex


class Player(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="player", description="Get information about a player.")
	@app_commands.rename(b_type="battle_type")
	@app_commands.describe(
		player_name="Player name",
		region="Player's region. Defaults to na",
		tier="Display top 10 ships of this tier",
		ship="Display player's stat of this ship",
		b_type="Switch battle type for display. Acceptable values: solo, div2 (2-man divisions), div3 (3-man divisions). Default is pvp"
	)
	@app_commands.autocomplete(
		region=auto_complete_region,
		ship=auto_complete_ship_name,
		b_type=auto_complete_battle_type,
		tier=auto_complete_tier
	)
	async def player(self,
	                 interaction: Interaction,
	                 player_name: str,
	                 region: Optional[str]='na',
	                 tier:Optional[int]=0,
	                 ship:Optional[str]="",
	                 b_type:Optional[str]='pvp'
	                 ):

		await interaction.response.defer(ephemeral=False, thinking=True)

		try:
			battle_type = 'pvp'
			battle_type_string = 'Random'
			username = player_name[:24]
			battle_type = b_type
			player_region = region
			ship_filter = ship
			try:
				ship_tier_filter = int(tier)
			except ValueError:
				ship_tier_filter = 0
			player_region = player_region.lower()

			player_id_results = WG[player_region].player(player_name=username, search_type='exact',)
			player_id = str(player_id_results[0]['account_id']) if len(player_id_results) > 0 else ""

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

			embed = Embed(title=f"Search result for player {escape_markdown(username)}", description='')
			if player_id:
				player_name = player_id_results[0]['nickname']
				if battle_type == 'pvp':
					player_general_stats = WG[player_region].player_info(player_id=player_id)[player_id]
				else:
					player_general_stats = WG[player_region].player_info(player_id=player_id, extra="statistics."+battle_type, )[player_id]
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
					player_clan_id = WG[player_region].player_clan_info(player_id=player_id)
					player_clan_tag = ""
					if player_clan_id[player_id] is not None: # Check if player has joined a clan yet
						player_clan_id = player_clan_id[player_id]['clan_id']
						if player_clan_id is not None: # check if player is in a clan
							player_clan = WG[player_region].clan_info(clan_id=player_clan_id)[str(player_clan_id)]
							player_clan_str = f"**[{escape_markdown(player_clan['tag'])}]** {player_clan['name']}"
							player_clan_tag = f"[{escape_markdown(player_clan['tag'])}]"
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
					embed.add_field(name=f'__**{player_clan_tag}{" " if player_clan_tag else ""}{escape_markdown(player_name)}**__', value=m, inline=False)

					# add listing for player owned ships and of requested battle type
					player_ships = WG[player_region].ships_stat(player_id=player_id, extra='' if battle_type == 'pvp' else battle_type)[player_id]
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
							"average": {
								"dmg"       : 0 if ship_stat['battles'] == 0 else ship_stat['damage_dealt'] / ship_stat['battles'],
								"spot_dmg"  : 0 if ship_stat['battles'] == 0 else ship_stat['damage_scouting'] / ship_stat['battles'],
								"kills"     : 0 if ship_stat['battles'] == 0 else ship_stat['frags'] / ship_stat['battles'],
								"xp"        : 0 if ship_stat['battles'] == 0 else ship_stat['xp'] / ship_stat['battles'],
							},
							"max": {
								"kills"     : ship_stat['max_frags_battle'],
								"dmg"       : ship_stat['max_damage_dealt'],
								"spot_dmg"  : ship_stat['max_damage_scouting'],
								"xp"        : ship_stat['max_xp'],
							},
							'main_battery'  : ship_stat['main_battery'].copy(),
							'secondary_battery': ship_stat['second_battery'].copy(),
							'ramming'       : ship_stat['ramming'].copy(),
							'torpedoes'     : ship_stat['torpedoes'].copy(),
							'aircraft'      : ship_stat['aircraft'].copy()
						}
						player_ship_stats[ship_id] = stats.copy()
					# sort player owned ships by battle count
					player_ship_stats = {k: v for k, v in sorted(player_ship_stats.items(), key=lambda x: x[1]['battles'], reverse=True)}
					player_ship_stats_df = pd.DataFrame.from_dict(player_ship_stats, orient='index')
					player_battle_stat = player_general_stats['statistics'][battle_type]

					if not ship_filter and not ship_tier_filter:
						# general information
						max_kills_ship_data = get_ship_data_by_id(player_battle_stat['max_frags_ship_id'])
						max_damage_ship_data = get_ship_data_by_id(player_battle_stat['max_damage_dealt_ship_id'])
						max_spotting_ship_data = get_ship_data_by_id(player_battle_stat['max_scouting_damage_ship_id'])
						player_stat = {
							'wr': player_battle_stat['wins'] / player_battle_stat['battles'],
							'sr': player_battle_stat['survived_battles'] / player_battle_stat['battles'],
							'max': {
								'kills': {
									'count': player_battle_stat['max_frags_battle'],
									'ship': {
										'name': max_kills_ship_data['name'],
										'type': max_kills_ship_data['emoji'],
										'tier': ROMAN_NUMERAL[max_kills_ship_data['tier'] - 1],
										'nation': ICONS_EMOJI[f"flag_{max_kills_ship_data['nation'].upper() if max_kills_ship_data['nation'] in ITEMS_TO_UPPER else max_kills_ship_data['nation'].title()}"]
									},
								},
								'damage': {
									'count': player_battle_stat['max_damage_dealt'],
									'ship': {
										'name': max_damage_ship_data['name'],
										'type': max_damage_ship_data['emoji'],
										'tier': ROMAN_NUMERAL[max_damage_ship_data['tier'] - 1],
										'nation': ICONS_EMOJI[f"flag_{max_damage_ship_data['nation'].upper() if max_damage_ship_data['nation'] in ITEMS_TO_UPPER else max_damage_ship_data['nation'].title()}"]
									}
								},
								'spotting': {
									'count': player_battle_stat['max_damage_scouting'],
									'ship': {
										'name': max_spotting_ship_data['name'],
										'type': max_spotting_ship_data['emoji'],
										'tier': ROMAN_NUMERAL[max_spotting_ship_data['tier'] - 1],
										'nation': ICONS_EMOJI[f"flag_{max_spotting_ship_data['nation'].upper() if max_spotting_ship_data['nation'] in ITEMS_TO_UPPER else max_spotting_ship_data['nation'].title()}"]
									}
								}
							},
							'average': {
								'kills': player_battle_stat['frags'] / player_battle_stat['battles'],
								'damage': player_battle_stat['damage_dealt'] / player_battle_stat['battles'],
								'xp': player_battle_stat['xp'] / player_battle_stat['battles'],
								'spotting': player_battle_stat['damage_scouting'] / player_battle_stat['battles'],
							}
						}

						m = f"**{player_battle_stat['battles']:,} battles**\n"
						m += f"**Win Rate**: {player_stat['wr']:0.2%} ({player_battle_stat['wins']} W / {player_battle_stat['losses']} L / {player_battle_stat['draws']} D)\n"
						m += f"**Survival Rate**: {player_stat['sr']:0.2%} ({player_battle_stat['survived_battles']} battles)\n"
						m += f"**Average Kills**: {number_separator(player_stat['average']['kills'], '.2f')}\n"
						m += f"**Average Damage**: {number_separator(player_stat['average']['damage'], '.0f')}\n"
						m += f"**Average Spotting**: {number_separator(player_stat['average']['spotting'], '.0f')}\n"
						m += f"**Average XP**: {number_separator(player_stat['average']['xp'], '.0f')} XP\n"
						m += f"**Highest Kill**: {to_plural('kill', player_stat['max']['kills']['count'])} with " \
						     f"{player_stat['max']['kills']['ship']['nation']} {player_stat['max']['kills']['ship']['type']} " \
						     f"**{player_stat['max']['kills']['ship']['tier']} {player_stat['max']['kills']['ship']['name']}**\n"
						m += f"**Highest Damage**: {number_separator(player_stat['max']['damage']['count'], '.0f')} with " \
						     f"{player_stat['max']['damage']['ship']['nation']} {player_stat['max']['damage']['ship']['type']} " \
						     f"**{player_stat['max']['damage']['ship']['tier']} {player_stat['max']['damage']['ship']['name']}**\n"
						m += f"**Highest Spotting Damage**: {number_separator(player_stat['max']['spotting']['count'], '.0f')} with " \
						     f"{player_stat['max']['spotting']['ship']['nation']} {player_stat['max']['spotting']['ship']['type']} " \
						     f"**{player_stat['max']['spotting']['ship']['tier']} {player_stat['max']['spotting']['ship']['name']}**\n"
						embed.add_field(name=f"__**{battle_type_string} Battle**__", value=m, inline=True)

						# top 10 ships by battle count
						m = ""
						for i in range(5):
							try:
								ship = player_ship_stats[list(player_ship_stats)[i]] # get ith ship
								ship_nation_emoji = ICONS_EMOJI[f"flag_{ship['nation'].upper() if ship['nation'] in ITEMS_TO_UPPER else ship['nation'].title()}"]
								m += f"**{ship_nation_emoji}{ship['emoji']}{ROMAN_NUMERAL[ship['tier'] - 1]} {ship['name'].title()}** ({ship['battles']} | {ship['wr']:0.2%} WR)\n"
							except IndexError:
								pass
						embed.add_field(name=f"__**Top 5 {battle_type_string} Ships (by battles)**__", value=m, inline=True)

						embed.add_field(name=EMPTY_LENGTH_CHAR, value=EMPTY_LENGTH_CHAR, inline=False)

						# battle distribution by ship types
						player_ship_stats_df = player_ship_stats_df.groupby(['type']).sum()
						m = ""
						for s_t in sorted([i for i in ship_types if i != "Aircraft Carrier"]):
							try:
								if s_t in list(player_ship_stats_df.index):
									type_stat = player_ship_stats_df.loc[s_t]
									if type_stat['battles'] > 0:
										emoji = {
											"AirCarrier": ICONS_EMOJI['cv'],
											"Battleship": ICONS_EMOJI['bb'],
											"Cruiser":  ICONS_EMOJI['c'],
											"Destroyer": ICONS_EMOJI['dd'],
											"Submarine": ICONS_EMOJI['ss']
										}[s_t]
										m += f"**{emoji}{ship_types[s_t]}s**\n"

										type_average_kills = type_stat['kills'] / max(1, type_stat['battles'])
										type_average_dmg = type_stat['damage'] / max(1, type_stat['battles'])
										type_average_wr = type_stat['wins'] / max(1, type_stat['battles'])
										m += f"{int(type_stat['battles'])} battle{'s' if type_stat['battles'] else ''} ({type_stat['battles'] / player_battle_stat['battles']:2.1%})\n"
										m += f"{type_average_wr:0.2%} WR | {type_average_kills:0.2f} Kills | {number_separator(type_average_dmg, '.0f')} DMG\n\n"
							except KeyError:
								traceback.print_exc()
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

								m += f"**{ROMAN_NUMERAL[tier - 1]}: {number_separator(tier_stat['battles'], '.0f')} battles ({tier_stat['battles'] / player_battle_stat['battles']:2.1%})**\n"
								m += f"{tier_average_wr:0.2%} WR | {tier_average_kills:0.2f} Kills | {number_separator(tier_average_dmg, '.0f')} DMG\n"
							except KeyError:
								m += f"**{list(ROMAN_NUMERAL)[tier - 1]}**: No battles\n"
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
										ship_nation_emoji = ICONS_EMOJI[f"flag_{ship['nation'].upper() if ship['nation'] in ITEMS_TO_UPPER else ship['nation'].title()}"]
										m += f"**{r}) {ship_nation_emoji} {ROMAN_NUMERAL[ship['tier']- 1]} {ship['emoji']} {ship['name'].title()}**\n"
										m += f"({ship['battles']} battles | {ship['wr']:0.2%} WR | {ship['sr']:2.2%} SR)\n"
										m += f"Avg. Kills: {ship['average']['kills']:0.2f} | Avg. Damage: {number_separator(ship['average']['dmg'], '.0f')}\n\n"
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
							ship_nation = ICONS_EMOJI[f"flag_{player_ship_stats_df['nation'].upper() if player_ship_stats_df['nation'] in ITEMS_TO_UPPER else player_ship_stats_df['nation'].title()}"]
							m += f"**{ship_nation} {player_ship_stats_df['emoji']} {ROMAN_NUMERAL[player_ship_stats_df['tier'] - 1]} {player_ship_stats_df['name'].title()}**\n"
							m += f"**{player_ship_stats_df['battles']} Battles**\n"
							m += f"**Win Rate:** {player_ship_stats_df['wr']:2.2%} ({player_ship_stats_df['wins']} W | {player_ship_stats_df['losses']} L | {ship_battles_draw} D)\n"
							m += f"**Survival Rate: ** {player_ship_stats_df['sr']:2.2%} ({player_ship_stats_df['sr'] * player_ship_stats_df['battles']:1.0f} battles)\n"
							m += f"**{'-'*10}Average{'-'*10}**\n"
							m += f"**Kills: ** {player_ship_stats_df['average']['kills']:0.2f}\n"
							m += f"**Damage: ** {number_separator(player_ship_stats_df['average']['dmg'], '.0f')}\n"
							m += f"**Spotting Damage: ** {number_separator(player_ship_stats_df['average']['spot_dmg'], '.0f')}\n"
							m += f"**XP: ** {number_separator(player_ship_stats_df['average']['xp'], '.0f')}\n"
							m += f"**{'-' * 10}Best{'-' * 10}**\n"
							m += f"**Kills: ** {number_separator(player_ship_stats_df['max']['kills'], '.0f')}\n"
							m += f"**Damage: ** {number_separator(player_ship_stats_df['max']['dmg'], '.0f')}\n"
							m += f"**Spotting Damage: ** {number_separator(player_ship_stats_df['max']['spot_dmg'], '.0f')}\n"
							m += f"**XP: ** {number_separator(player_ship_stats_df['max']['xp'], '.0f')}\n"
						except Exception as e:
							if type(e) == NoShipFound:
								m += f"Ship with name {ship_filter} is not found\n"
							if type(e) == KeyError:
								m += f"This player has never played {ship_filter.title()}\n"
							else:
								m += "An internal error has occurred.\n"
								traceback.print_exc()
						embed.add_field(name="__Ship Specific Stat__", value=m, inline=True)

						for field in [['main_battery', 'secondary_battery'], ['ramming', 'torpedoes', 'aircraft']]:
							m = ""
							for kill_type in field:
								field_title = ' '.join(kill_type.split("_")).title()
								kill_type_stat = player_ship_stats_df[kill_type]
								m += f"__**{field_title}**__\n"
								m += f"**Kills:** {kill_type_stat['frags']}\n"
								m += f"**Max Kills:** {kill_type_stat['max_frags_battle']}\n"
								if 'hits' in kill_type_stat:
									m += f"**Accuracy:** {kill_type_stat['hits']/max(1, kill_type_stat['shots']):0.1%} ({kill_type_stat['hits']}/{kill_type_stat['shots']})\n"
								m += "\n"
							embed.add_field(name=f"__Stat by Armament__", value=m, inline=True)

					embed.set_footer(text=f"Last updated at {date.fromtimestamp(player_general_stats['stats_updated_at']).strftime('%b %d, %Y')}")
			else:
				embed.add_field(name='Information not available', value=f"mackbot cannot find player with name {escape_markdown(username)} in the {player_region.upper()} region", inline=True)

			await interaction.followup.send(embed=embed)
		except Exception as e:
			logger.warning(f"Exception in player {type(e)}: {e}")
			traceback.print_exc()

			embed = Embed(title="An internal error has occurred.")
			await interaction.response.send_message(embed=embed)