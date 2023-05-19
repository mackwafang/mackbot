import requests, json

from http.client import responses
from http import HTTPStatus

from mackbot.utilities.logger import logger
from mackbot.constants import WOWS_REALMS

VERBOSE = False
ALLOWED_CATEGORY = {
	"account": ['list', 'info', 'achievements', 'statsbydate'],
	"encyclopedia": ['info', 'ships', 'shipprofile', 'modules', 'crews', 'crewskills', 'consumables', 'battlearenas'],
	"ships": ["stats"],
	"clans": ["list", "info", "accountinfo", "glossary", "season"],
}

class WOWS:
	def __init__(self, application_id: str, region: str):
		assert region.lower() in WOWS_REALMS
		self.application_id = application_id
		self.region = region.lower()
		self.WOWS_API_DOMAIN = {
			'na': 'com',
			'eu': 'eu',
			'asia': 'asia'
		}[self.region]
		self.BASE_URL = f"https://api.worldofwarships.{self.WOWS_API_DOMAIN}"

	def _create_request_url(self, category: str, subcategory, query: dict):
		"""
		Generate a WG API URL for World of Warships
		Args:
			category (str): See wows.ALLOWED_CATEGORY
			subcategory (str): See wows.ALLOWED_CATEGORY
			query (dict):

		Returns:
			str
		"""
		assert (category in ALLOWED_CATEGORY) and (subcategory in ALLOWED_CATEGORY[category])

		url = f"{self.BASE_URL}/wows/{category}/{subcategory}/?application_id={self.application_id}&{'&'.join(f'{k}={v}' for k, v in query.items() if v)}"
		if VERBOSE:
			logger.info(f"Generating URL for category: {category}/{subcategory} with query: {query}")
		return url

	def _fetch_data(self, category: str, subcategory, query: dict={}):
		if VERBOSE:
			logger.info(f"Fetching data for {category}/{subcategory} with {query}")
		res = requests.get(url=self._create_request_url(category, subcategory, query))
		if VERBOSE:
			logger.info(f"Finished in {res.elapsed}")

		if res.status_code != 200:
			return None

		raw_data = json.loads(res.content)

		if raw_data['status'] != 'ok':
			logger.error(f"{raw_data['error']}")

		data = raw_data['data'].copy()
		if 'page_total' in raw_data['meta']:
			page_total = raw_data['meta']['page_total']
			if page_total > 1:
				new_query = query.copy()
				next_page = raw_data['meta']['page'] + 1
				new_query['page_no'] = next_page

				if next_page <= page_total:
					next_page_data = self._fetch_data(category, subcategory, new_query)
					if next_page_data is not None:
						data.update(next_page_data)

		return data

	def encyclopedia_info(self):
		return self._fetch_data("encyclopedia", "info")

	def modules(self):
		return self._fetch_data("encyclopedia", "modules")

	def ships(self):
		return self._fetch_data("encyclopedia", "ships")

	def commanders(self):
		return self._fetch_data("encyclopedia", "crews")

	def consumables(self):
		# Not things like warships consumables (like heals, damecon)
		# wtf wg why you did this to me back in 2021
		return self._fetch_data("encyclopedia", "consumables")

	def upgrades(self):
		return self._fetch_data("encyclopedia", "consumables", {"type": "Modernization"})

	def player(self, player_name: str, search_type: str):
		assert search_type in ['startswith', 'exact']
		return self._fetch_data("account", "list", {"search": player_name, "type": search_type})

	def player_info(self, player_id: int, extra:str=""):
		return self._fetch_data("account", "info", {"account_id": player_id, "extra": extra})

	def player_clan_info(self, player_id: int):
		return self._fetch_data("clans", "accountinfo", {"account_id": player_id})

	def clan_info(self, clan_id: int):
		return self._fetch_data("clans", "info", {"clan_id": clan_id})

	def ships_stat(self, player_id: int, extra: str=""):
		return self._fetch_data("ships", "stats", {"account_id": player_id, "extra": extra})