import datetime
import json

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from reactionmenu import ViewButton, ViewMenu

from erm import crp_data_to_mongo, generator, is_management, is_staff
from menus import (
    ChannelSelect,
    CustomisePunishmentType,
    CustomModalView,
    CustomSelectMenu,
    EditWarning,
    RemoveWarning,
    RequestDataView,
)
from utils.autocompletes import punishment_autocomplete, user_autocomplete
from utils.utils import invis_embed, removesuffix


class Punishments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="modstats",
        description="View all information of moderations you've made",
        extras={
            "category": "Punishments"
        }
    )
    @is_staff()
    async def modstats(self, ctx, user: discord.Member = None):
        bot = self.bot
        settings = await bot.settings.find_by_id(ctx.guild.id)
        if settings is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if user == None:
            user = ctx.author

        selected = None
        async for document in bot.shift_storage.db.find({"_id": user.id}):
            selected = document

        loas = []
        async for document in bot.loas.db.find({"user_id": user.id}):
            loas.append(document)

        if not selected:
            moderations = []
            shifts = []
        else:
            moderations = [i for i in list(filter(
                lambda x: (x if x else {}).get('moderations') is not None and (x if x else {})['guild'] == ctx.guild.id,
                selected['shifts'])) if i is not None]
            print(moderations)
            moderations = []
            for i in moderations:
                moderations = [x for x in i['moderations'] if x is not None]
            print(moderations)
            shifts = [x for x in [x['shifts'] for x in
                                  list(filter(lambda x: (x if x else {}).get('shifts') is True, selected['shifts']))] if
                      (x if x else {}) is not None and (x if x else {})['guild'] == ctx.guild.id]

        leaves = list(filter(lambda x: x['type'] == "LoA", loas))
        reduced_activity = list(filter(lambda x: x['type'] == "RA", loas))
        accepted_leaves = list(filter(lambda x: x['accepted'] == True, leaves))
        denied_leaves = list(filter(lambda x: x['denied'] == True, leaves))
        accepted_ras = list(filter(lambda x: x['accepted'] == True, reduced_activity))
        denied_ras = list(filter(lambda x: x['denied'] == True, reduced_activity))

        embed = discord.Embed(
            title="<:SConductTitle:1053359821308567592> Moderation Statistics",
            description="*Moderation statistics displays relevant information about a user.*",
            color=0x2e3136
        )

        INVISIBLE_CHAR = "‎"

        embed.add_field(
            name="<:MalletWhite:1035258530422341672> Moderations",
            value=f"<:ArrowRightW:1035023450592514048> **Moderations:** {len(moderations)}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Warnings:** {len(list(filter(lambda x: x['Type'] == 'Warning', moderations)))}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Kicks:** {len(list(filter(lambda x: x['Type'] == 'Kick', moderations)))}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Bans:** {len(list(filter(lambda x: x['Type'] == 'Ban', moderations)))}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **BOLOs:** {len(list(filter(lambda x: x['Type'] in ['BOLO', 'Bolo'], moderations)))}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Custom:** {len(list(filter(lambda x: x['Type'] not in ['Warning', 'Kick', 'Ban', 'BOLO', 'Bolo'], moderations)))}",
            inline=True
        )
        embed.add_field(
            name="<:Clock:1035308064305332224> Activity Notices",
            value=f"<:ArrowRightW:1035023450592514048> **LOAs:** {len(leaves)}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Accepted:** {len(accepted_leaves)}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Denied:** {len(denied_leaves)}\n<:ArrowRightW:1035023450592514048> **Reduced Activity:** {len(reduced_activity)}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Accepted:** {len(accepted_ras)}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Denied:** {len(denied_ras)}",
            inline=True
        )

        embed.add_field(
            name="<:Resume:1035269012445216858> Shifts",
            value=f"<:ArrowRightW:1035023450592514048> **Shifts:** {len(shifts)}\n<:ArrowRightW:1035023450592514048> **Shift Time:** {td_format(datetime.timedelta(seconds=sum([(x['endTimestamp']) - (x['startTimestamp']) for x in shifts])))}\n<:ArrowRightW:1035023450592514048> **Average Shift Time:** {td_format(datetime.timedelta(seconds=((sum([(x['endTimestamp']) - (x['startTimestamp']) for x in shifts]) / (len([(x['endTimestamp']) - (x['startTimestamp']) for x in shifts]))) if len([(x['endTimestamp']) - (x['startTimestamp']) for x in shifts]) != 0 else 1) - 1))}\n",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="punish",
        description="Punish a user",
        extras={"category": "Punishments"},
        usage="punish <user> <type> <reason>",
    )
    @is_staff()
    @app_commands.autocomplete(type=punishment_autocomplete)
    @app_commands.autocomplete(user=user_autocomplete)
    @app_commands.describe(type="The type of punishment to give.")
    @app_commands.describe(
        user="What's their username? You can mention a Discord user, or provide a ROBLOX username."
    )
    @app_commands.describe(reason="What is your reason for punishing this user?")
    async def punish(self, ctx, user: str, type: str, *, reason: str):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        generic_warning_types = ["Warning", "Kick", "Ban", "BOLO"]

        warning_types = await bot.punishment_types.find_by_id(ctx.guild.id)
        if warning_types is None:
            warning_types = {"_id": ctx.guild.id, "types": generic_warning_types}
            await bot.punishment_types.insert(warning_types)
            warning_types = warning_types["types"]
        else:
            warning_types = warning_types["types"]

        designated_channel = None
        settings = await bot.settings.find_by_id(ctx.guild.id)
        if settings:
            warning_type = None
            for warning in warning_types:
                if isinstance(warning, str):
                    if warning.lower() == type.lower():
                        warning_type = warning
                elif isinstance(warning, dict):
                    if warning["name"].lower() == type.lower():
                        warning_type = warning

            if isinstance(warning_type, str):
                if settings["customisation"].get("kick_channel"):
                    if settings["customisation"]["kick_channel"] != "None":
                        if type.lower() == "kick":
                            designated_channel = bot.get_channel(
                                settings["customisation"]["kick_channel"]
                            )
                if settings["customisation"].get("ban_channel"):
                    if settings["customisation"]["ban_channel"] != "None":
                        if type.lower() == "ban":
                            designated_channel = bot.get_channel(
                                settings["customisation"]["ban_channel"]
                            )
                if settings["customisation"].get("bolo_channel"):
                    if settings["customisation"]["bolo_channel"] != "None":
                        if type.lower() == "bolo":
                            designated_channel = bot.get_channel(
                                settings["customisation"]["bolo_channel"]
                            )
            else:
                if isinstance(warning_type, dict):
                    if "channel" in warning_type.keys():
                        if warning_type["channel"] != "None":
                            designated_channel = bot.get_channel(
                                warning_type["channel"]
                            )

        print(designated_channel)

        if len(reason) > 800:
            reason = reason[:797] + "..."

        if designated_channel is None:
            try:
                designated_channel = bot.get_channel(settings["punishments"]["channel"])
            except KeyError:
                return await invis_embed(
                    ctx,
                    "I could not find a designated channel for logging punishments. Ask a server administrator to use `/config change`.",
                )
        if type.lower() == "tempban":
            return await invis_embed(
                ctx,
                f"Tempbans are currently not possible due to discord limitations. Please use the corresponding command `/tempban` for an alternative.",
            )

        if type.lower() == "warn":
            type = "Warning" if "Warning" in warning_types else "Warning"

        already_types = []
        for item in warning_types:
            if isinstance(item, dict):
                already_types.append(item["name"].lower())
            else:
                already_types.append(item.lower())

        if type.lower() not in already_types:
            return await invis_embed(
                ctx,
                f"`{type}` is an invalid punishment type. Ask your server administrator to add this type via `/punishment manage`",
            )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://users.roblox.com/v1/usernames/users",
                json={"usernames": [user]},
            ) as r:
                if r.status == 200:
                    robloxUser = await r.json()
                    if len(robloxUser["data"]) == 0:
                        return await invis_embed(
                            ctx, f"No user found with the name `{user}`"
                        )
                    robloxUser = robloxUser["data"][0]
                    Id = robloxUser["id"]
                    async with session.get(
                        f"https://users.roblox.com/v1/users/{Id}"
                    ) as r:
                        requestJson = await r.json()
                else:
                    async with session.post(
                        f"https://users.roblox.com/v1/usernames/users",
                        json={"usernames": [user]},
                    ) as r:
                        robloxUser = await r.json()
                        if len(robloxUser["data"]) != 0:
                            robloxUser = robloxUser["data"][0]
                            Id = robloxUser["id"]
                            async with session.get(
                                f"https://users.roblox.com/v1/users/{Id}"
                            ) as r:
                                requestJson = await r.json()
                        else:
                            try:
                                userConverted = await (
                                    discord.ext.commands.MemberConverter()
                                ).convert(ctx, user.replace(" ", ""))
                                if userConverted:
                                    verified_user = await bot.verification.find_by_id(
                                        userConverted.id
                                    )
                                    if verified_user:
                                        Id = verified_user["roblox"]
                                        async with session.get(
                                            f"https://users.roblox.com/v1/users/{Id}"
                                        ) as r:
                                            requestJson = await r.json()
                                    else:
                                        async with aiohttp.ClientSession(
                                            headers={"api-key": bot.bloxlink_api_key}
                                        ) as newSession:
                                            async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}"
                                            ) as r:
                                                tempRBXUser = await r.json()
                                                if tempRBXUser["success"]:
                                                    tempRBXID = tempRBXUser["user"][
                                                        "robloxId"
                                                    ]
                                                else:
                                                    return await invis_embed(
                                                        ctx,
                                                        f"No user found with the name `{userConverted.display_name}`",
                                                    )
                                                Id = tempRBXID
                                                async with session.get(
                                                    f"https://users.roblox.com/v1/users/{Id}"
                                                ) as r:
                                                    requestJson = await r.json()
                            except discord.ext.commands.MemberNotFound:
                                return await invis_embed(
                                    ctx, f"No member found with the query: `{user}`"
                                )

        print(requestJson)
        try:
            data = requestJson["data"]
        except KeyError:
            data = [requestJson]

        if not "data" in locals():
            data = [requestJson]

        Embeds = []

        for dataItem in data:
            embed = discord.Embed(
                title=f"{dataItem['name']} ({dataItem['id']})", color=0x2E3136
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://thumbnails.roblox.com/v1/users/avatar?userIds={dataItem["id"]}&size=420x420&format=Png'
                ) as f:
                    if f.status == 200:
                        avatar = await f.json()
                        Headshot_URL = avatar["data"][0]["imageUrl"]
                    else:
                        Headshot_URL = ""

            user = await bot.warnings.find_by_id(dataItem["name"].lower())
            if user is None:
                embed.description = """
                    <:ArrowRightW:1035023450592514048>**Warnings:** 0
                    <:ArrowRightW:1035023450592514048>**Kicks:** 0
                    <:ArrowRightW:1035023450592514048>**Bans:** 0
                    <:ArrowRightW:1035023450592514048>**Custom:** 0

                    `Banned:` <:ErrorIcon:1035000018165321808>
                    """
            else:
                warnings = 0
                kicks = 0
                bans = 0
                bolos = 0
                custom = 0

                for warningItem in user["warnings"]:
                    if warningItem["Guild"] == ctx.guild.id:
                        if warningItem["Type"] == "Warning":
                            warnings += 1
                        elif warningItem["Type"] == "Kick":
                            kicks += 1
                        elif warningItem["Type"] == "Ban":
                            bans += 1
                        elif warningItem["Type"] == "Temporary Ban":
                            bans += 1
                        elif warningItem["Type"].lower() == "bolo":
                            bolos += 1
                        else:
                            custom += 1
                if bans != 0:
                    banned = "<:CheckIcon:1035018951043842088>"
                else:
                    banned = "<:ErrorIcon:1035000018165321808>"

                if bolos >= 1:
                    embed.description = f"<:ArrowRightW:1035023450592514048>**Warnings:** {warnings}\n<:ArrowRightW:1035023450592514048>**Kicks:** {kicks}\n<:ArrowRightW:1035023450592514048>**Bans:** {bans}\n<:ArrowRightW:1035023450592514048>**Custom:** {custom}\n\n<:WarningIcon:1035258528149033090> **BOLOs:**\n<:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo active` before continuing.\n\n`Banned:` {banned}"
                else:
                    embed.description = f"<:ArrowRightW:1035023450592514048>**Warnings:** {warnings}\n<:ArrowRightW:1035023450592514048>**Kicks:** {kicks}\n<:ArrowRightW:1035023450592514048>**Bans:** {bans}\n<:ArrowRightW:1035023450592514048>**Custom:** {custom}\n`Banned:` {banned}"
            embed.set_thumbnail(url=Headshot_URL)
            embed.set_footer(
                text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.'
            )

            Embeds.append(embed)

        if ctx.interaction:
            gtx = ctx.interaction
        else:
            gtx = ctx

        menu = ViewMenu(
            gtx, menu_type=ViewMenu.TypeEmbed, show_page_director=False, timeout=None
        )

        async def warn_function(ctx, menu, designated_channel=None):
            user = menu.message.embeds[0].title.split(" ")[0]
            await menu.stop(disable_items=True)
            default_warning_item = {
                "_id": user.lower(),
                "warnings": [
                    {
                        "id": next(generator),
                        "Type": f"{type.lower().title()}",
                        "Reason": reason,
                        "Moderator": [ctx.author.name, ctx.author.id],
                        "Time": ctx.message.created_at.strftime("%m/%d/%Y, %H:%M:%S"),
                        "Guild": ctx.guild.id,
                    }
                ],
            }

            singular_warning_item = {
                "id": next(generator),
                "Type": f"{type.lower().title()}",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime("%m/%d/%Y, %H:%M:%S"),
                "Guild": ctx.guild.id,
            }

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await invis_embed(
                    ctx,
                    "The server has not been set up yet. Please run `/setup` to set up the server.",
                )

            if not configItem["punishments"]["enabled"]:
                return await invis_embed(
                    ctx,
                    "This server has punishments disabled. Please run `/config change` to enable punishments.",
                )

            embed = discord.Embed(title=user, color=0x2E3136)
            embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
            try:
                embed.set_footer(text="Staff Logging Module")
            except:
                pass
            embed.add_field(
                name="<:staff:1035308057007230976> Staff Member",
                value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
                inline=False,
            )
            embed.add_field(
                name="<:WarningIcon:1035258528149033090> Violator",
                value=f"<:ArrowRight:1035003246445596774> {menu.message.embeds[0].title.split(' ')[0]}",
                inline=False,
            )
            embed.add_field(
                name="<:MalletWhite:1035258530422341672> Type",
                value=f"<:ArrowRight:1035003246445596774> {type.lower().title()}",
                inline=False,
            )
            embed.add_field(
                name="<:QMark:1035308059532202104> Reason",
                value=f"<:ArrowRight:1035003246445596774> {reason}",
                inline=False,
            )

            if designated_channel is None:
                designated_channel = discord.utils.get(
                    ctx.guild.channels, id=configItem["punishments"]["channel"]
                )

            if not await bot.warnings.find_by_id(user.lower()):
                await bot.warnings.insert(default_warning_item)
            else:
                dataset = await bot.warnings.find_by_id(user.lower())
                dataset["warnings"].append(singular_warning_item)
                await bot.warnings.update_by_id(dataset)

            shift = await bot.shifts.find_by_id(ctx.author.id)

            if shift is not None:
                if "data" in shift.keys():
                    for index, item in enumerate(shift["data"]):
                        if isinstance(item, dict):
                            if item["guild"] == ctx.guild.id:
                                if "moderations" in item.keys():
                                    item["moderations"].append(
                                        {
                                            "id": next(generator),
                                            "Type": f"{type.lower().title()}",
                                            "Reason": reason,
                                            "Moderator": [
                                                ctx.author.name,
                                                ctx.author.id,
                                            ],
                                            "Time": ctx.message.created_at.strftime(
                                                "%m/%d/%Y, %H:%M:%S"
                                            ),
                                            "Guild": ctx.guild.id,
                                        }
                                    )
                                else:
                                    item["moderations"] = [
                                        {
                                            "id": next(generator),
                                            "Type": f"{type.lower().title()}",
                                            "Reason": reason,
                                            "Moderator": [
                                                ctx.author.name,
                                                ctx.author.id,
                                            ],
                                            "Time": ctx.message.created_at.strftime(
                                                "%m/%d/%Y, %H:%M:%S"
                                            ),
                                            "Guild": ctx.guild.id,
                                        }
                                    ]
                                shift["data"][index] = item
                                await bot.shifts.update_by_id(shift)

            success = discord.Embed(
                title=f"<:CheckIcon:1035018951043842088> {type.lower().title()} Logged",
                description=f"<:ArrowRightW:1035023450592514048>**{user}**'s {type.lower()} has been logged.",
                color=0x71C15F,
            )

            roblox_id = (
                menu.message.embeds[0]
                .title.split(" ")[1]
                .replace("(", "")
                .replace(")", "")
            )

            discord_user = None
            async for document in bot.synced_users.db.find({"roblox": roblox_id}):
                discord_user = document["_id"]

            if discord_user:
                try:
                    member = await ctx.guild.fetch_member(discord_user)
                except discord.NotFound:
                    member = None

                if member:
                    should_dm = True

                    async for doc in bot.consent.db.find({"_id": member.id}):
                        if document.get("punishments"):
                            if document.get("punishments") is False:
                                should_dm = False

                    if should_dm:
                        try:
                            personal_embed = discord.Embed(
                                title="<:WarningIcon:1035258528149033090> You have been moderated!",
                                description=f"***{ctx.guild.name}** has moderated you in-game*",
                                color=0x2E3136,
                            )
                            personal_embed.add_field(
                                name="<:MalletWhite:1035258530422341672> Moderation Details",
                                value=f"<:ArrowRightW:1035023450592514048> **Username:** {menu.message.embeds[0].title.split(' ')[0]}\n<:ArrowRightW:1035023450592514048> **Reason:** {reason}\n<:ArrowRightW:1035023450592514048> **Type:** {type.lower().title()}",
                                inline=False,
                            )

                            try:
                                personal_embed.set_author(
                                    name=ctx.guild.name, icon_url=ctx.guild.icon.url
                                )
                            except:
                                personal_embed.set_author(name=ctx.guild.name)

                            await member.send(embed=personal_embed)

                        except:
                            pass

            await menu.message.edit(embed=success)

            await designated_channel.send(embed=embed)

        async def task():
            await warn_function(ctx, menu, designated_channel)

        def taskWrapper():
            bot.loop.create_task(task())

        async def cancelTask():
            embed = discord.Embed(
                title="<:ErrorIcon:1035000018165321808> Cancelled",
                description="<:ArrowRight:1035003246445596774>This punishment has not been logged.",
                color=0xFF3C3C,
            )

            await menu.message.edit(embed=embed)

            await menu.stop(disable_items=True)

        def cancelTaskWrapper():
            bot.loop.create_task(cancelTask())

        followUp = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(taskWrapper)
        )
        cancelFollowup = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(cancelTaskWrapper)
        )

        menu.add_buttons(
            [
                ViewButton(
                    emoji="✅", custom_id=ViewButton.ID_CALLER, followup=followUp
                ),
                ViewButton(
                    emoji="❎", custom_id=ViewButton.ID_CALLER, followup=cancelFollowup
                ),
            ]
        )

        try:
            menu.add_pages(Embeds)
            await menu.start()
        except:
            return await invis_embed(
                ctx,
                "This user does not exist on the Roblox platform. Please try again with a valid username.",
            )

    @commands.hybrid_group(
        name="punishment",
        description="Punishment commands",
        extras={"category": "Punishments"},
    )
    async def punishments(self, ctx):
        pass

    # Punishment Manage command, containing `types`, `void` and `modify`
    @punishments.command(
        name="manage",
        description="Manage punishments",
        extras={"category": "Punishments"},
        aliases=["m"],
    )
    @is_management()
    async def punishment_manage(self, ctx):
        bot = self.bot
        embed = discord.Embed(
            title="<:MalletWhite:1035258530422341672> Punishment Management",
            color=0x2E3136,
        )
        embed.description = "*You can manage the punishments module here. You can view and modify the types of punishments, void punishments, and modify punishments.*"
        embed.add_field(
            name="<:LinkIcon:1044004006109904966> Manage Punishment Types",
            value="<:ArrowRight:1035003246445596774> View and modify the types of punishments.",
            inline=False,
        )
        embed.add_field(
            name="<:EditIcon:1042550862834323597> Modify a Punishment",
            value="<:ArrowRight:1035003246445596774> Modify a punishment's attributes.",
            inline=False,
        )
        embed.add_field(
            name="<:TrashIcon:1042550860435181628> Void a Punishment",
            value="<:ArrowRight:1035003246445596774> Remove a punishment from your server.",
            inline=False,
        )

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Manage Punishment Types",
                    value="manage_types",
                    emoji="<:LinkIcon:1044004006109904966>",
                    description="View and modify the types of punishments.",
                ),
                discord.SelectOption(
                    label="Modify a Punishment",
                    value="modify",
                    emoji="<:EditIcon:1042550862834323597>",
                    description="Modify a punishment's attributes.",
                ),
                discord.SelectOption(
                    label="Void a Punishment",
                    value="void",
                    emoji="<:TrashIcon:1042550860435181628>",
                    description="Remove a punishment from your server.",
                ),
            ],
        )
        msg = await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return
        if view.value == "manage_types":
            Data = await bot.punishment_types.find_by_id(ctx.guild.id)
            if Data is None:
                Data = {"_id": ctx.guild.id, "types": ["Warning", "Kick", "Ban"]}

            embed = discord.Embed(
                title="<:MalletWhite:1035258530422341672> Punishment Types",
                color=0x2E3136,
            )
            for item in Data["types"]:
                if isinstance(item, str):
                    embed.add_field(
                        name=f"<:WarningIcon:1035258528149033090> {item}",
                        value=f"<:ArrowRight:1035003246445596774> Generic: {'<:CheckIcon:1035018951043842088>' if item.lower() in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRight:1035003246445596774> Custom: {'<:CheckIcon:1035018951043842088>' if item.lower() not in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}",
                        inline=False,
                    )
                elif isinstance(item, dict):
                    embed.add_field(
                        name=f"<:WarningIcon:1035258528149033090> {item['name'].lower().title()}",
                        value=f"<:ArrowRight:1035003246445596774> Generic: {'<:CheckIcon:1035018951043842088>' if item['name'].lower() in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRight:1035003246445596774> Custom: {'<:CheckIcon:1035018951043842088>' if item['name'].lower() not in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRight:1035003246445596774> Channel: {bot.get_channel(item['channel']).mention if item['channel'] is not None else 'None'}",
                        inline=False,
                    )

            if len(embed.fields) == 0:
                embed.add_field(
                    name="<:WarningIcon:1035258528149033090> No types",
                    value="<:ArrowRightW:1035023450592514048> No punishment types are available.",
                    inline=False,
                )

            view = CustomisePunishmentType(ctx.author.id)

            msg = await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.value == "create":
                typeName = view.modal.name.value

                # send a view for the channel of the type
                already_types = []
                for item in Data["types"]:
                    if isinstance(item, dict):
                        already_types.append(item["name"].lower())
                    else:
                        already_types.append(item.lower())

                if typeName.lower() in already_types:
                    return await invis_embed(
                        ctx, "This punishment type already exists."
                    )

                embed = discord.Embed(
                    title="<:MalletWhite:1035258530422341672> Create a Punishment Type",
                    color=0x2E3136,
                    description=f"<:ArrowRight:1035003246445596774> What channel do you want this punishment type to be logged in?",
                )
                newview = ChannelSelect(ctx.author.id, limit=1)
                await msg.edit(embed=embed, view=newview)
                await newview.wait()

                if not newview.value:
                    return await invis_embed(
                        ctx,
                        "A channel is required for a punishment type. Please try again.",
                    )

                data = {
                    "name": typeName.lower().title(),
                    "channel": newview.value[0].id,
                }

                Data["types"].append(data)
                await bot.punishment_types.upsert(Data)
                success = discord.Embed(
                    title=f"<:CheckIcon:1035018951043842088> {typeName.lower().title()} Added",
                    description=f"<:ArrowRightW:1035023450592514048>**{typeName.lower().title()}** has been added as a punishment type.",
                    color=0x71C15F,
                )
                await msg.edit(embed=success, view=None)
            else:
                if view.value == "delete":
                    typeName = view.modal.name.value
                    already_types = []
                    for item in Data["types"]:
                        if isinstance(item, dict):
                            already_types.append(item["name"].lower())
                        else:
                            already_types.append(item.lower())
                    if typeName.lower() not in already_types:
                        return await invis_embed(
                            ctx, "This punishment type doesn't exist."
                        )
                    try:
                        Data["types"].remove(typeName.lower().title())
                    except ValueError:
                        for item in Data["types"]:
                            if isinstance(item, dict):
                                if item["name"].lower() == typeName.lower():
                                    Data["types"].remove(item)
                            elif isinstance(item, str):
                                if item.lower() == typeName.lower():
                                    Data["types"].remove(item)
                    await bot.punishment_types.upsert(Data)
                    success = discord.Embed(
                        title=f"<:CheckIcon:1035018951043842088> {typeName.lower().title()} Removed",
                        description=f"<:ArrowRightW:1035023450592514048>**{typeName.lower().title()}** has been removed as a punishment type.",
                        color=0x71C15F,
                    )
                    await msg.edit(embed=success)
        if view.value == "void":
            embed = discord.Embed(
                title="<:MalletWhite:1035258530422341672> Void Punishments",
                color=0x2E3136,
                description=f"<:ArrowRight:1035003246445596774> What punishment do you want to remove?",
            )
            view = RequestDataView(ctx.author.id, "Punishment", "Punishment ID")
            await msg.edit(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            id = view.modal.data.value

            try:
                id = int(id.replace(" ", ""))
            except:
                print(id)
                return await invis_embed(ctx, "`id` is not a valid ID.")

            keyStorage = None
            selected_item = None
            selected_items = []
            item_index = 0

            async for item in bot.warnings.db.find(
                {"warnings": {"$elemMatch": {"id": id}}}
            ):
                for index, _item in enumerate(item["warnings"]):
                    if _item["id"] == id:
                        selected_item = _item
                        selected_items.append(_item)
                        parent_item = item
                        item_index = index
                        break

            if selected_item is None:
                return await invis_embed(ctx, "That punishment does not exist.")

            if selected_item["Guild"] != ctx.guild.id:
                return await invis_embed(
                    ctx,
                    "You are trying to remove a punishment that is not apart of this guild.",
                )

            if len(selected_items) > 1:
                return await invis_embed(
                    ctx,
                    "There is more than one punishment associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.",
                )

            Moderator = discord.utils.get(
                ctx.guild.members, id=selected_item["Moderator"][1]
            )
            if Moderator:
                Moderator = Moderator.mention
            else:
                Moderator = selected_item["Moderator"][0]

            embed = discord.Embed(
                title="<:MalletWhite:1035258530422341672> Remove Punishment",
                description=f"<:ArrowRightW:1035023450592514048> **Type:** {selected_item['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {selected_item['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {Moderator}\n<:ArrowRightW:1035023450592514048> **ID:** {selected_item['id']}\n",
                color=0x2E3136,
            )

            view = RemoveWarning(bot, ctx.author.id)
            await msg.edit(embed=embed, view=view)
            await view.wait()

            if view.value:
                parent_item["warnings"].remove(selected_item)
                await bot.warnings.update_by_id(parent_item)
        if view.value == "modify":
            embed = discord.Embed(
                title="<:MalletWhite:1035258530422341672> Modify Punishments",
                color=0x2E3136,
                description=f"<:ArrowRight:1035003246445596774> What punishment do you want to modify?",
            )

            view = RequestDataView(ctx.author.id, "Punishment", "Punishment ID")
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            id = view.modal.data.value
            try:
                id = int(id)
            except:
                print(id)
                return await invis_embed(ctx, "`id` is not a valid ID.")

            keyStorage = None
            selected_item = None
            selected_items = []
            item_index = 0

            async for item in bot.warnings.db.find(
                {"warnings": {"$elemMatch": {"id": id}}}
            ):
                for index, _item in enumerate(item["warnings"]):
                    if _item["id"] == id:
                        selected_item = _item
                        selected_items.append(_item)
                        parent_item = item
                        item_index = index
                        break

            if selected_item is None:
                return await invis_embed(ctx, "That punishment does not exist.")

            if selected_item["Guild"] != ctx.guild.id:
                return await invis_embed(
                    ctx,
                    "You are trying to edit a punishment that is not apart of this guild.",
                )

            if len(selected_items) > 1:
                return await invis_embed(
                    ctx,
                    "There is more than one punishment associated with this ID. Please contact ERM Support as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.",
                )

            Moderator = discord.utils.get(
                ctx.guild.members, id=selected_item["Moderator"][1]
            )
            if Moderator:
                Moderator = Moderator.mention
            else:
                Moderator = selected_item["Moderator"][0]

            embed = discord.Embed(
                title="<:MalletWhite:1035258530422341672> Edit Punishment",
                description=f"<:ArrowRightW:1035023450592514048> **Type:** {selected_item['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {selected_item['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {Moderator}\n<:ArrowRightW:1035023450592514048> **ID:** {selected_item['id']}\n",
                color=0x2E3136,
            )

            punishment_types = await bot.punishment_types.find_by_id(ctx.guild.id)
            if punishment_types:
                punishment_types = punishment_types["types"]
            view = EditWarning(bot, ctx.author.id, punishment_types or [])
            msg = await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.value == "edit":
                selected_item["Reason"] = view.further_value
                parent_item["warnings"][item_index] = selected_item
                await bot.warnings.update_by_id(parent_item)
            elif view.value == "change":
                if isinstance(view.further_value, list):
                    type = view.further_value[0]
                    seconds = view.further_value[1]
                else:
                    type = view.further_value

                selected_item["Type"] = type
                try:
                    selected_item["Until"] = (
                        datetime.datetime.utcnow().timestamp() + seconds
                    )
                except:
                    pass
                parent_item["warnings"][item_index] = selected_item
                await bot.warnings.update_by_id(parent_item)
            elif view.value == "delete":
                parent_item["warnings"].remove(selected_item)
                await bot.warnings.update_by_id(parent_item)
            else:
                return await invis_embed(ctx, "You have not selected an option.")
            success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Punishment Modified",
                description=f"<:ArrowRightW:1035023450592514048>This punishment has been modified successfully.",
                color=0x71C15F,
            )
            await ctx.send(embed=success)

    @commands.hybrid_group(
        name="bolo",
        description="Manage the server's BOLO list.",
        extras={"category": "Punishments"},
    )
    async def bolo(self, ctx):
        pass

    @bolo.command(
        name="active",
        description="View the server's active BOLOs.",
        extras={"category": "Punishments"},
        aliases=["search", "lookup"],
    )
    @app_commands.autocomplete(user=user_autocomplete)
    @app_commands.describe(user="The user to search for.")
    @is_staff()
    async def active(self, ctx, user: str = None):
        bot = self.bot
        if user is None:
            bolos = []

            async for document in bot.warnings.db.find(
                {
                    "warnings": {
                        "$elemMatch": {
                            "Guild": ctx.guild.id,
                            "Type": {"$in": ["Bolo", "BOLO"]},
                        }
                    }
                }
            ):
                if "warnings" in document.keys():
                    for warning in document["warnings"].copy():
                        if isinstance(warning, dict):
                            if warning["Guild"] == ctx.guild.id and warning["Type"] in [
                                "Bolo",
                                "BOLO",
                            ]:
                                warning["TARGET"] = document["_id"]
                                bolos.append(warning)

            if len(bolos) == 0:
                await invis_embed(ctx, "There are no active BOLOs in this server.")
                return
            embeds = []

            embed = discord.Embed(
                title="<:WarningIcon:1035258528149033090> Active Ban BOLOs",
                color=0x2E3136,
            )

            embed.set_author(
                name=f"{len(bolos)} Active BOLOs",
                icon_url=ctx.author.display_avatar.url,
            )

            embed.set_footer(text="Click 'Mark as Complete' then, enter BOLO ID.")

            embeds.append(embed)

            for bolo in bolos:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://users.roblox.com/v1/usernames/users",
                        json={
                            "usernames": [bolo["TARGET"]],
                            "excludeBannedUsers": False,
                        },
                    ) as resp:
                        if resp.status == 200:
                            rbx = await resp.json()
                            if len(rbx["data"]) != 0:
                                rbx = rbx["data"][0]

                if len(embeds[-1].fields) == 4:
                    new_embed = discord.Embed(
                        title="<:WarningIcon:1035258528149033090> Active Ban BOLOs",
                        color=0x2E3136,
                    )

                    new_embed.set_author(
                        name=f"{len(bolos)} Active BOLOs",
                        icon_url=ctx.author.display_avatar.url,
                    )

                    new_embed.set_footer(
                        text="Click 'Mark as Complete' then, enter BOLO ID."
                    )
                    embeds.append(new_embed)
                    print("new embed")

                if vars().get("rbx") not in [None, [], {}]:
                    if "id" in rbx.keys() and "name" in rbx.keys():
                        print(f"Added to {embeds[-1]}")
                        embeds[-1].add_field(
                            name=f"<:SConductTitle:1053359821308567592> {rbx['name']} ({rbx['id']})",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {bolo['Reason']}\n<:ArrowRightW:1035023450592514048> **Staff:** {ctx.guild.get_member(bolo['Moderator'][1]).mention if ctx.guild.get_member(bolo['Moderator'][1]) is not None else bolo['Moderator'][1]}\n<:ArrowRightW:1035023450592514048> **Time:** {bolo['Time'] if isinstance(bolo['Time'], str) else datetime.datetime.fromtimestamp(bolo['Time']).strftime('%m/%d/%Y, %H:%M:%S')}\n<:ArrowRightW:1035023450592514048> **ID:** {bolo['id']}",
                            inline=False,
                        )
                        print("new field")

            if ctx.interaction:
                gtx = ctx.interaction
            else:
                gtx = ctx

            menu = ViewMenu(
                gtx, menu_type=ViewMenu.TypeEmbed, show_page_director=True, timeout=None
            )
            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            menu.add_pages(embeds)

            async def task():
                embed = discord.Embed(
                    title="<:WarningIcon:1035258528149033090> Active Ban BOLOs",
                    color=0x2E3136,
                    description="<:ArrowRight:1035003246445596774> Enter the ID of the BOLO you wish to mark as complete.",
                )

                view = CustomModalView(
                    ctx.author.id,
                    "Mark as Complete",
                    "Mark as Complete",
                    [
                        (
                            "bolo",
                            discord.ui.TextInput(
                                placeholder="The ID for the BOLO you are marking as complete",
                                label="BOLO ID",
                            ),
                        )
                    ],
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.bolo:
                    id = view.modal.bolo.value

                    matching_docs = []
                    async for doc in bot.warnings.db.find(
                        {
                            "warnings": {
                                "$elemMatch": {
                                    "Guild": ctx.guild.id,
                                    "Type": {"$in": ["Bolo", "BOLO"]},
                                    "id": int(id),
                                }
                            }
                        }
                    ):
                        matching_docs.append(doc)

                    if len(matching_docs) == 0:
                        return await invis_embed(
                            ctx, "No BOLOs were found with that ID."
                        )

                    if len(matching_docs) > 1:
                        return await invis_embed(
                            ctx,
                            "Multiple BOLOs were found with that ID. Please contact a developer.",
                        )

                    doc = matching_docs[0]

                    for index, warning in enumerate(doc["warnings"].copy()):
                        if isinstance(warning, dict):
                            if (
                                warning["Guild"] == ctx.guild.id
                                and warning["Type"] in ["Bolo", "BOLO"]
                                and warning["id"] == int(id)
                            ):
                                warning["Type"] = "Ban"
                                if warning.get("TARGET"):
                                    del warning["TARGET"]
                                warning["Reason"] = (
                                    f"BOLO marked as complete by {ctx.author} ({ctx.author.id}). Original BOLO Reason was {warning['Reason']}",
                                )
                                warning["Moderator"] = [ctx.author.name, ctx.author.id]
                                warning["Time"] = datetime.datetime.utcnow().strftime(
                                    "%m/%d/%Y, %H:%M:%S"
                                )

                                doc["warnings"].append(warning)
                                doc["warnings"].pop(index)

                                await bot.warnings.update_by_id(doc)

                    success_embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> The BOLO ({id}) has been marked as complete.",
                        color=0x71C15F,
                    )

                    await ctx.send(embed=success_embed)
                    return

            def taskWrapper():
                bot.loop.create_task(task())

            followUp = ViewButton.Followup(
                details=ViewButton.Followup.set_caller_details(taskWrapper)
            )

            print(embeds)

            menu.add_buttons(
                [
                    ViewButton(
                        label="Mark as Complete",
                        custom_id=ViewButton.ID_CALLER,
                        followup=followUp,
                    )
                ]
            )
            await menu.start()

        else:
            user = await bot.warnings.find_by_id(user.lower())
            bolos = []

            if user is None:
                return await invis_embed(
                    ctx,
                    "No user was found in the database. If this is a correct user, they do not have a BOLO. If you believe them to have a BOLO, ensure there are no mistakes in the username you have provided.",
                )
            for warning in user["warnings"].copy():
                if isinstance(warning, dict):
                    if warning["Guild"] == ctx.guild.id and warning["Type"] in [
                        "Bolo",
                        "BOLO",
                    ]:
                        bolos.append(warning)

            if len(bolos) == 0:
                await invis_embed(ctx, "This user does not have any active BOLOs.")
                return

            embeds = []

            embed = discord.Embed(
                title="<:WarningIcon:1035258528149033090> Active Ban BOLOs",
                color=0x2E3136,
            )

            embed.set_author(
                name=f"{len(bolos)} Active BOLOs",
                icon_url=ctx.author.display_avatar.url,
            )

            embed.set_footer(text="Click 'Mark as Complete' then, enter BOLO ID.")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://users.roblox.com/v1/usernames/users",
                    json={"usernames": [user["_id"]], "excludeBannedUsers": False},
                ) as resp:
                    if resp.status == 200:
                        rbx = await resp.json()
                        if len(rbx["data"]) != 0:
                            rbx = rbx["data"][0]

                            async with session.get(
                                f'https://thumbnails.roblox.com/v1/users/avatar?userIds={rbx["id"]}&size=420x420&format=Png'
                            ) as f:
                                if f.status == 200:
                                    avatar = await f.json()
                                    Headshot_URL = avatar["data"][0]["imageUrl"]
                                else:
                                    Headshot_URL = ""

                            embed.set_thumbnail(url=Headshot_URL)

            embeds.append(embed)

            for bolo in bolos:
                if len(embeds[-1].fields) == 4:
                    new_embed = discord.Embed(
                        title="<:WarningIcon:1035258528149033090> Active Ban BOLOs",
                        color=0x2E3136,
                    )

                    new_embed.set_author(
                        name=f"{len(bolos)} Active BOLOs",
                        icon_url=ctx.author.display_avatar.url,
                    )

                    new_embed.set_footer(
                        text="Click 'Mark as Complete' then, enter BOLO ID."
                    )
                    embeds.append(new_embed)

                print(f"Added to {embeds[-1]}")
                embeds[-1].add_field(
                    name=f"<:SConductTitle:1053359821308567592> {rbx['name']} ({rbx['id']})",
                    value=f"<:ArrowRightW:1035023450592514048> **Reason:** {bolo['Reason']}\n<:ArrowRightW:1035023450592514048> **Staff:** {ctx.guild.get_member(bolo['Moderator'][1]).mention if ctx.guild.get_member(bolo['Moderator'][1]) is not None else bolo['Moderator'][1]}\n<:ArrowRightW:1035023450592514048> **Time:** {bolo['Time'] if isinstance(bolo['Time'], str) else datetime.datetime.fromtimestamp(bolo['Time']).strftime('%m/%d/%Y, %H:%M:%S')}\n<:ArrowRightW:1035023450592514048> **ID:** {bolo['id']}",
                    inline=False,
                )

            if ctx.interaction:
                gtx = ctx.interaction
            else:
                gtx = ctx

            menu = ViewMenu(
                gtx,
                menu_type=ViewMenu.TypeEmbed,
                show_page_director=False,
                timeout=None,
            )
            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            menu.add_pages(embeds)

            async def task():
                embed = discord.Embed(
                    title="<:WarningIcon:1035258528149033090> Active Ban BOLOs",
                    color=0x2E3136,
                    description="<:ArrowRight:1035003246445596774> Enter the ID of the BOLO you wish to mark as complete.",
                )

                view = CustomModalView(
                    ctx.author.id,
                    "Mark as Complete",
                    "Mark as Complete",
                    [
                        (
                            "bolo",
                            discord.ui.TextInput(
                                placeholder="The ID for the BOLO you are marking as complete",
                                label="BOLO ID",
                            ),
                        )
                    ],
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return
                print(bolos)
                if view.modal.bolo:
                    id = view.modal.bolo.value

                    matching_docs = []
                    async for doc in bot.warnings.db.find(
                        {
                            "warnings": {
                                "$elemMatch": {
                                    "Guild": ctx.guild.id,
                                    "Type": {"$in": ["Bolo", "BOLO"]},
                                    "id": int(id),
                                }
                            }
                        }
                    ):
                        matching_docs.append(doc)

                    if len(matching_docs) == 0:
                        return await invis_embed(
                            ctx, "No BOLOs were found with that ID."
                        )

                    if len(matching_docs) > 1:
                        return await invis_embed(
                            ctx,
                            "Multiple BOLOs were found with that ID. Please contact a developer.",
                        )

                    doc = matching_docs[0]

                    for index, warning in enumerate(doc["warnings"].copy()):
                        if isinstance(warning, dict):
                            if (
                                warning["Guild"] == ctx.guild.id
                                and warning["Type"] in ["Bolo", "BOLO"]
                                and warning["id"] == int(id)
                            ):
                                warning["Type"] = "Ban"
                                warning["Reason"] = (
                                    f"BOLO marked as complete by {ctx.author} ({ctx.author.id}). Original BOLO Reason was {warning['Reason']}",
                                )
                                warning["Moderator"] = [ctx.author.name, ctx.author.id]
                                warning["Time"] = datetime.datetime.utcnow().strftime(
                                    "%m/%d/%Y, %H:%M:%S"
                                )

                                doc["warnings"].append(warning)
                                doc["warnings"].pop(index)

                                await bot.warnings.update_by_id(doc)

                    success_embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> The BOLO ({id}) has been marked as complete.",
                        color=0x71C15F,
                    )

                    await ctx.send(embed=success_embed)
                    return

            def taskWrapper():
                bot.loop.create_task(task())

            followUp = ViewButton.Followup(
                details=ViewButton.Followup.set_caller_details(taskWrapper)
            )

            menu.add_buttons(
                [
                    ViewButton(
                        label="Mark as Complete",
                        custom_id=ViewButton.ID_CALLER,
                        followup=followUp,
                    )
                ]
            )
            await menu.start()

    @commands.hybrid_command(
        name="import",
        description="Import CRP Moderation data",
        extras={"category": "Punishments"},
    )
    @app_commands.describe(export_file="Your CRP Moderation export file. (.json)")
    @is_management()
    async def _import(self, ctx, export_file: discord.Attachment):
        # return await invis_embed(ctx,  '`/import` has been temporarily disabled for performance reasons. We are currently working on a fix as soon as possible.')
        bot = self.bot
        read = await export_file.read()
        decoded = read.decode("utf-8")
        jsonData = json.loads(decoded)
        # except Exception as e:
        #     print(e)
        #     return await invis_embed(ctx,
        #                              "You have not provided a correct CRP export file. You can find this by doing `/export` with the CRP bot.")

        await invis_embed(ctx, "We are currently processing your export file.")
        await crp_data_to_mongo(jsonData, ctx.guild.id)
        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Data Merged",
            description=f"<:ArrowRightW:1035023450592514048>**{ctx.guild.name}**'s data has been merged.",
            color=0x71C15F,
        )

        await ctx.send(embed=success)

    @commands.hybrid_command(
        name="tempban",
        aliases=["tb", "tba"],
        description="Tempbans a user.",
        extras={"category": "Punishments"},
        with_app_command=True,
    )
    @is_staff()
    @app_commands.describe(user="What's their ROBLOX username?")
    @app_commands.describe(reason="How long are you banning them for? (s/m/h/d)")
    @app_commands.describe(reason="What is your reason for punishing this user?")
    async def tempban(self, ctx, user, time: str, *, reason):
        bot = self.bot
        reason = "".join(reason)

        timeObj = list(reason)[-1]
        reason = list(reason)

        if not time.lower().endswith(("h", "m", "s", "d", "w")):
            reason.insert(0, time)
            if not timeObj.lower().endswith(("h", "m", "s", "d", "w")):
                return await invis_embed(
                    ctx,
                    "A time must be provided at the **start** of your reason. Example: >tban i_iMikey 12h LTAP",
                )
            else:
                time = timeObj
                reason.pop()

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

        startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
        endTimestamp = int(startTimestamp + time)

        reason = "".join([str(item) for item in reason])
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://users.roblox.com/v1/users/search?keyword={user}&limit=10"
            ) as r:
                if r.status == 200:
                    robloxUser = await r.json()
                    if len(robloxUser["data"]) == 0:
                        return await invis_embed(
                            ctx, f"No user found with the name `{user}`"
                        )
                    robloxUser = robloxUser["data"][0]
                    Id = robloxUser["id"]
                    async with session.get(
                        f"https://users.roblox.com/v1/users/{Id}"
                    ) as r:
                        requestJson = await r.json()
                else:
                    async with session.post(
                        f"https://users.roblox.com/v1/usernames/users",
                        json={"usernames": [user]},
                    ) as r:
                        robloxUser = await r.json()
                        if "data" in robloxUser.keys():
                            Id = robloxUser["data"][0]["id"]
                            async with session.get(
                                f"https://users.roblox.com/v1/users/{Id}"
                            ) as r:
                                requestJson = await r.json()
                        else:
                            try:
                                userConverted = await (
                                    discord.ext.commands.MemberConverter()
                                ).convert(ctx, user.replace(" ", ""))
                                if userConverted:
                                    verified_user = await bot.verification.find_by_id(
                                        userConverted.id
                                    )
                                    if verified_user:
                                        Id = verified_user["roblox"]
                                        async with session.get(
                                            f"https://users.roblox.com/v1/users/{Id}"
                                        ) as r:
                                            requestJson = await r.json()
                                    else:
                                        async with aiohttp.ClientSession(
                                            headers={"api-key": bot.bloxlink_api_key}
                                        ) as newSession:
                                            async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}"
                                            ) as r:
                                                tempRBXUser = await r.json()
                                                if tempRBXUser["success"]:
                                                    tempRBXID = tempRBXUser["user"][
                                                        "robloxId"
                                                    ]
                                                else:
                                                    return await invis_embed(
                                                        ctx,
                                                        f"No user found with the name `{userConverted.display_name}`",
                                                    )
                                                Id = tempRBXID
                                                async with session.get(
                                                    f"https://users.roblox.com/v1/users/{Id}"
                                                ) as r:
                                                    requestJson = await r.json()
                            except discord.ext.commands.MemberNotFound:
                                return await invis_embed(
                                    ctx, f"No member found with the query: `{user}`"
                                )

        print(requestJson)
        try:
            data = requestJson["data"]
        except KeyError:
            data = [requestJson]

        if not "data" in locals():
            data = [requestJson]

        Embeds = []

        for dataItem in data:
            embed = discord.Embed(title=dataItem["name"], color=0x2E3136)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://thumbnails.roblox.com/v1/users/avatar?userIds={dataItem["id"]}&size=420x420&format=Png'
                ) as f:
                    if f.status == 200:
                        avatar = await f.json()
                        avatar = avatar["data"][0]["imageUrl"]
                    else:
                        avatar = ""

            user = await bot.warnings.find_by_id(dataItem["name"].lower())
            if user is None:
                embed.description = """
                       <:ArrowRightW:1035023450592514048>**Warnings:** 0
                       <:ArrowRightW:1035023450592514048>**Kicks:** 0
                       <:ArrowRightW:1035023450592514048>**Bans:** 0

                       `Banned:` <:ErrorIcon:1035000018165321808>
                       """
            else:
                warnings = 0
                kicks = 0
                bans = 0
                bolos = 0
                for warningItem in user["warnings"]:
                    if warningItem["Guild"] == ctx.guild.id:
                        if warningItem["Type"] == "Warning":
                            warnings += 1
                        elif warningItem["Type"] == "Kick":
                            kicks += 1
                        elif warningItem["Type"] == "Ban":
                            bans += 1
                        elif warningItem["Type"] == "Temporary Ban":
                            bans += 1
                        elif warningItem["Type"].upper() == "BOLO":
                            bolos += 1

                if bans != 0:
                    banned = "<:CheckIcon:1035018951043842088>"
                else:
                    banned = "<:ErrorIcon:1035000018165321808>"

                if bolos >= 1:
                    embed.description = f"""
                           <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                           <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                           <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                           <:WarningIcon:1035258528149033090> **BOLOs:**
                           <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo active` before continuing.

                           `Banned:` {banned}
                           """
                else:
                    embed.description = f"""
                           <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                           <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                           <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                           `Banned:` {banned}
                           """

            embed.set_thumbnail(url=avatar)
            embed.set_footer(
                text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.'
            )

            Embeds.append(embed)

        async def ban_function(ctx, menu):
            user = menu.message.embeds[0].title
            await menu.stop(disable_items=True)
            default_warning_item = {
                "_id": user.lower(),
                "warnings": [
                    {
                        "id": next(generator),
                        "Type": "Temporary Ban",
                        "Reason": reason,
                        "Moderator": [ctx.author.name, ctx.author.id],
                        "Time": ctx.message.created_at.strftime("%m/%d/%Y, %H:%M:%S"),
                        "Until": endTimestamp,
                        "Guild": ctx.guild.id,
                    }
                ],
            }

            singular_warning_item = {
                "id": next(generator),
                "Type": "Temporary Ban",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime("%m/%d/%Y, %H:%M:%S"),
                "Until": endTimestamp,
                "Guild": ctx.guild.id,
            }

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await invis_embed(
                    ctx,
                    "The server has not been set up yet. Please run `/setup` to set up the server.",
                )

            if not configItem["punishments"]["enabled"]:
                return await invis_embed(
                    ctx,
                    "This server has punishments disabled. Please run `/config change` to enable punishments.",
                )

            embed = discord.Embed(title=user, color=0x2E3136)
            embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
            try:
                embed.set_footer(text="Staff Logging Module")
            except:
                pass
            embed.add_field(
                name="<:staff:1035308057007230976> Staff Member",
                value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
                inline=False,
            )
            embed.add_field(
                name="<:WarningIcon:1035258528149033090> Violator",
                value=f"<:ArrowRight:1035003246445596774> {menu.message.embeds[0].title}",
                inline=False,
            )
            embed.add_field(
                name="<:MalletWhite:1035258530422341672> Type",
                value="<:ArrowRight:1035003246445596774> Temporary Ban",
                inline=False,
            )
            embed.add_field(
                name="<:Clock:1035308064305332224> Until",
                value=f"<:ArrowRight:1035003246445596774> <t:{singular_warning_item['Until']}>",
                inline=False,
            )
            embed.add_field(
                name="<:QMark:1035308059532202104> Reason",
                value=f"<:ArrowRight:1035003246445596774> {reason}",
                inline=False,
            )

            try:
                channel = discord.utils.get(
                    ctx.guild.channels, id=configItem["customisation"]["ban_channel"]
                )
            except:
                channel = None

            if not channel:
                channel = discord.utils.get(
                    ctx.guild.channels, id=configItem["punishments"]["channel"]
                )
            if not channel:
                return await invis_embed(
                    ctx,
                    "The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.",
                )

            if not await bot.warnings.find_by_id(user.lower()):
                await bot.warnings.insert(default_warning_item)
            else:
                dataset = await bot.warnings.find_by_id(user.lower())
                dataset["warnings"].append(singular_warning_item)
                await bot.warnings.update_by_id(dataset)

            shift = await bot.shifts.find_by_id(ctx.guild.id)
            if shift is not None:
                if "data" in shift.keys():
                    for item in shift["data"]:
                        if isinstance(item, dict):
                            if item["guild"] == ctx.guild.id:
                                if "moderations" in item.keys():
                                    item["moderations"].append(
                                        {
                                            "id": next(generator),
                                            "Type": "Temporary Ban",
                                            "Reason": reason,
                                            "Moderator": [
                                                ctx.author.name,
                                                ctx.author.id,
                                            ],
                                            "Time": ctx.message.created_at.strftime(
                                                "%m/%d/%Y, %H:%M:%S"
                                            ),
                                            "Until": endTimestamp,
                                            "Guild": ctx.guild.id,
                                        }
                                    )
                                else:
                                    item["moderations"] = [
                                        {
                                            "id": next(generator),
                                            "Type": "Temporary Ban",
                                            "Reason": reason,
                                            "Moderator": [
                                                ctx.author.name,
                                                ctx.author.id,
                                            ],
                                            "Time": ctx.message.created_at.strftime(
                                                "%m/%d/%Y, %H:%M:%S"
                                            ),
                                            "Until": endTimestamp,
                                            "Guild": ctx.guild.id,
                                        }
                                    ]

            success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Ban Logged",
                description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s ban has been logged.",
                color=0x71C15F,
            )

            await menu.message.edit(embed=success)
            await channel.send(embed=embed)

        if ctx.interaction:
            interaction = ctx.interaction
        else:
            interaction = ctx
        menu = ViewMenu(
            interaction,
            menu_type=ViewMenu.TypeEmbed,
            show_page_director=False,
            timeout=None,
        )

        async def task():
            await ban_function(ctx, menu)

        def taskWrapper():
            bot.loop.create_task(task())

        async def cancelTask():
            embed = discord.Embed(
                title="<:ErrorIcon:1035000018165321808> Cancelled",
                description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
                color=0xFF3C3C,
            )

            await menu.message.edit(embed=embed)

            await menu.stop(disable_items=True)

        def cancelTaskWrapper():
            bot.loop.create_task(cancelTask())

        followUp = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(taskWrapper)
        )
        cancelFollowup = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(cancelTaskWrapper)
        )

        menu.add_buttons(
            [
                ViewButton(
                    emoji="✅", custom_id=ViewButton.ID_CALLER, followup=followUp
                ),
                ViewButton(
                    emoji="❎", custom_id=ViewButton.ID_CALLER, followup=cancelFollowup
                ),
            ]
        )

        try:
            menu.add_pages(Embeds)
            await menu.start()
        except:
            return await invis_embed(
                ctx,
                "This user does not exist on the Roblox platform. Please try again with a valid username.",
            )


async def setup(bot):
    await bot.add_cog(Punishments(bot))
