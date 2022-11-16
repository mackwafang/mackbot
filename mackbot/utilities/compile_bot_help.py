import os, json
from .logger import logger

help_dictionary = {}
help_dictionary_index = {}

def compile_help_strings() -> None:
	logger.info("Creating help index")
	with open(os.path.join(os.getcwd(), "data", "help_command_strings.json")) as f:
		data = json.load(f)
		for k, v in data.items():
			help_dictionary[k] = v
			help_dictionary_index[k] = k

	with open(os.path.join(os.getcwd(), "data", "help_terminology_strings.json")) as f:
		data = json.load(f)
		for k, v in data.items():
			help_dictionary[k] = v
			help_dictionary_index[k] = k
			for related_term in v['related_terms']:
				help_dictionary_index[related_term.lower()] = k

	del data