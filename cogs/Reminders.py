import discord
from discord.ext import commands

from erm import is_management
from menus import (
    ChannelSelect,
    ManageReminders,
    RoleSelect,
    YesNoColourMenu,
    YesNoMenu,
    CustomSelectMenu,
    CustomModalView,
)
from utils.utils import (
    generator,
    invis_embed,
    removesuffix,
    request_response,
    failure_embed,
)


class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="reminders")
    @is_management()
    async def reminders(self, ctx):
        pass

    @reminders.command(
        name="manage",
        description="Manage your reminders",
        extras={"category": "Reminders"},
    )
    @is_management()
    async def manage_reminders(self, ctx):
        bot = self.bot
        Data = await bot.reminders.find_by_id(ctx.guild.id)
        if Data is None:
            Data = {"_id": ctx.guild.id, "reminders": []}

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Create",
                    value="create",
                    description="Create a reminder.",
                    emoji="<:ERMAdd:1113207792854106173>",
                ),
                discord.SelectOption(
                    label="List",
                    value="list",
                    description="List all of the reminders",
                    emoji="<:ERMList:1111099396990435428>",
                ),
                discord.SelectOption(
                    label="Pause",
                    value="pause",
                    description="Pause a reminder",
                    emoji="<:ERMReminder:1113211641736208506>",
                ),
                discord.SelectOption(
                    label="Delete",
                    value="delete",
                    description="Delete a reminder",
                    emoji="<:ERMTrash:1111100349244264508>",
                ),
            ],
        )

        msg = await ctx.reply(
            f"<:ERMPending:1111097561588183121> **{ctx.author.name},** select an option.",
            view=view,
        )
        await view.wait()

        if view.value == "list":
            embed = discord.Embed(
                title="<:ERMReminder:1113211641736208506> Reminders", color=0xED4348
            )
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )
            embed.set_thumbnail(url=ctx.guild.icon.url)
            for item in Data["reminders"]:
                embed.add_field(
                    name=f"<:ERMList:1111099396990435428> {item['name']}",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Interval:** {item['interval']} seconds\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Paused:** { {True: '<:ERMCheck:1111089850720976906>', False: '<:ERMClose:1111101633389146223>', None: '<:ERMClose:1111101633389146223>'}[item.get('paused')]}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Able to be Completed:** {'<:ERMCheck:1111089850720976906>' if item.get('completion_ability') else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Channel:** <#{item['channel']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **ID:** {item['id']}",
                    inline=False,
                )

            if len(embed.fields) == 0:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> No reminders",
                    value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912> No reminders have been added.",
                    inline=False,
                )

            view = ManageReminders(ctx.author.id)

            await msg.edit(
                embed=embed,
                view=None,
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** you are **viewing** reminders.",
            )

        if view.value == "pause":
            view = CustomModalView(
                ctx.author.id,
                "Pause Reminder",
                "Pause Reminder",
                [
                    (
                        "id",
                        discord.ui.TextInput(
                            label="Reminder ID",
                            min_length=1,
                        ),
                    )
                ],
            )
            await msg.edit(
                content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** what reminder do you want to pause?",
                view=view,
            )
            await view.wait()
            reminder = view.modal.id.value

            try:
                for index, item in enumerate(Data["reminders"]):
                    if item["id"] == int(reminder):
                        if item.get("paused") is True:
                            item["paused"] = False
                            Data["reminders"][index] = item
                            await bot.reminders.upsert(Data)
                            return await msg.edit(
                                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** your reminder has been resumed!",
                                view=None,
                            )
                        else:
                            item["paused"] = True
                            Data["reminders"][index] = item
                            await bot.reminders.upsert(Data)
                            return await msg.edit(
                                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** your reminder has been paused!",
                                view=None,
                            )
            except:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that is not a valid reminder ID.",
                    view=None,
                )

        if view.value == "create":
            view = CustomModalView(
                ctx.author.id,
                "Create Reminder",
                "Create Reminder",
                [
                    (
                        "name",
                        discord.ui.TextInput(
                            label="Reminder Name",
                            min_length=1,
                        ),
                    ),
                    (
                        "time",
                        discord.ui.TextInput(
                            label="Reminder Interval",
                            placeholder="1s, 1m, 1h",
                            min_length=1,
                        ),
                    ),
                    (
                        "content",
                        discord.ui.TextInput(
                            label="Reminder Content",
                            min_length=1,
                            style=discord.TextStyle.long,
                        ),
                    ),
                ],
            )
            await msg.edit(
                content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** what do you want to call this reminder?",
                view=view,
            )
            await view.wait()

            if view.modal:
                timeout = await view.modal.wait()
                if timeout:
                    return

                time = view.modal.time.value
                message = view.modal.content.value
                name = view.modal.name.value
                try:
                    if time.lower().endswith("s"):
                        time = int(removesuffix(time.lower(), "s"))
                    elif time.lower().endswith("m"):
                        time = int(removesuffix(time.lower(), "m")) * 60
                    elif time.lower().endswith("h"):
                        time = int(removesuffix(time.lower(), "h")) * 60 * 60
                    elif time.lower().endswith("d"):
                        time = int(removesuffix(time.lower(), "d")) * 60 * 60 * 24
                    elif time.lower().endswith("w"):
                        time = int(removesuffix(time.lower(), "w")) * 60 * 60 * 24 * 7
                    else:
                        return await failure_embed(
                            ctx, "you haven't used the right time format!"
                        )
                except:
                    return await ctx.reply(
                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a correct time must be provided."
                    )

                view = YesNoColourMenu(ctx.author.id)

                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** do you want this reminder to be able to be completed?",
                    view=view,
                )
                timeout = await view.wait()
                if timeout:
                    return

                completed = view.value

                view = ChannelSelect(ctx.author.id, limit=1)
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** what channel do you want it to be sent in?",
                    view=view,
                )

                timeout = await view.wait()
                if timeout:
                    return

                channel = view.value[0] if view.value else None
                if not channel:
                    return await failure_embed(ctx, "you haven't selected a channel!")

                view = YesNoMenu(ctx.author.id)

                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** do you want to mention a role?",
                    view=view,
                )

                roleObject = None
                timeout = await view.wait()
                if view.value == True:
                    view = RoleSelect(ctx.author.id)
                    await msg.edit(
                        content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** what roles?",
                        view=view,
                    )

                    timeout = await view.wait()
                    if timeout:
                        return
                    roleObject = view.value

                if roleObject:
                    Data["reminders"].append(
                        {
                            "id": next(generator),
                            "name": name,
                            "interval": time,
                            "completion_ability": completed,
                            "message": message,
                            "channel": channel.id,
                            "role": [role.id for role in roleObject]
                            if roleObject
                            else [],
                            "lastTriggered": 0,
                        }
                    )
                else:
                    Data["reminders"].append(
                        {
                            "id": next(generator),
                            "name": name,
                            "interval": time,
                            "completion_ability": completed,
                            "message": message,
                            "channel": channel.id,
                            "role": 0,
                            "lastTriggered": 0,
                        }
                    )
                await bot.reminders.upsert(Data)
                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** your reminder has been created!"
                )

        elif view.value == "delete":
            view = CustomModalView(
                ctx.author.id,
                "Delete Reminder",
                "Delete Reminder",
                [
                    (
                        "id",
                        discord.ui.TextInput(
                            label="Reminder ID",
                            min_length=1,
                        ),
                    )
                ],
            )
            await msg.edit(
                content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** what reminder do you want to delete?",
                view=view,
            )
            await view.wait()
            name = view.modal.id.value
            try:
                for item in Data["reminders"]:
                    if item["id"] == int(name):
                        Data["reminders"].remove(item)
                        await bot.reminders.upsert(Data)
                        return await msg.edit(
                            view=None,
                            content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** your reminder has been deleted!",
                        )
            except:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223> **{ctx.author.name},** I could not find this reminder!"
                )


async def setup(bot):
    await bot.add_cog(Reminders(bot))
