import json, os

from pprint import pprint

with open("../data/GameParams-0.json") as f:
	data = json.load(f)

with open('../data/translator.json') as f:
	translator = json.load(f)
	translator_keys = tuple(translator.keys())

_allowed_type = ('Ability', 'Aircraft', 'Ship', 'Projectile', 'Modernization', 'Gun', 'Crew')
unicode_replacements = (
	("\xa0", ' '),
	("\xc2", '.'),
)

ITEMS_PER_FILE = 5000
NUM_FILES = (len(data) // ITEMS_PER_FILE) + 1

for file_count in range(NUM_FILES):
	game_data_pruned_dir = os.path.join("../data", f"GameParamsPruned_{file_count}.json")
	print(f"Writing {game_data_pruned_dir}")
	with open(game_data_pruned_dir, "w") as f:
		items_to_dump = {}
		for key in list(data.keys())[ITEMS_PER_FILE * file_count : ITEMS_PER_FILE * (file_count + 1)]:
			if data[key]['typeinfo']['type'] in _allowed_type:
				items_to_dump[key] = data[key].copy()

				# translate names to human readable names
				for tk in translator_keys:
					if data[key]['name'].upper() in tk:
						key_index = translator_keys[translator_keys.index(tk)]
						for string, replace in unicode_replacements:
							translated_name = translator[key_index].replace(string, replace)
						items_to_dump[key]['name'] = translated_name

				# adds consumable names and description
				if data[key]['typeinfo']['type'] == 'Ability':
					consumable_name = translator["IDS_DOCK_CONSUME_TITLE_" + data[key]['name'].upper()]
					consumable_description = translator["IDS_DOCK_CONSUME_DESCRIPTION_" + data[key]['name'].upper()]
					items_to_dump[key]['name'] = consumable_name
					items_to_dump[key]['description'] = consumable_description

		json.dump(items_to_dump, f)
