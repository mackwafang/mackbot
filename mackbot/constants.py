import json, os


from math import inf
from .enums import SHIP_CONSUMABLE, SHIP_CONSUMABLE_CHARACTERISTIC

EXCHANGE_RATE_DOUB_TO_DOLLAR = 250
DEGREE_SYMBOL = "\xb0"
SIGMA_SYMBOL = "\u03c3"
EMPTY_LENGTH_CHAR = '\u200b'


# dictionary to convert user input to output nations
with open(os.path.join(os.getcwd(), "data", "nation_dictionary.json")) as f:
	nation_dictionary = json.load(f)

ship_types = {
	'Destroyer': 'Destroyer',
	'AirCarrier': 'Aircraft Carrier',
	'Aircraft Carrier': 'Aircraft Carrier',
	'Battleship': 'Battleship',
	'Cruiser': 'Cruiser',
	'Submarine': 'Submarine'
}

# convert weegee ship type to usn hull classifications
hull_classification_converter = {
	'Destroyer': 'DD',
	'AirCarrier': 'CV',
	'Aircraft Carrier': 'CV',
	'Battleship': 'BB',
	'Cruiser': 'C',
	'Submarine': 'SS'
}

# see the ship name conversion dictionary comment
cmdr_name_to_ascii = {
	'jean-jacques honore': 'jean-jacques honoré',
	'paul kastner': 'paul kästner',
	'quon rong': 'quán róng',
	'myoko': 'myōkō',
	'myoukou': 'myōkō',
	'reinhard von jutland': 'reinhard von jütland',
	'matsuji ijuin': 'matsuji ijūin',
	'kongo': 'kongō',
	'kongou': 'kongō',
	'tao ji': 'tāo ji',
	'gunther lutjens': 'günther lütjens',
	'franz von jutland': 'franz von jütland',
	'da rong': 'dà róng',
	'rattenkonig': 'rattenkönig',
	'leon terraux': 'léon terraux',
	'charles-henri honore': 'charles-henri honoré',
	'jerzy swirski': 'Jerzy Świrski',
	'swirski': 'Jerzy Świrski',
	'halsey': 'william f. Halsey jr.',
}

# here because of lazy
ROMAN_NUMERAL = (
	'I',
	'II',
	'III',
	'IV',
	'V',
	'VI',
	'VII',
	'VIII',
	'IX',
	'X',
	':star:',
)

# barrel count names
BARREL_COUNT_NAMES = {
	1: "Single",
	2: "Double",
	3: "Triple",
	4: "Quadruple",
	5: "Quintuple",
	6: "Sextuple"
}

AA_RATING_DESCRIPTOR = {
	(0, 1): "Non-Existence",
	(1, 20): "Very Weak",
	(20, 40): "Weak",
	(40, 50): "Moderate",
	(50, 70): "High",
	(70, 90): "Dangerous",
	(90, 175): "Very Dangerous",
	(175, inf): "Do Not Approach",
}

GOOD_BOT_MESSAGES = (
	'Thank you!',
	'Mackbot tattara kekkō ganbatta poii? Homete hometei!',
	':3',
	':heart:',
)

MM_WITH_CV_TIER = (
	(),
	(),
	(),
	(4,6),
	(4,6),
	(4,6,8),
	(6,8,10),
	(6,8,10),
	(8,10),
	(8,10),
	(10, ),
)

WOWS_REALMS = ('na', 'ru', 'eu', 'asia')

# defines the which categories of ships are in (i.e. researchable, doubloons, coal, etc)
SHIP_GROUP_DICT = {
	'disabled':             "Unavailable",
	'ultimate':             "Armory", # ship available via the armory
	'special':              "Premium",
	'specialUnsellable':    "Premium (Unsellable)",
	'demoWithStats':        "",
	'clan':                 "Clan Battle",
	'coopOnly':             "Co-Op Only",
	'upgradeableExclusive': "Free XP",
	'preserved':            "",
	'demoWithoutStats':     "Test",
	'upgradeableUltimate':  "Free XP",
	'upgradeable':          "Researchable", # tech line ship
	'unavailable':          "Unavailable",
	'earlyAccess':          "Early Access",
	'superShip':            "Super",
	'start':                "Starting"
}

# icons for prettifying outputs
ICONS_EMOJI = {
	"torp": "<:torp:917573129579151392>",
	"dd": "<:destroyer:917573129658859573>",
	"Destroyer": "<:destroyer:917573129658859573>",
	"gun": "<:gun:917573129730146325>",
	"bb_prem": "<:battleship_premium:917573129801449563>",
	"plane_torp": "<:plane_torpedo:917573129847590993>",
	"ss_prem": "<:submarine_premium:917573129851764776>",
	"ss": "<:submarine:917573129876955147>",
	"Submarine": "<:submarine:917573129876955147>",
	"bb": "<:battleship:917573129876959232>",
	"Battleship": "<:battleship:917573129876959232>",
	"cv": "<:carrier:917573129931477053>",
	"AirCarrier": "<:carrier:917573129931477053>",
	"Aircraft Carrier": "<:carrier:917573129931477053>",
	"c": "<:cruiser:917573129885323374>",
	"Cruiser": "<:cruiser:917573129885323374>",
	"dd_prem": "<:destroyer_premium:917573129944059965>",
	"plane_rocket": "<:plane_projectile:917573129956638750>",
	"c_prem": "<:cruiser_premium:917573129965027398>",
	"cv_prem": "<:carrier_premium:917573130019557416>",
	"plane_bomb": "<:plane_bomb:917573130023759893>",
	"penetration": "<:penetration:917583397122084864>",
	"ap": "<:ap:917585790765252608>",
	"he": "<:he:917585790773653536>",
	"sap": "<:sap:917585790811402270>",
	"cs": "<:sap:917585790811402270>",
	"reload": "<:reload:917585790815584326>",
	"range": "<:range:917589573415088178>",
	"aa": "<:aa:917590394806599780>",
	"plane": "<:plane:917601379235815524>",
	"concealment": "<:concealment:917605435278782474>",
	"clan_in": "<:clan_in:952757125225021450>",
	"clan_out": "<:clan_out:952757125237575690>",
	"green_plus": "<:green_plus:979497350869450812>",
	"red_dash": "<:red_dash:979497350911385620>",
	'flag_Commonwealth': '<:flag_Commonwealth:1039970300030373930>',
	'flag_Europe': '<:flag_Europe:1039970301552885780>',
	'flag_France': '<:flag_France:1039970302647599175>',
	'flag_Germany': '<:flag_Germany:1039970303729737748>',
	'flag_Italy': '<:flag_Italy:1039970305592012810>',
	'flag_Japan': '<:flag_Japan:1039970306674151475>',
	'flag_Netherlands': '<:flag_Netherlands:1039970307664007328>',
	'flag_Pan_America': '<:flag_Pan_America:1039970308943249438>',
	'flag_Pan_Asia': '<:flag_Pan_Asia:1039970310499356725>',
	'flag_Poland': '<:flag_Poland:1039970311698927776>',
	'flag_Spain': '<:flag_Spain:1039970312785240124>',
	'flag_UK': '<:flag_UK:1039970313808662658>',
	'flag_USA': '<:flag_USA:1039970314613956692>',
	'flag_USSR': '<:flag_USSR:1039970316388147230>',

}

ITEMS_TO_UPPER = (
	'bb',
	'c',
	'cv',
	'dd',
	'ss',
	'dfaa',
	'ijn',
	'usn',
	'usa',
	'uk',
	'ussr',
	'aa',
)

CONSUMABLES_CHARACTERISTIC_THRESHOLDS = {
	(SHIP_CONSUMABLE.DAMCON, SHIP_CONSUMABLE_CHARACTERISTIC.LIMITED_CHARGE): {"threshold": -1, "comparator": "neq"},
	(SHIP_CONSUMABLE.DAMCON, SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE): {"threshold": 40, "comparator": "lte"},
	(SHIP_CONSUMABLE.RADAR, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION): {"threshold": 30, "comparator": "gte"},
	(SHIP_CONSUMABLE.RADAR, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE): {"threshold": 10000, "comparator": "gt"},
	(SHIP_CONSUMABLE.DFAA, SHIP_CONSUMABLE_CHARACTERISTIC.UNLIMITED_CHARGE): {"threshold": -1, "comparator": "eq"},
	(SHIP_CONSUMABLE.HYDRO, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_DURATION): {"threshold": 120, "comparator": "gt"},
	(SHIP_CONSUMABLE.HYDRO, SHIP_CONSUMABLE_CHARACTERISTIC.SHORT_RANGE): {"threshold": 3000, "comparator": "lte"},
	(SHIP_CONSUMABLE.HYDRO, SHIP_CONSUMABLE_CHARACTERISTIC.LONG_RANGE): {"threshold": 5000, "comparator": "gt"},
	(SHIP_CONSUMABLE.SMOKE, SHIP_CONSUMABLE_CHARACTERISTIC.HIGH_CHARGE): {"threshold": 4, "comparator": "gt"},
	(SHIP_CONSUMABLE.SMOKE, SHIP_CONSUMABLE_CHARACTERISTIC.TRAILING): {"threshold": 15, "comparator": "gt"},
	(SHIP_CONSUMABLE.HEAL, SHIP_CONSUMABLE_CHARACTERISTIC.SUPER): {"threshold": 1, "comparator": "gt"},
	(SHIP_CONSUMABLE.HEAL, SHIP_CONSUMABLE_CHARACTERISTIC.QUICK_RECHARGE): {"threshold": 60, "comparator": "lte"},
}

with open(os.path.join(os.getcwd(), "data", "upgrade_modifier_description.json")) as f:
	UPGRADE_MODIFIER_DESC = json.load(f)

ARMOR_ID_TO_STRING = {
	"fore and aft": {
		"65584": "Fore-end Armor Belt",
		"65585": "Aft-end Armor Belt",
		# "262247": "Fore-end Armor Belt",
	},
	"citadel": {
		"65600": "Citadel Deck",
		# "131133": "Citadel Deck",
		"131136": "Citadel Deck (Center)",
		"131138": "Citadel Armored Deck Slope (Side)",
	},
	"superstructure": {
		"65593": "Casemate Deck",
		"65625": "Superstructure Plating",
		# "65626": "Superstructure Plating",
		"65643": "Conning Tower (Top Plate)",
		"65644": "Conning Tower",
		"262234": "Superstructure Plating (Secondary Bottom)",
	},
	"turret": {
		"65568": "Turret Side Plate (Front)",
		"65569": "Turret Top Plate",
		"65635": "Turret Bottom Plate",
		"65636": "Turret Frontal Plate",
		"65571": "Turret Rear Plate",
		"65670": "Barbette Armor (Top)",
		"65710": "Barbette Bottom",
		"65750": "Barbette Hatch",
		"131104": "Turret Side Plate (Rear)",
		"131206": "Barbette Armor (Bottom)",
		# "131207": "Barbette Armor (Bottom)",
		# "131208": "Barbette Armor (Bottom)",
		# "131209": "Barbette Armor (Bottom)",
	},
	"torpedo protection": {
		"65548": "Torpedo Protection Bottom (?)",
		"65583": "Torpedo Protection Side Plating",
		# "65584": "Torpedo Protection Side Plating",
	},
}
