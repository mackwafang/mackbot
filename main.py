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
print("Fetching Skill List")
skill_list = wows_encyclopedia.crewskills()
print("Fetching Modification List")
upgrade_list = wows_encyclopedia.info()['ship_modifications']
print("Auto build Modification Abbreviation")
upgrade_abbr_list = {}
for i in upgrade_list:
    # print("'"+''.join([i[0] for i in mod_list[i].split()])+"':'"+f'{mod_list[i]}\',')
	upgrade_list[i] = upgrade_list[i].replace(chr(160),chr(32))
	upgrade_abbr_list[''.join([i[0] for i in upgrade_list[i].split()]).lower()] = upgrade_list[i].lower()


print("Fetching Ship List")
ship_list = {}
for page in range(1,6):
    list = wows_encyclopedia.ships(language='en',page_no=page)
    for i in list:
        ship_list[i] = list[i]
print("Filtering Ships and Categories")
del ship_list['3749623248']
frame = pd.DataFrame(ship_list)
frame = frame.filter(items=['name','nation','images','type','tier'],axis=0)
ship_list = frame.to_dict()
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
	build[ship.attrib['name']] = {"upgrades":upgrades,"skills":skills}
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

def get_ship_data(ship):
	'''
		returns name, nation, images, ship type, tier of requested warship name
		
		raise exceptions for dictionary
	'''
	ship = ship.lower()
	try:
		if ship.lower() in ship_name_to_ascii: #does name includes non-ascii character (outside prinable ?
			ship = ship_name_to_ascii[ship.lower()] # convert to the appropiate name
		for i in ship_list:
			ship_name_in_dict = ship_list[i]['name']
			# print(ship.lower(),ship_name_in_dict.lower())
			if ship.lower() == ship_name_in_dict.lower(): # find ship based on name
				ship_found = True
				break
		if ship_found:
			name, nation, images, ship_type, tier = ship_list[i].values()
			upgrades, skills = {}, {}
			if name.lower() in build:
				upgrades, skills = build[name.lower()].values()
			return name, nation, images, ship_type, tier, upgrades, skills
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
			if upgrade.lower() == upgrade_list[i].lower():
				upgrade_found = True
				break
		# parsed item is probably an abbreviation, checking abbreviation
		if not upgrade_found:
			upgrade = upgrade_abbr_list[upgrade.lower()]
			for i in upgrade_list:
				if upgrade.lower() == upgrade_list[i].lower():
					upgrade_found = True
					break
		name = upgrade_list[i]
		return name
	except Exception as e:
		raise e
		print(f"Exception {type(e)}: ",e)

class Client(discord.Client):
	async def on_ready(self):
		print("Logged on")
	
	def help_message(self,message):
		# help message
		arg = message.split(token)
		command = arg[2]
		embed = discord.Embed(title=f"Command Help")
		embed.add_field(name='Command',value=f"{''.join([i+' ' for i in arg[2:]])}")
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
					embed.add_field(name='Usage',value=command_header+token+command+token+"[skills/upgrade]")
					embed.add_field(name='Description',value=f'Select a category to list all items of the requested category. type **{command_header+token+command+token} [skills/upgrade]** for help on the category.{chr(10)}'+
						'**skills**: List all skills.\n'+
						'**upgrades**: List all upgrades.\n')
				else:
					if arg[3] == 'skills':
						embed.add_field(name='Usage',value=command_header+token+command+token+"skills"+token+"[type/tier] [type_name/tier_number]")
						embed.add_field(name='Description',value='List name and the abbreviation of all commander skills.\n'+
						'**type [type_name]**: Optional. Returns all skills of indicated skill type. Acceptable values: [Attack, Endurance, Support, Versatility]\n'+
						'**tier [tier_number]**: Optional. Returns all skills of the indicated tier. Acceptable values: [1,2,3,4]')
					if arg[3] == 'upgrades':
						embed.add_field(name='Usage',value=command_header+token+command+token+"upgrades"+token+"[page_number]")
						embed.add_field(name='Description',value='List name and the abbreviation of all upgrades.\n'+
							'**[page_number]**: Required. Select a page number to list upgrades.\n')
					else:
						embed.add_field(name='Error',value="Invalid command.")
						 
			if command == 'upgrade':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[upgrade/abbr]')
				embed.add_field(name='Description',value='List name requested warship upgrade')
		else:
			embed.add_field(name='Error',value="Invalid command.")
		return embed
	
	async def on_message(self,message):
		channel = message.channel
		arg = message.content.split(token)
		if message.content.startswith("<@!"+str(self.user.id)+">"):
			print(f"User {message.author} requested my help.")
			embed = self.help_message(command_header+token+"help"+token+"help")
			if not embed is None:
				print(f"sending help message")
				await channel.send("はい、サラはここに。", embed=embed)
		if message.content.startswith(command_header+token):
			if DEBUG_IS_MAINTANCE and message.author != self.user and not message.author.name == 'mackwafang':
				await channel.send(self.user.display_name+" is under maintance. Please wait until maintance is over. Or contact Mack if he ~~fucks up~~ did an oopsie.")
				return
			request_type = arg[1:]
			print(f'User <{message.author}> in <{message.guild}, {message.channel}> requested command "<{request_type}>"')
			if arg[1] == command_list[0]:
				embed = self.help_message(message.content+token+"help")
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
						name, nation, images, ship_type, tier, upgrades, skills = get_ship_data(ship)
						print(f"returning ship information for <{name}>")
						ship_type = ship_type if ship_type != 'AirCarrier' else 'Aicraft Carrier'
						embed = discord.Embed(title="Warship Information")
						embed.set_thumbnail(url=images['small'])
						embed.add_field(name='Name', value=name)
						embed.add_field(name='Nation', value=iso_country_code[nation])
						embed.add_field(name='Type', value=ship_type)
						embed.add_field(name='Tier', value=tier)
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
										upgrade_name = get_upgrade_data(upgrade)
									except: 
										upgrade_name = upgrade+" [!]"
								m += f'(Slot {i}) **'+upgrade_name+'**\n'
								i += 1
							embed.add_field(name='Suggested Upgrades', value=m)
						if len(skills) > 0:
							m = ""
							i = 1
							for skill in skills:
								skill_name = "[Missing]"
								try: # ew, nested try/catch
									skill_name, id, skill_type, perk, tier, icon = get_skill_data(skill)
								except: 
									skill_name = skill+" [!]"
								m += f'(Tier {tier}) **'+skill_name+'**\n'
								i += 1
							embed.add_field(name='Suggested Cmdr. Skills', value=m)
						embed.set_footer(text="[!]: If this is present next to an item, then this item is either entered incorrectly or not known to the WG's database. Contact Mack.\n"+
							"Suggested skills are listed in ascending acquiring order.")
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
								m = [skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list]
								embed.title="Commander Skills"
							elif len(arg) > 3:
								# asking for specific category
								if arg[3] == 'type':
									# get all skills of this type
									try:
										skill_type = arg[4] # get type
										embed.title = f"{skill_type.title()} Commander Skills"
										m = [f"(Tier {skill_list[i]['tier']}) "+skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['type_name'].lower() == skill_type.lower()]
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
										embed.title = f"Tier {tier} Commander Skills"
										m = [f"({skill_list[i]['type_name']}) "+skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['tier'] == tier]
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
								message_string = message.content
								embed = discord.Embed(title="Upgrade List")
								try:
									page = int(arg[3])
									output_list = [(i,upgrade_abbr_list[i]) for i in upgrade_abbr_list]
									output_list.sort()
									num_pages = len(output_list)
									items_per_page = 10
									m = [name.title()+f' ('+abbr.upper()+')'+chr(10) for abbr, name in output_list[(page-1)*items_per_page:min(len(output_list),page*items_per_page)]]
									
								except Exception as e:
									print(f"Exception {type(e)}", e)
						
						else:
							# something else detected
							print(f"{arg[2]} is not a known argument for command {arg[1]}.")
							embed = None
							error_message = f"Argument **{arg[2]}** is not a valid argument."
					else:
						send_help_message = True
						embed = self.help_message(command_header+token+"help"+token+arg[1])
				if not embed == None:
					if not send_help_message:
						m.sort()
						m = ''.join(m)
						embed.add_field(name='_',value=m)
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
						name = get_upgrade_data(upgrade)
						embed = discord.Embed(title="Ship Upgrade")
						embed.add_field(name='Name', value=name)
						embed.add_field(name='Slot',value='[Unavailable]')
						embed.add_field(name='Description',value='[Unavailable]')
						await channel.send(embed=embed)
					except:
						await channel.send(f"Upgrade **{upgrade}** is not understood.")
			if not arg[1] in command_list:
				await channel.send(f"I don't know command **{arg[1]}**. Please check the help page by tagging me or use **{command_header+token+command_list[0]}**")
client = Client()
try:
	client.run('NjY3ODY2MzkxMjMxMzMyMzUz.XiI94A.JjQtinUguaHFnu_XOWNokwZ0B6s')
except Exception as e:
	print(f"{type(e)}",e)