import datetime
import discord
from discord.ext import commands
from erm import is_management, is_admin
from menus import (
    ManageReminders,
    YesNoColourMenu,
    ReminderCreationToolkit,
)
from utils.constants import BLANK_COLOR, GREEN_COLOR
from utils.timestamp import td_format
from utils.utils import generator, time_converter, require_settings, log_command_usage


class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="reminders")
    @is_management()
    async def reminders(self, ctx):
        pass

    @commands.guild_only()
    @reminders.command(
        name="manage",
        description="Manage your reminders",
        extras={"category": "Reminders"},
    )
    @is_admin()
    @require_settings()
    async def manage_reminders(self, ctx):
        bot = self.bot
        await log_command_usage(self.bot, ctx.guild, ctx.author, f"Reminders Manage")
        reminder_data = await bot.reminders.find_by_id(ctx.guild.id)
        if reminder_data is None:
            reminder_data = {"_id": ctx.guild.id, "reminders": []}

        embed = discord.Embed(title="Reminders", color=BLANK_COLOR)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        [
            embed.add_field(
                name=f"{reminder['name']}",
                value=(
                    f"> **Name:** {reminder['name']}\n"
                    f"> **ID:** {reminder['id']}\n"
                    f"> **Interval:** {td_format(datetime.timedelta(seconds=reminder['interval']))}\n"
                    f"> **ER:LC Integration:** {self.bot.emoji_controller.get_emoji('check') if reminder.get('integration') is not None else self.bot.emoji_controller.get_emoji('xmark')}\n"
                    f"> **Paused:** {self.bot.emoji_controller.get_emoji('check') if reminder.get('paused') is True else self.bot.emoji_controller.get_emoji('xmark')}"
                ),
                inline=False,
            )
            for reminder in reminder_data["reminders"]
        ]
        embed.set_thumbnail(url=ctx.guild.icon)

        if len(embed.fields) == 0:
            embed.add_field(name="No Reminders", value="This server has no reminders.")

        view = ManageReminders(ctx.author.id)

        msg = await ctx.reply(
            embed=embed,
            view=view,
        )
        await view.wait()
        if view.value == "pause":
            reminder = view.modal.id_value.value

            for index, item in enumerate(reminder_data["reminders"]):
                if item["id"] == int(
                    reminder if all(n for n in reminder if n.isdigit()) else 0
                ):
                    if item.get("paused") is True:
                        item["paused"] = False
                        reminder_data["reminders"][index] = item
                        await bot.reminders.upsert(reminder_data)
                        return await msg.edit(
                            embed=discord.Embed(
                                title=f"{self.bot.emoji_controller.get_emoji('success')} Reminder Resumed",
                                description="Your reminder has been resumed!",
                                color=GREEN_COLOR,
                            ),
                            view=None,
                        )
                    else:
                        item["paused"] = True
                        reminder_data["reminders"][index] = item
                        await bot.reminders.upsert(reminder_data)
                        return await msg.edit(
                            embed=discord.Embed(
                                title=f"{self.bot.emoji_controller.get_emoji('success')} Reminder Paused",
                                description="Your reminder has been paused!",
                                color=GREEN_COLOR,
                            ),
                            view=None,
                        )

            return await msg.edit(
                embed=discord.Embed(
                    title="Invalid Reminder",
                    description="We could not find the reminder associated with that ID.",
                    color=BLANK_COLOR,
                ),
                view=None,
            )

        if view.value == "edit":
            id = view.modal.identifier.value
            dataset = None
            for item in reminder_data["reminders"]:
                if item["id"] == int(id if all(n for n in id if n.isdigit()) else 0):
                    dataset = item
                    break
            if not dataset:
                return await msg.edit(
                    embed=discord.Embed(
                        title="Could not find reminder",
                        description="I could not find the reminder with the ID you specified.",
                        color=BLANK_COLOR,
                    ),
                    view=None,
                )

            completion_ability = dataset.get("completion_ability", False)
            if completion_ability:
                completion_styling = {
                    "label": "Completion Ability: Enabled",
                    "style": discord.ButtonStyle.green,
                }
            else:
                completion_styling = {
                    "label": "Completion Ability: Disabled",
                    "style": discord.ButtonStyle.danger,
                }

            view = ReminderCreationToolkit(
                ctx.author.id,
                dataset,
                "edit",
                {
                    "Reminder Channel": list(
                        filter(
                            lambda x: x is not None,
                            [
                                discord.utils.get(
                                    ctx.guild.channels, id=dataset.get("channel", None)
                                )
                            ],
                        )
                    ),
                    "Mentioned Roles": list(
                        filter(
                            lambda x: x is not None,
                            [
                                discord.utils.get(ctx.guild.roles, id=i)
                                for i in dataset.get("role") or []
                            ],
                        )
                    ),
                    "Completion Ability: Disabled": completion_styling,
                },
            )
            await msg.edit(
                embed=discord.Embed(
                    title="Edit a Reminder",
                    description=(
                        f"> **Name:** {dataset['name']}\n"
                        f"> **ID:** {dataset['id']}\n"
                        f"> **Channel:** {'<#{}>'.format(dataset.get('channel', None)) if dataset.get('channel', None) is not None else 'Not set'}\n"
                        f"> **Completion Ability:** {dataset.get('completion_ability') or 'Not set'}\n"
                        f"> **Mentioned Roles:** {', '.join(['<@&{}>'.format(r) for r in (dataset.get('role') or [])]) or 'Not set'}\n"
                        f"> **Interval:** {td_format(datetime.timedelta(seconds=dataset.get('interval', 0))) or 'Not set'}\n"
                        f"> **ER:LC Integration Enabled:** {dataset.get('integration') is not None}"
                        f"\n\n**Content:**\n{dataset['message']}"
                    ),
                    color=BLANK_COLOR,
                ),
                view=view,
            )
            await view.wait()
            if view.cancelled is True:
                return

            # Update the reminder
            for index, item in enumerate(reminder_data["reminders"]):
                if item["id"] == dataset["id"]:
                    reminder_data["reminders"][index] = dataset

            await bot.reminders.upsert(reminder_data)
            await msg.edit(
                embed=discord.Embed(
                    title=f"{self.bot.emoji_controller.get_emoji('success')} Reminder Edited",
                    description="Your reminder has been edited!",
                    color=GREEN_COLOR,
                ),
                view=None,
            )
            return
        if view.value == "create":
            time_arg = view.modal.time.value
            message = view.modal.content.value
            name = view.modal.name.value
            try:
                new_time = time_converter(time_arg)
            except ValueError:
                return await msg.edit(
                    embed=discord.Embed(
                        title="Invalid Time",
                        description="You did not enter a valid time.",
                        color=BLANK_COLOR,
                    ),
                    view=None,
                )

            dataset = {
                "id": next(generator),
                "name": name,
                "interval": new_time,
                "completion_ability": None,
                "message": message,
                "channel": None,
                "role": [],
                "lastTriggered": 0,
                "paused": False,
            }

            view = ReminderCreationToolkit(ctx.author.id, dataset, "create")
            await msg.edit(
                embed=discord.Embed(
                    title="Reminder Creation",
                    description=(
                        f"> **Name:** {dataset['name']}\n"
                        f"> **ID:** {dataset['id']}\n"
                        f"> **Channel:** {'<#{}>'.format(dataset.get('channel', None)) if dataset.get('channel', None) is not None else 'Not set'}\n"
                        f"> **Completion Ability:** {dataset.get('completion_ability') or 'Not set'}\n"
                        f"> **Mentioned Roles:** {', '.join(['<@&{}>'.format(r) for r in dataset.get('role', [])]) or 'Not set'}\n"
                        f"> **Interval:** {td_format(datetime.timedelta(seconds=dataset.get('interval', 0))) or 'Not set'}\n"
                        f"> **ER:LC Integration Enabled:** {dataset.get('integration') is not None}"
                        f"\n\n**Content:**\n{dataset['message']}"
                    ),
                    color=BLANK_COLOR,
                ),
                view=view,
            )
            await view.wait()
            if view.cancelled is True:
                return

            reminder_data["reminders"].append(view.dataset)

            await bot.reminders.upsert(reminder_data)
            await msg.edit(
                embed=discord.Embed(
                    title=f"{self.bot.emoji_controller.get_emoji('success')} Reminder Created",
                    description="Your reminder has been created!",
                    color=GREEN_COLOR,
                ),
                view=None,
            )

        elif view.value == "delete":
            name = view.modal.id_value.value
            for item in reminder_data["reminders"]:
                if item["id"] == int(
                    name if all(n for n in name if n.isdigit()) else 0
                ):
                    reminder_data["reminders"].remove(item)
                    await bot.reminders.upsert(reminder_data)
                    return await msg.edit(
                        embed=discord.Embed(
                            title=f"{self.bot.emoji_controller.get_emoji('success')} Reminder Deleted",
                            description="Your reminder has been deleted!",
                            color=GREEN_COLOR,
                        ),
                        view=None,
                    )
            else:
                return await msg.edit(
                    embed=discord.Embed(
                        title="Invalid Reminder",
                        description="We could not find the reminder associated with that ID.",
                        color=BLANK_COLOR,
                    ),
                    view=None,
                )


async def setup(bot):
    await bot.add_cog(Reminders(bot))
