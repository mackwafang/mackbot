import gettext, json

translator = gettext.translation("global", localedir="language", languages=['en'])
translator.install()

catalog = translator._catalog
keys_to_remove = []
keys_to_add = []

from pprint import pprint

for k in catalog:
	if type(k) == tuple or not k:
		keys_to_remove.append(k)

for k in keys_to_remove:
	del catalog[k]
	
with open("../data/translator.json", 'w') as f:
	json.dump(catalog, f)
