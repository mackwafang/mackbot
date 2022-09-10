import traceback, discord, logging, os, time

from logging.handlers import RotatingFileHandler
from discord.ext import commands
from random import randint, sample

# logger stuff
class LogFilterBlacklist(logging.Filter):
	def __init__(self, *blacklist):
		self.blacklist = [i for i in blacklist]

	def filter(self, record):
		return not any(i in record.getMessage() for i in self.blacklist)

# log settings
if not os.path.exists(os.path.join(os.getcwd(), "logs")):
	os.mkdir(os.path.join(os.getcwd(), "logs"))

LOG_FILE_NAME = os.path.join(os.getcwd(), 'logs', f'mackbot_{time.strftime("%m_%d_%Y", time.localtime())}.log')
handler = RotatingFileHandler(LOG_FILE_NAME, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8', delay=0)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] [%(name)-8s] [%(levelname)-5s] %(message)s')

handler.setFormatter(formatter)
handler.addFilter(LogFilterBlacklist("RESUME", "RESUMED"))
stream_handler.setFormatter(formatter)
stream_handler.addFilter(LogFilterBlacklist("RESUME", "RESUMED"))

logger = logging.getLogger("Wontonlogy")
logger.addHandler(handler)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

EMPTY_LENGTH_CHAR = '\u200b'
NEXT_MINE_TIME_DELAY = 12 * 60 * 60
WONTON_CAP = 500000
WONTON_GIF_URL = (
	"https://c.tenor.com/opiDAQ_TFrsAAAAC/dip%E6%B2%BE%E9%86%AC.gif",
	"https://c.tenor.com/wn_cso2tCq8AAAAd/eating-dumplings.gif",
	"https://c.tenor.com/rye5tgag5PwAAAAC/dumpling-food-porn.gif"
)

def to_plural(str: str, count: int) -> str:
	if str[-1].lower() == 'y':
		return f"{count} {str[:-1] + 'ies'}"
	elif str[-1].lower() == 'o':
		return f"{count} {str[:-1] + 'es'}"
	else:
		return f"{count} {str + 's'}"

def to_minutes(seconds):
	return seconds * 60

async def cook(context: commands.Context, db):
	if db is None:
		# can't connect to db, can't use
		embed = discord.Embed(
			title="Cannot connect to mackbot's database",
			description="We apologize for the inconvenience and will have this issue fixed soon (シ_ _)シ"
		)
		await context.send(embed=embed)
	else:
		try:
			author = context.author
			query_result = db.wtn_wallet.find_one({"user": author.id})

			wonton_image_file = None
			add_wonton = randint(0, 100) < 5
			add_wantan = (randint(0, 100) < 5) and add_wonton
			coins_gained = (5 + randint(1, 5)) * (2 if add_wonton else 1) * (2 if add_wantan else 1)

			current_time = time.time()
			embed = discord.Embed()
			m = ""

			if query_result is None:
				# new user!
				logger.info("New wontologist!")
				next_mine_time = int(current_time + NEXT_MINE_TIME_DELAY) # posix time
				db.wtn_wallet.insert_one({
					"user": author.id,
					"coins": coins_gained,
					"next_mine_time": next_mine_time
				})
				embed.title = "Welcome to Wontology"
				embed.description = "Where the wontons are made up and the usage doesn't matter."
				embed.set_image(url=sample(WONTON_GIF_URL, 1)[0])
				m += f"**You cooked {coins_gained} wonton**\n"
			else:
				# returning user
				next_mine_time = query_result['next_mine_time'] # convert posix time back to datetime
				seconds_until_next_mine = next_mine_time - current_time
				if seconds_until_next_mine <= 0:
					# user can mine again, cooldown is lifted
					if query_result['coins'] < WONTON_CAP:
						logger.info(f"Returning wontologist, made {to_plural('wonton', coins_gained)}")
						db.wtn_wallet.update_one({"user": author.id}, {
							"$set": {
								"coins": query_result['coins'] + coins_gained,
								"next_mine_time": int(current_time + NEXT_MINE_TIME_DELAY)
							}
						})
						embed.title = "**Wontons made!**\n"
						m += f"**{author.mention} cooked {to_plural('wonton', coins_gained)}**\n"
						m += f"**You have {to_plural('wonton', query_result['coins'] + coins_gained)}**\n"

						if add_wonton:
							wonton_image_file = discord.File(os.path.join(os.getcwd(), "data", "wonton", "wonton.png"), filename="image.png")
							embed.set_image(url="attachment://image.png")
							embed.title = "You have found the blessed wonton!"
							embed.description = "Your wonton gain doubled!"

							if add_wantan:
								wonton_image_file = discord.File(os.path.join(os.getcwd(), "data", "wonton", "wantan.png"), filename="image.png")
								embed.set_image(url="attachment://image.png")
								embed.title = "You have found the accursed wantan!"
								embed.description = "Your wonton gain quadrupled!"
								logger.info("Cursed wantan found")
							else:
								logger.info("Blessed wonton found")
						else:
							embed.set_image(url=sample(WONTON_GIF_URL, 1)[0])
					else:
						embed.title = "**Wontons full!**\n"
						m += f"**You have {to_plural('wonton', WONTON_CAP)}**\n"
				else:
					# nope, can't mine yet
					time_left = abs(seconds_until_next_mine)
					logger.info(f"Returning wontologist, cook cooldown: {time_left:2.0f}s")
					embed.title = "**You can't cook yet!**\n"
					m += f"Time left: " \
					     f"{time_left // 3600:1.0f}h " \
					     f"{(time_left % 3600) // 60:2.0f}m " \
					     f"{time_left % 60:02.0f}s"

			embed.add_field(name=EMPTY_LENGTH_CHAR, value=m)
			await context.send(file=wonton_image_file, embed=embed)
		except Exception as e:
			traceback.print_exc()

async def wonton_count(context: commands.Context, db):
	if db is None:
		# can't connect to db, can't use
		embed = discord.Embed(
			title="Cannot connect to mackbot's database",
			description="We apologize for the inconvenience and will have this issue fixed soon (シ_ _)シ"
		)
		await context.send(embed=embed)
	else:
		try:
			author = context.author
			query_result = db.wtn_wallet.find_one({"user": author.id})

			embed = discord.Embed(title="Wonton Count", description="")
			if query_result is None:
				embed.description += f"{author.mention}, you have no wontons!\n"
				embed.description += "use **/cook** or **mackbot cook** to start making wontons!"
			else:
				embed.description += f"{author.mention}, you have {to_plural('wonton', query_result['coins'])}!\n"

			await context.send(embed=embed)
		except Exception as e:
			traceback.print_exc()
