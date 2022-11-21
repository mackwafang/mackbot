import discord, asyncio
from discord.ext import commands
from mackbot.utilities.game_data.game_data_finder import *
from mackbot.utilities.bot_data import *
from mackbot.utilities.compile_bot_help import compile_help_strings
from cogs import *

class Mackbot(commands.Bot):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	async def setup_hook(self) -> None:
		await self.tree.sync()


# define bot stuff
cmd_sep = ' '
command_prefix += cmd_sep
bot_intents = discord.Intents().default()
bot_intents.members = True
bot_intents.typing = True
bot_intents.message_content = True

mackbot = Mackbot(command_prefix=command_prefix, intents=bot_intents, help_command=None)

def post_process() -> None:
	compile_help_strings()

async def main():
	# load some stuff
	post_process()
	if not os.path.isdir("logs"):
		os.mkdir("logs")

	if database_client is None:
		load_ship_builds()

	await mackbot.load_extension("mackbot.misc_commands.wtn")
	await mackbot.add_cog(Listener(mackbot, command_prefix))
	for cog in BOT_COGS:
		await mackbot.add_cog(cog(mackbot))


if __name__ == '__main__':
	asyncio.run(main())
	mackbot.run(bot_token)

	logger.info("kill switch detected")
	# write clan history file
	with open(clan_history_file_path, 'wb') as f:
		pickle.dump(clan_history, f)
	logger.info(f"Wrote {clan_history_file_path}")