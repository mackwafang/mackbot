from discord import Embed, app_commands, Interaction
from discord.ext import commands

from mackbot.utilities.bot_data import faq_data

class FAQ(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="faq", description="What is a mackbot?")
	async def faq(self, interaction: Interaction):
		async with interaction.channel.typing():
			embed = Embed(title="mackbot FAQ")
			for item in faq_data:
				question, answer = item.values()
				embed.add_field(name=f":grey_question: {question}", value='\n'.join(answer), inline=False)
		await interaction.response.send_message(embed=embed)