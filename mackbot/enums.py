from enum import IntEnum, auto

class COMMAND_INPUT_TYPE(IntEnum):
	CLI = 0
	SLASH = auto()

class SHIP_BUILD_FETCH_FROM(IntEnum):
	LOCAL = auto()
	MONGO_DB = auto()

class SHIP_CONSUMABLE(IntEnum):
	NONE = 0
	DAMCON = auto()
	RADAR = auto()
	SPEED_BOOST = auto()
	GUN_BOOST = auto()
	TORP_BOOST = auto()
	DFAA = auto()
	HYDRO = auto()
	SMOKE = auto()
	SPOTTER = auto()
	HEAL = auto()
	FIGHTER = auto()

class SHIP_CONSUMABLE_CHARACTERISTIC(IntEnum):
	NONE = 0
	UNLIMITED_CHARGE = auto()
	LIMITED_CHARGE = auto()
	HIGH_CHARGE = auto()
	LONG_DURATION = auto()
	LONG_RANGE = auto()
	SHORT_DURATION = auto()
	SHORT_RANGE = auto()
	SUPER = auto()
	TRAILING = auto()
	QUICK_RECHARGE = auto()

class SHIP_COMBAT_PARAM_FILTER(IntEnum):
	HULL = 0
	GUNS = auto()
	ATBAS = auto()
	TORPS = auto()
	ROCKETS = auto()
	TORP_BOMBER = auto()
	BOMBER = auto()
	ENGINE = auto()
	AA = auto()
	CONCEAL = auto()
	CONSUMABLE = auto()
	UPGRADES = auto()
	ARMOR = auto()
	SONAR = auto()

class SUPER_SHIP_SPECIAL_TYPE(IntEnum):
	NONE = 0
	COMBAT_INSTRUCTION = auto()
	ALT_FIRE = auto()

class ANSI_FORMAT(IntEnum):
	NONE = 0
	BOLD = 1
	UNDERLINE = 4

class ANSI_TEXT_COLOR(IntEnum):
	GRAY = 30
	RED = 31
	GREEN = 32
	YELLOW = 33
	BLUE = 34
	PINK = 35
	CYAN = 36
	WHITE = 37

class ANSI_BKG_COLOR(IntEnum):
	DARK_BLUE = 40
	ORANGE = 41
	MARBLE_BLUE = 42
	GRAY_TURQUOISE = 43
	GRAY = 44
	INDIGO = 45
	LIGHT_GRAY = 46
	WHITE = 47