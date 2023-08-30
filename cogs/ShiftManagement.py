import asyncio
import copy
import datetime
from io import BytesIO
from utils.flags import DutyManageOptions
import discord
import num2words
import pytz
from decouple import config
from discord.ext import commands
from reactionmenu import Page, ViewButton, ViewMenu, ViewSelect
from reactionmenu.abc import _PageController

from erm import credentials_dict, is_management, is_staff, management_predicate, scope
from menus import (
    AdministrativeSelectMenu,
    CustomExecutionButton,
    CustomSelectMenu,
    ModificationSelectMenu,
    RequestGoogleSpreadsheet,
    YesNoMenu,
    CustomModalView,
)
from utils.timestamp import td_format
from utils.utils import failure_embed, request_response, failure_embed, end_break, get_elapsed_time


class ShiftManagement(commands.Cog):
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
    async def dutytime(self, ctx, member: discord.Member = None):
        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        if not member:
            member = ctx.author

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await failure_embed(
                ctx,
                "the server has not been set up yet. Please run `/setup` to set up the server.",
            )

        if not configItem["shift_management"]["enabled"]:
            return await failure_embed(
                ctx, "shift management is not enabled on this server."
            )
        try:
            shift_channel = discord.utils.get(
                ctx.guild.channels, id=configItem["shift_management"]["channel"]
            )
        except:
            return await failure_embed(
                ctx,
                f'some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.',
            )

        if not configItem["shift_management"]["enabled"]:
            return await failure_embed(
                ctx, "shift management is not enabled on this server."
            )

        embed = discord.Embed(
            title=f"<:ERMSchedule:1111091306089939054> {member.name}",
            color=0xED4348,
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

        try:
            if shift:
                embed.add_field(
                    name="<:ERMActivity:1113209176664064060> Current Shift Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=get_elapsed_time(shift)))}",
                    inline=False,
                )
        except:
            if shift:
                embed.add_field(
                    name="<:ERMActivity:1113209176664064060> Current Shift Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Could not display current shift time.",
                    inline=False,
                )

        embed.add_field(
            name="<:ERMMisc:1113215605424795648> Total Shift Time",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=total_seconds))}",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(icon_url=ctx.author.display_avatar.url, name=ctx.author.name)
        await ctx.reply(
            embed=embed,
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, the user **{member.name}** has logged a total of **{td_format(datetime.timedelta(seconds=total_seconds))}**.",
        )

    @duty.command(
        name="quota",
        description="Checks if you have completed the quota",
        extras={"category": "Shift Management", "ephemeral": True},
    )
    @is_staff()
    async def duty_quota(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author

        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await failure_embed(
                ctx,
                "this server is not setup! Run `/setup` to setup the bot.",
            )

        if not configItem["shift_management"]["enabled"]:
            return await failure_embed(
                ctx, "shift management is not enabled on this server."
            )

        if not configItem["shift_management"].get("quota"):
            return await ctx.send(
                f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, this server **does not** have a quota."
            )

        shifts = [
            i
            async for i in bot.shift_management.shifts.db.find(
                {"UserID": member.id, "Guild": ctx.guild.id}
            )
        ]

        for i in shifts:
            if i["EndEpoch"] == 0:
                i["EndEpoch"] = int(datetime.datetime.now(tz=pytz.UTC).timestamp())

        total_seconds = sum(
            [
                get_elapsed_time(i)
                for i in shifts
            ]
        )

        quota_formatted = td_format(
            datetime.timedelta(seconds=configItem["shift_management"]["quota"])
        )

        if total_seconds >= configItem["shift_management"]["quota"]:
            if member != ctx.author:
                return await ctx.send(
                    f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, **{member.name}** has completed the quota!"
                )
            else:
                return await ctx.send(
                    f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, you have completed the quota!"
                )

        else:
            met_quota_formatted = td_format(
                datetime.timedelta(
                    seconds=configItem["shift_management"]["quota"] - total_seconds
                )
            )
            if member != ctx.author:
                return await ctx.send(
                    f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, **{member.name}** has **not met** the quota! They need **{met_quota_formatted}** more."
                )
            else:
                return await ctx.send(
                    f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, you have **not met** the quota. You need **{met_quota_formatted}** more."
                )

    @duty.command(
        name="admin",
        description="Allows for you to administrate someone else's shift",
        extras={"category": "Shift Management"},
    )
    @is_management()
    async def duty_admin(self, ctx, member: discord.Member):
        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await failure_embed(
                ctx,
                "this server is not setup! Run `/setup` to setup the bot.",
            )

        try:
            shift_channel = discord.utils.get(
                ctx.guild.channels, id=configItem["shift_management"]["channel"]
            )
        except:
            return await failure_embed(
                ctx,
                f'some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.',
            )

        if not configItem["shift_management"]["enabled"]:
            return await failure_embed(
                ctx, "shift management is not enabled on this server."
            )

        shift = None
        shift = await bot.shift_management.get_current_shift(member, ctx.guild.id)
        has_started = shift is not None

       # # print(shift)
        view = AdministrativeSelectMenu(ctx.author.id)

        embed = discord.Embed(
            color=0xED4348,
            title=f"<:ERMAdmin:1111100635736187011> {member.name}",
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            icon_url=ctx.author.display_avatar.url, name=ctx.author.name
        )

        quota_seconds = None
        met_quota = None
        member_seconds = 0
        ordinal_place = None
        ordinal_formatted = None
        shift_type = None

        if "quota" in configItem["shift_management"].keys():
            quota_seconds = configItem["shift_management"]["quota"]

        all_staff = [{"id": None, "total_seconds": 0, "quota_seconds": 0}]

        datetime_obj = datetime.datetime.now(tz=pytz.UTC)
        ending_period = datetime_obj
        starting_period = datetime_obj - datetime.timedelta(days=7)

        async for document in bot.shift_management.shifts.db.find(
            {
                "Guild": ctx.guild.id,
                "EndEpoch": {"$ne": 0},
            }
        ):
            total_seconds = get_elapsed_time(document)

            if document["EndEpoch"] > starting_period.timestamp():
                quota_seconds = total_seconds
            else:
                quota_seconds = 0

            if document["EndEpoch"] != 0:
                if document["UserID"] not in [item["id"] for item in all_staff]:
                    all_staff.append(
                        {
                            "id": document["UserID"],
                            "total_seconds": total_seconds,
                            "quota_seconds": quota_seconds,
                        }
                    )
                else:
                    for item in all_staff:
                        if item["id"] == document["_id"]:
                            item["total_seconds"] += total_seconds
                            item["quota_seconds"] += quota_seconds

        if len(all_staff) == 0:
            return await failure_embed(ctx, "no shifts were made in your server.")
        for item in all_staff:
            if item["id"] is None:
                all_staff.remove(item)

        sorted_staff = sorted(all_staff, key=lambda x: x["total_seconds"], reverse=True)

        for index, value in enumerate(sorted_staff):
            m = discord.utils.get(ctx.guild.members, id=value["id"])
           # # print(m)
            if m:
                if m.id == member.id:
                   # # print("member seconds")
                    member_seconds = value["total_seconds"]
                    if quota_seconds is not None:
                        if value["total_seconds"] > quota_seconds:
                            met_quota = "Met "
                        else:
                            met_quota = "Not met"
                        ordinal_place = index + 1
                    else:
                        met_quota = "Not met"
                        ordinal_place = index + 1

        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )  # NOQA: E731
        ms_delta = datetime.timedelta(seconds=member_seconds)

        if ordinal_place is not None:
            ordinal_formatted = ordinal(ordinal_place)

        if td_format(ms_delta) != "":
            embed.add_field(
                name="<:ERMSync:1113209904979771494> Previous Shift Data",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** {td_format(ms_delta)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Quota:** {met_quota}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Rank:** {ordinal_formatted}",
                inline=False,
            )
        status = None

       # # print(shift)
        if shift not in [None, []]:
            if shift.get("Breaks") is not None:
                for i in shift["Breaks"]:
                    if i["EndEpoch"] == 0:
                        status = "break"
                        break
            if status != "break":
                status = "on"
        else:
            status = "off"

        embed.add_field(
            name="<:ERMLog:1113210855891423302> Shift Management",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **On-Duty** {'(Current)' if status == 'on' else ''}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **On-Break** {'(Current)' if status == 'break' else ''}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Off-Duty** {'(Current)' if status == 'off' else ''}",
        )

        doc = [
            i
            async for i in bot.shift_management.shifts.db.find(
                {"Guild": ctx.guild.id, "EndEpoch": 0}
            )
        ]
        currently_active = len(doc)

        if status == "on" or status == "break":
            warnings = 0
            kicks = 0
            bans = 0
            ban_bolos = 0
            custom = 0
            if "Moderations" in shift.keys():
                for item in shift["Moderations"]:
                    warning_item = await bot.punishments.find_warning_by_spec(
                        ctx.guild.id,
                        identifier=item,
                    )
                    if warning_item:
                        if warning_item["Type"] == "Warning":
                            warnings += 1
                        elif warning_item["Type"] == "Kick":
                            kicks += 1
                        elif (
                            warning_item["Type"] == "Ban"
                            or warning_item["Type"] == "Temporary Ban"
                        ):
                            bans += 1
                        elif warning_item["Type"].upper() == "BOLO":
                            ban_bolos += 1

            raw_shift_type: str = shift["Type"]
            settings = await bot.settings.find_by_id(ctx.guild.id)
            shift_types = settings.get("shift_types")
            shift_types = (
                shift_types.get("types")
                if (shift_types or {}).get("types") not in [None, []]
                else []
            )
            if shift_types:
                sh_typelist = [
                    item for item in shift_types if item["name"] == raw_shift_type
                ]
                if len(sh_typelist) > 0:
                    shift_type = sh_typelist[0]
                else:
                    shift_type = {
                        "name": "Unknown",
                        "id": 0,
                        "role": settings["shift_management"].get("role"),
                    }
            else:
                shift_type = {
                    "name": "Default",
                    "id": 0,
                    "role": settings["shift_management"].get("role"),
                }

            if shift_type:
                if shift_type.get("channel"):
                    temp_shift_channel = discord.utils.get(
                        ctx.guild.channels, id=shift_type.get("channel")
                    )
                    if temp_shift_channel:
                        shift_channel = temp_shift_channel

           # # print(datetime.datetime.fromtimestamp(shift["StartEpoch"], tz=pytz.UTC))
            time_delta = datetime.timedelta(seconds=get_elapsed_time(shift))

            embed2 = discord.Embed(
                title=f"<:ERMActivity:1113209176664064060> Current Shift",
                color=0xED4348,
            )

            embed2.add_field(
                name="<:ERMPunish:1111095942075138158> Moderation Details",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Warnings:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Kicks:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Bans:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**BOLOs:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Custom:** {}".format(
                    warnings, kicks, bans, ban_bolos, custom
                ),
                inline=False,
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_author(
                icon_url=ctx.author.display_avatar.url, name=ctx.author.name
            )

            break_seconds = 0
            if "Breaks" in shift.keys():
                for item in shift["Breaks"]:
                    if item["EndEpoch"] != 0:
                        break_seconds += item["EndEpoch"] - item["StartEpoch"]
                    else:
                        break_seconds += (
                            datetime.datetime.now(tz=pytz.UTC).timestamp()
                            - item["StartEpoch"]
                        )

            break_seconds = int(break_seconds)

            doc = [
                doc
                async for doc in bot.shift_management.shifts.db.find(
                    {"Guild": ctx.guild.id, "EndEpoch": 0}
                )
            ]
            currently_active = len(doc)

            if shift_type:
                embed2.add_field(
                    name="<:ERMList:1111099396990435428> Shift Status",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{'**On-Duty**' if status == 'on' else '**On-Break**'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** {td_format(time_delta)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Breaks:** {len(shift['breaks']) if 'breaks' in shift.keys() else '0'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time on Break:** {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Current Shift Type:** {shift_type['name']}",
                )
            else:
                embed2.add_field(
                    name="<:ERMList:1111099396990435428> Shift Status",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{'**On-Duty**' if status == 'on' else '**On-Break**'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** {td_format(time_delta)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Breaks:** {len(shift['breaks']) if 'breaks' in shift.keys() else '0'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time on Break:** {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Current Shift Type:** Default",
                )

            embed2.set_footer(text=f"Currently online staff: {currently_active}")
            msg = await ctx.reply(
                embeds=[embed, embed2],
                view=view,
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you're viewing **{member.name}'s** Admin Panel",
            )
        else:
            embed.set_footer(text=f"Currently online staff: {currently_active}")
            msg = await ctx.reply(
                embed=embed,
                view=view,
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you're viewing **{member.name}'s** Admin Panel",
            )
        timeout = await view.wait()
        if timeout:
            new_view = copy.copy(view)
            new_view.clear_items()
            new_view.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label="You didn't respond in time!",
                    disabled=True,
                )
            )
            return await msg.edit(view=new_view)

        if view.value == "on":
            if status == "on":
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223> **{ctx.author.name}**, the user **{member.name}** is already on-duty. You can force them off-duty by selecting **Off-Duty**.",
                    embed=None,
                )
            elif status == "break":
                await end_break(
                    bot, shift, shift_type, configItem, ctx, msg, member, manage=False
                )
            else:
                settings = await bot.settings.find_by_id(ctx.guild.id)
                shift_type = None
                nickname_prefix = None

                maximum_staff = settings["shift_management"].get("maximum_staff")
                if maximum_staff not in [None, 0]:
                    if (currently_active + 1) > maximum_staff:
                        return await failure_embed(
                            ctx,
                            f"the maximum amount of staff that can be on-duty at once is **{maximum_staff}**. Ask your server administration for more details.",
                        )

                if settings.get("shift_types"):
                    if (
                        len(settings["shift_types"].get("types") or []) > 1
                        and settings["shift_types"].get("enabled") is True
                    ):
                        shift_types = settings["shift_types"]["types"]
                        v = CustomSelectMenu(
                            ctx.author.id,
                            [
                                discord.SelectOption(
                                    label=item["name"],
                                    value=item["id"],
                                    description=item["name"],
                                )
                                for item in settings["shift_types"]["types"]
                            ],
                        )
                        await msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you have {num2words.num2words(len(shift_types))} shift types - {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select which one you want to use.",
                            embed=None,
                            view=v,
                        )
                        timeout = await v.wait()
                        if timeout:
                            return
                        if v.value:
                            shift_type = [
                                item
                                for item in settings["shift_types"]["types"]
                                if item["id"] == int(v.value)
                            ]
                            if len(shift_type) == 1:
                                shift_type = shift_type[0]
                            else:
                                return await failure_embed(
                                    ctx,
                                    "something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).",
                                )
                        else:
                            return
                    else:
                        if (
                            settings["shift_types"].get("enabled") is True
                            and len(settings["shift_types"].get("types")) > 0
                        ):
                            shift_type = settings["shift_types"]["types"][0]
                        else:
                            shift_type = None
                            nickname_prefix = None
                            changed_nick = False

                if shift_type:
                    if shift_type.get("nickname"):
                        nickname_prefix = shift_type.get("nickname")
                else:
                    if configItem["shift_management"].get("nickname_prefix"):
                        nickname_prefix = configItem["shift_management"].get(
                            "nickname_prefix"
                        )

                old_shift_type = None
                shift_type_item = None
                if shift_type:
                    old_shift_type = shift_type
                    shift_type = shift_type["name"]
                else:
                    shift_type = "Default"
                if nickname_prefix:
                    current_name = member.nick if member.nick else member.name
                    new_name = "{}{}".format(nickname_prefix, current_name)

                    try:
                        await member.edit(nick=new_name)
                        changed_nick = True
                    except Exception as e:
                        ## print(e)
                        pass

                await bot.shift_management.add_shift_by_user(
                    member, shift_type, [], ctx.guild.id
                )

                role = None

                if old_shift_type:
                    # if old_shift_type:
                    #     shift_type = old_shift_type
                    if old_shift_type.get("role"):
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in old_shift_type.get("role")
                        ]
                else:
                    if configItem["shift_management"]["role"]:
                        if not isinstance(configItem["shift_management"]["role"], list):
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles,
                                    id=configItem["shift_management"]["role"],
                                )
                            ]
                        else:
                            role = [
                                discord.utils.get(ctx.guild.roles, id=role)
                                for role in configItem["shift_management"]["role"]
                            ]

                if role:
                    for rl in role:
                        if not rl in member.roles and rl is not None:
                            try:
                                await member.add_roles(rl)
                            except:
                                await failure_embed(
                                    ctx, f"could not add {rl} to {member.mention}"
                                )

                embed = discord.Embed(
                    title=f"<:ERMAdd:1113207792854106173> Shift Logged", color=0xED4348
                )
                try:
                    embed.set_thumbnail(url=ctx.author.display_avatar.url)
                    embed.set_author(
                        icon_url=ctx.author.display_avatar.url, name=ctx.author.name
                    )
                    embed.set_footer(text="Staff Logging Module")
                except:
                    pass

                if shift_type != "Default":
                    embed.add_field(
                        name="<:ERMList:1111099396990435428> Type",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking in. **({shift_type.get('name')})**",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="<:ERMList:1111099396990435428> Type",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking in.",
                        inline=False,
                    )
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Current Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(ctx.message.created_at.timestamp())}>",
                    inline=False,
                )

                if shift_channel is None:
                    return

                await shift_channel.send(embed=embed)
                await msg.edit(
                    embed=None,
                    view=None,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've started **{member.name}**'s shift.",
                )
        elif view.value == "off":
            break_seconds = 0
            shift = await bot.shift_management.get_current_shift(member, ctx.guild.id)
            if shift:
                if shift["Guild"] != ctx.guild.id:
                    shift = None

                if shift:
                    for index, item in enumerate(shift["Breaks"].copy()):
                        if item["EndEpoch"] == 0:
                            item["EndEpoch"] = ctx.message.created_at.timestamp()
                            shift["Breaks"][index] = item

                        startTimestamp = item["StartEpoch"]
                        endTimestamp = item["EndEpoch"]
                        break_seconds += int(endTimestamp - startTimestamp)
            else:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223> **{ctx.author.name}**, the user **{member.name}** is not on-duty. You can force them on-duty by selecting **On-Duty**.",
                    embed=None,
                )
            if status == "off":
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223> **{ctx.author.name}**, the user **{member.name}** is not on-duty. You can force them on-duty by selecting **On-Duty**.",
                    embed=None,
                )

            if shift.get("Nickname"):
                if shift.get("Nickname") == member.nick:
                    nickname = None
                    if shift.get("Type") is not None:
                        settings = await bot.settings.get_settings(ctx.guild.id)
                        shift_types = None
                        if settings.get("shift_types"):
                            shift_types = settings["shift_types"].get("types", [])
                        else:
                            shift_types = []
                        for s in shift_types:
                            if s["name"] == shift.get("Type"):
                                shift_type = s
                                nickname = s["nickname"] if s.get("nickname") else None
                    if nickname is None:
                        nickname = settings["shift_management"].get(
                            "nickname_prefix", ""
                        )
                    try:
                        await member.edit(nick=member.nick.replace(nickname, ""))
                    except Exception as e:
                        ## print(e)
                        pass

            embed = discord.Embed(
                title=f"<:ERMRemove:1113207777662345387> Shift Ended", color=0xED4348
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )

            if shift.get("Type") != "Default":
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Type",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking out. **({shift_type.get('name')})**",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Type",
                    value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking out.",
                    inline=False,
                )

            time_delta = ctx.message.created_at - datetime.datetime.fromtimestamp(
                shift["StartEpoch"], tz=pytz.UTC
            )



            added_seconds = 0
            removed_seconds = 0
            if "AddedTime" in shift.keys():
                added_seconds = shift["AddedTime"]
            if "RemovedTime" in shift.keys():
                removed_seconds = shift["RemovedTime"]

            if break_seconds > 0:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Type",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)} **({td_format(datetime.timedelta(seconds=break_seconds))})** on break",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Elapsed Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)}",
                    inline=False,
                )

            await msg.edit(
                embed=None,
                view=None,
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've ended **{member.name}**'s shift.",
            )

            if shift_channel is None:
                return

            await shift_channel.send(embed=embed)

            embed = discord.Embed(
                title="<:ERMActivity:1113209176664064060> Shift Report",
                color=0xED4348,
            )

            mods = shift.get("Moderations") if shift.get("Moderations") else []
            all_moderation_items = [
                await bot.punishments.find_warning_by_spec(
                    ctx.guild.id, identifier=moderation
                )
                for moderation in mods
            ]
            moderations = len(all_moderation_items)

            embed.set_author(
                name=f"You have made {moderations} moderations during your shift.",
                icon_url=ctx.author.display_avatar.url,
            )

            embed.add_field(
                name="<:ERMMisc:1113215605424795648> Elapsed Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)} **({td_format(datetime.timedelta(seconds=break_seconds))} on break)**",
                inline=False,
            )

            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0
            custom = 0

            for moderation in all_moderation_items:
                if moderation is None:
                    continue
                if moderation["Type"] == "Warning":
                    warnings += 1
                elif moderation["Type"] == "Kick":
                    kicks += 1
                elif moderation["Type"] == "Ban":
                    bans += 1
                elif moderation["Type"] == "BOLO" or moderation["Type"] == "Bolo":
                    bolos += 1
                elif moderation["Type"] not in [
                    "Warning",
                    "Kick",
                    "Ban",
                    "BOLO",
                    "Bolo",
                ]:
                    custom += 1

            embed.add_field(
                name="<:ERMPunish:1111095942075138158> Total Moderations",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Warnings:** {warnings}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Kicks:** {kicks}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Bans:** {bans}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **BOLO:** {bolos}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Custom:** {custom}",
                inline=False,
            )
            dm_channel = await member.create_dm()
            # dm_msg = await dm_channel.send(
            #     embed=create_invis_embed(
            #         'Your Shift Report is being generated. Please wait up to 5 seconds for complete generation.')
            # )
            new_ctx = copy.copy(ctx)
            new_ctx.guild = None
            new_ctx.channel = dm_channel

            menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
            menu.add_page(embed)

            moderation_embed = discord.Embed(
                title="<:ERMActivity:1113209176664064060> Shift Report",
                color=0xED4348,
            )

            moderation_embed.set_author(
                name=f"You have made {moderations} moderations during your shift.",
                icon_url=ctx.author.display_avatar.url,
            )

            moderation_embeds = []
            moderation_embeds.append(moderation_embed)
            ## print("9867")

            for moderation in all_moderation_items:
                if moderation is not None:
                    if len(moderation_embeds[-1].fields) >= 10:
                        moderation_embeds.append(
                            discord.Embed(
                                title="<:ERMActivity:1113209176664064060> Shift Report",
                                color=0xED4348,
                            )
                        )

                        moderation_embeds[-1].set_author(
                            name=f"You have made {moderations} moderations during your shift.",
                            icon_url=ctx.author.display_avatar.url,
                        )

                    moderation_embeds[-1].add_field(
                        name=f"<:ERMList:1111099396990435428> {moderation['Type'].title()}",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **ID:** {moderation['Snowflake']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Type:** {moderation['Type']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Reason:** {moderation['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time:** <t:{int(moderation['Epoch'])}>",
                        inline=False,
                    )

            time_embed = discord.Embed(
                title="<:ERMActivity:1113209176664064060> Shift Report",
                color=0xED4348,
            )

            time_embed.set_author(
                name=f"You were on-shift for {td_format(time_delta)}.",
                icon_url=ctx.author.display_avatar.url,
            )
            ## print("9919")

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Shift Start",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(shift['StartEpoch'])}>",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Shift End",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(datetime.datetime.now(tz=pytz.UTC).timestamp())}>",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Added Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=added_seconds))}",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Removed Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=removed_seconds))}",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Total Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)}",
                inline=False,
            )

            menu.add_select(
                ViewSelect(
                    title="Shift Report",
                    options={
                        discord.SelectOption(
                            label="Moderations",
                            description="View all of your moderations during this shift",
                        ): [Page(embed=embed) for embed in moderation_embeds],
                        discord.SelectOption(
                            label="Shift Time",
                            description="View your shift time",
                        ): [Page(embed=time_embed)],
                    },
                )
            )

            menu.add_button(ViewButton.back())
            menu.add_button(ViewButton.next())
            consent_obj = await bot.consent.find_by_id(ctx.author.id)
            should_send = True
            if consent_obj:
                ## print(consent_obj)
                if consent_obj.get("shift_reports") is not None:
                    if consent_obj.get("shift_reports") is False:
                        should_send = False
            if should_send:
                try:
                    await menu.start()
                except:
                    pass

            ## print("9960")

            try:
                await bot.shift_management.end_shift(
                    identifier=shift["_id"], guild_id=ctx.guild.id
                )
            except ValueError as e:
                return await failure_embed(ctx, "shift not found. Could not end shift.")

            if shift.get("Nickname"):
                if shift.get("Nickname") == member.nick:
                    nickname = None
                    if shift.get("Type") is not None:
                        settings = await bot.settings.get_settings(ctx.guild.id)
                        if settings.get("shift_types"):
                            shift_types = settings["shift_types"].get("types", [])
                        else:
                            shift_types = []
                        for s in shift_types:
                            if s["name"] == shift.get("Type"):
                                shift_type = s
                                nickname = s["nickname"] if s.get("nickname") else None
                    if nickname is None:
                        nickname = settings["shift_management"].get(
                            "nickname_prefix", ""
                        )
                    try:
                        await member.edit(nick=member.nick.replace(nickname, ""))
                    except Exception as e:
                        # print(e)
                        pass
            role = None
            if shift_type:
                if shift_type.get("role"):
                    role = [
                        discord.utils.get(ctx.guild.roles, id=role)
                        for role in shift_type.get("role")
                    ]
            else:
                if configItem["shift_management"]["role"]:
                    if not isinstance(configItem["shift_management"]["role"], list):
                        role = [
                            discord.utils.get(
                                ctx.guild.roles,
                                id=configItem["shift_management"]["role"],
                            )
                        ]
                    else:
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in configItem["shift_management"]["role"]
                        ]

            if role:
                for rl in role:
                    if rl in member.roles and rl is not None:
                        try:
                            await member.remove_roles(rl)
                        except:
                            await failure_embed(
                                ctx, f"could not remove {rl} from {member.mention}"
                            )
        elif view.value == "break":
            if status == "off":
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, the user **{member.name}** cannot be on break if they are not currently on-duty. If you would like them to be on-duty, select **On-Duty**",
                    embed=None,
                )
            toggle = "on"
            role = None

            if "Breaks" in shift.keys():
                for item in shift["Breaks"]:
                    if item["EndEpoch"] == 0:
                        toggle = "off"

            if toggle == "on":
                if "Breaks" in shift.keys():
                    shift["Breaks"].append(
                        {
                            "StartEpoch": ctx.message.created_at.timestamp(),
                            "EndEpoch": 0,
                        }
                    )
                else:
                    shift["Breaks"] = [
                        {
                            "StartEpoch": ctx.message.created_at.timestamp(),
                            "EndEpoch": 0,
                        }
                    ]

                if shift.get("Nickname"):
                    if shift.get("Nickname") == member.nick:
                        nickname = None
                        if shift.get("Type") is not None:
                            settings = await bot.settings.get_settings(ctx.guild.id)
                            shift_types = None
                            if settings.get("shift_types"):
                                shift_types = settings["shift_types"].get("types", [])
                            else:
                                shift_types = []
                            for s in shift_types:
                                if s["name"] == shift.get("Type"):
                                    shift_type = s
                                    nickname = (
                                        s["nickname"] if s.get("nickname") else None
                                    )
                        if nickname is None:
                            nickname = settings["shift_management"].get(
                                "nickname_prefix", ""
                            )
                        try:
                            await member.edit(nick=member.nick.replace(nickname, ""))
                        except Exception as e:
                            # print(e)
                            pass

                await bot.shift_management.shifts.update_by_id(shift)

                await msg.edit(
                    embed=None,
                    view=None,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've started **{member.name}**'s break.",
                )

                if shift_type:
                    if shift_type.get("role"):
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in shift_type.get("role")
                        ]
                else:
                    if configItem["shift_management"]["role"]:
                        if not isinstance(configItem["shift_management"]["role"], list):
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles,
                                    id=configItem["shift_management"]["role"],
                                )
                            ]
                        else:
                            role = [
                                discord.utils.get(ctx.guild.roles, id=role)
                                for role in configItem["shift_management"]["role"]
                            ]

                if role:
                    for rl in role:
                        if rl in member.roles and rl is not None:
                            try:
                                await member.remove_roles(rl)
                            except:
                                await failure_embed(
                                    ctx, f"could not remove {rl} from {member.mention}"
                                )

            else:
                await end_break(
                    bot, shift, shift_type, configItem, ctx, msg, member, manage=False
                )
        if view.admin_value:
            if view.admin_value == "add":
                settings = await bot.settings.get_settings(ctx.guild.id)
                sh = await bot.shift_management.get_current_shift(member, ctx.guild.id)
                if not sh:
                    if settings.get("shift_types"):
                        if (
                            len(settings["shift_types"].get("types") or []) > 1
                            and settings["shift_types"].get("enabled") is True
                        ):
                            shift_types = settings["shift_types"]["types"]
                            v = CustomSelectMenu(
                                ctx.author.id,
                                [
                                    discord.SelectOption(
                                        label=item["name"],
                                        value=item["id"],
                                        description=item["name"],
                                    )
                                    for item in settings["shift_types"]["types"]
                                ],
                            )
                            msg = await ctx.reply(
                                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you have {num2words.num2words(len(shift_types))} shift types - {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select which one you want to use.",
                                view=v,
                                embed=None,
                            )
                            timeout = await v.wait()
                            if timeout:
                                return
                            if v.value:
                                shift_type = [
                                    item
                                    for item in settings["shift_types"]["types"]
                                    if item["id"] == int(v.value)
                                ]
                                if len(shift_type) == 1:
                                    shift_type = shift_type[0]
                                else:
                                    return await failure_embed(
                                        ctx,
                                        "something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).",
                                    )
                            else:
                                return
                        else:
                            if (
                                settings["shift_types"].get("enabled") is True
                                and len(settings["shift_types"].get("types")) > 0
                            ):
                                shift_type = settings["shift_types"]["types"][0]
                            else:
                                shift_type = None

                second_view = CustomModalView(
                    ctx.author.id,
                    "Add Time",
                    "Add Time",
                    [
                        (
                            "time",
                            discord.ui.TextInput(
                                label="Time (s/m/h/d)", placeholder="1s, 1m, 1h, 1d"
                            ),
                        )
                    ],
                )
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** how much time do you want to add?",
                    view=second_view,
                    embed=None,
                )
                timeout = await second_view.wait()
                if (not timeout) and second_view.modal.time.value:
                    content = second_view.modal.time.value
                else:
                    return await failure_embed(ctx, "you didn't provide a time!")

                content = content.strip()
                try:
                    if content.endswith(("s", "m", "h", "d")):
                        full = None
                        seconds = 0
                        if content.endswith("s"):
                            full = "seconds"
                            num = int(content[:-1])
                            seconds = num
                            # print("seconds")
                        if content.endswith("m"):
                            full = "minutes"
                            num = int(content[:-1])
                            seconds = num * 60
                            # print("minutes")
                        if content.endswith("h"):
                            full = "hours"
                            num = int(content[:-1])
                            seconds = num * 60 * 60

                            # print("hours")
                        if content.endswith("d"):
                            full = "days"
                            num = int(content[:-1])
                            seconds = num * 60 * 60 * 24

                            # print("days")
                    else:
                        return await failure_embed(ctx, "invalid time format. (e.g. 120m)")
                except:
                    return await failure_embed(ctx, "invalid time format. (e.g. 120m)")

                sh = await bot.shift_management.get_current_shift(member, ctx.guild.id)
                if sh:
                    await bot.shift_management.add_time_to_shift(sh["_id"], seconds)
                else:
                    shift_type_name = "Default"
                    if isinstance(shift_type, str):
                        shift_type_name = shift_type
                    elif isinstance(shift_type, dict):
                        shift_type_name = shift_type["name"]

                    try:
                        oid = await bot.shift_management.add_shift_by_user(
                            member, shift_type_name, [], ctx.guild.id
                        )
                        await bot.shift_management.add_time_to_shift(oid, seconds)
                        await bot.shift_management.end_shift(oid, ctx.guild.id)
                    except ValueError as e:
                        return await failure_embed(
                            ctx, "shift not found. Could not manipulate shift."
                        )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've added **{num} {full}** to **{member.display_name}**'s shift.",
                    view=None,
                )

            if view.admin_value == "remove":
                settings = await bot.settings.get_settings(ctx.guild.id)
                sh = await bot.shift_management.get_current_shift(member, ctx.guild.id)
                if not sh:
                    if settings.get("shift_types"):
                        if (
                            len(settings["shift_types"].get("types") or []) > 1
                            and settings["shift_types"].get("enabled") is True
                        ):
                            v = CustomSelectMenu(
                                ctx.author.id,
                                [
                                    discord.SelectOption(
                                        label=item["name"],
                                        value=item["id"],
                                        description=item["name"],
                                    )
                                    for item in settings["shift_types"]["types"]
                                ],
                            )
                            await msg.edit(embed=embed, view=v)
                            timeout = await v.wait()
                            if timeout:
                                return
                            if v.value:
                                shift_type = [
                                    item
                                    for item in settings["shift_types"]["types"]
                                    if item["id"] == int(v.value)
                                ]
                                if len(shift_type) == 1:
                                    shift_type = shift_type[0]
                                else:
                                    return await failure_embed(
                                        ctx,
                                        "something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).",
                                    )
                            else:
                                return
                        else:
                            if (
                                settings["shift_types"].get("enabled") is True
                                and len(settings["shift_types"].get("types")) > 0
                            ):
                                shift_type = settings["shift_types"]["types"][0]
                            else:
                                shift_type = None

                second_view = CustomModalView(
                    ctx.author.id,
                    "Remove Time",
                    "Remove Time",
                    [
                        (
                            "time",
                            discord.ui.TextInput(
                                label="Time (s/m/h/d)", placeholder="1s, 1m, 1h, 1d"
                            ),
                        )
                    ],
                )
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** how much time do you want to remove?",
                    view=second_view,
                    embed=None,
                )
                timeout = await second_view.wait()
                if (not timeout) and second_view.modal.time.value:
                    content = second_view.modal.time.value
                else:
                    return await failure_embed(ctx, "you didn't provide a time!")
                content = content.strip()
                try:
                    if content.endswith(("s", "m", "h", "d")):
                        full = None
                        seconds = 0
                        if content.endswith("s"):
                            full = "seconds"
                            num = int(content[:-1])
                            seconds = num
                            # print("seconds")
                        if content.endswith("m"):
                            full = "minutes"
                            num = int(content[:-1])
                            seconds = num * 60
                            # print("minutes")
                        if content.endswith("h"):
                            full = "hours"
                            num = int(content[:-1])
                            seconds = num * 60 * 60

                            # print("hours")
                        if content.endswith("d"):
                            full = "days"
                            num = int(content[:-1])
                            seconds = num * 60 * 60 * 24

                            # print("days")
                    else:
                        return await failure_embed(ctx, "invalid time format. (e.g. 120m)")
                except:
                    return await failure_embed(ctx, "invalid time format. (e.g. 120m)")
                sh = await bot.shift_management.get_current_shift(member, ctx.guild.id)
                if sh:
                    await bot.shift_management.remove_time_from_shift(
                        sh["_id"], seconds
                    )
                else:
                    shift_type_name = "Default"
                    if isinstance(shift_type, str):
                        shift_type_name = shift_type
                    elif isinstance(shift_type, dict):
                        shift_type_name = shift_type["name"]

                    try:
                        oid = await bot.shift_management.add_shift_by_user(
                            member, shift_type_name, [], ctx.guild.id
                        )
                        await bot.shift_management.remove_time_from_shift(oid, seconds)
                        await bot.shift_management.end_shift(oid, ctx.guild.id)
                    except Exception as e:
                        return await failure_embed(
                            ctx, "something went wrong. Please try again later."
                        )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've removed **{num} {full}** from **{member.display_name}**'s shift.",
                    view=None,
                )

            if view.admin_value == "void":
                if not has_started:
                    return await msg.edit(
                        content=f"<:ERMClose:1111101633389146223> **{ctx.author.name}**, the member has not started a shift yet. You cannot void a shift that has not started.",
                        embed=None,
                        view=None,
                    )

                if shift.get("Nickname"):
                    if shift.get("Nickname") == member.nick:
                        nickname = None
                        if shift.get("Type") is not None:
                            settings = await bot.settings.get_settings(ctx.guild.id)
                            shift_types = None
                            if settings.get("shift_types"):
                                shift_types = settings["shift_types"].get("types", [])
                            else:
                                shift_types = []
                            for s in shift_types:
                                if s["name"] == shift.get("Type"):
                                    shift_type = s
                                    nickname = (
                                        s["nickname"] if s.get("nickname") else None
                                    )
                        if nickname is None:
                            nickname = settings["shift_management"].get(
                                "nickname_prefix", ""
                            )
                        try:
                            await member.edit(nick=member.nick.replace(nickname, ""))
                        except Exception as e:
                            # print(e)
                            pass

                embed = discord.Embed(
                    title=f"<:ERMTrash:1111100349244264508> {member.name}",
                    color=0xED4348,
                )

                try:
                    embed.set_thumbnail(url=member.display_avatar.url)
                except:
                    pass
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Type",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Voided time, performed by ({ctx.author.display_name})",
                    inline=False,
                )

                embed.add_field(
                    name="<:ERMList:1111099396990435428> Elapsed Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(ctx.message.created_at.replace(tzinfo=pytz.UTC) - datetime.datetime.fromtimestamp(shift['StartEpoch'], tz=pytz.UTC))}",
                    inline=False,
                )

                embed.set_footer(text="Staff Logging Module")

                sh = await bot.shift_management.get_current_shift(member, ctx.guild.id)
                await bot.shift_management.shifts.delete_by_id(sh["_id"])

                if shift_channel is None:
                    return

                await shift_channel.send(embed=embed)
                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, I've voided **{member.name}**'s Shift.",
                    view=None,
                )
                role = None
                if shift_type:
                    if shift_type.get("role"):
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in shift_type.get("role")
                        ]
                else:
                    if configItem["shift_management"]["role"]:
                        if not isinstance(configItem["shift_management"]["role"], list):
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles,
                                    id=configItem["shift_management"]["role"],
                                )
                            ]
                        else:
                            role = [
                                discord.utils.get(ctx.guild.roles, id=role)
                                for role in configItem["shift_management"]["role"]
                            ]

                if role:
                    for rl in role:
                        if rl in member.roles and rl is not None:
                            try:
                                await member.remove_roles(rl)
                            except:
                                await failure_embed(
                                    ctx, f"could not remove {rl} from {member.mention}"
                                )

            if view.admin_value == "clear":
                all_shifts = [
                    i
                    async for i in bot.shift_management.shifts.db.find(
                        {"UserID": member.id}
                    )
                ]
                for i in all_shifts:
                    await bot.shift_management.shifts.delete_by_id(i["_id"])

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}** I've cleared **{member.display_name}**'s shifts - per your request.",
                    embed=None,
                    view=None,
                )

    @duty.command(
        name="manage",
        description="Manage your own shift in an easy way!",
        extras={"category": "Shift Management", "ignoreDefer": True},
    )
    @is_staff()
    async def manage(self, ctx, flags: DutyManageOptions):
        option_selected = None

        if flags.without_command_execution is True:
            # print(1)
            if ctx.interaction:
                # print(2)
                await ctx.interaction.response.defer(ephemeral=True, thinking=True)
            else:
                await ctx.defer()
        else:
            await ctx.defer()

        if flags is not None:
            # print(1556)
            option_selected = {
                flags.onduty: "on",
                flags.togglebreak: "break",
                flags.offduty: "off",
            }.get(True)

            # print(flags.onduty)
            # print(flags.togglebreak)
            # print(flags.offduty)
        else:
            pass
            # print(1563)
        # print(option_selected)

        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await failure_embed(
                ctx,
                "the server has not been set up yet. Please run `/setup` to set up the server.",
            )

        try:
            shift_channel = discord.utils.get(
                ctx.guild.channels, id=configItem["shift_management"]["channel"]
            )
        except:
            return await failure_embed(
                ctx,
                f'some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.',
            )

        if not configItem["shift_management"]["enabled"]:
            return await failure_embed(
                ctx, "Shift management is not enabled on this server."
            )

        shift = await bot.shift_management.get_current_shift(ctx.author, ctx.guild.id)
        view = ModificationSelectMenu(ctx.author.id)

        embed = discord.Embed(
            color=0xED4348,
            title=f"<:ERMUser:1111098647485108315> {ctx.author.name}",
        )

        quota_seconds = None
        met_quota = None
        member_seconds = 0
        ordinal_place = None
        ordinal_formatted = None

        if "quota" in configItem["shift_management"].keys():
            quota_seconds = configItem["shift_management"]["quota"]

        all_staff = [{"id": None, "total_seconds": 0, "quota_seconds": 0}]

        datetime_obj = datetime.datetime.now(tz=pytz.UTC)
        ending_period = datetime_obj
        starting_period = datetime_obj - datetime.timedelta(days=7)

        async for document in bot.shift_management.shifts.db.find(
            {
                "Guild": ctx.guild.id,
                "EndEpoch": {"$ne": 0},
            }
        ):
            total_seconds = 0
            quota_seconds = 0

            total_seconds = get_elapsed_time(document)

            if document["StartEpoch"] > starting_period.timestamp():
                quota_seconds = total_seconds

            if document["UserID"] not in [item["id"] for item in all_staff]:
                all_staff.append(
                    {
                        "id": document["UserID"],
                        "total_seconds": total_seconds,
                        "quota_seconds": quota_seconds,
                    }
                )
            else:
                for item in all_staff:
                    if item["id"] == document["UserID"]:
                        item["total_seconds"] += total_seconds
                        item["quota_seconds"] += quota_seconds

        if len(all_staff) == 0:
            return await failure_embed(ctx, "no shifts were made in your server.")
        for item in all_staff:
            if item["id"] is None:
                all_staff.remove(item)

        sorted_staff = sorted(all_staff, key=lambda x: x["total_seconds"], reverse=True)

        for index, value in enumerate(sorted_staff):
            member = discord.utils.get(ctx.guild.members, id=value["id"])
            if member:
                if member.id == ctx.author.id:
                    member_seconds = value["total_seconds"]
                    if quota_seconds is not None:
                        if value["total_seconds"] > quota_seconds:
                            met_quota = "Met "
                        else:
                            met_quota = "Not met"
                        ordinal_place = index + 1
                    else:
                        met_quota = "Not met"
                        ordinal_place = index + 1

        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )  # NOQA: E731
        ms_delta = datetime.timedelta(seconds=member_seconds)

        if ordinal_place is not None:
            ordinal_formatted = ordinal(ordinal_place)

        if td_format(ms_delta) != "":
            embed.add_field(
                name="<:ERMList:1111099396990435428> Previous Shift Data",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** {td_format(ms_delta)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Quota:** {met_quota}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Rank:** {ordinal_formatted}",
                inline=False,
            )
        status = None

        # print(shift)
        if shift:
            for item in shift["Breaks"]:
                if item["EndEpoch"] == 0:
                    status = "break"
                    break

            if status != "break" and shift["EndEpoch"] == 0:
                status = "on"
            elif shift["EndEpoch"] != 0:
                status = "off"
        else:
            status = "off"

        embed.add_field(
            name="<:ERMList:1111099396990435428> Shift Management",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **On-Duty** {'(Current)' if status == 'on' else ''}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **On-Break** {'(Current)' if status == 'break' else ''}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Off-Duty** {'(Current)' if status == 'off' else ''}",
        )
        embed.set_author(
            name=ctx.author.name,
            icon_url=ctx.author.display_avatar.url,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        doc = [
            i
            async for i in bot.shift_management.shifts.db.find(
                {"Guild": ctx.guild.id, "EndEpoch": 0}
            )
        ]
        currently_active = len(doc)

        if status == "on" or status == "break":
            warnings = 0
            kicks = 0
            bans = 0
            ban_bolos = 0
            custom = 0
            if "Moderations" in shift.keys():
                for mod in shift["Moderations"]:
                    item = await bot.punishments.find_warning_by_spec(
                        identifier=mod, guild_id=ctx.guild.id
                    )
                    if item is None:
                        continue
                    if item["Type"] == "Warning":
                        warnings += 1
                    elif item["Type"] == "Kick":
                        kicks += 1
                    elif item["Type"] == "Ban" or item["Type"] == "Temporary Ban":
                        bans += 1
                    elif item["Type"] == "BOLO":
                        ban_bolos += 1
                    else:
                        custom += 1

            if "Type" in shift.keys():
                if shift["Type"]:
                    raw_shift_type: str = shift["Type"]
                    settings = await bot.settings.find_by_id(ctx.guild.id)
                    shift_types = settings.get("shift_types")
                    shift_types = (
                        shift_types.get("types")
                        if (shift_types or {}).get("types") is not None
                        else []
                    )
                    if shift_types:
                        sh_typelist = [
                            item
                            for item in shift_types
                            if item["name"] == raw_shift_type
                        ]
                        if len(sh_typelist) > 0:
                            shift_type = sh_typelist[0]
                        else:
                            shift_type = {
                                "name": "Default",
                                "id": 0,
                                "role": settings["shift_management"].get("role"),
                            }
                    else:
                        shift_type = {
                            "name": "Default",
                            "id": 0,
                            "role": settings["shift_management"].get("role"),
                        }
                else:
                    shift_type = None
            else:
                shift_type = None

            if shift_type:
                if shift_type.get("channel"):
                    temp_shift_channel = discord.utils.get(
                        ctx.guild.channels, id=shift_type["channel"]
                    )
                    if temp_shift_channel is not None:
                        shift_channel = temp_shift_channel

            time_delta = datetime.timedelta(seconds=get_elapsed_time(shift))

            embed2 = discord.Embed(
                title=f"<:ERMActivity:1113209176664064060> Current Shift",
                color=0xED4348,
            )

            embed2.add_field(
                name="<:ERMList:1111099396990435428> Moderation Details",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{} Warnings\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{} Kicks\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{} Bans\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{} Ban BOLOs\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{} Custom".format(
                    warnings, kicks, bans, ban_bolos, custom
                ),
                inline=False,
            )

            break_seconds = 0
            if "Breaks" in shift.keys():
                for item in shift["Breaks"]:
                    if item["EndEpoch"] != 0:
                        break_seconds += item["EndEpoch"] - item["StartEpoch"]
                    else:
                        break_seconds += (
                            datetime.datetime.now(tz=pytz.UTC).timestamp()
                            - item["StartEpoch"]
                        )

            break_seconds = int(break_seconds)

            doc = [
                i
                async for i in bot.shift_management.shifts.db.find(
                    {"Guild": ctx.guild.id, "EndEpoch": 0}
                )
            ]
            currently_active = len(doc)

            if shift_type:
                embed2.add_field(
                    name="<:ERMList:1111099396990435428> Shift Status",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{'**On-Duty**' if status == 'on' else '**On-Break**'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time:** {td_format(time_delta)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Breaks:** {len(shift['breaks']) if 'breaks' in shift.keys() else '0'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time on Break:** {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Current Shift Type:** {shift_type['name']}",
                )
            else:
                embed2.add_field(
                    name="<:ERMList:1111099396990435428> Shift Status",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{'**On-Duty**' if status == 'on' else '**On-Break**'} \n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time:** {td_format(time_delta)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Breaks:** {len(shift['breaks']) if 'breaks' in shift.keys() else '0'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time on Break:** {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Current Shift Type:** Default",
                )

            embed2.set_footer(text=f"Currently online staff: {currently_active}")

            if option_selected is None:
                msg = await ctx.reply(
                    embeds=[embed, embed2],
                    view=view,
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, looks like you want to manage your shift. Select an option.",
                )
            else:
                msg = await ctx.reply(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** please wait."
                )
        else:
            embed.set_footer(text=f"Currently online staff: {currently_active}")
            if option_selected is None:
                msg = await ctx.reply(
                    embed=embed,
                    view=view,
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, looks like you want to manage your shift. Select an option.",
                )
            else:
                msg = await ctx.reply(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** please wait."
                )
        if msg.components:
            timeout = await view.wait()
        else:
            timeout = False
        # print(1877)
        if timeout:
            new_view = copy.copy(view)
            new_view.clear_items()
            new_view.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label="You didn't respond in time!",
                    disabled=True,
                )
            )
            try:
                await msg.edit(view=new_view)
            except:
                pass
            return

        if option_selected:
            view.value = option_selected

        # print(1897)
        if view.value == "on":
            if status == "on":
                if msg is not None:
                    return await msg.edit(
                        content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you are already on-duty. You can go off-duty by selecting **Off-Duty**.",
                        embed=None,
                        view=None,
                    )
                else:
                    return await ctx.send(
                        content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you are already on-duty. You can go off-duty by selecting **Off-Duty**.",
                        embed=None,
                        view=None,
                    )
            elif status == "break":
                for index, item in enumerate(shift["Breaks"].copy()):
                    if item["EndEpoch"] == 0:
                        item["EndEpoch"] = ctx.message.created_at.timestamp()
                        shift["Breaks"][index] = item

                sh = await bot.shift_management.get_current_shift(
                    ctx.author, ctx.guild.id
                )
                if sh:
                    if sh["Guild"] == ctx.guild.id:
                        await bot.shift_management.shifts.update_by_id(sh)
                role = None
                if shift_type:
                    if shift_type.get("role"):
                        if isinstance(shift_type.get("role"), list):
                            role = [
                                discord.utils.get(ctx.guild.roles, id=rl)
                                for rl in shift_type.get("role")
                            ]
                        else:
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles, id=shift_type.get("role")
                                )
                            ]
                else:
                    if configItem["shift_management"]["role"]:
                        if not isinstance(configItem["shift_management"]["role"], list):
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles,
                                    id=configItem["shift_management"]["role"],
                                )
                            ] or []
                        else:
                            role = [
                                discord.utils.get(ctx.guild.roles, id=role)
                                for role in configItem["shift_management"]["role"]
                            ]
                if role:
                    for rl in role:
                        if rl not in ctx.author.roles and rl is not None:
                            try:
                                await ctx.author.add_roles(rl)
                            except:
                                await failure_embed(
                                    ctx, f"could not add {rl} to {ctx.author.mention}"
                                )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, you are no longer on break.",
                    view=None,
                )
            else:
                settings = await bot.settings.find_by_id(ctx.guild.id)
                shift_type = None

                maximum_staff = settings["shift_management"].get("maximum_staff")
                if maximum_staff not in [None, 0]:
                    if (currently_active + 1) > maximum_staff:
                        return await failure_embed(
                            ctx,
                            f"the maximum amount of staff that can be on-duty at once is **{maximum_staff}**. Ask your server administration for more details.",
                        )

                if settings.get("shift_types"):
                    if (
                        len(settings["shift_types"].get("types") or []) > 1
                        and settings["shift_types"].get("enabled") is True
                    ):
                        shift_types = settings["shift_types"]["types"]
                        view = CustomSelectMenu(
                            ctx.author.id,
                            [
                                discord.SelectOption(
                                    label=item["name"],
                                    value=item["id"],
                                    description=item["name"],
                                )
                                for item in settings["shift_types"]["types"]
                            ],
                        )
                        await msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you have {num2words.num2words(len(shift_types))} shift types - {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select which one you want to use.",
                            embed=None,
                            view=view,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return
                        if view.value:
                            shift_type = [
                                item
                                for item in settings["shift_types"]["types"]
                                if item["id"] == int(view.value)
                            ]
                            if len(shift_type) == 1:
                                shift_type = shift_type[0]
                            else:
                                return await failure_embed(
                                    ctx,
                                    "something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).",
                                )
                        else:
                            return
                    else:
                        if (
                            settings["shift_types"].get("enabled") is True
                            and len(settings["shift_types"].get("types") or []) == 1
                        ):
                            shift_type = settings["shift_types"]["types"][0]
                        else:
                            shift_type = None

                nickname_prefix = None
                changed_nick = False
                if shift_type:
                    if shift_type.get("nickname"):
                        nickname_prefix = shift_type.get("nickname")
                else:
                    if configItem["shift_management"].get("nickname_prefix"):
                        nickname_prefix = configItem["shift_management"].get(
                            "nickname_prefix"
                        )

                if nickname_prefix:
                    current_name = (
                        ctx.author.nick if ctx.author.nick else ctx.author.name
                    )
                    new_name = "{}{}".format(nickname_prefix, current_name)

                    try:
                        await ctx.author.edit(nick=new_name)
                        changed_nick = True
                    except Exception as e:
                        # print(e)
                        pass

                old = shift_type
                shift_type = shift_type["name"] if shift_type else "Default"

                await bot.shift_management.add_shift_by_user(
                    ctx.author, shift_type, [], ctx.guild.id
                )
                shift_type = old

                role = None

                if shift_type:
                    if shift_type.get("role"):
                        if isinstance(shift_type.get("role"), list):
                            role = [
                                discord.utils.get(ctx.guild.roles, id=rl)
                                for rl in shift_type.get("role")
                            ]
                        else:
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles, id=shift_type.get("role")
                                )
                            ]
                else:
                    if configItem["shift_management"]["role"]:
                        if not isinstance(configItem["shift_management"]["role"], list):
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles,
                                    id=configItem["shift_management"]["role"],
                                )
                            ]
                        else:
                            role = [
                                discord.utils.get(ctx.guild.roles, id=role)
                                for role in configItem["shift_management"]["role"]
                            ]
                if role:
                    for rl in role:
                        if rl not in ctx.author.roles and rl is not None:
                            try:
                                await ctx.author.add_roles(rl)
                            except:
                                await failure_embed(
                                    ctx, f"could not add {rl} to {ctx.author.mention}"
                                )

                embed = discord.Embed(
                    title=f"<:ERMAdd:1113207792854106173> Shift Started", color=0xED4348
                )
                try:
                    embed.set_thumbnail(url=ctx.author.display_avatar.url)
                    embed.set_footer(text="Staff Logging Module")
                    embed.set_author(
                        name=ctx.author.name,
                        icon_url=ctx.author.display_avatar.url,
                    )
                except:
                    pass

                if shift_type:
                    embed.add_field(
                        name="<:ERMList:1111099396990435428> Type",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking in. **({shift_type['name']})**",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="<:ERMList:1111099396990435428> Type",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking in.",
                        inline=False,
                    )
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Current Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(ctx.message.created_at.timestamp())}>",
                    inline=False,
                )

                if shift_channel is None:
                    return

                await shift_channel.send(embed=embed)
                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your shift is now active.",
                    embed=None,
                    view=None,
                )
        elif view.value == "off":
            break_seconds = 0
            if shift:
                if "breaks" in shift.keys():
                    for item in shift["breaks"]:
                        if item["ended"] == None:
                            item["ended"] = ctx.message.created_at.replace(
                                tzinfo=pytz.UTC
                            ).timestamp()
                        startTimestamp = item["started"]
                        endTimestamp = item["ended"]
                        break_seconds += int(endTimestamp - startTimestamp)
            else:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you are not on-duty. You can go on-duty by selecting **On-Duty**.",
                    embed=None,
                    view=None,
                )
            if status == "off":
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you are already off-duty. You can go on-duty by selecting **On-Duty**.",
                    embed=None,
                    view=None,
                )

            embed = discord.Embed(
                title=f"<:ERMRemove:1113207777662345387> Shift Ended", color=0xED4348
            )

            if shift.get("Nickname"):
                if shift.get("Nickname") == ctx.author.nick:
                    nickname = None
                    if shift.get("Type") is not None:
                        settings = await bot.settings.get_settings(ctx.guild.id)
                        shift_types = None
                        if settings.get("shift_types"):
                            shift_types = settings["shift_types"].get("types", [])
                        else:
                            shift_types = []
                        for s in shift_types:
                            if s["name"] == shift.get("Type"):
                                shift_type = s
                                nickname = s["nickname"] if s.get("nickname") else None
                    if nickname is None:
                        nickname = settings["shift_management"].get(
                            "nickname_prefix", ""
                        )
                    try:
                        await ctx.author.edit(
                            nick=ctx.author.nick.replace(nickname, "")
                        )
                    except Exception as e:
                        # print(e)
                        pass

            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")

            if shift.get("Type") != "":
                settings = await bot.settings.find_by_id(ctx.author.id)
                shift_type = None
                if settings:
                    if "shift_types" in settings.keys():
                        for item in settings["shift_types"].get("types") or []:
                            if item["name"] == shift["Type"]:
                                shift_type = item
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )

            if shift_type:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Type",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking out. **({shift_type['name']})**",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Type",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking out.",
                    inline=False,
                )

            time_delta = ctx.message.created_at - datetime.datetime.fromtimestamp(
                shift["StartEpoch"], tz=pytz.UTC
            )

            time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

            added_seconds = 0
            removed_seconds = 0
            if "AddedTime" in shift.keys():
                added_seconds += shift["AddedTime"]

            if "RemovedTime" in shift.keys():
                removed_seconds += shift["RemovedTime"]

            try:
                time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)
            except OverflowError:
                await failure_embed(
                    ctx,
                    f"{ctx.author.mention}'s added or removed time has been voided due to it being an unfeasibly massive numeric value. If you find a vulnerability in ERM, please report it via our Support Server.",
                )

            if break_seconds > 0:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Elapsed Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Elapsed Time",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)}",
                    inline=False,
                )

            await msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your shift is now over.",
                embed=None,
                view=None,
            )

            if shift.get("Nickname"):
                if shift.get("Nickname") == ctx.author.nick:
                    nickname = None
                    if shift.get("Type") is not None:
                        settings = await bot.settings.get_settings(ctx.guild.id)
                        shift_types = None
                        if settings.get("shift_types"):
                            shift_types = settings["shift_types"].get("types", [])
                        else:
                            shift_types = []
                        for s in shift_types:
                            if s["name"] == shift.get("Type"):
                                shift_type = s
                                nickname = s["nickname"] if s.get("nickname") else None
                    if nickname is None:
                        nickname = settings["shift_management"].get(
                            "nickname_prefix", ""
                        )
                    try:
                        await ctx.author.edit(
                            nick=ctx.author.nick.replace(nickname, "")
                        )
                    except Exception as e:
                        # print(e)
                        pass
            if shift_channel is None:
                return

            await shift_channel.send(embed=embed)

            embed = discord.Embed(
                title="<:ERMSchedule:1111091306089939054> Shift Report",
                color=0xED4348,
            )

            mods = shift.get("Moderations") if shift.get("Moderations") else []
            all_moderation_items = [
                await bot.punishments.find_warning_by_spec(
                    ctx.guild.id, identifier=moderation
                )
                for moderation in mods
            ]
            moderations = len(all_moderation_items)

            embed.set_author(
                name=f"You have made {moderations} moderations during your shift.",
                icon_url=ctx.author.display_avatar.url,
            )

            embed.add_field(
                name="<:ERMList:1111099396990435428> Elapsed Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                inline=False,
            )

            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0
            custom = 0

            for moderation in all_moderation_items:
                if moderation is None:
                    continue
                if moderation["Type"] == "Warning":
                    warnings += 1
                elif moderation["Type"] == "Kick":
                    kicks += 1
                elif moderation["Type"] == "Ban":
                    bans += 1
                elif moderation["Type"] == "BOLO" or moderation["Type"] == "Bolo":
                    bolos += 1
                elif moderation["Type"] not in [
                    "Warning",
                    "Kick",
                    "Ban",
                    "BOLO",
                    "Bolo",
                ]:
                    custom += 1

            embed.add_field(
                name="<:ERMList:1111099396990435428> Total Moderations",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Warnings:** {warnings}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Kicks:** {kicks}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Bans:** {bans}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **BOLO:** {bolos}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Custom:** {custom}",
                inline=False,
            )
            dm_channel = await ctx.author.create_dm()
            # dm_msg = await dm_channel.send(
            #     embed=create_invis_embed(
            #         'Your Shift Report is being generated. Please wait up to 5 seconds for complete generation.')
            # )
            new_ctx = copy.copy(ctx)
            new_ctx.guild = None
            new_ctx.channel = dm_channel

            menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
            menu.add_page(embed)

            moderation_embed = discord.Embed(
                title="<:ERMSchedule:1111091306089939054> Shift Report",
                color=0xED4348,
            )

            moderation_embed.set_author(
                name=f"You have made {moderations} moderations during your shift.",
                icon_url=ctx.author.display_avatar.url,
            )

            moderation_embeds = []
            moderation_embeds.append(moderation_embed)
            # print("9867")

            for moderation in all_moderation_items:
                if moderation is not None:
                    if len(moderation_embeds[-1].fields) >= 10:
                        moderation_embeds.append(
                            discord.Embed(
                                title="<:ERMSchedule:1111091306089939054> Shift Report",
                                color=0xED4348,
                            )
                        )

                        moderation_embeds[-1].set_author(
                            name=f"You have made {moderations} moderations during your shift.",
                            icon_url=ctx.author.display_avatar.url,
                        )

                    moderation_embeds[-1].add_field(
                        name=f"<:ERMList:1111099396990435428> {moderation['Type'].title()}",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **ID:** {moderation['Snowflake']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Type:** {moderation['Type']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Reason:** {moderation['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time:** <t:{int(moderation['Epoch'])}>",
                        inline=False,
                    )

            time_embed = discord.Embed(
                title="<:ERMSchedule:1111091306089939054> Shift Report",
                color=0xED4348,
            )

            time_embed.set_author(
                name=f"You were on-shift for {td_format(time_delta)}.",
                icon_url=ctx.author.display_avatar.url,
            )
            # print("9919")

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Shift Start",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(shift['StartEpoch'])}>",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Shift End",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(datetime.datetime.now(tz=pytz.UTC).timestamp())}>",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Added Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=added_seconds))}",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Removed Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=removed_seconds))}",
                inline=False,
            )

            time_embed.add_field(
                name="<:ERMList:1111099396990435428> Total Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)}",
                inline=False,
            )

            menu.add_select(
                ViewSelect(
                    title="Shift Report",
                    options={
                        discord.SelectOption(
                            label="Moderations",
                            description="View all of your moderations during this shift",
                        ): [Page(embed=embed) for embed in moderation_embeds],
                        discord.SelectOption(
                            label="Shift Time",
                            description="View your shift time",
                        ): [Page(embed=time_embed)],
                    },
                )
            )

            menu.add_button(ViewButton.back())
            menu.add_button(ViewButton.next())
            consent_obj = await bot.consent.find_by_id(ctx.author.id)
            should_send = True
            if consent_obj:
                # print(consent_obj)
                if consent_obj.get("shift_reports") is not None:
                    if consent_obj.get("shift_reports") is False:
                        should_send = False
            if should_send:
                try:
                    await menu.start()
                except:
                    pass

            try:
                await bot.shift_management.end_shift(
                    identifier=shift["_id"],
                    guild_id=ctx.guild.id,
                )
            except ValueError as e:
                return await failure_embed(ctx, "shift not found. Could not end shift.")
            role = None
            if shift_type:
                if shift_type.get("role"):
                    role = [
                        discord.utils.get(ctx.guild.roles, id=role)
                        for role in shift_type.get("role")
                    ]
            else:
                if configItem["shift_management"]["role"]:
                    if not isinstance(configItem["shift_management"]["role"], list):
                        role = [
                            discord.utils.get(
                                ctx.guild.roles,
                                id=configItem["shift_management"]["role"],
                            )
                        ]
                    else:
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in configItem["shift_management"]["role"]
                        ]

            if role:
                for rl in role:
                    if rl in ctx.author.roles and rl is not None:
                        try:
                            await ctx.author.remove_roles(rl)
                        except:
                            await failure_embed(
                                ctx, f"Could not remove {rl} from {ctx.author.mention}"
                            )
        elif view.value == "break":
            if status == "off":
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you cannot be on break if you are not currently on-duty. If you would like to be on-duty, pick **On-Duty**",
                    embed=None,
                )
            toggle = "on"

            if "Breaks" in shift.keys():
                for item in shift["Breaks"]:
                    if item["EndEpoch"] == 0:
                        toggle = "off"

            if toggle == "on":
                shift["Breaks"].append(
                    {
                        "StartEpoch": ctx.message.created_at.timestamp(),
                        "EndEpoch": 0,
                    }
                )

                await bot.shift_management.shifts.update_by_id(shift)

                await msg.edit(
                    embed=None,
                    view=None,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your break has started - see you soon! <:BreakStart:1111093969871446067>",
                )
                if shift.get("Nickname"):
                    if shift.get("Nickname") == ctx.author.nick:
                        nickname = None
                        if shift.get("Type") is not None:
                            settings = await bot.settings.get_settings(ctx.guild.id)
                            shift_types = None
                            if settings.get("shift_types"):
                                shift_types = settings["shift_types"].get("types", [])
                            else:
                                shift_types = []
                            for s in shift_types:
                                if s["name"] == shift.get("Type"):
                                    shift_type = s
                                    nickname = (
                                        s["nickname"] if s.get("nickname") else None
                                    )
                        if nickname is None:
                            nickname = settings["shift_management"].get(
                                "nickname_prefix", ""
                            )
                        try:
                            await ctx.author.edit(
                                nick=ctx.author.nick.replace(nickname, "")
                            )
                        except Exception as e:
                            # print(e)
                            pass

                role = []
                if shift_type:
                    if shift_type.get("role"):
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in shift_type.get("role")
                        ]
                else:
                    if configItem["shift_management"]["role"]:
                        if not isinstance(configItem["shift_management"]["role"], list):
                            role = [
                                discord.utils.get(
                                    ctx.guild.roles,
                                    id=configItem["shift_management"]["role"],
                                )
                            ]
                        else:
                            role = [
                                discord.utils.get(ctx.guild.roles, id=role)
                                for role in configItem["shift_management"]["role"]
                            ]

                if role is not None:
                    for rl in role:
                        if rl in ctx.author.roles and rl is not None:
                            try:
                                await ctx.author.remove_roles(rl)
                            except:
                                await failure_embed(
                                    ctx,
                                    f"could not remove {rl} from {ctx.author.mention}",
                                )

            else:
                await end_break(
                    bot,
                    shift,
                    shift_type,
                    configItem,
                    ctx,
                    msg,
                    ctx.author,
                    manage=True,
                )
        elif view.value == "void":
            if status == "off":
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you have not started a shift yet. You cannot void a shift that has not started.",
                    embed=None,
                    view=None,
                )
            embed = discord.Embed(
                title=f"<:ERMTrash:1111100349244264508> Voided Time", color=0xED4348
            )

            if shift.get("Nickname"):
                if shift.get("Nickname") == ctx.author.nick:
                    nickname = None
                    if shift.get("Type") is not None:
                        settings = await bot.settings.get_settings(ctx.guild.id)
                        shift_types = None
                        if settings.get("shift_types"):
                            shift_types = settings["shift_types"].get("types", [])
                        else:
                            shift_types = []
                        for s in shift_types:
                            if s["name"] == shift.get("Type"):
                                shift_type = s
                                nickname = s["nickname"] if s.get("nickname") else None
                    if nickname is None:
                        nickname = settings["shift_management"].get(
                            "nickname_prefix", ""
                        )
                    try:
                        await ctx.author.edit(
                            nick=ctx.author.nick.replace(nickname, "")
                        )
                    except Exception as e:
                        # print(e)
                        pass

            try:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url,
                )
            except:
                pass
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Voided time.",
                inline=False,
            )

            embed.add_field(
                name="<:ERMList:1111099396990435428> Elapsed Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(ctx.message.created_at.replace(tzinfo=pytz.UTC) - datetime.datetime.fromtimestamp(shift['StartEpoch'], tz=pytz.UTC))}",
                inline=False,
            )

            embed.set_footer(text="Staff Logging Module")

            sh = await bot.shift_management.get_current_shift(ctx.author, ctx.guild.id)
            await bot.shift_management.shifts.delete_by_id(sh["_id"])

            if shift_channel is None:
                return

            await shift_channel.send(embed=embed)
            await msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your shift has been voided.",
                view=None,
            )
            role = None
            if shift_type:
                if shift_type.get("role"):
                    role = [
                        discord.utils.get(ctx.guild.roles, id=role)
                        for role in shift_type.get("role")
                    ]
            else:
                if configItem["shift_management"]["role"]:
                    if not isinstance(configItem["shift_management"]["role"], list):
                        role = [
                            discord.utils.get(
                                ctx.guild.roles,
                                id=configItem["shift_management"]["role"],
                            )
                        ]
                    else:
                        role = [
                            discord.utils.get(ctx.guild.roles, id=role)
                            for role in configItem["shift_management"]["role"]
                        ]

            if role:
                for rl in role:
                    if rl in ctx.author.roles and rl is not None:
                        try:
                            await ctx.author.remove_roles(rl)
                        except:
                            await failure_embed(
                                ctx, f"could not remove {rl} from {ctx.author.mention}"
                            )

    @duty.command(
        name="active",
        description="Get all members of the server currently on shift.",
        extras={"category": "Shift Management"},
        aliases=["ac", "ison"],
    )
    @is_staff()
    async def duty_active(self, ctx):
        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await failure_embed(
                ctx,
                "this server has not been set up yet. Please run `/setup` to set up the server.",
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
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you have {num2words.num2words(len(shift_types))} shift types - {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select which one you want to use.",
                        embed=None,
                        view=view,
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
                                return await failure_embed(
                                    ctx,
                                    "if you somehow encounter this error, please contact [ERM Support](https://discord.gg/FAC629TzBy)",
                                )

        embed = discord.Embed(
            title="<:ERMActivity:1113209176664064060> Active Shifts", color=0xED4348
        )
        embed.description = "<:ERMMisc:1113215605424795648> **Shifts:**"
        embed.set_author(
            name=f"{ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )
        try:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        except:
            pass

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
                    title="<:ERMActivity:1113209176664064060> Active Shifts",
                    color=0xED4348,
                )
                embed.description = "<:ERMMisc:1113215605424795648> **Shifts:**"
                embed.set_author(
                    name=f"{ctx.author.name}",
                    icon_url=ctx.author.display_avatar.url,
                )
                added_staff.append(member.id)
                embeds.append(embed)
            if member.id not in added_staff:
                embeds[
                    -1
                ].description += f"\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=staff['total_seconds']))}{(' **(Currently on break: {})**'.format(td_format(datetime.timedelta(seconds=staff['break_seconds'])))) if staff['break_seconds'] > 0 else ''}"

        if ctx.interaction:
            gtx = ctx.interaction
        else:
            gtx = ctx

        menu = ViewMenu(gtx, menu_type=ViewMenu.TypeEmbed, timeout=None)
        for embed in embeds:
            menu.add_page(embed=embed)
        menu._pc = _PageController(menu.pages)
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        if len(menu.pages) == 1:
            try:
                return await msg.edit(
                    embed=embed,
                    view=None,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the Active Shifts in **{ctx.guild.name}**.",
                )
            except UnboundLocalError:
                return await ctx.reply(embed=embed)
        try:
            await msg.edit(embed=embeds[0], view=menu._ViewMenu__view)
        except UnboundLocalError:
            await ctx.reply(embed=embeds[0], view=menu._ViewMenu__view)

    @duty.command(
        name="leaderboard",
        description="Get the total time worked for the whole of the staff team.",
        extras={"category": "Shift Management"},
        aliases=["lb"],
    )
    @is_staff()
    async def shift_leaderboard(self, ctx):
        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        try:
            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                raise ValueError("Settings does not exist.")
        except:
            return await failure_embed(
                ctx,
                "this server has not been set up yet. Please run `/setup` to set up the server.",
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
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you have {num2words.num2words(len(shift_types))} shift types - {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select which one you want to use.",
                        embed=None,
                        view=view,
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
                                return await failure_embed(
                                    ctx,
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
                    int(
                        (
                            document["EndEpoch"]
                            if document["EndEpoch"] != 0
                            else document["StartEpoch"]
                        )
                    )
                    - int(document["StartEpoch"])
                    + document["AddedTime"]
                    - document["RemovedTime"]
                    - break_seconds
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
            return await failure_embed(ctx, "no shifts were made in your server.")
        for item in all_staff:
            if item["id"] is None:
                all_staff.remove(item)

        sorted_staff = sorted(all_staff, key=lambda x: x["total_seconds"], reverse=True)

        buffer = None
        embeds = []

        embed = discord.Embed(
            color=0xED4348, title="<:ERMMisc:1113215605424795648> Leaderboard"
        )
        embed.set_author(
            name=f"{ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        embed.set_thumbnail(url=ctx.guild.icon.url)

        embeds.append(embed)
        # print(sorted_staff)
        data = []
        if not sorted_staff:
            if shift_type != 0 and shift_type is not None:
                await failure_embed(
                    ctx,
                    f"no shifts were made for the `{shift_type['name']}` shift type.",
                )
            else:
                await failure_embed(ctx, "no shifts were made in your server.")
            return

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
                        ].description = f"<:ERMList:1111099396990435428> **Total Shifts**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
                    else:
                        embeds[
                            -1
                        ].description += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"

                else:
                    # print("fields more than 24")
                    new_embed = discord.Embed(
                        color=0xED4348,
                        title="<:ERMMisc:1113215605424795648> Leaderboard",
                    )

                    new_embed.set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                    )

                    new_embed.set_thumbnail(url=ctx.guild.icon.url)
                    new_embed.description = ""
                    new_embed.description += f"<:ERMList:1111099396990435428> **Total Shifts**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
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
                                    ].description = f"<:ERMList:1111099396990435428> **Total Shifts**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index}.** {member.mention} - 0 seconds\n"
                                else:
                                    embeds[
                                        -1
                                    ].description += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index}.** {member.mention} - 0 seconds\n"

                            else:
                                # print("fields more than 24")
                                new_embed = discord.Embed(
                                    color=0xED4348,
                                    title="<:ERMMisc:1113215605424795648> Leaderboard",
                                )

                                new_embed.set_author(
                                    name=ctx.author.name,
                                    icon_url=ctx.author.display_avatar.url,
                                )
                                new_embed.set_thumbnail(url=ctx.guild.icon.url)
                                new_embed.description = ""
                                new_embed.description += f"<:ERMList:1111099396990435428> **Total Shifts**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
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
                            ].description = f"<:ERMList:1111099396990435428> **Total Shifts**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index}.** {member.mention} - 0 seconds\n"
                        else:
                            embeds[
                                -1
                            ].description += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index + 1}.** {member.mention} - 0 seconds\n"

                    else:
                        # print("fields more than 24")
                        new_embed = discord.Embed(
                            color=0xED4348,
                            title="<:ERMMisc:1113215605424795648> Leaderboard",
                        )

                        new_embed.set_author(
                            name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                        )
                        new_embed.set_thumbnail(url=ctx.guild.icon.url)
                        new_embed.description = ""
                        new_embed.description += f"<:ERMList:1111099396990435428> **Total Shifts**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **{index + 1}.** {member.mention} - 0 seconds\n"
                        embeds.append(new_embed)

        combined = []
        for list_item in data:
            for item in list_item:
                combined.append(item)

        # print(all_staff)
        # print(sorted_staff)
        # print(buffer)

        if my_data is not None:
            ordinal_formatted = ordinal(my_data["index"] + 1)
            if "quota" in configItem["shift_management"].keys():
                quota_seconds = configItem["shift_management"]["quota"]

            embeds[
                0
            ].description += f"\n\n<:ERMList:1111099396990435428> **Your Stats**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** {td_format(datetime.timedelta(seconds=my_data['total_seconds']))}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Rank:** {ordinal_formatted}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Quota:** {'<:ERMCheck:1111089850720976906>' if my_data['total_seconds'] >= quota_seconds else '<:ERMClose:1111101633389146223>'}"
        else:
            embeds[
                0
            ].description += f"\n\n<:ERMList:1111099396990435428> **Your Stats**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** 0 seconds\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Quota:** <:ERMClose:1111101633389146223>"

        try:
            bbytes = buffer.encode("utf-8")
        except Exception as e:
            # print(e)
            if len(embeds) == 0:
                return await failure_embed(ctx, "no shift data has been found.")
            elif embeds[0].description is None:
                return await failure_embed(ctx, "no shift data has been found.")
            else:
                if ctx.interaction:
                    interaction = ctx.interaction
                else:
                    interaction = ctx

                menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, timeout=None)
                for embed in embeds:
                    if embed is not None:
                        menu.add_pages([embed])

                if len(menu.pages) == 1:
                    return await ctx.reply(
                        embed=embed,
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the leaderboard for **{ctx.guild.name}**.",
                    )

                menu.add_buttons([ViewButton.back(), ViewButton.next()])
                await menu.start()

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
                view=view,
            )
        else:
            file = discord.File(fp=BytesIO(bbytes), filename="shift_leaderboard.txt")
            if ctx.interaction:
                interaction = ctx
            else:
                interaction = ctx

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
                await interaction.response.send_message(file=file, ephemeral=True)

            menu = ViewMenu(
                interaction,
                menu_type=ViewMenu.TypeEmbed,
                show_page_director=True,
                timeout=None,
            )
            for embed in embeds:
                if embed is not None:
                    menu.add_page(
                        embed=embed,
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the leaderboard for **{ctx.guild.name}**.",
                    )

            menu._pc = _PageController(menu.pages)
            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            menu._ViewMenu__view.add_item(
                CustomExecutionButton(
                    ctx.author.id,
                    "Download Shift Leaderboard",
                    discord.ButtonStyle.gray,
                    emoji=None,
                    func=response_func,
                )
            )
            if len(menu.pages) == 1:
                try:
                    return await msg.edit(
                        embed=embed,
                        file=file,
                        view=view,
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the leaderboard for **{ctx.guild.name}**.",
                    )
                except UnboundLocalError:
                    return await ctx.reply(
                        embed=embed,
                        file=file,
                        view=view,
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the leaderboard for **{ctx.guild.name}**.",
                    )
            if view:
                for child in view.children:
                    menu._ViewMenu__view.add_item(child)

            try:
                await msg.edit(
                    embed=embeds[0],
                    view=menu._ViewMenu__view,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the leaderboard for **{ctx.guild.name}**.",
                )
            except UnboundLocalError:
                await ctx.reply(
                    embed=embeds[0],
                    view=menu._ViewMenu__view,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's the leaderboard for **{ctx.guild.name}**.",
                )

    @duty.command(
        name="clearall",
        description="Clears all of the shift data.",
        extras={"category": "Shift Management"},
        aliases=["shift-cla"],
    )
    @is_management()
    async def clearall(self, ctx):
        if self.bot.shift_management_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        try:
            configItem = await bot.settings.find_by_id(ctx.guild.id)
        except:
            return await failure_embed(
                ctx,
                "the server has not been set up yet. Please run `/setup` to set up the server.",
            )

        view = YesNoMenu(ctx.author.id)

        msg = await ctx.reply(
            view=view,
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, are you sure you would like to do this? I can't reverse this action.",
        )
        await view.wait()
        if view.value is False:
            return await failure_embed(ctx, "Successfully cancelled.")

        async for document in bot.shift_management.shifts.db.find(
            {"Guild": ctx.guild.id}
        ):
            await bot.shift_management.shifts.db.delete_one({"_id": document["_id"]})

        await msg.edit(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, alright. I've erased all of your servers shift data.",
            view=None,
        )


async def setup(bot):
    await bot.add_cog(ShiftManagement(bot))
