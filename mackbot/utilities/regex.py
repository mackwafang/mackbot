import re, os

with open(os.path.join(os.getcwd(), "data", "regex", "ship_list")) as f:
	regex = '|'.join(f"({i})" for i in f.read().split("\n"))
	regex += "|(consumables?:\\s?[\"\'](?:.*)[\"\'])"
with open(os.path.join(os.getcwd(), "data", "regex", "nation")) as f:
	regex += '|(' + '|'.join(f"(?:{i})" for i in f.read().split("\n")) + ')'
ship_list_regex = re.compile(regex, flags=re.I)


with open(os.path.join(os.getcwd(), "data", "regex", "consumable")) as f:
	regex = "(" + '|'.join(f"(?:{i})" for i in f.read().split("\n")) + ")"
consumable_regex = re.compile(regex, flags=re.I)

skill_list_regex = re.compile('((?:battleship|[bB]{2})|(?:carrier|[cC][vV])|(?:cruiser|[cC][aAlL]?)|(?:destroyer|[dD]{2})|(?:submarine|[sS]{2}))|page (\d{1,2})|tier (\d{1,2})')
equip_regex = re.compile('(slot (\d))|(tier ([0-9]{1,2}|([iI][vV|xX]|[vV|xX]?[iI]{0,3})))|(page (\d{1,2}))|((defensive aa fire)|(main battery)|(aircraft carrier[sS]?)|(\w|-)*)')
ship_param_filter_regex = re.compile('('
                                     '(hull|health|hp)|'
                                     '(guns?|artiller(?:y|ies))|'
                                     '(secondar(?:y|ies))|'
                                     '(torp(?:s|edo)? bombers?)|'
                                     '(torp(?:s|edo(?:es)?)?)|((?:dive )?bombers?)|'
                                     '(rockets?|attackers?)|'
                                     '(speed)|'
                                     '(aa|anti-air)|'
                                     '(concealment|dectection)|'
                                     '(consumables?)|'
                                     '(upgrades?)|'
                                     '(armou?r)|'
                                     ')*')
player_arg_filter_regex = re.compile('(?:--type (solo|div2|div3))|(?:--ship (.+?(?= -|$)))|(?:--tier (\d+))|(?:--region (na|eu|ru|asia))')
clan_filter_regex = re.compile('(.+?(?= -|$))(?: --region (na|eu|ru|asia))?')