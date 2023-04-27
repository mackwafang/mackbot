import requests, re, json

from mackbot.utilities.logger import logger
from http.client import responses

NON_EVENT_SHIP_CURRENCY = (
	'coal',
	'paragon_xp',    # research xp
	'steel',
)

def get_armory_data():
	logger.info("Extracting armory data")
	res = requests.get('https://armory.worldofwarships.com/en/category/ships?filter_category=ships&preset=ships_filter_all')
	if not res.ok:
		logger.warning(f"Response failed. {res.status_code} {responses[res.status_code]}")
		return None

	logger.info("Response OK, parsing data")
	data = res.text
	# regex = re.compile("metashop\.state\.content = (.*)\\s*try")
	regex = re.compile("const ?_state = (.*);+\n")

	match = regex.findall(data)[0]

	armory_data = json.loads(match)

	return armory_data['content']['bundles']

def get_armory_ships():
	"""
	Get list of ships that are sold in the armory that does NOT cost doubloons
	Returns:
		dicts - ship data that are sold in coal, free xp, or gold
	"""
	armory_data = get_armory_data()
	if not armory_data:
		return None

	logger.info("Extracting coal, research, and steel ship prices")
	ships = {}
	for k, data in armory_data.items():
		# for each item in bundle
		for item in data['entitlements']:
			# check if ship and it is a ship that requires listed currency
			if (item['type'] == 'ship') and (data['currency'] in NON_EVENT_SHIP_CURRENCY):
				d = {
					"ship_id": item['identifier'],
					"currency_type": data['currency'],
					"value": data['price'],
				}
				ships[d['ship_id']] = d.copy()

	return ships