import asyncio
import traceback
from random import sample, randint
from typing import Optional

from discord import app_commands, Embed, Interaction
from discord.ext import commands

from cogs import BotHelp
from mackbot.constants import GOOD_BOT_MESSAGES, EXCHANGE_RATE_DOUB_TO_DOLLAR, WOWS_REALMS
from mackbot.utilities.bot_data import hottake_strings, bot_invite_url, discord_invite_url
from mackbot.utilities.compile_bot_help import help_dictionary
from mackbot.utilities.discord.formatting import number_separator
from mackbot.utilities.logger import logger

class Misc(commands.Cog):
	def __init__(self, client):
		self.client = client

	@app_commands.command(name="goodbot", description="Compliment mackbot")
	async def goodbot(self, interaction: Interaction):
		# good bot
		logger.info(f"send reply message for goodbot")
		await interaction.response.send_message(sample(GOOD_BOT_MESSAGES, 1)[0])  # block until message is sent

	@app_commands.command(name="feedback", description="Provide feedback to the developer")
	async def feedback(self, interaction: Interaction):
		logger.info("send feedback link")
		await interaction.response.send_message(f"Got a feedback about mackbot? Submit a feedback form here!\nhttps://forms.gle/Lqm9bU5wbtNkpKSn7")

	@app_commands.command(name="doubloons", description="Converts doubloons to USD, vice versa.")
	@app_commands.describe(
		value="The doubloon value for conversion to dollars.",
		is_dollar="Set True to indicate to convert USD -> Dollars"
	)
	async def doubloons(self, interaction: Interaction, value: int, is_dollar:Optional[bool]=False):
		# get conversion between doubloons and usd and vice versa
		doub = 0
		try:
			# check reverse conversion
			# dollars to doubloons
			if is_dollar:
				dollar = float(value)

				def dollar_formula(x):
					return x * EXCHANGE_RATE_DOUB_TO_DOLLAR

				logger.info(f"converting {dollar} dollars -> doubloons")
				embed = Embed(description="## Doubloon Conversion (Dollars -> Doubloons)")
				embed.add_field(name=f"Requested Dollars", value=f"{number_separator(dollar, '.2f')}$")
				embed.add_field(name=f"Doubloons", value=f"Approx. {number_separator(dollar_formula(dollar), '.0f')} Doubloons")
			else:
				# doubloon to dollars
				doub = int(value)
				value_exceed = not (500 <= doub <= 100000)

				def doub_formula(x):
					return x / EXCHANGE_RATE_DOUB_TO_DOLLAR

				logger.info(f"converting {doub} doubloons -> dollars")
				embed = Embed(description="## Doubloon Conversion (Doubloons -> Dollars)")
				embed.add_field(name=f"Requested Doubloons", value=f"{number_separator(doub, '.0f')} Doubloons")
				embed.add_field(name=f"Price: ", value=f"{number_separator(doub_formula(doub), '.2f')}$")
				footer_message = f"Current exchange rate: {EXCHANGE_RATE_DOUB_TO_DOLLAR} Doubloons : 1 USD"
				if value_exceed:
					footer_message += "\n:warning: You cannot buy the requested doubloons."
				embed.set_footer(text=footer_message)

			await interaction.response.send_message(embed=embed)
		except Exception as e:
			logger.info(f"Exception {type(e)} {e}")
			if type(e) == TypeError:
				await interaction.response.send_message(f"Value **{doub}** is not a number.")
			else:
				await interaction.response.send_message(f"An internal error has occured.")
				traceback.print_exc()

	@app_commands.command(name="code", description="Generate WoWS bonus code links")
	@app_commands.describe(
		codes="WoWS codes to generate link, multiple links should be separated by space",
		region="Change region to the correct URL. Defaults to NA",
	)
	async def code(self, interaction: Interaction, codes: str, region:Optional[str]='na'):
		s = ""

		for c in codes.split():
			s += f"**({region.upper()}) {c.upper()}** https://{region}.wargaming.net/shop/redeem/?bonus_mode={c.upper()}\n"
			logger.info(f"returned a wargaming bonus code link with code {c}")
		await interaction.response.send_message(s)

	@app_commands.command(name="hottake", description="Give a WoWS hottake")
	async def hottake(self, interaction: Interaction):
		logger.info("sending a hottake")
		await interaction.response.send_message('I tell people that ' + sample(hottake_strings, 1)[0])
		if randint(0, 9) == 0:
			await asyncio.sleep(6)
			await self.purpose(interaction)

	async def purpose(self, interaction: Interaction):
		author = interaction.user
		await interaction.channel.send(f"{author.mention}, what is my purpose?")

		def check(message):
			return author == message.author and message.content.lower().startswith("you") and len(message.content[3:]) > 0

		message = await self.client.wait_for('message', timeout=30, check=check)
		await interaction.channel.send("Oh my god...")

	@app_commands.command(name="web", description="Get the link to mackbot's web application")
	async def web(self, interaction: Interaction):
		await interaction.response.send_message("**~~mackbot's web application URL:\nhttps://mackbot-web.herokuapp.com/~~**")

	@app_commands.command(name="invite", description="Get a Discord invite link to get mackbot to your server.")
	async def invite(self, interaction: Interaction):
		await interaction.response.send_message(bot_invite_url)

	@app_commands.command(name="support", description="Get mackbot's support Discord server")
	async def support(self, interaction: Interaction):
		await interaction.response.send_message(discord_invite_url)