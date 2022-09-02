import discord


class Setup(discord.ui.View):
	def __init__(self, user_id):
		super().__init__()
		self.value = None
		self.user_id = user_id

	# When the confirm button is pressed, set the inner value to `True` and
	# stop the View from listening to more input.
	# We also send the user an ephemeral message that we're confirming their choice.
	@discord.ui.button(label='All', style=discord.ButtonStyle.green)
	async def all(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return
		await interaction.response.defer()
		self.value = 'all'
		self.stop()

	# This one is similar to the confirmation button except sets the inner value to `False`
	@discord.ui.button(label='Punishments', style=discord.ButtonStyle.blurple)
	async def punishments(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return
		await interaction.response.defer()
		self.value = 'punishments'
		self.stop()
	
	@discord.ui.button(label='Staff Management', style=discord.ButtonStyle.blurple)
	async def staff_management(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return
		await interaction.response.defer()
		self.value = 'staff management'
		self.stop()

	@discord.ui.button(label='Shift Management', style=discord.ButtonStyle.blurple)
	async def shift_management(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return
		await interaction.response.defer()
		self.value = 'shift management'
		self.stop()

class YesNoMenu(discord.ui.View):
	def __init__(self, user_id):
		super().__init__()
		self.value = None
		self.user_id = user_id

	# When the confirm button is pressed, set the inner value to `True` and
	# stop the View from listening to more input.
	# We also send the user an ephemeral message that we're confirming their choice.
	@discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
	async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return
		await interaction.response.defer()
		for item in self.children:
			item.disabled = True
		self.value = True
		self.stop()

	# This one is similar to the confirmation button except sets the inner value to `False`
	@discord.ui.button(label='No', style=discord.ButtonStyle.danger)
	async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return
		await interaction.response.defer()
		for item in self.children:
			item.disabled = True
		self.value = False
		self.stop()

class Dropdown(discord.ui.Select):
	def __init__(self, user_id):
		self.user_id = user_id
		options = [
			discord.SelectOption(
				label="Staff Management",
				value="staff_management",
				description="Inactivity Notices, and managing staff members"
			),
			discord.SelectOption(
				label="Anti-ping",
				value="antiping",
				description="Responding to certain pings, ping immunity"
			),
			discord.SelectOption(
				label="Punishments",
				value="punishments",
				description="Punishing community members for rule infractions"
			),
			discord.SelectOption(
				label="Shift Management",
				value="shift_management",
				description="Shifts (duty on, duty off), and where logs should go"
			),
			discord.SelectOption(
				label="Verification",
				value="verification",
				description="Currently in active development"
			),
			discord.SelectOption(
				label="Customisation",
				value="customisation",
				description="Colours, branding, prefix, to customise to your liking"
			)
		]

		# The placeholder is what will be shown when no option is chosen
		# The min and max values indicate we can only pick one of the three options
		# The options parameter defines the dropdown options. We defined this above
		super().__init__(placeholder='Select a category', min_values=1, max_values=1, options=options)

	async def callback(self, interaction: discord.Interaction):
		if interaction.user.id == self.user_id:
			await interaction.response.defer()
			self.view.value = self.values[0]
			self.view.stop()

class CustomDropdown(discord.ui.Select):
	def __init__(self, user_id, options: list):
		self.user_id = user_id
		optionList = []

		for option in options:
			optionList.append(
				discord.SelectOption(
					label=option.replace('_', ' ').title(),
					value=option
				)
			)

		# The placeholder is what will be shown when no option is chosen
		# The min and max values indicate we can only pick one of the three options
		# The options parameter defines the dropdown options. We defined this above
		super().__init__(placeholder='Select an option', min_values=1, max_values=1, options=optionList)

	async def callback(self, interaction: discord.Interaction):
		if interaction.user.id == self.user_id:
			await interaction.response.defer()
			self.view.value = self.values[0]
			self.view.stop()
class SettingsSelectMenu(discord.ui.View):
	def __init__(self, user_id):
		super().__init__()
		self.value = None
		self.user_id = user_id

		self.add_item(Dropdown(self.user_id))

class CustomSelectMenu(discord.ui.View):
	def __init__(self, user_id, options: list):
		super().__init__()
		self.value = None
		self.user_id = user_id

		self.add_item(CustomDropdown(self.user_id, options))
