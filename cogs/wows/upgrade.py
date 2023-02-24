import traceback

from discord import app_commands, Embed
from discord.ext import commands

from mackbot.enums import COMMAND_INPUT_TYPE
from mackbot.exceptions import NoUpgradeFound
from mackbot.constants import UPGRADE_MODIFIER_DESC
from mackbot.utilities.correct_user_mispell import correct_user_misspell
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.game_data.game_data_finder import get_upgrade_data, get_legendary_upgrade_by_ship_name
from mackbot.utilities.logger import logger
from mackbot.utilities.discord.items_autocomplete import auto_complete_upgrades_name

class Upgrade(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="upgrade", description="Get information on an upgrade")
	@app_commands.describe(
		upgrade_name="Upgrade name, upgrade abbreviation, or ship name (applicable to ships with unique upgrades)."
	)
	@app_commands.autocomplete(upgrade_name=auto_complete_upgrades_name)
	async def upgrade(self, context: commands.Context, upgrade_name: str):
		logger.info(f"Received {upgrade_name}")
		# check if *not* slash command,
		if context.clean_prefix != '/' or '[modified]' in context.message.content:
			args = context.message.content.split()[2:]
			if '[modified]' in context.message.content:
				args = args[:-1]
			input_type = COMMAND_INPUT_TYPE.CLI
		else:
			args = list(context.kwargs.values())
			input_type = COMMAND_INPUT_TYPE.SLASH
		upgrade_name = ' '.join(args)

		# getting appropriate search function
		try:
			# does user provide upgrade name?
			get_upgrade_data(upgrade_name)
			search_func = get_upgrade_data
		except NoUpgradeFound:
			# does user provide ship name, probably?
			get_legendary_upgrade_by_ship_name(upgrade_name)
			search_func = get_legendary_upgrade_by_ship_name

		try:
			# assuming that user provided the correct upgrade
			logger.info(f'sending message for upgrade <{upgrade_name}>')
			output = search_func(upgrade_name)
			profile = output['profile']
			name = output['name']
			image = output['image']
			price_credit = output['price_credit']
			description = output['description']
			is_special = output['is_special']
			ship_restriction = output['ship_restriction']
			nation_restriction = output['nation_restriction']
			tier_restriction = output['tier_restriction']
			type_restriction = output['type_restriction']
			slot = output['slot']
			special_restriction = output['additional_restriction']

			embed_title = 'Ship Upgrade'
			if is_special == 'Unique':
				embed_title = "Legendary Ship Upgrade"
			elif is_special == 'Coal':
				embed_title = "Coal Ship Upgrade"

			embed = Embed(title=embed_title, description="")
			embed.set_thumbnail(url=image)
			# get server emoji
			if context.guild is not None:
				server_emojis = context.guild.emojis
			else:
				server_emojis = []

			embed.description += f"**{name}**\n"
			embed.description += f"**Slot {slot}**\n"
			if len(description.split()) > 0:
				embed.add_field(name='Description', value=description, inline=False)

			if len(profile) > 0:
				m = ""
				for effect in profile:
					modifier_string_data = UPGRADE_MODIFIER_DESC[effect]
					value = profile[effect]
					m += modifier_string_data['description'] + ": "
					if modifier_string_data['unit'] != "%":
						# not percentage modifier
						m += f"{value:2.0f}{modifier_string_data['unit']}\n"
					else:
						if type(value) == dict:
							value = list(value.values())[0]
						s = '+' if (value - 1) > 0 else ''
						m += f"{s}{value - 1:2.{0 if (value*100).is_integer() else 1}%}\n"

				embed.add_field(name='Effect', value=m, inline=False)
			else:
				logger.info("effect field empty")

			if not is_special == 'Unique':
				if len(type_restriction) > 0:
					# find the server emoji id for this emoji id
					if len(server_emojis) == 0:
						m = ''.join([i.title() + ', ' for i in sorted(type_restriction)])[:-2]
					else:
						m = ''
						for t in type_restriction:
							t = 'carrier' if t == 'Aircraft Carrier' else t
							for e in server_emojis:
								if t.lower() == e.name:
									m += str(e) + ' '
									break
						else:
							type_icon = ""
				else:
					m = "All types"
				embed.add_field(name="Ship Type", value=m)

				if len(tier_restriction) > 0:
					m = ''.join([str(i) + ', ' for i in tier_restriction])[:-2]
				else:
					m = "All tiers"
				embed.add_field(name="Tier", value=m)

				if len(nation_restriction) > 0:
					m = ''.join([i + ', ' for i in sorted(nation_restriction)])[:-2]
				else:
					m = 'All nations'
				embed.add_field(name="Nation", value=m)

				if len(ship_restriction) > 0:
					m = ''.join([i + ', ' for i in sorted(ship_restriction[:10])])[:-2]
					if len(ship_restriction) > 10:
						m += "...and more"
					if len(m) > 0:
						ship_restrict_title = {
							'': "Also Found On",
							'Coal': "Also Found On",
						}[is_special]
						embed.add_field(name=ship_restrict_title, value=m)
					else:
						logger.warning('Ships field is empty')
			if len(special_restriction) > 0:
				m = special_restriction
				if len(m) > 0:
					embed.add_field(name="Additonal Requirements", value=m)
				else:
					logger.warning("Additional requirements field empty")
			if price_credit > 0 and len(is_special) == 0:
				embed.add_field(name='Price (Credit)', value=f'{price_credit:,}')
			await context.send(embed=embed)
		except Exception as e:
			logger.info(f"Exception in upgrade: {type(e)} {e}")
			traceback.print_exc()

			closest_match = find_close_match_item(upgrade_name.lower(), "upgrade_list")

			embed = Embed(title=f"Upgrade **{upgrade_name}** is not understood.\n", description="")
			if len(closest_match) > 0:
				embed.description += f'\nDid you mean **{closest_match[0]}**?'
				embed.description += "\n\nType \"y\" or \"yes\" to confirm."
				embed.set_footer(text="Response expires in 10 seconds")
			await context.send(embed=embed)
			await correct_user_misspell(self.client, context, 'upgrade', closest_match[0])
