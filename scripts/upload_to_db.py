import json, os, logging, traceback, argparse
import scripts.mackbot_data_prep as data_loader

from getpass import getpass
from hashlib import sha256
from pymongo import MongoClient
from tqdm import tqdm
from enum import IntEnum, auto

class UploaderError(IntEnum):
	NONE = 0
	CONNECTION_ERROR = 1

_allowed_collections = (
	'ship_list',
	'skill_list',
	'module_list',
	'upgrade_list',
	'legendary_upgrade_list',
	'upgrade_abbr_list',
	'consumable_list',
	'ship_build'
)

# set up logger
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-5s %(message)s')

stream_handler.setFormatter(formatter)

logger = logging.getLogger("mackbot_data_uploader")
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

mackbot_db = None
sheet_id = None
db, pw = "", ""

def db_login(config_file_name="config"):
	global mackbot_db, db, pw, sheet_id
	try:
		with open(os.path.join("../data", f"{config_file_name}.json")) as f:
			data = json.load(f)
			mongodb_host = data['mongodb_host']
			sheet_id = data['sheet_id']
			db = mongodb_host.split(":")[1][2:]
			pw = sha256(mongodb_host.split(":")[2].split("@")[0].encode()).hexdigest()

		mackbot_db = MongoClient(mongodb_host).mackbot_db
		del mongodb_host

		logger.info("MongoDB connection successful.")
	except ConnectionError:
		logger.error("MongoDB cannot be connected")
		traceback.print_exc()
		exit(UploaderError.CONNECTION_ERROR)

def confirm(string):
	while True:
		usr_input = input(string).lower()
		if usr_input == 'y':
			return True
		if usr_input == 'n':
			return False

def upload_data(collection_name, index_name):
	if collection_name not in _allowed_collections:
		logger.warning(f"{collection_name} is not in the allowed list")
		return
	else:
		logger.info(f"Uploading to {collection_name}")
		# check data to remove and add
		local_data = getattr(data_loader, collection_name)
		items_in_local = set((local_data[i][index_name], local_data[i]['hash']) for i in local_data)
		items_in_db = set((i[index_name], i['hash']) for i in mackbot_db[collection_name].find({}))

		items_to_upload = items_in_local - items_in_db
		items_to_remove = items_in_db - items_in_local

		if items_to_upload:
			print(f"Found {len(items_to_upload)} items to upload")
			for item_id, item_hash in tqdm(items_to_upload):
				mackbot_db[collection_name].insert_one(local_data[str(item_id)])

		if items_to_remove:
			print(f"Found {len(items_to_remove)} items to remove")
			for item_id, item_hash in tqdm(items_to_remove):
				res = mackbot_db[collection_name].delete_one({index_name: item_id, 'hash': item_hash})

def main(yeet=False, use_live=False):
	if use_live:
		db_login("live_config")
	else:
		db_login()

	if yeet:
		# YEETUS DELETUS
		print("Warning!: You are about to delete all of mackbot db. Which includes: ")
		for collection in mackbot_db.list_collection_names():
			print(collection)

		if confirm("Proceed? > "):
			proceed_to_yeet = False
			while True:
				usr_pw = sha256(getpass("DB password: ").encode()).hexdigest()
				if usr_pw == pw:
					proceed_to_yeet = True
					break
				else:
					print("Incorrect")

			if proceed_to_yeet:
				for collection in mackbot_db.list_collection_names():
					mackbot_db[collection].drop()
	else:
		data_loader.load()

		upload_data('ship_list', 'ship_id')
		upload_data('skill_list', 'skill_id')
		upload_data('module_list', 'module_id')
		upload_data('upgrade_list', 'consumable_id')
		upload_data('upgrade_abbr_list', 'upgrade_id')
		upload_data('consumable_list', 'consumable_id')
		upload_data('ship_build', 'build_id')


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Upload data to mongoDB")
	parser.add_argument("--yeet", action="store_true", help="Delete database")
	parser.add_argument("--use_live", action="store_true", help="use live config file")
	args = parser.parse_args()

	main(yeet=args.yeet, use_live=args.use_live)