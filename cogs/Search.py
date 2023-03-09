import datetime
import logging

import aiohttp
import discord
import pytz
from discord import app_commands
from discord.ext import commands
from reactionmenu import ViewMenu, ViewButton
from roblox import client as roblox

from erm import is_staff, staff_field, check_privacy
from utils.autocompletes import user_autocomplete
from utils.utils import invis_embed

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
        bot = self.bot
        alerts = {
            "NoAlerts": "<:ArrowRight:1035003246445596774> No alerts found for this account!",
            "AccountAge": "<:ArrowRight:1035003246445596774> The account age of the user is less than 100 days.",
            "NoDescription": "<:ArrowRight:1035003246445596774> This account has no description.",
            "SuspiciousUsername": "<:ArrowRight:1035003246445596774> This account could be an alt account.",
            "MassPunishments": "<:ArrowRight:1035003246445596774> This user exceeds the regular amount of warnings that a user should have.",
            "UserDoesNotExist": "<:ArrowRight:1035003246445596774> This user does not exist.",
            "IsBanned": "<:ArrowRight:1035003246445596774> This user is banned from Roblox.",
            "NotManyFriends": "<:ArrowRight:1035003246445596774> This user has less than 30 friends.",
            "NotManyGroups": "<:ArrowRight:1035003246445596774> This user has less than 5 groups.",
            "HasBOLO": "<:ArrowRight:1035003246445596774> This user has a BOLO active.",
        }

        user = query
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

        RESULTS = []
        query = requestJson["name"]

        dataset = await bot.warnings.find_by_id(query.lower())
        try:
            logging.info(dataset["warnings"][0])
        except:
            dataset = None
        if dataset:
            logging.info(dataset)
            dataset["warnings"][0]["name"] = query.lower()
            RESULTS.append(dataset["warnings"])

        if len(RESULTS) == 0:
            try:
                User = await client.get_user_by_username(query)
            except:
                return await invis_embed(ctx, "No user matches your query.")

            triggered_alerts = []

            if User.is_banned:
                triggered_alerts.append("IsBanned")
            if (
                pytz.utc.localize(datetime.datetime.utcnow()) - User.created
            ).days < 100:
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

            embed1 = discord.Embed(title=f"{query} ({User.id})", color=0x2E3136)
            embed1.set_author(
                name=f"{ctx.author.name}#{ctx.author.discriminator}",
                icon_url=ctx.author.display_avatar.url,
            )
            if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
                await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])
            embed1.add_field(
                name="<:MalletWhite:1035258530422341672> Punishments",
                value=f"<:ArrowRight:1035003246445596774> 0",
                inline=False,
            )
            string = "\n".join([alerts[i] for i in triggered_alerts])

            embed1.add_field(
                name="<:WarningIcon:1035258528149033090> Alerts",
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

            await ctx.send(embed=embed1)

        if len(RESULTS) > 1:
            return await invis_embed(
                ctx,
                "More than one result match your query. If this is unexpected, join the [support server](https://discord.gg/5pMmJEYazQ) and contact a Support Team member.",
            )

        if len(RESULTS) == 1:
            message = ctx.message

            result_var = None
            logging.info(message.content.lower())

            for result in RESULTS:
                if result[0]["name"] == RESULTS[0][0]["name"]:
                    result_var = RESULTS[0]

            result = result_var

            triggered_alerts = []

            User = await client.get_user_by_username(
                result[0]["name"], expand=True, exclude_banned_users=False
            )

            embed1 = discord.Embed(
                title=f"{RESULTS[0][0]['name']} ({User.id})", color=0x2E3136
            )
            embed2 = discord.Embed(
                title=f"{RESULTS[0][0]['name']} ({User.id})", color=0x2E3136
            )

            listOfPerGuild = []
            for item in result:
                if item["Guild"] == ctx.guild.id:
                    listOfPerGuild.append(item)

            if User.is_banned:
                triggered_alerts.append("IsBanned")
            if (
                pytz.utc.localize(datetime.datetime.utcnow()) - User.created
            ).days < 100:
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

            for warning in listOfPerGuild:
                if warning["Type"].upper() == "BOLO":
                    triggered_alerts.append("HasBOLO")
                    break

            if len(triggered_alerts) == 0:
                triggered_alerts.append("NoAlerts")

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
            embeds = [embed1, embed2]

            if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
                await staff_field(bot, embeds[0], embed1.title.lower().split(" ")[0])

            embeds[0].add_field(
                name="<:MalletWhite:1035258530422341672> Punishments",
                value=f"<:ArrowRight:1035003246445596774> {len(listOfPerGuild)}",
                inline=False,
            )
            string = "\n".join([alerts[i] for i in triggered_alerts])
            embeds[0].add_field(
                name="<:WarningIcon:1035258528149033090> Alerts",
                value=f"{string}",
                inline=False,
            )
            print(result)

            for action in result:
                if action["Guild"] == ctx.guild.id:
                    if isinstance(action["Moderator"], list):
                        user = discord.utils.get(
                            ctx.guild.members, id=action["Moderator"][1]
                        )
                        if user:
                            action["Moderator"] = user.mention
                        else:
                            action["Moderator"] = action["Moderator"][1]
                    if "Until" in action.keys():
                        if len(embeds[-1].fields) <= 2:
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                                inline=False,
                            )
                        else:
                            new_embed = discord.Embed(
                                title=embeds[0].title, color=0x2E3136
                            )

                            embeds.append(new_embed)
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                                inline=False,
                            )
                    else:
                        if len(embeds[-1].fields) <= 2:
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                                inline=False,
                            )
                        else:
                            new_embed = discord.Embed(
                                title=embeds[0].title, color=0x2E3136
                            )

                            embeds.append(new_embed)
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
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
                    name=f"{ctx.author.name}#{ctx.author.discriminator}",
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
        bot = self.bot
        user = query
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
                        if "success" not in robloxUser.keys():
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

        embed = discord.Embed(title=query, color=0x2E3136)
        embed.add_field(
            name=f"<:LinkIcon:1044004006109904966> Username",
            value=f"<:ArrowRight:1035003246445596774> {query}",
            inline=False,
        )
        embed.add_field(
            name="<:Search:1035353785184288788> User ID",
            value=f"<:ArrowRight:1035003246445596774> `{user_id}`",
            inline=False,
        )
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text="Search Module")
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="globalsearch",
        aliases=["gs"],
        description="Searches for a user in the warning database. This will show warnings from all servers.",
        extras={"category": "Search"},
        usage="<user>",
        with_app_command=True,
    )
    @is_staff()
    @app_commands.autocomplete(query=user_autocomplete)
    @app_commands.describe(
        query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username."
    )
    async def globalsearch(self, ctx, *, query):
        bot = self.bot
        alerts = {
            "NoAlerts": "<:ArrowRight:1035003246445596774> No alerts found for this account!",
            "AccountAge": "<:ArrowRight:1035003246445596774> The account age of the user is less than 100 days.",
            "NoDescription": "<:ArrowRight:1035003246445596774> This account has no description.",
            "SuspiciousUsername": "<:ArrowRight:1035003246445596774> This account could be an alt account.",
            "MassPunishments": "<:ArrowRight:1035003246445596774> This user exceeds the regular amount of warnings that a user should have.",
            "UserDoesNotExist": "<:ArrowRight:1035003246445596774> This user does not exist.",
            "IsBanned": "<:ArrowRight:1035003246445596774> This user is banned from Roblox.",
            "NotManyFriends": "<:ArrowRight:1035003246445596774> This user has less than 30 friends.",
            "NotManyGroups": "<:ArrowRight:1035003246445596774> This user has less than 5 groups.",
        }
        user = query
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

        RESULTS = []
        query = requestJson["name"]

        dataset = await bot.warnings.find_by_id(query.lower())
        if dataset:
            logging.info(dataset)
            try:
                logging.info(dataset["warnings"][0])
                dataset["warnings"][0]["name"] = query.lower()
                RESULTS.append(dataset["warnings"])
            except:
                pass

        if len(RESULTS) == 0:
            try:
                User = await client.get_user_by_username(query)
            except:
                return await invis_embed(ctx, "No user matches your query.")
            triggered_alerts = []

            if User.is_banned:
                triggered_alerts.append("IsBanned")
            if (
                pytz.utc.localize(datetime.datetime.utcnow()) - User.created
            ).days < 100:
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

            embed1 = discord.Embed(title=f"{User.name} ({User.id})", color=0x2E3136)
            embed1.set_author(
                name=f"{ctx.author.name}#{ctx.author.discriminator}",
                icon_url=ctx.author.display_avatar.url,
            )

            if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
                await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])

            embed1.add_field(
                name="<:MalletWhite:1035258530422341672> Punishments",
                value=f"<:ArrowRight:1035003246445596774> 0",
                inline=False,
            )
            string = "\n".join([alerts[i] for i in triggered_alerts])
            embed1.add_field(
                name="<:WarningIcon:1035258528149033090> Alerts",
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
                    else:
                        avatar = ""
            embed1.set_thumbnail(url=avatar)

            await ctx.send(embed=embed1)
        if len(RESULTS) == 1:
            result_var = None

            for result in RESULTS:
                if result[0]["name"] == RESULTS[0][0]["name"]:
                    result_var = RESULTS[0]

            result = result_var
            triggered_alerts = []

            for warning in result:
                if not warning["Guild"] == ctx.guild.id:
                    privacySettings = await check_privacy(
                        bot, warning["Guild"], "global_warnings"
                    )
                    if not privacySettings:
                        result.remove(warning)

            try:
                User = await client.get_user_by_username(
                    result[0]["name"], expand=True, exclude_banned_users=False
                )
                embed1 = discord.Embed(title=f"{User.name} ({User.id})", color=0x2E3136)
                embed2 = discord.Embed(title=f"{User.name} ({User.id})", color=0x2E3136)
            except (IndexError, KeyError):
                try:
                    User = await client.get_user_by_username(
                        query, exclude_banned_users=False, expand=True
                    )
                    embed1 = discord.Embed(
                        title=f"{User.name} ({User.id})", color=0x2E3136
                    )
                    embed2 = discord.Embed(
                        title=f"{User.name} ({User.id})", color=0x2E3136
                    )
                except:
                    return await invis_embed(ctx, "No user matches your query.")
                triggered_alerts = []

                if User.is_banned:
                    triggered_alerts.append("IsBanned")
                if (
                    pytz.utc.localize(datetime.datetime.utcnow()) - User.created
                ).days < 100:
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
                embed1 = discord.Embed(title=query, color=0x2E3136)

                embed1.set_author(
                    name=f"{ctx.author.name}#{ctx.author.discriminator}",
                    icon_url=ctx.author.display_avatar.url,
                )

                if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
                    await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])

                embed1.add_field(
                    name="<:MalletWhite:1035258530422341672> Punishments",
                    value=f"<:ArrowRight:1035003246445596774> 0",
                    inline=False,
                )
                string = "\n".join([alerts[i] for i in triggered_alerts])
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://thumbnails.roblox.com/v1/users/avatar?userIds={User.id}&size=420x420&format=Png"
                    ) as f:
                        if f.status == 200:
                            avatar = await f.json()
                            avatar = avatar["data"][0]["imageUrl"]
                        else:
                            avatar = ""
                embed1.add_field(
                    name="<:WarningIcon:1035258528149033090> Alerts",
                    value=f"{string}",
                    inline=False,
                )

                embed1.set_thumbnail(url=avatar)
                return await ctx.send(embed=embed1)

            if User.is_banned:
                triggered_alerts.append("IsBanned")
            if (
                pytz.utc.localize(datetime.datetime.utcnow()) - User.created
            ).days < 100:
                triggered_alerts.append("AccountAge")
            if not User:
                triggered_alerts.append("UserDoesNotExist")
            if len(User.description) < 10:
                triggered_alerts.append("NoDescription")
            if any(x in User.name for x in ["alt", "alternative", "account"]):
                triggered_alerts.append("SuspiciousUsername")
            if len(result) > 5:
                triggered_alerts.append("MassPunishments")
            if await User.get_friend_count() <= 30:
                triggered_alerts.append("NotManyFriends")
            if len(await User.get_group_roles()) <= 5:
                triggered_alerts.append("NotManyGroups")

            if len(triggered_alerts) == 0:
                triggered_alerts.append("NoAlerts")

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await invis_embed(
                    ctx,
                    "The server has not been set up yet. Please run `/setup` to set up the server.",
                )

            embeds = [embed1, embed2]

            if await bot.flags.find_by_id(embed1.title.lower().split(" ")[0]):
                await staff_field(bot, embed1, embed1.title.lower().split(" ")[0])

            embeds[0].add_field(
                name="<:MalletWhite:1035258530422341672> Punishments",
                value=f"<:ArrowRight:1035003246445596774> {len(result)}",
                inline=False,
            )
            string = "\n".join([alerts[i] for i in triggered_alerts])
            embeds[0].add_field(
                name="<:WarningIcon:1035258528149033090> Alerts",
                value=f"{string}",
                inline=False,
            )

            del result[0]["name"]

            for index, action in enumerate(result):
                if "Until" in action.keys():
                    if "Until" in action.keys():
                        if len(embeds[-1].fields) <= 2:
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                                inline=False,
                            )
                        else:
                            new_embed = discord.Embed(
                                title=embeds[0].title, color=0x2E3136
                            )

                            embeds.append(new_embed)
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                                inline=False,
                            )
                    else:
                        if len(embeds[-1].fields) <= 2:
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(action['Time'], str) else int(action['Time'])}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                                inline=False,
                            )
                        else:
                            new_embed = discord.Embed(
                                title=embeds[0].title, color=0x2E3136
                            )

                            embeds.append(new_embed)
                            embeds[-1].add_field(
                                name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(action['Time'], '%m/%d/%Y, %H:%M:%S').timestamp())}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
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
                        else:
                            avatar = ""
                embed.set_thumbnail(url=avatar)
                embed.set_author(
                    name=f"{ctx.author.name}#{ctx.author.discriminator}",
                    icon_url=ctx.author.display_avatar.url,
                )
                if index != 0:
                    embed.set_footer(
                        text=f"Navigate this page by using the reactions below."
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


async def setup(bot):
    await bot.add_cog(Search(bot))
