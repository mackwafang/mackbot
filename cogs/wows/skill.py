import traceback

from discord import app_commands, Embed, Interaction
from discord.ext import commands

from mackbot.enums import COMMAND_INPUT_TYPE
from mackbot.exceptions import NoSkillFound, SkillTreeInvalid
from mackbot.utilities.correct_user_mispell import correct_user_misspell
from mackbot.utilities.find_close_match_item import find_close_match_item
from mackbot.utilities.game_data.game_data_finder import get_skill_data
from mackbot.utilities.logger import logger
from mackbot.constants import ICONS_EMOJI


class Skill(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="skill", description="Get information on a commander skill")
	@app_commands.describe(
		skill_name="Skill name"
	)
	async def skill(self, interaction: Interaction, skill_name: str):
		# get information on requested skill
		try:
			embed = Embed(title=f"{skill_name.title()}", description="")
			skill_data = get_skill_data(skill_name)
			for skill in skill_data:
				name = skill['name']
				tree = skill['tree']
				description = skill['description']
				effect = skill['effect']
				column = skill['x'] + 1
				tier = skill['y'] + 1
				category = skill['category']

				# embed.set_thumbnail(url=icon)
				m = f"Tier {tier} {category} Skill, Column {column}\n\n" \
				    f"{description}\n{effect}\n\n"
				embed.add_field(name=f"__{ICONS_EMOJI[tree]} {tree} Skill__", value=m, inline=False)

			await interaction.response.send_message(embed=embed)

		except Exception as e:
			logger.info(f"Exception in skill {type(e)}: {e}. No skill found for {skill_name}")
			traceback.print_exc()
			if type(e) == NoSkillFound:
				closest_match = find_close_match_item(skill_name, "skill_list")

				embed = Embed(title=f"Skill {skill_name} is not understood.\n", description="")
				if len(closest_match) > 0:
					embed.description += f'\nDid you mean **{closest_match[0]}**?'
					embed.description += "\n\nType \"y\" or \"yes\" to confirm."
					embed.set_footer(text="Response expires in 10 seconds")
				msg = await interaction.channel.send(embed=embed)
				await correct_user_misspell(self.bot, interaction, Skill, "skill", closest_match[0])
				await msg.delete()
			if type(e) == SkillTreeInvalid:
				embed = Embed(title=f"Skill tree is not understood.\n", description="")
				embed.description += f'\n{e}'
				await interaction.response.send_message.send(embed=embed)