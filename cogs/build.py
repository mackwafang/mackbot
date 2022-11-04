import traceback

from discord import app_commands, Embed, SelectOption, File
from discord.errors import Forbidden
from discord.ext import commands
from scripts.mackbot_constants import ship_types, roman_numeral, nation_dictionary
from scripts.mackbot_enums import SHIP_BUILD_FETCH_FROM
from scripts.mackbot_exceptions import *
from scripts.utilities.logger import logger
from scripts.utilities.create_build_image import create_build_image
from scripts.utilities.game_data.warships_data import database_client
from scripts.utilities.game_data.game_data_finder import get_ship_data, get_upgrade_data, get_commander_data, get_ship_builds_by_name, skill_list
from scripts.utilities.correct_user_mispell import correct_user_misspell
from scripts.utilities.find_close_match_item import find_close_match_item
from scripts.utilities.discord.drop_down_menu import UserSelection, get_user_response_with_drop_down

class Build(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name='build', description='Get a basic warship build')
	@app_commands.rename(args="value")
	@app_commands.describe(
		args="Ship name. Adds -i before ship name to get image variation",
	)
	async def build(self, context: commands.Context, args: str):

		# check if *not* slash command,
		if context.clean_prefix != '/':
			args = ' '.join(context.message.content.split()[2:])

		args = args.split()
		send_image_build = args[0] in ["--image", "-i"]
		if send_image_build:
			args = args[1:]
		user_ship_name = ''.join([i + ' ' for i in args])[:-1]
		name, images = "", None
		try:
			output = get_ship_data(user_ship_name)
			name = output['name']
			nation = output['nation']
			images = output['images']
			ship_type = output['type']
			tier = output['tier']
			is_prem = output['is_premium']

			# find ship build
			builds = get_ship_builds_by_name(name, fetch_from=SHIP_BUILD_FETCH_FROM.MONGO_DB)
			user_selected_build_id = 0
			multi_build_user_response = None

			# get user selection for multiple ship builds
			if len(builds) > 1:
				embed = Embed(title=f"Build for {name}", description='')
				embed.set_thumbnail(url=images['small'])

				embed.description = f"**Tier {list(roman_numeral.keys())[tier - 1]} {nation_dictionary[nation]} {ship_types[ship_type].title()}**"

				m = ""
				for i, bid in enumerate(builds):
					build_name = builds[i]['name']
					m += f"[{i + 1}] {build_name}\n"
				embed.add_field(name="mackbot found multiple builds for this ship", value=m, inline=False)
				embed.set_footer(text="Please select a build.\nResponse expires in 15 seconds.")
				options = [SelectOption(label=f"[{i + 1}] {builds[i]['name']}", value=i) for i, b in enumerate(builds)]
				view = UserSelection(
					author=context.message.author,
					timeout=15,
					options=options,
					placeholder="Select a build"
				)
				view.message = await context.send(embed=embed, view=view)
				user_selected_build_id = await get_user_response_with_drop_down(view)
				if 0 <= user_selected_build_id < len(builds):
					pass
				else:
					await context.send(f"Input {user_selected_build_id} is incorrect")

			if not builds:
				raise NoBuildFound
			else:
				build = builds[user_selected_build_id]
				build_name = build['name']
				upgrades = build['upgrades']
				skills = build['skills']
				cmdr = build['cmdr']
				build_errors = build['errors']

			if not send_image_build:
				embed = Embed(title=f"{build_name.title()} Build for {name}", description='')

				embed.set_thumbnail(url=images['small'])

				logger.info(f"returning build information for <{name}> in embeded format")

				tier_string = roman_numeral[tier - 1]

				embed.description += f'**Tier {tier_string} {"Premium" if is_prem else ""} {nation_dictionary[nation]} {ship_types[ship_type]}**\n'

				footer_message = ""
				error_value_found = False
				if len(upgrades) and len(skills) and len(cmdr):
					# suggested upgrades
					if len(upgrades) > 0:
						m = ""
						i = 1
						for upgrade in upgrades:
							upgrade_name = "[Missing]"
							if upgrade == -1:
								# any thing
								upgrade_name = "Any"
							else:
								try:  # ew, nested try/catch
									if database_client is not None:
										query_result = database_client.mackbot_db.upgrade_list.find_one({"consumable_id": upgrade})
										if query_result is None:
											raise IndexError
										else:
											upgrade_name = query_result['name']
									else:
										upgrade_name = get_upgrade_data(upgrade)['name']
								except Exception as e:
									logger.info(f"Exception {type(e)} {e} in ship, listing upgrade {i}")
									error_value_found = True
									upgrade_name = upgrade + ":warning:"
							m += f'(Slot {i}) **' + upgrade_name + '**\n'
							i += 1
						embed.add_field(name='Suggested Upgrades', value=m, inline=False)
					else:
						embed.add_field(name='Suggested Upgrades', value="Coming Soon:tm:", inline=False)
					# suggested skills
					if len(skills) > 0:
						m = ""
						i = 1
						for s in skills:
							skill_name = "[Missing]"
							try:  # ew, nested try/catch
								if database_client is not None:
									query_result = database_client.mackbot_db.skill_list.find_one({"skill_id": s})
									if query_result is None:
										raise IndexError
									else:
										skill = query_result.copy()
								else:
									skill = skill_list[str(s)]
								skill_name = skill['name']
								col = skill['x'] + 1
								tier = skill['y'] + 1
							except Exception as e:
								logger.info(f"Exception {type(e)} {e} in ship, listing skill {i}")
								error_value_found = True
								skill_name = skill + ":warning:"
							m += f'(Col. {col}, Row {tier}) **' + skill_name + '**\n'
							i += 1
						embed.add_field(name='Suggested Cmdr. Skills', value=m, inline=False)
					else:
						embed.add_field(name='Suggested Cmdr. Skills', value="Coming Soon:tm:", inline=False)
					# suggested commander
					if cmdr != "":
						m = ""
						if cmdr == "*":
							m = "Any"
						else:
							try:
								m = get_commander_data(cmdr)[0]
							except Exception as e:
								logger.info(f"Exception {type(e)} {e} in ship, listing commander")
								error_value_found = True
								m = f"{cmdr}:warning:"
						# footer_message += "Suggested skills are listed in ascending acquiring order.\n"
						embed.add_field(name='Suggested Cmdr.', value=m)
					else:
						embed.add_field(name='Suggested Cmdr.', value="Coming Soon:tm:", inline=False)

					# show user error if there is any that is missed by data prepper
					if build_errors:
						m = "This build has the following errors:\n"
						for error in build_errors:
							error_string = ' '.join(BuildError(error).name.split("_")).title()
							m += f"{error_string}\n"
						embed.add_field(name=":warning: Warning! :warning: ", value=m, inline=False)

					footer_message += "mackbot ship build should be used as a base for your builds. Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.\n"
					footer_message += f"For image variant of this message, use [mackbot build [-i/--image] {user_ship_name}]\n"
					if build_errors:
						footer_message += f"This build has error that may affect this ship's performance. Please contact a mackbot developer.\n"
				else:
					m = "mackbot does not know any build for this ship :("
					embed.add_field(name=f'No known build', value=m, inline=False)
				error_footer_message = ""
				if error_value_found:
					error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact mackwafang#2071.\n"
				embed.set_footer(text=error_footer_message + footer_message)

			if not send_image_build:
				if multi_build_user_response:
					# response to user's selection of drop-down menu
					await multi_build_user_response.respond(embed=embed, ephemeral=False)
				else:
					await context.send(embed=embed)
			else:
				# send image
				if database_client is None:
					# getting from local ship build file
					build_image = builds[user_selected_build_id]['image']
				else:
					# dynamically create
					build_image = create_build_image(build_name, name, skills, upgrades, cmdr)
				build_image.save("temp.png")
				try:
					if multi_build_user_response:
						# response to user's selection of drop-down menu
						await multi_build_user_response.respond(file=File('temp.png'), ephemeral=False)
					else:
						await context.send(file=File('temp.png'))
					await context.send("__Note: mackbot ship build should be used as a base for your builds. Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.__")
				except Forbidden:
					await context.send("mackbot requires the **Send Attachment** feature for this feature.")
		except Exception as e:
			if type(e) == NoShipFound:
				# ship with specified name is not found, user might mistype ship name?
				closest_match = find_close_match_item(user_ship_name.lower(), "ship_list")
				embed = Embed(title=f"Ship {user_ship_name} is not understood.\n", description="")
				if closest_match:
					closest_match_string = closest_match[0].title()
					closest_match_string = f'\nDid you mean **{closest_match_string}**?'
					embed.description = closest_match_string
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expires in 10 seconds")
					await context.send(embed=embed)
					await correct_user_misspell(context, 'build', f"{'-i' if send_image_build else ''} {closest_match[0]}")
				else:
					await context.send(embed=embed)
			elif type(e) == NoBuildFound:
				# no build for this ship is found
				embed = Embed(title=f"Build for {name}", description='')
				embed.description = f"**Tier {list(roman_numeral.keys())[tier - 1]} {nation_dictionary[nation]} {ship_types[ship_type].title()}**"
				embed.set_thumbnail(url=images['small'])
				m = "mackbot does not know any build for this ship :("
				embed.add_field(name=f'No known build', value=m, inline=False)

				await context.send(embed=embed)
			else:
				logger.error(f"{type(e)}")
				traceback.print_exc()