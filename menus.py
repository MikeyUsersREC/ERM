import typing

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
        embed.set_footer(
            text=f'Staff Logging Module - Accepted by {interaction.user.name}#{interaction.user.discriminator}')

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
                        return await int_invis_embed(interaction, "User could not be found in the server.",
                                                     ephemeral=True)
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



class AddCustomCommand(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
        self.information = {}
        self.user_id = user_id
        self.view: typing.Union[MessageCustomisation, None] = None

    @discord.ui.button(label='Create a custom command', style=discord.ButtonStyle.secondary, emoji="<:Resume:1035269012445216858>")
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

class MessageCustomisation(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value: typing.Union[str, None] = None
        self.modal: typing.Union[discord.ui.Modal, None] = None
        self.newView: typing.Union[EmbedCustomisation, None] = None
        self.msg = None
        self.user_id = user_id

    @discord.ui.button(label='Set Message', style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
    async def content(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetContent()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            await interaction.message.edit(content=modal.name.value)

    @discord.ui.button(label='Add Embed', style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
    async def addembed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            if len(interaction.message.embeds) > 0:
                return await int_invis_embed(interaction, "You can only have one embed per custom command. This is a temporary restriction and will be removed soon.", ephemeral=True)

            newView = EmbedCustomisation(interaction.user.id, self)
            self.newView = newView
            await interaction.message.edit(view=newView, embed=discord.Embed(colour=0x2E3136, description="\u200b"))
            await int_invis_embed(interaction, 'You can now customise your embed. Once you are done, click the "Finish" button to save your embed.', ephemeral=True)

    @discord.ui.button(label='✅ Finish', style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            self.msg = interaction.message
            self.newView = self
            self.value = "finish"
            await int_invis_embed(interaction, 'Your custom command has been created. You can now use it in your server by using `/custom run <name> [channel]`!', ephemeral=True)
            await interaction.message.delete()
            self.stop()



class EmbedCustomisation(discord.ui.View):
    def __init__(self, user_id, view):
        super().__init__()
        self.value: typing.Union[str, None] = None
        self.modal: typing.Union[discord.ui.Modal, None] = None
        self.msg = None
        self.user_id = user_id
        self.parent_view = view

    @discord.ui.button(label='Set Message', style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
    async def content(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetContent()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal

    @discord.ui.button(label='Remove Embed', style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
    async def remove_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            if len(interaction.message.embeds) > 0:
                await interaction.message.edit(view=self.parent_view, embed=None)
                return await int_invis_embed(interaction, 'Embed removed.', ephemeral=True)

            await interaction.edit_original_response(embed=discord.Embed())



    @discord.ui.button(label='✅ Finish', style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            for item in self.children:
                item.disabled = True
            self.msg = interaction.message
            await interaction.message.edit(view=self)
            self.value = "finish"
            await int_invis_embed(interaction, 'Your custom command has been created. You can now use it in your server by using `/custom run <name> [channel]`!', ephemeral=True)
            await interaction.message.delete()
            self.parent_view.stop()
            self.stop()

    @discord.ui.button(label="Set Title", row=1, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
    async def set_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetTitle()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.title = modal.name.value
            await interaction.message.edit(embed=embed)

    @discord.ui.button(label="Set Description", row=1, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
    async def set_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            modal = SetDescription()
            await interaction.response.send_modal(modal)
            await modal.wait()
            self.modal = modal
            embed = interaction.message.embeds[0]
            embed.description = modal.name.value
            await interaction.message.edit(embed=embed)

    @discord.ui.button(label="Set Embed Colour", row=1, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
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
                    return await int_invis_embed(interaction, "Invalid colour. Please try again.\n*Example: #ff0000*", ephemeral=True)
            await interaction.message.edit(embed=embed)

    @discord.ui.button(label="Set Thumbnail", row=2, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
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

    @discord.ui.button(label="Set Image", row=2, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
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

    @discord.ui.button(label="Add Field", row=3, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
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

    @discord.ui.button(label="Set Footer", row=3, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
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

    @discord.ui.button(label="Set Author", row=3, style=discord.ButtonStyle.secondary, emoji="<:ArrowRight:1035003246445596774>")
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
class RemoveReminder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
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
class RemoveCustomCommand(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
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


class RequestReason(discord.ui.Modal, title="Edit Reason"):
    name = discord.ui.TextInput(label='Reason')

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class SetContent(discord.ui.Modal, title="Set Message Content"):
    name = discord.ui.TextInput(label='Content', placeholder="Content of the message", max_length=2000, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class SetTitle(discord.ui.Modal, title="Set Embed Title"):
    name = discord.ui.TextInput(label='Title', placeholder="Title of the embed", style=discord.TextStyle.short)
    url = discord.ui.TextInput(label="Title URL", placeholder="URL of the title", style=discord.TextStyle.short, required=False)
    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class CustomCommandSettings(discord.ui.Modal, title="Custom Command Settings"):
    name = discord.ui.TextInput(label='Custom Command Name', placeholder="e.g. ssu", style=discord.TextStyle.short, max_length=20)
    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class SetDescription(discord.ui.Modal, title="Set Embed Title"):
    name = discord.ui.TextInput(label='Title', placeholder="Description of the embed", style=discord.TextStyle.long, max_length=2000)

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
    inline = discord.ui.TextInput(label='Inline?', placeholder="Yes/No", default="Yes", style=discord.TextStyle.short, required=False)


    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class SetFooter(discord.ui.Modal, title="Set Footer"):
    name = discord.ui.TextInput(label='Footer Text', placeholder="Footer Text", style=discord.TextStyle.short)
    icon = discord.ui.TextInput(label='Footer Icon URL', placeholder="Footer Icon URL", default="", style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await int_invis_embed(interaction, "Your response has been submitted.", ephemeral=True)
        self.stop()

class SetAuthor(discord.ui.Modal, title="Set Author"):
    name = discord.ui.TextInput(label='Author Name', placeholder="Author Name", style=discord.TextStyle.short)
    url = discord.ui.TextInput(label='Author URL', placeholder="Author URL", default="", style=discord.TextStyle.short, required=False)
    icon = discord.ui.TextInput(label='Author Icon URL', placeholder="Author Icon URL", default="", style=discord.TextStyle.short, required=False)

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
    def __init__(self, user_id):
        self.user_id: int = user_id

        options = [
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
        super().__init__(placeholder='Select a warning type', min_values=1, max_values=1, options=options)

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


class EditWarningSelect(discord.ui.Select):

    def __init__(self, user_id: int):
        self.user_id: int = user_id

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
                description="Change the punishment type to a higher or lower severity"
            ),
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
                view = WarningDropdownMenu(interaction.user.id)
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
                await interaction.response.edit_original_response(view=self.view)
                self.view.stop()
            else:
                await int_invis_embed(interaction, "You have not picked an option.")

class EditWarning(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__()
        self.value: typing.Union[None, str] = None
        self.bot: typing.Union[discord.ext.commands.Bot, discord.ext.commands.AutoShardedBot] = bot
        self.user_id: int = user_id
        self.modal: typing.Union[None, discord.ui.Modal] = None
        self.further_value: typing.Union[None, str] = None

        self.add_item(EditWarningSelect(user_id))


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

class CustomSelectMenu(discord.ui.View):
    def __init__(self, user_id, options: list):
        super().__init__()
        self.value = None
        self.user_id = user_id

        self.add_item(CustomDropdown(self.user_id, options))


class WarningDropdownMenu(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
        self.user_id = user_id

        self.add_item(ChangeWarningType(self.user_id))


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


class CheckMark(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.value = None
        self.user_id = user_id

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(emoji="✅", style=discord.ButtonStyle.gray)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(emoji='❎', style=discord.ButtonStyle.gray)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        self.value = False
        self.stop()
