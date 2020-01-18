import discord
import wargaming
from numpy.random import randint

wows_encyclopedia = wargaming.WoWS('74309abd627a3082035c0be246f43086',region='na',language='en').encyclopedia
skill_list = wows_encyclopedia.crewskills()

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
	'good-bot',
	'ship',
	'skill',
	'whoami',
	'listskills'
)
# skill_type_list = ('Endurance','Attack','Support','Versatility')

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
	
	async def on_message(self,message):
		channel = message.channel
		if message.content.startswith(command_header+token):
			print(f'User <{message.author}> requested command "<{message.content[message.content.find(chr(45))+1:]}>"')
			if message.content.startswith(command_header+token+command_list[0]):
				# help message
				embed = discord.Embed(title="Command List")
				embed.add_field(name='command',value=''.join([i+'\n' for i in command_list]))
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
				
				
			if message.content.startswith(command_header+token+command_list[3]):
				# get information on requested skill
				message_string = message.content
				skill_found = False
				# message parse
				skill = message_string[message_string.rfind('-')+1:]
				try:
					# assuming input is full skill name
					for i in skill_list:
						if skill.lower() == skill_list[i]['name'].lower():
							skill_found = True
							break
					if skill_found:
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
						print(skill)
						for i in skill_list:
							if skill.lower() == skill_list[i]['name'].lower():
								skill_found = True
								break
						if skill_found:
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
				embed = discord.Embed(title="Commander List")
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