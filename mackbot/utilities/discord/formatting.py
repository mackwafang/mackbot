def number_separator(value, formatting="") -> str:
	"""
	custom number separator
	Args:
		value ():

	Returns: string

	"""
	return f"{value:{','+formatting}}".replace(',', ' ')

def embed_subcategory_title(string: str, space=12):
	return f"> **`{string:<{space}}`**"

def seconds_to_minutes_format(value: int):
	return f'{str(int(value // 60)) + "m" if value >= 60 else ""} {str(int(value % 60)) + "s" if value % 60 > 0 else ""}'