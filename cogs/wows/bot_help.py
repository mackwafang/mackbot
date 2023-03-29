import discord, re

from typing import Optional
from discord import app_commands, Interaction
from discord.ext import commands
from mackbot.utilities.compile_bot_help import *
from mackbot.constants import ICONS_EMOJI, EMPTY_LENGTH_CHAR
from mackbot.utilities.bot_data import command_list, command_prefix

class BotHelp(commands.Cog):
	def __init__(self, client):
		self.client = client

	@app_commands.command(name="help", description="Get help on a mackbot command or a WoWS terminology")
	@app_commands.describe(help_key="Command or WoWS terminology")
	async def custom_help(self, interaction: Interaction, help_key: Optional[str]=""):
		help_key = help_key.lower()
		logger.info(f"can i haz halp for {help_key}")
		if len(help_key):
			if help_key in help_dictionary_index:
				# look for help content and tries to find its index
				help_content = help_dictionary[help_dictionary_index[help_key]]
				if help_key.split()[0] in command_list:
					embed = discord.Embed(title=f"The {help_key} command")

					embed.add_field(name="Usage", value=f"/{help_key} {help_content['usage']}", inline=False)
					embed.add_field(name="Description", value='\n'.join(i for i in help_content['description']), inline=False)
					if "options" in help_content:
						embed.add_field(name="Options", value='\n'.join(f"**{k}**: {chr(10).join(v) if type(v) == list else v}" for k, v in help_content['options'].items()), inline=False)

					await interaction.response.send_message(embed=embed)
				else:
					# a help on terminology
					embed = discord.Embed(title=help_content['title'])
					pat = re.compile('\$(' + '|'.join(ICONS_EMOJI.keys()) + ')')

					description_string = '\n'.join(help_content['description'])
					description_string = pat.sub(lambda x: ICONS_EMOJI[x.group(0)[1:]], description_string)

					# split "paragraphs" that are split by 2 newlines into fields
					for p, content in enumerate(description_string.split("\n\n")):
						embed.add_field(name="Description" if p == 0 else EMPTY_LENGTH_CHAR, value=content, inline=False)

					if help_content['related_commands']:
						embed.add_field(name="Related mackbot Commands", value='\n'.join(f"{command_prefix} {i}" for i in help_content['related_commands']), inline=False)
					if help_content['related_terms']:
						embed.add_field(name="Related Terms", value=', '.join(i for i in help_content['related_terms']), inline=False)

					await interaction.response.send_message(embed=embed)
			else:
				await interaction.response.send_message(f"The term {help_key} is not understood.")
		else:

			help_content = help_dictionary[help_dictionary_index["help"]]
			embed = discord.Embed(title=f"The help command")

			embed.add_field(name="Usage", value=f"{command_prefix} help {help_content['usage']}", inline=False)
			embed.add_field(name="Description", value='\n'.join(i for i in help_content['description']), inline=False)
			embed.add_field(name="Commands", value='\n'.join(f"**{k}**: {v['brief']}" for k, v in sorted(help_dictionary.items()) if k in command_list), inline=False)
			await interaction.response.send_message(embed=embed)
