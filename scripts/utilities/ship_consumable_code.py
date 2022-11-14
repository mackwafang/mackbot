from scripts.mackbot_constants import CONSUMABLES_CHARACTERISTIC_THRESHOLDS
from scripts.mackbot_enums import SHIP_CONSUMABLE, SHIP_CONSUMABLE_CHARACTERISTIC

def characteristic_rules(encoded: tuple) -> str:
	"""
	Returns why this consumable is classified as so
	Args:
		encoded (tuple): encoded tuple from encode()

	Returns:
		list - list of strings of reasons, or None if not tuple or tuple less than 2
	"""
	if type(encoded) != tuple or (type(encoded) == tuple and len(encoded) != 2):
		return None

	reasons = []
	c_characteristic = encoded[1]

	for c in SHIP_CONSUMABLE_CHARACTERISTIC:
		if c_characteristic & 1 == 1:
			if (encoded[0], c) in CONSUMABLES_CHARACTERISTIC_THRESHOLDS:
				threshold_data = CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(encoded[0], c)]

				threshold = threshold_data['threshold']
				comparator_to_string = {
					"eq": "is",
					"neq": "not equals to",
					"gt": "more than",
					"gte": "at least",
					"lt": "less than",
					"lte": "at most",
				}[threshold_data['comparator']]

				characteristic_to_string = {
					SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE: "with unlimited charge",
					SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE: "with limited charges",
					SHIP_CONSUMABLE_CHARACTERISTIC.HIGH_CHARGE: f"with {comparator_to_string} {threshold} charges",
					SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION: f"with {comparator_to_string} {threshold} seconds of active duration",
					SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE: f"with {comparator_to_string} {threshold/1000:0.1f} km of range",
					SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_DURATION: f"with {comparator_to_string} {threshold} seconds of active duration",
					SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_RANGE: f"with {comparator_to_string} {threshold/1000:0.1f} km of range",
					SHIP_CONSUMABLE_CHARACTERISTIC.SUPER: f"that recovers {comparator_to_string} {threshold}% of max HP per second",
					SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING: f"smokes that cover the ship traveling {comparator_to_string} {threshold} knots",
					SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE: f"with {comparator_to_string} {threshold} seconds of cooldown time",
				}[c]
				reasons.append(characteristic_to_string)
		c_characteristic >>= 1
	return reasons

def consumable_check(consumable_data):
	"""
	check if data is a consumable
	Args:
		consumable_data (dict): dictionary containing ship consumable data

	Returns:
		bool - if data is consumable data
	"""
	return all(i in ['consumableType', 'workTime'] for i in consumable_data)

def encode(consumable_data: dict) -> int:
	"""
	encode consumable type and its characteristics
	Args:
		consumable_data (dict): dictionary containing ship consumable data

	Returns:
		tuple - (consumable type, consumable characteristic)
	"""
	if consumable_check(consumable_data):
		return -1, -1
	consumable_type = consumable_data['consumableType']
	c_type = 0
	c_characteristic = 0
	if consumable_type == 'crashCrew':
		c_type = SHIP_CONSUMABLE.DAMCON
		if consumable_data['numConsumables'] != CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.DAMCON, SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE)
		if consumable_data['reloadTime'] <= CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.DAMCON, SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE)
	if consumable_type == 'rls':
		c_type = SHIP_CONSUMABLE.RADAR
		if consumable_data['workTime'] > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.RADAR, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION)
		if consumable_data['distShip'] * 30 > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.RADAR, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE)
	if consumable_type == 'speedBoosters':
		c_type = SHIP_CONSUMABLE.SPEED_BOOST
	if consumable_type == 'artilleryBoosters':
		c_type = SHIP_CONSUMABLE.GUN_BOOST
	if consumable_type == 'airDefenseDisp':
		c_type = SHIP_CONSUMABLE.DFAA
		if consumable_data['numConsumables'] == CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.DFAA, SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE)
	if consumable_type == 'sonar':
		c_type = SHIP_CONSUMABLE.HYDRO
		if consumable_data['workTime'] > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.HYDRO, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION)
		if consumable_data['distShip'] * 30 <= CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.HYDRO, SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_RANGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_RANGE)
		if consumable_data['distShip'] * 30 > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.HYDRO, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE)
	if consumable_type == 'smokeGenerator':
		c_type = SHIP_CONSUMABLE.SMOKE
		if consumable_data['numConsumables'] > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.SMOKE, SHIP_CONSUMABLE_CHARACTERISTIC.HIGH_CHARGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.HIGH_CHARGE)
		if consumable_data['speedLimit'] > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.SMOKE, SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING)
	if consumable_type == 'scout':
		c_type = SHIP_CONSUMABLE.SPOTTER
	if consumable_type == 'regenCrew':
		c_type = SHIP_CONSUMABLE.HEAL
		if consumable_data['regenerationHPSpeed'] * 100 > CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.HEAL, SHIP_CONSUMABLE_CHARACTERISTIC.SUPER)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.SUPER)
		if consumable_data['reloadTime'] <= CONSUMABLES_CHARACTERISTIC_THRESHOLDS[(SHIP_CONSUMABLE.HEAL, SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE)]:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE)
	if consumable_type == 'fighter':
		c_type = SHIP_CONSUMABLE.FIGHTER
	if consumable_type == 'torpedoReloader':
		c_type = SHIP_CONSUMABLE.TORP_BOOST

	encoder_check(c_type, c_characteristic)

	return c_type, c_characteristic

def encoder_check(c_type, c_characteristic):
	if c_characteristic >> SHIP_CONSUMABLE_CHARACTERISTIC.SUPER == 1:
		assert(c_type == SHIP_CONSUMABLE.HEAL)
	if c_characteristic >> SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING == 1:
		assert(c_type == SHIP_CONSUMABLE.SMOKE)

def decode(c_type: int, c_characteristic: int=0):
	"""
	convert encoded consumable data to strings
	Args:
		c_type (int): consumable value
		c_characteristic (int): consumable characteristic

	Returns:
		list of tuples - strings
	"""
	ct = ' '.join(SHIP_CONSUMABLE(c_type).name.split("_")).title()
	cc = [' '.join(SHIP_CONSUMABLE_CHARACTERISTIC(c).name.split("_")).title() for c in SHIP_CONSUMABLE_CHARACTERISTIC if ((c_characteristic >> c) & 1) == 1]
	return [ct] + [f"{i} {ct}" for i in cc]

def consumable_data_to_string(consumable_data):
	c_type, c_char = encode(consumable_data)
	for i in decode(c_type, c_char):
		yield i.lower()