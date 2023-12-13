import datetime

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
    CustomModalView, ReminderCreationToolkit,
)
from utils.constants import BLANK_COLOR, GREEN_COLOR
from utils.timestamp import td_format
from utils.utils import (
    generator,
    invis_embed,
    removesuffix,
    request_response,
    failure_embed, time_converter,
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
        reminder_data = await bot.reminders.find_by_id(ctx.guild.id)
        if reminder_data is None:
            reminder_data = {"_id": ctx.guild.id, "reminders": []}

        embed = discord.Embed(
            title="<:reminder:1163143497348558848> Reminders",
            color=BLANK_COLOR
        )
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
        )
        embed.set_thumbnail(
            url=ctx.guild.icon.url if ctx.guild.icon else ''
        )
        _ = [embed.add_field(
            name=f"{reminder['name']}",
            value=(
                f"<:replytop:1138257149705863209> **Name:** {reminder['name']}\n"
                f"<:replymiddle:1138257195121791046> **ID:** {reminder['id']}\n"
                f"<:replymiddle:1138257195121791046> **Interval:** {td_format(datetime.timedelta(seconds=reminder['interval']))}\n"
                f"<:replybottom:1138257250448855090> **Paused:** {'<:check:1163142000271429662>' if reminder.get('paused') is True else '<:xmark:1166139967920164915>'}"
            ),
            inline=False
        ) for reminder in reminder_data["reminders"]]

        if len(embed.fields) == 0:
            embed.add_field(
                name="No Reminders",
                value="<:replybottom:1138257250448855090> *This server has no reminders.*"
            )

        view = ManageReminders(ctx.author.id)

        msg = await ctx.reply(
            embed=embed,
            view=view,
        )
        await view.wait()
        if view.value == "pause":
            reminder = view.modal.id_value.value

            for index, item in enumerate(reminder_data["reminders"]):
                if item["id"] == int(reminder if all(n for n in reminder if n.isdigit()) else 0):
                    if item.get("paused") is True:
                        item["paused"] = False
                        reminder_data["reminders"][index] = item
                        await bot.reminders.upsert(reminder_data)
                        return await msg.edit(
                            embed=discord.Embed(
                                title="<:success:1163149118366040106> Reminder Resumed",
                                description="Your reminder has been resumed!",
                                color=GREEN_COLOR
                            ),
                            view=None,
                        )
                    else:
                        item["paused"] = True
                        reminder_data["reminders"][index] = item
                        await bot.reminders.upsert(reminder_data)
                        return await msg.edit(
                            embed=discord.Embed(
                                title="<:success:1163149118366040106> Reminder Paused",
                                description="Your reminder has been paused!",
                                color=GREEN_COLOR
                            ),
                            view=None,
                        )

            return await msg.edit(
                embed=discord.Embed(
                    title='Invalid Reminder',
                    description="We could not find the reminder associated with that ID.",
                    color=BLANK_COLOR
                ),
                view=None,
            )

        if view.value == "create":
                time_arg = view.modal.time.value
                message = view.modal.content.value
                name = view.modal.name.value
                try:
                    new_time = time_converter(time_arg)
                except ValueError:
                    return await msg.edit(
                        embed=discord.Embed(
                            title='Invalid Time',
                            description="You did not enter a valid time.",
                            color=BLANK_COLOR
                        ),
                        view=None,
                    )



                view = YesNoColourMenu(ctx.author.id)

                dataset = {
                        "id": next(generator),
                        "name": name,
                        "interval": new_time,
                        "completion_ability": None,
                        "message": message,
                        "channel": None,
                        "role": [],
                        "lastTriggered": 0,
                        "paused": False
                    }

                view = ReminderCreationToolkit(ctx.author.id, dataset)
                await msg.edit(embed=discord.Embed(
                    title="<:reminder:1163143497348558848> Reminder Creation",
                    description=(
                        f"<:replytop:1138257149705863209> **Name:** {dataset['name']}\n"
                        f"<:replymiddle:1138257195121791046> **ID:** {dataset['id']}\n"
                        f"<:replymiddle:1138257195121791046>**Channel:** {'<#{}>'.format(dataset.get('channel', None)) or 'Not set'}\n"
                        f"<:replymiddle:1138257195121791046> **Completion Ability:** {dataset.get('completion_ability') or 'Not set'}\n"
                        f"<:replymiddle:1138257195121791046> **Mentioned Roles:** {', '.join(['<@&{}>'.format(r) for r in dataset.get('roles', [])]) or 'Not set'}\n"
                        f"<:replybottom:1138257250448855090> **Interval:** {td_format(datetime.timedelta(seconds=dataset.get('interval', 0))) or 'Not set'}"
                        f"\n\n**Content:**\n{dataset['message']}"
                    ),
                    color=BLANK_COLOR
                ), view=view)
                await view.wait()
                if view.cancelled is True:
                    return

                reminder_data["reminders"].append(
                    view.dataset
                )

                await bot.reminders.upsert(reminder_data)
                await msg.edit(
                    embed=discord.Embed(
                        title="<:success:1163149118366040106> Reminder Created",
                        description="Your reminder has been created!",
                        color=GREEN_COLOR
                    ),
                    view=None
                )

        elif view.value == "delete":
            name = view.modal.id_value.value
            for item in reminder_data["reminders"]:
                if item["id"] == int(name if all(n for n in name if n.isdigit()) else 0):
                    reminder_data["reminders"].remove(item)
                    await bot.reminders.upsert(reminder_data)
                    return await msg.edit(
                    embed=discord.Embed(
                        title="<:success:1163149118366040106> Reminder Deleted",
                        description="Your reminder has been deleted!",
                        color=GREEN_COLOR
                    ),
                    view=None
                )
            else:
                return await msg.edit(
                    embed=discord.Embed(
                        title='Invalid Reminder',
                        description="We could not find the reminder associated with that ID.",
                        color=BLANK_COLOR
                    ),
                    view=None,
                )


async def setup(bot):
    await bot.add_cog(Reminders(bot))
