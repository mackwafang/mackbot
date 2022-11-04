import inflect

grammar = inflect.engine()

def to_plural(str: str, count: int):
	if count != 0:
		return f"{count} {grammar.plural(str)}"
	else:
		return f"{count} {str}"