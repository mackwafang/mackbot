import discord, traceback

from discord import app_commands, Interaction
from discord.ext import commands
from cogs.wows.bot_help import BotHelp
from mackbot.utilities.logger import logger
from mackbot.utilities.bot_data import command_list

class Listener(commands.Cog):
	def __init__(self, client: discord.Client, command_prefix: str):
		self.client = client
		self.command_prefix = command_prefix

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		# check for mackbot response testing by checking it only contains the ping
		if message.content == f"<@{self.client.application_id}>":
			logger.info(f"Checking response in {message.channel.name}...")
			m = ""
			permissions = message.channel.permissions_for(message.guild.me)
			missing_permission = [
				("Application Commands", not permissions.use_application_commands, "All commands"),
				("Embed Links", not permissions.embed_links, "All commands"),
				("Attach Files", not permissions.attach_files, "build"),
			]

			m += f"mackbot response in **{message.channel.name}**:\n"
			for permission_name, is_permission_missing, use_in in missing_permission:
				logger.info(f"{permission_name}: {not is_permission_missing}")
				m += f"**{permission_name}:** {':x:' if is_permission_missing else ':white_check_mark:'} (Use in: {use_in})\n"
			m += "\n"
			await message.channel.send(content=m)

	@commands.Cog.listener()
	async def on_ready(self):
		await self.client.change_presence(activity=discord.Game(self.command_prefix + ' help'))
		logger.info(f"Logged on as {self.client.user} (ID: {self.client.user.id})")

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