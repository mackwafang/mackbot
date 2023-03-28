import traceback

from discord import app_commands, Embed
from discord.ext import commands

from mackbot.enums import COMMAND_INPUT_TYPE
from mackbot.exceptions import NoSkillFound, SkillTreeInvalid
from mackbot.utilities.correct_user_mispell import correct_user_misspell
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.game_data.game_data_finder import get_skill_data
from mackbot.utilities.logger import logger


class Skill(commands.Cog):
	def __init__(self, client):
		self.client = client

	@app_commands.command(name="skill", description="Get information on a commander skill")
	@app_commands.describe(
		skill_tree="Skill tree query. Accepts ship hull classification or ship type",
		skill_name="Skill name"
	)
	async def skill(self, context: commands.Context, skill_tree: str, skill_name: str):
		# get information on requested skill
		# message parse
		# check if *not* slash command,
		if context.clean_prefix != '/' or '[modified]' in context.message.content:
			args = context.message.content.split()[3:]
			if '[modified]' in context.message.content:
				args = args[:-1]
			args = ' '.join(args)
			input_type = COMMAND_INPUT_TYPE.CLI
		else:
			args = list(context.kwargs.values())
			input_type = COMMAND_INPUT_TYPE.SLASH
		try:
			# ship_class = args[0].lower()
			# skill_name = ''.join([i + ' ' for i in args[1:]])[:-1]  # message_string[message_string.rfind('-')+1:]

			# await context.typing()
			skill_data = get_skill_data(skill_tree, skill_name)
			name = skill_data['name']
			tree = skill_data['tree']
			description = skill_data['description']
			effect = skill_data['effect']
			column = skill_data['x'] + 1
			tier = skill_data['y'] + 1
			category = skill_data['category']
			embed = Embed(title=f"{name}", description="")
			# embed.set_thumbnail(url=icon)
			embed.description += f"**{tree} Skill**\n"
			embed.description += f"**Tier {tier} {category} Skill**, "
			embed.description += f"**Column {column}**"
			embed.add_field(name='Description', value=description, inline=False)
			embed.add_field(name='Effect', value=effect, inline=False)
			await context.send(embed=embed)

		except Exception as e:
			logger.info(f"Exception in skill {type(e)}: {e}")
			traceback.print_exc()
			if type(e) == NoSkillFound:
				closest_match = find_close_match_item(skill_name, "skill_list")

				embed = Embed(title=f"Skill {skill_name} is not understood.\n", description="")
				if len(closest_match) > 0:
					embed.description += f'\nDid you mean **{closest_match[0]}**?'
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expires in 10 seconds")
				await context.reply(embed=embed)
				await correct_user_misspell(self.client, context, 'skill', skill_tree, closest_match[0])
			if type(e) == SkillTreeInvalid:
				embed = Embed(title=f"Skill tree is not understood.\n", description="")
				embed.description += f'\n{e}'
				await context.send(embed=embed)