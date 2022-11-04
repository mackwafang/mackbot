import traceback
import pandas as pd

from datetime import date

from discord import app_commands, Embed
from discord.utils import escape_markdown
from discord.ext import commands

from scripts.mackbot_exceptions import NoShipFound
from scripts.utilities.game_data.game_data_finder import get_ship_data_by_id, get_ship_data
from scripts.utilities.game_data.warships_data import ship_list_simple
from scripts.utilities.logger import logger
from scripts.utilities.to_plural import to_plural
from .bot_help import BotHelp
from scripts.mackbot_constants import WOWS_REALMS, roman_numeral, EMPTY_LENGTH_CHAR, ship_types
from scripts.utilities.bot_data import WG
from scripts.utilities.regex import player_arg_filter_regex


class Player(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="player", description="Get information about a player.")
	@app_commands.describe(
		value="Player name. For optional arguments, see mackbot help player or /player help"
	)
	async def player(self, context: commands.Context, value: str):
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

					embed = Embed(title=f"Search result for player {escape_markdown(username)}", description='')
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
								player_stat_max_kills_ship_tier = roman_numeral[ship_data['tier'] - 1]

								ship_data = get_ship_data_by_id(player_battle_stat['max_damage_dealt_ship_id'])
								player_stat_max_damage_ship = ship_data['name']
								player_stat_max_damage_ship_type = ship_data['emoji']
								player_stat_max_damage_ship_tier = roman_numeral[ship_data['tier'] - 1]

								ship_data = get_ship_data_by_id(player_battle_stat['max_scouting_damage_ship_id'])
								player_stat_max_spot_dmg_ship = ship_data['name']
								player_stat_max_spot_dmg_ship_type = ship_data['emoji']
								player_stat_max_spot_dmg_ship_tier = roman_numeral[ship_data['tier'] - 1]

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

										m += f"**{roman_numeral[tier - 1]}: {int(tier_stat['battles'])} battles ({tier_stat['battles'] / player_battle_stat['battles']:2.1%})**\n"
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
						embed.add_field(name='Information not available', value=f"mackbot cannot find player with name {escape_markdown(username)} in the {player_region.upper()} region", inline=True)
				except Exception as e:
					logger.warning(f"Exception in player {type(e)}: {e}")
					traceback.print_exc()
			await context.send(embed=embed)
		else:
			await BotHelp.custom_help(BotHelp, context, "player")
