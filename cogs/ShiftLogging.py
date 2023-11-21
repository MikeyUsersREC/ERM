import datetime
from io import BytesIO


import discord
import pytz
from decouple import config
from discord import app_commands
from discord.ext import commands

from datamodels.ShiftManagement import ShiftItem
from erm import credentials_dict, is_management, is_staff, management_predicate, scope
from menus import (
    CustomExecutionButton,
    CustomSelectMenu,
    RequestGoogleSpreadsheet,
    ShiftMenu,
    AdministratedShiftMenu,
)
from utils.autocompletes import shift_type_autocomplete
from utils.constants import BLANK_COLOR, GREEN_COLOR, ORANGE_COLOR, RED_COLOR
from utils.paginators import SelectPagination, CustomPage
from utils.timestamp import td_format
from utils.utils import get_elapsed_time, new_failure_embed, require_settings


class ShiftLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="duty")
    async def duty(self, ctx):
        pass

    @duty.command(
        name="time",
        description="Allows for you to check your shift time, as well as your past data.",
        extras={"category": "Shift Management"},
        with_app_command=True,
    )
    @is_staff()
    @require_settings()
    async def duty_time(self, ctx, member: discord.Member = None):
        if self.bot.shift_management_disabled is True:
            return await new_failure_embed(
                ctx,
                "Maintenance",
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance.",
            )

        bot = self.bot
        if not member:
            member = ctx.author

        configItem = await bot.settings.find_by_id(ctx.guild.id)

        if not configItem["shift_management"]["enabled"]:
            return await new_failure_embed(
                ctx,
                "Not Enabled",
                "Shift Logging is not enabled on this server."
            )
        try:
            shift_channel = discord.utils.get(
                ctx.guild.channels, id=configItem["shift_management"]["channel"]
            )
        except:
            return await new_failure_embed(
                ctx,
                "Incorrect Configuration",
                'This server is not configured correctly.',
            )

        embed = discord.Embed(
            title=f"Total Shifts" if member == ctx.author else f'{member.name}\'s Total Shifts',
            color=BLANK_COLOR,
        )
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
        )


        # Get current shift
        shift = None
        shift_data = await bot.shift_management.get_current_shift(member, ctx.guild.id)
        if shift_data:
            if shift_data["Guild"] == ctx.guild.id:
                shift = shift_data


        # Get all past shifts
        shifts = []
        storage_item = [
            i
            async for i in bot.shift_management.shifts.db.find(
                {"UserID": member.id, "Guild": ctx.guild.id}
            )
        ]

        for s in storage_item:
            if s["EndEpoch"] != 0:
                shifts.append(s)

        total_seconds = sum([get_elapsed_time(i) for i in shifts])

        quota = configItem.get('shift_management', {}).get('quota', 0)
        met_quota = None
        if quota != 0:
            met_quota = bool(total_seconds > quota)

        try:
            if shift:
                embed.add_field(
                    name="Ongoing Shift",
                    value=f"{td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}",
                    inline=False,
                )
        except:
            if shift:
                embed.add_field(
                    name="Ongoing Shift",
                    value="Could not display current shift time.",
                    inline=False,
                )

        newline = '\n'
        embed.add_field(
            name=f"Shift Time [{len(shifts)}]",
            value=f"{td_format(datetime.timedelta(seconds=total_seconds))} {'{0}*{1}*'.format(newline, 'Met Quota' if met_quota is True else 'Not Met Quota') if met_quota is not None else ''}",
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.reply(
            embed=embed,
        )


    @duty.command(
        name="admin",
        description="Allows for you to administrate someone else's shift",
        extras={"category": "Shift Management"},
    )
    @require_settings()
    @is_management()
    @app_commands.autocomplete(
        type=shift_type_autocomplete
    )
    async def duty_admin(self, ctx, member: discord.Member, type: str = "Default"):
        if self.bot.shift_management_disabled is True:
            return await new_failure_embed(
                ctx,
                "Maintenance",
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance.",
            )

        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings.get('shift_management', {}).get('enabled', False):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Shift Logging is not enabled on this server.",
                    color=BLANK_COLOR
                )
            )

        shift_types = settings.get('shift_types', {}).get('types', [])
        if shift_types:
            if type.lower() not in [t['name'].lower() for t in shift_types]:
                return await ctx.send(
                    embed=discord.Embed(
                        title="Incorrect Shift Type",
                        description="The shift type provided is not valid.",
                        color=BLANK_COLOR
                    )
                )

            shift_type_item = None
            for item in shift_types:
                if item['name'].lower() == type.lower():
                    shift_type_item = item

            if shift_type_item:
                if shift_type_item.get('access_roles') is not None:
                    item = shift_type_item
                    access_roles = item.get('access_roles') or []
                    if len(access_roles) > 0:
                        access = False
                        for role in access_roles:
                            if role in [i.id for i in member.roles]:
                                access = True
                                break
                        if access is False:
                            return await ctx.send(
                                embed=discord.Embed(
                                    title="Access Denied",
                                    description="This individual does not have access to this shift type.",
                                    color=BLANK_COLOR
                                )
                            )

        shift = await self.bot.shift_management.get_current_shift(ctx.author, ctx.guild.id)

        previous_shifts = [i async for i in self.bot.shift_management.shifts.db.find({
            "UserID": member.id,
            "Guild": ctx.guild.id,
            "EndEpoch": {'$ne': 0}
        })]
        embed = discord.Embed(
            color=BLANK_COLOR
        )

        embed.add_field(
            name="Current Statistics",
            value=(
                f"<:replytop:1138257149705863209> **Total Shift Duration:** {td_format(datetime.timedelta(seconds=sum([get_elapsed_time(item) for item in previous_shifts])))}\n"
                f"<:replymiddle:1138257195121791046> **Total Shifts:** {len(previous_shifts)}\n"
                f"<:replybottom:1138257250448855090> **Average Shift Duration:** {td_format(datetime.timedelta(seconds=(sum([get_elapsed_time(item) for item in previous_shifts]).__truediv__(len(previous_shifts) or 1))))}\n"
            ),
            inline=False
        )

        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
        )

        if shift:
            if (shift.get('Breaks', [{}]) or [{}])[-1].get("EndEpoch", 1) == 0:
                status = "break"
            else:
                status = "on"
        else:
            status = "off"

        contained_document = None
        if status == "on":
            contained_document: ShiftItem = await self.bot.shift_management.fetch_shift(shift['_id'])
            embed.colour = GREEN_COLOR
            embed.add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            )
            embed.title = "<:ShiftStarted:1178033763477889175> **On-Duty**"
        elif status == "break":
            contained_document: ShiftItem = await self.bot.shift_management.fetch_shift(shift['_id'])
            embed.colour = ORANGE_COLOR
            embed.add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Shift Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Break Started:** <t:{int(contained_document.breaks[0].start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            )
            embed.title = "<:ShiftBreak:1178034531702411375> **On-Break**"
        else:
            embed.colour = RED_COLOR
            embed.title = "<:ShiftEnded:1178035088655646880> **Off-Duty**"

        view = AdministratedShiftMenu(
            self.bot,
            status,
            ctx.author.id,
            member.id,
            type,
            shift,
            contained_document
        )
        view.message = await ctx.send(embed=embed, view=view)

    @duty.command(
        name="manage",
        description="Manage your own shift in an easy way!",
        extras={"category": "Shift Management"},
    )
    @is_staff()
    @require_settings()
    @app_commands.autocomplete(
        type=shift_type_autocomplete
    )
    async def duty_manage(self, ctx, *, type: str = "Default"):
        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings.get('shift_management', {}).get('enabled', False):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Shift Logging is not enabled on this server.",
                    color=BLANK_COLOR
                )
            )

        shift_types = settings.get('shift_types', {}).get('types', [])
        if shift_types:
            if type.lower() not in [t['name'].lower() for t in shift_types]:
                return await ctx.send(
                    embed=discord.Embed(
                        title="Incorrect Shift Type",
                        description="The shift type provided is not valid.",
                        color=BLANK_COLOR
                    )
                )

            shift_type_item = None
            for item in shift_types:
                if item['name'].lower() == type.lower():
                    shift_type_item = item

            if shift_type_item:
                if shift_type_item.get('access_roles') is not None:
                    item = shift_type_item
                    access_roles = item.get('access_roles') or []
                    if len(access_roles) > 0:
                        access = False
                        for role in access_roles:
                            if role in [i.id for i in ctx.author.roles]:
                                access = True
                                break
                        if access is False:
                            return await ctx.send(
                                embed=discord.Embed(
                                    title="Access Denied",
                                    description="You do not have access to this shift type.",
                                    color=BLANK_COLOR
                                )
                            )


        if self.bot.shift_management_disabled is True:
            return await new_failure_embed(
                ctx,
                "Maintenance",
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance.",
            )

        shift = await self.bot.shift_management.get_current_shift(ctx.author, ctx.guild.id)
        # view = ModificationSelectMenu(ctx.author.id)
        previous_shifts = [i async for i in self.bot.shift_management.shifts.db.find({
            "UserID": ctx.author.id,
            "Guild": ctx.guild.id,
            "EndEpoch": {'$ne': 0}
        })]
        embed = discord.Embed(
            color=BLANK_COLOR
        )


        embed.add_field(
            name="Current Statistics",
            value=(
                f"<:replytop:1138257149705863209> **Total Shift Duration:** {td_format(datetime.timedelta(seconds=sum([get_elapsed_time(item) for item in previous_shifts])))}\n"
                f"<:replymiddle:1138257195121791046> **Total Shifts:** {len(previous_shifts)}\n"
                f"<:replybottom:1138257250448855090> **Average Shift Duration:** {td_format(datetime.timedelta(seconds=(sum([get_elapsed_time(item) for item in previous_shifts]).__truediv__(len(previous_shifts) or 1))))}\n"
            ),
            inline=False
        )

        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
        )

        if shift:
            if (shift.get('Breaks', [{}]) or [{}])[-1].get("EndEpoch", 1) == 0:
                status = "break"
            else:
                status = "on"
        else:
            status = "off"

        contained_document = None
        if status == "on":
            contained_document: ShiftItem = await self.bot.shift_management.fetch_shift(shift['_id'])
            embed.colour = GREEN_COLOR
            embed.add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            )
            embed.title = "<:ShiftStarted:1178033763477889175> **On-Duty**"
        elif status == "break":
            contained_document: ShiftItem = await self.bot.shift_management.fetch_shift(shift['_id'])
            embed.colour = ORANGE_COLOR
            embed.add_field(
                name="Current Shift",
                value=(
                    f"<:replytop:1138257149705863209> **Shift Started:** <t:{int(contained_document.start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Break Started:** <t:{int(contained_document.breaks[0].start_epoch)}:R>\n"
                    f"<:replymiddle:1138257195121791046> **Breaks:** {len(contained_document.breaks)}\n"
                    f"<:replybottom:1138257250448855090> **Elapsed Time:** {td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}"
                ),
                inline=False
            )
            embed.title = "<:ShiftBreak:1178034531702411375> **On-Break**"
        else:
            embed.colour = RED_COLOR
            embed.title = "<:ShiftEnded:1178035088655646880> **Off-Duty**"

        view = ShiftMenu(
            self.bot,
            status,
            ctx.author.id,
            type,
            starting_document=shift,
            starting_container=contained_document
        )

        view.message = await ctx.send(embed=embed, view=view)


    @duty.command(
        name="active",
        description="Get all members of the server currently on shift.",
        extras={"category": "Shift Management"}
    )
    @require_settings()
    @is_staff()
    async def duty_active(self, ctx):
        if self.bot.shift_management_disabled is True:
            return await new_failure_embed(
                ctx,
                "Maintenance",
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem.get('shift_management', {}).get('enabled', False):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Shift Logging is not enabled on this server."
                )
            )

        shift_type = None
        if configItem.get("shift_types"):
            shift_types = configItem.get("shift_types")
            if shift_types.get("enabled") is True:
                if len(shift_types.get("types")) > 1:
                    shift_types = shift_types.get("types")

                    view = CustomSelectMenu(
                        ctx.author.id,
                        [
                            discord.SelectOption(
                                label=i["name"],
                                value=i["id"],
                                description=i["name"],
                            )
                            for i in shift_types
                        ]
                        + [
                            discord.SelectOption(
                                label="All",
                                value="all",
                                description="Data from all shift types",
                            )
                        ],
                    )

                    msg = await ctx.reply(
                        embed=discord.Embed(
                            title="Shift Types",
                            description=f"You have **{len(shift_types)}** shift types. Which ones would you like to see?",
                            color=BLANK_COLOR
                        ),
                        view=view
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value:
                        if view.value == "all":
                            shift_type = 0
                        else:
                            shift_type = view.value
                            shift_list = [
                                i for i in shift_types if i["id"] == int(shift_type)
                            ]
                            if shift_list:
                                shift_type = shift_list[0]
                            else:
                                return await new_failure_embed(
                                    ctx,
                                    "Critical Error",
                                    "if you somehow encounter this error, please contact [ERM Support](https://discord.gg/FAC629TzBy)",
                                )

        embed = discord.Embed(
            title="Active Shifts", color=BLANK_COLOR
        )
        embed.description = f"**Total Shifts**"
        embed.set_author(
            name=f"{ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
        )

        embeds = []
        embeds.append(embed)

        all_staff = []
        staff_members = []

        if not shift_type:
            async for sh in bot.shift_management.shifts.db.find(
                {"Guild": ctx.guild.id, "EndEpoch": 0}
            ):
                if sh["Guild"] == ctx.guild.id:
                    member = discord.utils.get(ctx.guild.members, id=sh["UserID"])
                    if member:
                        if member not in staff_members:
                            staff_members.append(member)
        else:
            async for shift in bot.shift_management.shifts.db.find(
                {"Guild": ctx.guild.id, "Type": shift_type["name"], "EndEpoch": 0}
            ):
                s = shift
                member = discord.utils.get(ctx.guild.members, id=shift["UserID"])
                if member:
                    if member not in staff_members:
                        staff_members.append(member)

        for member in staff_members:
            sh = await bot.shift_management.get_current_shift(member, ctx.guild.id)

            time_delta = datetime.timedelta(seconds=get_elapsed_time(sh))

            break_seconds = 0
            if "Breaks" in sh.keys():
                for item in sh["Breaks"]:
                    if item["EndEpoch"] == 0:
                        break_seconds += (
                            ctx.message.created_at.replace(tzinfo=pytz.UTC).timestamp()
                            - item["StartEpoch"]
                        )


            all_staff.append(
                {
                    "id": sh["UserID"],
                    "total_seconds": time_delta.total_seconds(),
                    "break_seconds": break_seconds,
                }
            )

        sorted_staff = sorted(all_staff, key=lambda x: x["total_seconds"], reverse=True)
        added_staff = []
        for index, staff in enumerate(sorted_staff):
            # print(staff)
            member = discord.utils.get(ctx.guild.members, id=staff["id"])
            if not member:
                continue

            if (
                len((embeds[-1].description or "").splitlines()) >= 16
                and ctx.author.id not in added_staff
            ):
                embed = discord.Embed(
                    title="Active Shifts", color=BLANK_COLOR
                )
                embed.description = f"**Total Shifts**"
                embed.set_author(
                    name=f"{ctx.guild.name}",
                    icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
                )
                added_staff.append(member.id)
                embeds.append(embed)
            if member.id not in added_staff:
                embeds[
                    -1
                ].description += f"\n**{index+1}.** {member.mention} • {td_format(datetime.timedelta(seconds=staff['total_seconds']))}{(' **(Currently on break: {})**'.format(td_format(datetime.timedelta(seconds=staff['break_seconds'])))) if staff['break_seconds'] > 0 else ''}"


        paginator = SelectPagination(ctx.author.id, [CustomPage(embeds=[embed], identifier=str(index+1)) for index, embed in enumerate(embeds)])


        if len(embeds) == 1:
            if embeds[0].description == "**Total Shifts**":
                try:
                    return await msg.edit(
                        embed=discord.Embed(
                            title="No Active Shifts",
                            description="No active shifts have been found in this server.",
                            color=BLANK_COLOR
                        )
                    )
                except UnboundLocalError:
                    return await ctx.send(
                        embed=discord.Embed(
                            title="No Active Shifts",
                            description="No active shifts have been found in this server.",
                            color=BLANK_COLOR
                        )
                    )
            try:
                return await msg.edit(
                    embed=embed,
                    view=None
                )
            except UnboundLocalError:
                return await ctx.reply(embed=embed)
        try:
            await msg.edit(embed=embeds[0], view=paginator.get_current_view())
        except UnboundLocalError:
            await ctx.reply(embed=embeds[0], view=paginator.get_current_view())

    @duty.command(
        name="leaderboard",
        description="Get the total time worked for the whole of the staff team.",
        extras={"category": "Shift Management"},
        aliases=["lb"],
    )
    @require_settings()
    @is_staff()
    async def shift_leaderboard(self, ctx):
        if self.bot.shift_management_disabled is True:
            return await new_failure_embed(
                ctx,
                "Maintenance",
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem.get('shift_management', {}).get('enabled', False):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Shift Logging is not enabled on this server."
                )
            )


        shift_type = None
        if configItem.get("shift_types"):
            shift_types = configItem.get("shift_types")
            if shift_types.get("enabled") is True:
                if len(shift_types.get("types")) > 1:
                    shift_types = shift_types.get("types")

                    view = CustomSelectMenu(
                        ctx.author.id,
                        [
                            discord.SelectOption(
                                label=i["name"],
                                value=i["id"],
                                description=i["name"],
                            )
                            for i in shift_types
                        ]
                        + [
                            discord.SelectOption(
                                label="All",
                                value="all",
                                description="Data from all shift types",
                            )
                        ],
                    )

                    msg = await ctx.reply(
                        embed=discord.Embed(
                            title="Shift Types",
                            description=f"You have **{len(shift_types)}** shift types. Which ones would you like to see?",
                            color=BLANK_COLOR
                        ),
                        view=view
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value:
                        if view.value == "all":
                            shift_type = 0
                        else:
                            shift_type = view.value
                            shift_list = [
                                i for i in shift_types if i["id"] == int(shift_type)
                            ]
                            if shift_list:
                                shift_type = shift_list[0]
                            else:
                                return await new_failure_embed(
                                    ctx,
                                    "Critical Error",
                                    "if you somehow encounter this error, please contact [ERM Support](https://discord.gg/FAC629TzBy)",
                                )

        all_staff = [{"id": None, "total_seconds": 0}]

        if shift_type != 0 and shift_type is not None:
            async for document in bot.shift_management.shifts.db.find(
                {
                    "Guild": ctx.guild.id,
                    "Type": shift_type["name"],
                    "EndEpoch": {"$ne": 0},
                }
            ):
                total_seconds = 0
                moderations = 0
                if "Moderations" in document.keys():
                    moderations += len(document["Moderations"])

                break_seconds = 0

                total_seconds += get_elapsed_time(document)

                if document["UserID"] not in [item["id"] for item in all_staff]:
                    all_staff.append(
                        {
                            "id": document["UserID"],
                            "total_seconds": total_seconds,
                            "moderations": moderations,
                        }
                    )
                else:
                    for item in all_staff:
                        if item["id"] == document["UserID"]:
                            item["total_seconds"] += total_seconds
                            item["moderations"] += moderations
        else:
            async for document in bot.shift_management.shifts.db.find(
                {
                    "Guild": ctx.guild.id,
                    "EndEpoch": {"$ne": 0},
                }
            ):
                total_seconds = 0
                moderations = 0
                break_seconds = 0

                for breaks in document["Breaks"]:
                    break_seconds += int(breaks["EndEpoch"]) - int(breaks["StartEpoch"])

                if "Moderations" in document.keys():
                    moderations += len(document["Moderations"])
                # print(document)
                total_seconds += (
                    get_elapsed_time(document)
                )
                # print(total_seconds)
                if document["UserID"] not in [item["id"] for item in all_staff]:
                    all_staff.append(
                        {
                            "id": document["UserID"],
                            "total_seconds": total_seconds,
                            "moderations": moderations,
                        }
                    )
                else:
                    for item in all_staff:
                        if item["id"] == document["UserID"]:
                            item["total_seconds"] += total_seconds
                            item["moderations"] += moderations

        if len(all_staff) == 0:
            return await ctx.send(
                embed=discord.Embed(
                    title="No Shifts",
                    description="No shifts have been found in this server.",
                    color=BLANK_COLOR
                )
            )

        for item in all_staff:
            if item["id"] is None:
                all_staff.remove(item)

        sorted_staff = sorted(all_staff, key=lambda x: x["total_seconds"], reverse=True)

        buffer = None
        embeds = []

        embed = discord.Embed(
            color=BLANK_COLOR, title="Shift Leaderboard"
        )
        embed.set_author(
            name=f"{ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
        )


        embeds.append(embed)
        # print(sorted_staff)
        data = []
        if not sorted_staff:
            if shift_type != 0 and shift_type is not None:
                return await ctx.send(
                    embed=discord.Embed(
                        title="No Shifts",
                        description="No shifts have been found in this server for this Shift Type.",
                        color=BLANK_COLOR
                    )
                )
            else:
                return await ctx.send(
                    embed=discord.Embed(
                        title="No Shifts",
                        description="No shifts have been found in this server.",
                        color=BLANK_COLOR
                    )
                )


        my_data = None

        for index, i in enumerate(sorted_staff):
            try:
                member = await ctx.guild.fetch_member(i["id"])
            except:
                member = None
            # print(index)
            # print(i)
            # print(member)
            if member:
                if member.id == ctx.author.id:
                    i["index"] = index
                    my_data = i

                if buffer is None:
                    # print("buffer none")
                    buffer = "%s - %s" % (
                        f"{member.name}",
                        td_format(datetime.timedelta(seconds=i["total_seconds"])),
                    )
                    data.append(
                        [
                            index + 1,
                            f"{member.name}",
                            member.top_role.name,
                            td_format(datetime.timedelta(seconds=i["total_seconds"])),
                            i["moderations"],
                        ]
                    )
                else:
                    # print("buffer not none")
                    buffer = buffer + "\n%s - %s" % (
                        f"{member.name}",
                        td_format(datetime.timedelta(seconds=i["total_seconds"])),
                    )
                    data.append(
                        [
                            index + 1,
                            f"{member.name}",
                            member.top_role.name,
                            td_format(datetime.timedelta(seconds=i["total_seconds"])),
                            i["moderations"],
                        ]
                    )

                if len((embeds[-1].description or "").splitlines()) < 16:
                    if embeds[-1].description is None:
                        embeds[
                            -1
                        ].description = f"**Total Shifts**\n**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
                    else:
                        embeds[
                            -1
                        ].description += f"**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"

                else:
                    # print("fields more than 24")
                    new_embed = discord.Embed(
                        color=BLANK_COLOR, title="Shift Leaderboard"
                    )

                    new_embed.set_author(
                        name=f"{ctx.guild.name}",
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
                    )
                    new_embed.description = ""
                    new_embed.description += f"**Total Shifts**\n**{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
                    embeds.append(new_embed)

        staff_roles = []
        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )  # NOQA: E731
        ordinal_formatted = None
        quota_seconds = 0

        if configItem["staff_management"].get("role"):
            if isinstance(configItem["staff_management"]["role"], int):
                staff_roles.append(configItem["staff_management"]["role"])
            elif isinstance(configItem["staff_management"]["role"], list):
                for role in configItem["staff_management"]["role"]:
                    staff_roles.append(role)

        if configItem["staff_management"].get("management_role"):
            if isinstance(configItem["staff_management"]["management_role"], int):
                staff_roles.append(configItem["staff_management"]["management_role"])
            elif isinstance(configItem["staff_management"]["management_role"], list):
                for role in configItem["staff_management"]["management_role"]:
                    staff_roles.append(role)
        staff_roles = [ctx.guild.get_role(role) for role in staff_roles]
        added_staff = []

        for role in staff_roles.copy():
            if role is None:
                staff_roles.remove(role)

        for role in staff_roles:
            if role.members:
                for member in role.members:
                    if member.id not in [item["id"] for item in sorted_staff]:
                        if member not in added_staff:
                            index = index + 1

                            if buffer is None:
                                buffer = "%s - %s" % (
                                    f"{member.name}",
                                    "0 seconds",
                                )
                                data.append(
                                    [
                                        index,
                                        f"{member.name}",
                                        member.top_role.name,
                                        "0 seconds",
                                        0,
                                    ]
                                )
                                added_staff.append(member)
                            else:
                                buffer = buffer + "\n%s - %s" % (
                                    f"{member.name}",
                                    "0 seconds",
                                )
                                data.append(
                                    [
                                        index,
                                        f"{member.name}",
                                        member.top_role.name,
                                        "0 seconds",
                                        0,
                                    ]
                                )
                                added_staff.append(member)

                            if len((embeds[-1].description or "").splitlines()) < 16:
                                if embeds[-1].description is None:
                                    embeds[
                                        -1
                                    ].description = f"**Total Shifts**\n**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=0))}\n"
                                else:
                                    embeds[
                                        -1
                                    ].description += f"**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=0))}\n"

                            else:
                                # print("fields more than 24")
                                new_embed = discord.Embed(
                                    color=BLANK_COLOR, title="Shift Leaderboard"
                                )

                                new_embed.set_author(
                                    name=f"{ctx.guild.name}",
                                    icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
                                )
                                new_embed.description = ""
                                new_embed.description += f"**Total Shifts**\n**{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=0))}\n"
                                embeds.append(new_embed)
        perm_staff = list(
            filter(
                lambda m: (
                    m.guild_permissions.manage_messages
                    or m.guild_permissions.manage_guild
                )
                and not m.bot,
                ctx.guild.members,
            )
        )
        for member in perm_staff:
            if member.id not in [item["id"] for item in sorted_staff]:
                if member not in added_staff:
                    index = index + 1

                    if buffer is None:
                        buffer = "%s - %s" % (
                            f"{member.name}",
                            "0 seconds",
                        )
                        data.append(
                            [
                                index + 1,
                                f"{member.name}",
                                member.top_role.name,
                                "0 seconds",
                                0,
                            ]
                        )
                        added_staff.append(member)

                    else:
                        buffer = buffer + "\n%s - %s" % (
                            f"{member.name}",
                            "0 seconds",
                        )
                        data.append(
                            [
                                index + 1,
                                f"{member.name}",
                                member.top_role.name,
                                "0 seconds",
                                0,
                            ]
                        )
                        added_staff.append(member)

                    if len((embeds[-1].description or "").splitlines()) < 16:
                        if embeds[-1].description is None:
                            embeds[
                                -1
                            ].description = f"**Total Shifts**\n**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=0))}\n"
                        else:
                            embeds[
                                -1
                            ].description += f"**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=0))}\n"

                    else:
                        # print("fields more than 24")
                        new_embed = discord.Embed(
                            color=BLANK_COLOR, title="Shift Leaderboard"
                        )

                        new_embed.set_author(
                            name=f"{ctx.guild.name}",
                            icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
                        )
                        new_embed.description = ""
                        new_embed.description += f"**Total Shifts**\n**{index + 1}.** {member.mention} • {td_format(datetime.timedelta(seconds=0))}\n"
                        embeds.append(new_embed)

        combined = []
        for list_item in data:
            for item in list_item:
                combined.append(item)

        bbytes = buffer.encode("utf-8", "ignore")

        if len(embeds) == 1:
            new_embeds = []
            for i in embeds:
                new_embeds.append(i)
            if await management_predicate(ctx):
                view = RequestGoogleSpreadsheet(
                    ctx.author.id,
                    credentials_dict,
                    scope,
                    combined,
                    config("DUTY_LEADERBOARD_ID"),
                )
            else:
                view = None
            await ctx.reply(
                embeds=new_embeds,
                file=discord.File(fp=BytesIO(bbytes), filename="shift_leaderboard.txt"),
                view=view
            )
        else:
            if await management_predicate(ctx):
                view = RequestGoogleSpreadsheet(
                    ctx.author.id,
                    credentials_dict,
                    scope,
                    combined,
                    config("DUTY_LEADERBOARD_ID"),
                )
            else:
                view = None

            async def response_func(
                interaction: discord.Interaction, button: discord.Button
            ):
                file = discord.File(fp=BytesIO(bbytes), filename="shift_leaderboard.txt")
                await interaction.response.send_message(file=file, ephemeral=True)

            if view:
                view.add_item(CustomExecutionButton(
                    ctx.author.id,
                    "Download Shift Leaderboard",
                    discord.ButtonStyle.gray,
                    emoji=None,
                    func=response_func
                ))

            pages = [CustomPage(embeds=[embed], view=view, identifier=str(index+1)) for index, embed in enumerate(embeds)]
            menu = SelectPagination(ctx.author.id, pages)


            if len(menu.pages) == 1:
                try:
                    return await msg.edit(
                        embed=embed,
                        view=view
                    )
                except UnboundLocalError:
                    return await ctx.reply(
                        embed=embed,
                        view=view
                    )

            view_page = menu.get_current_view()
            try:
                menu.message = await msg.edit(
                    embed=embeds[0],
                    view=view_page
                )
            except UnboundLocalError:
                menu.message = await ctx.reply(
                    embed=embeds[0],
                    view=view_page
                )



async def setup(bot):
    await bot.add_cog(ShiftLogging(bot))
