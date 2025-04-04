from typing import List

from discord import ui, ButtonStyle, Interaction

class ConfirmCorrectionButton(ui.Button['TicTacToe']):
	def __init__(self, name: str, value: str):
		super().__init__(style=ButtonStyle.green, label=name.title())
		self.name = name
		self.value = value

	# This function is called whenever this particular button is pressed
	# This is part of the "meat" of the game logic
	async def callback(self, interaction: Interaction):
		view = self.view

		await interaction.response.send_message(f"Confirmed. Getting information for {self.value.title()}.", ephemeral=True, delete_after=5)
		view.value = self.value
		view.stop()


class ConfirmCorrectionView(ui.View):
	def __init__(self, choices: List[str]):
		super().__init__(timeout=None)
		self.value = None
		self.choices = choices
		for i in choices:
			self.add_item(ConfirmCorrectionButton(i, i))