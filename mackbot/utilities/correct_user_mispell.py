from asyncio.exceptions import TimeoutError, CancelledError
from collections.abc import Callable

import discord
from discord import Client, app_commands
from discord.ext.commands import Context, Cog, Bot
from traceback import print_exc

async def correct_user_misspell(bot: Bot, interaction: discord.Interaction, cog: Cog, command: str, *args) -> None:
	"""
	Correct user's spelling mistake on ships on some commands

	Args:

	Returns:
		None
	"""
	author = interaction.user
	def check(message):
		return author == message.author and message.content.lower() in ['y', 'yes']

	try:
		res = await bot.wait_for('message', timeout=10, check=check)
		# interaction.message.content = f"{command_prefix} {command} {' '.join(args)} [modified]" # change cli inputs
		# await client.all_commands[command](interaction, *args)
		await getattr(bot.get_cog(cog.__name__), command).callback(cog, interaction, *args) # call command from cogs again
		await res.delete()
	except Exception as e:
		if type(e) in (TimeoutError, CancelledError):
			pass
		else:
			print_exc()