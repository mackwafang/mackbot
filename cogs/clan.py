from datetime import date

from discord import app_commands, Embed, SelectOption
from discord.utils import escape_markdown
from discord.ext import commands

from .bot_help import BotHelp
from scripts.mackbot_constants import WOWS_REALMS, icons_emoji
from scripts.utilities.bot_data import WG, clan_history
from scripts.utilities.discord.drop_down_menu import UserSelection, get_user_response_with_drop_down
from scripts.utilities.regex import clan_filter_regex


class Clan(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="clan", description="Get some basic information about a clan")
	@app_commands.rename(args="clan")
	@app_commands.describe(
		args="Name or tag of clan"
	)
	async def clan(self, context: commands.Context, args: str):
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
				await BotHelp.custom_help(BotHelp, context, "clan")
				return

			clan_search = WG[clan_region].clans.list(search=search_term)
			if clan_search:
				# check for multiple clan
				selected_clan = None
				if len(clan_search) > 1:
					clan_options= [SelectOption(label=f"[{i + 1}] [{escape_markdown(c['tag'])}] {c['name']}", value=i) for i, c in enumerate(clan_search)][:25]
					view = UserSelection(context.author, 15, "Select a clan", clan_options)

					embed = Embed(title=f"Search result for clan {search_term}", description="")
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
				embed = Embed(title=f"Search result for clan {clan_detail['name']}", description="")
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
				clan_members_sort_by_alpha = sorted(list([escape_markdown(clan_detail['members'][m]['account_name']) for m in clan_detail['members']]))
				for i in range(0, 50, members_per_column):
					sliced_member_list = clan_members_sort_by_alpha[i:i+members_per_column]
					if sliced_member_list:
						embed.add_field(name=f"__**Members**__", value='\n'.join(sliced_member_list), inline=True)
				await context.send(embed=embed)
			else:
				# no clan matches search
				embed = Embed(title=f"Search result for clan {search_term}", description="")
				embed.description += "Clan not found"

				await context.send(embed=embed)
		else:
			await BotHelp.custom_help(BotHelp, context, "clan")
