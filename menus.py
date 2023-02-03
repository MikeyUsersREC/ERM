import typing

import discord

from utils.utils import int_invis_embed, create_invis_embed

REQUIREMENTS = ["gspread", "oauth2client"]
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except:
    import os, pip

    pip_args = ['-vvv']
    try:
        proxy = os.environ['http_proxy']
    except KeyError:
        proxy = None
    if proxy:
        pip_args.append('--proxy')
        pip_args.append(proxy)
    pip_args.append('install')
    for req in REQUIREMENTS:
        pip_args.append(req)
    print('Installing requirements: ' + str(REQUIREMENTS))
    pip.main(args=pip_args)

    # do it again
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials


class Setup(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='All', style=discord.ButtonStyle.green)
    async def all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(create_invis_embed('You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'))
        await interaction.response.defer()
        self.value = 'all'
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Punishments', style=discord.ButtonStyle.blurple)
    async def punishments(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(create_invis_embed('You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'))
        await interaction.response.defer()
        self.value = 'punishments'
        self.stop()

    @discord.ui.button(label='Staff Management', style=discord.ButtonStyle.blurple)
    async def staff_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(create_invis_embed('You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'))
        await interaction.response.defer()
        self.value = 'staff management'
        self.stop()

    @discord.ui.button(label='Shift Management', style=discord.ButtonStyle.blurple)
    async def shift_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(create_invis_embed('You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'))
        await interaction.response.defer()
        self.value = 'shift management'
        self.stop()


class Dropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label="Staff Management",
                value="staff_management",
                emoji="<:staff:1035308057007230976>",
                description="Inactivity Notices, and managing staff members"
            ),
            discord.SelectOption(
                label="Anti-ping",
                value="antiping",
                emoji="<:MessageIcon:1035321236793860116>",
                description="Responding to certain pings, ping immunity"
            ),
            discord.SelectOption(
                label="Punishments",
                value="punishments",
                emoji="<:MalletWhite:1035258530422341672>",
                description="Punishing community members for rule infractions"
            ),
            discord.SelectOption(
                label="Shift Management",
                value="shift_management",
                emoji="<:Search:1035353785184288788>",
                description="Shifts (duty on, duty off), and where logs should go"
            ),
            discord.SelectOption(
                label="Shift Types",
                value="shift_types",
                emoji="<:Search:1035353785184288788>",
                description="View and customise shift types"
            ),
            discord.SelectOption(
                label="Verification",
                value="verification",
                emoji="<:SettingIcon:1035353776460152892>",
                description="Roblox Verification, simplified!"
            ),
            discord.SelectOption(
                label="Game Logging",
                value="game_logging",
                emoji="<:SConductTitle:1053359821308567592>",
                description="Game Logging! Messages, STS, Events, and more!"
            ),
            discord.SelectOption(
                label="Customisation",
                value="customisation",
                emoji="<:FlagIcon:1035258525955395664>",
                description="Colours, branding, prefix, to customise to your liking"
            ),
            discord.SelectOption(
                label="Game Security",
                value="security",
                emoji="<:WarningIcon:1035258528149033090>",
                description="Anti-abuse detection, and security measures"
            ),
            discord.SelectOption(
                label="Privacy",
                value="privacy",
                description="Disable global warnings, privacy features"
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
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class ShiftModificationDropdown(discord.ui.Select):
    def __init__(self, user_id, other=False):
        self.user_id = user_id
        if other is False:
            options = [
                discord.SelectOption(
                    label="On Duty",
                    value="on",
                    emoji="<:CurrentlyOnDuty:1045079678353932398>",
                    description="Start your in-game shift"
                ),
                discord.SelectOption(
                    label="Toggle Break",
                    value="break",
                    emoji="<:Break:1045080685012062329>",
                    description="Taking a break? Toggle your break status"
                ),
                discord.SelectOption(
                    label="Off Duty",
                    value="off",
                    emoji="<:OffDuty:1045081161359183933>",
                    description="End your in-game shift"
                ),
                discord.SelectOption(
                    label="Void shift",
                    value="void",
                    emoji="<:TrashIcon:1042550860435181628>",
                    description="Void your in-game shift. This is irreversible."
                )
            ]
        else:
            options = [
                discord.SelectOption(
                    label="On Duty",
                    value="on",
                    emoji="<:CurrentlyOnDuty:1045079678353932398>",
                    description="Start their in-game shift"
                ),
                discord.SelectOption(
                    label="Toggle Break",
                    value="break",
                    emoji="<:Break:1045080685012062329>",
                    description="Taking a break? Toggle their break status"
                ),
                discord.SelectOption(
                    label="Off Duty",
                    value="off",
                    emoji="<:OffDuty:1045081161359183933>",
                    description="End their in-game shift"
                )
            ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Select an option', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.view.value = self.values[0]
            self.disabled = True
            for option in self.options:
                if option.value == self.values[0]:
                    option.default = True

            await interaction.message.edit(view=self.view)
            self.view.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

class AdministrativeActionsDropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label="Add time",
                value="add",
                emoji="<:Resume:1035269012445216858>",
                description="Add time to their current shift"
            ),
            discord.SelectOption(
                label="Remove time",
                value="remove",
                emoji="<:Pause:1035308061679689859>",
                description="Remove time from their current shift"
            ),
            discord.SelectOption(
                label="Void shift",
                value="void",
                emoji="<:WarningIcon:1035258528149033090>",
                description="Void their shift, and remove it from the leaderboard"
            ),
            discord.SelectOption(
                label="Clear Member Shifts",
                value="clear",
                emoji="<:TrashIcon:1042550860435181628>",
                description="Clear all of their shifts from the leaderboard"
            )

        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Administrative Actions', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.view.admin_value = self.values[0]
            self.disabled = True
            for option in self.options:
                if option.value == self.values[0]:
                    option.default = True

            for item in self.view.children:
                if isinstance(item, discord.ui.Select):
                    if item is not self:
                        item.disabled = True

            await interaction.message.edit(view=self.view)
            self.view.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

class CustomDropdown(discord.ui.Select):
    def __init__(self, user_id, options: list, limit=1):
        self.user_id = user_id
        optionList = []

        for option in options:
            if isinstance(option, str):
                optionList.append(
                    discord.SelectOption(
                        label=option.replace('_', ' ').title(),
                        value=option
                    )
                )
            elif isinstance(option, discord.SelectOption):
                optionList.append(option)

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Select an option', min_values=1, max_values=limit, options=optionList)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            if len(self.values) == 1:
                self.view.value = self.values[0]
            else:
                self.view.value = self.values
            self.view.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

class MultiDropdown(discord.ui.Select):
    def __init__(self, user_id, options: list):
        self.user_id = user_id
        optionList = []

        for option in options:
            if isinstance(option, str):
                optionList.append(
                    discord.SelectOption(
                        label=option.replace('_', ' ').title(),
                        value=option
                    )
                )
            elif isinstance(option, discord.SelectOption):
                optionList.append(option)

        print(optionList)

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Select an option', max_values=len(optionList), options=optionList)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            if len(self.values) == 1:
                self.view.value = self.values[0]
            else:
                self.view.value = self.values
            self.view.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

class SettingsSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

        self.add_item(Dropdown(self.user_id))


class ModificationSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

        self.add_item(ShiftModificationDropdown(self.user_id))

class AdministrativeSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.admin_value = None
        self.user_id = user_id

        self.add_item(ShiftModificationDropdown(self.user_id, other=True))
        self.add_item(AdministrativeActionsDropdown(self.user_id))

class YesNoMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='No', style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class YesNoExpandedMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Yes, continue', style=discord.ButtonStyle.primary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='I\'ll do this another time', style=discord.ButtonStyle.secondary)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class YesNoColourMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Yes', style=discord.ButtonStyle.primary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='No', style=discord.ButtonStyle.secondary)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class ColouredButton(discord.ui.Button):
    def __init__(self, user_id, label, style, emoji=None):
        super().__init__(label=label, style=style, emoji=emoji)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.view.value = self.label
            self.view.stop()
class ColouredMenu(discord.ui.View):
    def __init__(self, user_id, buttons: list[str]):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        for index, button in enumerate(buttons):
            if index == 0:
                self.add_item(ColouredButton(self.user_id, button, discord.ButtonStyle.primary, emoji=None))
            else:
                self.add_item(ColouredButton(self.user_id, button, discord.ButtonStyle.secondary, emoji=None))

class EnableDisableMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Enable', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Disable', style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class ShiftModify(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Add time (+)', style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "add"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Remove time (-)', style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label='End shift', style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "end"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label='Void shift', style=discord.ButtonStyle.danger)
    async def void(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "void"
        await interaction.edit_original_response(view=self)
        self.stop()

class ActivityNoticeModification(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Add time (+)', style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "add"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Remove time (-)', style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label='End Activity Notice', style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "end"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label='Void Activity Notice', style=discord.ButtonStyle.danger)
    async def void(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "void"
        await interaction.edit_original_response(view=self)
        self.stop()

class PartialShiftModify(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Add time (+)', style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "add"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Remove time (-)', style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()


class LOAMenu(discord.ui.View):
    def __init__(self, bot, roles, loa_roles, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.bot = bot
        if isinstance(roles, list):
            self.roles = roles
        elif isinstance(roles, int):
            self.roles = [roles]
        self.loa_role = loa_roles
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green, custom_id="loamenu:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not any(role in interaction.user.roles for role in self.roles):
            if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator and not interaction.user == interaction.guild.owner:
                embed = discord.Embed(
                    description=f'You do not have permissions to accept this person\'s request. If you believe to have received this message in error, please contact a server administrator.',
                    color=0x2e3136
                )
                await interaction.followup.send(embed=embed)
                return

        for item in self.children:
            item.disabled = True
            if item.label == "Accept":
                item.label = "Accepted"
            else:
                self.remove_item(item)
        s_loa = None
        for loa in await self.bot.loas.get_all():
            if loa['message_id'] == interaction.message.id and loa['guild_id'] == interaction.guild.id:
                s_loa = loa

        s_loa['accepted'] = True
        guild = self.bot.get_guild(s_loa['guild_id'])
        try:
            try:
                guild = self.bot.get_guild(s_loa['guild_id'])
                user = guild.get_member(s_loa['user_id'])
            except:
                try:
                    return await int_invis_embed(interaction, "User could not be found in the server.", ephemeral=True)
                except:
                    pass

            settings = await self.bot.settings.find_by_id(interaction.guild.id)
            mentionable = ""
            success = discord.Embed(
                title=f"<:CheckIcon:1035018951043842088> {s_loa['type']} Accepted",
                description=f"<:ArrowRight:1035003246445596774> Your {s_loa['type']} request in **{interaction.guild.name}** has been accepted.",
                color=0x71c15f
            )
            await user.send(embed=success)
        except:
            pass
        try:
            await self.bot.loas.update_by_id(s_loa)
            if isinstance(self.loa_role, int):
                role = [discord.utils.get(guild.roles, id=self.loa_role)]
            elif isinstance(self.loa_role, list):
                role = [discord.utils.get(guild.roles, id=role) for role in self.loa_role]

            for rl in role:
                if rl not in user.roles:
                    await user.add_roles(rl)

            self.value = True
        except:
            pass
        embed = interaction.message.embeds[0]
        embed.title = f"<:CheckIcon:1035018951043842088> {s_loa['type']} Accepted"
        embed.colour = 0x71c15f
        embed.set_footer(
            text=f'Staff Logging Module - Accepted by {interaction.user.name}#{interaction.user.discriminator}')

        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Deny', style=discord.ButtonStyle.danger, custom_id="loamenu:deny-EPHEMERAL")
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role in interaction.user.roles for role in self.roles):
            if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator and not interaction.user == interaction.guild.owner:
                await interaction.response.defer(ephemeral=True, thinking=True)
                embed = discord.Embed(
                    description=f'You do not have permissions to deny this person\'s request. If you believe to have received this message in error, please contact a server administrator.',
                    color=0x2e3136
                )
                await interaction.followup.send(embed=embed)

        await interaction.response.defer()

        modal = CustomModal(f'Reason for Denial', [
            ('value', (
                discord.ui.TextInput(
                    label='Reason for denial',
                    placeholder='Enter a reason for denying this person\'s request.',
                    required=True
                )
            ))
        ])
        await interaction.response.send_modal(modal)

        timeout = await modal.wait()
        if timeout:
            return

        reason = modal.value.value

        for item in self.children:
            if item.label == button.label:
                item.label = "Denied"
            item.disabled = True
        s_loa = None
        for loa in await self.bot.loas.get_all():
            if loa['message_id'] == interaction.message.id and loa['guild_id'] == interaction.guild.id:
                s_loa = loa
            if s_loa != None:
                print(s_loa)
                s_loa['denied'] = True
                s_loa['denial_reason'] = reason

                try:
                    guild = self.bot.get_guild(s_loa['guild_id'])
                    user = guild.get_member(s_loa['user_id'])
                except:
                    try:
                        return await interaction.followup.send(create_invis_embed(interaction, "User could not be found in the server."),
                                                     ephemeral=True)
                    except:
                        pass
                settings = await self.bot.settings.find_by_id(interaction.guild.id)
                mentionable = ""
                success = discord.Embed(
                    title=f"<:ErrorIcon:1035000018165321808> {s_loa['type']} Denied",
                    description=f"<:ArrowRight:1035003246445596774> Your {s_loa['type']} request in **{interaction.guild.name}** has been denied for **{reason}**.",
                    color=0xff3c3c
                )
                await user.send(embed=success)
                await self.bot.loas.update_by_id(s_loa)

        embed = interaction.message.embeds[0]
        embed.title = f"<:ErrorIcon:1035000018165321808> {s_loa['type']} Denied"
        embed.colour = 0xff3c3c
        embed.set_footer(
            text=f'Staff Logging Module - Denied by {interaction.user.name}#{interaction.user.discriminator}')

        await interaction.edit_original_response(embed=embed, view=self)
        self.value = True
        self.stop()


class AddReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    @discord.ui.button(label='Create a reminder', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            self.value = "create"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

class ManageReminders(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, CustomModal] = None

    @discord.ui.button(label='Create a reminder', style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            for item in self.children:
                item.disabled = True
            self.modal = CustomModal(f'Create a reminder', [
                ('name',
                 discord.ui.TextInput(
                        label='Name',
                        placeholder="Name of your reminder",
                        required=True
                 )
                ),
                (
                'content',
                    discord.ui.TextInput(
                        label='Content',
                        style=discord.TextStyle.long,
                        placeholder="Content of your reminder",
                        required=True
                    )
                ),
                (
                    'time',
                    discord.ui.TextInput(
                        label='Interval',
                        placeholder="What would you like you like the interval to be? (e.g. 5m)",
                        required=True,
                        style=discord.TextStyle.short
                    )
                )
            ])
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()
            self.value = "create"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label='Delete a reminder', style=discord.ButtonStyle.red)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            self.value = "delete"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class CustomisePunishmentType(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[CreatePunishmentType, DeletePunishmentType, None] = None

    @discord.ui.button(label='Create a punishment type', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = CreatePunishmentType()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            self.value = "create"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Delete a punishment type", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = DeletePunishmentType()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            self.value = "delete"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)




class AddCustomCommand(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.information = {}
        self.user_id = user_id
        self.view: typing.Union[MessageCustomisation, None] = None

    @discord.ui.button(label='Create a custom command', style=discord.ButtonStyle.secondary,
                       emoji="<:Resume:1035269012445216858>")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = CustomCommandSettings()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.information = {
                "name": modal.name.value
            }
            view = MessageCustomisation(interaction.user.id)
            self.view = view
            await interaction.message.edit(view=view)
            self.value = "create"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class MessageCustomisation(discord.ui.View):
    def __init__(self, user_id, data=None):
        super().__init__(timeout=None)
        if data is None:
            data = {}
        self.value: typing.Union[str, None] = None
        self.modal: typing.Union[discord.ui.Modal, None] = None
        self.newView: typing.Union[EmbedCustomisation, None] = None
        self.msg = None
        self.has_embeds = False
        if data != {}:
            msg = data['message']
            content = msg['content']
            embeds = msg.get('embeds')
            if embeds != []:
                self.has_embeds = True

        self.user_id = user_id

    @discord.ui.button(label='Set Message', style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def content(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetContent()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            await interaction.message.edit(content=modal.name.value)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label='Add Embed', style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def addembed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            if len(interaction.message.embeds) > 0:
                return await int_invis_embed(interaction,
                                             "You can only have one embed per custom command. This is a temporary restriction and will be removed soon.",
                                             ephemeral=True)

            newView = EmbedCustomisation(interaction.user.id, self)
            self.newView = newView
            await interaction.message.edit(view=newView, embed=discord.Embed(colour=0x2E3136, description="\u200b"))
            await int_invis_embed(interaction,
                                  'You can now customise your embed. Once you are done, click the "Finish" button to save your embed.\n\n`{user}` - Mention of the user running the command\n`{username}` - The name of the user running the command\n`{display_name}` - The nickname of the user running the command\n`{time}` - The current time, represented in the Discord format of timestamps\n`{server}` - The name of the current guild\n`{channel}` - The channel where the command is running.\n`{prefix}` - The prefix of the server\n\nNote that these prefixes will **not show in the preview** however will work when the command is run.',
                                  ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label='✅ Finish', style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            self.msg = interaction.message
            self.newView = self
            self.value = "finish"
            await int_invis_embed(interaction,
                                  'Your custom command has been created. You can now use it in your server by using `/custom run <name> [channel]`!',
                                  ephemeral=True)
            await interaction.message.delete()
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class EmbedCustomisation(discord.ui.View):
    def __init__(self, user_id, view=None):
        super().__init__(timeout=None)
        self.value: typing.Union[str, None] = None
        self.modal: typing.Union[discord.ui.Modal, None] = None
        self.msg = None
        self.user_id = user_id
        if view is not None:
            self.parent_view = view
        else:
            self.parent_view = None

    @discord.ui.button(label='Set Message', style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def content(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetContent()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            await interaction.message.edit(content=modal.name.value)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label='Remove Embed', style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def remove_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            if len(interaction.message.embeds) > 0:
                if self.parent_view is not None:
                    await interaction.message.edit(view=self.parent_view, embed=None)
                    await int_invis_embed(interaction, 'Embed removed.', ephemeral=True)
                else:
                    newView = MessageCustomisation(interaction.user.id)
                    self.parent_view = newView
                    await interaction.message.edit(view=newView, embed=None)
                    return await int_invis_embed(interaction, 'Embed removed.', ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label='✅ Finish', style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            for item in self.children:
                item.disabled = True
            self.msg = interaction.message
            self.value = "finish"
            await int_invis_embed(interaction,
                                  'Your custom command has been created. You can now use it in your server by using `/custom run <name> [channel]`!',
                                  ephemeral=True)
            await interaction.message.edit(view=None)
            if self.parent_view is not None:
                self.parent_view.stop()
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Title", row=1, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetTitle()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.title = modal.name.value
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Description", row=1, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetDescription()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.description = modal.name.value
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Embed Colour", row=1, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetColour()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            try:
                embed.colour = modal.name.value
            except:
                try:
                    embed.colour = int(modal.name.value.replace('#', ''), 16)
                except:
                    return await int_invis_embed(interaction, "Invalid colour. Please try again.\n*Example: #ff0000*",
                                                 ephemeral=True)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Thumbnail", row=2, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_thumbnail(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetThumbnail()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            try:
                embed.set_thumbnail(url=modal.thumbnail.value)
            except:
                return await int_invis_embed(interaction, "Invalid URL. Please try again.", ephemeral=True)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Image", row=2, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetImage()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            try:
                embed.set_image(url=modal.image.value)
            except:
                return await int_invis_embed(interaction, "Invalid URL. Please try again.", ephemeral=True)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Add Field", row=3, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = AddField()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            try:
                inline = modal.inline.value
                if inline.lower() in ['yes', 'y', 'true']:
                    inline = True
                elif inline.lower() in ['no', 'n', 'false']:
                    inline = False
                else:
                    inline = False
                embed.add_field(name=modal.name.value, value=modal.value.value, inline=inline)
            except:
                return await int_invis_embed(interaction, "Invalid field. Please try again.", ephemeral=True)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Footer", row=3, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetFooter()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            try:
                embed.set_footer(text=modal.name.value, icon_url=modal.icon.value)
            except:
                return await int_invis_embed(interaction, "Invalid footer. Please try again.", ephemeral=True)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)

    @discord.ui.button(label="Set Author", row=3, style=discord.ButtonStyle.secondary,
                       emoji="<:ArrowRight:1035003246445596774>")
    async def set_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetAuthor()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            try:
                embed.set_author(name=modal.name.value, url=modal.url.value, icon_url=modal.icon.value)
            except:
                return await int_invis_embed(interaction, "Invalid author. Please try again.", ephemeral=True)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class RemoveReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    @discord.ui.button(label="Delete a reminder", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            self.value = "delete"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class RemoveCustomCommand(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    @discord.ui.button(label="Delete a custom command", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
            self.value = "delete"
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class RemoveWarning(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.bot = bot
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Removed Punishment",
            description="<:ArrowRightW:1035023450592514048>I've successfully removed the punishment from the user.",
            color=0x71c15f
        )

        await interaction.edit_original_response(embed=success, view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='No', style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False

        success = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRightW:1035023450592514048>The punishment has not been removed from the user.",
            color=0xff3c3c
        )

        await interaction.edit_original_response(embed=success, view=self)
        self.stop()


class RequestReason(discord.ui.Modal, title="Edit Reason"):
    name = discord.ui.TextInput(label='Reason')

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class RequestData(discord.ui.Modal, title="Edit Reason"):
    data = discord.ui.TextInput(label='Reason')

    def __init__(self, title="PLACEHOLDER", label="PLACEHOLDER"):
        self.data.label = label
        super().__init__(title=title)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class CustomModal(discord.ui.Modal, title="Edit Reason"):
    def __init__(self, title, options):
        super().__init__(title=title)
        self.saved_items = {}

        for name, option in options:
            self.add_item(option)
            self.saved_items[name] = option


    async def on_submit(self, interaction: discord.Interaction):
        for key, item in self.saved_items.items():
            setattr(self, key, item)

        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()



class SetContent(discord.ui.Modal, title="Set Message Content"):
    name = discord.ui.TextInput(label='Content', placeholder="Content of the message", max_length=2000,
                                style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class CreatePunishmentType(discord.ui.Modal, title="Create Punishment Type"):
    name = discord.ui.TextInput(label='Name', placeholder="e.g. Verbal Warning", max_length=20,
                                style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.stop()


class DeletePunishmentType(discord.ui.Modal, title="Delete Punishment Type"):
    name = discord.ui.TextInput(label='Name', placeholder="e.g. Verbal Warning", max_length=20,
                                style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class RobloxUsername(discord.ui.Modal, title="Verification"):
    name = discord.ui.TextInput(label='Roblox Username', placeholder="e.g. RoyalCrests", max_length=32,
                                style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.stop()


class SetTitle(discord.ui.Modal, title="Set Embed Title"):
    name = discord.ui.TextInput(label='Title', placeholder="Title of the embed", style=discord.TextStyle.short)
    url = discord.ui.TextInput(label="Title URL", placeholder="URL of the title", style=discord.TextStyle.short,
                               required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class CustomCommandSettings(discord.ui.Modal, title="Custom Command Settings"):
    name = discord.ui.TextInput(label='Custom Command Name', placeholder="e.g. ssu", style=discord.TextStyle.short,
                                max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class SetDescription(discord.ui.Modal, title="Set Embed Description"):
    name = discord.ui.TextInput(label='Description', placeholder="Description of the embed",
                                style=discord.TextStyle.long, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class SetColour(discord.ui.Modal, title="Set Embed Colour"):
    name = discord.ui.TextInput(label='Colour', placeholder="#2E3136", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class SetImage(discord.ui.Modal, title="Set Image"):
    image = discord.ui.TextInput(label='Image URL', placeholder="Image URL", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class AddField(discord.ui.Modal, title="Add Field"):
    name = discord.ui.TextInput(label='Field Name', placeholder="Field Name", style=discord.TextStyle.short)
    value = discord.ui.TextInput(label='Field Value', placeholder="Field Value", style=discord.TextStyle.short)
    inline = discord.ui.TextInput(label='Inline?', placeholder="Yes/No", default="Yes", style=discord.TextStyle.short,
                                  required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class SetFooter(discord.ui.Modal, title="Set Footer"):
    name = discord.ui.TextInput(label='Footer Text', placeholder="Footer Text", style=discord.TextStyle.short)
    icon = discord.ui.TextInput(label='Footer Icon URL', placeholder="Footer Icon URL", default="",
                                style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class SetAuthor(discord.ui.Modal, title="Set Author"):
    name = discord.ui.TextInput(label='Author Name', placeholder="Author Name", style=discord.TextStyle.short)
    url = discord.ui.TextInput(label='Author URL', placeholder="Author URL", default="", style=discord.TextStyle.short,
                               required=False)
    icon = discord.ui.TextInput(label='Author Icon URL', placeholder="Author Icon URL", default="",
                                style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class SetThumbnail(discord.ui.Modal, title="Set Thumbnail"):
    thumbnail = discord.ui.TextInput(label='Thumbnail URL', placeholder="Thumbnail URL", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class TimeRequest(discord.ui.Modal, title="Temporary Ban"):
    time = discord.ui.TextInput(label='Time (s/m/h/d)')

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()


class ChangeWarningType(discord.ui.Select):
    def __init__(self, user_id, options: list):
        self.user_id: int = user_id

        selected_options = []
        using_options = False
        for option in options:
            if isinstance(option, str | int):
                option = discord.SelectOption(label=str(option), value=str(option),
                                              emoji="<:MalletWhite:1035258530422341672>")
                selected_options.append(option)
                using_options = True
            elif isinstance(option, discord.SelectOption):
                option.emoji = "<:MalletWhite:1035258530422341672>"
                selected_options.append(option)
                using_options = True

        if not using_options:
            selected_options = [
                discord.SelectOption(
                    label="Warning",
                    value="Warn",
                    description="A warning, the smallest form of logged punishment",
                    emoji="<:WarningIcon:1035258528149033090>"
                ),
                discord.SelectOption(
                    label="Kick",
                    value="Kick",
                    description="Removing a user from the game, usually given after warnings",
                    emoji="<:MalletWhite:1035258530422341672>"
                ),
                discord.SelectOption(
                    label="Ban",
                    value="Ban",
                    description="A permanent form of removing a user from the game, given after kicks",
                    emoji="<:MalletWhite:1035258530422341672>"
                ),
                discord.SelectOption(
                    label="Temporary Ban",
                    value="Temporary Ban",
                    description="Given after kicks, not enough to warrant a permanent removal",
                    emoji="<:Clock:1035308064305332224>"
                ),
                discord.SelectOption(
                    label="BOLO",
                    value="BOLO",
                    description="Cannot be found in the game, be on the lookout",
                    emoji="<:Search:1035353785184288788>"
                ),
            ]
        super().__init__(placeholder='Select a warning type', min_values=1, max_values=1, options=selected_options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            if self.values[0] == "Temporary Ban":
                modal = TimeRequest()
                await interaction.response.send_modal(modal)
                seconds = 0
                if modal.time.value.endswith('s', 'm', 'h', 'd'):
                    if modal.time.value.endswith('s'):
                        seconds = int(modal.time.value.removesuffix('s'))
                    elif modal.time.value.endswith('m'):
                        seconds = int(modal.time.value.removesuffix('m')) * 60
                    elif modal.time.value.endswith('h'):
                        seconds = int(modal.time.value.removesuffix('h')) * 60 * 60
                    else:
                        seconds = int(modal.time.value.removesuffix('d')) * 60 * 60 * 24
                else:
                    seconds = int(modal.time.value)
            await interaction.response.defer()
            try:
                self.view.value = [self.values[0], seconds]
            except:
                self.view.value = self.values[0]
            self.view.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class EditWarningSelect(discord.ui.Select):

    def __init__(self, user_id: int, inherited_options: list):
        self.user_id: int = user_id
        self.inherited_options = inherited_options

        options = [
            discord.SelectOption(
                label="Edit reason",
                value="edit",
                emoji="<:EditIcon:1042550862834323597>",
                description="Edit the reason of the punishment"
            ),
            discord.SelectOption(
                label="Change punishment type",
                value="change",
                emoji="<:EditIcon:1042550862834323597>",
                description="Change the punishment type to a higher or lower severity"
            ),
            discord.SelectOption(
                label="Delete punishment",
                value="delete",
                emoji="<:TrashIcon:1042550860435181628>",
                description="Delete the punishment from the database. This is irreversible."
            )
        ]

        super().__init__(placeholder='Select an option', min_values=1, max_values=1, options=options)

    # This one is similar to the confirmation button except sets the inner value to `False`
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            self.view.value = self.values[0]
            if self.view.value == "edit":
                if interaction.user.id != self.user_id:
                    return
                # await interaction.response.defer()
                for item in self.view.children:
                    item.disabled = True
                self.view.value = "edit"

                self.view.modal = RequestReason()
                await interaction.response.send_modal(self.view.modal)
                await self.view.modal.wait()
                self.view.further_value = self.view.modal.name.value
                self.view.stop()
            elif self.view.value == "change":
                if interaction.user.id != self.user_id:
                    return
                for item in self.view.children:
                    item.disabled = True
                self.value = "type"
                view = WarningDropdownMenu(interaction.user.id, self.inherited_options)
                await int_invis_embed(interaction, "What type would you like the punishment to be?", view=view)
                await view.wait()
                self.view.further_value = view.value

                self.view.stop()
            elif self.view.value == "delete":
                if interaction.user.id != self.user_id:
                    return
                await interaction.response.defer()
                for item in self.view.children:
                    item.disabled = True
                self.value = "delete"
                await interaction.edit_original_response(view=self.view)
                self.view.stop()
            else:
                await int_invis_embed(interaction, "You have not picked an option.")
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class EditWarning(discord.ui.View):
    def __init__(self, bot, user_id, options):
        super().__init__(timeout=None)
        self.value: typing.Union[None, str] = None
        self.bot: typing.Union[discord.ext.commands.Bot, discord.ext.commands.AutoShardedBot] = bot
        self.user_id: int = user_id
        self.modal: typing.Union[None, discord.ui.Modal] = None
        self.further_value: typing.Union[None, str] = None
        self.options = options
        self.add_item(EditWarningSelect(user_id, options))


class RemoveBOLO(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
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

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Removed BOLO",
            description="<:ArrowRightW:1035023450592514048>I've successfully removed the BOLO from the user.",
            color=0x71c15f
        )

        await interaction.edit_original_response(embed=success, view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='No', style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False

        success = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRightW:1035023450592514048>The punishment has not been removed from the user.",
            color=0xff3c3c
        )

        await interaction.edit_original_response(embed=success, view=self)
        self.stop()


class EnterRobloxUsername(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, RobloxUsername] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Verify', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        self.modal = RobloxUsername()
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stop()


class RequestDataView(discord.ui.View):
    def __init__(self, user_id, title: str, label: str):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, RequestData] = None
        self.title = title
        self.label = label
        for item in self.children:
            item.label = self.title

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Enter Strike Amount", style=discord.ButtonStyle.secondary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        self.modal = RequestData(self.title, self.label)
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stop()

class CustomModalView(discord.ui.View):
    def __init__(self, user_id, title: str, label: str, options: typing.List[typing.Tuple[str, discord.ui.TextInput]]):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, CustomModal] = None
        self.title = title
        self.label = label
        self.options = options

        for item in self.children:
            item.label = self.title

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Enter Strike Amount", style=discord.ButtonStyle.secondary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        self.modal = CustomModal(self.label, self.options)
        print(self.options)
        print(self.modal.children)
        print(self.modal)
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stop()



class LinkView(discord.ui.View):
    def __init__(self, label: str, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label=label, url=url))


class RequestGoogleSpreadsheet(discord.ui.View):
    def __init__(self, user_id, config: dict, scopes: list, data: list, template: str, type="lb", additional_data=None, label="Google Spreadsheet"):
        print(type)
        if type:
            self.type = type
        else:
            self.type = "lb"
        print(additional_data)
        if additional_data:
            self.additional_data = additional_data
        else:
            self.additional_data = []

        super().__init__(timeout=None)
        self.user_id = user_id
        self.config = config
        self.scopes = scopes
        self.data = data
        self.template = template
        if label:
            for item in self.children:
                item.label = label


    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Google Spreadsheet", style=discord.ButtonStyle.secondary)
    async def googlespreadsheet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await int_invis_embed(interaction, "We are currently creating the Google spreadsheet, please wait.",
                              ephemeral=True)
        client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(self.config, self.scopes))
        sheet = client.copy(self.template, interaction.guild.name, copy_permissions=True)
        new_sheet = sheet.get_worksheet(0)
        try:
            new_sheet.update_cell(4, 2, f'=IMAGE("{interaction.guild.icon.url}")')
        except AttributeError:
            pass

        if self.type == "lb":
            cell_list = new_sheet.range('D13:H999')
        elif self.type == "ar":
            cell_list = new_sheet.range('D13:I999')
        from pprint import pprint
        pprint(cell_list)
        pprint(self.data)
        for c, n_v in zip(cell_list, self.data):
            c.value = str(n_v)

        pprint(cell_list)
        new_sheet.update_cells(cell_list, "USER_ENTERED")
        if self.type == "ar":
            LoAs = sheet.get_worksheet(1)
            LoAs.update_cell(4, 2, f'=IMAGE("{interaction.guild.icon.url}")')
            cell_list = LoAs.range('D13:H999')
            print(self.additional_data)
            for cell, new_value in zip(cell_list, self.additional_data):
                if isinstance(new_value, int):
                    cell.value = f"=({new_value}/ 86400 + DATE(1970, 1, 1))"
                else:
                    cell.value = str(new_value)
            LoAs.update_cells(cell_list, "USER_ENTERED")

        sheet.share(None, perm_type='anyone', role='writer')

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Google Spreadsheet",
            description=f"<:ArrowRightW:1035023450592514048>I've successfully created a Google Spreadsheet for you. You can access it [here]({sheet.url}).",
            color=0x71c15f
        )
        view = LinkView("Open Google Spreadsheet", sheet.url)

        await interaction.edit_original_response(embed=success, view=view)

        self.stop()


class Verification(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, RobloxUsername] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Done!', style=discord.ButtonStyle.green, emoji="✅")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

        self.value = "done"
        self.stop()


class CustomSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

        self.add_item(CustomDropdown(self.user_id, options))


class WarningDropdownMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        new_options = []

        for option in options:
            if isinstance(option, discord.SelectOption):
                new_options.append(option)
            else:
                if isinstance(option, dict):
                    new_options.append(discord.SelectOption(label=option['name'], value=option['name']))
                else:
                    new_options.append(discord.SelectOption(label=option, value=option))

        self.add_item(ChangeWarningType(self.user_id, new_options))


class MultiSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

        self.add_item(MultiDropdown(self.user_id, options))


class RoleSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.limit = 25

        for key, value in kwargs.items():
            if key == "limit":
                self.limit = value

        if self.limit > 1:
            self.placeholder = "Select roles"
        else:
            self.placeholder = "Select a role"

        for child in self.children:
            child.placeholder = self.placeholder
            child.max_values = self.limit
            child.min_values = 1

    @discord.ui.select(cls=discord.ui.RoleSelect)
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.value = select.values
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class UserSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.limit = 25

        for key, value in kwargs.items():
            if key == "limit":
                self.limit = value

        if self.limit > 1:
            self.placeholder = "Select users"
        else:
            self.placeholder = "Select a user"

        for child in self.children:
            child.placeholder = self.placeholder
            child.max_values = self.limit
            child.min_values = 1

    @discord.ui.select(cls=discord.ui.UserSelect)
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.value = select.values
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)



class ChannelSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id
        self.limit = 25

        for key, value in kwargs.items():
            if key == "limit":
                self.limit = value

        if self.limit > 1:
            self.placeholder = "Select channels"
        else:
            self.placeholder = "Select a channel"

        for child in self.children:
            child.placeholder = self.placeholder
            child.max_values = self.limit
            child.min_values = 1

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text])
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.value = select.values
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)


class CheckMark(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(emoji="✅", style=discord.ButtonStyle.gray)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(emoji='❎', style=discord.ButtonStyle.gray)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await interaction.followup.send(embed=create_invis_embed(
                'You are not the user that has initialised this menu. Only the user that has initialised this menu can use this menu.'), ephemeral=True)
        await interaction.response.defer()
        self.value = False
        self.stop()
