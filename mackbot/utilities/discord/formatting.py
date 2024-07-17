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