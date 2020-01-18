import discord
from numpy.random import randint

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

skill_type_list = ('Endurance','Attack','Support','Versatility')

# dictionary that stores skill name as key and a tuple (abbreviation, description, cost)
skill_list = {
	'priority target'									:	('pt',1,'The detection indicator displays the number of opponents that are currently aiming at your ship or squadron.', 1),
	'preventive maintenance'							:	('pm',1,'Reduces the risk of main turrets, torpedo tubes, steering gears, and engine becoming incapacitated.', 1),
	'expert loader'										:	('el',2,'Accelerates shell type switching if all main battery guns are loaded.', 1),
	'air supremacy'										:	('as',2,'Decreases aircraft servicing time.',1),
	'direction center for catapult aircraft'			:	('dcca',3,'More effective fighter squadrons.',1),
	'improved engine boost'								:	('ieb',3,'Increases the engine boost time for a carrier\'s squadrons.',1),
	'incoming fire alert'								:	('ifa',4,'desc',1),
	'last gasp'											:	('lg',4,'desc',1),
	
	'high alert'										:	('ha',1,'Hastens the next availability of the ship\'s Damage Control Party.', 2),
	'jack of all trades'								:	('jat',1,'Decreases the reload time of all ship and squadron consumables.', 2),
	'expert marksman'									:	('em',2,'Increases the rate of traverse of main gun turrets.', 2),
	'torpedo acceleration'								:	('ta',2,'Increases the speed of torpedoes launched from both ships and aircraft while reducing torpedo range.', 2),
	'smoke screen expert'								:	('sse',3,'Expands the smoke screen area.', 2),
	'improved engines'									:	('ie',3,'Increases the speed of a carrier\'s squadrons.',2),
	'adrenaline rush'									:	('ar',4,'desc', 2),
	'last stand'										:	('ls',4,'desc', 2),
	
	'basics of survivability'							:	('bos',1,'Accelerates repairs to modules, firefighting, and recovery from flooding.', 3),
	'survivability expert'								:	('se',1,'Increases both ship and aircraft HP, including fighters, depending on the ship or aircraft carrier tier.', 3),
	'torpedo armament expertise'						:	('tae',2,'Reduces reload time of torpedo tubes.	', 3),
	'aircraft armor'									:	('aa',2,'Reduces continuous damage to aircraft in all AA defense zones.',3),
	'basic fire training'								:	('bft',3,'Improves the performance of smaller main guns and all secondary and AA guns.', 3),
	'superintendent'									:	('s',3,'Increases capacity of consumables.', 3),
	'demolition expert'									:	('de',4,'desc', 3),
	'vigilance'											:	('v',4,'desc', 3),
	
	'manual secondary control for secondary armament'	:	('ms',1,'Greatly increases the effectiveness of secondary guns against the manually selected target.', 4),
	'fire prevention'									:	('fp',1,'Reduces the risk of fire. The maximum number of fires on a ship is reduced to three.', 4),
	'inertia fuse high explosive'						:	('ifhe',2,'ncreases the armor penetration of high explosive (HE) warheads, while decreasing the chance of setting the enemy ship on fire.', 4),
	'sight stabilization'								:	('ss',2,'Speeds up the aiming of a carrier\'s aircraft.',4),
	'advanced firing training'							:	('aft',3,'Extends firing range of main guns with a caliber up to and including 139mm and all secondary battery guns. Increases damage per second within the explosion radius of shells fired by large caliber (>85mm) AA guns.',4),
	'massive aa fire'									:	('maf',3,'Activation of a priority sector increases the amount of instantaneous damage only. Time to the next sector reinforcement is decreased.',4),
	'radio location'									:	('rl',4,'Shows the direction to the nearest enemy.', 4),
	'concealment expert'								:	('ce',4,'Reduces detectability range.', 4),
}

class Client(discord.Client):
	async def on_ready(self):
		print("Logged on")
		
	async def on_message(self,message):
		channel = message.channel
		if message.content.startswith(command_header+token+command_list[0]):
			# help message
			await channel.send(f'''
				List of commands:
				{''.join([i+chr(10) for i in command_list])}
			''') # block until message is sent
		if message.content.startswith(command_header+token+command_list[1]):
			# good bot
			r = randint(len(good_bot_messages))
			await channel.send(good_bot_messages[r]) # block until message is sent
		if message.content.startswith(command_header+token+command_list[2]):
			# get voted ship build
			message_string = message.content
			# message parse
			ship = message_string[message_string.rfind('-')+1:]
			print(ship)
		if message.content.startswith(command_header+token+command_list[3]):
			# get information on requested skill
			message_string = message.content
			skill_found = False
			# message parse
			skill = message_string[message_string.rfind('-')+1:]
			try:
				abbr, type, desc, cost = skill_list[skill.lower()]
				m = f'''
				---Commander Skill---
				{skill.title()} (Abbr. {abbr.upper()})
				Tier {cost} skill.
				{desc}
				'''
				await channel.send(m)
				skill_found = True
			except:
				pass
			# parsed item is probably an abbreviation, checking abbreviation
			if not skill_found:
				try:
					skill = [i for i in skill_list if skill_list[i][0] == skill][0]
					abbr, type, desc, cost = skill_list[skill.lower()]
					m = f'''---Commander Skill---
					{skill.title()} (Abbr. {abbr.upper()})
					Tier {cost} skill.
					{desc}
					'''
					await channel.send(m)
				except:
					await channel.send(f"Skill <{skill.title()}> is not understood.")
		if message.content.startswith(command_header+token+command_list[4]):
			# identify yourself, bot
			await channel.send("Beep bop. I'm a bot Mack created for the purpose of helping LODGE players with clan builds.") # block until message is sent
		if message.content.startswith(command_header+token+command_list[5]):
			# list skills
			await channel.send(f"List of Commander Skills in World of Warships:\n{''.join([i.title()+'('+skill_list[i][0].upper()+')'+chr(10) for i in skill_list])}")
		
client = Client()
try:
	client.run('NjY3ODY2MzkxMjMxMzMyMzUz.XiI94A.JjQtinUguaHFnu_XOWNokwZ0B6s')
except Exception as e:
	print(e)