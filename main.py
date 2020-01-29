import discord

DEBUG_IS_MAINTANCE = False

import subprocess
import sys
import xml.etree.ElementTree as et
def install(package):
	subprocess.check_call([sys.executable, "-m", "pip", "install", package])
if not DEBUG_IS_MAINTANCE:
	install('wargaming')
	install('pandas')
	install('numpy')

import wargaming
import pandas as pd
from numpy.random import randint

print("Fetching WoWS Encyclopedia")
wows_encyclopedia = wargaming.WoWS('74309abd627a3082035c0be246f43086',region='na',language='en').encyclopedia
ship_types = wows_encyclopedia.info()['ship_types']
del ship_types['Submarine']
print("Fetching Skill List")
skill_list = wows_encyclopedia.crewskills()
print("Fetching Commander List")
cmdr_list = wows_encyclopedia.crews()
print("Fetching Camo, Flags and Modification List")
camo_list, flag_list, upgrade_list, flag_list = {}, {}, {}, {}
for page_num in range(1,3):
	consumable_list = wows_encyclopedia.consumables(page_no=page_num)
	for consumable in consumable_list:
		c_type = consumable_list[consumable]['type']
		if c_type == 'Camouflage' or c_type == 'Permoflage' or c_type == 'Skin':
			camo_list[consumable] = consumable_list[consumable]
		if c_type == 'Modernization':
			upgrade_list[consumable] = consumable_list[consumable]
		if c_type == 'Flags':
			flag_list[consumable] = consumable_list[consumable]
print("Auto build Modification Abbreviation")
upgrade_abbr_list = {}
for i in upgrade_list:
	# print("'"+''.join([i[0] for i in mod_list[i].split()])+"':'"+f'{mod_list[i]}\',')
	upgrade_list[i]['name'] = upgrade_list[i]['name'].replace(chr(160),chr(32))
	key = ''.join([i[0] for i in upgrade_list[i]['name'].split()]).lower()
	if not key in upgrade_abbr_list:
		upgrade_abbr_list[key] = upgrade_list[i]['name'].lower()
	else:
		key = ''.join([i[:2]+"_" for i in upgrade_list[i]['name'].split()]).lower()[:-1]
		upgrade_abbr_list[key] = upgrade_list[i]['name'].lower()
print("Fetching Ship List")
ship_list = {}
for page in range(1,6):
	list = wows_encyclopedia.ships(language='en',page_no=page)
	for i in list:
		ship_list[i] = list[i]
print("Filtering Ships and Categories")
del ship_list['3749623248']
ship_list_frame = pd.DataFrame(ship_list)
ship_list_frame = ship_list_frame.filter(items=['name','nation','images','type','tier', 'upgrades', 'is_premium', 'price_gold'],axis=0)
ship_list = ship_list_frame.to_dict()
print('Fetching build file...')
root = et.parse("./ship_builds.xml").getroot()
print('Making build dictionary...')
build = {}
for ship in root:
	upgrades = []
	skills = []
	for upgrade in ship.find('upgrades'):
		upgrades.append(upgrade.text)
	for skill in ship.find('skills'):
		skills.append(skill.text)
	cmdr = ship.find('commander').text
	build[ship.attrib['name']] = {"upgrades":upgrades,"skills":skills,"cmdr":cmdr}
print("Preprocessing Done")

command_header = 'mackbot'
token = ' '

good_bot_messages = (
	'Thank you!',
	'Yūdachi tattara kekkō ganbatta poii? Teitoku-san homete hometei!',
	':3',
	':heart:',
)
command_list = (
	'help',
	'goodbot',
	'ship',
	'skill',
	'whoami',
	'list',
	'upgrade',
	'commander',
	'flag',
)
iso_country_code = {
	'usa': 'US',
	'pan_asia': 'Pan-Asian',
	'ussr': 'Russian',
	'europe': 'European',
	'japan': 'Japanese',
	'uk': 'British',
	'france': 'France',
	'germany': 'German',
	'italy': 'Italian',
	'commonwealth': 'Commonwealth',
	'pan_america': 'Pan-American'
}
ship_name_to_ascii ={
	'[zao]':'[zaō]',
	'arp myoko':'arp myōkō',
	'arp myoukou':'arp myōkō',
	'smaland':'småland',
	'arp kongo':'arp kongō',
	'arp kongou':'arp kongō',
	'[grober kurfurst]':'[großer kurfürst]',
	'l\'effronte':'l\'effronte',
	'błyskawica':'błyskawica',
	'yudachi':'yūdachi',
	'yuudachi':'yūdachi',
	'yugumo':'yūgumo',
	'yuugumo':'yūgumo',
	'kleber':'kléber',
	'hakuryu':'hakuryū',
	'hakuryuu':'hakuryū',
	'kagero':'kagerō',
	'kagerou':'kagerō',
	'konig albert':'könig albert',
	'großer kurfürst':'großer kurfürst',
	'grober kurfurst':'großer kurfürst',
	'republique':'république',
	'konig':'könig',
	'ryuujou':'ryūjō',
	'ryujo':'ryūjō',
	'guepard':'guépard',
	'ostergotland':'östergötland',
	'shoukaku':'shōkaku',
	'skane':'skåne',
	'vasteras':'västerås',
	'la galissonniere':'la galissonnière',
	'algerie':'algérie',
	'oland':'öland',
	'konigsberg':'königsberg',
	'hosho':'hōshō',
	'houshou':'hōshō',
	'emile bertin':'émile bertin',
	'nurnberg':'nürnberg',
	'friedrich der grobe':'friedrich der große',
	'fdg':'friedrich der große',
	'tatra':'tátra',
	'myoko':'myōkō',
	'myoukou':'myōkō',
	'kongo':'kongō',
	'kongou':'kongō',
	'fujin':'fūjin',
	'yubari':'yūbari',
	'yuubari':'yūbari',
	'zao':'zaō',
	'fuso':'fusō',
	'fusou':'fusō',
	'tenryu':'tenryū',
	'tenryuu':'tenryū',
	'st. louis':'st. louis',
	'myogi':'myōgi',
	'myougi':'myōgi',
	'jurien de la graviere':'jurien de la gravière',
}
# dictionary that stores skill abbreviation
skill_name_abbr = {
	'bft':'basic firing training',
	'bs':'basics of survivability',
	'em':'expert marksman',
	'tae':'torpedo armament expertise',
	'ha':'high alert',
	'v':'vigilance',
	'de':'demolition expert',
	'aft':'advanced firing training',
	'aa':'aircraft armor',
	'ieb':'improved engine boost',
	'ce':'concealment expert',
	'jat':'jack of all trades',
	'fp':'fire prevention',
	'ss':'sight stabilization',
	'ie':'improved engines',
	's':'superintendent',
	'pm':'preventive maintenance',
	'ifa':'incoming fire alert',
	'ls':'last stand',
	'el':'expert loader',
	'ar':'adrenaline rush',
	'ta':'torpedo acceleration',
	'se':'survivability expert',
	'mfcsa':'manual fire control for secondary armament',
	'maaf':'massive aa fire',
	'pt':'priority target',
	'as':'air supremacy',
	'sse':'smoke screen expert',
	'dcf':'direction center for fighters',
	'lg':'last gasp',
	'ifhe':'inertia fuse for he shells',
	'ifhes':'inertia fuse for he shells',
	'rl':'radio location',
}
cmdr_name_to_ascii ={
	'jean-jacques honore':'jean-jacques honoré',
	'paul kastner':'paul kästner',
	'quon rong':'quán róng',
	'myoko':'myōkō',
	'myoukou':'myōkō',
	'reinhard von jutland':'reinhard von jütland',
	'matsuji ijuin':'matsuji ijūin',
	'kongo':'kongō',
	'kongou':'kongō',
	'tao ji':'tāo ji',
	'gunther lutjens':'günther lütjens',
	'franz von jutland':'franz von jütland',
	'da rong':'dà róng',
	'rattenkonig':'rattenkönig',
	'leon terraux':'léon terraux',
	'charles-henri honore':'charles-henri honoré',
}
to_roman_numeral = {
	1:'I',
	2:'II',
	3:'III',
	4:'IV',
	5:'V',
	6:'VI',
	7:'VII',
	8:'VIII',
	9:'IX',
	10:'X',
}
def get_ship_data(ship):
	'''
		returns name, nation, images, ship type, tier of requested warship name
		
		raise exceptions for dictionary
	'''
	original_arg = ship
	try:
		ship_found = False
		if ship.lower() in ship_name_to_ascii: #does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()] # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			# print(ship.lower(),ship_name_in_dict.lower())
			if ship.lower() == ship_name_in_dict.lower(): # find ship based on name
				ship_found = True
				break
		if ship_found:
			name, nation, images, ship_type, tier, equip_upgrades, is_prem, price_gold = ship_list[i].values()
			upgrades, skills, cmdr = {}, {}, ""
			if original_arg.lower() in build:
				upgrades, skills, cmdr = build[original_arg.lower()].values()
			return name, nation, images, ship_type, tier, equip_upgrades, is_prem, price_gold, upgrades, skills, cmdr
	except Exception as e:
		raise e
def get_skill_data(skill):
	'''
		returns name, id, skill type, perk, tier, and icon for the requested skill
		
		raises exception from dictionary
	'''
	skill = skill.lower()
	try:
		skill_found = False
		# assuming input is full skill name
		for i in skill_list:
			if skill.lower() == skill_list[i]['name'].lower():
				skill_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not skill_found:
			skill = skill_name_abbr[skill.lower()]
			for i in skill_list:
				if skill.lower() == skill_list[i]['name'].lower():
					skill_found = True
					break
		# found it!
		name, id, skill_type, perk, tier, icon = skill_list[i].values()
		return name, id, skill_type, perk, tier, icon
	except Exception as e:
		# oops, probably not found
		print(f"Exception {type(e)}: ",e)
		raise e
def get_upgrade_data(upgrade):
	'''
		returns name for the requested upgrade 
		
		raises exception from dictionary
	'''
	upgrade = upgrade.lower()
	try:
		upgrade_found = False
		# assuming input is full upgrade name
		for i in upgrade_list:
			if upgrade.lower() == upgrade_list[i]['name'].lower():
				upgrade_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not upgrade_found:
			upgrade = upgrade_abbr_list[upgrade]
			for i in upgrade_list:
				if upgrade.lower() == upgrade_list[i]['name'].lower():
					upgrade_found = True
					break
		profile, name, price_gold, image, _, price_credit, upgrade_type, description = upgrade_list[i].values()
		# check availability of upgrade (which tier, ship)
		usable_in = {'nation':[],'type':[],'tier':[]}
		for s in ship_list_frame:
			_, n, _, ship_type, tier, u, _, _ = ship_list_frame[s]
			if int(i) in u: # if the upgrade with id 'i' in the list of upgrades 'u'
				if not n in usable_in['nation']:
					usable_in['nation'].append(n)
				if not ship_type in usable_in['type']:
					usable_in['type'].append(ship_type)
				if not tier in usable_in['tier']:
					usable_in['tier'].append(tier)
#         print(usable_in)
		nation_usable = set(usable_in['nation'])
		ship_type_usable = set(usable_in['type'])
		tier_usable = set(usable_in['tier'])
		
		nation_restriction = set([ship_list[s]['nation'] for s in ship_list])
		ship_type_restriction = set(ship_types)
		tier_restriction = set(range(1,11))
		
		# find difference
		nation_restriction = nation_restriction - nation_usable
		ship_type_restriction = ship_type_restriction - ship_type_usable
		tier_restriction = tier_restriction - tier_usable
		
		nation_restriction = nation_usable # if len(ship_restriction) > len(ship_usable) else (ship_restriction,'restricted')
		ship_type_restriction = ship_type_usable # if len(ship_type_restriction) > len(ship_type_usable) else (ship_type_restriction,'restricted')
		tier_restriction = tier_usable # if len(tier_restriction) > len(tier_usable) else (tier_restriction,'restricted')
		
		return profile, name, price_gold, image, price_credit, upgrade_type, description, nation_restriction, ship_type_restriction, tier_restriction
	except Exception as e:
		raise e
		print(f"Exception {type(e)}: ",e)
def get_commander_data(cmdr):
	'''
		returns name, icon and nation requested special commander 
		
		raise exceptions for dictionary
	'''
	cmdr = cmdr.lower()
	try:
		cmdr_found = False
		if cmdr.lower() in cmdr_name_to_ascii:
			cmdr = cmdr_name_to_ascii[cmdr.lower()]
		for i in cmdr_list:
			if cmdr.lower() == cmdr_list[i]['first_names'][0].lower():
				cmdr_found = True
				break
		if cmdr_found:
			if cmdr_list[i]['last_names'] == []:
				# get special commaders
				name = cmdr_list[i]['first_names'][0]
				icons = cmdr_list[i]['icons'][0]['1']
				nation = cmdr_list[i]['nation']
				
				return name, icons, nation
	except Exception as e:
		print(f"Exception {type(e)}",e)
		raise e
def get_flag_data(flag):
	'''
		returns information for the requested flag
		
		raises exception from dictionary
	'''
	flag = flag.lower()
	try:
		flag_found = False
		# assuming input is full flag name
		for i in flag_list:
			if flag == flag_list[i]['name'].lower():
				flag_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not flag_found:
			for i in flag_list:
				if flag.lower() == flag_list[i]['name'].lower():
					flag_found = True
					break
		profile, name, price_gold, image, _, price_credit, upgrade_type, description = flag_list[i].values()
		return profile, name, price_gold, image, price_credit, upgrade_type, description
		
	except Exception as e:
		raise e
		print(f"Exception {type(e)}: ",e)

class Client(discord.Client):
	async def on_ready(self):
		await self.change_presence(activity=discord.Game(command_header+token+command_list[0]))
		print("Logged on")
	
	def help_message(self,message):
		# help message
		arg = message.split(token)
		embed = discord.Embed(title=f"Command Help")
		try:
			command = arg[2]
			embed.add_field(name='Command',value=f"{''.join([i+' ' for i in arg[2:]])}")
		except Exception as e:
			if arg[1].lower() == "help" and type(e) == IndexError:
				# invoking help message
				command = "help"
				embed.add_field(name='Command',value="help")
		if command in command_list:
			if command == 'help':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[command]')
				embed.add_field(name='Description',value='List proper usage for [command]. Omit -[command] to list all possible commands')
				m = [i+'\n' for i in command_list]
				m.sort()
				m = ''.join(m)
				embed.add_field(name='All Commands',value=m)
			if command == 'goodbot':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='Praise the bot for being a good bot')
			if command == 'ship':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[ship]')
				embed.add_field(name='Description',value='List name, nationality, type, tier, recommended build (WIP) of the requested warships')
			if command == 'skill':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[skill/abbr]')
				embed.add_field(name='Description',value='List name, type, tier and effect of the requested commander skill')
			if command == 'whoami':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='Who\'s this bot?')
			if command == 'list':
				if len(arg) == 3:
					embed.add_field(name='Usage',value=command_header+token+command+token+"[skills/upgrades/commanders]")
					embed.add_field(name='Description',value=f'Select a category to list all items of the requested category. type **{command_header+token+command+token} [skills/upgrades/commanders]** for help on the category.{chr(10)}'+
						'**skills**: List all skills.\n'+
						'**upgrades**: List all upgrades.\n'+
						'**commanders**: List all commanders.\n')
				else:
					if arg[3] == 'skills':
						embed.add_field(name='Usage',value=command_header+token+command+token+"skills"+token+"[type/tier] [type_name/tier_number]")
						embed.add_field(name='Description',value='List name and the abbreviation of all commander skills.\n'+
						'**type [type_name]**: Optional. Returns all skills of indicated skill type. Acceptable values: **[Attack, Endurance, Support, Versatility]**\n'+
						'**tier [tier_number]**: Optional. Returns all skills of the indicated tier. Acceptable values: **[1,2,3,4]**')
					elif arg[3] == 'upgrades':
						embed.add_field(name='Usage',value=command_header+token+command+token+"upgrades"+token+"[page_number]")
						embed.add_field(name='Description',value='List name and the abbreviation of all upgrades.\n'+
							'**[page_number]**: Required. Select a page number to list upgrades. Acceptable values **[1-7]**\n')
					elif arg[3] == 'commanders':
						embed.add_field(name='Usage',value=command_header+token+command+token+"commanders"+token+"[page_number/nation]")
						embed.add_field(name='Description',value='List names of all unique commanders.\n'+
							f'**[page_number]** Required. Select a page number to list commanders.\n'+
							f'**[nation]** Required. Select a nation to filter. Acceptable values: **[{"".join([iso_country_code[i]+", " for i in iso_country_code][:-3])}]**')
					elif arg[3] == 'flags':
						embed.add_field(name='Usage',value=command_header+token+command+token+"flag")
						embed.add_field(name='Description',value='List names of all signal flags.\n')
					else:
						embed.add_field(name='Error',value="Invalid command.")
						 
			if command == 'upgrade':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[upgrade/abbr]')
				embed.add_field(name='Description',value='List the name and description of the requested warship upgrade')
			if command == 'commander':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[cmdr_name]')
				embed.add_field(name='Description',value='List the nationality of the requested commander')
			if command == 'flag':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[flag_name]')
				embed.add_field(name='Description',value='List the name and description of the requested signal flag')
		else:
			embed.add_field(name='Error',value="Invalid command.")
		return embed
	
	async def on_message(self,message):
		channel = message.channel
		arg = message.content.split(token)
		if message.author != self.user:
			if message.content.startswith("<@!"+str(self.user.id)+">"):
				if len(arg) == 1:
					# no additional arguments, send help
					print(f"User {message.author} requested my help.")
					embed = self.help_message(command_header+token+"help"+token+"help")
					if not embed is None:
						print(f"sending help message")
						await channel.send("はい、サラはここに。", embed=embed)
				else:
					# with arguments, change arg[0] and perform its normal task
					arg[0] = command_header
			if message.content.startswith(command_header+token):
				if DEBUG_IS_MAINTANCE and message.author != self.user and not message.author.name == 'mackwafang':
					# maintanance message
					await channel.send(self.user.display_name+" is under maintanance. Please wait until maintanance is over. Or contact Mack if he ~~fucks up~~ did an oopsie.")
					return
				request_type = arg[1:]
				print(f'User <{message.author}> in <{message.guild}, {message.channel}> requested command "<{request_type}>"')
				if arg[1] == command_list[0]:
					embed = self.help_message(message.content)
					if not embed is None:
						print(f"sending help message for command <{command_list[0]}>")
						await channel.send(embed=embed)
						
				if arg[1] == command_list[1]:
					# good bot
					r = randint(len(good_bot_messages))
					print(f"send reply message for {command_list[1]}")
					await channel.send(good_bot_messages[r]) # block until message is sent
				if arg[1] == command_list[2]:
					# get voted ship build
					message_string = message.content
					# message parse
					ship = ''.join([i+' ' for i in arg[2:]])[:-1] 
					ship_found = False
					if len(arg) <= 2:
						embed = self.help_message(command_header+token+"help"+token+arg[1])
						if not embed is None:
							await channel.send(embed=embed)
					else:
						try:
							name, nation, images, ship_type, tier, _, is_prem, price_gold, upgrades, skills, cmdr = get_ship_data(ship)
							print(f"returning ship information for <{name}>")
							ship_type = ship_types[ship_type]
							embed = discord.Embed(title="Warship Information")
							embed.set_thumbnail(url=images['small'])
							embed.add_field(name='Name', value=name)
							embed.add_field(name='Nation', value=iso_country_code[nation])
							embed.add_field(name='Type', value="Premium "+ship_type if is_prem else ship_type)
							embed.add_field(name='Tier', value=tier)
							
							error_value_found = False
							# suggested upgrades
							if len(upgrades) > 0:
								m = ""
								i = 1
								for upgrade in upgrades:
									upgrade_name = "[Missing]"
									if upgrade == '*':
										# any thing
										upgrade_name = "Any"
									else:
										try: # ew, nested try/catch
											upgrade_name = get_upgrade_data(upgrade)[1]
										except Exception as e: 
											print(f"Exception {type(e)}", e, f"in ship, listing upgrade {i}")
											error_value_found = True
											upgrade_name = upgrade+" [!]"
									m += f'(Slot {i}) **'+upgrade_name+'**\n'
									i += 1
								embed.add_field(name='Suggested Upgrades', value=m,inline=True)
							# suggested skills
							if len(skills) > 0:
								m = ""
								i = 1
								for skill in skills:
									skill_name = "[Missing]"
									try: # ew, nested try/catch
										skill_name, id, skill_type, perk, tier, icon = get_skill_data(skill)
									except Exception as e: 
										print(f"Exception {type(e)}", e, f"in ship, listing skill {i}")
										error_value_found = True
										skill_name = skill+" [!]"
									m += f'(Tier {tier}) **'+skill_name+'**\n'
									i += 1
								embed.add_field(name='Suggested Cmdr. Skills', value=m,inline=True)
							# suggested commander
							if cmdr != "":
								m = ""
								if cmdr == "*":
									m = "Any"
								else:
									try:
										m = get_commander_data(cmdr)[0]
									except Exception as e: 
										print(f"Exception {type(e)}", e, "in ship, listing commander")
										error_value_found = True
										m = f"{cmdr} [!]"
								embed.add_field(name='Suggested Cmdr.', value=m)
						
							error_footer_message = ""
							if error_value_found:
								error_footer_message = "[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact Mack.\n"
							embed.set_footer(text=error_footer_message+"Suggested skills are listed in ascending acquiring order.")
							await channel.send(embed=embed)
						except Exception as e:
							print(f"Exception {type(e)}", e)
							await channel.send(f"Ship **{ship}** is not understood")
							
				if arg[1] == command_list[3]:
					# get information on requested skill
					message_string = message.content
					skill_found = False
					# message parse
					skill = ''.join([i+' ' for i in arg[2:]])[:-1] #message_string[message_string.rfind('-')+1:]
					if len(arg) <= 2:
						embed = self.help_message(command_header+token+"help"+token+arg[1])
						if not embed is None:
							await channel.send(embed=embed)
					else:
						try:
							print(f'sending message for skill <{skill}>')
							async with channel.typing():
								name, id, skill_type, perk, tier, icon = get_skill_data(skill)
								embed = discord.Embed(title="Commander Skill")
								embed.set_thumbnail(url=icon)
								embed.add_field(name='Skill Name', value=name)
								embed.add_field(name='Tier', value=tier)
								embed.add_field(name='Category', value=skill_type)
								embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk))
							await channel.send(embed=embed)
						except:
							await channel.send(f"Skill **{skill}** is not understood.")
						
				if arg[1] == command_list[4]: #message.content.startswith(command_header+token+command_list[4]):
					# identify yourself, bot
					await channel.send("Beep bop. I'm a bot Mack created for the purpose of helping LODGE players with clan builds.") # block until message is sent
				if arg[1] == command_list[5]: #message.content.startswith(command_header+token+command_list[5]):
					# list command
					m = []
					embed = discord.Embed()
					send_help_message = False
					error_message = ""
					async with channel.typing():
						if len(arg) > 2:
							if arg[2] == 'skills':
								# list all skills
								if len(arg) == 3:
									# did not provide a filter, send all skills
									embed = discord.Embed(name="Commander Skill")
									m = ["**"+skill_list[i]['name']+'** ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list]
									m.sort()
									m = [m[i:i+10] for i in range(0,len(m),10)]
									for i in m:
										embed.add_field(name="Skill (Abbr.)",value=''.join([v for v in i]))
								elif len(arg) > 3:
									# asking for specific category
									if arg[3] == 'type':
										# get all skills of this type
										try:
											skill_type = arg[4] # get type
											embed = discord.Embed(name=f"{skill_type} Commander Skill")
											m = [f"(Tier {skill_list[i]['tier']}) **"+skill_list[i]['name']+'** ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['type_name'].lower() == skill_type.lower()]
											m.sort()
											m = ''.join([i for i in m])
											embed.add_field(name="(Tier) Skill (Abbr.)",value=m)
											message_success = True
										except Exception as e:
											embed = None
											print(e)
											if type(e) == IndexError:
												error_message = f"Please specify a skill type! Acceptable values: [Attack, Endurance, Support, Versatility]"
											else:
												print(f"Skill listing argument <{arg[4]}> is invalid.")
												error_message = f"Value {arg[4]} is not understood"
									elif arg[3] == 'tier':
										# get all skills of this tier
										try:
											tier = int(arg[4]) # get tier number
											embed = discord.Embed(name=f"Tier {tier} Commander Skill")
											m = [f"({skill_list[i]['type_name']}) **"+skill_list[i]['name']+'** ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['tier'] == tier]
											m.sort()
											m = ''.join([i for i in m])
											embed.add_field(name="(Category) Skill (Abbr.)",value=m)
											message_success = True
										except Exception as e:
											embed = None
											if type(e) == IndexError:
												error_message = f"Please specify a skill tier! Acceptable values: [1,2,3,4]"
											else:
												print(f"Skill listing argument <{arg[4]}> is invalid.")
												error_message = f"Value {arg[4]} is not understood"
									else:
										# not a known argument
										print(f"{arg[3]} is not a known argument for command {arg[2]}.")
										embed = None
										error_message = f"Argument **{arg[3]}** is not a valid argument."
										return

							elif arg[2] == 'upgrades':
								# list all upgrades
								if len(arg) == 3:
									embed = self.help_message(command_header+token+"help"+token+arg[1]+token+"upgrades")
									send_help_message = True
								elif len(arg) > 3:
									# list upgrades
									try:
										page = int(arg[3])-1
										m = [f"{upgrade_abbr_list[i].title()} ({i.upper()})" for i in upgrade_abbr_list]
										m.sort()
										items_per_page = 20
										num_pages = (len(upgrade_abbr_list) // items_per_page)
										m = [m[i:i+items_per_page] for i in range(0,len(upgrade_abbr_list),items_per_page)] # splitting into pages
										embed = discord.Embed(title="Upgrade List "+f"({page+1}/{num_pages+1})")
										m = m[page] # select page
										m = [m[i:i+items_per_page//2] for i in range(0,len(m),items_per_page//2)] # spliting into columns
										for i in m:
											embed.add_field(name="Upgrade (Abbr.)", value=''.join([v+'\n' for v in i]))
										if 0 > num_pages and num_pages > num_pages:
											embed = None
											error_message = f"Page {page+1} does not exists"
									except Exception as e:
										if type(e) == ValueError:
											print(f"Upgrade listing argument <{arg[3]}> is invalid.")
											error_message = f"Value {arg[3]} is not understood"
										else:
											print(f"Exception {type(e)}", e)
										
							elif arg[2] == 'commanders':
								# list all unique commanders
								message_success = False
								if len(arg) == 3:
									embed = self.help_message(command_header+token+"help"+token+arg[1]+token+"commanders")
									send_help_message = True
								elif len(arg) > 3:
									# list commanders by page
									try:
										page = int(arg[3])-1
										m = [f"({iso_country_code[cmdr_list[cmdr]['nation']]}) {cmdr_list[cmdr]['first_names'][0]}" for cmdr in cmdr_list if cmdr_list[cmdr]['last_names'] == []]
										m.sort()
										items_per_page = 20
										num_pages = (len(cmdr_list) // items_per_page)
										m = [m[i:i+items_per_page] for i in range(0,len(cmdr_list),items_per_page)] # splits into pages
										embed = discord.Embed(title=f"Commanders ({page+1}/{num_pages})")
										m = m[page] #grab desired page
										m = [m[i:i+items_per_page//2] for i in range(0,len(m),items_per_page//2)] # spliting into columns
										for i in m:
											print(i)
											embed.add_field(name="(Nation) Name",value=''.join([v+'\n' for v in i]))
										if 0 > page and page > num_pages:
											embed = None
											error_message = f"Page {page+1} does not exists"
										else:
											message_success = True
									except Exception as e:
										if type(e) == ValueError:
											pass
										else:
											print(f"Exception {type(e)}",e)
									# list commanders by nationality
									if not message_success and error_message == "": #page not listed
										try:
											nation = ''.join([i+' ' for i in arg[3:]])[:-1]
											embed = discord.Embed(title=f"{nation.title() if nation.lower() != 'us' else 'US'} Commanders")
											m = [cmdr_list[cmdr]['first_names'][0] for cmdr in cmdr_list if iso_country_code[cmdr_list[cmdr]['nation']].lower() == nation.lower()] 
											m.sort()
											m = [m[i:i+10] for i in range(0,len(m),10)] # splits into columns of 10 items each
											for i in m:
												embed.add_field(name="Name",value=''.join([v+'\n' for v in i]))
											# output_list = [(i,upgrade_abbr_list[i]) for i in upgrade_abbr_list]
											# output_list.sort()
											# num_pages = len(output_list)
											# items_per_page = 10
											# m = [name.title()+f' ('+abbr.upper()+')'+chr(10) for abbr, name in output_list[(page-1)*items_per_page:min(len(output_list),page*items_per_page)]]
											
										except Exception as e:
											print(f"Exception {type(e)}", e)
									pass
							elif arg[2] == 'flags':
								# list all flags
								if len(arg) == 3:
									# list upgrades
									try:
										embed = discord.Embed(title="Signal Flags")
										output_list = [flag_list[i]['name']+'\n' for i in flag_list]
										output_list.sort()
										items_per_page = 10
										m = output_list
										embed.add_field(name="Flag",value=''.join([i for i in m]))
									except Exception as e:
										# print(f"Flag listing argument <{arg[3]}> is invalid.")
										error_message = f"Internal Exception {type(e)} (X_X)"
							
							else:
								# something else detected
								print(f"{arg[2]} is not a known argument for command {arg[1]}.")
								embed = None
								error_message = f"Argument **{arg[2]}** is not a valid argument."
						else:
							# no arugments listed, show help message
							send_help_message = True
							embed = self.help_message(command_header+token+"help"+token+arg[1])
					if not embed == None:
						# if not send_help_message:
							# m.sort()
							# m = ''.join(m)
							# embed.add_field(name='_',value=m,inline=True)
						await channel.send(embed=embed)
					else:
						if error_message == "":
							error_message = f"Embed message for command {arg[1]} is empty! arg list: {arg}"
						await channel.send(error_message)
						
				if arg[1] == command_list[6]: #message.content.startswith(command_header+token+command_list[6]):
					# get information on requested upgrade
					message_string = message.content
					upgrade_found = False
					# message parse
					upgrade = ''.join([i+' ' for i in arg[2:]])[:-1]  # message_string[message_string.rfind('-')+1:]
					if len(arg) <= 2:
						# argument is empty, send help message
						embed = self.help_message(command_header+token+"help"+token+arg[1])
						if not embed is None:
							await channel.send(embed=embed)
					else:
						# user provided an argument
						try:
							print(f'sending message for upgrade <{upgrade}>')
							profile, name, price_gold, image, price_credit, _, description, nation_restriction, ship_type_restriction, tier_restriction = get_upgrade_data(upgrade)
							embed = discord.Embed(title="Ship Upgrade")
							embed.set_thumbnail(url=image)
							embed.add_field(name='Name', value=name)
							embed.add_field(name='Description',value=description)
							embed.add_field(name='Effect',value=''.join([profile[detail]['description']+'\n' for detail in profile]))
							
							if len(ship_type_restriction) > 0:
								print(len(ship_type_restriction), len(ship_types))
								m = f"{'All types' if len(ship_type_restriction) == len(ship_types) else ''.join([ship_types[i]+'s, ' for i in sorted(ship_type_restriction)])[:-3]}"
								embed.add_field(name="Type",value=m)
							if len(tier_restriction) > 0:
								m = f"{'All tiers' if len(tier_restriction) == 10 else ''.join([str(i)+', ' for i in sorted(tier_restriction)])[:-2]}"
								embed.add_field(name="Tier",value=m)
							if len(nation_restriction) > 0:
								m = f"{'All Nations' if len(nation_restriction) == len(iso_country_code) else ''.join([iso_country_code[i]+', ' for i in sorted(nation_restriction)])[:-2]}"
								embed.add_field(name="Nation",value=m)
									
							if price_credit > 0:
								embed.add_field(name='Price (Credit)', value=price_credit)
							await channel.send(embed=embed)
						except Exception as e:
							print(f"Exception {type(e)}", e)
							await channel.send(f"Upgrade **{upgrade}** is not understood.")
				if arg[1] == command_list[7]:
					# get information on requested commander
					message_string = message.content
					cmdr_found = False
					# message parse
					cmdr = ''.join([i+' ' for i in arg[2:]])[:-1] #message_string[message_string.rfind('-')+1:]
					if len(arg) <= 2:
						embed = self.help_message(command_header+token+"help"+token+arg[1])
						if not embed is None:
							await channel.send(embed=embed)
					else:
						try:
							async with channel.typing():
								print(f'sending message for commander <{cmdr}>')
								name, icon, nation = get_commander_data(cmdr)
								embed = discord.Embed(title="Commander")
								embed.set_thumbnail(url=icon)
								embed.add_field(name='Name',value=name)
								embed.add_field(name='Nation',value=iso_country_code[nation])
								
							await channel.send(embed=embed)
						except:
							await channel.send(f"Commander **{cmdr}** is not understood.")
				if arg[1] == command_list[8]:
					# get information on requested flag
					message_string = message.content
					upgrade_found = False
					# message parse
					flag = ''.join([i+' ' for i in arg[2:]])[:-1]  # message_string[message_string.rfind('-')+1:]
					if len(arg) <= 2:
						# argument is empty, send help message
						embed = self.help_message(command_header+token+"help"+token+arg[1])
						if not embed is None:
							await channel.send(embed=embed)
					else:
						# user provided an argument
						try:
							print(f'sending message for flag <{flag}>')
							profile, name, price_gold, image, price_credit, _, description = get_flag_data(flag)
							embed = discord.Embed(title="Flag Information")
							embed.set_thumbnail(url=image)
							embed.add_field(name='Name', value=name)
							embed.add_field(name='Description',value=description)
							embed.add_field(name='Effect',value=''.join([profile[detail]['description']+'\n' for detail in profile]))
							if price_credit > 0:
								embed.add_field(name='Price (Credit)', value=price_credit)
							if price_gold > 0:
								embed.add_field(name='Price (Doub.)', value=price_gold)
							await channel.send(embed=embed)
						except Exception as e:
							print(f"Exception {type(e)}", e)
							await channel.send(f"Flag **{flag}** is not understood.")
				# if not arg[1] in command_list:
					# await channel.send(f"I don't know command **{arg[1]}**. Please check the help page by tagging me or use **{command_header+token+command_list[0]}**")
client = Client()
try:
	client.run('NjY3ODY2MzkxMjMxMzMyMzUz.XiI94A.JjQtinUguaHFnu_XOWNokwZ0B6s')
except Exception as e:
	print(f"{type(e)}",e)