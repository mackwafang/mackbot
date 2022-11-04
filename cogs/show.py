import re
import traceback
from math import ceil
from typing import Optional

from discord import app_commands, Embed
from discord.ext import commands

from mackbot import icons_emoji
from scripts.mackbot_constants import hull_classification_converter, roman_numeral
from scripts.utilities.bot_data import command_prefix
from scripts.utilities.game_data.warships_data import database_client, skill_list, upgrade_abbr_list, upgrade_list, ship_list
from scripts.utilities.logger import logger
from scripts.utilities.regex import skill_list_regex, equip_regex, ship_list_regex


class Show(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_group(name="show", description="List out all items from a category", pass_context=True, invoke_without_command=True)
	# @mackbot.group(pass_context=True, invoke_without_command=True)
	async def show(self, context: commands.Context):
		# list command
		if context.invoked_subcommand is None:
			await context.invoke(self.client.get_command('help'), 'show')

	@show.command(name="skills", description="Show all ships in a query.")
	@app_commands.rename(args="query")
	@app_commands.describe(args="Query to list items")
	async def skills(self, context: commands.Context, args: Optional[str]=""):
		# check if *not* slash command,
		if context.clean_prefix != '/':
			args = ' '.join(context.message.content.split()[3:])

		# list all skills
		search_param = args.split()
		search_param = skill_list_regex.findall(''.join([i + ' ' for i in search_param]))

		if database_client is not None:
			filtered_skill_list = database_client.mackbot_db.skill_list.find({})
			filtered_skill_list = dict((str(i['skill_id']), i) for i in filtered_skill_list)
		else:
			filtered_skill_list = skill_list.copy()

		# filter by ship class
		ship_class = [i[0] for i in search_param if len(i[0])]
		# convert hull classification to ship type full name
		ship_class = ship_class[0] if len(ship_class) >= 1 else ''
		if len(ship_class) > 0:
			if len(ship_class) <= 2:
				for h in hull_classification_converter:
					if ship_class == hull_classification_converter[h].lower():
						ship_class = h.lower()
						break
			if ship_class.lower() in ['cv', 'carrier']:
				ship_class = 'aircarrier'
			filtered_skill_list = dict([(s, filtered_skill_list[s]) for s in filtered_skill_list if filtered_skill_list[s]['tree'].lower() == ship_class])
		# filter by skill tier
		tier = [i[2] for i in search_param if len(i[2]) > 0]
		tier = int(tier[0]) if len(tier) >= 1 else 0
		if tier != 0:
			filtered_skill_list = dict([(s, filtered_skill_list[s]) for s in filtered_skill_list if filtered_skill_list[s]['y'] + 1 == tier])

		# select page
		page = [i[1] for i in search_param if len(i[1]) > 0]
		page = int(page[0]) if len(page) > 0 else 0

		# generate list of skills
		m = [
			f"**({hull_classification_converter[filtered_skill_list[s]['tree']]} T{filtered_skill_list[s]['y'] + 1})** {filtered_skill_list[s]['name']}" for s in filtered_skill_list
		]
		# splitting list into pages
		num_items = len(m)
		m.sort()
		items_per_page = 24
		num_pages = ceil(len(m) / items_per_page)
		m = [m[i:i + items_per_page] for i in range(0, len(m), items_per_page)]

		logger.info(f"found {num_items} items matching criteria: {args}")
		embed = Embed(title="Commander Skill (%i/%i)" % (min(1, page+1), max(1, num_pages)))
		m = m[page]  # select page
		# spliting selected page into columns
		m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]
		for i in m:
			embed.add_field(name="(Type, tier) Skill", value=''.join([v + '\n' for v in i]))
		embed.set_footer(text=f"{num_items} skills found.\nFor more information on a skill, use [{command_prefix} skill [ship_class] [skill_name]]")

		await context.send(embed=embed)

	@show.command(name="upgrades", description="Show all upgrades in a query.")
	@app_commands.rename(args="query")
	@app_commands.describe(args="Query to list items")
	async def upgrades(self, context: commands.Context, args: Optional[str]=""):
		# list upgrades

		# check if *not* slash command,
		if context.clean_prefix != '/':
			args = ' '.join(context.message.content.split()[3:])

		embed = None
		try:
			# parsing search parameters
			logger.info("starting parameters parsing")
			search_param = args.split()
			s = equip_regex.findall(''.join([i + ' ' for i in search_param]))

			slot = ''.join([i[1] for i in s])
			key = [i[7] for i in s if len(i[7]) > 1]
			page = [i[6] for i in s if len(i[6]) > 1]
			tier = [i[3] for i in s if len(i[3]) > 1]
			embed_title = "Search result for: "

			# select page
			page = int(page[0]) if len(page) > 0 else 1

			if len(tier) > 0:
				for t in tier:
					if t in roman_numeral:
						t = roman_numeral[t]
					tier = f't{t}'
					key += [t]
			if len(slot) > 0:
				key += [slot]
			key = [i.lower() for i in key if not 'page' in i]
			embed_title += f"{''.join([i.title() + ' ' for i in key])}"
			# look up
			result = []
			u_abbr_list = upgrade_abbr_list

			if database_client is not None:
				u_abbr_list = database_client.mackbot_db.upgrade_abbr_list.find({})
				query_result = database_client.mackbot_db.upgrade_list.find({"tags": {"$all": [re.compile(i, re.I) for i in key]}} if key else {})
				result = dict((i['consumable_id'], i) for i in query_result)
				u_abbr_list = dict((i['abbr'], i['upgrade']) for i in u_abbr_list)
			else:
				for u in upgrade_list:
					tags = [str(i).lower() for i in upgrade_list[u]['tags']]
					if all([k in tags for k in key]):
						result += [u]
			logger.info("parsing complete")
			logger.info("compiling message")

			if len(result) > 0:
				m = []
				for u in result:
					upgrade = result[u]
					name = upgrade['name']
					for u_b in u_abbr_list:
						if u_abbr_list[u_b] == name.lower():
							m += [f"**{name}** ({u_b.upper()})"]
							break

				num_items = len(m)
				m.sort()
				items_per_page = 30
				num_pages = ceil(len(m) / items_per_page)
				m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

				embed = Embed(title=embed_title + f"({max(1, page)}/{num_pages})")
				m = m[page]  # select page
				m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
				embed.set_footer(text=f"{num_items} upgrades found.\nFor more information on an upgrade, use [{command_prefix} upgrade [name/abbreviation]]")
				for i in m:
					embed.add_field(name="Upgrade (abbr.)", value=''.join([v + '\n' for v in i]))
			else:
				embed = Embed(title=embed_title, description="")
				embed.description = "No upgrades found"
		except Exception as e:
			if type(e) == IndexError:
				error_message = f"Page {page + 1} does not exists"
			elif type(e) == ValueError:
				logger.info(f"Upgrade listing argument <{args[3]}> is invalid.")
				error_message = f"Value {args[3]} is not understood"
			else:
				logger.info(f"Exception {type(e)} {e}")
		await context.send(embed=embed)

	@show.command(name="ships", description="Show all ships in a query.")
	@app_commands.rename(args="query")
	@app_commands.describe(args="Query to list items")
	# @show.command()
	async def ships(self, context: commands.Context, args: Optional[str]=""):
		# parsing search parameters
		# check if *not* slash command,
		if context.clean_prefix != '/':
			args = ' '.join(context.message.content.split()[3:])

		search_param = args.split()
		s = ship_list_regex.findall(''.join([str(i) + ' ' for i in search_param])[:-1])

		tier = ''.join([i[2] for i in s])
		key = [i[7] for i in s if len(i[7]) > 1]
		page = [i[6] for i in s if len(i[6]) > 0]

		# select page
		page = int(page[0]) if len(page) > 0 else 1

		if len(tier) > 0:
			if tier in roman_numeral:
				tier = roman_numeral[tier]
			tier = f't{tier}'
			key += [tier]
		key = [i.lower() for i in key if not 'page' in i]
		embed_title = f"Search result for {''.join([i.title() + ' ' for i in key])}"

		# look up
		result = []
		if database_client is not None:
			query_result = database_client.mackbot_db.ship_list.find({"tags": {"$all": [re.compile(f"^{i}$", re.I) for i in key]}} if key else {})
			if query_result is not None:
				result = dict((str(i["ship_id"]), i) for i in query_result)
		else:
			for s in ship_list:
				try:
					tags = [i.lower() for i in ship_list[s]['tags']]
					if all([k in tags for k in key]):
						result += [s]
				except Exception as e:
					traceback.print_exc()
					pass
		m = []
		logger.info(f"found {len(result)} items matching criteria: {' '.join(key)}")
		if len(result) > 0:
			# return the list of ships with fitting criteria
			for ship in result:
				ship_data = result[ship]
				if ship_data is None:
					continue
				name = ship_data['name']
				ship_type = ship_data['type']
				tier = ship_data['tier']
				is_prem = ship_data['is_premium']

				tier_string = roman_numeral[tier - 1]
				type_icon = icons_emoji[hull_classification_converter[ship_type].lower() + ("_prem" if is_prem else "")]
				# m += [f"**{tier_string:<6} {type_icon}** {name}"]
				m += [[tier, tier_string, type_icon, name]]

			num_items = len(m)
			m.sort(key=lambda x: (x[0], x[2], x[-1]))
			m = [f"**{(tier_string + ' '+ type_icon).ljust(16, chr(160))}** {name}" for tier, tier_string, type_icon, name in m]

			items_per_page = 30
			num_pages = ceil(len(m) / items_per_page)
			m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

			embed = Embed(title=embed_title + f"({max(1, page)}/{max(1, num_pages)})")
			m = m[page - 1]  # select page
			m = [m[i:i + items_per_page // 2] for i in range(0, len(m), items_per_page // 2)]  # spliting into columns
			embed.set_footer(text=f"{num_items} ships found\nTo get ship build, use [{command_prefix} build [ship_name]]")
			for i in m:
				embed.add_field(name="(Tier) Ship", value=''.join([v + '\n' for v in i]))
		else:
			# no ships found
			embed = Embed(title=embed_title, description="")
			embed.description = "**No ships found**"
		await context.send(embed=embed)
