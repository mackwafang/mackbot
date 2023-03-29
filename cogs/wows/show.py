import re
import traceback
from math import ceil
from typing import Optional

from discord import app_commands, Embed, Interaction
from discord.ext import commands

from bot import ICONS_EMOJI
from mackbot.enums import SHIP_CONSUMABLE, SHIP_CONSUMABLE_CHARACTERISTIC
from mackbot.constants import hull_classification_converter, ROMAN_NUMERAL, ITEMS_TO_UPPER
from mackbot.utilities.bot_data import command_prefix
from mackbot.utilities.game_data.warships_data import database_client, skill_list, upgrade_abbr_list, upgrade_list, ship_list
from mackbot.utilities.logger import logger
from mackbot.utilities.regex import skill_list_regex, equip_regex, ship_list_regex, consumable_regex
from mackbot.utilities.ship_consumable_code import characteristic_rules


class Show(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.bot.tree.add_command(ShowGroup(name="show", description="List out all items from a category"))
	# @app_commands.command(name="show", description="List out all items from a category")#, pass_context=True, invoke_without_command=True)
	# async def show(self, interaction: Interaction):
	# 	pass

class ShowGroup(app_commands.Group):
	@app_commands.command(name="skills", description="Show all ships in a query.")
	@app_commands.rename(args="query")
	@app_commands.describe(args="Query to list items")
	async def skills(self, interaction: Interaction, args: Optional[str]=""):
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

		await interaction.response.send_message(embed=embed)

	@app_commands.command(name="upgrades", description="Show all upgrades in a query.")
	@app_commands.rename(args="query")
	@app_commands.describe(args="Query to list items")
	async def upgrades(self, interaction: Interaction, args: Optional[str]=""):

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
					if t in ROMAN_NUMERAL:
						t = ROMAN_NUMERAL[t]
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
		await interaction.response.send_message(embed=embed)

	@app_commands.command(name="ships", description="Show all ships in a query.")
	@app_commands.rename(args="query")
	@app_commands.describe(args="Query to list items")
	# @show.command()
	async def ships(self, interaction: Interaction, args: Optional[str]=""):

		s = ship_list_regex.findall(args)

		# how dafuq did this even works
		tier_key = [match[0] for match in s if match[0]]
		if tier_key:
			tier_key = f"t{tier_key[0]}"
		else:
			tier_key = ""
		ship_key = [[group for gi, group in enumerate(match) if group and gi not in [6, 5, 4, 3, 1, 0, 10]] for match in s] # tokenize
		ship_key = [i[0] for i in ship_key if i] # extract

		# specific keys
		c_char_reason = []
		consumable_filter_keys = []
		try:
			consumable_filter_keys = consumable_regex.findall(args) # get consumable filters
			# create consumable characteristics reasoning
			for match in consumable_filter_keys:
				for group in [2, 4, 6, 8, 10, 12]:
					if match[group]:
						if match[group-1]:
							consumable = {
								2: SHIP_CONSUMABLE.DAMCON,
								4: SHIP_CONSUMABLE.HYDRO,
								6: SHIP_CONSUMABLE.RADAR,
								8: SHIP_CONSUMABLE.SMOKE,
								10: SHIP_CONSUMABLE.DFAA,
								12: SHIP_CONSUMABLE.HEAL,
							}[group]
							characteristic = {
								"quick ": SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE,
								"quick charge ": SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE,
								"limited ": SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE,
								"limited charge ": SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE,
								"long duration ": SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION,
								"short duration ": SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_DURATION,
								"long range ": SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE,
								"short range ": SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_RANGE,
								"super ": SHIP_CONSUMABLE_CHARACTERISTIC.SUPER,
								"high charge ": SHIP_CONSUMABLE_CHARACTERISTIC.HIGH_CHARGE,
								"trailing ": SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING,
								"unlimited ": SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE,
								"unlimited charge ": SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE,
							}[match[group - 1].lower()]
							reason = [f"{match[group - 1].title()}{match[group].title()} refers to {match[group].title()}s {r}" for r in characteristic_rules((consumable.value, 1 << characteristic.value))]
							c_char_reason.extend(reason)
		except IndexError:
			pass

		try:
			gun_caliber_comparator = [v for v in [i[4] for i in s if i] if v][0]
			gun_caliber_compare_value = int([v for v in [i[5] for i in s if i] if v][0])
		except (ValueError, IndexError):
			gun_caliber_comparator = ""
			gun_caliber_compare_value = 0

		key = ship_key.copy()
		if consumable_filter_keys:
			key.extend([i[0] for i in consumable_filter_keys]) # add consumable filters
		if tier_key:
			key.append(tier_key)

		# set up title
		embed_title = f"Search result for {', '.join([i.title() if i.upper() not in ITEMS_TO_UPPER else i.upper() for i in ship_key])}"
		if not ship_key:
			embed_title += "ships"
		if gun_caliber_compare_value > 0:
			embed_title += f", with guns {gun_caliber_comparator} {gun_caliber_compare_value}mm"
		if consumable_filter_keys:
			embed_title += f" and {', '.join([i[0].title() if i[0].upper() not in ITEMS_TO_UPPER else i[0].upper() for i in consumable_filter_keys])} consumables"

		# look up
		result = []
		if database_client is not None:
			search_query = {}
			if ship_key or tier_key:
				tag_query = [re.compile(f"^{i}$", re.I) for i in ship_key]
				if tier_key:
					tag_query.append(re.compile(f"^{tier_key}$", re.I))
				search_query["tags.ship"] = {"$all": tag_query}
			if consumable_filter_keys:
				search_query["tags.consumables"] = {"$all": [re.compile(f"^{i[0]}$", re.I) for i in consumable_filter_keys]}
			if gun_caliber_comparator:
				comparator_map = {
					">": "gt",
					"<": "lt",
					">=": "gte",
					"<=": "lte",
					"==": "eq"
				}
				search_query["tags.gun_caliber"] = {f"${comparator_map[gun_caliber_comparator]}": gun_caliber_compare_value}

			query_result = database_client.mackbot_db.ship_list.find(search_query)
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
		try:
			page = [match[1][5:] for match in s if match[1]]
			page = max(0, int(page[0]) - 1)
		except (IndexError, ValueError):
			page = 0

		logger.info(f"found {len(result)} items matching criteria: {' '.join(key)}")
		if len(result) > 0:
			# compile search information
			for ship in result:
				ship_data = result[ship]
				if ship_data is None:
					continue
				name = ship_data['name']
				ship_type = ship_data['type']
				tier = ship_data['tier']
				is_prem = ship_data['is_premium']
				nation = ship_data['nation']
				nation = ICONS_EMOJI[f"flag_{nation.upper() if nation in ITEMS_TO_UPPER else nation.title()}"]

				gun_caliber_string = ""
				if gun_caliber_comparator:
					gun_caliber_string += f" ({', '.join(f'{i}mm' for i in ship_data['tags']['gun_caliber'])})"

				tier_string = ROMAN_NUMERAL[tier - 1]
				type_icon = ICONS_EMOJI[hull_classification_converter[ship_type].lower() + ("_prem" if is_prem else "")]
				# m += [f"**{tier_string:<6} {type_icon}** {name}"]
				m += [[tier, tier_string, type_icon, name + gun_caliber_string, nation]]

			# separate into pages
			num_items = len(m)
			m.sort(key=lambda x: (x[-1], x[0], x[2], x[-2]))
			m = [f"{nation} **{type_icon} {tier_string}** {name}" for tier, tier_string, type_icon, name, nation in m]

			items_per_page = 60
			columns = 6
			num_pages = ceil(len(m) / items_per_page)
			m = [m[i:i + items_per_page] for i in range(0, len(result), items_per_page)]  # splitting into pages

			embed = Embed(title=f"{embed_title} ({max(1, page + 1)}/{max(1, num_pages)})")
			m = m[page]  # select page
			m = [m[i:i + items_per_page // columns] for i in range(0, len(m), items_per_page // columns)]  # spliting into columns
			embed.set_footer(text=f"{num_items} ships found\n"
			                      f"To get ship build, use [{command_prefix} build ship_name]\n"
			                      f"To get ship data, use [{command_prefix} ship ship_name]\n" +
			                      '\n'.join(c_char_reason))
			for i in m:
				embed.add_field(name="(Tier) Ship", value='\n'.join(i))
		else:
			# no ships found
			embed = Embed(title=embed_title, description="")
			embed.description = "**No ships found**"
		await interaction.response.send_message(embed=embed)
