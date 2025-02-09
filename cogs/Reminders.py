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
from utils.utils import (
    generator,
    time_converter,
    require_settings,
    log_command_usage
)
from utils.paginators import SelectPagination, CustomPage


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
        await log_command_usage(self.bot,ctx.guild, ctx.author, f"Reminders Manage")
        reminder_data = await bot.reminders.find_by_id(ctx.guild.id)
        if reminder_data is None:
            reminder_data = {"_id": ctx.guild.id, "reminders": []}

        embed_list = []

        for i in range(0, len(reminder_data["reminders"]), 3):
            embed = discord.Embed(
                title="Reminders",
                color=BLANK_COLOR
            )
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            )
            embed.set_thumbnail(
                url=ctx.guild.icon
            )

            chunk = reminder_data["reminders"][i:i+3]
            for reminder in chunk:
                embed.add_field(
                    name=f"{reminder['name']}",
                    value=(
                        f"> **Name:** {reminder['name']}\n"
                        f"> **ID:** {reminder['id']}\n"
                        f"> **Interval:** {td_format(datetime.timedelta(seconds=reminder['interval']))}\n"
                        f"> **ER:LC Integration:** {'<:check:1163142000271429662>' if reminder.get('integration') is not None else '<:xmark:1166139967920164915>'}\n"
                        f"> **Paused:** {'<:check:1163142000271429662>' if reminder.get('paused') is True else '<:xmark:1166139967920164915>'}"
                    ),
                    inline=False
                )
            embed_list.append(embed)

        if not embed_list:
            embed = discord.Embed(
                title="Reminders",
                color=BLANK_COLOR
            )
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            )
            embed.set_thumbnail(
                url=ctx.guild.icon
            )
            embed.add_field(
                name="No Reminders",
                value="This server has no reminders."
            )
            embed_list.append(embed)

        manage_view = ManageReminders(ctx.author.id)

        pages = []
        for index, embed in enumerate(embed_list):
            combined_view = discord.ui.View(timeout=None)
            for item in manage_view.children:
                combined_view.add_item(item)
                
            page = CustomPage(
                embeds=[embed],
                identifier=f"Page {index + 1}" if index != 0 else 'Reminders',
                view=combined_view
            )
            pages.append(page)

        if len(pages) == 1:
            msg = await ctx.reply(
                embed=embed_list[0],
                view=manage_view
            )
        else:
            paginator = SelectPagination(ctx.author.id, pages)
            view_page = paginator.get_current_view()
            msg = await ctx.reply(
                embed=pages[0].embeds[0],
                view=view_page
            )

        await manage_view.wait()
        if manage_view.value == "pause":
            reminder = manage_view.modal.id_value.value
            for index, item in enumerate(reminder_data["reminders"]):
                if item["id"] == int(reminder if all(n for n in reminder if n.isdigit()) else 0):
                    item["paused"] = not item.get("paused", False)
                    reminder_data["reminders"][index] = item
                    await bot.reminders.upsert(reminder_data)
                    return await msg.edit(
                        embed=discord.Embed(
                            title=f"<:success:1163149118366040106> Reminder {'Paused' if item['paused'] else 'Resumed'}",
                            description=f"Your reminder has been {'paused' if item['paused'] else 'resumed'}!",
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

        elif manage_view.value == "edit":
                id = manage_view.modal.identifier.value
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
                            color=BLANK_COLOR
                        ),
                        view=None
                    )


                completion_ability = dataset.get("completion_ability", False)
                if completion_ability:
                    completion_styling = {
                        "label": "Completion Ability: Enabled",
                        "style": discord.ButtonStyle.green
                    }
                else:
                    completion_styling = {
                        "label": "Completion Ability: Disabled",
                        "style": discord.ButtonStyle.danger
                    }

                view = ReminderCreationToolkit(ctx.author.id, dataset, "edit", {
                    "Reminder Channel": list(filter(lambda x: x is not None, [discord.utils.get(ctx.guild.channels, id=dataset.get("channel", None))])),
                    "Mentioned Roles": list(filter(lambda x: x is not None, [discord.utils.get(ctx.guild.roles, id=i) for i in dataset.get('role') or []])),
                    "Completion Ability: Disabled": completion_styling
                })
                await msg.edit(embed=discord.Embed(
                    title="Edit a Reminder",
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
                    color=BLANK_COLOR
                ), view=view)
                await view.wait()
                if view.cancelled is True:
                    return

                # Update the reminder
                for index, item in enumerate(reminder_data['reminders']):
                    if item['id'] == dataset['id']:
                        reminder_data['reminders'][index] = dataset

                await bot.reminders.upsert(reminder_data)
                await msg.edit(
                    embed=discord.Embed(
                        title="<:success:1163149118366040106> Reminder Edited",
                        description="Your reminder has been edited!",
                        color=GREEN_COLOR
                    ),
                    view=None
                )
                return
        elif manage_view.value == "create":
            time_arg = manage_view.modal.time.value
            message = manage_view.modal.content.value
            name = manage_view.modal.name.value
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
                    color=BLANK_COLOR
                ),
                view=view
            )
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

        elif manage_view.value == "delete":
            name = manage_view.modal.id_value.value
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
