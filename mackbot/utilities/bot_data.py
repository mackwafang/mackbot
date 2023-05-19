import os, json, wargaming, pickle
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

# get weegee's wows encyclopedia
WG = {
	'na': wargaming.WoWS(wg_token, region='na', language='en'),
	'asia': wargaming.WoWS(wg_token, region='asia', language='en'),
	'eu': wargaming.WoWS(wg_token, region='eu', language='en'),
}
wows_encyclopedia = WG['na'].encyclopedia

clan_history = {}
clan_history_file_path = os.path.join(os.getcwd(), "data", "clan_history")
if os.path.exists(clan_history_file_path):
	with open(clan_history_file_path, 'rb') as f:
		clan_history = pickle.load(f)

with open(os.path.join(os.getcwd(), "data", "hottakes.txt")) as f:
	hottake_strings = f.read().split('\n')

with open(os.path.join(os.getcwd(), "data", "faq.json")) as f:
	faq_data = json.load(f)