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
	regex = re.compile("metashop\.state\.content = (.*)\\s*try")

	match = regex.findall(data)[0]
	match = match[:-1]

	armory_data = json.loads(match)

	return armory_data['bundles']

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
		for item in data['items']:
			if (item['type'] == 'ship') and (data['price'][0]['currency'] in NON_EVENT_SHIP_CURRENCY):
				d = {
					"ship_id": item['cd'],
					"currency_type": data['price'][0]['currency'],
					"value": data['price'][0]['value'],
				}
				ships[d['ship_id']] = d.copy()

	return ships