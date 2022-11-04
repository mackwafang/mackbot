import os, json
from .logger import logger

# actual stuff
logger.info("Fetching WoWS Encyclopedia")
# load important stuff
with open(os.path.join(os.getcwd(), "data", "config.json")) as f:
	data = json.load(f)
	wg_token = data['wg_token']
	bot_token = data['bot_token']
	sheet_id = data['sheet_id']
	bot_invite_url = data['bot_invite_url']
	mongodb_host = data['mongodb_host']
	discord_invite_url = data['discord_invite_url']
	command_prefix = data['command_prefix'] if 'command_prefix' in data else 'mackbot'

with open(os.path.join(os.getcwd(), "data", "command_list.json")) as f:
	command_list = json.load(f)