from traceback import print_exc
from asyncio.exceptions import TimeoutError, CancelledError
from discord import Client
from discord.ext.commands import Context

async def correct_user_misspell(client: Client, context: Context, command: str, *args: list[str]) -> None:
	"""
	Correct user's spelling mistake on ships on some commands

	Args:
		context (discord.ext.commands.Context): A Discord Context object
		command (string): The original command
		*args (list[string]): The original command's arguments

	Returns:
		None
	"""
	author = context.author
	def check(message):
		return author == message.author and message.content.lower() in ['y', 'yes']

	try:
		res = await client.wait_for('message', timeout=10, check=check)

		prefix_and_invoke = ' '.join(context.message.content.split()[:2])
		context.message.content = f"{prefix_and_invoke} {' '.join(args)}"
		await client.all_commands[command](context, *args)
	except Exception as e:
		if type(e) in (TimeoutError, CancelledError):
			pass
		else:
			print_exc()