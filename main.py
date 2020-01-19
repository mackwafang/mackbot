import discord

import subprocess
import sys
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
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


command_header = 'buildbot'
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
	'listskills'
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
	'rl':'radio location',
}

class Client(discord.Client):
	async def on_ready(self):
		print("Logged on")
	
	def help_message(self,message):
		# help message
		command = message[message.rfind('-')+1:]
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
				embed.add_field(name='Usage',value=command_header+token+command+token+'[skill]')
				embed.add_field(name='Description',value='List name, type, tier and effect of the requested commander skill')
			if command == 'whoami':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='Who\'s this bot?')
			if command == 'listskills':
				embed.add_field(name='Usage',value=command_header+token+command)
				embed.add_field(name='Description',value='List name and the abbreviation of the all commander skills')
			return embed
		return None
	
	async def on_message(self,message):
		channel = message.channel
		if message.content.startswith(command_header+token):
			arg = message.content[message.content.find('-')+1:]
			print(f'User <{message.author}> requested command "<{arg}>"')
			if message.content.startswith(command_header+token+command_list[0]):
				embed = self.help_message(message.content)
				if not embed is None:
					await channel.send(embed=embed)
			if message.content.startswith(command_header+token+command_list[1]):
				# good bot
				r = randint(len(good_bot_messages))
				await channel.send(good_bot_messages[r]) # block until message is sent
			if message.content.startswith(command_header+token+command_list[2]):
				# get voted ship build
				message_string = message.content
				# message parse
				ship = message_string[message_string.rfind('-')+1:]
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
							name, nation, images, type, tier = ship_list[i].values()
							embed = discord.Embed(title="Warship Information")
							embed.set_thumbnail(url=images['small'])
							embed.add_field(name='Name', value=name,inline=True)
							embed.add_field(name='Nation', value=iso_country_code[nation],inline=True)
							embed.add_field(name='Type', value=type,inline=True)
							embed.add_field(name='Tier', value=tier,inline=True)
							await channel.send(embed=embed)
						else:
							await channel.send(f"Ship <{ship}> is not understood")
					except Exception as e:
						print(e)
			if message.content.startswith(command_header+token+command_list[3]):
				# get information on requested skill
				message_string = message.content
				skill_found = False
				# message parse
				skill = message_string[message_string.rfind('-')+1:]
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
							print(f'returning skill <{skill}>')
							name, id, type, perk, tier, icon = skill_list[i].values()
							embed = discord.Embed(title="Commander Skill")
							embed.set_thumbnail(url=icon)
							embed.add_field(name='Skill Name', value=name)
							embed.add_field(name='Tier', value=tier)
							embed.add_field(name='Category', value=type)
							embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk))
							await channel.send(embed=embed)
					except Exception as e:
						print(e)
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
								print(f'returning skill <{skill}>')
								name, id, type, perk, tier, icon = skill_list[i].values()
								embed = discord.Embed(title="Commander Skill")
								embed.set_thumbnail(url=icon)
								embed.add_field(name='Skill Name', value=name)
								embed.add_field(name='Tier', value=tier)
								embed.add_field(name='Category', value=type)
								embed.add_field(name='Description', value=''.join('- '+p["description"]+chr(10) for p in perk))
								await channel.send(embed=embed)
						except:
							await channel.send(f"Skill <{skill.title()}> is not understood.")
			if message.content.startswith(command_header+token+command_list[4]):
				# identify yourself, bot
				await channel.send("Beep bop. I'm a bot Mack created for the purpose of helping LODGE players with clan builds.") # block until message is sent
			if message.content.startswith(command_header+token+command_list[5]):
				# list skills
				embed = discord.Embed(title="Commander Skill List")
				m = [skill_list[i]['name']+' ('+''.join([c for c in skill_list[i]['name'] if 64 < ord(c) and ord(c) < 90])+')'+chr(10) for i in skill_list]
				m.sort()
				m = ''.join(m)
				embed.add_field(name='Skill (Abbr.)',value=m)
				await channel.send(embed=embed)
client = Client()
try:
	client.run('NjY3ODY2MzkxMjMxMzMyMzUz.XiI94A.JjQtinUguaHFnu_XOWNokwZ0B6s')
except Exception as e:
	print(e)