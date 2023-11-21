import asyncio
import datetime
import typing
import discord
import pytz
import roblox
from discord import Interaction
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials

from datamodels.ShiftManagement import ShiftItem
from utils.constants import blank_color, BLANK_COLOR, GREEN_COLOR, ORANGE_COLOR, RED_COLOR
from utils.timestamp import td_format
from utils.utils import int_invis_embed, int_failure_embed, int_pending_embed, time_converter, get_elapsed_time, \
    generalised_interaction_check_failure, generator
import gspread_asyncio

REQUIREMENTS = ["gspread", "oauth2client"]


class Setup(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="All", style=discord.ButtonStyle.green)
    async def all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()
        self.value = "all"
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Punishments", style=discord.ButtonStyle.blurple)
    async def punishments(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()
        self.value = "punishments"
        self.stop()

    @discord.ui.button(label="Staff Management", style=discord.ButtonStyle.blurple)
    async def staff_management(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()
        self.value = "staff management"
        self.stop()

    @discord.ui.button(label="Shift Management", style=discord.ButtonStyle.blurple)
    async def shift_management(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()
        self.value = "shift management"
        self.stop()


class Dropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label="Staff Management",
                value="staff_management",
                description="Inactivity Notices, and managing staff members",
            ),
            discord.SelectOption(
                label="Anti-ping",
                value="antiping",
                description="Responding to certain pings, ping immunity",
            ),
            discord.SelectOption(
                label="Punishments",
                value="punishments",
                description="Punishing community members for rule infractions",
            ),
            discord.SelectOption(
                label="Moderation Sync",
                value="moderation_sync",
                description="Syncing moderation actions from Roblox to Discord",
            ),
            discord.SelectOption(
                label="Shift Management",
                value="shift_management",
                description="Shifts (duty on, duty off), and where logs should go",
            ),
            discord.SelectOption(
                label="Shift Types",
                value="shift_types",
                description="View and customise shift types",
            ),
            discord.SelectOption(
                label="Verification",
                value="verification",
                description="Roblox Verification, simplified!",
            ),
            discord.SelectOption(
                label="Game Logging",
                value="game_logging",
                description="Game Logging! Messages, STS, Events, and more!",
            ),
            discord.SelectOption(
                label="Customisation",
                value="customisation",
                description="Colours, branding, prefix, to customise to your liking",
            ),
            discord.SelectOption(
                label="Game Security",
                value="security",
                description="Anti-abuse detection, and security measures",
            ),
            discord.SelectOption(
                label="Privacy",
                value="privacy",
                description="Disable global warnings, privacy features",
            ),
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Select a category", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.view.value = self.values[0]
            self.view.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)


class ShiftModificationDropdown(discord.ui.Select):
    def __init__(self, user_id, other=False):
        self.user_id = user_id
        if other is False:
            options = [
                discord.SelectOption(
                    label="On Duty",
                    value="on",
                    description="Start your in-game shift",
                ),
                discord.SelectOption(
                    label="Toggle Break",
                    value="break",
                    description="Taking a break? Toggle your break status",
                ),
                discord.SelectOption(
                    label="Off Duty",
                    value="off",
                    description="End your in-game shift",
                ),
                discord.SelectOption(
                    label="Void shift",
                    value="void",
                    description="Void your in-game shift. This is irreversible.",
                ),
            ]
        else:
            options = [
                discord.SelectOption(
                    label="On Duty",
                    value="on",
                    description="Start their in-game shift",
                ),
                discord.SelectOption(
                    label="Toggle Break",
                    value="break",
                    description="Taking a break? Toggle their break status",
                ),
                discord.SelectOption(
                    label="Off Duty",
                    value="off",
                    description="End their in-game shift",
                ),
            ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Select an option", min_values=1, max_values=1, options=options
        )

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
            return await generalised_interaction_check_failure(interaction.followup)


class AdministrativeActionsDropdown(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label="Add time",
                value="add",
                description="Add time to their current shift",
            ),
            discord.SelectOption(
                label="Remove time",
                value="remove",
                description="Remove time from their current shift",
            ),
            discord.SelectOption(
                label="Void shift",
                value="void",
                description="Void their shift, and remove it from the leaderboard",
            ),
            discord.SelectOption(
                label="Clear Member Shifts",
                value="clear",
                description="Clear all of their shifts from the leaderboard",
            ),
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Administrative Actions",
            min_values=1,
            max_values=1,
            options=options,
        )

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
            return await generalised_interaction_check_failure(interaction.followup)


class CustomDropdown(discord.ui.Select):
    def __init__(self, user_id, options: list, limit=1):
        self.user_id = user_id
        optionList = []

        for option in options:
            if isinstance(option, str):
                optionList.append(
                    discord.SelectOption(
                        label=option.replace("_", " ").title(), value=option
                    )
                )
            elif isinstance(option, discord.SelectOption):
                optionList.append(option)

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Select an option",
            min_values=1,
            max_values=limit,
            options=optionList,
        )

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
            return await generalised_interaction_check_failure(interaction.followup)


class MultiPaginatorDropdown(discord.ui.Select):
    def __init__(self, user_id, options: list, pages: dict, limit=1):
        self.user_id = user_id
        self.pages = pages
        optionList = []

        for option in options:
            if isinstance(option, str):
                optionList.append(
                    discord.SelectOption(
                        label=option.replace("_", " ").title(), value=option
                    )
                )
            elif isinstance(option, discord.SelectOption):
                optionList.append(option)

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Select an option",
            min_values=1,
            max_values=limit,
            options=optionList,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            await interaction.message.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{interaction.user.name},** you're currently viewing the **{self.values[0].replace('_', ' ').title()}** commands!",
                embed=self.pages.get(self.values[0]),
            )
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return


# noinspection PyUnresolvedReferences
class MultiDropdown(discord.ui.Select):
    def __init__(self, user_id, options: list):
        self.user_id = user_id
        optionList = []

        for option in options:
            if isinstance(option, str):
                optionList.append(
                    discord.SelectOption(
                        label=option.replace("_", " ").title(), value=option
                    )
                )
            elif isinstance(option, discord.SelectOption):
                optionList.append(option)

        # # print(optionList)

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Select an option",
            max_values=len(optionList),
            options=optionList,
        )

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
            await generalised_interaction_check_failure(interaction.followup)
            return


class SettingsSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

        self.add_item(Dropdown(self.user_id))


class ModificationSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.00)
        self.value = None
        self.user_id = user_id

        self.add_item(ShiftModificationDropdown(self.user_id))


class AdministrativeSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.00)
        self.value = None
        self.admin_value = None
        self.user_id = user_id

        self.add_item(ShiftModificationDropdown(self.user_id, other=True))
        self.add_item(AdministrativeActionsDropdown(self.user_id))


class YesNoMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class AcknowledgeMenu(discord.ui.View):
    def __init__(self, user_id, note: str):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        if note:
            for child in self.children:
                if child.label == "NOTE":
                    child.label = note

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="I acknowledge and understand", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="NOTE", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def note(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


class YesNoExpandedMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Yes, continue", style=discord.ButtonStyle.primary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(
        label="I'll do this another time", style=discord.ButtonStyle.secondary
    )
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class YesNoColourMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return

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
        else:
            await generalised_interaction_check_failure(interaction.response)
            return


class CustomExecutionButton(discord.ui.Button):
    def __init__(self, user_id, label, style, emoji=None, func=None, row=0):
        """

        A button used for custom execution functions. This is often used to subvert pagination limitations.

        :param user_id: the user who can use this button
        :param label: the label of the button
        :param style: style of the button : discord.ButtonStyle
        :param emoji: emoji of the button
        :param func: function to be executed when pressed
        """

        super().__init__(label=label, style=style, emoji=emoji, row=row)
        self.func = func
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            await self.func(interaction, self)
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)


class ColouredMenu(discord.ui.View):
    def __init__(self, user_id, buttons: list[str]):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        for index, button in enumerate(buttons):
            if index == 0:
                self.add_item(
                    ColouredButton(
                        self.user_id, button, discord.ButtonStyle.primary, emoji=None
                    )
                )
            else:
                self.add_item(
                    ColouredButton(
                        self.user_id, button, discord.ButtonStyle.secondary, emoji=None
                    )
                )


class EnableDisableMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Enable", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class LinkPathwayMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="ERM", style=discord.ButtonStyle.secondary)
    async def ERM(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "erm"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Bloxlink", style=discord.ButtonStyle.danger)
    async def Bloxlink(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "bloxlink"
        await interaction.edit_original_response(view=self)
        self.stop()


class ShiftModify(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Add time (+)", style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "add"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Remove time (-)", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label="End shift", style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "end"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label="Void shift", style=discord.ButtonStyle.danger)
    async def void(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "void"
        await interaction.edit_original_response(view=self)
        self.stop()


class ActivityNoticeModification(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Add time (+)", style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "add"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Remove time (-)", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label="End Activity Notice", style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "end"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label="Void Activity Notice", style=discord.ButtonStyle.danger)
    async def void(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "void"
        await interaction.edit_original_response(view=self)
        self.stop()


class PartialShiftModify(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Add time (+)", style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "add"
        await interaction.edit_original_response(view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Remove time (-)", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await generalised_interaction_check_failure(interaction.followup)
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()


class LOAMenu(discord.ui.View):
    def __init__(self, bot, roles, loa_roles, loa_object, user_id, code):

        super().__init__(timeout=None)
        self.value = None
        self.bot = bot
        self.loa_object = loa_object
        if isinstance(roles, list):
            self.roles = roles
        elif isinstance(roles, int):
            self.roles = [roles]
        self.loa_role = loa_roles
        self.user_id = user_id
        self.id = code

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(
        label="Accept", style=discord.ButtonStyle.green, custom_id="loamenu:accept"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await interaction.response.defer()
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not any(
                role in [r.id for r in interaction.user.roles] for role in self.roles
        ):
            # await interaction.response.defer(ephemeral=True, thinking=True)
            if (
                    not interaction.user.guild_permissions.manage_guild
                    and not interaction.user.guild_permissions.administrator
                    and not interaction.user == interaction.guild.owner
            ):
                await generalised_interaction_check_failure(interaction.followup)
                return
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        for item in self.children:
            item.disabled = True
            if item.label == "Accept":
                item.label = "Accepted"
            else:
                self.remove_item(item)
        await interaction.message.edit(view=self)
        s_loa = None
        # # print(self)
        # # print(self.bot)
        for loa in await self.bot.loas.get_all():
            if (
                    loa["message_id"] == interaction.message.id
                    and loa["guild_id"] == interaction.guild.id
            ):
                s_loa = loa

        s_loa["accepted"] = True
        guild = self.bot.get_guild(s_loa["guild_id"])

        user = guild.get_member(s_loa["user_id"])

        if not user:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Could not find member",
                    description="I could not find the staff member which requested this Leave of Absence.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        settings = await self.bot.settings.find_by_id(interaction.guild.id)
        mentionable = ""
        await user.send(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Activity Notice Accepted",
                description=f"Your {s_loa['type']} request in **{interaction.guild.name}** was accepted!",
                color=GREEN_COLOR
            )
        )

        try:
            await self.bot.loas.update_by_id(s_loa)
            if isinstance(self.loa_role, int):
                role = [discord.utils.get(guild.roles, id=self.loa_role)]
            elif isinstance(self.loa_role, list):
                role = [
                    discord.utils.get(guild.roles, id=role) for role in self.loa_role
                ]

            for rl in role:
                if rl not in user.roles:
                    await user.add_roles(rl)

            self.value = True
        except:
            pass
        embed = interaction.message.embeds[0]
        embed.title = (
            f"<:success:1163149118366040106> {s_loa['type']} Accepted"
        )
        embed.colour = GREEN_COLOR
        embed.set_footer(text=f"Accepted by {interaction.user.name}")

        await interaction.message.edit(
            embed=embed,
            view=None,
        )

        await self.bot.views.delete_by_id(self.id)
        await interaction.followup.send(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Request Accepted",
                description=f"You have successfully accepted this staff member's {s_loa['type']} Request.",
                color=GREEN_COLOR
            )
        )
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        custom_id="loamenu:deny",
    )
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(
                role in [r.id for r in interaction.user.roles] for role in self.roles
        ):
            if (
                    not interaction.user.guild_permissions.manage_guild
                    and not interaction.user.guild_permissions.administrator
                    and not interaction.user == interaction.guild.owner
            ):
                await interaction.response.defer(ephemeral=True, thinking=True)
                return await generalised_interaction_check_failure(interaction.followup)
        for item in self.children:
            item.disabled = True

        modal = CustomModal(
            f"Reason for Denial",
            [
                (
                    "value",
                    (
                        discord.ui.TextInput(
                            label="Reason for denial",
                            placeholder="Enter a reason for denying this person's request.",
                            required=True,
                        )
                    ),
                )
            ],
        )
        await interaction.response.send_modal(modal)

        timeout = await modal.wait()
        if timeout:
            return

        reason = modal.value.value

        for item in self.children:
            item.disabled = True
            if item.label == button.label:
                item.label = "Denied"
            else:
                self.remove_item(item)
        s_loa = None

        async for loa_item in self.bot.loas.db.find({
            "guild_id": interaction.guild.id,
            "message_id": interaction.message.id
        }):
            s_loa = loa_item

        if not s_loa:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Could not find LOA",
                    description="I could not find the activity notice associated with this menu."
                ),
                ephemeral=True
            )

        s_loa["denied"] = True
        s_loa["denial_reason"] = reason

        user = interaction.guild.get_member(s_loa["user_id"])
        if not user:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Could not find member",
                    description="I could not find the staff member who made this request."
                ),
                ephemeral=True,
            )

        await user.send(
            embed=discord.Embed(
                title="Activity Notice Denied",
                description=f"Your {s_loa['type']} request in **{interaction.guild.name}** was denied.\n**Reason:** {reason}",
                color=BLANK_COLOR
            )
        )
        await self.bot.loas.update_by_id(s_loa)

        embed = interaction.message.embeds[0]
        embed.title = f"{s_loa['type']} Denied"
        embed.colour = BLANK_COLOR
        embed.set_footer(text=f"Denied by {interaction.user.name}")

        await interaction.message.edit(embed=embed, view=None)
        self.value = False
        await self.bot.views.delete_by_id(self.id)

        self.stop()


class AddReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    @discord.ui.button(label="Create a reminder", style=discord.ButtonStyle.green)
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
            return await generalised_interaction_check_failure(interaction.followup)


class ManageReminders(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, CustomModal] = None

    @discord.ui.button(label="Create", style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            self.modal = CustomModal(
                f"Create a reminder",
                [
                    (
                        "name",
                        discord.ui.TextInput(
                            label="Name",
                            placeholder="Name of your reminder",
                            required=True,
                        ),
                    ),
                    (
                        "content",
                        discord.ui.TextInput(
                            label="Content",
                            style=discord.TextStyle.long,
                            placeholder="Content of your reminder",
                            required=True,
                        ),
                    ),
                    (
                        "time",
                        discord.ui.TextInput(
                            label="Interval",
                            placeholder="What would you like you like the interval to be? (e.g. 5m)",
                            required=True,
                            style=discord.TextStyle.short,
                        ),
                    ),
                ],
            )
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()
            self.value = "create"
            self.stop()
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            self.modal = CustomModal(
                f"Pause a reminder",
                [
                    (
                        "id_value",
                        discord.ui.TextInput(
                            label="ID",
                            placeholder="ID of your reminder",
                            required=True,
                        ),
                    ),
                ],
            )
            print(1261)
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()
            print(1264)
            self.value = "pause"
            self.stop()
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            self.modal = CustomModal(
                f"Delete a reminder",
                [
                    (
                        "id_value",
                        discord.ui.TextInput(
                            label="ID",
                            placeholder="ID of your reminder",
                            required=True,
                        ),
                    ),
                ],
            )
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()
            self.value = "delete"
            self.stop()
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)


class CustomisePunishmentType(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[
            CreatePunishmentType, DeletePunishmentType, None
        ] = None

    @discord.ui.button(label="Create", style=discord.ButtonStyle.green)
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
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
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
            return await generalised_interaction_check_failure(interaction.followup)


class CustomCommandModification(discord.ui.View):
    def __init__(self, user_id: int, command_data: dict):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.value = None
        self.command_data = command_data

    async def check_ability(self, message):
        if self.command_data.get('message', None) and self.command_data.get('name', None):
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False

            await message.edit(view=self)
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True
            await message.edit(view=self)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=BLANK_COLOR
            ), ephemeral=True)
            return False

    async def refresh_ui(self, message: discord.Message):
        embed = discord.Embed(
            title="Custom Commands",
            description=(
                "**Command Information**\n"
                f"<:replytop:1138257149705863209> **Command ID:** `{self.command_data['id']}`\n"
                f"<:replymiddle:1138257195121791046> **Command Name:** {self.command_data['name']}\n"
                f"<:replybottom:1138257250448855090> **Creator:** <@{self.command_data['author']}>\n"
                f"\n**Message:**\n"
                f"View the message below by clicking 'View Message'."
            ),
            color=BLANK_COLOR
        )
        await message.edit(embed=embed)

    @discord.ui.button(
        label="Edit Name",
        row=0
    )
    async def edit_custom_command_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomModal(
            "Edit Custom Command Name",
            [
                (
                    "name",
                    discord.ui.TextInput(
                        label="Custom Command Name",
                        max_length=50
                    )
                )
            ]
        )

        await interaction.response.send_modal(modal)
        await modal.wait()
        try:
            chosen_identifier = modal.name.value
        except ValueError:
            return

        if not chosen_identifier:
            return

        self.command_data['name'] = chosen_identifier
        await self.check_ability(interaction.message)
        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="View Message",
        row=0
    )
    async def view_custom_command_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        async def _return_failure():
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="No Message Found",
                    description="There is currently no message associated with this Custom Command.\nYou can add one using 'Edit Message'.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        view = discord.ui.View()
        for item in self.command_data.get('buttons') or []:
            view.add_item(
                discord.ui.Button(
                    label=item['label'],
                    url=item['url'],
                    row=item['row'],
                    style=discord.ButtonStyle.url
                )
            )

        if not self.command_data.get('message', None):
            return await _return_failure()

        if not self.command_data.get('message', {}).get('content', None) and not len(
                self.command_data.get('message', {}).get('embeds', [])) > 0:
            return await _return_failure()

        converted = []
        for item in self.command_data.get('message').get('embeds', []):
            converted.append(discord.Embed.from_dict(item))

        await interaction.followup.send(
            embeds=converted,
            content=self.command_data['message'].get('content', None),
            ephemeral=True,
            view=view
        )

    @discord.ui.button(
        label="Edit Message",
        row=0
    )
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MessageCustomisation(interaction.user.id, self.command_data.get('message', None), external=False,
                                    persist=False)
        view.sustained_interaction = interaction

        if not self.command_data.get('message', None):
            await interaction.response.send_message(
                view=view,
                ephemeral=True
            )
        else:
            converted = []
            for item in self.command_data.get('message', {}).get('embeds', []):
                converted.append(discord.Embed.from_dict(item))

            await interaction.response.send_message(
                content=self.command_data.get('message', {}).get('content', None),
                embeds=converted,
                view=view,
                ephemeral=True
            )

        await view.wait()
        if view.newView:
            await view.newView.wait()
            chosen_message = view.newView.msg
        else:
            chosen_message = view.msg

        new_content = chosen_message.content
        new_embeds = []
        for item in chosen_message.embeds or []:
            new_embeds.append(item.to_dict())

        self.command_data['message'] = {
            "content": new_content,
            "embeds": new_embeds
        }
        await self.check_ability(interaction.message)
        await self.refresh_ui(interaction.message)
        await (await interaction.original_response()).delete()

    @discord.ui.button(
        label="Edit Buttons",
        row=0
    )
    async def edit_buttons(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ButtonCustomisation(self.command_data, interaction.user.id)
        view.sustained_interaction = interaction

        if not self.command_data.get('message', None):
            await interaction.response.send_message(
                view=view,
                ephemeral=True
            )
        else:
            converted = []
            for item in self.command_data.get('message', {}).get('embeds', []):
                converted.append(discord.Embed.from_dict(item))

            await interaction.response.send_message(
                content=self.command_data.get('message', {}).get('content', None),
                embeds=converted,
                view=view,
                ephemeral=True
            )

        timeout = await view.wait()
        if timeout or not view.value:
            return

        print(view.command_data)
        self.command_data['buttons'] = view.command_data.get('buttons', [])
        await self.check_ability(interaction.message)
        await self.refresh_ui(interaction.message)
        await (await interaction.original_response()).delete()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        self.value = False
        pass

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        row=1,
        disabled=True
    )
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        self.value = True
        self.stop()


class ButtonCustomisation(discord.ui.View):
    def __init__(self, command_data: dict, user_id: int):
        super().__init__(timeout=600)
        for item in command_data.get('buttons') or []:
            self.add_item(
                discord.ui.Button(
                    label=item['label'],
                    url=item['url'],
                    row=item['row'],
                    style=discord.ButtonStyle.url
                )
            )

        self.command_data = command_data
        self.sustained_interaction = None
        self.value = None
        self.user_id = user_id

    @discord.ui.button(label="Add Button", row=4)
    async def add_button(self, interaction: discord.Interaction, _):
        if len(self.children) >= 25:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Limitation",
                    description="You can only have a maximum of 25 buttons per custom command.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        modal = CustomModal(
            "Add a Button",
            [
                (
                    "label",
                    discord.ui.TextInput(
                        label="Label",
                        max_length=80,
                        placeholder="Label of the button",
                        required=True
                    )
                ),
                (
                    "url",
                    discord.ui.TextInput(
                        label="URL",
                        max_length=500,
                        placeholder="URL of the button",
                        required=True
                    )
                ),
                (
                    "row",
                    discord.ui.TextInput(
                        label="Row",
                        placeholder="Row of the button (e.g. 0, 1, 2, 3)"
                    )
                )],
            {
                "ephemeral": True
            }
        )
        await interaction.response.send_modal(modal)
        await modal.wait()
        # Input validations
        if not all([i.isdigit() for i in modal.row.value.strip()]):
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid Row",
                    description="The row you provided is not a valid number.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        if int(modal.row.value.strip()) > 4:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid Row",
                    description="The row you provided must be within the range 0-4.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        if int(modal.row.value.strip()) < 0:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid Row",
                    description="The row you provided must be within the range 0-4.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        if not modal.label.value.strip():
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid Label",
                    description="The label you provided is not valid.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        if not modal.url.value.strip():
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid URL",
                    description="The URL you provided is not valid.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        if not any([modal.url.value.strip().startswith(prefix) for prefix in ["https://", "http://"]]):
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid URL",
                    description="The URL you provided is not valid.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )


        message = interaction.message
        if self.sustained_interaction:
            message = await self.sustained_interaction.original_response()

        relevant_item = discord.ui.Button(
            label=modal.label.value.strip(),
            url=modal.url.value.strip(),
            row=int(modal.row.value.strip()),
            style=discord.ButtonStyle.url
        )
        self.add_item(relevant_item)

        try:
            await message.edit(
                view=self
            )
        except discord.HTTPException:
            self.remove_item(relevant_item)
            return

        if self.command_data.get('buttons') is not None:
            self.command_data['buttons'].append({
                "label": modal.label.value.strip(),
                "url": modal.url.value.strip(),
                "row": int(modal.row.value.strip())
            })
        else:
            self.command_data['buttons'] = [
                {
                    "label": modal.label.value.strip(),
                    "url": modal.url.value.strip(),
                    "row": int(modal.row.value.strip())
                }
            ]

    @discord.ui.button(label="Remove Button", row=4)
    async def remove_button(self, interaction: discord.Interaction, _):
        modal = CustomModal(
            "Remove a Button",
            [
                (
                    "label",
                    discord.ui.TextInput(
                        label="Label",
                        max_length=80,
                        placeholder="Label of the button",
                        required=True
                    )
                ),
                ],
            {
                "ephemeral": True
            }
        )
        await interaction.response.send_modal(modal)
        await modal.wait()
        # Input validations


        message = interaction.message
        if self.sustained_interaction:
            message = await self.sustained_interaction.original_response()

        for item in self.command_data.get('buttons') or []:
            if item['label'].lower() == modal.label.value.strip().lower():
                self.command_data['buttons'].remove(item)

        for button in self.children:
            if isinstance(button, discord.ui.Button):
                if button.label.lower() == modal.label.value.strip().lower():
                    if button.label not in ["Add Button", "Remove Button", "Cancel", "Finish"]:
                        self.remove_item(button)
                        break


        await message.edit(
            view=self
        )

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=4
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        self.value = False
        pass

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        row=4,
        disabled=False
    )
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        self.value = True
        self.stop()

















class MessageCustomisation(discord.ui.View):
    def __init__(self, user_id, data=None, persist=False, external=False):
        super().__init__(timeout=600.0)
        if data is None:
            data = {}
        self.persist = persist
        self.value: typing.Union[str, None] = None
        self.modal: typing.Union[discord.ui.Modal, None] = None
        self.newView: typing.Union[EmbedCustomisation, None] = None
        self.msg = None
        self.has_embeds = False
        self.sustained_interaction = None
        self.external = external
        if data != {}:
            msg = data.get('message', data)
            content = msg["content"]
            embeds = msg.get("embeds")
            if embeds != []:
                self.has_embeds = True
        self.user_id = user_id

    async def check_ability(self, message):
        if message.content or message.embeds is not None:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False

            await message.edit(view=self)
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True
            await message.edit(view=self)

    @discord.ui.button(
        label="Set Message",
        style=discord.ButtonStyle.secondary,
    )
    async def content(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetContent()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            if self.sustained_interaction:
                await self.check_ability(await self.sustained_interaction.original_response())
                return await (await self.sustained_interaction.original_response()).edit(
                    content=modal.name.value
                )
            await interaction.message.edit(content=modal.name.value)
            await self.check_ability(interaction.message)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Add Embed",
        style=discord.ButtonStyle.secondary,
    )
    async def addembed(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            if len(interaction.message.embeds) > 0:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Limitation",
                        description="You can only have one embed per custom command message.",
                        color=BLANK_COLOR
                    ),
                    ephemeral=True
                )

            newView = EmbedCustomisation(interaction.user.id, self)
            newView.sustained_interaction = self.sustained_interaction
            self.newView = newView

            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message

            await chosen_interaction_message.edit(
                view=newView, embed=discord.Embed(colour=BLANK_COLOR, description="\u200b")
            )
            await interaction.response.defer(thinking=False)
            # await self.check_ability(chosen_interaction_message)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success, disabled=True)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            self.msg = interaction.message
            self.newView = self
            self.value = "finish"
            if not self.external:
                await interaction.response.defer(thinking=False)
            else:
                await int_invis_embed(
                    interaction,
                    "your custom message has been saved. You can now continue with your configuration."
                )
            if not self.persist and not self.sustained_interaction:
                await interaction.message.delete()
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)


class EmbedCustomisation(discord.ui.View):
    def __init__(self, user_id, view=None, external=False):
        super().__init__(timeout=600.0)
        self.value: typing.Union[str, None] = None
        self.modal: typing.Union[discord.ui.Modal, None] = None
        self.msg = None
        self.user_id = user_id
        self.external = external
        self.sustained_interaction = None
        if view is not None:
            self.parent_view = view
        else:
            self.parent_view = None

    async def check_ability(self, message):
        if message.content or message.embeds is not None:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False

            await message.edit(view=self)
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True
            await message.edit(view=self)

    @discord.ui.button(
        label="Set Message",
        style=discord.ButtonStyle.secondary,
    )
    async def content(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetContent()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            await chosen_interaction_message.edit(content=modal.name.value)
            await self.check_ability(chosen_interaction_message)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Remove Embed",
        style=discord.ButtonStyle.secondary,
    )
    async def remove_embed(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            if len(interaction.message.embeds) > 0:
                if self.parent_view is not None:
                    if self.sustained_interaction:
                        chosen_interaction_message = await self.sustained_interaction.original_response()
                    else:
                        chosen_interaction_message = interaction.message
                    await chosen_interaction_message.edit(view=self.parent_view, embed=None)
                    await int_invis_embed(interaction, "embed removed.", ephemeral=True)
                else:
                    newView = MessageCustomisation(interaction.user.id)
                    self.parent_view = newView
                    await interaction.message.edit(view=newView, embed=None)
                    return await int_invis_embed(
                        interaction, "embed removed.", ephemeral=True
                    )
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success, disabled=True)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            for item in self.children:
                item.disabled = True
            self.msg = interaction.message
            self.value = "finish"
            if not self.external:
                await interaction.response.defer(thinking=False)
            else:
                await int_invis_embed(
                    interaction,
                    "your custom message has been created. You can now continue with your configuration."
                )
            if not self.sustained_interaction:
                await interaction.message.edit(view=None)
            if self.parent_view is not None:
                self.parent_view.stop()
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Title",
        row=1,
        style=discord.ButtonStyle.secondary,
    )
    async def set_title(
            self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetTitle()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.title = modal.name.value
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            await chosen_interaction_message.edit(embed=embed)
            await self.check_ability(chosen_interaction_message)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Description",
        row=1,
        style=discord.ButtonStyle.secondary,
    )
    async def set_description(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetDescription()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.description = modal.name.value
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            await chosen_interaction_message.edit(embed=embed)
            await self.check_ability(chosen_interaction_message)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Embed Colour",
        row=1,
        style=discord.ButtonStyle.secondary,
    )
    async def set_color(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetColour()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            try:
                embed.colour = modal.name.value
            except:
                try:
                    embed.colour = int(modal.name.value.replace("#", ""), 16)
                except:
                    return await interaction.response.send_message(
                        embed=discord.Embed(
                            title="Invalid Colour",
                            description="This colour is invalid.",
                            color=BLANK_COLOR
                        ),
                        ephemeral=True
                    )
            await chosen_interaction_message.edit(embed=embed)
            await self.check_ability(chosen_interaction_message)

        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Thumbnail",
        row=2,
        style=discord.ButtonStyle.secondary,
    )
    async def set_thumbnail(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetThumbnail()
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.set_thumbnail(url=modal.thumbnail.value)

            try:
                await chosen_interaction_message.edit(embed=embed)
            except discord.HTTPException:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Unavailable URL",
                        description="This URL is invalid or unavailable.",
                        color=BLANK_COLOR
                    ),
                    ephemeral=True
                )
            await self.check_ability(chosen_interaction_message)

        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Image",
        row=2,
        style=discord.ButtonStyle.secondary,
    )
    async def set_image(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetImage()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            embed = interaction.message.embeds[0]
            embed.set_image(url=modal.image.value)
            try:
                await chosen_interaction_message.edit(embed=embed)
            except discord.HTTPException:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Unavailable URL",
                        description="This URL is invalid or unavailable.",
                        color=BLANK_COLOR
                    ),
                    ephemeral=True
                )
            await self.check_ability(chosen_interaction_message)

        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Add Field",
        row=3,
        style=discord.ButtonStyle.secondary,
    )
    async def add_field(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = AddField()
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message

            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            if len(interaction.message.embeds) == 0:
                return
            embed = interaction.message.embeds[0]
            try:
                inline = modal.inline.value
                if inline.lower() in ["yes", "y", "true"]:
                    inline = True
                elif inline.lower() in ["no", "n", "false"]:
                    inline = False
                else:
                    inline = False
                embed.add_field(
                    name=modal.name.value, value=modal.value.value, inline=inline
                )
            except:
                return
            await chosen_interaction_message.edit(embed=embed)
            await self.check_ability(chosen_interaction_message)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Footer",
        row=3,
        style=discord.ButtonStyle.secondary,
    )
    async def set_footer(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            modal = SetFooter()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.set_footer(text=modal.name.value, icon_url=modal.icon.value)
            try:
                await chosen_interaction_message.edit(embed=embed)
            except discord.HTTPException:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Unavailable URL",
                        description="This URL is invalid or unavailable.",
                        color=BLANK_COLOR
                    ),
                    ephemeral=True
                )
            await self.check_ability(chosen_interaction_message)

        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(
        label="Set Author",
        row=3,
        style=discord.ButtonStyle.secondary,
    )
    async def set_author(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id == self.user_id:
            modal = SetAuthor()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            if self.sustained_interaction:
                chosen_interaction_message = await self.sustained_interaction.original_response()
            else:
                chosen_interaction_message = interaction.message
            embed = interaction.message.embeds[0]
            embed.set_author(
                name=modal.name.value,
                url=modal.url.value,
                icon_url=modal.icon.value,
            )
            try:
                await chosen_interaction_message.edit(embed=embed)
            except discord.HTTPException:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Unavailable URL",
                        description="This URL is invalid or unavailable.",
                        color=BLANK_COLOR
                    ),
                    ephemeral=True
                )
            await self.check_ability(chosen_interaction_message)

        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)


class RemoveReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
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
            return await generalised_interaction_check_failure(interaction.followup)


class RemoveCustomCommand(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    @discord.ui.button(
        label="Delete a custom command", style=discord.ButtonStyle.danger
    )
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
            return await generalised_interaction_check_failure(interaction.followup)


class RemoveWarning(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.bot = bot
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)
        await interaction.response.defer()
        for item in self.children:
            self.remove_item(item)
        self.value = True

        # success = discord.Embed(
        #     title="<:CheckIcon:1035018951043842088> Removed Punishment",
        #     description="<:ArrowRightW:1035023450592514048>I've successfully removed the punishment from the user.",
        #     color=0x71C15F,
        # )

        # await interaction.edit_original_response(embed=success, view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)
        await interaction.response.defer()
        for item in self.children:
            self.remove_item(item)
        self.value = False

        # success = discord.Embed(
        #     title="<:ErrorIcon:1035000018165321808> Cancelled",
        #     description="<:ArrowRightW:1035023450592514048>The punishment has not been removed from the user.",
        #     color=0xFF3C3C,
        # )
        #
        # await interaction.edit_original_response(embed=success, view=self)
        self.stop()


class RequestReason(discord.ui.Modal, title="Edit Reason"):
    name = discord.ui.TextInput(label="Reason")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class RequestData(discord.ui.Modal, title="Edit Reason"):
    data = discord.ui.TextInput(label="Reason")

    def __init__(self, title="PLACEHOLDER", label="PLACEHOLDER"):
        self.data.label = label
        super().__init__(title=title)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class CustomModal(discord.ui.Modal, title="Edit Reason"):
    def __init__(self, title, options, epher_args: dict = None):
        super().__init__(title=title)
        if epher_args is None:
            epher_args = {}
        self.saved_items = {}
        self.epher_args = epher_args
        self.interaction = None

        for name, option in options:
            self.add_item(option)
            self.saved_items[name] = option

    async def on_submit(self, interaction: discord.Interaction):
        for key, item in self.saved_items.items():
            setattr(self, key, item)
        self.interaction = interaction
        await interaction.response.defer(**self.epher_args)
        self.stop()


class SetContent(discord.ui.Modal, title="Set Message Content"):
    name = discord.ui.TextInput(
        label="Content",
        placeholder="Content of the message",
        max_length=2000,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        self.stop()


class CreatePunishmentType(discord.ui.Modal, title="Create Punishment Type"):
    name = discord.ui.TextInput(
        label="Name",
        placeholder="e.g. Verbal Warning",
        max_length=20,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        self.stop()


class DeletePunishmentType(discord.ui.Modal, title="Delete Punishment Type"):
    name = discord.ui.TextInput(
        label="Name",
        placeholder="e.g. Verbal Warning",
        max_length=20,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class RobloxUsername(discord.ui.Modal, title="Verification"):
    name = discord.ui.TextInput(
        label="Roblox Username",
        placeholder="e.g. RoyalCrests",
        max_length=32,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        self.stop()


class SetTitle(discord.ui.Modal, title="Set Embed Title"):
    name = discord.ui.TextInput(
        label="Title", placeholder="Title of the embed", style=discord.TextStyle.short
    )
    url = discord.ui.TextInput(
        label="Title URL",
        placeholder="URL of the title",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class CustomCommandSettings(discord.ui.Modal, title="Custom Command Settings"):
    name = discord.ui.TextInput(
        label="Custom Command Name",
        placeholder="e.g. ssu",
        style=discord.TextStyle.short,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class SetDescription(discord.ui.Modal, title="Set Embed Description"):
    name = discord.ui.TextInput(
        label="Description",
        placeholder="Description of the embed",
        style=discord.TextStyle.long,
        max_length=2000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class SetColour(discord.ui.Modal, title="Set Embed Colour"):
    name = discord.ui.TextInput(
        label="Colour", placeholder="#DB514F", style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class SetImage(discord.ui.Modal, title="Set Image"):
    image = discord.ui.TextInput(
        label="Image URL", placeholder="Image URL", style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class AddField(discord.ui.Modal, title="Add Field"):
    name = discord.ui.TextInput(
        label="Field Name", placeholder="Field Name", style=discord.TextStyle.short
    )
    value = discord.ui.TextInput(
        label="Field Value", placeholder="Field Value", style=discord.TextStyle.short
    )
    inline = discord.ui.TextInput(
        label="Inline?",
        placeholder="Yes/No",
        default="Yes",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class SetFooter(discord.ui.Modal, title="Set Footer"):
    name = discord.ui.TextInput(
        label="Footer Text", placeholder="Footer Text", style=discord.TextStyle.short
    )
    icon = discord.ui.TextInput(
        label="Footer Icon URL",
        placeholder="Footer Icon URL",
        default="",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class SetAuthor(discord.ui.Modal, title="Set Author"):
    name = discord.ui.TextInput(
        label="Author Name", placeholder="Author Name", style=discord.TextStyle.short
    )
    url = discord.ui.TextInput(
        label="Author URL",
        placeholder="Author URL",
        default="",
        style=discord.TextStyle.short,
        required=False,
    )
    icon = discord.ui.TextInput(
        label="Author Icon URL",
        placeholder="Author Icon URL",
        default="",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class SetThumbnail(discord.ui.Modal, title="Set Thumbnail"):
    thumbnail = discord.ui.TextInput(
        label="Thumbnail URL",
        placeholder="Thumbnail URL",
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class TimeRequest(discord.ui.Modal, title="Temporary Ban"):
    time = discord.ui.TextInput(label="Time (s/m/h/d)")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        self.stop()


class ChangeWarningType(discord.ui.Select):
    def __init__(self, user_id, options: list):
        self.user_id: int = user_id

        selected_options = []
        using_options = False
        for option in options:
            if isinstance(option, str | int):
                option = discord.SelectOption(
                    label=str(option),
                    value=str(option),
                )
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
                ),
                discord.SelectOption(
                    label="Kick",
                    value="Kick",
                    description="Removing a user from the game, usually given after warnings",
                ),
                discord.SelectOption(
                    label="Ban",
                    value="Ban",
                    description="A permanent form of removing a user from the game, given after kicks",
                ),
                discord.SelectOption(
                    label="Temporary Ban",
                    value="Temporary Ban",
                    description="Given after kicks, not enough to warrant a permanent removal",
                ),
                discord.SelectOption(
                    label="BOLO",
                    value="BOLO",
                    description="Cannot be found in the game, be on the lookout",
                ),
            ]
        super().__init__(
            placeholder="Select a warning type",
            min_values=1,
            max_values=1,
            options=selected_options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id:
            if self.values[0] == "Temporary Ban":
                modal = TimeRequest()
                await interaction.response.send_modal(modal)
                seconds = 0
                if modal.time.value.endswith("s", "m", "h", "d"):
                    if modal.time.value.endswith("s"):
                        seconds = int(modal.time.value.removesuffix("s"))
                    elif modal.time.value.endswith("m"):
                        seconds = int(modal.time.value.removesuffix("m")) * 60
                    elif modal.time.value.endswith("h"):
                        seconds = int(modal.time.value.removesuffix("h")) * 60 * 60
                    else:
                        seconds = int(modal.time.value.removesuffix("d")) * 60 * 60 * 24
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
            return await generalised_interaction_check_failure(interaction.followup)


class EditWarningSelect(discord.ui.Select):
    def __init__(self, user_id: int, inherited_options: list):
        self.user_id: int = user_id
        self.inherited_options = inherited_options

        options = [
            discord.SelectOption(
                label="Edit reason",
                value="edit",
                description="Edit the reason of the punishment",
            ),
            discord.SelectOption(
                label="Change punishment type",
                value="change",
                description="Change the punishment type to a higher or lower severity",
            ),
            discord.SelectOption(
                label="Delete punishment",
                value="delete",
                description="Delete the punishment from the database. This is irreversible.",
            ),
        ]

        super().__init__(
            placeholder="Select an option", min_values=1, max_values=1, options=options
        )

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
                await interaction.message.edit(
                    content="<:ERMPending:1111097561588183121> **{},** please select a new punishment type.".format(
                        interaction.user.name
                    ),
                    embed=None,
                    view=view,
                )
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
                await int_failure_embed(interaction, "you have not picked an option.")
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)


class EditWarning(discord.ui.View):
    def __init__(self, bot, user_id, options):
        super().__init__(timeout=600.0)
        self.value: typing.Union[None, str] = None
        self.bot: typing.Union[
            discord.ext.commands.Bot, discord.ext.commands.AutoShardedBot
        ] = bot
        self.user_id: int = user_id
        self.modal: typing.Union[None, discord.ui.Modal] = None
        self.further_value: typing.Union[None, str] = None
        self.options = options
        self.add_item(EditWarningSelect(user_id, options))


class RemoveBOLO(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = True

        await interaction.edit_original_response(
            content=f"<:ERMCheck:1111089850720976906> **{interaction.user.name}**, I've removed the BOLO from that user.",
            view=self,
        )
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False

        await interaction.edit_original_response(
            content=f"<:ERMCheck:1111089850720976906> **{interaction.user.name}**, sounds good! I won't remove that punishment.",
            view=self,
        )
        self.stop()


class EnterRobloxUsername(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, RobloxUsername] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)
        self.modal = RobloxUsername()
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stop()


class RequestDataView(discord.ui.View):
    def __init__(self, user_id, title: str, label: str):
        super().__init__(timeout=600.0)
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
            return await generalised_interaction_check_failure(interaction.followup)
        self.modal = RequestData(self.title, self.label)
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stop()


class CustomModalView(discord.ui.View):
    def __init__(
            self,
            user_id,
            title: str,
            label: str,
            options: typing.List[typing.Tuple[str, discord.ui.TextInput]],
    ):
        super().__init__(timeout=600.0)
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
            return await generalised_interaction_check_failure(interaction.followup)

        self.modal = CustomModal(self.label, self.options)
        # print(self.options)
        # print(self.modal.children)
        # print(self.modal)
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stop()


class GoogleSpreadsheetModification(discord.ui.View):
    def __init__(self, config: dict, scopes: list, label: str, url: str):
        super().__init__(timeout=600.0)
        self.add_item(discord.ui.Button(label=label, url=url))
        self.config = config
        self.scopes = scopes
        self.url = url

    @discord.ui.button(label="Request Ownership", style=discord.ButtonStyle.secondary)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomModal(
            "Request Ownership",
            [
                (
                    "email",
                    discord.ui.TextInput(
                        placeholder="Email",
                        min_length=1,
                        max_length=100,
                        label="Email",
                        custom_id="email",
                    ),
                )
            ],
        )

        await interaction.response.send_modal(modal)

        timeout = await modal.wait()
        if timeout:
            return

        email = modal.email.value

        authorization_client = gspread_asyncio.AsyncioGspreadClientManager(
            lambda: ServiceAccountCredentials.from_json_keyfile_dict(self.config, self.scopes)
        )
        client = await authorization_client.authorize()

        sheet = await client.open_by_url(self.url)
        await client.insert_permission(
            sheet.id, value=email, perm_type="user", role="writer"
        )

        permission_id = (await sheet.list_permissions())[0]["id"]

        await sheet.transfer_ownership(permission_id)

        self.remove_item(button)

        await interaction.edit_original_response(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Ownership Transferred",
                description="An ownership transfer request has been sent to your email.",
                color=GREEN_COLOR
            ),
            view=self,
        )


class LinkView(discord.ui.View):
    def __init__(self, label: str, url: str):
        super().__init__(timeout=600.0)
        self.add_item(discord.ui.Button(label=label, url=url))


class RequestGoogleSpreadsheet(discord.ui.View):
    def __init__(
            self,
            user_id,
            config: dict,
            scopes: list,
            data: list,
            template: str,
            type="lb",
            additional_data=None,
            label="Google Spreadsheet",
    ):
        # print(type)
        if type:
            self.type = type
        else:
            self.type = "lb"
        # print(additional_data)
        if additional_data:
            self.additional_data = additional_data
        else:
            self.additional_data = []

        super().__init__(timeout=600.0)
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
    async def googlespreadsheet(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if interaction.user.id != self.user_id:
            return await interaction.followup.send(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))

        await interaction.followup.send(
            embed=discord.Embed(
                title="Generating...",
                description="We are currently generating your Google Spreadsheet.",
                color=BLANK_COLOR
            )
        )
        authorization_client = gspread_asyncio.AsyncioGspreadClientManager(
            lambda: ServiceAccountCredentials.from_json_keyfile_dict(self.config, self.scopes)
        )
        client = await authorization_client.authorize()

        sheet: gspread_asyncio.AsyncioGspreadSpreadsheet = await client.copy(
            self.template, interaction.guild.name, copy_permissions=True
        )
        new_sheet = await sheet.get_worksheet(0)
        try:
            await new_sheet.update_cell(4, 2, f'=IMAGE("{interaction.guild.icon.url}")')
        except AttributeError:
            pass

        if self.type == "lb":
            cell_list = await new_sheet.range("D13:H999")
        elif self.type == "ar":
            cell_list = await new_sheet.range("D13:I999")

        for c, n_v in zip(cell_list, self.data):
            c.value = str(n_v)

        await new_sheet.update_cells(cell_list, "USER_ENTERED")
        if self.type == "ar":
            LoAs = await sheet.get_worksheet(1)
            await LoAs.update_cell(4, 2, f'=IMAGE("{interaction.guild.icon.url}")')
            cell_list = await LoAs.range("D13:H999")

            for cell, new_value in zip(cell_list, self.additional_data):
                if isinstance(new_value, int):
                    cell.value = f"=({new_value}/ 86400 + DATE(1970, 1, 1))"
                else:
                    cell.value = str(new_value)
            await LoAs.update_cells(cell_list, "USER_ENTERED")

        await client.insert_permission(
            sheet.id, value=None, perm_type="anyone", role="writer"
        )

        view = GoogleSpreadsheetModification(
            self.config, self.scopes, "Open Google Spreadsheet", sheet.url
        )

        await interaction.edit_original_response(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Successfully generated",
                description="Your Google Spreadsheet has been successfully generated.",
                color=GREEN_COLOR
            ),
            view=view
        )

        self.stop()


#
# class LiveMenu(discord.ui.View):
#     def __init__(self, bot, ctx):
#         super().__init__(timeout=600.0)
#         self.bot = bot
#         self.context = ctx
#
#     async def execute_command(
#         self,
#         interaction: discord.Interaction,
#         arguments: str,
#         command: discord.ext.commands.HybridCommand = None,
#         extra_args: dict = None,
#         concatenate_to_last_argument: bool = False,
#         flag_class: discord.ext.commands.FlagConverter = DutyManageOptions,
#     ):
#         if command is None:
#             # assume default
#             command = self.bot.get_command("duty manage")
#         mockinteraction = copy(interaction)
#         mockinteraction._cs_command = command
#         mockinteraction.user = self.context.author
#
#         fakecontext = await discord.ext.commands.Context.from_interaction(
#             mockinteraction
#         )
#         mockcontext = copy(fakecontext)
#         can_run = await command.can_run(mockcontext)
#
#         if not can_run:
#             await interaction.response.send_message(
#                 content="<:ERMClose:1111101633389146223> You do not have permission to run this command!",
#                 ephemeral=True,
#             )
#             return
#
#         mockcontext.command = command
#         mockcontext.author = self.context.author
#
#         if not concatenate_to_last_argument:
#             await mockcontext.invoke(
#                 command,
#                 flags=await flag_class.convert(mockcontext, arguments),
#                 **extra_args,
#             )
#         else:
#             index = 0
#             for key, value in extra_args.copy().items():
#                 if index == len(extra_args) - 1:
#                     value += (" " + arguments)
#                     extra_args[key] = value
#                 index += 1
#
#
#             await mockcontext.invoke(
#                 command,
#                 **extra_args
#             )
#
#     @discord.ui.button(
#         label="On Duty", style=discord.ButtonStyle.green, custom_id="on_duty-execution"
#     )
#     async def on_duty(
#         self, interaction: discord.Interaction, button: discord.ui.Button
#     ):
#         await self.execute_command(
#             interaction, "/onduty=True /without_command_execution=True"
#         )
#
#     @discord.ui.button(
#         label="Toggle Break",
#         style=discord.ButtonStyle.secondary,
#         custom_id="toggle_break-execution",
#     )
#     async def toggle_break(
#         self, interaction: discord.Interaction, button: discord.ui.Button
#     ):
#         await self.execute_command(
#             interaction, "/togglebreak=True /without_command_execution=True"
#         )
#
#     @discord.ui.button(
#         label="Off Duty",
#         style=discord.ButtonStyle.danger,
#         custom_id="off_duty-execution",
#     )
#     async def off_duty(
#         self, interaction: discord.Interaction, button: discord.ui.Button
#     ):
#         await self.execute_command(
#             interaction, "/offduty=True /without_command_execution=True"
#         )
#
#     @discord.ui.button(
#         label="Log Punishment",
#         style=discord.ButtonStyle.secondary,
#         custom_id="punish-execution",
#         row=1,
#     )
#     async def _punish(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.user = None
#         self.punish_type = None
#         self.reason = None
#
#         class PunishModal(discord.ui.Modal):
#             def __init__(modal):
#                 super().__init__(title="Log Punishment", timeout=600.0)
#                 modal.add_item(
#                     discord.ui.TextInput(label="ROBLOX User", placeholder="ROBLOX User")
#                 )
#                 modal.add_item(
#                     discord.ui.TextInput(
#                         label="Punishment Type", placeholder="Punishment Type"
#                     )
#                 )
#                 modal.add_item(
#                     discord.ui.TextInput(label="Reason", placeholder="Reason")
#                 )
#
#             async def on_submit(modal, modal_interaction: discord.Interaction):
#                 for item in modal.children:
#                     if item.label == "ROBLOX User":
#                         self.user = item.value
#                     elif item.label == "Punishment Type":
#                         self.punish_type = item.value
#                     elif item.label == "Reason":
#                         self.reason = item.value
#                 await self.execute_command(
#                     modal_interaction,
#                     "\n/ephemeral=True /without_command_execution=True",
#                     command=self.bot.get_command("punish"),
#                     extra_args={
#                         "user": self.user,
#                         "type": self.punish_type,
#                         "reason": self.reason,
#                     },
#                     concatenate_to_last_argument=True,
#                     flag_class=PunishOptions,
#                 )
#
#         await interaction.response.send_modal(PunishModal())
#         self.user = None
#         self.punish_type = None
#         self.reason = None
#
#     @discord.ui.button(
#         label="Search",
#         style=discord.ButtonStyle.secondary,
#         custom_id="search-execution",
#         row=1,
#     )
#     async def _search(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.user = None
#
#         class SearchModal(discord.ui.Modal):
#             def __init__(modal):
#                 super().__init__(title="Search User", timeout=600.0)
#                 modal.add_item(
#                     discord.ui.TextInput(label="ROBLOX User", placeholder="ROBLOX User")
#                 )
#
#             async def on_submit(modal, modal_interaction: discord.Interaction):
#                 for item in modal.children:
#                     if item.label == "ROBLOX User":
#                         self.user = item.value
#                 await self.execute_command(
#                     modal_interaction,
#                     "/ephemeral=True /without_command_execution=True",
#                     command=self.bot.get_command("search"),
#                     extra_args={
#                         "query": self.user
#                     },
#                     flag_class=SearchOptions,
#                 )
#
#         await interaction.response.send_modal(SearchModal())
#         self.user = None
#
#     @discord.ui.button(
#         label="Active BOLOs",
#         style=discord.ButtonStyle.secondary,
#         custom_id="bolos-execution",
#         row=1,
#     )
#     async def _bolos(self, interaction: discord.Interaction, button: discord.ui.Button):
#         self.user = None
#
#         class SearchModal(discord.ui.Modal):
#             def __init__(modal):
#                 super().__init__(title="BOLO Search", timeout=600.0)
#                 modal.add_item(
#                     discord.ui.TextInput(label="ROBLOX User", placeholder="Optional, leave empty for all", required=False)
#                 )
#
#             async def on_submit(modal, modal_interaction: discord.Interaction):
#                 for item in modal.children:
#                     if item.label == "ROBLOX User":
#                         self.user = item.value
#                 args = {}
#                 if self.user.strip() != "":
#                     args['user'] = self.user
#
#                 await self.execute_command(
#                     modal_interaction,
#                     "/ephemeral=True /without_command_execution=True",
#                     command=self.bot.get_command("bolo active"),
#                     extra_args=args,
#                     flag_class=SearchOptions,
#                 )
#
#         await interaction.response.send_modal(SearchModal())
#         self.user = None

class Verification(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        self.modal: typing.Union[None, RobloxUsername] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Done!", style=discord.ButtonStyle.green, emoji="✅")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

        self.value = "done"
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

        self.value = "cancel"
        self.stop()


class CustomSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list, limit: typing.Optional[int] = 1):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

        self.add_item(CustomDropdown(self.user_id, options, limit))


class MultiPaginatorMenu(discord.ui.View):
    def __init__(self, user_id, options: list, pages: dict):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

        self.add_item(MultiPaginatorDropdown(self.user_id, options, pages))


class WarningDropdownMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id
        new_options = []

        for option in options:
            if isinstance(option, discord.SelectOption):
                new_options.append(option)
            else:
                if isinstance(option, dict):
                    new_options.append(
                        discord.SelectOption(label=option["name"], value=option["name"])
                    )
                else:
                    new_options.append(discord.SelectOption(label=option, value=option))

        self.add_item(ChangeWarningType(self.user_id, new_options))

class ActivityNoticeAdministration(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.value = None
        self.stored_interaction = None

    async def visual_close(self, message: discord.Message):
        for item in self.children:
            self.remove_item(item)

        await message.edit(view=self)
        await message.delete()

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Create",
        style=discord.ButtonStyle.green
    )
    async def create_notice(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.modal = CustomModal(
            'Create Activity Notice',
            [
                (
                    'reason',
                    discord.ui.TextInput(
                        label="Reason"
                    )
                ),
                (
                    'duration',
                    discord.ui.TextInput(
                        label="Duration"
                    )
                )
            ], {
                "ephemeral": True
            }
        )

        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        self.stored_interaction = self.modal.interaction
        self.value = "create"

        await self.visual_close(interaction.message)
        self.stop()

    @discord.ui.button(
        label="List",
        style=discord.ButtonStyle.secondary
    )
    async def list_notices(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False, ephemeral=True)
        self.stored_interaction = interaction
        self.value = "list"

        await self.visual_close(interaction.message)
        self.stop()

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger
    )
    async def delete_notice(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        self.stored_interaction = interaction
        self.value = "delete"

        await self.visual_close(interaction.message)
        self.stop()



class MultiSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

        self.add_item(MultiDropdown(self.user_id, options))


class NextView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600.0)
        self.user_id = user_id
        self.value = None

    @discord.ui.button(emoji="<:arrow:1169695690784518154>")
    async def _next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        self.value = True
        await interaction.response.defer()
        self.stop()


class ShiftTypeManagement(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600.0)
        self.user_id = user_id
        self.value = None
        self.selected_for_deletion = None
        self.name_for_creation = None
        self.modal = None

    @discord.ui.button(label="Create Shift Type")
    async def _create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        # await interaction.response.defer(thinking=False)
        self.modal = CustomModal(
            "Create Shift Type",
            [
                (
                    "shift_type_name",
                    discord.ui.TextInput(
                        label="Name",
                        placeholder="Name of Shift Type"
                    )
                )
            ]
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        if self.modal.shift_type_name.value:
            self.name_for_creation = self.modal.shift_type_name.value
        else:
            return
        self.value = 'create'
        self.stop()

    @discord.ui.button(label="Delete Shift Type")
    async def _delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        self.modal = CustomModal(
            "Shift Type Deletion",
            [
                (
                    'shift_type',
                    discord.ui.TextInput(
                        label="Shift Type ID",
                        placeholder="ID of the Shift Type"
                    )
                )
            ]
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        if self.modal.shift_type.value:
            self.selected_for_deletion = self.modal.shift_type.value
        else:
            return
        self.value = "delete"
        self.stop()


class RoleQuotaManagement(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600.0)
        self.user_id = user_id
        self.value = None
        self.selected_for_deletion = None
        self.name_for_creation = None
        self.modal = None

    @discord.ui.button(label="Create Role Quota")
    async def _create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        await interaction.response.defer(thinking=False)
        self.value = 'create'
        self.stop()

    @discord.ui.button(label="Delete Role Quota")
    async def _delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        self.modal = CustomModal(
            "Role Quota Deletion",
            [
                (
                    'role_id',
                    discord.ui.TextInput(
                        label="Role ID",
                        placeholder="ID of the Role"
                    )
                )
            ]
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        if self.modal.role_id.value:
            self.selected_for_deletion = self.modal.role_id.value
        else:
            return
        self.value = "delete"
        self.stop()


class BackNextView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600.0)
        self.user_id = user_id
        self.value = None

    @discord.ui.button(emoji="<:l_arrow:1169754353326903407>")
    async def _back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        self.value = -1
        self.stop()

    @discord.ui.button(emoji="<:arrow:1169695690784518154>")
    async def _next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ))
        self.value = 1
        self.stop()


class AssociationConfigurationView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int, associated_defaults: list):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

        for (label, defaults) in associated_defaults:
            print(label)
            print(defaults)
            use_configuration = None
            if isinstance(defaults[0], list):
                if defaults[0][0] == "CUSTOM_CONF":
                    configurator = defaults[0]
                    match_configurator = configurator[1]
                    if match_configurator.get('_FIND_BY_LABEL') is True:
                        items = defaults[1:]
                        use_configuration = {
                            "configuration": match_configurator,
                            "matchables": items
                        }
            item = None
            for iterating_item in self.children:
                if getattr(iterating_item, 'label', None) is None:
                    if iterating_item.placeholder == label:
                        item = iterating_item
                        break
                else:
                    if iterating_item.label == label:
                        item = iterating_item
                        break
            if use_configuration is None:
                print(3051)
                for index, defa in enumerate(defaults):
                    if defa is None:
                        defaults[index] = 0
                item.default_values = [i for i in defaults if i != 0]
            else:
                found_values = []
                for val in use_configuration['matchables']:
                    if isinstance(item, discord.ui.Select):
                        if use_configuration['configuration'].get('_FIND_BY_LABEL', False) is True:
                            found_value = [i for i in item.options if i.label == val][0]
                            if not found_value:
                                continue
                            found_values.append(found_value)

                if isinstance(item, discord.ui.Select):
                    for val in found_values:
                        find_index = 0
                        for index, option in enumerate(item.options):
                            if option == val:
                                find_index = index
                                break
                        new_opt = item.options[find_index]
                        new_opt.default = True
                        item.options[find_index] = new_opt

    async def on_timeout(self) -> None:
        for i in self.children:
            i.disabled = True

        await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        print('3064 : Interaction Check')
        if interaction.user.id == self.user_id:
            print('PASSED - {} - {}'.format(interaction.user.id, self.user_id))
            return True
        else:
            print('FAILED - {} - {}'.format(interaction.user.id, self.user_id))
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False


class ReminderCreationToolkit(discord.ui.View):
    def __init__(self, user_id: int, dataset: dict):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.dataset = dataset
        self.cancelled = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def refresh_ui(self, message: discord.Message):
        embed = discord.Embed(
            title="Reminder Creation",
            description=(
                f"<:replytop:1138257149705863209> **Name:** {self.dataset['name']}\n"
                f"<:replymiddle:1138257195121791046> **ID:** {self.dataset['id']}\n"
                f"<:replymiddle:1138257195121791046> **Channel:** {'<#{}>'.format(self.dataset.get('channel', None)) if self.dataset.get('channel', None) is not None else 'Not set'}\n"
                f"<:replymiddle:1138257195121791046> **Completion Ability:** {self.dataset.get('completion_ability') or 'Not set'}\n"
                f"<:replymiddle:1138257195121791046> **Mentioned Roles:** {', '.join(['<@&{}>'.format(r) for r in self.dataset.get('role', [])]) or 'Not set'}\n"
                f"<:replybottom:1138257250448855090> **Interval:** {td_format(datetime.timedelta(seconds=self.dataset.get('interval', 0))) or 'Not set'}"
                f"\n\n**Content:**\n{self.dataset['message']}"
            ),
            color=BLANK_COLOR
        )

        if all(
                [
                    self.dataset.get('channel') is not None,
                    self.dataset.get('interval') is not None
                ]
        ):
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True

        await message.edit(embed=embed, view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Mentioned Roles", row=0, max_values=25)
    async def mentioned_roles_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        await interaction.response.defer()

        self.dataset['role'] = [i.id for i in select.values]
        await self.refresh_ui(interaction.message)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Reminder Channel", row=1, max_values=1,
                       channel_types=[discord.ChannelType.text])
    async def channel_select(
            self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        await interaction.response.defer()

        self.dataset['channel'] = [i.id for i in select.values][0]
        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="Set Interval",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def set_interval(self, interaction: discord.Interaction, button: discord.Button):
        self.modal = CustomModal(
            "Set Interval",
            [(
                "interval",
                discord.ui.TextInput(
                    label="Interval",
                    placeholder="The interval between each reminder. (hours/minutes/seconds/days)",
                    default=str(self.dataset.get('interval', 0)),
                    required=False
                )
            )], {
                'ephemeral': True
            }
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        try:
            new_time = time_converter(self.modal.interval.value)
        except ValueError:
            return await self.modal.interaction.followup.send(
                embed=discord.Embed(
                    title='Invalid Time',
                    description="You did not enter a valid time.",
                    color=BLANK_COLOR
                )
            )

        self.dataset['interval'] = new_time
        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="Edit Content",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def edit_content(self, interaction: discord.Interaction, button: discord.Button):
        self.modal = CustomModal(
            "Edit Content",
            [(
                "content",
                discord.ui.TextInput(
                    label="Content",
                    placeholder="The content of the reminder",
                    default=str(self.dataset.get('message', '')),
                    style=discord.TextStyle.long,
                    max_length=2000,
                    required=False
                ))]
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        content = self.modal.content.value

        self.dataset['message'] = content
        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="Completion Ability: Disabled",
        style=discord.ButtonStyle.danger,
        row=2
    )
    async def edit_completion_ability(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer(thinking=False)
        if button.label == "Completion Ability: Disabled":
            self.dataset['completion_ability'] = True
            button.label = "Completion Ability: Enabled"
            button.style = discord.ButtonStyle.green
        else:
            self.dataset['completion_ability'] = False
            button.label = "Completion Ability: Disabled"
            button.style = discord.ButtonStyle.danger

        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer(ephemeral=True)
        self.cancelled = True
        await interaction.followup.send(embed=discord.Embed(
            title="Successfully cancelled",
            description="This reminder has not been created.",
            color=BLANK_COLOR
        ))
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        disabled=True,
        row=3
    )
    async def finish(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer()
        self.cancelled = False
        self.stop()


class BasicConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        return await super().interaction_check(interaction)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Staff Roles", row=0, max_values=25)
    async def staff_role_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['staff_management']['role'] = [i.id for i in select.values]
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Management Roles", row=1, max_values=25)
    async def management_role_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['staff_management']['management_role'] = [i.id for i in select.values]
        await bot.settings.update_by_id(sett)

    @discord.ui.select(placeholder="Prefix", row=2, options=[
        discord.SelectOption(
            label="!",
            description="Use '!' as your custom prefix."
        ),
        discord.SelectOption(
            label=">",
            description="Use '>' as your custom prefix."
        ),
        discord.SelectOption(
            label="?",
            description="Use '?' as your custom prefix."
        ),
        discord.SelectOption(
            label=":",
            description="Use ':' as your custom prefix."
        )
    ], max_values=1)
    async def prefix_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['customisation']['prefix'] = select.values[0]
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False


# class PunishmentTypesConfiguration(discord.ui.View):
#     def __init__(self, bot, user_id: int, given_data: list):
#             # Init vars
#             self.bot = bot
#             self.user_id = user_id
#             self.given_data = given_data
#
#             # TODO: match given data -> embed structure
#
#     async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
#         if interaction.user.id == self.user_id:
#             return True
#         else:
#             await interaction.response.send_message(embed=discord.Embed(
#                 title="Not Permitted",
#                 description="You are not permitted to interact with these buttons.",
#                 color=blank_color
#             ), ephemeral=True)
#             return False
#
#     @discord.ui.select(options=[
#         discord.SelectOption(
#             label="Add Type",
#             description="Add a Punishment Type",
#             value="add"
#         ),
#         discord.SelectOption(
#             label="Modify Type",
#             description="Change some settings about a punishment type",
#             value="modify"
#         ),
#         discord.SelectOption(
#             label="Delete Type",
#             description="Delete a punishment type",
#             value="delete"
#         )
#     ])

class LOAConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="LOA Role", row=1, max_values=1)
    async def loa_role_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['staff_management']['loa_role'] = select.values[0].id
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="LOA Channel", row=2, max_values=1,
                       channel_types=[discord.ChannelType.text])
    async def loa_channel_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['staff_management']['channel'] = select.values[0].id
        await bot.settings.update_by_id(sett)

    @discord.ui.select(placeholder="LOA Requests", row=0, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="LOA Requests are enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="LOA Requests are disabled."
        )
    ], max_values=1)
    async def enabled_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['staff_management']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False


class ExtendedShiftOptions(discord.ui.View):
    def __init__(self, bot, associated_defaults: list):
        super().__init__(timeout=None)
        self.modal = None
        self.bot = bot
        self.modal_default = 0
        self.nickname_default = None
        self.quota_default = None

        for (label, defaults) in associated_defaults:
            if label == "max_staff":
                self.modal_default = defaults
                continue
            if label == "nickname_prefix":
                self.nickname_default = defaults
                continue
            if label == "quota":
                self.quota_default = defaults
                continue
            use_configuration = None
            if isinstance(defaults[0], list):
                if defaults[0][0] == "CUSTOM_CONF":
                    configurator = defaults[0]
                    match_configurator = configurator[1]
                    if match_configurator.get('_FIND_BY_LABEL') is True:
                        items = defaults[1:]
                        use_configuration = {
                            "configuration": match_configurator,
                            "matchables": items
                        }

            item = None
            for iterating_item in self.children:
                if getattr(iterating_item, 'label', None) is None:
                    if iterating_item.placeholder == label:
                        item = iterating_item
                        break
                else:
                    if iterating_item.label == label:
                        item = iterating_item
                        break
            if use_configuration is None:
                for index, defa in enumerate(defaults):
                    if defa is None:
                        defaults[index] = 0
                item.default_values = [i for i in defaults if i != 0]
            else:
                found_values = []
                for val in use_configuration['matchables']:
                    if isinstance(item, discord.ui.Select):
                        if use_configuration['configuration'].get('_FIND_BY_LABEL', False) is True:
                            found_value = [i for i in item.options if i.label == val][0]
                            if not found_value:
                                continue
                            found_values.append(found_value)

                if isinstance(item, discord.ui.Select):
                    for val in found_values:
                        find_index = 0
                        for index, option in enumerate(item.options):
                            if option == val:
                                find_index = index
                                break
                        new_opt = item.options[find_index]
                        new_opt.default = True
                        item.options[find_index] = new_opt

    @discord.ui.button(
        label='Set Maximum Staff Online',
        row=4
    )
    async def set_maximum_staff_online(self, interaction: discord.Interaction, button: discord.Button):
        self.modal = CustomModal("Maximum Staff", [
            (
                'max_staff',
                discord.ui.TextInput(
                    label="Maximum Staff Online",
                    placeholder="This is the amount of staff members that can be online at one time.",
                    default=str(self.modal_default),
                    required=False
                )
            )
        ])
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        max_staff = self.modal.max_staff.value
        max_staff = int(max_staff.strip())

        bot = self.bot
        sett = await bot.settings.find_by_id(interaction.guild.id)
        sett['shift_management']['maximum_staff'] = max_staff
        await bot.settings.update_by_id(sett)
        self.modal_default = max_staff

    @discord.ui.button(
        label='Set Nickname Prefix',
        row=3
    )
    async def set_nickname_prefix(self, interaction: discord.Interaction, button: discord.Button):
        self.modal = CustomModal("Nickname Prefix", [
            (
                'nickname_prefix',
                discord.ui.TextInput(
                    label="Nickname Prefix",
                    placeholder="The nickname prefix that will be used when someone goes On-Duty.",
                    default=str(self.nickname_default),
                    required=False
                )
            )
        ])
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        nickname_prefix = self.modal.nickname_prefix.value

        bot = self.bot
        sett = await bot.settings.find_by_id(interaction.guild.id)
        sett['shift_management']['nickname_prefix'] = nickname_prefix
        await bot.settings.update_by_id(sett)
        self.nickname_default = nickname_prefix

    @discord.ui.button(
        label='Set Quota',
        row=2
    )
    async def set_quota(self, interaction: discord.Interaction, button: discord.Button):
        quota_hours = self.quota_default
        self.modal = CustomModal("Quota", [
            (
                'quota',
                discord.ui.TextInput(
                    label="Quota",
                    placeholder="This value will be used to judge whether a staff member has completed quota.",
                    default=td_format(datetime.timedelta(seconds=quota_hours)),
                    required=False
                )
            ), {
                "ephemeral": True
            }
        ])
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()

        try:
            seconds = time_converter(self.modal.quota.value)
        except ValueError:
            return await self.modal.followup.send(
                embed=discord.Embed(
                    title="Invalid Time",
                    description="You provided an invalid time format.",
                    color=BLANK_COLOR
                )
            )

        bot = self.bot
        sett = await bot.settings.find_by_id(interaction.guild.id)
        sett['shift_management']['quota'] = seconds
        await bot.settings.update_by_id(sett)
        self.quota_default = seconds



class ShiftConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="On-Duty Role", row=2, max_values=5)
    async def shift_role_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['shift_management']['role'] = [i.id for i in select.values]
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Shift Channel", row=1, max_values=1,
                       channel_types=[discord.ChannelType.text])
    async def shift_channel_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['shift_management']['channel'] = select.values[0].id
        await bot.settings.update_by_id(sett)

    @discord.ui.select(placeholder="Shift Management", row=0, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="Shift Management is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="Shift Management is disabled."
        )
    ], max_values=1)
    async def enabled_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['shift_management']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.button(
        label='More Options',
        row=3
    )
    async def more_options(self, interaction: discord.Interaction, button: discord.Button):
        val = await self.interaction_check(interaction)
        if val is False:
            return
        sett = await self.bot.settings.find_by_id(interaction.guild.id)
        new_view = ExtendedShiftOptions(self.bot, [
            (
                "max_staff",
                sett['shift_management'].get('maximum_staff', 0)
            ),
            (
                'quota',
                sett['shift_management'].get('quota', 0)
            ),
            (
                'nickname_prefix',
                sett['shift_management'].get('nickname_prefix', '')
            )
        ])
        await interaction.response.send_message(view=new_view, ephemeral=True)

    @discord.ui.button(
        label="Shift Types",
        row=3
    )
    async def shift_types(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if val is False:
            return

        settings = await self.bot.settings.find_by_id(interaction.guild.id)
        shift_types = settings.get('shift_types', {}).get('types', [])

        embed = discord.Embed(
            title="Shift Types",
            color=BLANK_COLOR
        )
        for item in shift_types:
            embed.add_field(
                name=f"{item['name']}",
                value=(
                    f"<:replytop:1138257149705863209> **Name:** {item['name']}\n"
                    f"<:replymiddle:1138257195121791046> **ID:** {item['id']}\n"
                    f"<:replymiddle:1138257195121791046> **Channel:** <#{item['channel']}>\n"
                    f"<:replymiddle:1138257195121791046> **Access Roles:** {','.join(['<@&{}>'.format(role) for role in item.get('access_roles') or []]) or 'None'}\n"
                    f"<:replybottom:1138257250448855090> **On-Duty Role:** {','.join(['<@&{}>'.format(role) for role in item.get('role', [])]) or 'None'}"
                ),
                inline=False
            )

        if len(embed.fields) == 0:
            embed.add_field(
                name="No Shift Types",
                value="There are no shift types on this server.",
                inline=False
            )
        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else ''
        )

        view = ShiftTypeManagement(interaction.user.id)

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

        await view.wait()
        if view.value == "create":
            data = {
                'id': next(generator),
                "name": view.name_for_creation,
                "channel": None,
                "roles": []
            }
            embed = discord.Embed(
                title="Shift Type Creation",
                description=(
                    f"<:replytop:1138257149705863209> **Name:** {data['name']}\n"
                    f"<:replymiddle:1138257195121791046> **ID:** {data['id']}\n"
                    f"<:replymiddle:1138257195121791046> **Shift Channel:** {'<#{}>'.format(data.get('channel', None)) if data.get('channel', None) is not None else 'Not set'}\n"
                    f"<:replymiddle:1138257195121791046> **On-Duty Roles:** {', '.join(['<@&{}>'.format(r) for r in data.get('role', [])]) or 'Not set'}\n"
                    f"<:replybottom:1138257250448855090> **Access Roles:** {', '.join(['<@&{}>'.format(r) for r in data.get('access_roles', [])]) or 'Not set'}\n\n\n"
                    f"*Access Roles are roles that are able to freely use this Shift Type and are able to go on-duty as this Shift Type. If an access role is selected, an individual must have it to go on-duty with this Shift Type.*"
                ),
                color=BLANK_COLOR
            )

            view = ShiftTypeCreator(interaction.user.id, data)
            view.restored_interaction = interaction
            msg = await interaction.original_response()
            await msg.edit(view=view, embed=embed)
            await view.wait()
            if view.cancelled is True:
                return

            dataset = settings.get('shift_types', {}).get('types', [])

            dataset.append(
                view.dataset
            )
            if not settings.get('shift_types'):
                settings['shift_types'] = {}
                settings['shift_types']['types'] = dataset
            else:
                settings['shift_types']['types'] = dataset

            await self.bot.settings.update_by_id(settings)
            await msg.edit(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Shift Type Created",
                    description="Your shift type has been created!",
                    color=GREEN_COLOR
                ),
                view=None
            )
        elif view.value == "delete":
            try:
                type_id = int(view.selected_for_deletion.strip())
            except ValueError:
                return await (await interaction.original_response()).edit(
                    embed=discord.Embed(
                        title="Invalid Shift Type",
                        description="The ID you have provided is not associated with a shift type.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            shift_types = settings.get('shift_types', {}).get('types', [])
            if len(shift_types) == 0:
                return await (await interaction.original_response()).edit(
                    embed=discord.Embed(
                        title="Invalid Shift Type",
                        description="The ID you have provided is not associated with a shift type.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            if type_id not in [t['id'] for t in shift_types]:
                return await (await interaction.original_response()).edit(
                    embed=discord.Embed(
                        title="Invalid Shift Type",
                        description="The ID you have provided is not associated with a shift type.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            for item in shift_types:
                if item['id'] == type_id:
                    shift_types.remove(item)
                    break

            if not settings.get('shift_types'):
                settings['shift_types'] = {}

            settings['shift_types']['types'] = shift_types
            await self.bot.settings.update_by_id(settings)
            msg = await interaction.original_response()
            await msg.edit(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Shift Type Deleted",
                    description="Your shift type has been deleted!",
                    color=GREEN_COLOR
                ),
                view=None
            )

    @discord.ui.button(
        label="Role Quotas",
        row=3
    )
    async def role_quotas(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if val is False:
            return

        settings = await self.bot.settings.find_by_id(interaction.guild.id)
        role_quotas = settings.get('shift_management').get('role_quotas', [])

        embed = discord.Embed(
            title="Role Quotas",
            description="",
            color=BLANK_COLOR
        )
        for item in role_quotas:
            role_id, particular_quota = item['role'], item['quota']
            # role = interaction.guild.get_role(role_id)
            try:
                roles = await interaction.guild.fetch_roles()
                role = discord.utils.get(roles, id=role_id)
            except discord.HTTPException:
                continue

            if not role:
                continue
            embed.description += f"{role.mention} `{role_id}` • {td_format(datetime.timedelta(seconds=particular_quota))}\n"

        if len(embed.description) == 0:
            embed.add_field(
                name="No Role Quotas",
                value="There are no role quotas in this server.",
                inline=False
            )
        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else ''
        )

        view = RoleQuotaManagement(interaction.user.id)

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

        await view.wait()
        if view.value == "create":
            data = {
                'role': 0,
                "quota": 0
            }
            embed = discord.Embed(
                title="Role Quota Creation",
                description=(
                    f"<:replytop:1138257149705863209> **Role:** {'<@&{}>'.format(data['role']) if data['role'] != 0 else 'Not set'}\n"
                    f"<:replybottom:1138257250448855090> **Quota:** {td_format(datetime.timedelta(seconds=data['quota']))}\n"
                ),
                color=BLANK_COLOR
            )

            view = RoleQuotaCreator(self.bot, interaction.user.id, data)
            view.restored_interaction = interaction
            msg = await interaction.original_response()
            await msg.edit(view=view, embed=embed)
            await view.wait()
            if view.cancelled is True:
                return

            dataset = settings.get('shift_management', {}).get('role_quotas', [])

            dataset.append(
                view.dataset
            )
            settings['shift_management']['role_quotas'] = dataset

            await self.bot.settings.update_by_id(settings)
            await msg.edit(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Role Quota Created",
                    description="Your Role Quota has been created!",
                    color=GREEN_COLOR
                ),
                view=None
            )
        elif view.value == "delete":
            try:
                type_id = int(view.selected_for_deletion.strip())
            except ValueError:
                return await (await interaction.original_response()).edit(
                    embed=discord.Embed(
                        title="Invalid Role ID",
                        description="The ID you have provided is not associated with a Role Quota.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            role_quotas = settings.get('shift_management', {}).get('role_quotas', [])
            if len(role_quotas) == 0:
                return await (await interaction.original_response()).edit(
                    embed=discord.Embed(
                        title="Invalid Role ID",
                        description="The ID you have provided is not associated with a Role Quota.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            if type_id not in [t['role'] for t in role_quotas]:
                return await (await interaction.original_response()).edit(
                    embed=discord.Embed(
                        title="Invalid Role ID",
                        description="The ID you have provided is not associated with a Role Quota.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            for item in role_quotas:
                if item['role'] == type_id:
                    role_quotas.remove(item)
                    break

            settings['shift_management']['role_quotas'] = role_quotas
            await self.bot.settings.update_by_id(settings)
            msg = await interaction.original_response()
            await msg.edit(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Role Quota Deleted",
                    description="Your Role Quota has been deleted!",
                    color=GREEN_COLOR
                ),
                view=None
            )


class RAConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="RA Role", row=2, max_values=1, min_values=0)
    async def ra_role_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['staff_management']['ra_role'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

class ExtendedPunishmentConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Kick Channel", row=0, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def kick_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot

        sett = await bot.settings.find_by_id(guild_id)
        sett['punishments']['kick_channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Ban Channel", row=1, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def ban_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot

        sett = await bot.settings.find_by_id(guild_id)
        sett['punishments']['ban_channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="BOLO Channel", row=2, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def bolo_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot

        sett = await bot.settings.find_by_id(guild_id)
        sett['punishments']['bolo_channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)



class PunishmentsConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(placeholder="ROBLOX Punishments", row=0, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="ROBLOX Punishments are enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="ROBLOX Punishments are disabled."
        )
    ], max_values=1)
    async def enabled_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['punishments']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Punishments Channel", row=1, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def punishment_channel_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        sett['punishments']['channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.button(
        label='More Options',
        row=2
    )
    async def more_options(self, interaction: discord.Interaction, button: discord.Button):
        val = await self.interaction_check(interaction)
        if val is False:
            return
        sett = await self.bot.settings.find_by_id(interaction.guild.id)
        new_view = ExtendedPunishmentConfiguration(self.bot, interaction.user.id, [
            (
                "Kick Channel",
                [discord.utils.get(interaction.guild.channels,
                                   id=sett.get('punishments', {}).get('kick_channel', 0))]
            ),
            (
                "Ban Channel",
                [discord.utils.get(interaction.guild.channels,
                                   id=sett.get('punishments', {}).get('ban_channel', 0))]
            ),
            (
                "BOLO Channel",
                [discord.utils.get(interaction.guild.channels,
                                   id=sett.get('punishments', {}).get('bolo_channel', 0))]
            ),
        ])
        await interaction.response.send_message(view=new_view, ephemeral=True)


class GameSecurityConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(placeholder="Game Security", row=0, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="Game Security is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="Game Security is disabled."
        )
    ], max_values=1)
    async def enabled_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_security'):
            sett['game_security'] = {}
        sett['game_security']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Webhook Channel", row=1, max_values=1, min_values=0,
                       channel_types=[discord.ChannelType.text])
    async def security_webhook_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_security'):
            sett['game_security'] = {}
        sett['game_security']['webhook_channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Alert Channel", row=2, max_values=1, min_values=0,
                       channel_types=[discord.ChannelType.text])
    async def security_alert_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_security'):
            sett['game_security'] = {}
        sett['game_security']['channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Mentionables", row=3, max_values=5, min_values=0)
    async def security_mentionables(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_security'):
            sett['game_security'] = {}
        sett['game_security']['role'] = [i.id for i in select.values]
        await bot.settings.update_by_id(sett)


class ExtendedGameLogging(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Message Logging Channel", row=0, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def message_logging_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_logging'):
            sett['game_logging'] = {"message": {}}
        if not sett.get('game_logging', {}).get('message'):
            sett['game_logging']['message'] = {}
        sett['game_logging']['message']['channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="STS Logging Channel", row=1, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def sts_logging_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_logging'):
            sett['game_logging'] = {"sts": {}}
        if not sett.get('game_logging', {}).get('sts'):
            sett['game_logging']['sts'] = {}
        sett['game_logging']['sts']['channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Priority Logging Channel", row=2, max_values=1,
                       min_values=0, channel_types=[discord.ChannelType.text])
    async def priority_logging_channel(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_logging'):
            sett['game_logging'] = {"priority": {}}
        if not sett.get('game_logging', {}).get('priority'):
            sett['game_logging']['priority'] = {}
        sett['game_logging']['priority']['channel'] = int(select.values[0].id or None)
        await bot.settings.update_by_id(sett)


class AntipingConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(placeholder="Anti-Ping", row=0, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="Anti-Ping is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="Anti-Ping is disabled."
        )
    ], max_values=1)
    async def antiping_enabled(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('antiping'):
            sett['antiping'] = {}

        sett['antiping']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Affected Roles", row=1, max_values=5, min_values=0)
    async def affected_roles(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('antiping'):
            sett['antiping'] = {
                'enabled': False,
                'role': [],
                'bypass_role': []
            }
        sett['antiping']['role'] = [i.id for i in select.values]
        await bot.settings.update_by_id(sett)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Bypass Roles", row=2, max_values=5, min_values=0)
    async def bypass_roles(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('antiping'):
            sett['antiping'] = {
                'enabled': False,
                'role': [],
                'bypass_role': []
            }
        sett['antiping']['bypass_role'] = [i.id for i in select.values]
        await bot.settings.update_by_id(sett)

    @discord.ui.select(placeholder="Use Hierarchy", row=3, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="Hierarchy is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="Hierarchy is disabled."
        )
    ], max_values=1)
    async def hierarchy_enabled(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('antiping'):
            sett['antiping'] = {
                'enabled': False,
                'role': [],
                'bypass_role': [],
                'use_hierarchy': None
            }

        sett['antiping']['use_hierarchy'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False


class GameLoggingConfiguration(AssociationConfigurationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.select(placeholder="Message Logging", row=0, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="Message Logging is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="Message Logging is disabled."
        )
    ], max_values=1)
    async def message_logging_enabled(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_logging'):
            sett['game_logging'] = {
                "message": {}
            }
        if not sett.get('game_logging', {}).get('message'):
            sett['game_logging']['message'] = {}

        sett['game_logging']['message']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.select(placeholder="STS Logging", row=1, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="STS Logging is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="STS Logging is disabled."
        )
    ], max_values=1)
    async def sts_logging_enabled(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_logging'):
            sett['game_logging'] = {
                "sts": {}
            }
        if not sett.get('game_logging', {}).get('sts'):
            sett['game_logging']['sts'] = {}

        sett['game_logging']['sts']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.select(placeholder="Priority Logging", row=2, options=[
        discord.SelectOption(
            label='Enabled',
            value="enabled",
            description="Priority Logging is enabled."
        ),
        discord.SelectOption(
            label="Disabled",
            value="disabled",
            description="Priority Logging is disabled."
        )
    ], max_values=1)
    async def priority_logging_enabled(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = await self.interaction_check(interaction)
        if not value: return

        await interaction.response.defer()
        guild_id = interaction.guild.id

        bot = self.bot
        sett = await bot.settings.find_by_id(guild_id)
        if not sett.get('game_logging'):
            sett['game_logging'] = {
                "priority": {}
            }
        if not sett.get('game_logging', {}).get('priority'):
            sett['game_logging']['priority'] = {}

        sett['game_logging']['priority']['enabled'] = bool(select.values[0] == "enabled")
        await bot.settings.update_by_id(sett)
        for i in select.options:
            i.default = False

    @discord.ui.button(
        label='More Options',
        row=3
    )
    async def more_options(self, interaction: discord.Interaction, button: discord.Button):
        val = await self.interaction_check(interaction)
        if val is False:
            return
        sett = await self.bot.settings.find_by_id(interaction.guild.id)
        new_view = ExtendedGameLogging(self.bot, interaction.user.id, [
            (
                "Priority Logging Channel",
                [discord.utils.get(interaction.guild.channels,
                                   id=sett.get('game_logging', {}).get('priority', {}).get('channel', 0))]
            ),
            (
                "Message Logging Channel",
                [discord.utils.get(interaction.guild.channels,
                                   id=sett.get('game_logging', {}).get('message', {}).get('channel', 0))]
            ),
            (
                "STS Logging Channel",
                [discord.utils.get(interaction.guild.channels,
                                   id=sett.get('game_logging', {}).get('sts', {}).get('channel', 0))]
            ),
        ])
        await interaction.response.send_message(view=new_view, ephemeral=True)


class RoleSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=600.0)
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
    async def role_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success, row=2)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.RoleSelect):
                select = child

        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.value = select.values
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)


class ExpandedRoleSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=600.0)
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

    @discord.ui.select(cls=discord.ui.RoleSelect, row=0)
    async def role_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success, row=3)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        selects = []
        for child in self.children:
            if isinstance(child, discord.ui.RoleSelect):
                selects.append(child)

        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            value_list = [s.values for s in selects]
            new_list = []
            for list_of_values in value_list:
                for value in list_of_values:
                    if value not in new_list:
                        new_list.append(value)
            self.value = new_list
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

    @discord.ui.button(label="I have more than 25 roles", style=discord.ButtonStyle.secondary, row=4)
    async def expand(self, interaction: discord.Interaction, button: discord.ui.Button):
        for i in self.children:
            print(i)
            if isinstance(i, discord.ui.RoleSelect):
                for value in range(1, 3):
                    print(value)
                    instance = discord.ui.RoleSelect(row=value, placeholder="Select roles", max_values=25)
                    print('?')
                    # async def callback(interaction: discord.Interaction, select: discord.ui.Select):
                    #     await interaction.response.defer()

                    instance.callback = i.callback
                    print('*')
                    self.add_item(instance)
                    print('!')
        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.defer()


class UserSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=600.0)
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
    async def user_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success, row=2)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.UserSelect):
                select = child

        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.value = select.values
            self.stop()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)


class ChannelSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__(timeout=600.0)
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

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text]
    )
    async def channel_select(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success, row=2)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.ChannelSelect):
                select = child

        if interaction.user.id == self.user_id:
            await interaction.response.defer()
            self.value = select.values
            self.stop()
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)


class CheckMark(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600.0)
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(emoji="✅", style=discord.ButtonStyle.gray)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(emoji="❎", style=discord.ButtonStyle.gray)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True, thinking=True)
            return await generalised_interaction_check_failure(interaction.followup)

        await interaction.response.defer()
        self.value = False
        self.stop()


class CompleteReminder(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600.0)

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Mark as Complete", style=discord.ButtonStyle.gray)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        embed.set_footer(
            text="Completed by {0.name}".format(interaction.user),
            icon_url=interaction.user.avatar.url,
        )
        embed.timestamp = datetime.datetime.now()
        embed.color = 0xED4348
        embed.title = "<:ERMCheck:1111089850720976906> Reminder Completed"

        for item in self.children:
            item.disabled = True
            item.label = "Completed"
            item.style = discord.ButtonStyle.green

        await interaction.message.edit(
            embed=embed,
            view=self,
            content=f"<:ERMCheck:1111089850720976906>  **{interaction.user.name}** completed this reminder.",
        )

        self.stop()


class ReloadView(discord.ui.View):
    def __init__(self, user_id: int, custom_callback: typing.Callable, args: list):
        super().__init__(timeout=2100)
        self.user_id = user_id
        self.custom_callback = custom_callback
        self.callback_args = args
        self.message = None

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def _temp_disable(self, timer: int):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        await asyncio.sleep(timer)
        for item in self.children:
            item.disabled = False
        await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(label="Reload", emoji="<:lastupdated:1176999148084535326>", style=discord.ButtonStyle.secondary)
    async def _reload(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()
        await self.custom_callback(
            *self.callback_args
        )
        await self._temp_disable(30)


class ShiftTypeCreator(discord.ui.View):
    def __init__(self, user_id: int, dataset: dict):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.restored_interaction = None
        self.dataset = dataset
        self.cancelled = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def refresh_ui(self, message: discord.Message):
        embed = discord.Embed(
            title="Shift Type Creation",
            description=(
                f"<:replytop:1138257149705863209> **Name:** {self.dataset['name']}\n"
                f"<:replymiddle:1138257195121791046> **ID:** {self.dataset['id']}\n"
                f"<:replymiddle:1138257195121791046> **Shift Channel:** {'<#{}>'.format(self.dataset.get('channel', None)) if self.dataset.get('channel', None) is not None else 'Not set'}\n"
                f"<:replymiddle:1138257195121791046> **On-Duty Roles:** {', '.join(['<@&{}>'.format(r) for r in self.dataset.get('role', [])]) or 'Not set'}\n"
                f"<:replybottom:1138257250448855090> **Access Roles:** {', '.join(['<@&{}>'.format(r) for r in self.dataset.get('access_roles', [])]) or 'Not set'}\n\n\n"
                f"*Access Roles are roles that are able to freely use this Shift Type and are able to go on-duty as this Shift Type. If an access role is selected, an individual must have it to go on-duty with this Shift Type.*"
            ),
            color=BLANK_COLOR
        )

        if all(
                [
                    self.dataset.get('channel') is not None
                ]
        ):
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True

        await message.edit(embed=embed, view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="On-Duty Roles", row=0, max_values=25)
    async def mentioned_roles_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        await interaction.response.defer()

        self.dataset['role'] = [i.id for i in select.values]
        try:
            await self.refresh_ui(interaction.message)
        except discord.NotFound:
            await self.refresh_ui(await self.restored_interaction.original_response())

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Access Roles", row=1, max_values=25, min_values=0)
    async def access_roles_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        await interaction.response.defer()

        self.dataset['access_roles'] = [i.id for i in select.values]
        try:
            await self.refresh_ui(interaction.message)
        except discord.NotFound:
            await self.refresh_ui(await self.restored_interaction.original_response())

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Shift Channel", row=2, max_values=1,
                       channel_types=[discord.ChannelType.text])
    async def channel_select(
            self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        await interaction.response.defer()

        self.dataset['channel'] = [i.id for i in select.values][0]
        try:
            await self.refresh_ui(interaction.message)
        except discord.NotFound:
            await self.refresh_ui(await self.restored_interaction.original_response())

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer(ephemeral=True)
        self.cancelled = True
        await interaction.followup.send(embed=discord.Embed(
            title="Successfully cancelled",
            description="This Shift Type has not been created.",
            color=BLANK_COLOR
        ), ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.NotFound:
            await (await self.restored_interaction.original_response()).delete()
        self.stop()

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        disabled=True,
        row=3
    )
    async def finish(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer()
        self.cancelled = False
        self.stop()


class RoleQuotaCreator(discord.ui.View):
    def __init__(self, bot, user_id: int, dataset: dict):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.bot = bot
        self.restored_interaction = None
        self.dataset = dataset
        self.cancelled = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def refresh_ui(self, message: discord.Message):
        embed = discord.Embed(
            title="Role Quota Creation",
            description=(
                f"<:replytop:1138257149705863209> **Role:** {'<@&{}>'.format(self.dataset['role']) if self.dataset['role'] != 0 else 'Not set'}\n"
                f"<:replybottom:1138257250448855090> **Quota:** {td_format(datetime.timedelta(seconds=self.dataset['quota']))}\n"
            ),
            color=BLANK_COLOR
        )

        if all(
                [
                    self.dataset.get('role') != 0,
                    self.dataset.get('quota') != 0
                ]
        ):
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True

        await message.edit(embed=embed, view=self)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Binded Role", row=0, max_values=1, min_values=0)
    async def mentioned_roles_select(
            self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        if len(select.values) == 0:
            return await interaction.response.defer(thinking=False)

        settings = await self.bot.settings.find_by_id(interaction.guild.id)
        already_roles = []
        for item in settings.get('shift_management', {}).get('role_quotas', []):
            already_roles.append(item['role'])
        self.dataset['role'] = select.values[0].id if select.values else 0
        if self.dataset['role'] in already_roles:
            self.dataset['role'] = 0

        if self.dataset['role'] == 0:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Unavailable Role",
                    description="This role already has a specified quota attached to it.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )
        else:
            await interaction.response.defer()
        try:
            await self.refresh_ui(interaction.message)
        except discord.NotFound:
            await self.refresh_ui(await self.restored_interaction.original_response())

    @discord.ui.button(
        label='Set Quota',
        row=1
    )
    async def set_quota(self, interaction: discord.Interaction, button: discord.Button):
        quota_hours = self.dataset['quota']
        self.modal = CustomModal("Quota", [
            (
                'quota',
                discord.ui.TextInput(
                    label="Quota",
                    placeholder="This value will be used to judge whether a staff member has completed quota.",
                    default=f"{td_format(datetime.timedelta(seconds=quota_hours))}",
                    required=False
                )
            )
        ])
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()

        try:
            seconds = time_converter(self.modal.quota.value)
        except ValueError:
            return

        self.dataset['quota'] = seconds
        try:
            await self.refresh_ui(interaction.message)
        except discord.NotFound:
            await self.refresh_ui(await self.restored_interaction.original_response())

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer(ephemeral=True)
        self.cancelled = True
        await interaction.followup.send(embed=discord.Embed(
            title="Successfully cancelled",
            description="This Role Quota has not been created.",
            color=BLANK_COLOR
        ), ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.NotFound:
            await (await self.restored_interaction.original_response()).delete()
        self.stop()

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        disabled=True,
        row=3
    )
    async def finish(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer()
        self.cancelled = False
        self.stop()


class CustomCommandOptionSelect(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.modal = None
        self.value = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Create",
        style=discord.ButtonStyle.green,
        row=0
    )
    async def create_custom_command(self, interaction: discord.Interaction, _: discord.Button):
        self.value = "create"
        self.modal = CustomModal(
            "Create a Custom Command",
            [
                (
                    "name",
                    discord.ui.TextInput(
                        label="Custom Command Name"
                    )
                )
            ],
            {
                "thinking": False
            }
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        if self.modal.name.value is None:
            return

        self.stop()

    # @discord.ui.button(
    #     label="Edit",
    #     style=discord.ButtonStyle.secondary,
    #     row=0
    # )
    # async def edit_custom_command(self, interaction: discord.Interaction, button: discord.Button):
    #     self.value = "edit"
    #     await interaction.response.defer()
    #     self.stop()

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def delete_custom_command(self, interaction: discord.Interaction, _: discord.Button):
        self.value = "delete"
        self.modal = CustomModal(
            "Delete a custom command",
            [
                (
                    "name",
                    discord.ui.TextInput(
                        placeholder="Command Name", label="Command Name"
                    ),
                )
            ],
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        if self.modal.name.value is None:
            return
        self.stop()


class ShiftMenu(discord.ui.View):
    def __init__(
            self,
            bot: commands.Bot,
            starting_state: typing.Literal['on', 'break', 'off'],
            user_id: int,
            shift_type: str,
            starting_document: dict | None = None,
            starting_container: ShiftItem | None = None,
    ):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.state = starting_state
        self.bot = bot
        self.shift_type = shift_type
        self.shift = starting_document
        self.contained_document = starting_container
        self.message = None

        self.check_buttons(self.state)

    def check_buttons(self, option: typing.Literal['on', 'break', 'off']):
        if option == "on":
            buttons = ["Toggle Break", "Off-Duty"]
        elif option == "break":
            buttons = ["On-Duty", "Off-Duty"]
        else:
            buttons = ["On-Duty"]

        for item in self.children:
            if item.label not in buttons:
                item.disabled = True
            else:
                item.disabled = False

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def cycle_ui(self, option: typing.Literal['on', 'break', 'off'], message: discord.Message):
        shift = self.shift
        contained_document = self.contained_document
        uis = {
            "on": discord.Embed(
                title="<:ShiftStarted:1178033763477889175> **Shift Started**",
                color=GREEN_COLOR
            ).set_author(
                name=message.guild.name,
                icon_url=message.guild.icon.url if message.guild.icon else ''
            ).add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(self.shift['Breaks'])}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            ),
            'off': discord.Embed(
                title="<:ShiftEnded:1178035088655646880> **Off-Duty**",
                color=RED_COLOR
            ).set_author(
                name=message.guild.name,
                icon_url=message.guild.icon.url if message.guild.icon else ''
            ).add_field(
                name="Shift Overview",
                value=(
                    f"<:replytop:1138257149705863209> **Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(self.shift['Breaks'])}\n"
                    f"<:replybottom:1138257250448855090> **Ended:** <t:{int(contained_document.end_epoch or datetime.datetime.now(tz=pytz.UTC).timestamp())}:R>"
                ),
                inline=False
            )
        }
        if option == "break":
            selected_ui = discord.Embed(
                title="<:ShiftBreak:1178034531702411375> **On-Break**",
                color=ORANGE_COLOR
            ).set_author(
                name=message.guild.name,
                icon_url=message.guild.icon.url if message.guild.icon else ''
            ).add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Shift Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Break Started:** <t:{int(contained_document.breaks[0].start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(self.shift['Breaks'])}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            )
        else:
            selected_ui = uis[option]

        if not selected_ui:
            return
        self.check_buttons(option)
        await message.edit(embed=selected_ui, view=self)

    async def on_timeout(self) -> None:
        if not self.message:
            for item in self.children:
                item.disabled = True

            return await self.message.edit(
                view=self
            )

    @discord.ui.button(label="On-Duty", style=discord.ButtonStyle.green)
    async def on_duty_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer(thinking=False)
        if self.state == "break":
            self.shift["Breaks"][-1]['EndEpoch'] = datetime.datetime.now(tz=pytz.UTC).timestamp()
            self.shift['_id'] = self.contained_document.id
            await self.bot.shift_management.shifts.update_by_id(self.shift)
            self.contained_document = await self.bot.shift_management.fetch_shift(self.contained_document.id)
            await self.cycle_ui('on', interaction.message)
            self.bot.dispatch('break_end', self.contained_document.id)
            return

        settings = await self.bot.settings.find_by_id(interaction.guild.id)
        access = True
        for item in settings.get('shift_management', {}).get('shift_types', []):
            if isinstance(item, dict):
                if item['name'] == self.shift_type:
                    access_roles = item.get('access_roles') or []
                    if len(access_roles) > 0:
                        access = False
                        for role in access_roles:
                            if role in [i.id for i in interaction.user.roles]:
                                access = True
                                break
        if not access:
            return await interaction.response.send_message(embed=discord.Embed(
                title="No Access",
                description="You are not permitted to go on-duty as this Shift Type.",
                color=blank_color
            ), ephemeral=True)


        object_id = await self.bot.shift_management.add_shift_by_user(
            interaction.user,
            self.shift_type,
            [],
            interaction.guild.id
        )
        self.contained_document: ShiftItem = await self.bot.shift_management.fetch_shift(object_id)
        self.shift = await self.bot.shift_management.shifts.find_by_id(object_id)
        await self.cycle_ui('on', interaction.message)
        self.bot.dispatch('shift_start', self.shift['_id'])
        return

    @discord.ui.button(label="Toggle Break", style=discord.ButtonStyle.secondary)
    async def toggle_break_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer(thinking=False)
        self.shift['Breaks'].append({
            "StartEpoch": datetime.datetime.now(tz=pytz.UTC).timestamp(),
            "EndEpoch": 0
        })
        self.shift['_id'] = self.contained_document.id
        await self.bot.shift_management.shifts.update_by_id(self.shift)
        self.contained_document = await self.bot.shift_management.fetch_shift(self.contained_document.id)
        await self.cycle_ui('break', interaction.message)
        self.bot.dispatch('break_start', self.contained_document.id)
        return

    @discord.ui.button(label="Off-Duty", style=discord.ButtonStyle.red)
    async def off_duty_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer(thinking=False)
        await self.bot.shift_management.end_shift(self.contained_document.id, self.contained_document.guild)
        self.contained_document = await self.bot.shift_management.fetch_shift(self.contained_document.id)
        self.shift = await self.bot.shift_management.shifts.find_by_id(self.contained_document.id)
        await self.cycle_ui('off', interaction.message)
        self.bot.dispatch('shift_end', self.contained_document.id)
        return


class AdministratedShiftMenu(discord.ui.View):
    def __init__(
            self,
            bot: commands.Bot,
            starting_state: typing.Literal['on', 'break', 'off'],
            user_id: int,
            target_id: int,
            shift_type: str,
            starting_document: dict | None = None,
            starting_container: ShiftItem | None = None,
    ):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.target_id = target_id
        self.state = starting_state
        self.bot = bot
        self.shift_type = shift_type
        self.shift = starting_document
        self.contained_document = starting_container
        self.message = None

        self.check_buttons(self.state)

    def check_buttons(self, option: typing.Literal['on', 'break', 'off']):
        if option == "on":
            buttons = ["Toggle Break", "Off-Duty", "Other Options"]
        elif option == "break":
            buttons = ["On-Duty", "Off-Duty", "Other Options"]
        else:
            buttons = ["On-Duty", "Other Options"]

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label not in buttons:
                    item.disabled = True
                else:
                    item.disabled = False

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def cycle_ui(self, option: typing.Literal['on', 'break', 'off', 'void'], message: discord.Message):
        shift = self.shift
        contained_document = self.contained_document
        previous_shifts = [i async for i in self.bot.shift_management.shifts.db.find({
            "UserID": self.target_id,
            "Guild": message.guild.id,
            "EndEpoch": {'$ne': 0}
        })]
        self.state = option
        if option == "void":
            selected_ui = discord.Embed(
                title="<:ShiftEnded:1178035088655646880> **Off-Duty**",
                color=RED_COLOR
            ).set_author(
                name=message.guild.name,
                icon_url=message.guild.icon.url if message.guild.icon else ''
            ).add_field(
                name="Current Statistics",
                value=(
                    f"<:replytop:1138257149705863209> **Total Shift Duration:** {td_format(datetime.timedelta(seconds=sum([get_elapsed_time(item) for item in previous_shifts])))}\n"
                    f"<:replymiddle:1138257195121791046> **Total Shifts:** {len(previous_shifts)}\n"
                    f"<:replybottom:1138257250448855090> **Average Shift Duration:** {td_format(datetime.timedelta(seconds=(sum([get_elapsed_time(item) for item in previous_shifts]).__truediv__(len(previous_shifts) or 1))))}\n"
                ),
                inline=False
            )
        elif option not in ["void", "break"]:
            uis = {
                "on": discord.Embed(
                    title="<:ShiftStarted:1178033763477889175> **Shift Started**",
                    color=GREEN_COLOR
                ).set_author(
                    name=message.guild.name,
                    icon_url=message.guild.icon.url if message.guild.icon else ''
                ).add_field(
                    name="Current Shift",
                    value=(
                        f"<:replytop:1138257149705863209> **Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                        f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                        f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                    ),
                    inline=False
                ),
                'off': discord.Embed(
                    title="<:ShiftEnded:1178035088655646880> **Off-Duty**",
                    color=RED_COLOR
                ).set_author(
                    name=message.guild.name,
                    icon_url=message.guild.icon.url if message.guild.icon else ''
                ).add_field(
                    name="Shift Overview",
                    value=(
                        f"<:replytop:1138257149705863209> **Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                        f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                        f"<:replybottom:1138257250448855090> **Ended:** <t:{int(contained_document.end_epoch or datetime.datetime.now(tz=pytz.UTC).timestamp())}:R>"
                    ),
                    inline=False
                ),
            }
        if option == "break":
            selected_ui = discord.Embed(
                title="<:ShiftBreak:1178034531702411375> **On-Break**",
                color=ORANGE_COLOR
            ).set_author(
                name=message.guild.name,
                icon_url=message.guild.icon.url if message.guild.icon else ''
            ).add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Shift Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Break Started:** <t:{int(contained_document.breaks[0].start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            )
        elif option not in ["void", "break"]:
            selected_ui = uis[option]

        if not selected_ui:
            return
        self.check_buttons(option)
        await message.edit(embed=selected_ui, view=self)

    async def on_timeout(self) -> None:
        if not self.message:
            for item in self.children:
                item.disabled = True

            return await self.message.edit(
                view=self
            )

    async def _manipulate_shift_time(self, message, op: typing.Literal["add", "subtract"], amount: int):
        self.message = message
        member = await self.message.guild.fetch_member(self.target_id)
        guild = self.message.guild

        operations = {
            "add": self.bot.shift_management.add_time_to_shift,
            "subtract": self.bot.shift_management.remove_time_from_shift
        }

        chosen_operation = operations[op]
        if self.contained_document is not None:
            if self.contained_document.end_epoch == 0:
                await chosen_operation(self.contained_document.id, amount)
                self.bot.dispatch('shift_edit', self.contained_document.id,
                                  'added_time' if op == "add" else 'removed_time',
                                  (await self.message.guild.fetch_member(self.user_id)))
                return

        oid = await self.bot.shift_management.add_shift_by_user(
            member, self.shift_type, [], guild.id
        )
        await chosen_operation(oid, amount)
        await self.bot.shift_management.end_shift(oid, guild.id)

    @discord.ui.button(label="On-Duty", style=discord.ButtonStyle.green)
    async def on_duty_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer(thinking=False)
        if self.state == "break":
            self.shift["Breaks"][-1]['EndEpoch'] = datetime.datetime.now(tz=pytz.UTC).timestamp()
            self.shift['_id'] = self.contained_document.id
            await self.bot.shift_management.shifts.update_by_id(self.shift)
            self.contained_document = await self.bot.shift_management.fetch_shift(self.contained_document.id)
            await self.cycle_ui('on', interaction.message)
            self.bot.dispatch('break_end', self.contained_document.id)
            return

        object_id = await self.bot.shift_management.add_shift_by_user(
            await interaction.guild.fetch_member(self.target_id),
            self.shift_type,
            [],
            interaction.guild.id
        )
        self.contained_document: ShiftItem = await self.bot.shift_management.fetch_shift(object_id)
        self.shift = await self.bot.shift_management.shifts.find_by_id(object_id)
        await self.cycle_ui('on', interaction.message)
        self.bot.dispatch('shift_start', self.shift['_id'])
        return

    @discord.ui.button(label="Toggle Break", style=discord.ButtonStyle.secondary)
    async def toggle_break_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer(thinking=False)
        self.shift['Breaks'].append({
            "StartEpoch": datetime.datetime.now(tz=pytz.UTC).timestamp(),
            "EndEpoch": 0
        })
        self.shift['_id'] = self.contained_document.id
        await self.bot.shift_management.shifts.update_by_id(self.shift)
        self.contained_document = await self.bot.shift_management.fetch_shift(self.contained_document.id)
        await self.cycle_ui('break', interaction.message)
        self.bot.dispatch('break_start', self.contained_document.id)
        return

    @discord.ui.button(label="Off-Duty", style=discord.ButtonStyle.red)
    async def off_duty_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer(thinking=False)
        await self.bot.shift_management.end_shift(self.contained_document.id, self.contained_document.guild)
        self.contained_document = await self.bot.shift_management.fetch_shift(self.contained_document.id)
        self.shift = await self.bot.shift_management.shifts.find_by_id(self.contained_document.id)
        await self.cycle_ui('off', interaction.message)
        self.bot.dispatch('shift_end', self.contained_document.id)
        return

    @discord.ui.select(placeholder="Other Options", options=[
        discord.SelectOption(
            label="Add Time",
            value="add",
            description="Add time to an ongoing shift.",
        ),
        discord.SelectOption(
            label="Subtract Time",
            value="subtract",
            description="Subtract time to an ongoing shift.",
        ),
        discord.SelectOption(
            label="Void shift",
            value="void",
            description="Void an ongoing shift.",
        ),
        discord.SelectOption(
            label="Clear Member Shifts",
            value="clear",
            description="Remove all shifts associated with this member.",
        ),
    ], row=1)
    async def other_options(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = select.values[0]
        if value not in ["add", "subtract"]:
            await interaction.response.defer(thinking=False)
        if value == "add":
            self.modal = CustomModal(
                title="Add Time",
                options=[(
                    'time',
                    discord.ui.TextInput(
                        label="Time",
                        placeholder="How much time to add to this shift?"
                    )
                )], epher_args={
                    "ephemeral": True,
                    "thinking": False
                }
            )
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()
            unfiltered = self.modal.time.value
            try:
                converted = time_converter(unfiltered)
            except ValueError:
                return await self.modal.interaction.followup.send(
                    embed=discord.Embed(
                        title="Invalid Time",
                        description="I could not convert this time. Please try again.",
                        color=BLANK_COLOR
                    )
                )

            await self._manipulate_shift_time(interaction.message, "add", converted)
            await self.cycle_ui(self.state, interaction.message)
        elif value == "subtract":
            self.modal = CustomModal(
                title="Subtract Time",
                options=[(
                    'time',
                    discord.ui.TextInput(
                        label="Time",
                        placeholder="How much time to subtract from this shift?"
                    )
                )], epher_args={
                    "ephemeral": True,
                    "thinking": False
                }
            )
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()
            unfiltered = self.modal.time.value
            try:
                converted = time_converter(unfiltered)
            except ValueError:
                return await self.modal.interaction.followup.send(
                    embed=discord.Embed(
                        title="Invalid Time",
                        description="I could not convert this time. Please try again.",
                        color=BLANK_COLOR
                    )
                )

            await self._manipulate_shift_time(interaction.message, "add", converted)
            await self.cycle_ui(self.state, interaction.message)

        elif value == "void":
            self.bot.dispatch('shift_void', interaction.user, self.contained_document.id)
            await asyncio.sleep(2)
            await self.bot.shift_management.shifts.delete_by_id(self.contained_document.id)
            self.contained_document = None
            self.shift = None
            await self.cycle_ui('void', interaction.message)

        elif value == "clear":
            all_target_shifts = [shift async for shift in self.bot.shift_management.shifts.db.find({
                "UserID": self.target_id, 'Guild': interaction.guild.id
            })]
            for item in all_target_shifts:
                await self.bot.shift_management.shifts.delete_by_id(item['_id'])
            self.shift = None
            self.contained_document = None
            await self.cycle_ui('void', interaction.message)

class ActivityNoticeManagement(discord.ui.View):
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=900.0)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Erase Pending Requests",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def erase_pending_requests(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased Pending Requests",
                description="All pending activity notice requests have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )


        async for item in self.bot.loas.db.find({
            "guild_id": interaction.guild.id,
            "accepted": False,
            "denied": False,
            "voided": False
        }):
            await self.bot.loas.delete_by_id(item['_id'])

    @discord.ui.button(
        label="Erase LOA Notices",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def erase_loa_notices(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased LOA Notices",
                description="All LOA notices have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        async for item in self.bot.loas.db.find({
            "guild_id": interaction.guild.id,
            "type": "LOA",
            "accepted": True
        }):
            await self.bot.loas.delete_by_id(item['_id'])


    @discord.ui.button(
        label="Erase RA Notices",
        style=discord.ButtonStyle.danger,
        row=2
    )
    async def erase_ra_notices(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased RA Notices",
                description="All RA notices have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        async for item in self.bot.loas.db.find({
            "guild_id": interaction.guild.id,
            "type": "RA",
            "accepted": True
        }):
            await self.bot.loas.delete_by_id(item['_id'])


class PunishmentManagement(discord.ui.View):
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=900.0)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Erase All Punishments",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def erase_all_punishments(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased All Punishments",
                description="All punishments have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        await self.bot.punishments.remove_warnings_by_spec(guild_id=interaction.guild.id)



    @discord.ui.button(
        label="Erase Punishments By Type",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def erase_type_punishments(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        modal = CustomModal(
            "Punishment Type",
            [
                (
                    'punishment_type',
                    discord.ui.TextInput(
                        label="Punishment Type",
                        placeholder="This is case-sensitive."
                    )
                )
            ],
            {
                'ephemeral': True
            }
        )

        await interaction.response.send_modal(modal)
        await modal.wait()
        sustained_interaction = modal.interaction

        count = await self.bot.punishments.db.count_documents({
            "Guild": interaction.guild.id,
            "Type": modal.punishment_type.value
        })
        if count == 0:
            return await sustained_interaction.followup.send(
                embed=discord.Embed(
                    title="Not Found",
                    description="There are no punishments with this type.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        await sustained_interaction.followup.send(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased Punishments",
                description=f"All punishments of **{modal.punishment_type.value}** have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )


        await self.bot.punishments.remove_warnings_by_spec(guild_id=interaction.guild.id, warning_type=modal.punishment_type.value)


    @discord.ui.button(
        label="Erase Punishments By Username",
        style=discord.ButtonStyle.danger,
        row=2
    )
    async def erase_username_punishments(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        modal = CustomModal(
            "Punishment Type",
            [
                (
                    'username',
                    discord.ui.TextInput(
                        label="ROBLOX Username",
                        placeholder="This is case-sensitive."
                    )
                )
            ],
            {
                'ephemeral': True
            }
        )

        await interaction.response.send_modal(modal)
        await modal.wait()
        sustained_interaction = modal.interaction

        try:
            roblox_client = roblox.Client()
            roblox_player = await roblox_client.get_user_by_username(modal.username.value)
        except roblox.UserNotFound:
            return await sustained_interaction.followup.send(
                embed=discord.Embed(
                    title="Not Found",
                    description="There are no punishments associated to this username.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )


        count = await self.bot.punishments.db.count_documents({
            "Guild": interaction.guild.id,
            "UserID": roblox_player.id
        })
        if count == 0:
            return await sustained_interaction.followup.send(
                embed=discord.Embed(
                    title="Not Found",
                    description="There are no punishments associated to this username.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        await sustained_interaction.followup.send(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased Punishments",
                description=f"All punishments of **{roblox_player.name}** have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        await self.bot.punishments.remove_warnings_by_spec(guild_id=interaction.guild.id,
                                                           user_id=roblox_player.id)


class ShiftLoggingManagement(discord.ui.View):
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=900.0)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Erase All Shifts",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def erase_all_shifts(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased All Shifts",
                description="All shifts have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        async for item in self.bot.shift_management.shifts.db.find({
            "Guild": interaction.guild.id
        }):
            await self.bot.shift_management.shifts.delete_by_id(item['_id'])


    @discord.ui.button(
        label="Erase Past Shifts",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def erase_past_shifts(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased Past Shifts",
                description="All past shifts have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        async for item in self.bot.shift_management.shifts.db.find({
            "Guild": interaction.guild.id,
            "EndEpoch": {'$ne': 0}
        }):
            await self.bot.shift_management.shifts.delete_by_id(item['_id'])


    @discord.ui.button(
        label="Erase Active Shifts",
        style=discord.ButtonStyle.danger,
        row=2
    )
    async def erase_active_shifts(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased Active Shifts",
                description="All active shifts have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        async for item in self.bot.shift_management.shifts.db.find({
            "Guild": interaction.guild.id,
            "EndEpoch": {'$eq': 0}
        }):
            await self.bot.shift_management.shifts.delete_by_id(item['_id'])

    @discord.ui.button(
        label="Erase Shifts By Type",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def erase_type_shifts(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        modal = CustomModal(
            "Shift Type",
            [
                (
                    'shift_type',
                    discord.ui.TextInput(
                        label="Shift Type",
                        placeholder="This is case-sensitive."
                    )
                )
            ],
            {
                'ephemeral': True
            }
        )

        await interaction.response.send_modal(modal)
        await modal.wait()
        sustained_interaction = modal.interaction

        count = await self.bot.shift_management.shifts.db.count_documents({
            "Guild": interaction.guild.id,
            "Type": modal.shift_type.value
        })
        if count == 0:
            return await sustained_interaction.followup.send(
                embed=discord.Embed(
                    title="Not Found",
                    description="There are no shifts with this type.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        await sustained_interaction.followup.send(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Erased Shifts",
                description=f"All shifts of **{modal.punishment_type.value}** have been deleted.",
                color=GREEN_COLOR
            ),
            ephemeral=True
        )

        async for item in self.bot.shift_management.shifts.db.find({
            "Guild": interaction.guild.id,
            "Type": modal.shift_type.value
        }):
            await self.bot.shift_management.shifts.delete_by_id(item)



class ManagementOptions(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.value = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Manage Types"
    )
    async def manage_types(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return
        await interaction.response.defer(thinking=False)
        self.value = "types"
        self.stop()

    @discord.ui.button(
        label="Modify Punishment"
    )
    async def modify_punishment(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return
        self.modal = CustomModal(
            "Modify Punishment",
            [
                (
                    "punishment_id",
                    discord.ui.TextInput(
                        label="Punishment ID"
                    )
                )
            ]
        )
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        if not self.modal.punishment_id.value:
            return

        self.value = "modify"
        self.stop()

class ManageTypesView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=900.0)
        self.bot = bot
        self.value = None
        self.user_id = user_id
        self.selected_for_deletion = None
        self.name_for_creation = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    @discord.ui.button(
        label="Create Punishment Type",
        style=discord.ButtonStyle.green
    )
    async def create_punishment_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return
        modal = CustomModal(
            "Create Type",
            [
                (
                    'punishment_type',
                    discord.ui.TextInput(
                        label="Punishment Type Name",
                        placeholder="Name of the punishment type you want to create."
                    )
                )
            ]
        )
        await interaction.response.send_modal(modal)
        await modal.wait()
        if not modal.punishment_type.value:
            return
        self.name_for_creation = modal.punishment_type.value
        self.value = "create"
        self.stop()


    @discord.ui.button(
        label="Delete Punishment Type",
        style=discord.ButtonStyle.danger
    )
    async def delete_punishment_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        val = await self.interaction_check(interaction)
        if not val:
            return

        modal = CustomModal(
            "Delete Type",
            [
                (
                    'punishment_type',
                    discord.ui.TextInput(
                        label="Punishment Type ID",
                        placeholder="ID of the punishment type you want to delete."
                    )
                )
            ]
        )
        await interaction.response.send_modal(modal)
        await modal.wait()
        if not modal.punishment_type.value:
            return
        self.selected_for_deletion = modal.punishment_type.value
        self.value = "delete"
        self.stop()



class PunishmentTypeCreator(discord.ui.View):
    def __init__(self, user_id: int, dataset: dict):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.restored_interaction = None
        self.dataset = dataset
        self.cancelled = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def refresh_ui(self, message: discord.Message):
        embed = discord.Embed(
            title="Punishment Type Creation",
            description=(
                f"<:replytop:1138257149705863209> **Name:** {self.dataset['name']}\n"
                f"<:replymiddle:1138257195121791046> **ID:** {self.dataset['id']}\n"
                f"<:replybottom:1138257250448855090> **Punishment Channel:** {'<#{}>'.format(self.dataset.get('channel', None)) if self.dataset.get('channel', None) is not None else 'Not set'}\n"
            ),
            color=BLANK_COLOR
        )

        if all(
                [
                    self.dataset.get('channel') is not None
                ]
        ):
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = False
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.label == "Finish":
                        item.disabled = True

        await message.edit(embed=embed, view=self)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Punishment Channel", row=1, max_values=1,
                       channel_types=[discord.ChannelType.text])
    async def channel_select(
            self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        await interaction.response.defer()

        self.dataset['channel'] = [i.id for i in select.values][0]
        try:
            await self.refresh_ui(interaction.message)
        except discord.NotFound:
            await self.refresh_ui(await self.restored_interaction.original_response())

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer(ephemeral=True)
        self.cancelled = True
        await interaction.followup.send(embed=discord.Embed(
            title="Successfully cancelled",
            description="This Punishment Type has not been created.",
            color=BLANK_COLOR
        ), ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.NotFound:
            await (await self.restored_interaction.original_response()).delete()
        self.stop()

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        disabled=True,
        row=3
    )
    async def finish(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.defer()
        self.cancelled = False
        self.stop()

class PunishmentModifier(discord.ui.View):
    def __init__(self, bot, user_id: int, dataset: dict):
        super().__init__(timeout=900.0)
        self.user_id = user_id
        self.restored_interaction = None
        self.bot = bot
        self.dataset = dataset
        self.root_dataset = dataset
        self.cancelled = None

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.user_id:
            return True
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=blank_color
            ), ephemeral=True)
            return False

    async def refresh_ui(self, message: discord.Message):
        embed = discord.Embed(
            title="Punishment Modification",
            description=(
                f"<:replytop:1138257149705863209> **Username:** {self.dataset['Username']}\n"
                f"<:replymiddle:1138257195121791046> **Type:** {self.dataset['Type']}\n"
                f"<:replymiddle:1138257195121791046> **ID:** {self.dataset['Snowflake']}\n"
                f"<:replybottom:1138257250448855090> **Reason:** {self.dataset['Reason']}"
            ),
            color=BLANK_COLOR
        )

        await message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="Change Type",
        row=0
    )
    async def change_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomModal(
            "Edit Punishment Type",
            [
                (
                    "punishment_type",
                    discord.ui.TextInput(
                        label="Punishment Type Name"
                    )
                )
            ]
        )

        await interaction.response.send_modal(modal)
        await modal.wait()
        try:
            chosen_type = modal.punishment_type.value
        except ValueError:
            return

        punishment_types = (await self.bot.punishment_types.get_punishment_types(interaction.guild.id)) or {'types': []}
        chosen_identifier = None
        for item in punishment_types['types']:
            if isinstance(item, str) and item.lower() == chosen_type.lower():
                chosen_identifier = item
            elif isinstance(item, dict) and item['name'].lower() == chosen_type.lower():
                chosen_identifier = item['name']


        if not chosen_identifier:
            return await modal.interaction.followup.send(
                embed=discord.Embed(
                    title="Could not find type",
                    description="This punishment type does not exist.",
                    color=BLANK_COLOR
                )
            )


        self.dataset['Type'] = chosen_identifier
        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="Edit Reason",
        row=0
    )
    async def edit_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomModal(
            "Edit Reason",
            [
                (
                    "reason",
                    discord.ui.TextInput(
                        label="Reason"
                    )
                )
            ]
        )

        await interaction.response.send_modal(modal)
        await modal.wait()

        self.dataset['Reason'] = modal.reason.value
        await self.refresh_ui(interaction.message)

    @discord.ui.button(
        label="Delete Punishment",
        row=0
    )
    async def delete_punishment(self, interaction: discord.Interaction, button: discord.ui.Button):

        punishment = await self.bot.punishments.db.find_one(self.root_dataset)
        if punishment:
            await self.bot.punishments.remove_warnings_by_snowflake(punishment['Snowflake'])
            await interaction.message.delete()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Punishment Deleted",
                    color=GREEN_COLOR,
                    description="This punishment has been deleted successfully!"
                )
            )


    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer(ephemeral=True)
        self.cancelled = True
        await interaction.followup.send(embed=discord.Embed(
            title="Successfully cancelled",
            description="This punishment has not been modified.",
            color=BLANK_COLOR
        ), ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.NotFound:
            await (await self.restored_interaction.original_response()).delete()
        self.stop()

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.green,
        disabled=False,
        row=3
    )
    async def finish(self, interaction: discord.Interaction, _: discord.Button):
        punishment = await self.bot.punishments.find_by_id(self.dataset['_id'])
        if punishment:
            await self.bot.punishments.upsert(self.dataset)
        self.cancelled = False
        self.stop()