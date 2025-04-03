from discord import ui, ButtonStyle, Interaction

# Define a simple View that gives us a confirmation menu
class ConfirmCorrectionView(ui.View):
	def __init__(self, corrected_name: str):
		super().__init__(timeout=None)
		self.value = None
		self.corrected_name = corrected_name

	# When the confirm button is pressed, set the inner value to `True` and
	# stop the View from listening to more input.
	# We also send the user an ephemeral message that we're confirming their choice.
	@ui.button(label='Yes', style=ButtonStyle.green)
	async def confirm(self, interaction: Interaction, button: ui.Button):
		await interaction.response.send_message(f"Confirmed. Getting information for {self.corrected_name}.", ephemeral=True, delete_after=5)
		self.value = True
		self.stop()

	# This one is similar to the confirmation button except sets the inner value to `False`
	@ui.button(label='No', style=ButtonStyle.red)
	async def cancel(self, interaction: Interaction, button: ui.Button):
		await interaction.response.send_message("Doing nothing. \n-# You don't need to do anything.", ephemeral=True, delete_after=5)
		self.value = False
		self.stop()
