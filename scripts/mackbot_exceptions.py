from enum import IntEnum, auto

class NoShipFound(Exception):
	pass

class NoBuildFound(Exception):
	pass

class NoUpgradeFound(Exception):
	pass

class NoSkillFound(Exception):
	pass

class BuildError(IntEnum):
	NONE = 0
	SKILL_POINTS_EXCEED = auto()
	SKILL_INCORRECT = auto()
	UPGRADE_INCORRECT = auto()
	UPGRADE_NOT_FOUND = auto()
	SHIP_NOT_FOUND = auto()