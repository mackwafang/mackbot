import os

import discord
import csv

from datetime import date
from typing import Optional
from io import BytesIO

from discord import app_commands, Embed, SelectOption, Interaction
from discord.utils import escape_markdown
from discord.ext import commands

from cogs import Build
from mackbot.enums import ANSI_FORMAT, ANSI_BKG_COLOR, ANSI_TEXT_COLOR, SHIP_BUILD_FETCH_FROM
from mackbot.constants import WOWS_REALMS, ICONS_EMOJI, ROMAN_NUMERAL
from mackbot.utilities.game_data.game_data_finder import get_ship_build_by_id, get_ship_data
from mackbot.utilities.game_data.warships_data import database_client
from mackbot.utilities.game_data import data_uploader
from mackbot.utilities.to_plural import to_plural
from mackbot.utilities.bot_data import WG, clan_history
from mackbot.utilities.discord.drop_down_menu import UserSelection, get_user_response_with_drop_down
from mackbot.utilities.discord.items_autocomplete import auto_complete_region, auto_complete_ship_name
from mackbot.wargaming.clans import clan_ranking

LEAGUE_STRING = [
	"Hurricane",
	"Typhoon",
	"Storm",
	"Gale",
	"Squall",
]

def start_ansi_string(_format: ANSI_FORMAT, _color:ANSI_TEXT_COLOR, _bkg: ANSI_BKG_COLOR=""):
	if _bkg:
		return f"[{_format};{_color};{_bkg}m"
	return f"[{_format};{_color}m"

def end_ansi_string():
	return "\u001b[0m"

class Clan(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.bot.tree.add_command(ClanGroup(name="clan", description="Clan related functions"))

class ClanGroup(app_commands.Group):
	@app_commands.command(name='build', description='Get a warship build from your clan')
	@app_commands.describe(
		ship_name="Ship name",
		text_version="Use text version instead",
	)
	@app_commands.autocomplete(ship_name=auto_complete_ship_name)
	async def build(self, interaction: Interaction, ship_name: str, text_version: Optional[bool] = False):
		await getattr(interaction.client.get_cog(Build.__name__), 'build').callback(Build, interaction, ship_name, text_version, True)

	@app_commands.command(name="builds", description="Show what builds you has has uploaded to mackbot")
	async def builds(self, interaction: Interaction):
		embed = discord.Embed(description=f"## Your Clan's Builds\n\n")
		build_ids = dict(database_client.mackbot_db.clan_build.find_one({"guild_id": interaction.guild_id}))['builds']

		if build_ids is None:
			embed.description += "Your clan has not uploaded any builds"
		else:
			for bid in build_ids:
				build_data = get_ship_build_by_id(bid, SHIP_BUILD_FETCH_FROM.MONGO_DB, from_guild=interaction.guild_id)
				ship_data = get_ship_data(build_data['ship'])
				embed.description += f"**{ROMAN_NUMERAL[ship_data['tier'] - 1]} {ICONS_EMOJI[ship_data['type']]} {ship_data['name']}**: {build_data['name']}\n"

		await interaction.response.send_message(embed=embed)

	@app_commands.command(name="sample", description="Download a sample build file to use with the upload command")
	async def sample(self, interaction: Interaction):
		# check if admin to avoid spams
		if not interaction.user.guild_permissions.administrator:
			embed = discord.Embed(description="## You do not have permission to use this command\nYou need to be the server's administration to use this command.")
			await interaction.response.send_message(embed=embed)
			return
		sample_file_dir = os.path.join("tmp", "sample_upload.csv")
		with open(sample_file_dir, "w") as f:
			writer = csv.writer(f)
			writer.writerows([
				["ship_name","build_name","upgrade1","upgrade2","upgrade3","upgrade4","upgrade5","upgrade6","skill1","skill2","skill3","skill4","skill5","skill6","skill7","skill8","skill9","skill10","skill11","skill12","skill13","skill14",
				 "skill15","skill16","cmdr_name"],
				["midway", "test", "agm1", "aem1", "atm1", "tbm2", "fcm1", "fcm2", "air supremacy", " improved engines", " survivability expert", " aircraft armor", " enhanced aircraft armor", " proximity fuze", " torpedo bomber",
				 "repair specialist", " ", " ", " ", " ", " ", " ", " ", " ", "*"],
				["lexington", "another test", "agm1", "aem1", "atm1", "tbm2", "fcm1", "", "air supremacy", " improved engines", " survivability expert", " aircraft armor", " enhanced aircraft armor", " proximity fuze", " torpedo bomber",
				 "repair specialist", " ", " ", " ", " ", " ", " ", " ", " ", "*"],
				["shoukaku", "dank cv build", "agm1", "aem1", "atm1", "tbm2", "fcm1", "", "air supremacy", " improved engines", " survivability expert", " aircraft armor", " enhanced aircraft armor", " proximity fuze", " torpedo bomber",
				 "repair specialist", " ", " ", " ", " ", " ", " ", " ", " ", "*"],
			])

		with open(sample_file_dir, "rb") as f:
			await interaction.response.send_message(
				"The CSV file will need the following values:\n"
				"- It must include 25 values\n"
				"- Value 1 is the ship name\n"
				"- Value 2 is the build's name\n"
				"- Values 3-8 is the upgrade's name\n"
			    " - This can either be the upgrade's full name, or it's abbreviation that @mackbot can understand\n"
			    " - You can check the abbreviation via the **show upgrades** command\n"
				"- Values 9-24 is the commander's skill\n"
			    " - Commander's skill must be a valid WoWS commander skill sequence (i.e. you cannot take a 3-points skill without previously taking a 2-points skill)\n"
				"- Value 25 is the commander's name\n"
				"- A field may be left blank (i.e. you can't fit anymore command skills in a 21-points commander)\n"
				"- A * may be used in the upgrades section of the file to indicate any upgrades\n",
				ephemeral=True,
				file=discord.File(f, "sample_build.csv")
			)

	@app_commands.command(name="upload", description="Upload clan specific build for your clan")
	async def upload(self, interaction: Interaction, file: discord.Attachment):
		# check if admin to avoid spams
		if not interaction.user.guild_permissions.administrator:
			embed = discord.Embed(description="## You do not have permission to use this command\nYou need to be the server's administration to use this command.")
			await interaction.response.send_message(embed=embed)
			return

		if file.filename.split(".")[-1] != 'csv':
			embed = discord.Embed(description="## Your file is of the wrong extension\nI only accepts .csv files")
			await interaction.response.send_message(embed=embed)
			return

		if file.size > 1_000_000:
			embed = discord.Embed(description="## Your file is too big\nI only accept files up to 1MB")
			await interaction.response.send_message(embed=embed)
			return

		# defer first, incase it takes long
		await interaction.response.defer(ephemeral=False, thinking=True)
		# parse file
		file_io = BytesIO(await file.read())
		file_content = file_io.read().decode("utf-8").splitlines()[:30]
		file_content = csv.reader(file_content, delimiter=",", skipinitialspace=True)
		errors = []
		builds = []

		# compile builds
		for index, row in enumerate(file_content):
			if index == 0:
				continue

			if len(row) == 25:
				build_ship_name = row[0]
				build_name = row[1][:32]
				build_upgrades = row[2:8]
				build_skills = row[8:-2]
				build_cmdr = row[-2]
				builds.append([build_ship_name, build_name, build_upgrades, build_skills, build_cmdr])
			else:
				errors.append(f"Line {index+1} excepts 25 values. Found {len(row)} values")

		# upload and compile errors
		build_ids, errors = data_uploader.clan_build_upload(builds, interaction.guild_id)
		send_res_file = False
		res_file = None
		kwargs = {}
		if errors:
			output = "```ansi\n" \
			         f"{start_ansi_string(ANSI_FORMAT.NONE, ANSI_TEXT_COLOR.RED)}" \
			         f"WARNING: Uploaded file has errors\n" \
			         f"{chr(10)+chr(10).join(errors)}" \
			         f"{end_ansi_string()}" \
			         f"```"
			# ye too big, send file instead
			kwargs = {"content": output}
			if len(output) > 1500:
				send_res_file = True
				res_file_path = os.path.join(".", "tmp", f"{interaction.id}_response.txt")
				with open(res_file_path, 'w') as f:
					f.write(output)
				res_file = discord.File(res_file_path, "response.txt")
				kwargs = {"file": res_file}

		embed = discord.Embed(description=f"## {'Partial' if errors else ''} Success\nYour clan's builds has been uploaded\n\nHere are the builds that mackbot knows:\n")
		for bid in build_ids:
			build_data = get_ship_build_by_id(bid, SHIP_BUILD_FETCH_FROM.MONGO_DB)
			ship_data = get_ship_data(build_data['ship'])
			embed.description += f"**{ROMAN_NUMERAL[ship_data['tier']-1]} {ICONS_EMOJI[ship_data['type']]} {ship_data['name']}**: {build_data['name']}\n"
		kwargs["embed"] = embed

		if interaction.response.is_done():
			await interaction.followup.send(**kwargs)
		else:
			await interaction.response.send_message(**kwargs)

	@app_commands.command(name="info", description="Get some basic information about a clan")
	@app_commands.describe(
		clan_name="Name or tag of clan",
		region='Clan region'
	)
	@app_commands.autocomplete(region=auto_complete_region)
	async def info(self, interaction: Interaction, clan_name: str, region: Optional[str]='na'):
		args = clan_name
		await interaction.response.defer(ephemeral=False, thinking=True)
		search_term = clan_name
		clan_region = region

		if clan_region not in WOWS_REALMS:
			clan_region = 'na'

		clan_search = WG[clan_region].clan_list(clan_name=search_term)
		if clan_search:
			# check for multiple clan
			selected_clan = None
			if len(clan_search) > 1:
				clan_options= [SelectOption(label=f"[{i + 1}] [{escape_markdown(c['tag'])}] {c['name']}", value=i) for i, c in enumerate(clan_search)][:25]
				view = UserSelection(interaction.user, 15, "Select a clan", clan_options)

				embed = Embed(description=f"## Search result for clan {search_term}\n")
				embed.description += "**mackbot found the following clans**\n"
				embed.description += '\n'.join(i.label for i in clan_options)
				embed.set_footer(text="Please reply with the number indicating the clan you would like to search\n"+
				                      "Response expires in 15 seconds")
				view.message = await interaction.channel.send(embed=embed, view=view)
				selected_clan_index = await get_user_response_with_drop_down(view)
				if selected_clan_index != -1:
					# user responded
					selected_clan = clan_search[selected_clan_index]
					await view.message.delete()
				else:
					# no response
					return
			else:
				selected_clan = clan_search[0]
			# output clan information
			# get clan information

			clan_detail = WG[clan_region].clan_info(clan_id=selected_clan['clan_id'], extra='members')[str(selected_clan['clan_id'])]
			clan_id = clan_detail['clan_id']
			clan_ladder = clan_ranking(clan_id, clan_region)

			embed = Embed(description=f"## [{clan_detail['tag']}] {clan_detail['name']}", color=clan_ladder['color'])
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
			m += ' old)\n'
			if clan_detail['old_tag'] and clan_detail['old_name']:
				m += f"**Formerly:** [{escape_markdown(clan_detail['old_tag'])}] {clan_detail['old_name']}\n"
			m += f"**Members: ** {clan_detail['members_count']}\n"
			m += f"**Region: ** {clan_region.upper()}\n"
			m += f"**League: **{LEAGUE_STRING[clan_ladder['league']]} {ROMAN_NUMERAL[clan_ladder['division']]}\n"
			embed.add_field(name=f"__**Basic detail**__", value=m, inline=not clan_detail['description'])

			if clan_detail['description']:
				embed.add_field(name="__**Description**__", value=clan_detail['description'], inline=False)

			# clan current ranking
			if clan_ladder is not None:
				battle_count = clan_ladder['battles_count']
				best_position = clan_ladder['max_position']
				m = ""
				m += f"{LEAGUE_STRING[clan_ladder['league']]} {ROMAN_NUMERAL[clan_ladder['division']]} ({clan_ladder['division_rating']} / 100)\n"
				m += f"Best: {LEAGUE_STRING[best_position['league']]} {ROMAN_NUMERAL[best_position['division']]} ({best_position['division_rating']} / 100)\n\n"

				m += f"{to_plural('battle', battle_count)} ({clan_ladder['wins_count']} W - {battle_count - clan_ladder['wins_count']} L | {clan_ladder['wins_count']/max(1, battle_count):0.2%})\n"
				embed.add_field(name="__**Clan Battle**__", value=m, inline=False)

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
					history_output += [(previous_member_list[m]['account_name'], ICONS_EMOJI['clan_out'])]
				for m in members_in:
					history_output += [(new_member_list[m]['account_name'], ICONS_EMOJI['clan_in'])]

				# check if last update was at least a week ago
				if (date.fromtimestamp(clan_detail['updated_at']) - date.fromtimestamp(clan_history[clan_id]['updated_at'])).days > 7:
					# update history
					clan_history[clan_id] = {'members': clan_detail['members'], 'updated_at': clan_detail['updated_at']}
			else:
				# not in history, add to history
				clan_history[clan_id] = {'members': clan_detail['members'], 'updated_at': clan_detail['updated_at']}

			if history_output:
				embed.add_field(name=f"__**Transfer History**__", value='\n'.join(f"{escape_markdown(name)}{icon}" for name, icon in history_output), inline=False)

			# output members
			members_per_column = 10
			clan_members_sort_by_alpha = sorted(list([escape_markdown(clan_detail['members'][m]['account_name']) for m in clan_detail['members']]))
			for i in range(0, 50, members_per_column):
				sliced_member_list = clan_members_sort_by_alpha[i:i+members_per_column]
				if sliced_member_list:
					embed.add_field(name=f"__**Members**__", value='\n'.join(sliced_member_list), inline=True)
		else:
			# no clan matches search
			embed = Embed(title=f"Search result for clan {search_term}", description="")
			embed.description += "Clan not found"

		if interaction.response.is_done():
			await interaction.followup.send(embed=embed)
		else:
			await interaction.response.send_message(embed=embed)