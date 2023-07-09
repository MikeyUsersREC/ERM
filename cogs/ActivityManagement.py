import datetime
from io import BytesIO
import pytz
import discord
import gspread as gspread
import num2words
from dateutil import parser
from decouple import config
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials
from reactionmenu import ViewButton, ViewMenu

from erm import credentials_dict, is_management, scope
from menus import CustomSelectMenu, GoogleSpreadsheetModification
from utils.timestamp import td_format
from utils.utils import invis_embed, request_response, failure_embed


class ActivityManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="activity")
    async def activity(self, ctx):
        return await ctx.reply(
            f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** you have not entered a subcommand."
        )

    @activity.command(
        name="report",
        description="Send an activity report",
        extras={"category": "Activity Management"},
    )
    @is_management()
    async def activity_report(self, ctx):
        # return await invis_embed(ctx,  "This feature has not been released yet.")
        bot = self.bot
        if bot.shift_management_disabled:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="1 day",
                    value="1d",
                    description="Shows the activity of staff members within the last day",
                ),
                discord.SelectOption(
                    label="7 days",
                    value="7d",
                    description="Shows the activity of staff members within the last week",
                ),
                discord.SelectOption(
                    label="14 days",
                    value="14d",
                    description="Shows the activity of staff members within the last 2 weeks",
                ),
                discord.SelectOption(
                    label="28 days",
                    value="28d",
                    description="Shows the activity of staff members within the last month",
                ),
                discord.SelectOption(
                    label="Custom",
                    value="custom",
                    description="Choose a custom time period",
                ),
            ],
        )
        activity_msg = await ctx.reply(
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, choose a period of time for me to report on.",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return await activity_msg.edit(
                content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** you took too long to respond. Prompt timed out."
            )

        starting_period = None
        ending_period = None
        if view.value.endswith("d"):
            amount_of_days = view.value.removesuffix("d")
            amount = int(amount_of_days)
            datetime_obj = datetime.datetime.now(tz=pytz.UTC).replace(tzinfo=pytz.UTC)
            ending_period = datetime_obj
            starting_period = datetime_obj - datetime.timedelta(days=amount)
        elif view.value == "custom":
            msg = await request_response(
                bot,
                ctx,
                embed=discord.Embed(
                    color=0xED4348,
                    description="<:ERMModify:1111100050718867577> **PRO TIP:** Use `dd/mm/yyyy` for time formatting.\n*e.g. 21/04/2023*",
                ),
                question="when do you want this period of time to start?",
            )
            try:
                start_date = parser.parse(msg.content)
            except:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** we were unable to translate your time. Try again in the correct format."
                )

            msg = await request_response(
                bot, ctx, "When do you want this period of time to end?"
            )
            try:
                end_date = parser.parse(msg.content)
            except:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** we were unable to translate your time. Try again in the correct format."
                )

            starting_period = start_date
            ending_period = end_date

        embeds = []
        embed = discord.Embed(
            title="<:ERMSchedule:1111091306089939054> Activity Report", color=0xED4348
        )

        embed.set_footer(text="Click 'Next' to see users who are on LoA.")

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

                    msg = await activity_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you have {num2words.num2words(len(shift_types))} shift types - {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select which one you want to view the activity for.",
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
                                return await activity_msg.edit(
                                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** something really bad just happened. Please contact support."
                                )

        all_staff = [{"id": None, "total_seconds": 0, "moderations": 0}]

        if shift_type != 0 and shift_type is not None:
            print(f"Starting period: {starting_period}")
            print(f"Ending period: {ending_period}")
            quantifiers = {
                "$gte": starting_period.timestamp(),
                "$lte": ending_period.timestamp(),
            }

            async for document in bot.shift_management.shifts.db.find(
                {
                    "StartEpoch": quantifiers,
                    "Guild": ctx.guild.id,
                    "Type": shift_type["name"],
                    "EndEpoch": {"$ne": 0},
                }
            ):
                total_seconds = 0
                moderations = 0
                break_seconds = 0

                for breaks in document["Breaks"]:
                    break_seconds += breaks["EndEpoch"] - breaks["StartEpoch"]

                print(document)
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
                moderations += len(document["Moderations"])
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
            print(f"Starting period: {starting_period}")
            print(f"Ending period: {ending_period}")
            quantifiers = {
                "$gte": starting_period.timestamp(),
                "$lte": ending_period.timestamp(),
            }

            async for document in bot.shift_management.shifts.db.find(
                {
                    "StartEpoch": quantifiers,
                    "Guild": ctx.guild.id,
                    "EndEpoch": {"$ne": 0},
                }
            ):
                total_seconds = 0
                moderations = 0
                break_seconds = 0

                for breaks in document["Breaks"]:
                    break_seconds += breaks["EndEpoch"] - breaks["StartEpoch"]
                print(document)

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
                moderations += len(document["Moderations"])
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

        staff_roles = []
        config_item = await bot.settings.find_by_id(ctx.guild.id)
        if config_item["staff_management"].get("role"):
            if config_item["staff_management"].get("role") is not None:
                if isinstance(config_item["staff_management"]["role"], int):
                    staff_roles = [
                        ctx.guild.get_role(config_item["staff_management"]["role"])
                    ]
                elif isinstance(config_item["staff_management"]["role"], list):
                    for role_id in config_item["staff_management"]["role"]:
                        if isinstance(role_id, int):
                            staff_roles.append(ctx.guild.get_role(role_id))

        for role in staff_roles.copy():
            if role is None:
                staff_roles.remove(role)

        for role in staff_roles:
            if isinstance(role, discord.Role):
                for member in role.members:
                    if member.id not in [item["id"] for item in all_staff]:
                        all_staff.append(
                            {"id": member.id, "total_seconds": 0, "moderations": 0}
                        )

        management_roles = []
        config_item = await bot.settings.find_by_id(ctx.guild.id)
        if "management_role" in config_item["staff_management"]:
            if config_item["staff_management"].get("management_role") is not None:
                if isinstance(config_item["staff_management"]["management_role"], int):
                    management_roles = [
                        ctx.guild.get_role(
                            config_item["staff_management"]["management_role"]
                        )
                    ]
                elif isinstance(
                    config_item["staff_management"]["management_role"], list
                ):
                    for role_id in config_item["staff_management"]["management_role"]:
                        if isinstance(role_id, int):
                            management_roles.append(ctx.guild.get_role(role_id))

        for role in management_roles:
            if isinstance(role, discord.Role):
                for member in role.members:
                    if member.id not in [item["id"] for item in all_staff]:
                        all_staff.append(
                            {"id": member.id, "total_seconds": 0, "moderations": 0}
                        )

        # Get all members with manage_messages or manage_guild
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
            if member.id not in [item["id"] for item in all_staff]:
                all_staff.append(
                    {"id": member.id, "total_seconds": 0, "moderations": 0}
                )

        loa_staff = []
        print(all_staff)

        async for document in bot.loas.db.find({}):
            if document["guild_id"] == ctx.guild.id:
                if document["expiry"] >= starting_period.timestamp():
                    if document["denied"] is False and document["accepted"] is True:
                        loa_staff.append(
                            {
                                "_id": document["_id"],
                                "member": document["user_id"],
                                "expiry": document["expiry"],
                                "reason": document["reason"],
                                "type": document["type"],
                            }
                        )

        if len(all_staff) == 0:
            return await activity_msg.edit(
                content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** no shifts were made in this server."
            )
        for item in all_staff:
            if item["id"] is None:
                all_staff.remove(item)

        sorted_staff = sorted(all_staff, key=lambda x: x["total_seconds"], reverse=True)

        string = ""
        loas = []
        try:
            settings = await bot.settings.find_by_id(ctx.guild.id)
            quota = settings["shift_management"]["quota"]
        except:
            quota = 0

        data = []
        for index, value in enumerate(sorted_staff):
            print(value)
            member = ctx.guild.get_member(value["id"])
            if value["total_seconds"] > quota:
                met_quota = "<:ERMCheck:1111089850720976906>"
            else:
                met_quota = "<:ERMClose:1111101633389146223>"
            if member:
                string += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=value['total_seconds']))} {met_quota}\n"
                if value["moderations"]:
                    data.append(
                        [
                            index + 1,
                            "YES"
                            if met_quota == "<:ERMCheck:1111089850720976906>"
                            else "NO",
                            f"{member.name}",
                            member.top_role.name,
                            td_format(
                                datetime.timedelta(seconds=value["total_seconds"])
                            ),
                            value["moderations"],
                        ]
                    )
                else:
                    data.append(
                        [
                            index + 1,
                            "YES"
                            if met_quota == "<:ERMCheck:1111089850720976906>"
                            else "NO",
                            f"{member.name}",
                            member.top_role.name,
                            td_format(
                                datetime.timedelta(seconds=value["total_seconds"])
                            ),
                            0,
                        ]
                    )
            else:
                string += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**{index + 1}.** `{value['id']}` - {td_format(datetime.timedelta(seconds=value['total_seconds']))} {met_quota}\n"
                data.append(
                    [
                        index + 1,
                        "YES"
                        if met_quota == "<:ERMCheck:1111089850720976906>"
                        else "NO",
                        value["id"],
                        "Not in server",
                        td_format(datetime.timedelta(seconds=value["total_seconds"])),
                        value["moderations"],
                    ]
                )

        combined = []
        for item in data:
            for i in item:
                combined.append(i)

        additional_data = []

        for index, value in enumerate(loa_staff):
            if value["member"] in [item["id"] for item in all_staff]:
                item = None
                print(value["member"])

                for i in all_staff:
                    print(i)
                    if value["member"] == i["id"]:
                        print(i)
                        item = i

                print(item)

                formatted_data = td_format(
                    datetime.timedelta(seconds=item["total_seconds"])
                )
            else:
                formatted_data = "0 seconds"

            print(value)

            member = discord.utils.get(ctx.guild.members, id=value["member"])
            if member:
                try:
                    loas.append(
                        (
                            f"{member.name}",
                            value["type"],
                            value["reason"],
                            formatted_data,
                            td_format(
                                datetime.timedelta(
                                    seconds=value["expiry"]
                                    - int(value["_id"].split("_")[2])
                                )
                            ),
                            value["_id"].split("_")[2],
                            value["expiry"],
                        )
                    )
                    additional_data.append(
                        [
                            f"{member.name}",
                            member.top_role.name,
                            formatted_data,
                            value["type"],
                            value["_id"].split("_")[2],
                            value["expiry"],
                        ]
                    )
                except:
                    pass

        additional_combined = []
        for item in additional_data:
            for i in item:
                additional_combined.append(i)

        splitted_str = []
        resplit = string.splitlines()

        strAR = ""
        for index, i in enumerate(resplit):
            strAR += f"{i}\n"
            if index % 4 == 0:
                splitted_str.append(i)
            else:
                splitted_str[-1] += f"\n{i}"
        if splitted_str == []:
            splitted_str.append(string)

        try:
            bbytes = strAR.encode("utf-8")
        except:
            return await activity_msg.edit(
                content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** no shift data was found."
            )

        embeds.append(embed)

        for string_obj in splitted_str:
            if len(embeds[-1].fields) == 0:
                embeds[-1].add_field(
                    name="<:ERMUser:1111098647485108315> Shifts", value=string_obj
                )
            else:
                if len(embeds[-1].fields) >= 3:
                    new_embed = discord.Embed(
                        title="<:ERMSchedule:1111091306089939054> Activity Report",
                        color=0xED4348,
                    )
                    new_embed.add_field(
                        name="<:ERMUser:1111098647485108315> Shifts", value=string_obj
                    )
                    embeds.append(new_embed)
                else:
                    embeds[-1].add_field(name="\u200b", value=string_obj, inline=False)

        embed2 = discord.Embed(
            title="<:ERMActivity:1113209176664064060> Activity Notices", color=0xED4348
        )

        embed2.set_footer(text="Click 'Next' to see more information.")

        embeds.append(embed2)
        for member, type, reason, total_time, duration, start, end in loas:
            if len(embeds[-1].fields) >= 3:
                new_embed = discord.Embed(
                    title="<:ERMSchedule:1111091306089939054> Activity Notices",
                    color=0xED4348,
                )
                new_embed.add_field(
                    name=f"<:ERMUser:1111098647485108315> {member}",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Type:** {'Reduced Activity' if type.lower() == 'ra' else 'Leave of Absence'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Reason:** {reason}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time on Shift:** {total_time}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Duration:** {duration}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Start:** <t:{start}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Expires at:** <t:{end}>",
                    inline=False,
                )
                embeds.append(new_embed)
            else:
                embeds[-1].add_field(
                    name=f"<:ERMUser:1111098647485108315> {member}",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Type:** {'Reduced Activity' if type.lower() == 'ra' else 'Leave of Absence'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {reason}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Time on Shift:** {total_time}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Duration:** {duration}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Start:** <t:{start}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Expires at:** <t:{end}>",
                    inline=False,
                )

        for index, em in enumerate(embeds):
            if len(em.fields) == 0:
                print("0 em fields")
                if em.title == "<:ERMSchedule:1111091306089939054> Activity Notices":
                    em.add_field(
                        name="<:ERMUser:1111098647485108315> Currently on LoA",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>No Activity Notices found.",
                    )
                    embeds[index] = em
                else:
                    em.add_field(
                        name="<:ERMActivity:1113209176664064060> Shifts",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>No shifts found.",
                    )
                    embeds[index] = em
            elif em.fields[0].value == "":
                print("empty em field")
                if em.title == "<:ERMSchedule:1111091306089939054> Activity Notices":
                    em.set_field_at(
                        name="<:ERMUser:1111098647485108315> Currently on LoA",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>No Activity Notices found.",
                        index=0,
                    )
                    embeds[index] = em
                else:
                    em.set_field_at(
                        name="<:ERMSchedule:1111091306089939054> Shifts",
                        value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>No shifts found.",
                        index=0,
                    )
                    embeds[index] = em

        if ctx.interaction:
            gtx = ctx.interaction
        else:
            gtx = ctx

        menu = ViewMenu(
            gtx, menu_type=ViewMenu.TypeEmbed, show_page_director=True, timeout=None
        )
        for page_embed in embeds:
            menu.add_page(embed=page_embed, content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** here is the activity report for **{ctx.guild.name}**.")

        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        print(bbytes)
        file = discord.File(fp=BytesIO(bbytes), filename="raw_activity_report.txt")

        async def task():
            await ctx.reply(
                file=file,
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, here's a file preview of the activity report.",
            )

        async def google_task():
            msg = await ctx.reply(
                content=f"<a:Loading:1044067865453670441>**{ctx.author.name}**, we're loading your Google Spreadsheet."
            )

            client = gspread.authorize(
                ServiceAccountCredentials.from_json_keyfile_dict(
                    credentials_dict, scope
                )
            )
            sheet = client.copy(
                config("ACTIVITY_REPORT_ID"), ctx.guild.name, copy_permissions=True
            )
            new_sheet = sheet.get_worksheet(0)
            try:
                new_sheet.update_cell(4, 2, f'=IMAGE("{ctx.guild.icon.url}")')
            except AttributeError:
                pass

            cell_list = new_sheet.range("D13:I999")
            for c, n_v in zip(cell_list, combined):
                c.value = str(n_v)

            new_sheet.update_cells(cell_list, "USER_ENTERED")
            LoAs = sheet.get_worksheet(1)
            LoAs.update_cell(4, 2, f'=IMAGE("{ctx.guild.icon.url}")')
            cell_list = LoAs.range("D13:I999")
            for cell, new_value in zip(cell_list, additional_combined):
                if cell.col == 8 or cell.col == 9:
                    cell.value = f"=({new_value}/ 86400 + DATE(1970, 1, 1))"
                else:
                    print(f"{cell.col} {new_value}")
                    cell.value = str(new_value)
            LoAs.update_cells(cell_list, "USER_ENTERED")

            sheet.share(None, perm_type="anyone", role="writer")

            view = GoogleSpreadsheetModification(
                credentials_dict, scope, "Open Google Spreadsheet", sheet.url
            )

            await msg.edit(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, good news! We have your spreadsheet. You can access it with the button below.",
                view=view,
            ),

            menu.remove_button(spread)
            await menu.refresh_menu_items()

        def taskWrapper():
            bot.loop.create_task(task())

        def googleTaskWrapper():
            bot.loop.create_task(google_task())

        followUp = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(taskWrapper)
        )

        googleFollowUp = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(googleTaskWrapper)
        )
        menu.add_button(
            ViewButton(
                style=discord.ButtonStyle.secondary,
                label="Not your expected result?",
                custom_id=ViewButton.ID_CALLER,
                followup=followUp,
            )
        )

        spread = ViewButton(
            style=discord.ButtonStyle.secondary,
            label="Google Spreadsheet",
            custom_id=ViewButton.ID_CALLER,
            followup=googleFollowUp,
        )
        menu.add_button(spread)
        await menu.start()
        await activity_msg.delete()


async def setup(bot):
    await bot.add_cog(ActivityManagement(bot))
