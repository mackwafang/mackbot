import os

from scripts.utilities.game_data.warships_data import database_client, skill_list, game_data
from scripts.utilities.game_data.game_data_finder import get_ship_data
from scripts.mackbot_constants import roman_numeral
from PIL import Image, ImageFont, ImageDraw

def create_build_image(
		build_name: str,
		build_ship_name: str,
		build_skills: list,
		build_upgrades: list,
		build_cmdr: str
	) -> Image:
	# create dictionary for upgrade gamedata index to image name
	image_file_dict = {}
	image_folder_dir = os.path.join("data", "modernization_icons")
	for file in os.listdir(image_folder_dir):
		image_file = os.path.join(image_folder_dir, file)
		upgrade_index = file.split("_")[2] # get index
		image_file_dict[upgrade_index] = image_file

	font = ImageFont.truetype("./data/arialbd.ttf", encoding='unic', size=20)

	# create build image
	image_size = (400, 400)

	ship = get_ship_data(build_ship_name)

	# get ship type image
	ship_type_image_filename = ""
	if ship['type'] == 'AirCarrier':
		ship_type_image_filename = 'carrier'
	else:
		ship_type_image_filename = ship['type'].lower()
	if ship['is_premium']:
		ship_type_image_filename += "_premium"
	ship_type_image_filename += '.png'

	ship_type_image_dir = os.path.join("data", "icons", ship_type_image_filename)
	ship_tier_string = roman_numeral[ship['tier'] - 1]

	image = Image.new("RGBA", image_size, (0, 0, 0, 255)) # initialize new image
	draw = ImageDraw.Draw(image) # get drawing context

	# draw ship name and ship type
	with Image.open(ship_type_image_dir).convert("RGBA") as ship_type_image:
		ship_type_image = ship_type_image.resize((ship_type_image.width * 2, ship_type_image.height * 2), Image.NEAREST)
		image.paste(ship_type_image, (0, 0), ship_type_image)
	draw.text((56, 27), f"{ship_tier_string} {ship['name']}", fill=(255, 255, 255, 255), font=font, anchor='lm') # add ship name
	draw.text((image.width - 8, 27), f"{build_name.title()} build", fill=(255, 255, 255, 255), font=font, anchor='rm') # add build name

	# get skills from this ship's tree
	if database_client is not None:
		query_result = database_client.mackbot_db.skill_list.find({"tree": ship['type']}, {"_id": 0})
		skill_list_filtered_by_ship_type = {i['skill_id']: i for i in query_result}
	else:
		skill_list_filtered_by_ship_type = {k: v for k, v in skill_list.items() if v['tree'] == ship['type']}
	# draw skills
	for skill_id in skill_list_filtered_by_ship_type:
		skill = skill_list_filtered_by_ship_type[skill_id]
		skill_image_filename = os.path.join("data", "cmdr_skills_images", skill['image'] + ".png")
		if os.path.isfile(skill_image_filename):
			with Image.open(skill_image_filename).convert("RGBA") as skill_image:

				coord = (4 + (skill['x'] * 64), 50 + (skill['y'] * 64))
				green = Image.new("RGBA", (60, 60), (0, 255, 0, 255))

				if int(skill_id) in build_skills:
					# indicate user should take this skill
					skill_image = Image.composite(green, skill_image, skill_image)
					# add number to indicate order should user take this skill
					skill_acquired_order = build_skills.index(int(skill_id)) + 1
					image.paste(skill_image, coord, skill_image)
					draw.text((coord[0], coord[1] + 40), str(skill_acquired_order), fill=(255, 255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0, 255))
				else:
					# fade out unneeded skills
					skill_image = Image.blend(skill_image, Image.new("RGBA", skill_image.size, (0, 0, 0, 0)), 0.5)
					image.paste(skill_image, coord, skill_image)

	# draw upgrades
	for slot, u in enumerate(build_upgrades):
		if u != -1:
			# specific upgrade
			if database_client is not None:
				query_result = list(database_client.mackbot_db.upgrade_list.find({"consumable_id": u}))
				if query_result is None:
					continue
				upgrade_image_dir = os.path.join("data", query_result[0]['local_image'])
			else:
				upgrade_index = [game_data[i]['index'] for i in game_data if game_data[i]['id'] == u][0]
				upgrade_image_dir = image_file_dict[upgrade_index]
		else:
			# any upgrade
			upgrade_image_dir = image_file_dict['any.png']

		with Image.open(upgrade_image_dir).convert("RGBA") as upgrade_image:
			coord = (4 + (slot * 64), image.height - 60)
			image.paste(upgrade_image, coord, upgrade_image)

	return image
