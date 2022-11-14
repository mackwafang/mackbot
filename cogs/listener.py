import discord, traceback

from discord import app_commands
from discord.ext import commands
from .bot_help import BotHelp
from scripts.utilities.logger import logger

class Listener(commands.Cog):
	def __init__(self, client: discord.Client, command_prefix: str):
		self.client = client
		self.command_prefix = command_prefix

	@commands.Cog.listener()
	async def on_ready(self):
		await self.client.change_presence(activity=discord.Game(self.command_prefix + ' help'))
		logger.info(f"Logged on as {self.client.user} (ID: {self.client.user.id})")

	@commands.Cog.listener()
	async def on_command(self, context):
		if context.author != self.client.user:  # this prevent bot from responding to itself
			query = ''.join([i + ' ' for i in context.message.content.split()[1:]])
			if context.clean_prefix == "/":
				query = f"/{context.command} {' '.join(str(v) for k, v in context.kwargs.items())}"
			from_server = context.guild if context.guild else "DM"
			logger.info("User [{} ({})] via [{}] queried: {}".format(context.author, context.author.id, from_server, query))

	@commands.Cog.listener()
	async def on_command_error(self, context: commands.Context, error: commands.errors):
		logger.warning(f"Command failed: {error}")
		if type(error) == commands.errors.MissingRequiredArgument:
			# send help message when missing required argument
			await BotHelp.custom_help(BotHelp, context, context.invoked_with)
		elif type(error) == commands.errors.CommandNotFound:
			await context.send(f"Command is not understood.\n")
			logger.warning(f"{context.command} is not a command")
		else:
			await context.send("An internal error as occurred.")
			traceback.print_exc()

	@commands.Cog.listener()
	async def on_guild_join(self, guild: discord.Guild):
		logger.info(f"Joined server {guild.name} ({guild.id})")

	@commands.Cog.listener()
	async def on_guild_remove(self, guild: discord.Guild):
		logger.info(f"Left server {guild.name} ({guild.id})")