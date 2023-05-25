import discord, traceback

from discord import app_commands, Interaction
from discord.ext import commands
from cogs.wows.bot_help import BotHelp
from mackbot.utilities.logger import logger
from mackbot.utilities.bot_data import command_list, discord_invite_url, bot_invite_url, command_prefix

class Listener(commands.Cog):
	def __init__(self, client: discord.Client, command_prefix: str):
		self.client = client
		self.command_prefix = command_prefix

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		# check for mackbot response testing by checking it only contains the ping
		if message.content == f"<@{self.client.application_id}>":
			logger.info(f"Checking response in {message.guild.name}/{message.channel.name}...")
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
		else:
			args = message.content.split()
			if args:
				if args[0] in command_prefix and args[1] in command_list:
					logger.info("User [{} ({})] via [{}] queried: {}".format(message.author, message.author.id, message.guild, message.content))



	@commands.Cog.listener()
	async def on_app_command_completion(self, interaction: discord.Interaction, command):
		logger.info(f"user {interaction.user} ({interaction.user.id}) at "
		            f"[{interaction.guild.name[:25]:<25} ({interaction.guild_id}), {interaction.channel.name[:25]:<25} ({interaction.channel_id})] "
		            f"queried {interaction.data}"
		)

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
			if context.clean_prefix == self.command_prefix:
				if context.message.content.split():
					if context.message.content.split()[1] in command_list:
						embed = discord.Embed(
							title="CLI Commands has been Deprecated!",
							description=f"CLI commands has been deprecated since April 1st, 2023. please use **/{context.message.content.split()[1]}** instead!\n"
							            f"If slash command is not working properly, please try the following:\n"
						)

						embed.add_field(
							name=f":one: __**Server Administrations: To manually enable (or disable) mackbot's slash commands:**__\n",
							value=f":regional_indicator_a: Go to Server Settings -> Integrations -> mackbot -> Manage\n"
							      f":regional_indicator_b: Under Roles & Members, enable \@everyone or specific roles\n"
							      f":regional_indicator_c: Optional: Enable specific channels.\n",
							inline=False,
						)
						embed.add_field(
							name=f":two: Reinvite mackbot\n",
							value=f"mackbot's invite url: {bot_invite_url}",
							inline=False,
						)

						embed.set_footer(text=f"If everything else fails, please visit the support server at {discord_invite_url}.")
						await context.send(embed=embed)
						logger.warning(f"User invoked CLI command")
			else:
				await context.send(f"Command is not understood.\n")
				logger.warning(f"{context.command} is not a command")
		else:
			await context.send("An internal error as occurred.")
			traceback.print_exc()

	@commands.Cog.listener()
	async def on_guild_join(self, guild: discord.Guild):
		logger.info(f"Joined server [{guild.name}] ({guild.id})")

	@commands.Cog.listener()
	async def on_guild_remove(self, guild: discord.Guild):
		logger.info(f"Left server [{guild.name}] ({guild.id})")