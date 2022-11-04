from enum import IntEnum, auto

class SHIP_BUILD_FETCH_FROM(IntEnum):
	LOCAL = auto()
	MONGO_DB = auto()