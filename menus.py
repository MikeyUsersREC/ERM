import discord
from utils.utils import int_invis_embed

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
                label="Verification",
                value="verification",
                emoji="<:SettingIcon:1035353776460152892>",
                description="Currently in active development"
            ),
            discord.SelectOption(
                label="Customisation",
                value="customisation",
                emoji="<:FlagIcon:1035258525955395664>",
                description="Colours, branding, prefix, to customise to your liking"
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


class CustomDropdown(discord.ui.Select):
    def __init__(self, user_id, options: list, limit = 1):
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


class SettingsSelectMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
        self.user_id = user_id

        self.add_item(Dropdown(self.user_id))


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
        await interaction.edit_original_response(view=self)
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
        await interaction.edit_original_response(view=self)
        self.stop()

class EnableDisableMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Enable', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
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
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = False
        await interaction.edit_original_response(view=self)
        self.stop()


class ShiftModify(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Add time (+)', style=discord.ButtonStyle.green)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
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
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "remove"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label='End shift', style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "end"
        await interaction.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(label='Void shift', style=discord.ButtonStyle.danger)
    async def void(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        self.value = "void"
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
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
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
            if settings:
                if 'privacy_mode' in settings['staff_management'].keys():
                    if settings['staff_management']['privacy_mode'] == True:
                        mentionable = "Management"
                    else:
                        mentionable = interaction.user.mention
                else:
                    mentionable = interaction.user.mention
            else:
                mentionable = interaction.user.mention
            success = discord.Embed(
                title=f"<:CheckIcon:1035018951043842088> {s_loa['type']} Accepted",
                description=f"<:ArrowRightW:1035023450592514048> {mentionable} has accepted your {s_loa['type']} request.",
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
        embed.title = "<:CheckIcon:1035018951043842088> LOA Accepted"
        embed.colour = 0x71c15f
        embed.set_footer(text=f'Staff Logging Module - Accepted by {interaction.user.name}#{interaction.user.discriminator}')

        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Deny', style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            for item in self.children:
                if item.label == button.label:
                    item.label = "Denied"
                item.disabled = True
            await interaction.edit_original_response(view=self)

            s_loa = None
            for loa in await self.bot.loas.get_all():
                if loa['message_id'] == interaction.message.id and loa['guild_id'] == interaction.guild.id:
                    s_loa = loa
                if s_loa != None:
                    s_loa['denied'] = True

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
                    if settings:
                        if 'privacy_mode' in settings['staff_management'].keys():
                            if settings['staff_management']['privacy_mode'] == True:
                                mentionable = "Management"
                            else:
                                mentionable = interaction.user.mention
                        else:
                            mentionable = interaction.user.mention
                    else:
                        mentionable = interaction.user.mention
                    success = discord.Embed(
                        title=f"<:ErrorIcon:1035000018165321808> {s_loa['type']} Denied",
                        description=f"<:ArrowRightW:1035023450592514048>{mentionable} has denied your {s_loa['type']} request.",
                        color=0xff3c3c
                    )
                    await user.send(embed=success)
                    await self.bot.loas.update_by_id(s_loa)

            self.value = True
            self.stop()


class AddReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
    @discord.ui.button(label='Create a reminder', style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)
        self.value = "create"
        self.stop()

class RemoveReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
    @discord.ui.button(label="Delete a reminder", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)
        self.value = "delete"
        self.stop()

class RemoveWarning(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__()
        self.value = None
        self.bot = bot
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
            return
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


class RemoveBOLO(discord.ui.View):
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
            return
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

# class RemoveBOLO(discord.ui.View):
#     def __init__(self, user_id):
#         super().__init__()
#         self.value = None
#         self.user_id = user_id
#
#     # When the confirm button is pressed, set the inner value to `True` and
#     # stop the View from listening to more input.
#     # We also send the user an ephemeral message that we're confirming their choice.
#     @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
#     async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
#         if interaction.user.id != self.user_id:
#             return
#         await interaction.response.defer()
#         for item in self.children:
#             item.disabled = True
#         self.value = True
#
#         success = discord.Embed(
#             title="<:CheckIcon:1035018951043842088> Removed BOLO",
#             description="<:ArrowRightW:1035023450592514048>I've successfully removed the BOLO from the user.",
#             color=0x71c15f
#         )
#
#         await interaction.edit_original_response(embed=success, view=self)
#         self.stop()
#
#     # This one is similar to the confirmation button except sets the inner value to `False`
#     @discord.ui.button(label='No', style=discord.ButtonStyle.danger)
#     async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
#         if interaction.user.id != self.user_id:
#             return
#         await interaction.response.defer()
#         for item in self.children:
#             item.disabled = True
#         self.value = False
#
#         success = discord.Embed(
#             title="<:ErrorIcon:1035000018165321808> Cancelled",
#             description="<:ArrowRightW:1035023450592514048>The BOLO has not been removed from the user.",
#             color=0xff3c3c
#         )
#
#         await interaction.edit_original_response(embed=success, view=self)
#         self.stop()

class CustomSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__()
        self.value = None
        self.user_id = user_id

        self.add_item(CustomDropdown(self.user_id, options))

class MultiSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__()
        self.value = None
        self.user_id = user_id

        self.add_item(MultiDropdown(self.user_id, options))


class RoleSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__()
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

class ChannelSelect(discord.ui.View):
    def __init__(self, user_id, **kwargs):
        super().__init__()
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
