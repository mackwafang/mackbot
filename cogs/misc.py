import asyncio
import traceback
from random import sample, randint
from typing import Optional

from discord import app_commands, Embed
from discord.ext import commands

from cogs import BotHelp
from scripts.mackbot_constants import GOOD_BOT_MESSAGES, EXCHANGE_RATE_DOUB_TO_DOLLAR, WOWS_REALMS
from scripts.utilities.bot_data import hottake_strings, bot_invite_url, discord_invite_url
from scripts.utilities.compile_bot_help import help_dictionary
from scripts.utilities.logger import logger


class Misc(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="goodbot", description="Compliment mackbot")
	async def goodbot(self, context: commands.Context):
		# good bot
		logger.info(f"send reply message for goodbot")
		await context.send(sample(GOOD_BOT_MESSAGES, 1)[0])  # block until message is sent

	@commands.hybrid_command(name="feedback", description="Provide feedback to the developer")
	async def feedback(self, context: commands.Context):
		logger.info("send feedback link")
		await context.send(f"Got a feedback about mackbot? Submit a feedback form here!\nhttps://forms.gle/Lqm9bU5wbtNkpKSn7")

	@commands.hybrid_command(name="doubloons", description="Converts doubloons to USD, vice versa.")
	@app_commands.describe(
		value="The doubloon value for conversion to dollars. If is_dollar is filled, this value is converted to USD instead.",
		is_dollar="Add the word \"dollar\" or \"$\" to convert value into dollar value"
	)
	async def doubloons(self, context: commands.Context, value: int, is_dollar: Optional[str] = ""):
		# get conversion between doubloons and usd and vice versa
		doub = 0
		try:
			if is_dollar:
				# check reverse conversion
				# dollars to doubloons
				if is_dollar.lower() in ['dollars', '$']:
					dollar = float(value)

					def dollar_formula(x):
						return x * EXCHANGE_RATE_DOUB_TO_DOLLAR

					logger.info(f"converting {dollar} dollars -> doubloons")
					embed = Embed(title="Doubloon Conversion (Dollars -> Doubloons)")
					embed.add_field(name=f"Requested Dollars", value=f"{dollar:0.2f}$")
					embed.add_field(name=f"Doubloons", value=f"Approx. {dollar_formula(dollar):0.0f} Doubloons")
				else:
					embed = Embed(
						title="Doubloon Conversion Error",
						description=f"Value {is_dollar} is not a value optional argument"
					)
			else:
				# doubloon to dollars
				doub = int(value)
				value_exceed = not (500 <= doub <= 100000)

				def doub_formula(x):
					return x / EXCHANGE_RATE_DOUB_TO_DOLLAR

				logger.info(f"converting {doub} doubloons -> dollars")
				embed = Embed(title="Doubloon Conversion (Doubloons -> Dollars)")
				embed.add_field(name=f"Requested Doubloons", value=f"{doub} Doubloons")
				embed.add_field(name=f"Price: ", value=f"{doub_formula(doub):0.2f}$")
				footer_message = f"Current exchange rate: {EXCHANGE_RATE_DOUB_TO_DOLLAR} Doubloons : 1 USD"
				if value_exceed:
					footer_message += "\n:warning: You cannot buy the requested doubloons."
				embed.set_footer(text=footer_message)

			await context.send(embed=embed)
		except Exception as e:
			logger.info(f"Exception {type(e)} {e}")
			if type(e) == TypeError:
				await context.send(f"Value **{doub}** is not a number.")
			else:
				await context.send(f"An internal error has occured.")
				traceback.print_exc()

	@commands.hybrid_command(name="code", description="Generate WoWS bonus code links")
	@app_commands.rename(args="codes")
	@app_commands.describe(args="WoWS codes to generate link")
	async def code(self, context, args: str):
		if context.clean_prefix != '/':
			args = ' '.join(context.message.content.split()[2:])

		# find region
		if args.split()[0].lower() in WOWS_REALMS:
			region = args.split()[0].lower()
			has_region_option = True
		else:
			region = 'na'
			has_region_option = False

		if len(args) == 0 or (has_region_option and len(args) == 1):
			await BotHelp.custom_help(BotHelp, context, "code")
		else:
			s = ""

			for c in args.split()[1:] if has_region_option else args.split():
				s += f"**({region.upper()}) {c.upper()}** https://{region}.wargaming.net/shop/redeem/?bonus_mode={c.upper()}\n"
				logger.info(f"returned a wargaming bonus code link with code {c}")
			await context.send(s)

	@commands.hybrid_command(name="hottake", description="Give a WoWS hottake")
	async def hottake(self, context: commands.Context):
		logger.info("sending a hottake")
		await context.send('I tell people that ' + sample(hottake_strings, 1)[0])
		if randint(0, 9) == 0:
			await asyncio.sleep(2)
			await self.purpose(context)

	async def purpose(self, context: commands.Context):
		author = context.author
		await context.send(f"{author.mention}, what is my purpose?")

		def check(message):
			return author == message.author and message.content.lower().startswith("you") and len(message.content[3:]) > 0

		message = await self.client.wait_for('message', timeout=30, check=check)
		await context.send("Oh my god...")

	@commands.hybrid_command(name="web", description="Get the link to mackbot's web application")
	async def web(self, context: commands.Context):
		await context.send("**mackbot's web application URL:\nhttps://mackbot-web.herokuapp.com/**")

	@commands.hybrid_command(name="invite", description="Get a Discord invite link to get mackbot to your server.")
	async def invite(self, context: commands.Context):
		await context.send(bot_invite_url)

	@commands.hybrid_command(name="commands", description="Get list of commands")
	async def cmd(self, context: commands.Context):
		embed = Embed(title="mackbot commands")

		m = ""
		for command in sorted([c.name for c in self.client.commands]):
			m += f"**{command}:** {help_dictionary[command]['brief']}\n"
		embed.add_field(name="Command (Description)", value=m)
		embed.set_footer(text="For usage on any commands, use mackbot help <command>")

		await context.send(embed=embed)

	@commands.hybrid_command(name="support", description="Get mackbot's support Discord server")
	async def support(self, context: commands.Context):
		await context.send(discord_invite_url)