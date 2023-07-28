import copy
import datetime
import logging
import string

import aiohttp
import discord
import num2words
from discord.ext import commands
from reactionmenu import Page, ViewButton, ViewMenu, ViewSelect

from utils.utils import generator
from menus import CustomSelectMenu
from utils.timestamp import td_format
from utils.utils import get_guild_icon, get_prefix, invis_embed


class OnMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        bot = self.bot
        bypass_role = None

        if not hasattr(bot, "settings"):
            return

        if message.author == bot.user:
            return

        if not message.guild:
            return

        dataset = await bot.settings.find_by_id(message.guild.id)
        if dataset == None:
            return

        antiping_roles = None
        bypass_roles = None

        if "bypass_role" in dataset["antiping"].keys():
            bypass_role = dataset["antiping"]["bypass_role"]

        if isinstance(bypass_role, list):
            bypass_roles = [
                discord.utils.get(message.guild.roles, id=role) for role in bypass_role
            ]
        else:
            bypass_roles = [discord.utils.get(message.guild.roles, id=bypass_role)]

        if isinstance(dataset["antiping"]["role"], list):
            antiping_roles = [
                discord.utils.get(message.guild.roles, id=role)
                for role in dataset["antiping"]["role"]
            ]
        elif isinstance(dataset["antiping"]["role"], int):
            antiping_roles = [
                discord.utils.get(message.guild.roles, id=dataset["antiping"]["role"])
            ]
        else:
            antiping_roles = None

        aa_detection = False
        aa_detection_channel = None
        webhook_channel = None
        moderation_sync = False
        sync_channel = None

        if "game_security" in dataset.keys() or "moderation_sync" in dataset.keys():
            if "game_security" in dataset.keys():
                if "enabled" in dataset["game_security"].keys():
                    if (
                        "channel" in dataset["game_security"].keys()
                        and "webhook_channel" in dataset["game_security"].keys()
                    ):
                        if dataset["game_security"]["enabled"] is True:
                            aa_detection = True
                            webhook_channel = dataset["game_security"][
                                "webhook_channel"
                            ]
                            webhook_channel = discord.utils.get(
                                message.guild.channels, id=webhook_channel
                            )
                            aa_detection_channel = dataset["game_security"]["channel"]
                            aa_detection_channel = discord.utils.get(
                                message.guild.channels, id=aa_detection_channel
                            )
            if "moderation_sync" in dataset.keys():
                if dataset["moderation_sync"].get("enabled"):
                    if "webhook_channel" in dataset["moderation_sync"].keys():
                        sync_channel = dataset["moderation_sync"]["webhook_channel"]
                        sync_channel = discord.utils.get(
                            message.guild.channels, id=sync_channel
                        )

                        kick_ban_sync_channel = dataset["moderation_sync"][
                            "kick_ban_webhook_channel"
                        ]
                        kick_ban_sync_channel = discord.utils.get(
                            message.guild.channels, id=kick_ban_sync_channel
                        )

                        sync_channels = []
                        if sync_channel:
                            sync_channels.append(sync_channel.id)
                        if kick_ban_sync_channel:
                            sync_channels.append(kick_ban_sync_channel.id)

                        moderation_sync = True

        if moderation_sync is True:
            if sync_channels is not None:
                if message.channel.id in sync_channels:
                    for embed in message.embeds:
                        if embed.description not in ["", None] and embed.title not in [
                            "",
                            None,
                        ]:
                            if ":m " in embed.description:
                                if "Command Usage" in embed.title:
                                    raw_content = embed.description
                                    user, command = raw_content.split(
                                        "used the command: `"
                                    )

                                    profile_link = user.split("(")[1].split(")")[0]

                                    msg = "".join(command.split(":m ")[1:]).replace(
                                        "`", ""
                                    )

                                    discord_user = 0
                                    async for document in bot.synced_users.db.find(
                                        {"roblox": str(profile_link.split("/")[4])}
                                    ):
                                        discord_user = document["_id"]

                                    print(f"Discord User: {discord_user}")
                                    if discord_user == 0:
                                        await message.add_reaction("❌")
                                        return await message.add_reaction("6️⃣")

                                    user = discord.utils.get(
                                        message.guild.members, id=discord_user
                                    )
                                    if not user:
                                        user = await message.guild.fetch_member(
                                            discord_user
                                        )
                                        if not user:
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("7️⃣")

                                    new_message = copy.copy(message)
                                    new_message.channel = await user.create_dm()
                                    new_message.author = user

                                    new_ctx = await bot.get_context(new_message)
                                    ctx = new_ctx

                                    configItem = await bot.settings.find_by_id(
                                        ctx.guild.id
                                    )
                                    if not configItem:
                                        return

                                    if not configItem.get("game_logging"):
                                        return
                                    if not configItem["game_logging"].get("message"):
                                        return

                                    if (
                                        not configItem["game_logging"]
                                        .get("message")
                                        .get("enabled")
                                    ):
                                        return
                                    if (
                                        not configItem["game_logging"]
                                        .get("message")
                                        .get("channel")
                                    ):
                                        return
                                    channel = ctx.guild.get_channel(
                                        configItem["game_logging"]["message"]["channel"]
                                    )
                                    if not channel:
                                        return
                                    embed = discord.Embed(
                                        title="<:LinkIcon:1044004006109904966> Message Logging",
                                        description=f"<:ArrowRight:1035003246445596774> Please enter the message you would like to log.",
                                        color=0xED4348,
                                    )

                                    announcement = msg

                                    embed = discord.Embed(
                                        title="<:MessageIcon:1035321236793860116> Message Logged",
                                        description="*A new message has been logged in the server.*",
                                        color=0xED4348,
                                    )

                                    embed.set_author(
                                        name=ctx.author.name,
                                        icon_url=ctx.author.display_avatar.url,
                                    )

                                    embed.add_field(
                                        name="<:staff:1035308057007230976> Staff Member",
                                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
                                        inline=False,
                                    )

                                    embed.add_field(
                                        name="<:MessageIcon:1035321236793860116> Message",
                                        value=f"<:ArrowRight:1035003246445596774> `{announcement}`",
                                        inline=False,
                                    )

                                    await channel.send(embed=embed)

                                    success_embed = discord.Embed(
                                        title="<:CheckIcon:1035018951043842088> Success!",
                                        description=f"<:ArrowRight:1035003246445596774> The message has been logged.",
                                        color=0x71C15F,
                                    )

                                    await ctx.send(embed=success_embed)
                                return

        if aa_detection == True:
            if webhook_channel != None:
                print("webhook channel")
                if message.channel.id == webhook_channel.id:
                    for embed in message.embeds:
                        print("embed found")
                        if embed.description not in ["", None] and embed.title not in [
                            "",
                            None,
                        ]:
                            print("embed desc")
                            if (
                                "kicked" in embed.description
                                or "banned" in embed.description
                            ):
                                print("used kick/ban command")
                                if (
                                    "Players Kicked" in embed.title
                                    or "Players Banned" in embed.title
                                ):
                                    print("command usage")
                                    raw_content = embed.description
                                    if "kicked" in raw_content:
                                        user, command = raw_content.split(" kicked `")
                                    else:
                                        user, command = raw_content.split(" banned `")
                                    command = command.replace("`", "")
                                    code = embed.footer.text.split("Server: ")[1]
                                    if command.count(",") + 1 >= 5:
                                        embed = discord.Embed(
                                            title="<:ERMAlert:1113237478892130324> Excessive Moderations Detected",
                                            color=0xED4348,
                                        )

                                        embed.add_field(
                                            name="<:ERMAdmin:1111100635736187011> Staff Member:",
                                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{user.split(':')[0] + ']' + user.split(']')[1]}",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:ERMPunish:1111095942075138158> Trigger:",
                                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**{command.count(',') + 1}** kicks/bans in a single command.",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:ERMMisc:1113215605424795648> Explanation",
                                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>On <t:{int(message.created_at.timestamp())}>, {user.split(':')[0].replace('[', '').replace(']', '')} simultaneously kicked/banned {command.count(',') + 1} people from **{code}**",
                                            inline=False,
                                        )

                                        pings = []
                                        if "role" in dataset["game_security"].keys():
                                            if (
                                                dataset["game_security"]["role"]
                                                is not None
                                            ):
                                                if isinstance(
                                                    dataset["game_security"]["role"],
                                                    list,
                                                ):
                                                    for role in dataset[
                                                        "game_security"
                                                    ]["role"]:
                                                        role = discord.utils.get(
                                                            message.guild.roles, id=role
                                                        )
                                                        pings.append(role.mention)

                                        await aa_detection_channel.send(
                                            ",".join(pings) if pings != [] else "",
                                            embed=embed,
                                            allowed_mentions=discord.AllowedMentions(
                                                everyone=True,
                                                users=True,
                                                roles=True,
                                                replied_user=True,
                                            ),
                                        )
                                    if " all" in command:
                                        embed = discord.Embed(
                                            title="<:ERMAlert:1113237478892130324> Excessive Moderations Detected",
                                            color=0xED4348,
                                        )

                                        embed.add_field(
                                            name="<:ERMAdmin:1111100635736187011> Staff Member:",
                                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{user}",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:ERMPunish:1111095942075138158> Trigger:",
                                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Kicking/Banning everyone in the server",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:ERMMisc:1113215605424795648> Explanation",
                                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>On <t:{int(message.created_at.timestamp())}>, {user.split(']')[0].replace('[').replace(']')} kicked/banned everyone from **{code}**",
                                            inline=False,
                                        )

                                        pings = []
                                        if "role" in dataset["game_security"].keys():
                                            if (
                                                dataset["game_security"]["role"]
                                                is not None
                                            ):
                                                if isinstance(
                                                    dataset["game_security"]["role"],
                                                    list,
                                                ):
                                                    for role in dataset[
                                                        "game_security"
                                                    ]["role"]:
                                                        role = discord.utils.get(
                                                            message.guild.roles, id=role
                                                        )
                                                        pings.append(role.mention)

                                        await aa_detection_channel.send(
                                            ",".join(pings) if pings != [] else "",
                                            embed=embed,
                                            allowed_mentions=discord.AllowedMentions(
                                                everyone=True,
                                                users=True,
                                                roles=True,
                                                replied_user=True,
                                            ),
                                        )

        if message.author.bot:
            return

        if antiping_roles is None:
            return

        if (
            dataset["antiping"]["enabled"] is False
            or dataset["antiping"]["role"] is None
        ):
            return

        if bypass_roles is not None:
            for role in bypass_roles:
                if role in message.author.roles:
                    return

        for mention in message.mentions:
            isStaffPermitted = False
            logging.info(isStaffPermitted)

            if mention.bot:
                return

            if dataset["antiping"].get("use_hierarchy") in [True, None]:
                for role in antiping_roles:
                    if role != None:
                        if (
                            message.author.top_role > role
                            or message.author.top_role == role
                        ):
                            return

            if message.author == message.guild.owner:
                return

            if not isStaffPermitted:
                for role in antiping_roles:
                    print(antiping_roles)
                    print(role)
                    if dataset["antiping"].get("use_hierarchy") in [True, None]:
                        if role is not None:
                            if mention.top_role > role or mention.top_role == role:
                                embed = discord.Embed(
                                    title=f"Do not ping {role.name} or above!",
                                    color=discord.Color.red(),
                                    description=f"Do not ping {role.name} or above!\nIt is a violation of the rules, and you will be punished if you continue.",
                                )
                                try:
                                    msg = await message.channel.fetch_message(
                                        message.reference.message_id
                                    )
                                    if msg.author == mention:
                                        embed.set_image(
                                            url="https://i.imgur.com/pXesTnm.gif"
                                        )
                                except:
                                    pass

                                embed.set_footer(
                                    text=f'Thanks, {dataset["customisation"]["brand_name"]}',
                                    icon_url=get_guild_icon(bot, message.guild),
                                )

                                ctx = await bot.get_context(message)
                                await ctx.reply(
                                    f"{message.author.mention}", embed=embed
                                )
                                return
                            return
                        return
                    else:
                        if role is not None:
                            if (
                                role in mention.roles
                                and not role in message.author.roles
                            ):
                                embed = discord.Embed(
                                    title=f"Do not ping {role.name}!",
                                    color=discord.Color.red(),
                                    description=f"Do not ping those with {role.name}!\nIt is a violation of the rules, and you will be punished if you continue.",
                                )
                                try:
                                    msg = await message.channel.fetch_message(
                                        message.reference.message_id
                                    )
                                    if msg.author == mention:
                                        embed.set_image(
                                            url="https://i.imgur.com/pXesTnm.gif"
                                        )
                                except:
                                    pass

                                embed.set_footer(
                                    text=f'Thanks, {dataset["customisation"]["brand_name"]}',
                                    icon_url=get_guild_icon(bot, message.guild),
                                )

                                ctx = await bot.get_context(message)
                                await ctx.reply(
                                    f"{message.author.mention}", embed=embed
                                )
                                return

                            return

                        return


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
