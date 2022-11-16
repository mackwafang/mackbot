import inflect

from discord import Embed
from discord.ext import commands
from mackbot.constants import EMPTY_LENGTH_CHAR
from mackbot.utilities.game_data.warships_data import database_client
from mackbot.utilities.bot_data import discord_invite_url
from mackbot.utilities.to_plural import to_plural

grammar = inflect.engine()

class AboutBot(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="about", description="About mackbot")
	async def about_bot(self, context: commands.Context):
		query = list(database_client.mackbot_db.mackbot_info.find({}).sort("VERSION_TIME", -1))
		embed = Embed(title="About mackbot")

		embed.add_field(name=f"Currently deployed in {to_plural('server', len(self.client.guilds))}", value=EMPTY_LENGTH_CHAR)

		if query:
			m = ""
			m += f"mackbot v{query[0]['MACKBOT_VERSION']}\n"
			m += f"mackbot web v{query[0]['MACKBOT_WEB_VERSION']}\n"
			embed.add_field(name="Version", value=m, inline=False)

		m = ""
		m += f"Please visit the **mackbot's testing ground** server {discord_invite_url}"
		embed.add_field(name="Support", value=m, inline=False)

		m = ""
		m += "All copyrighted materials owned by Wargaming.net. All rights reserved.\n"
		m += "All other contents are available under the MIT license.\n"
		embed.add_field(name="Legal", value=m, inline=False)
		await context.send(embed=embed)