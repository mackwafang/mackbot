import discord

headder_name = 'buildbot'
token = '-'

command_list = {
	
}

class Client(discord.Client):
	async def on_ready(self):
		print("Logged on")
		
	async def on_message(self,message):
		print(message)
		channel = message.channel
		if message.content.startswith(headder_name+token+'help'):
			await channel.send("Beep bop. I'm a bot Mack created.") # block until message is sent
		
client = Client()
client.run('NjY3ODY2MzkxMjMxMzMyMzUz.XiI94A.JjQtinUguaHFnu_XOWNokwZ0B6s')