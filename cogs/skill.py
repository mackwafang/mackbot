import traceback

from discord import app_commands, Embed
from discord.ext import commands

from scripts.mackbot_exceptions import NoSkillFound, SkillTreeInvalid
from scripts.utilities.correct_user_mispell import correct_user_misspell
from scripts.utilities.find_close_match_item import find_close_match_item
from scripts.utilities.game_data.game_data_finder import get_skill_data
from scripts.utilities.logger import logger


class Skill(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="skill", description="Get information on a commander skill")
	@app_commands.describe(
		skill_tree="Skill tree query. Accepts ship hull classification or ship type",
		skill_name="Skill name"
	)
	async def skill(self, context: commands.Context, skill_tree: str, skill_name: str):
		# get information on requested skill
		# message parse
		if context.clean_prefix != '/':
			skill_name = ' '.join(context.message.content.split()[3:])

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
				await correct_user_misspell(context, 'skill', skill_tree, closest_match[0])
			if type(e) == SkillTreeInvalid:
				embed = Embed(title=f"Skill tree is not understood.\n", description="")
				embed.description += f'\n{e}'
				await context.send(embed=embed)