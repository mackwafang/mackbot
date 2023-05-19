import requests

from http.client import responses
from http import HTTPStatus

from mackbot.utilities.logger import logger
from mackbot.constants import WOWS_REALMS

#https://api.worldofwarships.eu/wows/encyclopedia/ships/

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

	def _create_request_url(self, category: str, query: dict):
		return f"{self.BASE_URL}/wows/{category}/?application_id={self.application_id}{'?'.join(k+'='+v for k, v in query)}"

	def encyclopedia(self):
		return self._create_request_url("encyclopedia")

