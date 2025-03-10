import datetime
import discord
import pytz
from discord.ext import commands
from erm import is_management
from menus import (
    YesNoMenu,
    AcknowledgeMenu,
    YesNoExpandedMenu,
    CustomModalView,
    CustomSelectMenu,
    MultiSelectMenu,
    RoleSelect,
    ExpandedRoleSelect,
    MessageCustomisation,
    EmbedCustomisation,
    ChannelSelect,
)

successEmoji = "<:ERMCheck:1111089850720976906>"
pendingEmoji = "<:ERMPending:1111097561588183121>"
errorEmoji = "<:ERMClose:1111101633389146223>"
embedColour = 0xED4348


class StaffConduct(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_settings(self, ctx: commands.Context):
        error_text = "<:ERMClose:1111101633389146223> **{},** this server isn't setup with ERM! Please run `/setup` to setup the bot before trying to manage infractions".format(
            ctx.author.name
        )
        guild_settings = await self.bot.settings.find_by_id(ctx.guild.id)
        # print(guild_settings)
        # print(guild_settings.get('staff_conduct'))
        if not guild_settings:
            await ctx.reply(error_text)
            return -1

        if guild_settings.get("staff_conduct") is not None:
            return 1
        else:
            return 0

    @commands.hybrid_group(
        name="infraction",
        description="Manage infractions with ease!",
        extras={"category": "Staff Conduct"},
    )
    @is_management()
    async def infraction(self, ctx: commands.Context):
        pass

    @infraction.command(
        name="manage",
        description="Manage staff infractions, staff conduct, and custom integrations!",
        extras={"category": "Staff Conduct"},
    )
    @is_management()
    async def manage(self, ctx: commands.Context):
        bot = self.bot
        guild_settings = await bot.settings.find_by_id(ctx.guild.id)
        result = await self.check_settings(ctx)
        if result == -1:
            return
        first_time_setup = bool(not result)

        if first_time_setup:
            view = YesNoExpandedMenu(ctx.author.id)
            message = await ctx.reply(
                f"{pendingEmoji} **{ctx.author.name},** it looks like your server hasn't setup **Staff Conduct**! Do you want to run the **First-time Setup** wizard?",
                view=view,
            )
            timeout = await view.wait()
            if timeout:
                return
            if not view.value:
                await message.edit(
                    content=f"{errorEmoji} **{ctx.author.name},** I have cancelled the setup wizard for **Staff Conduct.**",
                    view=None,
                )
                return

            embed = discord.Embed(
                title="<:ERMAlert:1113237478892130324> Information", color=embedColour
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/1113210855891423302.webp?size=96&quality=lossless"
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> What is Staff Conduct?",
                value=">>> Staff Conduct is a module within ERM which allows for infractions on your Staff team. Not only does it allow for manual punishments and infractions to others to be expanded and customised, it also allows for automatic punishments for those that don't meet activity requirements, integrating with other ERM modules.",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> How does this module work?",
                value=">>> For manual punishment assignment, you make your own Infraction Types, as dictated throughout this setup wizard. You can then infract staff members by using `/infract`, which will assign that Infraction Type to the staff individual. You will be able to see all infractions that individual has received, as well as any notes or changes that have been made over the course of their staff career.",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> If I have a Strike 1/2/3 system, do I have them as separate types?",
                value=">>> In the case where you have a counting infraction system, you can tell ERM to count the strikes automatically! It will then take the according actions that correspond with that infraction amount.",
                inline=False,
            )
            embed.set_footer(
                text="This module is in beta, and bugs are to be expected. If you notice a problem with this module, report it via our Support server."
            )
            embed.timestamp = datetime.datetime.now()
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)

            view = AcknowledgeMenu(
                ctx.author.id, "Read the information in full before acknowledging."
            )
            await message.edit(
                content=f"{pendingEmoji} **{ctx.author.name},** please read all the information below before continuing.",
                embed=embed,
                view=view,
            )
            timeout = await view.wait()
            if timeout or not view.value:
                return

            await message.edit(
                content=f"{pendingEmoji} **{ctx.author.name},** let's begin!",
                embed=None,
                view=(
                    view := CustomModalView(
                        ctx.author.id,
                        "Add an Infraction Type",
                        "Add Infraction Type",
                        [
                            (
                                "type_name",
                                discord.ui.TextInput(
                                    placeholder="e.g. Strike, Termination, Suspension, Blacklist",
                                    label="Name of Infraction Type",
                                ),
                            )
                        ],
                    )
                ),
            )
            timeout = await view.wait()
            if timeout:
                return

            try:
                infraction_type_name = view.modal.type_name.value
            except AttributeError:
                return

            await message.edit(
                content=f"{pendingEmoji} **{ctx.author.name},** what actions do you want to add to **{infraction_type_name}**?",
                view=(
                    view := CustomSelectMenu(
                        ctx.author.id,
                        [
                            discord.SelectOption(
                                label="Add Role",
                                description='Add a role, such as a "Strike" role to the individual',
                                emoji="<:ERMAdd:1113207792854106173>",
                                value="add_role",
                            ),
                            discord.SelectOption(
                                label="Remove Role",
                                description='Remove an individual role, such as "Trained", from an individual.',
                                emoji="<:ERMRemove:1113207777662345387>",
                                value="remove_role",
                            ),
                            discord.SelectOption(
                                label="Remove Staff Roles",
                                description="Remove all designated staff roles from an individual.",
                                emoji="<:ERMWarn:1113236697702989905>",
                                value="remove_staff_roles",
                            ),
                            discord.SelectOption(
                                label="Send Direct Message",
                                description="Send a Direct Message to the individual involved.",
                                emoji="<:ERMUser:1111098647485108315>",
                                value="send_dm",
                            ),
                            discord.SelectOption(
                                label="Send Message in Channel",
                                description="Send a Custom Message in a Channel",
                                emoji="<:ERMLog:1113210855891423302>",
                                value="send_message",
                            ),
                            discord.SelectOption(
                                label="Send Escalation Request",
                                description="Request for a Management member to complete extra actions",
                                emoji="<:ERMHelp:1111318459305951262>",
                                value="send_escalation",
                            ),
                        ],
                        limit=6,
                    )
                ),
            )

            await view.wait()

            value: list | None = None
            if isinstance(view.value, str):
                value = [view.value]
            elif isinstance(view.value, list):
                value = view.value
            # WE NEED TO MAKE THESE MESSAGES MORE NOTICABLE FOR WHICH YOU PICKED
            # noticeable* 🤓
            for item in value:
                if item == "add_role":  # Add to Database
                    await message.edit(
                        content=f"{pendingEmoji} **{ctx.author.name},** what roles do you wish to be assigned when \
                    a user receives a **{infraction_type_name}**?",
                        view=(view := ExpandedRoleSelect(ctx.author.id, limit=25)),
                    )
                    await view.wait()
                    addRoleList = view.value
                elif item == "remove_role":  # Add to Database
                    await message.edit(
                        content=f"{pendingEmoji} **{ctx.author.name},** what roles do you wish to be removed when \
a user receives a **{infraction_type_name}**?",
                        view=(view := ExpandedRoleSelect(ctx.author.id, limit=25)),
                    )
                    await view.wait()
                    removeRoleList = view.value
                elif item == "remove_staff_roles":  # Add to Database
                    await message.edit(
                        content=f"{pendingEmoji} **{ctx.author.name},** what staff roles do you wish to be affected \
when a user receives a **{infraction_type_name}**?",
                        view=(view := ExpandedRoleSelect(ctx.author.id, limit=25)),
                    )
                    await view.wait()
                    staffRoleList = view.value
                elif item == "send_dm":  # Add to Database
                    constant_msg_data = None
                    while True:
                        if not constant_msg_data:
                            view = MessageCustomisation(
                                ctx.author.id, persist=True, external=True
                            )
                        else:
                            if constant_msg_data.get("embeds"):
                                view = EmbedCustomisation(
                                    ctx.author.id,
                                    MessageCustomisation(
                                        ctx.author.id,
                                        {"message": constant_msg_data},
                                        persist=True,
                                        external=True,
                                    ),
                                    external=True,
                                )
                            else:
                                view = MessageCustomisation(
                                    ctx.author.id,
                                    {"message": constant_msg_data},
                                    persist=True,
                                    external=True,
                                )

                        if not constant_msg_data:
                            await message.edit(
                                content=f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send \
a user upon receiving a **{infraction_type_name}**.",
                                view=view,
                            )
                        else:
                            await message.edit(
                                content=(
                                    f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send \
a user upon receiving a **{infraction_type_name}**."
                                    if not message_data.get("content")
                                    else message_data.get("content")
                                ),
                                embeds=[
                                    discord.Embed.from_dict(embed)
                                    for embed in message_data.get("embeds")
                                ],
                                view=view,
                            )
                        await view.wait()
                        updated_message = await ctx.channel.fetch_message(message.id)
                        message_data = {
                            "content": (
                                updated_message.content
                                if updated_message.content
                                != f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send a user upon receiving a **{infraction_type_name}**."
                                else ""
                            ),
                            "embeds": [i.to_dict() for i in updated_message.embeds],
                        }
                        yesNoValue = YesNoMenu(ctx.author.id)
                        await message.edit(
                            content=f"{pendingEmoji} **{ctx.author.name},** please confirm below that you wish to use the content shown below.\n\n{message_data['content']}",
                            embeds=[
                                discord.Embed.from_dict(i)
                                for i in message_data["embeds"]
                            ],
                            view=yesNoValue,
                        )
                        await yesNoValue.wait()
                        if yesNoValue.value:
                            break
                        elif not yesNoValue.value:
                            constant_msg_data = message_data
                elif item == "send_message":  # Add to Database
                    # Get Channel(s) to Send Message To
                    await message.edit(
                        content=f"{pendingEmoji} **{ctx.author.name},** please select the channel(s) you wish to send a message to upon a user receiving a **{infraction_type_name}**.",
                        view=(view := ChannelSelect(ctx.author.id, limit=5)),
                    )
                    await view.wait()

                    # Get Custom Message
                    view = MessageCustomisation(
                        ctx.author.id, persist=True, external=True
                    )
                    await message.edit(content=None, view=view)
                    await view.wait()
                elif item == "send_escalation":  # Add to Database
                    await message.edit(
                        content=f"{pendingEmoji} **{ctx.author.name},** please select the channel you wish to send an escalation request to upon a user recieving a **{infraction_type_name}**.",
                        view=(view := ChannelSelect(ctx.author.id, limit=1)),
                    )
                    await view.wait()
                    # print(view.value)
                    await message.edit(
                        content=f"{pendingEmoji} **{ctx.author.name},** should the member responsible for issuing the infraction that triggers an escalation request also have the authority to approve the escalation request? **{infraction_type_name}**.",
                        view=(view := YesNoMenu(ctx.author.id)),
                    )
                    # print(view.value)
            else:
                await message.edit(
                    content=f"{successEmoji} **{infraction_type_name}** has been successfully submitted!",
                    view=None,
                    embed=None,
                )

        else:
            guild_settings["staff_conduct"] = None
            await self.bot.settings.update_by_id(guild_settings)
            await ctx.reply(
                f"{successEmoji} **{ctx.author.name},** I deleted your Staff Conduct configuration."
            )


async def setup(bot):
    await bot.add_cog(StaffConduct(bot))
