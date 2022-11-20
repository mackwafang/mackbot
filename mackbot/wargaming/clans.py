import requests

from ..utilities.logger import logger
from http.client import responses


def clan_ranking(clan_id: int, region: str='na') -> dict:
	domain_ext = {
		"na": "com",
		"eu": "eu",
		"asia": "asia"
	}[region]
	url = f"https://clans.worldofwarships.{domain_ext}/api/clanbase/{str(clan_id)}/claninfo/"
	response = requests.get(url)
	logger.info(f"Getting clan ranking info for clan with id {clan_id}")
	if not response.ok:
		logger.warning(f"Response failed. {response.status_code} {responses[response.status_code]}")
		return None
	if 'tag' not in response.json()['clanview']['clan']:
		logger.warning(f"Response OK, but clan may be in different region")
		return None
	logger.info(f"Response OK")

	data = response.json()['clanview']

	clan_ladder = data['wows_ladder']
	return clan_ladder
