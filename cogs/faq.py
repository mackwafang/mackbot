from discord import Embed
from discord.ext import commands
from scripts.utilities.game_data.warships_data import database_client


class FAQ(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="faq", description="What is a mackbot?")
	async def faq(self, context: commands.Context):
		async with context.typing():
			embed = Embed(title="mackbot FAQ")
			embed.add_field(name="**[Who created mackbot?]**", value="mackbot is created by mackwafang#2071, he plays way too much CV.", inline=False)
			embed.add_field(name="**[Why is it *mackbot* called *mackbot*?]**", value="Originally, mackbot was called buildbot. Until a clan member suggested that I (mackwafang#2071) should name it mackbot because I was its sole creator.", inline=False)
			embed.add_field(name="**[What can mackbot do?]**",
			                value="Mackbot can:"
			                      "Gives basic warship builds (via the **build** command)\n"
			                      "- Gives warship information (via the **ship** command)\n"
				                  "- Gives hot takes (via the **hottake** command)\n"
				                  "- And more!\n",
			                inline=False)
			embed.add_field(name="**[Where does mackbot get its builds?]**",
			                value="mackbot's ship builds are gathered from WoWS community driven sources.\n"
			                      "In particular, mackbot's builds are gathered from Yurra et al. and is found at this link: https://docs.google.com/document/d/1XfsIIbyORQAxgOE-ao_nVSP8_fpa1igg0t48pXZFIu0/edit.\n",
			                inline=False)
		await context.send(embed=embed)