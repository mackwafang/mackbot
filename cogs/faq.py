from discord import Embed
from discord.ext import commands

from scripts.utilities.bot_data import faq_data

class FAQ(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="faq", description="What is a mackbot?")
	async def faq(self, context: commands.Context):
		async with context.typing():
			embed = Embed(title="mackbot FAQ")
			for question, answer in faq_data['faq']:
				embed.add_field(name=question, value='\n'.join(answer), inline=False)
		await context.send(embed=embed)