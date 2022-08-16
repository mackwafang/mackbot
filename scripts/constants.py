from math import inf

# dictionary to convert user input to output nations
nation_dictionary = {
	'usa': 'US',
	'us': 'US',
	'pan_asia': 'Pan-Asian',
	'ussr': 'Russian',
	'russian': 'Russian',
	'europe': 'European',
	'japan': 'Japanese',
	'uk': 'British',
	'british': 'British',
	'france': 'France',
	'french': 'France',
	'germany': 'German',
	'italy': 'Italian',
	'commonwealth': 'Commonwealth',
	'pan_america': 'Pan-American',
	'netherlands': "Dutch",
	'spain': "Spanish"
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
roman_numeral = {
	'I': 1,
	'II': 2,
	'III': 3,
	'IV': 4,
	'V': 5,
	'VI': 6,
	'VII': 7,
	'VIII': 8,
	'IX': 9,
	'X': 10,
	':star:': 11,
}

# barrel count names
barrel_count_names = {
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
	(90, inf): "Very Dangerous",
}

MM_WITH_CV_TIER = (
	[],
	[],
	[],
	[4,6],
	[4,6],
	[4,6,8],
	[6,8,10],
	[6,8,10],
	[8,10],
	[8,10],
	[10],
)