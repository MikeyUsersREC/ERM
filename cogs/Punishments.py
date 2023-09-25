import datetime
import json

import aiohttp
import discord
import pytz
import reactionmenu
from decouple import config
from discord import app_commands
from discord.ext import commands
from reactionmenu import ViewButton, ViewMenu
from reactionmenu.abc import _PageController
import pytz
from datamodels.Settings import Settings
from erm import crp_data_to_mongo, generator, is_management, is_staff
from menus import (
    ChannelSelect,
    CustomisePunishmentType,
    CustomModalView,
    CustomSelectMenu,
    EditWarning,
    RemoveWarning,
    RequestDataView,
    CustomExecutionButton,
    UserSelect,
    YesNoMenu,
)
from utils.AI import AI
from utils.autocompletes import punishment_autocomplete, user_autocomplete
from utils.flags import PunishOptions, SearchOptions
from utils.utils import (
    failure_embed,
    removesuffix,
    get_roblox_by_username,
    failure_embed,
)
from utils.timestamp import td_format


class Punishments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="modstats",
        description="View all information of your staff statistics",
        extras={"category": "Punishments"},
    )
    @is_staff()
    async def modstats(self, ctx, user: discord.Member = None):
        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        settings = await bot.settings.find_by_id(ctx.guild.id)
        if settings is None:
            return await failure_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        if user == None:
            user = ctx.author

        selected = None
        all_shifts = [
            i
            async for i in bot.shift_management.shifts.db.find(
                {"Guild": ctx.guild.id, "UserID": user.id, "EndEpoch": {"$ne": 0}}
            )
        ]

        loas = []
        async for document in bot.loas.db.find(
            {"user_id": user.id, "guild_id": ctx.guild.id}
        ):
            loas.append(document)
        moderations = []

        async for document in bot.punishments.db.find(
            {"ModeratorID": user.id, "Guild": ctx.guild.id}
        ):
            moderations.append(document)

        leaves = list(filter(lambda x: x["type"].lower() == "loa", loas))
        reduced_activity = list(filter(lambda x: x["type"] == "RA", loas))
        accepted_leaves = list(filter(lambda x: x["accepted"] == True, leaves))
        denied_leaves = list(filter(lambda x: x["denied"] == True, leaves))
        accepted_ras = list(filter(lambda x: x["accepted"] == True, reduced_activity))
        denied_ras = list(filter(lambda x: x["denied"] == True, reduced_activity))

        embed = discord.Embed(
            title="<:ERMAdmin:1111100635736187011>  Moderation Statistics",
            color=0xED4348,
        )

        INVISIBLE_CHAR = "‎"

        embed.add_field(
            name="<:ERMList:1111099396990435428> Moderations",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Warnings:** {len(list(filter(lambda x: (x[0] if isinstance(x, list) else x)['Type'] == 'Warning', moderations)))}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Kicks:** {len(list(filter(lambda x: (x[0] if isinstance(x, list) else x)['Type'] == 'Kick', moderations)))}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Bans:** {len(list(filter(lambda x: (x[0] if isinstance(x, list) else x)['Type'] == 'Ban', moderations)))}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **BOLOs:** {len(list(filter(lambda x: (x[0] if isinstance(x, list) else x)['Type'] in ['BOLO', 'Bolo'], moderations)))}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Custom:** {len(list(filter(lambda x: (x[0] if isinstance(x, list) else x)['Type'] not in ['Warning', 'Kick', 'Ban', 'BOLO', 'Bolo'], moderations)))}",
            inline=True,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Activity Notices",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **LOAs:** {len(leaves)}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Accepted:** {len(accepted_leaves)}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Denied:** {len(denied_leaves)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Reduced Activity:** {len(reduced_activity)}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Accepted:** {len(accepted_ras)}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Denied:** {len(denied_ras)}",
            inline=True,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Shifts",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Shifts:** {len(all_shifts)}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Shift Time:** {td_format(datetime.timedelta(seconds=sum([(x['EndEpoch']) - (x['StartEpoch']) + (x['AddedTime']) - x['RemovedTime'] - sum(b['EndEpoch'] - b['StartEpoch'] for b in x['Breaks']) for x in all_shifts])))}\n",
            inline=True,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar)
        embed.set_author(
            name=f"{ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        await ctx.reply(embed=embed, content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** here's those modstats you requested.")

    @commands.hybrid_command(
        name="punish",
        description="Punish a user",
        extras={"category": "Punishments", "ignoreDefer": True},
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
        query, _, flags = reason.rpartition("\n")
       # ## # print(123)
        if (flags := flags.strip()).startswith("/"):
            # There are actually options here
           # ## # print(456)
            flags = await PunishOptions.convert(ctx, flags)
        else:
            # This line is actually the last line of the query and no option was given
            query += f"\n{flags}"

        reason = query

        if isinstance(flags, PunishOptions):
            if flags.without_command_execution is True:
               # ## print(1)
                if ctx.interaction:
                   # ## print(2)
                    await ctx.interaction.response.defer(ephemeral=True, thinking=True)
                else:
                    await ctx.defer()
            else:
                await ctx.defer()
        else:
            await ctx.defer()



        if reason.startswith("\n"):
            reason = reason.removeprefix('\n')

        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await failure_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        generic_warning_types = ["Warning", "Kick", "Ban", "BOLO"]

        warning_types = await bot.punishment_types.get_punishment_types(ctx.guild.id)
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

       # ## print(designated_channel)

        if len(reason) > 800:
            reason = reason[:797] + "..."

        if designated_channel is None:
            try:
                designated_channel = bot.get_channel(settings["punishments"]["channel"])
            except KeyError:
                return await failure_embed(
                    ctx,
                    "I could not find a designated channel for logging punishments. Ask a server administrator to use `/config change`.",
                )
        if type.lower() == "tempban":
            return await failure_embed(
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
            return await failure_embed(
                ctx,
                f"`{type}` is an invalid punishment type. Ask your server administrator to add this type via `/punishment manage`",
            )

        requestJson = await get_roblox_by_username(user, bot, ctx)
        if requestJson is None:
            return await failure_embed(
                ctx,
                "I could not find an associated user with the information you provided.",
            )

        stop_exception = False

        async for document in bot.consent.db.find({"_id": ctx.author.id}):
            if document.get("ai_predictions") is not None:
                if document.get("ai_predictions") is False:
                    stop_exception = True

        try:
            agent = AI(config("AI_API_URL"), config("AI_API_AUTH"))
        except:
            stop_exception = True
        auth_enabled = config("AI_API_ENABLED")
        if auth_enabled in ["FALSE", False]:
            stop_exception = True
        new_past = []
        warns = []
        past = []
       # ## print(requestJson)
        # Get all punishments of the user in the server in the last hour
        if requestJson.get("errors"):
            return await ctx.reply(
                f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** the ROBLOX API is down. Please try again later."
            )
        async for doc in bot.punishments.find_warnings_by_spec(
            ctx.guild.id, user_id=requestJson["id"]
        ):
           # ## print(doc)
            if (
                datetime.datetime.now(tz=pytz.UTC)
                - datetime.datetime.fromtimestamp(doc["Epoch"], tz=pytz.UTC)
            ).total_seconds() < 3600:
                new_past.append(doc)

       # ## print(designated_channel)
       # # print(requestJson)
        try:
            data = requestJson["data"]
        except KeyError:
            data = [requestJson]

        if not "data" in locals():
            data = [requestJson]

        Embeds = []

        for dataItem in data:
            embed = discord.Embed(
                title=f"<:ERMPunish:1111095942075138158> {dataItem['name']}",
                color=0xED4348,
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

            user = [
                i
                async for i in bot.punishments.find_warnings_by_spec(
                    guild_id=ctx.guild.id, user_id=dataItem["id"]
                )
            ]
            bolos = 0
            if user in [None, []]:
                embed.description = "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Warnings:** 0\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Kicks:** 0\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Bans:** 0\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Custom:** 0"
            else:
                warnings = 0
                kicks = 0
                bans = 0
                custom = 0

                for warningItem in user:
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

                embed.description = f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Warnings:** {warnings}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Kicks:** {kicks}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Bans:** {bans}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Custom:** {custom}"

            embed.set_thumbnail(url=Headshot_URL)
            embed.set_footer(text=f'Click "Yes" to confirm this punishment and log it.')

            Embeds.append(embed)

       # # print(new_past)
        if new_past:
            new_past = [x["Type"] for x in new_past]
            for index, x in enumerate(new_past):
                if x == "Bolo":
                    x = "BOLO"
                    new_past[index] = x

            for i in new_past:
                if x not in ["Warning", "Kick", "Ban", "Bolo"]:
                    new_past.remove(i)
           # # print(new_past)
            if not stop_exception:
                try:
                    recommended = await agent.recommended_punishment(reason, new_past)
                except:
                    stop_exception = True
        else:
            if not stop_exception:
                try:
                    recommended = await agent.recommended_punishment(reason, None)
                except:
                    stop_exception = True

        changed_type = None
        did_change_type = None
        show_recommendation = None

        if (
            type.lower() in [w.lower() for w in generic_warning_types]
            and not stop_exception
        ):
            if not recommended.modified:
                embed = discord.Embed(
                    title="<:SConductTitle:1053359821308567592> Recommended Punishment",
                    description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> Our AI has determined that the recommended punishment for `{reason}` is a `{recommended.prediction}`. Would you like to change the type of this punishment to a {recommended.prediction}?\n\n<:EditIcon:1042550862834323597> **Disclaimer**\nThis system is still in development. If you would like to report an issue, please join our [support server](https://discord.gg/FAC629TzBy). You can disable this feature by using `/consent` at any time.",
                    color=0xED4348,
                )
            else:
                embed = discord.Embed(
                    title="<:SConductTitle:1053359821308567592> Recommended Punishment",
                    description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> Our AI has determined that the recommended punishment for `{reason}` is a `{recommended.prediction}`. This is because this user has been identified as a repeat offender. Would you like to change the type of this punishment to a {recommended.prediction}?\n\n<:EditIcon:1042550862834323597> **Disclaimer**\nThis system is still in development. If you would like to report an issue, please join our [support server](https://discord.gg/FAC629TzBy). You can disable this feature by using `/consent` at any time.",
                    color=0xED4348,
                )

           # # print(type)
           # # print(recommended.prediction)
            show_recommendation = False
            if type.lower() != recommended.prediction.lower():
                if recommended.prediction.lower() in already_types:
                    show_recommendation = True

        if ctx.interaction:
            gtx = ctx.interaction
        else:
            gtx = ctx

        menu = ViewMenu(
            gtx, menu_type=ViewMenu.TypeEmbed, show_page_director=False, timeout=None
        )
       # # print(type)

        async def warn_function(ctx, menu, designated_channel=None):
           # # print(type)
            user = menu.message.embeds[0].title.split(" ")[0]
            await menu.stop(disable_items=True)

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await failure_embed(
                    ctx,
                    "this server has not been set up yet. Please run `/setup` to set up the server.",
                )

            if not configItem["punishments"]["enabled"]:
                return await failure_embed(
                    ctx,
                    "this server has punishments disabled. Please run `/config change` to enable punishments.",
                )

            embed = discord.Embed(
                title="<:ERMAdd:1113207792854106173> Punishment Logged", color=0xED4348
            )
            embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )
            try:
                embed.set_footer(text="Staff Logging Module")
            except:
                pass
            embed.add_field(
                name="<:ERMList:1111099396990435428> Staff Member",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {ctx.author.mention}",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Violator",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {menu.message.embeds[0].title.split(' ')[1]}",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {type.lower().title()}",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Reason",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {reason}",
                inline=False,
            )

            if designated_channel is None:
                designated_channel = discord.utils.get(
                    ctx.guild.channels, id=configItem["punishments"]["channel"]
                )

            oid = await bot.punishments.insert_warning(
                ctx.author.id,
                ctx.author.name,
                requestJson["id"],
                requestJson["name"],
                ctx.guild.id,
                reason,
                type.lower().title(),
                ctx.message.created_at.replace(tzinfo=pytz.UTC).timestamp(),
            )
           # # print(oid)

            shift = await bot.shift_management.get_current_shift(
                ctx.author, ctx.guild.id
            )
            if shift:
                shift["Moderations"].append(oid)
                await bot.shift_management.shifts.update_by_id(shift)

            success = (
                discord.Embed(
                    title=f"{menu.message.embeds[0].title}",
                    description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {reason}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Type:** {type.lower().title()}",
                    color=0xED4348,
                )
                .set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                .set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
            )

            roblox_id = dataItem["id"]

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
                        if doc.get("punishments"):
                            if document.get("punishments") is False:
                                should_dm = False

                    if should_dm:
                        try:
                            personal_embed = discord.Embed(
                                title="<:ERMPunish:1111095942075138158> You have been moderated!",
                                description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>***{ctx.guild.name}** has moderated you in-game*",
                                color=0xED4348,
                            )
                            personal_embed.add_field(
                                name="<:ERMList:1111099396990435428> Moderation Details",
                                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Username:** {menu.message.embeds[0].title.split(' ')[1]}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Reason:** {reason}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Type:** {type.lower().title()}",
                                inline=False,
                            )

                            try:
                                personal_embed.set_author(
                                    name=ctx.guild.name, icon_url=ctx.guild.icon.url
                                )
                            except:
                                personal_embed.set_author(name=ctx.guild.name)

                            await member.send(
                                embed=personal_embed,
                                content=f"<:ERMAlert:1113237478892130324>  **{ctx.author.name}**, you have been moderated inside of **{ctx.guild.name}**.",
                            )

                        except:
                            pass

            try:
                await designated_channel.send(embed=embed)
            except:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I was unable to log this punishment. "
                )

            if did_change_type:
                await menu.message.edit(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the moderation type to **{type}** and logged your moderation against **{menu.message.embeds[0].title.split(' ')[1]}**.",
                    embed=success,
                    view=None,
                )
            else:
                await menu.message.edit(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've logged your moderation against **{menu.message.embeds[0].title.split(' ')[1]}**.",
                    embed=success,
                    view=None,
                )

        async def changeTypeTask():
            nonlocal changed_type
            nonlocal did_change_type
            nonlocal type
            changed_type = recommended.prediction
            did_change_type = True
           # # print(recommended.prediction)
            type = recommended.prediction
            if settings:
                warning_type = None
                designated_channel = None
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

            try:
                if changed_type and did_change_type:
                    type = changed_type
            except:
                pass

            await warn_function(ctx, menu, designated_channel)

        async def task():
            await warn_function(ctx, menu, designated_channel)

        async def changeTaskWrapper():
            await changeTypeTask()

        def createChangeTaskWrapper():
            bot.loop.create_task(changeTaskWrapper())

        def taskWrapper():
            bot.loop.create_task(task())

        async def cancelTask():
            await menu.message.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** I've cancelled your log against **{menu.message.embeds[0].title.split(' ')[1]}**.",
                embed=None,
                view=None,
            )
            await menu.stop()

        def cancelTaskWrapper():
            bot.loop.create_task(cancelTask())

        followUp = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(taskWrapper)
        )
        cancelFollowup = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(cancelTaskWrapper)
        )

        changeFollowup = ViewButton.Followup(
            details=ViewButton.Followup.set_caller_details(createChangeTaskWrapper)
        )

        menu.add_buttons(
            [
                ViewButton(
                    label="Yes",
                    style=discord.ButtonStyle.green,
                    custom_id=ViewButton.ID_CALLER,
                    followup=followUp,
                ),
                ViewButton(
                    label="No",
                    style=discord.ButtonStyle.danger,
                    custom_id=ViewButton.ID_CALLER,
                    followup=cancelFollowup,
                ),
            ]
        )
        preset_text = f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** do you want to punish **{Embeds[0].title.split(' ')[1]}**?"

        if show_recommendation:
            menu.add_button(
                ViewButton(
                    label="Change Type",
                    style=discord.ButtonStyle.blurple,
                    custom_id=ViewButton.ID_CALLER,
                    followup=changeFollowup,
                    row=1,
                )
            )

        try:
            menu.add_pages(Embeds)
            menu._pc = _PageController(menu.pages)
            try:
                if bolos > 0:
                    preset_text = f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** the user **{Embeds[0].title.split(' ')[1]}** has a BOLO active. Do you want to proceed?"
                    menu._msg = await ctx.reply(
                        content=preset_text, embed=Embeds[0], view=menu._ViewMenu__view
                    )
                else:
                    if show_recommendation:
                        preset_text = f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** my AI is recommending a **{recommended.prediction}** for this punishment."
                        menu._msg = await ctx.reply(
                            content=preset_text,
                            embed=Embeds[0],
                            view=menu._ViewMenu__view,
                        )
                        return
                    menu._msg = await ctx.reply(
                        content=preset_text, embed=Embeds[0], view=menu._ViewMenu__view
                    )
            except:
                menu._msg = await ctx.reply(embed=Embeds[0], view=menu._ViewMenu__view)
        except:
            return await failure_embed(
                ctx,
                "this user does not exist on the Roblox platform. Please try again with a valid username.",
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
        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        embed = discord.Embed(
            title="<:ERMPunish:1111095942075138158> Manage Punishments", color=0xED4348
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.add_field(
            name="<:ERMList:1111099396990435428> Manage Punishment Types",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>View and modify the types of punishments.",
            inline=False,
        )
        embed.add_field(
            name="<:ERMModify:1111100050718867577> Modify a Punishment",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Modify a punishment's attributes.",
            inline=False,
        )
        embed.add_field(
            name="<:ERMTrash:1111100349244264508> Remove a Punishment",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Remove a punishment from your server.",
            inline=False,
        )
        embed.add_field(
            name="<:ERMAdmin:1111100635736187011> Administrative Actions",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Remove particular punishments from your server.",
            inline=False,
        )

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Manage Punishment Types",
                    value="manage_types",
                    description="View and modify the types of punishments.",
                ),
                discord.SelectOption(
                    label="Modify a Punishment",
                    value="modify",
                    description="Modify a punishment's attributes.",
                ),
                discord.SelectOption(
                    label="Remove a Punishment",
                    value="void",
                    description="Remove a punishment from your server.",
                ),
                discord.SelectOption(
                    label="Administrative Actions",
                    value="admin_actions",
                    description="Remove particular punishments from your server.",
                ),
            ],
        )
        msg = await ctx.reply(
            content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** select an option.",
            embed=embed,
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return
        if view.value == "manage_types":
            Data = await bot.punishment_types.find_by_id(ctx.guild.id)
            if Data is None:
                Data = {"_id": ctx.guild.id, "types": ["Warning", "Kick", "Ban"]}

            embed = discord.Embed(
                title="<:ERMPunish:1111095942075138158> Manage Punishments",
                color=0xED4348,
            )
            for item in Data["types"]:
                if isinstance(item, str):
                    embed.add_field(
                        name=f"<:ERMList:1111099396990435428> {item}",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Generic:** {'<:ERMCheck:1111089850720976906>' if item.lower() in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Custom:** {'<:ERMCheck:1111089850720976906>' if item.lower() not in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ERMClose:1111101633389146223>'}",
                        inline=False,
                    )
                elif isinstance(item, dict):
                    embed.add_field(
                        name=f"<:ERMList:1111099396990435428> {item['name'].lower().title()}",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Generic:** {'<:ERMCheck:1111089850720976906>' if item['name'].lower() in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Custom:** {'<:ERMCheck:1111089850720976906>' if item['name'].lower() not in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Channel:** {bot.get_channel(item['channel']).mention if item['channel'] is not None and bot.get_channel(item['channel']) is not None else 'None'}",
                        inline=False,
                    )

            override_content = False
            if len(embed.fields) == 0:
                override_content = True

            view = CustomisePunishmentType(ctx.author.id)

            if not override_content:
                embed.set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                msg = await ctx.reply(embed=embed, view=view)
            else:
                msg = await ctx.reply(
                    content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** there are no punishment types in **{ctx.guild.name}**.",
                    view=view,
                )
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
                    return await ctx.reply(
                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this punishment type already exists!"
                    )

                newview = ChannelSelect(ctx.author.id, limit=1)
                await msg.edit(
                    embed=None,
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what channel do you want this punishment type to send into?",
                    view=newview,
                )
                await newview.wait()

                if not newview.value:
                    return await ctx.reply(
                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** you need a channel for a punishment type!"
                    )

                data = {
                    "name": typeName.lower().title(),
                    "channel": newview.value[0].id,
                }

                Data["types"].append(data)
                await bot.punishment_types.upsert(Data)
                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** this punishment type has been successfully added!",
                    view=None,
                )
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
                        return await failure_embed(
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
                    await msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** this punishment type has been successfully removed!",
                        view=None,
                    )
        if view.value == "admin_actions":
            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Remove all punishments from a user",
                        description="Remove all punishments from a specific ROBLOX user.",
                        value="remove_user",
                    ),
                    discord.SelectOption(
                        label="Remove all punishments from a type",
                        description="Remove all punishments with a specific punishment type (warning, kick, etc)",
                        value="remove_type",
                    ),
                    discord.SelectOption(
                        label="Remove all punishments from a moderator",
                        description="Remove all punishments that a specific staff member has made.",
                        value="remove_moderator",
                    ),
                    discord.SelectOption(
                        label="Remove all punishments",
                        description="Nuke every single punishment.",
                        value="remove_all",
                    ),
                ],
            )

            msg = await msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what **administrative actions** would you like to run?",
                embed=None,
                view=view,
            )
            await view.wait()

            if view.value == "remove_user":
                view = RequestDataView(
                    ctx.author.id, "ROBLOX User ID", "ROBLOX User ID"
                )
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what ROBLOX User ID would you like to remove all punishments from?",
                    view=view,
                )
                await view.wait()
                value = view.modal.data.value

                await bot.punishments.remove_warnings_by_spec(
                    guild_id=ctx.guild.id, user_id=int(value)
                )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** all warnings from ID **{value}** have been removed!",
                    view=None,
                )
            elif view.value == "remove_type":
                view = RequestDataView(
                    ctx.author.id, "Punishment Type", "Punishment Type"
                )
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what punishment type would you like to remove all punishments from?",
                    view=view,
                )
                await view.wait()
                value = view.modal.data.value
                await bot.punishments.remove_warnings_by_spec(
                    guild_id=ctx.guild.id, warning_type=value
                )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** all warnings from **{value}** have been removed!",
                    view=None,
                )
            elif view.value == "remove_moderator":
                view = UserSelect(ctx.author.id, limit=1)
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what moderator would you like to remove all punishments from?",
                    view=view,
                )
                await view.wait()
                value = view.value[0]
                await bot.punishments.remove_warnings_by_spec(
                    guild_id=ctx.guild.id, moderator_id=value.id
                )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** I've removed **all** punishments from that staff member.",
                    view=None,
                )
            elif view.value == "remove_all":
                # Do a confirmation embed
                view = YesNoMenu(ctx.author.id)
                await msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** are you sure you'd like to remove all punishments? **This action is reversible.**",
                    embed=None,
                    view=view,
                )

                await view.wait()
                if view.value is True:
                    await bot.punishments.remove_warnings_by_spec(guild_id=ctx.guild.id)
                else:
                    return await msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** this action has been cancelled!",
                        view=None,
                    )

                return await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** all warnings have been **removed**!",
                    view=None,
                )

        if view.value == "void":
            view = RequestDataView(ctx.author.id, "Punishment", "Punishment ID")
            await msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what punishment do you want to remove?",
                view=view,
                embed=None,
            )
            timeout = await view.wait()
            if timeout:
                return

            id = view.modal.data.value

            try:
                id = int(id.replace(" ", ""))
            except:
               # # print(id)
                return await msg.edit(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist!",
                    view=None,
                )

            selected_item = await bot.punishments.get_warning_by_snowflake(snowflake=id)

            if selected_item is None:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist!",
                    view=None,
                )

            if selected_item["Guild"] != ctx.guild.id:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist in this server!",
                    view=None,
                )

            Moderator = discord.utils.get(
                ctx.guild.members, id=selected_item["ModeratorID"]
            )

            if Moderator:
                Moderator = Moderator.mention
            else:
                Moderator = selected_item["Moderator"]

            embed = discord.Embed(
                title="<:ERMPunish:1111095942075138158> Remove Punishment",
                description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Type:** {selected_item['Type']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {selected_item['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Moderator:** {Moderator}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {selected_item['Snowflake']}\n",
                color=0xED4348,
            )

            view = RemoveWarning(bot, ctx.author.id)
            await msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** are you sure you want to remove this punishment?",
                embed=embed,
                view=view,
            )
            await view.wait()
            if view.value is True:
                try:
                    await bot.punishments.remove_warning_by_snowflake(
                        identifier=selected_item["Snowflake"],
                        guild_id=ctx.guild.id,
                    )
                except ValueError as e:
                    return await msg.edit(
                        content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist in this server!",
                        view=None,
                    )

                await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** that punishment has been removed!",
                    embed=None,
                    view=None,
                )
            else:
                return await msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** this action has been cancelled!",
                    view=None,
                )

        if view.value == "modify":
            view = RequestDataView(ctx.author.id, "Punishment", "Punishment ID")
            await msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what punishment do you wish to modify?",
                view=view,
                embed=None,
            )
            timeout = await view.wait()
            if timeout:
                return

            id = view.modal.data.value
            try:
                id = int(id)
            except:
               # # print(id)
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist!",
                    view=None,
                )

            selected_item = await bot.punishments.get_warning_by_snowflake(id)

            if selected_item is None:
                return await msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist!",
                    view=None,
                )

            if selected_item["Guild"] != ctx.guild.id:
                return await failure_embed(
                    ctx,
                    "you are trying to edit a punishment that is not apart of this guild.",
                )

            Moderator = discord.utils.get(
                ctx.guild.members, id=selected_item["ModeratorID"]
            )
            if Moderator:
                Moderator = Moderator.mention
            else:
                Moderator = selected_item["Moderator"]

            embed = discord.Embed(
                title="<:ERMPunish:1111095942075138158> Modify Punishment",
                description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Type:** {selected_item['Type']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {selected_item['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Moderator:** {Moderator}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {selected_item['Snowflake']}\n",
                color=0xED4348,
            )

            punishment_types = await bot.punishment_types.get_punishment_types(
                ctx.guild.id
            )
            if punishment_types:
                punishment_types = punishment_types["types"]
            view = EditWarning(bot, ctx.author.id, punishment_types or [])
            msg = await ctx.reply(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** select an option.",
                embed=embed,
                view=view,
            )
            await view.wait()

            if view.value == "edit":
                selected_item["Reason"] = view.further_value
                await bot.punishments.update_by_id(selected_item)
            elif view.value == "change":
                if isinstance(view.further_value, list):
                    type = view.further_value[0]
                    seconds = view.further_value[1]
                else:
                    type = view.further_value

                selected_item["Type"] = type
                try:
                    selected_item["UntilEpoch"] = (
                        datetime.datetime.now(tz=pytz.UTC).timestamp() + seconds
                    )
                except:
                    pass
                await bot.punishments.update_by_id(selected_item)
            elif view.value == "delete":
                try:
                    await bot.punishments.remove_warning_by_snowflake(
                        identifier=selected_item["Snowflake"],
                        guild_id=ctx.guild.id,
                    )
                except ValueError as e:
                    return await msg.edit(
                        content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that punishment does not exist!",
                        view=None,
                    )
            else:
                return
            await msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** that punishment has been modified successfully!",
                embed=None,
                view=None,
            )

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
        extras={"category": "Punishments", "ignoreDefer": True},
        aliases=["search", "lookup"],
    )
    @app_commands.autocomplete(user=user_autocomplete)
    @app_commands.describe(user="The user to search for.")
    @is_staff()
    async def active(self, ctx, user: str = None, flags: SearchOptions = None):
        if isinstance(flags, SearchOptions) and flags is not None:
            if flags.without_command_execution is True:
               # # print(1)
                if ctx.interaction:
                   # # print(2)
                    await ctx.interaction.response.defer(ephemeral=True, thinking=True)
                else:
                    await ctx.defer()
            else:
                await ctx.defer()
        else:
            await ctx.defer()


        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        if user is None:
            bolos = await bot.punishments.get_guild_bolos(ctx.guild.id)

            if len(bolos) == 0:
                return await ctx.reply(
                    content=f"<:ERMClose:1111101633389146223> **{ctx.author.name},** there are no active BOLOs in **{ctx.guild.name}**.",
                    embed=None,
                    view=None,
                )
            embeds = []

            embed = discord.Embed(
                title="<:ERMAlert:1113237478892130324> Active Ban BOLOs",
                color=0xED4348,
            )

            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )

            embed.set_footer(text="Click 'Mark as Complete' then, enter BOLO ID.")

            embeds.append(embed)

            for bolo in bolos:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://users.roblox.com/v1/usernames/users",
                        json={
                            "usernames": [bolo["Username"]],
                            "excludeBannedUsers": False,
                        },
                    ) as resp:
                        if resp.status == 200:
                            rbx = await resp.json()
                            if len(rbx["data"]) != 0:
                                rbx = rbx["data"][0]

                if len(embeds[-1].fields) == 4:
                    new_embed = discord.Embed(
                        title="<:ERMAlert:1113237478892130324> Active BOLOs",
                        color=0xED4348,
                    )

                    new_embed.set_author(
                        name=ctx.author.name,
                        icon_url=ctx.author.display_avatar.url,
                    )

                    embeds.append(new_embed)
                   # # print("new embed")

                if vars().get("rbx") not in [None, [], {}]:
                    if "id" in rbx.keys() and "name" in rbx.keys():
                       # # print(f"Added to {embeds[-1]}")
                        embeds[-1].add_field(
                            name=f"<:ERMUser:1111098647485108315> {rbx['name']} ({rbx['id']})",
                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {bolo['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Staff:** {ctx.guild.get_member(bolo['ModeratorID']).mention if ctx.guild.get_member(bolo['ModeratorID']) is not None else '<@{}>'.format(bolo['ModeratorID'])}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(bolo['Epoch'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {bolo['Snowflake']}",
                            inline=False,
                        )
                       # # print("new field")

            if ctx.interaction:
                gtx = ctx.interaction
            else:
                gtx = ctx

            menu = ViewMenu(
                gtx, menu_type=ViewMenu.TypeEmbed, show_page_director=True, timeout=None
            )
            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            for e in embeds:
                menu.add_page(
                    embed=e,
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** there are **{len(bolos)}** active BOLOs.",
                )

            async def task():
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

                msg = await ctx.reply(
                    content=f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** what BOLO would you like to mark as complete?",
                    view=view,
                    embed=None,
                )
                timeout = await view.wait()
                if timeout:
                    return
               # # print(bolos)
                if view.modal.bolo:
                    id = view.modal.bolo.value

                    try:
                        id = int(id)
                    except:
                        return await msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that is not a valid ID."
                        )

                    matching_docs = []
                    matching_docs.append(
                        await bot.punishments.get_warning_by_snowflake(id)
                    )

                    if len(matching_docs) == 0:
                        return await msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I could not find a BOLO with that ID."
                        )
                    elif matching_docs[0] == None:
                        return await msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I could not find a BOLO with that ID."
                        )

                    doc = matching_docs[0]
                   # # print(f"{doc=}")
                   # # print(doc)

                    await bot.punishments.insert_warning(
                        ctx.author.id,
                        ctx.author.name,
                        doc["UserID"],
                        doc["Username"],
                        ctx.guild.id,
                        f"BOLO marked as complete by {ctx.author} ({ctx.author.id}). Original BOLO Reason was {doc['Reason']}",
                        "Ban",
                        datetime.datetime.now(tz=pytz.UTC).timestamp(),
                    )

                    await bot.punishments.remove_warning_by_snowflake(id)

                    await msg.edit(
                        content="<:ERMCheck:1111089850720976906> **{},** this BOLO been marked as complete.".format(
                            ctx.author.name
                        ),
                        view=None,
                        embed=None,
                    )
                    return

            def taskWrapper():
                bot.loop.create_task(task())

            followUp = ViewButton.Followup(
                details=ViewButton.Followup.set_caller_details(taskWrapper)
            )

           # # print(embeds)

            menu.add_buttons(
                [
                    ViewButton(
                        label="Mark as Complete",
                        custom_id=ViewButton.ID_CALLER,
                        followup=followUp,
                    )
                ]
            )

            menu._pc = _PageController(menu.pages)

            msg = await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** there are **{len(bolos)}** active BOLOs.",
                embed=embeds[0],
                view=menu._ViewMenu__view,
            )

        else:
            roblox_user = await get_roblox_by_username(user, bot, ctx)
            if roblox_user is None:
                return await ctx.reply(
                    content="<:ERMClose:1111101633389146223> **{},** I could not find this user.".format(
                        ctx.author.name
                    )
                )

            if roblox_user.get("errors") is not None:
                return await ctx.reply(
                    content="<:ERMClose:1111101633389146223> **{},** I could not find this user.".format(
                        ctx.author.name
                    )
                )

            user = [
                i
                async for i in bot.punishments.find_warnings_by_spec(
                    ctx.guild.id, user_id=roblox_user["id"], bolo=True
                )
            ]
            bolos = user

            if user is None:
                return await ctx.reply(
                    content="<:ERMClose:1111101633389146223> **{},** this user does not have any active BOLOs.".format(
                        ctx.author.name
                    )
                )
            if len(bolos) == 0:
                return await ctx.reply(
                    content="<:ERMClose:1111101633389146223> **{},** this user does not have any active BOLOs.".format(
                        ctx.author.name
                    )
                )

            embeds = []

            embed = discord.Embed(
                title="<:ERMAlert:1113237478892130324> Active Ban BOLOs",
                color=0xED4348,
            )

            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )

            # embed.set_footer(text="Click 'Mark as Complete' then, enter BOLO ID.")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://thumbnails.roblox.com/v1/users/avatar?userIds={roblox_user["id"]}&size=420x420&format=Png'
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
                        title="<:ERMAlert:1113237478892130324> Active Ban BOLOs",
                        color=0xED4348,
                    )

                    new_embed.set_author(
                        name=ctx.author.name,
                        icon_url=ctx.author.display_avatar.url,
                    )

                    embeds.append(new_embed)

                # print(f"Added to {embeds[-1]}")

                embeds[-1].add_field(
                    name=f"<:ERMUser:1111098647485108315> {roblox_user['name']} ({roblox_user['id']})",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {bolo['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Staff:** {ctx.guild.get_member(bolo['ModeratorID']).mention if ctx.guild.get_member(bolo['ModeratorID']) is not None else '<@{}>'.format(bolo['ModeratorID'])}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(bolo['Epoch'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {bolo['Snowflake']}",
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
            for e in embeds:
                menu.add_page(
                    embed=e,
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** there are **{len(bolos)}** active BOLOs on **{roblox_user['name']}**.",
                )

            async def task():
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

                await ctx.reply(
                    content=f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** what BOLO would you like to mark as complete?",
                    view=view,
                )
                timeout = await view.wait()
                if timeout:
                    return
                # print(bolos)
                if view.modal.bolo:
                    id = view.modal.bolo.value

                    matching_docs = []
                    matching_docs.append(
                        await bot.punishments.get_warning_by_snowflake(id)
                    )

                    if len(matching_docs) == 0:
                        return await ctx.reply(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I could not find a BOLO with that ID."
                        )

                    doc = matching_docs[0]

                    await bot.punishments.insert_warning(
                        ctx.author.id,
                        ctx.author.name,
                        doc["UserID"],
                        doc["Username"],
                        ctx.guild.id,
                        f"BOLO marked as complete by {ctx.author} ({ctx.author.id}). Original BOLO Reason was {doc['Reason']}",
                        "Ban",
                        datetime.datetime.now(tz=pytz.UTC).timestamp(),
                    )

                    await bot.punishments.remove_warning_by_snowflake(id)

                    await msg.edit(
                        content="<:ERMCheck:1111089850720976906> **{},** this BOLO been marked as complete.".format(
                            ctx.author.name
                        ),
                        view=None,
                        embed=None,
                    )
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

            menu._pc = _PageController(menu.pages)

            await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** there are **{len(bolos)}** active BOLOs on **{roblox_user['name']}**.",
                embed=embeds[0],
                view=menu._ViewMenu__view,
            )

    #
    # @commands.hybrid_command(
    #     name="import",
    #     description="Import CRP Moderation data",
    #     extras={"category": "Punishments"},
    # )
    # @app_commands.describe(export_file="Your CRP Moderation export file. (.json)")
    # @is_management()
    # async def _import(self, ctx, export_file: discord.Attachment):
    #     if self.bot.punishments_disabled is True:
    #         return await failure_embed(ctx,
    #                                    "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.")
    #
    #     # return await failure_embed(ctx,  '`/import` has been temporarily disabled for performance reasons. We are currently working on a fix as soon as possible.')
    #     bot = self.bot
    #     read = await export_file.read()
    #     decoded = read.decode("utf-8")
    #     jsonData = json.loads(decoded)
    #     # except Exception as e:
    #     #     # print(e)
    #     #     return await failure_embed(ctx,
    #     #                              "You have not provided a correct CRP export file. You can find this by doing `/export` with the CRP bot.")
    #
    #     await failure_embed(ctx, "We are currently processing your export file.")
    #     await crp_data_to_mongo(jsonData, ctx.guild.id)
    #     success = discord.Embed(
    #         title="<:CheckIcon:1035018951043842088> Data Merged",
    #         description=f"<:ArrowRightW:1035023450592514048>**{ctx.guild.name}**'s data has been merged.",
    #         color=0x71C15F,
    #     )
    #
    #     await ctx.reply(embed=success)

    @commands.hybrid_command(
        name="tempban",
        aliases=["tb", "tba"],
        description="Tempbans a user.",
        extras={"category": "Punishments"},
        with_app_command=True,
    )
    @is_staff()
    @app_commands.describe(user="What's their ROBLOX username?")
    @app_commands.describe(time="How long are you banning them for? (s/m/h/d)")
    @app_commands.describe(reason="What is your reason for punishing this user?")
    async def tempban(self, ctx, user, time: str, *, reason):
        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        reason = "".join(reason)

        timeObj = list(reason)[-1]
        reason = list(reason)

        if not time.lower().endswith(("h", "m", "s", "d", "w")):
            reason.insert(0, time)
            if not timeObj.lower().endswith(("h", "m", "s", "d", "w")):
                return await failure_embed(
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
        requestJson = await get_roblox_by_username(user, bot, ctx)

        # print(requestJson)
        try:
            data = requestJson["data"]
        except KeyError:
            data = [requestJson]

        if not "data" in locals():
            data = [requestJson]

        Embeds = []

        if requestJson.get("errors"):
            return await ctx.reply(
                f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** the ROBLOX API is down. Please try again later."
            )
        for dataItem in data:
            embed = discord.Embed(title=dataItem["name"], color=0xED4348)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://thumbnails.roblox.com/v1/users/avatar?userIds={dataItem["id"]}&size=420x420&format=Png'
                ) as f:
                    if f.status == 200:
                        avatar = await f.json()
                        avatar = avatar["data"][0]["imageUrl"]
                    else:
                        avatar = ""

            user = [
                i
                async for i in bot.punishments.find_warnings_by_spec(
                    ctx.guild.id, user_id=dataItem["id"]
                )
            ]
            if user in [[], None]:
                embed.description = """\n<:ArrowRightW:1035023450592514048>**Warnings:** 0\n<:ArrowRightW:1035023450592514048>**Kicks:** 0\n<:ArrowRightW:1035023450592514048>**Bans:** 0\n`Banned:` <:ErrorIcon:1035000018165321808>"""
            else:
                warnings = 0
                kicks = 0
                bans = 0
                bolos = 0
                for warningItem in user:
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

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await failure_embed(
                    ctx,
                    "The server has not been set up yet. Please run `/setup` to set up the server.",
                )

            if not configItem["punishments"]["enabled"]:
                return await failure_embed(
                    ctx,
                    "This server has punishments disabled. Please run `/config change` to enable punishments.",
                )

            embed = discord.Embed(title=user, color=0xED4348)
            embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
            try:
                embed.set_footer(text="Staff Logging Module")
            except:
                pass
            embed.add_field(
                name="<:ERMList:1111099396990435428> Staff Member",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {ctx.author.mention}",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Violator",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {menu.message.embeds[0].title}",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912> Temporary Ban",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Until",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> <t:{int(endTimestamp)}>",
                inline=False,
            )
            embed.add_field(
                name="<:ERMList:1111099396990435428> Reason",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {reason}",
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
                return await failure_embed(
                    ctx,
                    "the channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.",
                )

            oid = await bot.punishments.insert_warning(
                ctx.author.id,
                ctx.author.name,
                dataItem["id"],
                dataItem["name"],
                ctx.guild.id,
                reason,
                "Temporary Ban",
                datetime.datetime.now(tz=pytz.UTC).timestamp(),
                until_epoch=endTimestamp,
            )

            shift = await bot.shift_management.get_current_shift(
                ctx.author, ctx.guild.id
            )
            if shift:
                shift["Moderations"].append(oid)
                await bot.shift_management.shifts.update_by_id(shift)

            if channel is None:
                return await menu.message.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you have not set a logging channel.",
                    view=None,
                    embed=None,
                )

            await channel.send(embed=embed)
            await menu.message.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've logged **{menu.message.embeds[0].title}**'s temp-ban."
            )

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
            await menu.message.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've cancelled that log."
            )

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
                    label="Yes",
                    style=discord.ButtonStyle.green,
                    custom_id=ViewButton.ID_CALLER,
                    followup=followUp,
                ),
                ViewButton(
                    label="No",
                    style=discord.ButtonStyle.danger,
                    custom_id=ViewButton.ID_CALLER,
                    followup=cancelFollowup,
                ),
            ]
        )

        try:
            menu.add_pages(Embeds)
            await menu.start()
        except:
            return await failure_embed(
                ctx,
                "this user does not exist on the ROBLOX platform. Please try again with a valid username.",
            )


async def setup(bot):
    await bot.add_cog(Punishments(bot))
