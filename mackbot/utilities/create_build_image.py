import os, textwrap

from mackbot.utilities.game_data.warships_data import database_client, skill_list, game_data
from mackbot.utilities.game_data.game_data_finder import get_ship_data
from mackbot.constants import roman_numeral, ITEMS_TO_UPPER
from PIL import Image, ImageFont, ImageDraw

DISCLAIMER_TEXT = ["Please Note:",] + textwrap.wrap(
	"mackbot ship build should be used as a base for your builds.",
	width=90, break_long_words=False, replace_whitespace=False,
) + textwrap.wrap(
	"Please consult a friend to see if mackbot's commander skills or upgrades selection is right for you.",
	width=90, break_long_words=False, replace_whitespace=False,
)

# create build image
ITEMS_SPACING = 30
IMAGE_SIZE = (((60 + ITEMS_SPACING) * 6) - ITEMS_SPACING + 1, 470)
SKILL_IMAGE_POS_INIT = (0, 75)
UPGRADE_IMAGE_POS_INIT = (0, 335)

font = ImageFont.truetype("./data/arialbd.ttf", encoding='unic', size=20)
disclaimer_font = ImageFont.truetype("./data/arialbd.ttf", encoding='unic', size=12)

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
	ship_tier_image_dir = os.path.join("data", "icons", "tier.png")

	ship_nation = ship['nation']
	ship_nation = ship_nation.upper() if ship_nation.lower() in ['usa', 'uk', 'ussr'] else ship_nation.title()
	ship_nation_image_dir = os.path.join("data", "flags_medium", f"flag_{ship_nation}.png")

	image = Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 255)) # initialize new image
	draw = ImageDraw.Draw(image) # get drawing context

	# draw nation flag
	with Image.open(ship_nation_image_dir).convert("RGBA") as ship_nation_image:
		image.paste(ship_nation_image, (0, 0), ship_nation_image)

	# draw ship name and ship type
	with Image.open(ship_type_image_dir).convert("RGBA") as ship_type_image:
		ship_type_image = ship_type_image.resize((ship_type_image.width * 2, ship_type_image.height * 2), Image.NEAREST)
		image.paste(ship_type_image, (0, 8), ship_type_image)

	with Image.open(ship_tier_image_dir).convert("RGBA") as ship_tier_image:
		# ship_tier_image = ship_tier_image.resize((ship_tier_image.width * 2, ship_tier_image.height * 2), Image.NEAREST)
		ship_tier_image = ship_tier_image.crop((
			(ship['tier'] - 1) * 27,
			0,
			(ship['tier']) * 27,
			ship_tier_image.height,
		))
		image.paste(ship_tier_image, (56, 21), ship_tier_image)
	draw.text((91, 36), f"{ship['name']}", fill=(255, 255, 255, 255), font=font, anchor='lm', stroke_fill=(0, 0, 0, 255), stroke_width=2)

	# add build name
	build_title = build_name.upper() if build_name.lower() in ITEMS_TO_UPPER else build_name.title()
	draw.text((image.width - 8, 36), f"{build_title} Build", fill=(255, 255, 255, 255), font=font, anchor='rm', stroke_fill=(0, 0, 0, 255), stroke_width=2)

	# get skills from this ship's tree
	if database_client is not None:
		query_result = database_client.mackbot_db.skill_list.find({"tree": ship['type']}, {"_id": 0})
		skill_list_filtered_by_ship_type = {i['skill_id']: i for i in query_result}
	else:
		skill_list_filtered_by_ship_type = {k: v for k, v in skill_list.items() if v['tree'] == ship['type']}

	# draw skills
	draw.rounded_rectangle(
		(
			SKILL_IMAGE_POS_INIT,
			(
				SKILL_IMAGE_POS_INIT[0] + ((60 + ITEMS_SPACING) * 6) - ITEMS_SPACING,
				SKILL_IMAGE_POS_INIT[1] + (60 * 4)
			)
		),
		5,
		fill=(100, 100, 100, 255),
		outline=(255, 255, 255, 255),
		width=2,
	)

	for skill_id in skill_list_filtered_by_ship_type:
		skill = skill_list_filtered_by_ship_type[skill_id]
		skill_image_filename = os.path.join("data", "cmdr_skills_images", skill['image'] + ".png")
		if os.path.isfile(skill_image_filename):
			with Image.open(skill_image_filename).convert("RGBA") as skill_image:

				coord = (
					SKILL_IMAGE_POS_INIT[0] + (skill['x'] * (skill_image.width + ITEMS_SPACING)),
					SKILL_IMAGE_POS_INIT[1] + (skill['y'] * skill_image.height)
				)
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
					skill_image = Image.blend(skill_image, Image.new("RGBA", skill_image.size, (0, 0, 0, 0)), 0.75)
					image.paste(skill_image, coord, skill_image)

	# draw upgrades
	draw.rounded_rectangle(
		(
			UPGRADE_IMAGE_POS_INIT,
			(
				UPGRADE_IMAGE_POS_INIT[0] + (len(build_upgrades) * (60 + ITEMS_SPACING)) - ITEMS_SPACING,
				UPGRADE_IMAGE_POS_INIT[1] + 60
			)
		),
		5,
		fill=(100, 100, 100, 255),
		outline=(255, 255, 255, 255),
		width=2,
	)
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
			coord = (
				UPGRADE_IMAGE_POS_INIT[0] + (slot * (upgrade_image.width + ITEMS_SPACING)),
				UPGRADE_IMAGE_POS_INIT[1]
			)
			image.paste(upgrade_image, coord, upgrade_image)

	# draw disclaimer
	disclaimer_text_pos_init = (4, 400)
	draw.text(disclaimer_text_pos_init, '\n'.join(DISCLAIMER_TEXT), font=disclaimer_font, fill=(255, 255, 255, 255))

	return image
