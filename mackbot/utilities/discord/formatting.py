def number_separator(value, formatting="") -> str:
	"""
	custom number separator
	Args:
		value ():

	Returns: string

	"""
	return f"{value:{','+formatting}}".replace(',', ' ')