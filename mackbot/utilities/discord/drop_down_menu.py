from discord import Interaction, Message
from discord.ui import View, Select, select

# drop down menu from discord 2.0
class UserSelection(View):
	def __init__(self, author: Message.author, timeout: int, placeholder: str, options: list[select]):
		self.select_menu = self.DropDownSelect(placeholder, options)
		self.response = -1
		self.author = author
		super().__init__(timeout=timeout)
		super().add_item(self.select_menu)

	async def disable_component(self) -> None:
		for child in self.children:
			child.disabled = True
		if self.message is not None:
			await self.message.edit(view=self)

	async def on_timeout(self) -> None:
		self.select_menu.placeholder = "Response Expired"
		await self.disable_component()

	async def interaction_check(self, interaction: Interaction) -> bool:
		if interaction.user.id == self.author.id:
			await self.disable_component()
			return True
		return False

	class DropDownSelect(Select):
		def __init__(self, placeholder: str, options: list[select]):
			super().__init__(placeholder=placeholder, options=options)

		async def callback(self, interaction: Interaction) -> None:
			self.view.response = self.values[0]
			await interaction.response.defer()
			await self.view.disable_component()
			self.view.stop()


async def get_user_response_with_drop_down(view: View) -> int:
	"""
		Wait for a user message or if user selected an item from the drop-down menu
		Args:
			view : A Discord UI View object

		Returns:
			int: The value of the user selected item. Returns -1 if: A message is not attached to the view object or if view timed out.
	"""
	await view.wait()
	if view.message is None:
		return -1
	else:
		return int(view.response)