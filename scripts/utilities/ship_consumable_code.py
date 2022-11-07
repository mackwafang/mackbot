from scripts.mackbot_enums import SHIP_CONSUMABLE, SHIP_CONSUMABLE_CHARACTERISTIC

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
		if consumable_data['numConsumables'] != -1:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE)
		if consumable_data['reloadTime'] <= 40:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE)
	if consumable_type == 'rls':
		c_type = SHIP_CONSUMABLE.RADAR
		if consumable_data['workTime'] > 20:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION)
		if consumable_data['distShip'] * 30 > 10000:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE)
	if consumable_type == 'speedBoosters':
		c_type = SHIP_CONSUMABLE.SPEED_BOOST
	if consumable_type == 'artilleryBoosters':
		c_type = SHIP_CONSUMABLE.GUN_BOOST
	if consumable_type == 'airDefenseDisp':
		c_type = SHIP_CONSUMABLE.DFAA
		if consumable_data['numConsumables'] == -1:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE)
	if consumable_type == 'sonar':
		c_type = SHIP_CONSUMABLE.HYDRO
		if consumable_data['workTime'] > 120:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION)
		if consumable_data['distShip'] * 30 <= 3000:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_RANGE)
		if consumable_data['distShip'] * 30 > 5000:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE)
	if consumable_type == 'smokeGenerator':
		c_type = SHIP_CONSUMABLE.SMOKE
		if consumable_data['numConsumables'] > 4:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.HIGH_CHARGE)
		if consumable_data['speedLimit'] > 15:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING)
	if consumable_type == 'scout':
		c_type = SHIP_CONSUMABLE.SPOTTER
	if consumable_type == 'regenCrew':
		c_type = SHIP_CONSUMABLE.HEAL
		if consumable_data['regenerationHPSpeed'] * 100 > 1:
			c_characteristic |= (1 << SHIP_CONSUMABLE_CHARACTERISTIC.SUPER)
		if consumable_data['reloadTime'] <= 60:
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