import os, logging, time
from pathlib import Path
from logging.handlers import RotatingFileHandler

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
formatter = logging.Formatter('[%(asctime)s] [%(name)-8s] [%(module)s.%(funcName)s] [%(levelname)-5s] %(message)s')

handler.setFormatter(formatter)
handler.addFilter(LogFilterBlacklist("RESUME", "RESUMED"))
stream_handler.setFormatter(formatter)
stream_handler.addFilter(LogFilterBlacklist("RESUME", "RESUMED"))

logger = logging.getLogger("mackbot")
logger.addHandler(handler)
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)