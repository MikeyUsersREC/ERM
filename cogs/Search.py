import datetime
import logging

import aiohttp
import discord
import pytz
from discord import app_commands
from discord.ext import commands
from reactionmenu import ViewButton, ViewMenu
from roblox import client as roblox

from erm import check_privacy, is_staff, staff_field
from utils.autocompletes import user_autocomplete
from utils.utils import invis_embed, failure_embed

client = roblox.Client()


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="search",
        aliases=["s"],
        description="Searches for a user in the warning database.",
        extras={"category": "Search"},
        usage="<user>",
        with_app_command=True,
    )
    @is_staff()
    @app_commands.autocomplete(query=user_autocomplete)
    @app_commands.describe(
        query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username."
    )
    async def search(self, ctx, *, query):
        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        alerts = {
            "NoAlerts": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>No alerts found for this account!",
            "AccountAge": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>The account age of the user is less than 100 days.",
            "NoDescription": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This account has no description.",
            "SuspiciousUsername": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This account could be an alt account.",
            "MassPunishments": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user exceeds the regular amount of warnings that a user should have.",
            "UserDoesNotExist": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user does not exist.",
            "IsBanned": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user is banned from Roblox.",
            "NotManyFriends": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user has less than 30 friends.",
            "NotManyGroups": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user has less than 5 groups.",
            "HasBOLO": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user has a BOLO active.",
        }

        user = query
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://users.roblox.com/v1/users/search?keyword={user}&limit=10"
            ) as r:
                if r.status == 200:
                    robloxUser = await r.json()
                    if len(robloxUser["data"]) == 0:
                        return await ctx.reply(
                            f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{user}**.",
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
                        if "data" in robloxUser.keys() and len(robloxUser["data"]) == 1:
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
                                                    return await ctx.reply(
                                                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{userConverted.display_name}**.",
                                                    )
                                                Id = tempRBXID
                                                async with session.get(
                                                    f"https://users.roblox.com/v1/users/{Id}"
                                                ) as r:
                                                    requestJson = await r.json()
                            except discord.ext.commands.MemberNotFound:
                                return await ctx.reply(
                                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{user}**."
                                )

        RESULTS = []
        if requestJson.get("errors"):
            return await ctx.reply(
                f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** the ROBLOX API is down. Please try again later."
            )
        query = requestJson["name"]

        warnings = await bot.punishments.get_warnings(requestJson["id"], ctx.guild.id)
        if warnings:
            RESULTS.append(warnings)

        if len(RESULTS) == 0:
            try:
                User = await client.get_user_by_username(query)
            except:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{query}**."
                )

            triggered_alerts = []

            try:
                if User.is_banned:
                    triggered_alerts.append("IsBanned")
                if (datetime.datetime.now(tz=pytz.UTC) - User.created).days < 100:
                    triggered_alerts.append("AccountAge")
                if not User:
                    triggered_alerts.append("UserDoesNotExist")
                if len(User.description) < 10:
                    triggered_alerts.append("NoDescription")
                if any(x in User.name for x in ["alt", "alternative", "account"]):
                    triggered_alerts.append("SuspiciousUsername")
                if await User.get_friend_count() <= 30:
                    triggered_alerts.append("NotManyFriends")
                if len(await User.get_group_roles()) <= 5:
                    triggered_alerts.append("NotManyGroups")
                if len(triggered_alerts) == 0:
                    triggered_alerts.append("NoAlerts")
            except:
                pass

            embed1 = discord.Embed(
                title=f"<:ERMUser:1111098647485108315> {query} ({User.id})",
                color=0xED4348,
            )
            embed1.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )
            try:
                if await bot.flags.find_by_id(
                    embed1.title.split("<:ERMUser:1111098647485108315> ")[1]
                    .split(" ")[0]
                    .lower()
                ):
                    await staff_field(
                        bot,
                        embed1,
                        embed1.title.split("<:ERMUser:1111098647485108315> ")[1]
                        .split(" ")[0]
                        .lower(),
                    )
            except:
                pass
            embed1.add_field(
                name="<:ERMPunish:1111095942075138158> Punishments",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> 0",
                inline=False,
            )
            string = "\n".join([alerts[i] for i in triggered_alerts])

            embed1.add_field(
                name="<:ERMAlert:1113237478892130324> Alerts",
                value=f"{string}",
                inline=False,
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar?userIds={User.id}&size=420x420&format=Png"
                ) as f:
                    if f.status == 200:
                        avatar = await f.json()
                        avatar = avatar["data"][0]["imageUrl"]
                        embed1.set_thumbnail(url=avatar)
                    else:
                        avatar = ""

            await ctx.reply(embed=embed1)

        if len(RESULTS) > 1:
            return await ctx.reply(
                f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** more than one user matches your query. This is a fatal error. Contact our support team at <https://discord.gg/erm-systems-987798554972143728>",
            )

        if len(RESULTS) == 1:
            message = ctx.message

            result_var = None
            logging.info(message.content.lower())
            result = RESULTS[0]

            triggered_alerts = []

            User = await client.get_user_by_username(
                result[0]["Username"], expand=True, exclude_banned_users=False
            )

            embed1 = discord.Embed(
                title=f"<:ERMUser:1111098647485108315> {User.name} ({User.id})",
                color=0xED4348,
            )
            embed2 = discord.Embed(
                title=f"<:ERMUser:1111098647485108315> {User.name} ({User.id})",
                color=0xED4348,
            )
            embed_list = []
            if len(embed_list) > 0:
                embed1 = embed_list[0]

            listOfPerGuild = warnings

            try:
                if User.is_banned:
                    triggered_alerts.append("IsBanned")
                if (datetime.datetime.now(tz=pytz.UTC) - User.created).days < 100:
                    triggered_alerts.append("AccountAge")
                if not User:
                    triggered_alerts.append("UserDoesNotExist")
                if len(User.description) < 10:
                    triggered_alerts.append("NoDescription")
                if any(x in User.name for x in ["alt", "alternative", "account"]):
                    triggered_alerts.append("SuspiciousUsername")
                if len(listOfPerGuild) > 5:
                    triggered_alerts.append("MassPunishments")
                if await User.get_friend_count() <= 30:
                    triggered_alerts.append("NotManyFriends")
                if len(await User.get_group_roles()) <= 5:
                    triggered_alerts.append("NotManyGroups")
            except:
                pass

            for warning in listOfPerGuild:
                if warning["Type"].upper() == "BOLO":
                    triggered_alerts.append("HasBOLO")
                    break

            if len(triggered_alerts) == 0:
                triggered_alerts.append("NoAlerts")

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await ctx.reply(
                    f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
                )

            if not configItem["punishments"]["enabled"]:
                return await ctx.reply(
                    f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** this server has the punishment module disabled.",
                )
            embeds = [embed1, embed2]

            try:
                if await bot.flags.find_by_id(
                    embed1.title.split("<:ERMUser:1111098647485108315> ")[1]
                    .split(" ")[0]
                    .lower()
                ):
                    await staff_field(
                        bot,
                        embed1,
                        embed1.title.split("<:ERMUser:1111098647485108315> ")[1]
                        .split(" ")[0]
                        .lower(),
                    )
            except:
                pass

            embeds[0].add_field(
                name="<:ERMPunish:1111095942075138158> Punishments",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {len(listOfPerGuild)}",
                inline=False,
            )
            string = "\n".join([alerts[i] for i in triggered_alerts])
            embeds[0].add_field(
                name="<:ERMAlert:1113237478892130324> Alerts",
                value=f" {string}",
                inline=False,
            )
            print(result)

            for action in result:
                if action["Guild"] == ctx.guild.id:
                    if action.get("UntilEpoch"):
                        if len(embeds[-1].fields) <= 2:
                            embeds[-1].add_field(
                                name=f"<:ERMList:1111099396990435428> {action['Type']}",
                                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Moderator:** <@{action['ModeratorID']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(action['Epoch'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Until:** <t:{action['UntilEpoch']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['Snowflake']}",
                                inline=False,
                            )
                        else:
                            new_embed = discord.Embed(
                                title=embeds[0].title, color=0xED4348
                            )

                            embeds.append(new_embed)
                            embeds[-1].add_field(
                                name=f"<:ERMList:1111099396990435428> {action['Type']}",
                                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Moderator:** <@{action['ModeratorID']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(action['Epoch'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Until:** <t:{action['UntilEpoch']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['Snowflake']}",
                                inline=False,
                            )
                    else:
                        if len(embeds[-1].fields) <= 2:
                            embeds[-1].add_field(
                                name=f"<:ERMList:1111099396990435428> {action['Type']}",
                                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Moderator:** <@{action['ModeratorID']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(action['Epoch'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['Snowflake']}",
                                inline=False,
                            )
                        else:
                            new_embed = discord.Embed(
                                title=embeds[0].title, color=0xED4348
                            )

                            embeds.append(new_embed)
                            embeds[-1].add_field(
                                name=f"<:ERMList:1111099396990435428> {action['Type']}",
                                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Moderator:** <@{action['ModeratorID']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(action['Epoch'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['Snowflake']}",
                                inline=False,
                            )

            for index, embed in enumerate(embeds):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://thumbnails.roblox.com/v1/users/avatar?userIds={User.id}&size=420x420&format=Png"
                    ) as f:
                        if f.status == 200:
                            avatar = await f.json()
                            avatar = avatar["data"][0]["imageUrl"]
                            embed.set_thumbnail(url=avatar)
                        else:
                            avatar = ""
                embed.set_author(
                    name=f"{ctx.author.name}",
                    icon_url=ctx.author.display_avatar.url,
                )
                if index != 0:
                    embed.set_footer(
                        text=f"Navigate this page by using the buttons below."
                    )

            if ctx.interaction:
                interaction = ctx.interaction
            else:
                interaction = ctx
            menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, timeout=None)
            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            new_embeds = []
            for embed in embeds:
                new_embeds.append(embed)
            menu.add_pages(new_embeds)
            await menu.start()

    @commands.hybrid_command(
        name="userid",
        aliases=["u"],
        description="Returns the User Id of a searched user.",
        extras={"category": "Search"},
        usage="<user>",
        with_app_command=True,
    )
    @is_staff()
    @app_commands.autocomplete(query=user_autocomplete)
    @app_commands.describe(
        query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username."
    )
    async def userid(self, ctx, *, query):
        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "this command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        user = query
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://users.roblox.com/v1/users/search?keyword={user}&limit=10"
            ) as r:
                if r.status == 200:
                    robloxUser = await r.json()
                    if len(robloxUser["data"]) == 0:
                        return await ctx.reply(
                            f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{user}**."
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
                        if (
                            "success" not in robloxUser.keys()
                            and len(robloxUser["data"]) != 0
                        ):
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
                                                    return await ctx.reply(
                                                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{userConverted.display_name}**."
                                                    )
                                                Id = tempRBXID
                                                async with session.get(
                                                    f"https://users.roblox.com/v1/users/{Id}"
                                                ) as r:
                                                    requestJson = await r.json()
                            except discord.ext.commands.MemberNotFound:
                                return await ctx.reply(
                                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{user}**."
                                )
        if requestJson.get("errors"):
            return await ctx.reply(
                f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** the ROBLOX API is down. Please try again later."
            )
        query = requestJson["name"]
        user_id = requestJson["id"]

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png"
            ) as f:
                if f.status == 200:
                    thumbnail = await f.json()
                    thumbnail = thumbnail["data"][0]["imageUrl"]
                else:
                    thumbnail = ""

        embed = discord.Embed(title=query, color=0xED4348)
        embed.add_field(
            name=f"<:ERMList:1111099396990435428> Username",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{query}",
            inline=False,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> User ID",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>`{user_id}`",
            inline=False,
        )
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text="Search Module")
        await ctx.reply(
            embed=embed,
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, alright. Here's some information about **{query}**.",
        )

    #
    # @commands.hybrid_command(
    #     name="globalsearch",
    #     aliases=["gs"],
    #     description="Searches for a user in the warning database. This will show warnings from all servers.",
    #     extras={"category": "Search"},
    #     usage="<user>",
    #     with_app_command=True,
    # )
    # @is_staff()
    # @app_commands.autocomplete(query=user_autocomplete)
    # @app_commands.describe(
    #     query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username."
    # )
    # async def globalsearch(self, ctx, *, query):
    #     bot = self.bot
    #     alerts = {
    #         "NoAlerts": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>No alerts found for this account!",
    #         "AccountAge": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>The account age of the user is less than 100 days.",
    #         "NoDescription": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This account has no description.",
    #         "SuspiciousUsername": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This account could be an alt account.",
    #         "MassPunishments": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user exceeds the regular amount of warnings that a user should have.",
    #         "UserDoesNotExist": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user does not exist.",
    #         "IsBanned": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user is banned from Roblox.",
    #         "NotManyFriends": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user has less than 30 friends.",
    #         "NotManyGroups": "<:Space:1100877460289101954><:ERMArrow:1111091707841359912>This user has less than 5 groups.",
    #     }
    #     user = query
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(
    #             f"https://users.roblox.com/v1/users/search?keyword={user}&limit=10"
    #         ) as r:
    #             if r.status == 200:
    #                 robloxUser = await r.json()
    #                 if len(robloxUser["data"]) == 0:
    #                     return await ctx.reply(
    #                         f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{user}**."
    #                     )
    #                 robloxUser = robloxUser["data"][0]
    #                 Id = robloxUser["id"]
    #                 async with session.get(
    #                     f"https://users.roblox.com/v1/users/{Id}"
    #                 ) as r:
    #                     requestJson = await r.json()
    #             else:
    #                 async with session.post(
    #                     f"https://users.roblox.com/v1/usernames/users",
    #                     json={"usernames": [user]},
    #                 ) as r:
    #                     robloxUser = await r.json()
    #                     if "data" in robloxUser.keys() and len(robloxUser["data"]) == 1:
    #                         Id = robloxUser["data"][0]["id"]
    #                         async with session.get(
    #                             f"https://users.roblox.com/v1/users/{Id}"
    #                         ) as r:
    #                             requestJson = await r.json()
    #                     else:
    #                         try:
    #                             userConverted = await (
    #                                 discord.ext.commands.MemberConverter()
    #                             ).convert(ctx, user.replace(" ", ""))
    #                             if userConverted:
    #                                 verified_user = await bot.verification.find_by_id(
    #                                     userConverted.id
    #                                 )
    #                                 if verified_user:
    #                                     Id = verified_user["roblox"]
    #                                     async with session.get(
    #                                         f"https://users.roblox.com/v1/users/{Id}"
    #                                     ) as r:
    #                                         requestJson = await r.json()
    #                                 else:
    #                                     async with aiohttp.ClientSession(
    #                                         headers={"api-key": bot.bloxlink_api_key}
    #                                     ) as newSession:
    #                                         async with newSession.get(
    #                                             f"https://v3.blox.link/developer/discord/{userConverted.id}"
    #                                         ) as r:
    #                                             tempRBXUser = await r.json()
    #                                             if tempRBXUser["success"]:
    #                                                 tempRBXID = tempRBXUser["user"][
    #                                                     "robloxId"
    #                                                 ]
    #                                             else:
    #                                                 return await ctx.reply(
    #                                                     f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{userConverted.display_name}**."
    #                                                 )
    #                                             Id = tempRBXID
    #                                             async with session.get(
    #                                                 f"https://users.roblox.com/v1/users/{Id}"
    #                                             ) as r:
    #                                                 requestJson = await r.json()
    #                         except discord.ext.commands.MemberNotFound:
    #                             return await ctx.reply(
    #                                 f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{user}**."
    #                             )
    #
    #     RESULTS = []
    #     if requestJson.get("errors"):
    #         return await ctx.reply(
    #             f"<:ERMAlert:1113237478892130324>  **{ctx.author.name},** the ROBLOX API is down. Please try again later."
    #         )
    #     query = requestJson["name"]
    #
    #     dataset = await bot.warnings.find_by_id(query.lower())
    #     if dataset:
    #         logging.info(dataset)
    #         try:
    #             logging.info(dataset["warnings"][0])
    #             dataset["warnings"][0]["name"] = query.lower()
    #             RESULTS.append(dataset["warnings"])
    #         except:
    #             pass
    #
    #     if len(RESULTS) == 0:
    #         try:
    #             User = await client.get_user_by_username(query)
    #         except:
    #             return await ctx.reply(
    #                 f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{query}**."
    #             )
    #         triggered_alerts = []
    #
    #         if User.is_banned:
    #             triggered_alerts.append("IsBanned")
    #         if (
    #             pytz.utc.localize(datetime.datetime.now(tz=pytz.UTC)) - User.created
    #         ).days < 100:
    #             triggered_alerts.append("AccountAge")
    #         if not User:
    #             triggered_alerts.append("UserDoesNotExist")
    #         if len(User.description) < 10:
    #             triggered_alerts.append("NoDescription")
    #         if any(x in User.name for x in ["alt", "alternative", "account"]):
    #             triggered_alerts.append("SuspiciousUsername")
    #         if await User.get_friend_count() <= 30:
    #             triggered_alerts.append("NotManyFriends")
    #         if len(await User.get_group_roles()) <= 5:
    #             triggered_alerts.append("NotManyGroups")
    #
    #         if len(triggered_alerts) == 0:
    #             triggered_alerts.append("NoAlerts")
    #
    #         embed1 = discord.Embed(title=f"{User.name} ({User.id})", color=0xED4348)
    #         embed1.set_author(
    #             name=f"{ctx.author.name}",
    #             icon_url=ctx.author.display_avatar.url,
    #         )
    #
    #         if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
    #             await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])
    #
    #         embed1.add_field(
    #             name="<:ERMPunish:1111095942075138158> Punishments",
    #             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>0",
    #             inline=False,
    #         )
    #         string = "\n".join([alerts[i] for i in triggered_alerts])
    #         embed1.add_field(
    #             name="<:ERMAlert:1113237478892130324> Alerts",
    #             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{string}",
    #             inline=False,
    #         )
    #
    #         async with aiohttp.ClientSession() as session:
    #             async with session.get(
    #                 f"https://thumbnails.roblox.com/v1/users/avatar?userIds={User.id}&size=420x420&format=Png"
    #             ) as f:
    #                 if f.status == 200:
    #                     avatar = await f.json()
    #                     avatar = avatar["data"][0]["imageUrl"]
    #                 else:
    #                     avatar = ""
    #         embed1.set_thumbnail(url=avatar)
    #
    #         await ctx.reply(embed=embed1)
    #     if len(RESULTS) == 1:
    #         result_var = None
    #
    #         for result in RESULTS:
    #             if result[0]["name"] == RESULTS[0][0]["name"]:
    #                 result_var = RESULTS[0]
    #
    #         result = result_var
    #         triggered_alerts = []
    #
    #         for warning in result:
    #             if not warning["Guild"] == ctx.guild.id:
    #                 privacySettings = await check_privacy(
    #                     bot, warning["Guild"], "global_warnings"
    #                 )
    #                 if not privacySettings:
    #                     result.remove(warning)
    #
    #         try:
    #             User = await client.get_user_by_username(
    #                 result[0]["name"], expand=True, exclude_banned_users=False
    #             )
    #             embed1 = discord.Embed(title=f"{User.name} ({User.id})", color=0xED4348)
    #             embed2 = discord.Embed(title=f"{User.name} ({User.id})", color=0xED4348)
    #         except (IndexError, KeyError):
    #             try:
    #                 User = await client.get_user_by_username(
    #                     query, exclude_banned_users=False, expand=True
    #                 )
    #                 embed1 = discord.Embed(
    #                     title=f"{User.name} ({User.id})", color=0xED4348
    #                 )
    #                 embed2 = discord.Embed(
    #                     title=f"{User.name} ({User.id})", color=0xED4348
    #                 )
    #             except:
    #                 return await ctx.reply(
    #                     f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't find **{query}**."
    #                 )
    #             triggered_alerts = []
    #
    #             if User.is_banned:
    #                 triggered_alerts.append("IsBanned")
    #             if (
    #                 pytz.utc.localize(datetime.datetime.now(tz=pytz.UTC)) - User.created
    #             ).days < 100:
    #                 triggered_alerts.append("AccountAge")
    #             if not User:
    #                 triggered_alerts.append("UserDoesNotExist")
    #             if len(User.description) < 10:
    #                 triggered_alerts.append("NoDescription")
    #             if any(x in User.name for x in ["alt", "alternative", "account"]):
    #                 triggered_alerts.append("SuspiciousUsername")
    #             if await User.get_friend_count() <= 30:
    #                 triggered_alerts.append("NotManyFriends")
    #             if len(await User.get_group_roles()) <= 5:
    #                 triggered_alerts.append("NotManyGroups")
    #
    #             if len(triggered_alerts) == 0:
    #                 triggered_alerts.append("NoAlerts")
    #             embed1 = discord.Embed(title=query, color=0xED4348)
    #
    #             embed1.set_author(
    #                 name=f"{ctx.author.name}",
    #                 icon_url=ctx.author.display_avatar.url,
    #             )
    #
    #             if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
    #                 await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])
    #
    #             embed1.add_field(
    #                 name="<:ERMPunish:1111095942075138158> Punishments",
    #                 value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>0",
    #                 inline=False,
    #             )
    #             string = "\n".join([alerts[i] for i in triggered_alerts])
    #             async with aiohttp.ClientSession() as session:
    #                 async with session.get(
    #                     f"https://thumbnails.roblox.com/v1/users/avatar?userIds={User.id}&size=420x420&format=Png"
    #                 ) as f:
    #                     if f.status == 200:
    #                         avatar = await f.json()
    #                         avatar = avatar["data"][0]["imageUrl"]
    #                     else:
    #                         avatar = ""
    #             embed1.add_field(
    #                 name="<:ERMAlert:1113237478892130324> Alerts",
    #                 value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{string}",
    #                 inline=False,
    #             )
    #
    #             embed1.set_thumbnail(url=avatar)
    #             return await ctx.reply(embed=embed1)
    #
    #         if User.is_banned:
    #             triggered_alerts.append("IsBanned")
    #         if (
    #             pytz.utc.localize(datetime.datetime.now(tz=pytz.UTC)) - User.created
    #         ).days < 100:
    #             triggered_alerts.append("AccountAge")
    #         if not User:
    #             triggered_alerts.append("UserDoesNotExist")
    #         if len(User.description) < 10:
    #             triggered_alerts.append("NoDescription")
    #         if any(x in User.name for x in ["alt", "alternative", "account"]):
    #             triggered_alerts.append("SuspiciousUsername")
    #         if len(result) > 5:
    #             triggered_alerts.append("MassPunishments")
    #         if await User.get_friend_count() <= 30:
    #             triggered_alerts.append("NotManyFriends")
    #         if len(await User.get_group_roles()) <= 5:
    #             triggered_alerts.append("NotManyGroups")
    #
    #         if len(triggered_alerts) == 0:
    #             triggered_alerts.append("NoAlerts")
    #
    #         configItem = await bot.settings.find_by_id(ctx.guild.id)
    #         if configItem is None:
    #             return await ctx.reply(
    #                 f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
    #             )
    #
    #         embeds = [embed1, embed2]
    #
    #         if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
    #             await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])
    #
    #         embeds[0].add_field(
    #             name="<:ERMPunish:1111095942075138158> Punishments",
    #             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{len(result)}",
    #             inline=False,
    #         )
    #         string = "\n".join([alerts[i] for i in triggered_alerts])
    #         embeds[0].add_field(
    #             name="<:ERMAlert:1113237478892130324> Alerts",
    #             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{string}",
    #             inline=False,
    #         )
    #
    #         del result[0]["name"]
    #
    #         for index, action in enumerate(result):
    #             if "Until" in action.keys():
    #                 if "Until" in action.keys():
    #                     if len(embeds[-1].fields) <= 2:
    #                         embeds[-1].add_field(
    #                             name=f"<:ERMList:1111099396990435428> {action['Type']}",
    #                             value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
    #                             inline=False,
    #                         )
    #                     else:
    #                         new_embed = discord.Embed(
    #                             title=embeds[0].title, color=0xED4348
    #                         )
    #
    #                         embeds.append(new_embed)
    #                         embeds[-1].add_field(
    #                             name=f"<:ERMList:1111099396990435428> {action['Type']}",
    #                             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Until:** <t:{action['Until']}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['id']}",
    #                             inline=False,
    #                         )
    #                 else:
    #                     if len(embeds[-1].fields) <= 2:
    #                         embeds[-1].add_field(
    #                             name=f"<:ERMList:1111099396990435428> {action['Type']}",
    #                             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['id']}",
    #                             inline=False,
    #                         )
    #                     else:
    #                         new_embed = discord.Embed(
    #                             title=embeds[0].title, color=0xED4348
    #                         )
    #
    #                         embeds.append(new_embed)
    #                         embeds[-1].add_field(
    #                             name=f"<:ERMList:1111099396990435428> {action['Type']}",
    #                             value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {action['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp())}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**ID:** {action['id']}",
    #                             inline=False,
    #                         )
    #
    #         for index, embed in enumerate(embeds):
    #             async with aiohttp.ClientSession() as session:
    #                 async with session.get(
    #                     f"https://thumbnails.roblox.com/v1/users/avatar?userIds={User.id}&size=420x420&format=Png"
    #                 ) as f:
    #                     if f.status == 200:
    #                         avatar = await f.json()
    #                         avatar = avatar["data"][0]["imageUrl"]
    #                     else:
    #                         avatar = ""
    #             embed.set_thumbnail(url=avatar)
    #             embed.set_author(
    #                 name=f"{ctx.author.name}",
    #                 icon_url=ctx.author.display_avatar.url,
    #             )
    #             if index != 0:
    #                 embed.set_footer(
    #                     text=f"Navigate this page by using the reactions below."
    #                 )
    #
    #         if ctx.interaction:
    #             interaction = ctx.interaction
    #         else:
    #             interaction = ctx
    #         menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, timeout=None)
    #         menu.add_buttons([ViewButton.back(), ViewButton.next()])
    #         new_embeds = []
    #         for embed in embeds:
    #             new_embeds.append(embed)
    #         menu.add_pages(new_embeds)
    #         await menu.start()


async def setup(bot):
    await bot.add_cog(Search(bot))
