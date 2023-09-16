import datetime
import discord
import pytz
from discord.ext import commands
from erm import is_management
from menus import YesNoMenu, AcknowledgeMenu, YesNoExpandedMenu, CustomModalView, CustomSelectMenu, MultiSelectMenu, \
    RoleSelect, ExpandedRoleSelect, MessageCustomisation, EmbedCustomisation, ChannelSelect

successEmoji = "<:ERMCheck:1111089850720976906>"
pendingEmoji = "<:ERMPending:1111097561588183121>"
errorEmoji = "<:ERMClose:1111101633389146223>"
embedColour = 0xED4348


class StaffConduct(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_settings(self, ctx: commands.Context):
        error_text = '<:ERMClose:1111101633389146223> **{},** this server isn\'t setup with ERM! Please run `/setup` to setup the bot before trying to manage infractions'.format(ctx.author.name)
        guild_settings = await self.bot.settings.find_by_id(ctx.guild.id)
        # print(guild_settings)
        # print(guild_settings.get('staff_conduct'))
        if not guild_settings:
            await ctx.reply(error_text)
            return -1

        if guild_settings.get('staff_conduct') is not None:
            return 1
        else:
            return 0


    @commands.hybrid_group(name="infraction", description="Manage infractions with ease!", extras={
        "category": "Staff Conduct"
    })
    @is_management()
    async def infraction(self, ctx: commands.Context):
        pass

    @infraction.command(
        name="manage",
        description="Manage staff infractions, staff conduct, and custom integrations!",
        extras={"category": "Staff Conduct"}
    )
    @is_management()
    async def manage(self, ctx: commands.Context):
        bot = self.bot
        Data = await bot.staff_conduct.find_by_id(ctx.guild.id)
        if Data is None:
             Data = {"_id": ctx.guild.id, "conduct": []}
        send_dmContent = {}
        send_dmContent["content"] = None
        send_dmContent["embeds"] = None
        send_messageContent = {}
        send_messageContent["content"] = None
        send_messageContent["embeds"] = None

        choiceValue = None

        add_role_status = False
        remove_role_status = False
        remove_staff_roles_status = False
        send_dm_status = False
        send_message_status = False
        send_escalation_status = False

        addroleList = None
        removeroleList = None
        staffroleList = None
        send_messageCID = None
        send_escalationCID = None
        self_approval_status = None

        if not Data["conduct"]:
            view = YesNoExpandedMenu(ctx.author.id)
            message = await ctx.reply(f"{pendingEmoji} **{ctx.author.name},** it looks like your server hasn't setup **Staff Conduct**! Do you want to run the **First-time Setup** wizard?", view=view)
            timeout = await view.wait()
            if timeout:
                return
            if not view.value:
                await message.edit(content=f"{errorEmoji} **{ctx.author.name},** I have cancelled the setup wizard for **Staff Conduct.**", view=None)
                return

            embed = discord.Embed(title="<:ERMAlert:1113237478892130324> Information", color=embedColour)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1113210855891423302.webp?size=96&quality=lossless")
            embed.add_field(
                name="<:ERMList:1111099396990435428> What is Staff Conduct?",
                value=">>> Staff Conduct is a module within ERM which allows for infractions on your Staff team. Not only does it allow for manual punishments and infractions to others to be expanded and customised, it also allows for automatic punishments for those that don't meet activity requirements, integrating with other ERM modules.",
                inline=False
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> How does this module work?",
                value=">>> For manual punishment assignment, you make your own Infraction Types, as dictated throughout this setup wizard. You can then infract staff members by using `/infract`, which will assign that Infraction Type to the staff individual. You will be able to see all infractions that individual has received, as well as any notes or changes that have been made over the course of their staff career.",
                inline=False
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> If I have a Strike 1/2/3 system, do I have them as separate types?",
                value=">>> In the case where you have a counting infraction system, you can tell ERM to count the strikes automatically! It will then take the according actions that correspond with that infraction amount.",
                inline=False
            )
            embed.set_footer(
                text="This module is in beta, and bugs are to be expected. If you notice a problem with this module, report it via our Support server."
            )
            embed.timestamp = datetime.datetime.now()
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar
            )


            view = AcknowledgeMenu(ctx.author.id, "Read the information in full before acknowledging.")
            await message.edit(
                content=f"{pendingEmoji} **{ctx.author.name},** please read all the information below before continuing.",
                embed=embed,
                view=view
            )
            timeout = await view.wait()
            if timeout or not view.value:
                return

            choiceValue = "create_infraction_type"

        if Data["conduct"]:
            message = await ctx.reply(
                f"{pendingEmoji} **{ctx.author.name},** what would you like to do?",
                view=(view := CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Create",
                            description="Create an Infraction Type",
                            emoji="<:ERMAdd:1113207792854106173>",
                            value="create_infraction_type"
                        ),
                        discord.SelectOption(
                            label="List",
                            description="List all of the Infraction Types",
                            emoji="<:ERMList:1111099396990435428>",
                            value="list_infraction_types"
                        ),
                        discord.SelectOption(
                            label="Edit",
                            description="Edit an Infraction Type",
                            emoji="<:ERMMisc:1113215605424795648>",
                            value="edit_infraction_type"
                        ),
                        discord.SelectOption(
                            label="Delete",
                            description="Delete an Infraction Type",
                            emoji="<:ERMTrash:1111100349244264508>",
                            value="delete_infraction_type"
                        ),
                    ]
                ))
            )
            timeout = await view.wait()
            if timeout:
                return
            choiceValue = view.value


        match choiceValue:
            case "create_infraction_type":
                await message.edit(
                    content=f"{pendingEmoji} **{ctx.author.name},** let's create an Infraction Type!",
                    embed=None,
                    view=(view := CustomModalView(
                        ctx.author.id,
                        "Add an Infraction Type",
                        "Add Infraction Type",
                        [
                            (
                                "type_name",
                                discord.ui.TextInput(
                                    placeholder="e.g. Strike, Termination, Suspension, Blacklist",
                                    label="Name of Infraction Type"
                                )
                            )
                        ]
                    ))
                )
                await view.wait()
                try:
                    infraction_type_name = view.modal.type_name.value
                except:
                    return

                await message.edit(
                    content=f"{pendingEmoji} **{ctx.author.name},** what actions do you want to add to **{infraction_type_name}**?",
                    view=(view := CustomSelectMenu(ctx.author.id,
                                                   [
                                                       discord.SelectOption(
                                                           label="Add Role",
                                                           description="Add a role, such as a \"Strike\" role to the individual",
                                                           emoji="<:ERMAdd:1113207792854106173>",
                                                           value="add_role"
                                                       ),
                                                       discord.SelectOption(
                                                           label="Remove Role",
                                                           description="Remove an individual role, such as \"Trained\", from an individual.",
                                                           emoji="<:ERMRemove:1113207777662345387>",
                                                           value="remove_role"
                                                       ),
                                                       discord.SelectOption(
                                                           label="Remove Staff Roles",
                                                           description="Remove all designated staff roles from an individual.",
                                                           emoji="<:ERMWarn:1113236697702989905>",
                                                           value="remove_staff_roles"
                                                       ),
                                                       discord.SelectOption(
                                                           label="Send Direct Message",
                                                           description="Send a Direct Message to the individual involved.",
                                                           emoji="<:ERMUser:1111098647485108315>",
                                                           value="send_dm"
                                                       ),
                                                       discord.SelectOption(
                                                           label="Send Message in Channel",
                                                           description="Send a Custom Message in a Channel",
                                                           emoji="<:ERMLog:1113210855891423302>",
                                                           value="send_message"
                                                       ),
                                                       discord.SelectOption(
                                                           label="Send Escalation Request",
                                                           description="Request for a Management member to complete extra actions",
                                                           emoji="<:ERMHelp:1111318459305951262>",
                                                           value="send_escalation"
                                                       )
                                                   ], limit=6))

                )

                await view.wait()

                value: list | None = None
                if isinstance(view.value, str):
                    value = [view.value]
                elif isinstance(view.value, list):
                    value = view.value
                for item in value:
                    match item:
                        case "add_role":
                            add_role_status = True
                            addroleList = None
                            while not addroleList:
                                await message.edit(
                                    content=f"{pendingEmoji} **{ctx.author.name},** which roles do you want to be given when a user is given the **{infraction_type_name}**?",
                                    view=(view := ExpandedRoleSelect(ctx.author.id, limit=25))
                                )
                                await view.wait()
                                addroleList = [str(role.id) for role in view.value]
                                await message.edit(view=None, embed=None)

                        case "remove_role":
                            remove_role_status = True
                            removeroleList = None
                            while not removeroleList:
                                await message.edit(
                                    content=f"{pendingEmoji} **{ctx.author.name},** what roles should I remove when a user is given the **{infraction_type_name}** type?",

                                    view=(view := ExpandedRoleSelect(ctx.author.id, limit=25))
                                )
                                await view.wait()
                                removeroleList = [str(role.id) for role in view.value]
                                await message.edit(view=None, embed=None)
                        case "remove_staff_roles":
                            remove_staff_roles_status = True
                            staffroleList = None
                            while not staffroleList:
                                await message.edit(
                                    content=f"{pendingEmoji} **{ctx.author.name},** please add __all__ staff roles. These roles will be removed from a staff member when **{infraction_type_name}** has the **Remove Staff Role** action assigned to it?",
                                    view=(view := ExpandedRoleSelect(ctx.author.id, limit=25))
                                )
                                await view.wait()
                                staffroleList = [str(role.id) for role in view.value]
                                await message.edit(view=None)
                        case "send_dm":
                            send_dm_status = True

                            view = MessageCustomisation(ctx.author.id, persist=True, external=True)
                            await message.edit(
                                content=f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send to a user upon receiving a **{infraction_type_name}**.",
                                view=view
                            )
                            await view.wait()
                            await message.edit(view=None, embed=None)
                            updated_message = await ctx.channel.fetch_message(message.id)

                            send_dmContent = {
                                "content": updated_message.content if updated_message.content != f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send to a user upon receiving a **{infraction_type_name}**." else "",
                                "embeds": [i.to_dict() for i in updated_message.embeds]
                            }
                            await message.edit(view=None, embed=None)
                        case "send_message":
                            send_message_status = True

                            await message.edit(
                                content=f"{pendingEmoji} **{ctx.author.name},** please select the channel(s) you wish to send a message to upon a user receiving a **{infraction_type_name}**.",
                                view=(view := ChannelSelect(ctx.author.id, limit=5))
                            )
                            await view.wait()
                            await message.edit(view=None, embed=None)
                            send_messageCID = [str(channel.id) for channel in view.value]
                            view = MessageCustomisation(ctx.author.id, persist=True, external=True)
                            await message.edit(
                                content=f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send upon a user receiving a **{infraction_type_name}**.",
                                view=view
                            )
                            await view.wait()
                            await message.edit(view=None, embed=None)
                            updated_message = await ctx.channel.fetch_message(message.id)

                            send_messageContent = {
                                "content": updated_message.content if updated_message.content != f"{pendingEmoji} **{ctx.author.name},** please set the message you wish to send upon a user receiving a **{infraction_type_name}**." else "",
                                "embeds": [i.to_dict() for i in updated_message.embeds]
                            }
                            await message.edit(view=None, embed=None)
                        case "send_escalation":
                            send_escalation_status = True
                            await message.edit(
                                content=f"{pendingEmoji} **{ctx.author.name},** please select the channel you wish to send an escalation request to upon a user receiving a **{infraction_type_name}**.",
                                view=(view := ChannelSelect(ctx.author.id, limit=1))
                            )
                            await view.wait()
                            send_escalationCID = [str(channel.id) for channel in view.value]
                            await message.edit(
                                content=f"{pendingEmoji} **{ctx.author.name},** should the member responsible for issuing the infraction that triggers an escalation request also have the authority to approve the escalation request? **{infraction_type_name}**.",
                                view=(view := YesNoMenu(ctx.author.id))
                            )
                            await view.wait()
                            self_approval_status = view.value
                            await message.edit(view=None, embed=None)

                else:
                    await message.edit(
                        content=f"{successEmoji} **{infraction_type_name}** has been successfully submitted!",
                        view=None,
                        embed=None
                    )

                staff_conduct_data = {
                    "name": infraction_type_name,
                    "actions": {
                        "dm_user": {
                            "enabled": send_dm_status,
                            "embeds": {
                                "message": {
                                    "content": send_dmContent["content"],
                                    "embeds": send_dmContent["embeds"],
                                },
                            },
                        },
                        "send_message": {
                            "enabled": send_message_status,
                            "channel_id": send_messageCID,
                            "embeds": {
                                "message": {
                                    "content": send_messageContent["content"],
                                    "embeds": send_messageContent["embeds"],
                                },
                            },
                        },
                        "remove_roles": {
                            "enabled": remove_role_status,
                            "role_ids": removeroleList
                        },
                        "add_roles": {
                            "enabled": add_role_status,
                            "role_ids": addroleList
                        },
                        "escalation_requests": {
                            "enabled": send_escalation_status,
                            "channel_id": send_escalationCID,
                            "self_approval": self_approval_status
                        },
                        "remove_staff_roles": {
                            "enabled": remove_staff_roles_status,
                            "roles_to_remove": staffroleList
                        },
                    },
                }

                if Data:
                    Data["conduct"].append({
                        "name": infraction_type_name,
                        "actions": {
                            "dm_user": {
                                "enabled": send_dm_status,
                                "embeds": {
                                    "message": {
                                        "content": send_dmContent["content"],
                                        "embeds": send_dmContent["embeds"],
                                    },
                                },
                            },
                            "send_message": {
                                "enabled": send_message_status,
                                "channel_id": send_messageCID,
                                "embeds": {
                                    "message": {
                                        "content": send_messageContent["content"],
                                        "embeds": send_messageContent["embeds"],
                                    },
                                },
                            },
                            "remove_roles": {
                                "enabled": remove_role_status,
                                "role_ids": removeroleList
                            },
                            "add_roles": {
                                "enabled": add_role_status,
                                "role_ids": addroleList
                            },
                            "escalation_requests": {
                                "enabled": send_escalation_status,
                                "channel_id": send_escalationCID,
                                "self_approval": self_approval_status
                            },
                            "remove_staff_roles": {
                                "enabled": remove_staff_roles_status,
                                "roles_to_remove": staffroleList
                            },
                        },
                    })
                else:
                    Data = staff_conduct_data

                await bot.staff_conduct.upsert(Data)
            case "list_infraction_types":
                embed = discord.Embed(
                    title="<:ERMSecurity:1113209656370802879> Infractions", color=0xED4348
                )
                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url,
                )
                embed.set_thumbnail(url=ctx.guild.icon.url)
                for item in Data["conduct"]:
                    embed.add_field(
                        name=f"<:ERMList:1111099396990435428> {item['name']}",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**DM User:** { {True: '<:ERMCheck:1111089850720976906>', False: '<:ERMClose:1111101633389146223>', None: '<:ERMClose:1111101633389146223>'}[item.get('send_dm_status')]}",
                        inline=False,
                    )

                if len(embed.fields) == 0:
                    embed.add_field(
                        name="<:ERMList:1111099396990435428> No infractions",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912> No infractions have been added.",
                        inline=False,
                    )

                await message.edit(
                    embed=embed,
                    view=None,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** you are **viewing** infractions.",
                )
            case "edit_infraction_type":
                infractionList = []
                for item in Data["conduct"]:
                    infractionList.append(item["name"])
                else:
                    if not infractionList:
                        return await message.edit(
                            content=f"{errorEmoji} **{ctx.author.name},** there are no Infraction Types to edit!",
                            view=None,
                            embed=None
                        )

                options = []
                for item in infractionList:
                    options.append(discord.SelectOption(
                            label=f"{item}",
                            description=f"{item}",
                            value=f"{item}"
                        )
                    )

                view = CustomSelectMenu(ctx.author.id, options)

                await message.edit(
                    view=view,
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** please select the Infraction Type you wish to edit.",
                )
                await view.wait()

            case "delete_infraction_type":
                infractionList = []
                for item in Data["conduct"]:
                    infractionList.append(item["name"])
                else:
                    if not infractionList:
                        return await message.edit(
                            content=f"{errorEmoji} **{ctx.author.name},** there are no Infraction Types to delete!",
                            view=None,
                            embed=None
                        )

                options = []
                for item in infractionList:
                    options.append(discord.SelectOption(
                            label=f"{item}",
                            description=f"{item}",
                            value=f"{item}"
                        )
                    )

                view = CustomSelectMenu(ctx.author.id, options)

                await message.edit(
                    view=view,
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** please select the Infraction Type you wish to delete.",
                )
                await view.wait()
                name = view.value

                for item in Data["conduct"]:
                    if item["name"].lower() == name.lower():
                        Data["conduct"].remove(item)
                        await bot.staff_conduct.upsert(Data)

                return await message.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** I've deleted **{name}**.",
                    view=None,
                )

    @infraction.command(
        name="create",
        description="Give a staff member an infraction of specified type.",
        extras={"category": "Staff Conduct"}
    )
    @is_management()
    async def create(self, ctx: commands.Context):
        await ctx.reply(
            f"{pendingEmoji} **{ctx.author.name},** this feature has not been implemented yet! Please check back another time."
        )


async def setup(bot):
    await bot.add_cog(StaffConduct(bot))
