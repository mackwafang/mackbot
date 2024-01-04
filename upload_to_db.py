import json, os, logging, traceback, argparse

import mackbot.data_prep as data_loader

from getpass import getpass
from hashlib import sha256
from pymongo import MongoClient
from tqdm import tqdm
from enum import IntEnum, auto
from time import time

class UploaderError(IntEnum):
	NONE = 0
	CONNECTION_ERROR = auto()

MACKBOT_INFO = {
	"MACKBOT_VERSION": "1.12.1",
	"MACKBOT_WEB_VERSION": "0.5.0",
	"VERSION_TIME": int(time()),
}

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
		logger.info(f"[upload_to_db] connecting using {config_file_name}")
		with open(os.path.join("", "data", f"{config_file_name}.json")) as f:
			data = json.load(f)
			mongodb_host = data['mongodb_host']
			sheet_id = data['sheet_id']
			db = mongodb_host.split(":")[1][2:]
			pw = sha256(mongodb_host.split(":")[2].split("@")[0].encode()).hexdigest()

		mackbot_db = MongoClient(mongodb_host).mackbot_db
		del mongodb_host

		logger.info("[upload_to_db] MongoDB connection successful.")
	except ConnectionError:
		logger.error("[upload_to_db] MongoDB cannot be connected")
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
		logger.warning(f"[upload_data] {collection_name} is not in the allowed list")
		return
	else:
		# check data to remove and add
		local_data = getattr(data_loader, collection_name)
		items_in_local = set((local_data[i][index_name], local_data[i]['hash']) for i in local_data)
		items_in_db = set((i[index_name], i['hash']) for i in mackbot_db[collection_name].find({}))

		items_to_upload = items_in_local - items_in_db
		items_to_remove = items_in_db - items_in_local

		if items_to_upload or items_to_upload:
			logger.info(f"[upload_data] Uploading to {collection_name}")

		if items_to_remove:
			print(f"Found {len(items_to_remove)} items to remove")
			for item_id, item_hash in tqdm(items_to_remove):
				res = mackbot_db[collection_name].delete_one({index_name: item_id, 'hash': item_hash})

		if items_to_upload:
			print(f"Found {len(items_to_upload)} items to upload")
			for item_id, item_hash in tqdm(items_to_upload):
				mackbot_db[collection_name].insert_one(local_data[str(item_id)])

def upload():
	assert data_loader.all_data_loaded_for_use

	upload_data('ship_list', 'ship_id')
	upload_data('skill_list', 'skill_id')
	upload_data('module_list', 'module_id')
	upload_data('upgrade_list', 'consumable_id')
	upload_data('upgrade_abbr_list', 'upgrade_id')
	upload_data('consumable_list', 'consumable_id')
	upload_data('ship_build', 'build_id')

def main(yeet=False, use_live=False, change_version_only=False, update_all=False):
	if use_live:
		db_login("live_config")
	else:
		db_login()

	if not change_version_only:
		if yeet:
			# DATABASE-SUS DELETUS
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

			if update_all:
				for config_name in ["live_config", "config"]:
					db_login(config_name)
					upload()
			else:
				upload()

	if not list(mackbot_db['mackbot_info'].find({"MACKBOT_VERSION": MACKBOT_INFO['MACKBOT_VERSION']})):
		mackbot_db['mackbot_info'].insert_one(MACKBOT_INFO)

	logger.info("[upload_to_db] Finished")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Upload data to mongoDB")
	parser.add_argument("--yeet", action="store_true", help="Delete database")
	parser.add_argument("--use_live", action="store_true", help="use live config file")
	parser.add_argument("--change_version_only", action="store_true", help="change version number only")
	parser.add_argument("--update_all", action="store_true", help="Update both live and dev db")
	args = parser.parse_args()

	start_time = time()
	main(yeet=args.yeet, use_live=args.use_live, change_version_only=args.change_version_only, update_all=args.update_all)
	total_time = time() - start_time
	print(f"Operation completed in {total_time // 60:0.0f}m {total_time % 60:0.2f}s")