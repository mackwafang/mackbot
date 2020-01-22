import discord
DEBUG_IS_MAINTANCE = False
import subprocess
import sys
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
print("Preprocessing Done")


command_header = 'mackbot'
token = '-'

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
	'listskills',
	'upgrade',
	'listupgrades',
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

class Client(discord.Client):
	async def on_ready(self):
		print("Logged on")
	
	def help_message(self,message):
		# help message
		command = message[message.rfind('-')+1:]
		print(command)
		if command in command_list:
			embed = discord.Embed(title=f"Command Help")
			embed.add_field(name='Command',value=command)
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
			if command == 'listskills':
				embed.add_field(name='Usage',value=command_header+token+command+token+"[type/tier] [type_name/tier_number]")
				embed.add_field(name='Description',value='List name and the abbreviation of the all commander skills.\n'+
					'**-type-[type_name]**: Optional. Returns all skills of indicated skill type. Acceptable values: [Attack, Endurance, Support, Versatility]\n'+
					'**-tier-[tier_number]**: Optional. Returns all skills of the indicated tier. Acceptable values: [1,2,3,4]')
			if command == 'upgrade':
				embed.add_field(name='Usage',value=command_header+token+command+token+'[upgrade/abbr]')
				embed.add_field(name='Description',value='List name requested warship upgrade')
			if command == 'listupgrades':
				embed.add_field(name='Usage',value=command_header+token+command+'[page]')
				embed.add_field(name='Description',value=' Indicate a page number 1-8 and this command will list name and the abbreviation of the warship upgrades in that page')
			return embed
		return None
	
	async def on_message(self,message):
		channel = message.channel
		arg = message.content.split('-')
		if message.content.startswith("<@!"+str(self.user.id)+">"):
			print(f"User {message.author} requested my help.")
			embed = self.help_message(command_header+token+command_list[0])
			if not embed is None:
				print(f"sending help message")
				await channel.send("はい、サラはここに。", embed=embed)
		if message.content.startswith(command_header+token):
			if DEBUG_IS_MAINTANCE and message.author != self.user and not message.author.name == 'mackwafang':
				await channel.send(self.user.display_name+" is under maintance. Please wait until maintance is over. Or contact Mack if he ~~fucks up~~ did an oopsie.")
				return
			request_type = arg[1:]
			print(f'User <{message.author}> requested command "<{request_type}>"')
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
				ship = arg[2]
				ship_found = False
				if ship == command_list[2]:
					embed = self.help_message(command_header+token+command_list[2])
					if not embed is None:
						await channel.send(embed=embed)
				else:
					try:
						for i in ship_list:
							ship_name_in_dict = ship_list[i]['name']
							if ship.lower() in ship_name_to_ascii: #is the name suppose to include non-ascii character?
								ship = ship_name_to_ascii[ship.lower()] # convert to the appropiate name
							# print(ship.lower(),ship_name_in_dict.lower())
							if ship.lower() == ship_name_in_dict.lower():
								ship_found = True
								break
						if ship_found:
							name, nation, images, ship_type, tier = ship_list[i].values()
							print(f"returning ship information for <{name}>")
							ship_type = ship_type if ship_type != 'AirCarrier' else 'Aicraft Carrier'
							embed = discord.Embed(title="Warship Information")
							embed.set_thumbnail(url=images['small'])
							embed.add_field(name='Name', value=name,inline=True)
							embed.add_field(name='Nation', value=iso_country_code[nation],inline=True)
							embed.add_field(name='Type', value=ship_type,inline=True)
							embed.add_field(name='Tier', value=tier,inline=True)
							await channel.send(embed=embed)
						else:
							await channel.send(f"Ship <{ship}> is not understood")
					except Exception as e:
						print(f"Exception {type(e)}: ",e)
			if arg[1] == command_list[3]:
				# get information on requested skill
				message_string = message.content
				skill_found = False
				# message parse
				skill = arg[2] #message_string[message_string.rfind('-')+1:]
				if skill == command_list[3]:
					embed = self.help_message(command_header+token+command_list[3])
					if not embed is None:
						await channel.send(embed=embed)
				else:
					try:
						# assuming input is full skill name
						for i in skill_list:
							if skill.lower() == skill_list[i]['name'].lower():
								skill_found = True
								break
						if skill_found:
							print(f'sending message for skill <{skill}>')
							name, id, skill_type, perk, tier, icon = skill_list[i].values()
							embed = discord.Embed(title="Commander Skill")
							embed.set_thumbnail(url=icon)
							embed.add_field(name='Skill Name', value=name)
							embed.add_field(name='Tier', value=tier)
							embed.add_field(name='Category', value=skill_type)
							embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk))
							await channel.send(embed=embed)
					except Exception as e:
						print(f"Exception {type(e)}: ",e)
						if e == discord.Forbidden:
							channel.send('I do not have the proper permission :\(')
					# parsed item is probably an abbreviation, checking abbreviation
					if not skill_found:
						try:
							skill = skill_name_abbr[skill.lower()]
							for i in skill_list:
								if skill.lower() == skill_list[i]['name'].lower():
									skill_found = True
									break
							if skill_found:
								print(f'sending message for skill <{skill}>')
								name, id, skill_type, perk, tier, icon = skill_list[i].values()
								embed = discord.Embed(title="Commander Skill")
								embed.set_thumbnail(url=icon)
								embed.add_field(name='Skill Name', value=name)
								embed.add_field(name='Tier', value=tier)
								embed.add_field(name='Category', value=skill_type)
								embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk))
								await channel.send(embed=embed)
						except Exception as e:
							print(f"Exception {type(e)}: ",e)
							await channel.send(f"Skill <{skill.title()}> is not understood.")
			if arg[1] == command_list[4]: #message.content.startswith(command_header+token+command_list[4]):
				# identify yourself, bot
				await channel.send("Beep bop. I'm a bot Mack created for the purpose of helping LODGE players with clan builds.") # block until message is sent
			if arg[1] == command_list[5]: #message.content.startswith(command_header+token+command_list[5]):
				# list skills
				embed = discord.Embed(title="Commander Skill List")
				message_string = message.content
				m = [skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list]
				message_success = False
				if len(arg) >= 3:
					# asking for specific category, modifies message to something else
					if arg[2] == 'type':
						# get all skills of this type
						try:
							skill_type = arg[3]
							embed.title = f"{skill_type.title()} Commander Skills"
							m = [f"(Tier {skill_list[i]['tier']}) "+skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['type_name'].lower() == skill_type.lower()]
							message_success = True
						except Exception as e:
							m = ["Oops!"]
							print(e)
							if type(e) == IndexError:
								await channel.send(f"Please specify a skill type! Acceptable values: [Attack, Endurance, Support, Versatility]")
							else:
								print(f"Skill listing argument <{arg[3]}> is invalid.")
								await channel.send(f"Value {arg[3]} is not understood")
					elif arg[2] == 'tier':
						# get all skills of this tier
						try:
							tier = int(arg[3])
							embed.title = f"Tier {tier} Commander Skills"
							m = [f"({skill_list[i]['type_name']}) "+skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list if skill_list[i]['tier'] == tier]
							message_success = True
						except Exception as e:
							m = ["Oops!"]
							if type(e) == IndexError:
								await channel.send(f"Please specify a skill tier! Acceptable values: [1,2,3,4]")
							else:
								print(f"Skill listing argument <{arg[3]}> is invalid.")
								await channel.send(f"Value {arg[3]} is not understood")
					else:
						# not a known argument
						pass
				if message_success:
					m.sort()
					m = ''.join(m)
					embed.add_field(name='Skill (Abbr.)',value=m)
					await channel.send(embed=embed)
			if arg[1] == command_list[6]: #message.content.startswith(command_header+token+command_list[6]):
				# get information on requested upgrade
				message_string = message.content
				upgrade_found = False
				# message parse
				upgrade = arg[2] # message_string[message_string.rfind('-')+1:]
				if upgrade == command_list[6]:
					# argument is empty, send help message
					embed = self.help_message(command_header+token+command_list[6])
					if not embed is None:
						await channel.send(embed=embed)
				else:
					# user provided an argument
					try:
						# assuming input is full upgrade name
						for i in upgrade_list:
							if upgrade.lower() == upgrade_list[i].lower():
								upgrade_found = True
								break
						if upgrade_found:
							print(f'sending message for upgrade <{upgrade}>')
							name = upgrade_list[i]
							embed = discord.Embed(title="Ship Upgrade")
							embed.add_field(name='Name', value=name)
							await channel.send(embed=embed)
					except Exception as e:
						print(f"Exception {type(e)}: ",e)
						if e == discord.Forbidden:
							channel.send('I do not have the proper permission :\(')
					# parsed item is probably an abbreviation, checking abbreviation
					if not upgrade_found:
						try:
							upgrade = upgrade_abbr_list[upgrade.lower()]
							for i in upgrade_list:
								if upgrade.lower() == upgrade_list[i].lower():
									upgrade_found = True
									break
							if upgrade_found:
								print(f'sending message for upgrade <{upgrade}>')
								name = upgrade_list[i]
								embed = discord.Embed(title="Ship Upgrade")
								embed.add_field(name='Name', value=name)
								embed.add_field(name='Slot',value='[Unavailable]')
								embed.add_field(name='Description',value='[Unavailable]')
								await channel.send(embed=embed)
						except Exception as e:
							print(f"Exception {type(e)}: ",e)
							await channel.send(f"upgrade <{upgrade.title()}> is not understood.")
			if arg[1] == command_list[7]: #message.content.startswith(command_header+token+command_list[7]):
				# list upgrades
				message_string = message.content
				embed = discord.Embed(title="Upgrade List")
				try:
					page = arg[2] #message_string[message_string.rfind('-')+1:]
					# argument is a number
					if page == command_list[7]:
						# argument is empty, send help message
						embed = self.help_message(command_header+token+command_list[7])
						if not embed is None:
							await channel.send(embed=embed)
					else:
						page = int(page)
						output_list = [(i,upgrade_abbr_list[i]) for i in upgrade_abbr_list]
						output_list.sort()
						num_pages = len(output_list)
						items_per_page = 10
						m = [name.title()+f' ('+abbr.upper()+')'+chr(10) for abbr, name in output_list[(page-1)*items_per_page:min(len(output_list),page*items_per_page)]]
						m = ''.join(m)
					
						embed.add_field(name='Upgrade (Abbr.)',value=m)
						await channel.send(embed=embed)
				except Exception as e:
					# argument is something else
					print(f"Exception {type(e)}: ",e)
					await channel.send("Value given is not a valid value.")
		else:
			await channel.send(f"I don't know command **{command}**. Please check the help page by tagging me or use **{command_header+token+command_list[0]}**")
client = Client()
try:
	client.run('NjY3ODY2MzkxMjMxMzMyMzUz.XiI94A.JjQtinUguaHFnu_XOWNokwZ0B6s')
except Exception as e:
	print(e)