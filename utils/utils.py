import datetime
import typing

import aiohttp
import discord
from discord import Embed
from discord.ext import commands
from snowflake import SnowflakeGenerator
from zuid import ZUID

tokenGenerator = ZUID(
    prefix="",
    length=64,
    timestamped=True,
    charset="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_",
)

generator = SnowflakeGenerator(192)
error_gen = ZUID(prefix="error_", length=10)
system_code_gen = ZUID(prefix="erm-systems-", length=7)


def removesuffix(input_string: str, suffix: str):
    if suffix and input_string.endswith(suffix):
        return input_string[: -len(suffix)]
    return input_string


def get_guild_icon(
    bot: typing.Union[commands.Bot, commands.AutoShardedBot], guild: discord.Guild
):
    if guild.icon is None:
        return bot.user.display_avatar.url
    else:
        return guild.icon.url


async def get_roblox_by_username(user: str, bot, ctx: commands.Context):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://users.roblox.com/v1/usernames/users",
            json={"usernames": [user]},
        ) as r:
            try:
                requestJson = await r.json()
                should_switch = len(requestJson["data"]) == 0
            except:
                requestJson = None
                should_switch = False

            if r.status == 200 and should_switch is False:
                requestJson = requestJson["data"][0]
                Id = requestJson["id"]
                async with session.get(f"https://users.roblox.com/v1/users/{Id}") as r:
                    requestJson = await r.json()
                    return requestJson
            else:
                async with session.post(
                    f"https://users.roblox.com/v1/usernames/users",
                    json={"usernames": [user]},
                ) as r:
                    requestJson = await r.json()
                    if len(requestJson["data"]) != 0:
                        requestJson = requestJson["data"][0]
                        Id = requestJson["id"]
                        async with session.get(
                            f"https://users.roblox.com/v1/users/{Id}"
                        ) as r:
                            requestJson = await r.json()
                            return requestJson
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
                                        return requestJson
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
                                                requestJson = {
                                                    "errors": [
                                                        "No username could be found."
                                                    ]
                                                }
                                                return requestJson
                                            Id = tempRBXID
                                            async with session.get(
                                                f"https://users.roblox.com/v1/users/{Id}"
                                            ) as r:
                                                requestJson = await r.json()
                                                return requestJson
                        except discord.ext.commands.MemberNotFound:
                            requestJson = {
                                "errors": ["Member could not be found in Discord."]
                            }
                            return requestJson

    return requestJson


async def interpret_embed(bot, ctx, channel, embed: dict):
    embed = discord.Embed.from_dict(embed)
    try:
        embed.title = await sub_vars(bot, ctx, channel, embed.title)
    except:
        pass
    try:
        embed.set_author(name=await sub_vars(bot, ctx, channel, embed.author.name))
    except:
        pass
    try:
        embed.description = await sub_vars(bot, ctx, channel, embed.description)
    except:
        pass
    try:
        embed.set_footer(
            text=await sub_vars(bot, ctx, channel, embed.footer.text),
            icon_url=embed.footer.icon_url,
        )
    except:
        pass
    for i in embed.fields:
        i.name = await sub_vars(bot, ctx, channel, i.name)
        i.value = await sub_vars(bot, ctx, channel, i.value)

    return embed


async def interpret_content(bot, ctx, channel, content: str):
    return await sub_vars(bot, ctx, channel, content)


async def sub_vars(bot, ctx, channel, string, **kwargs):
    string = string.replace("{user}", ctx.author.mention)
    string = string.replace("{username}", ctx.author.name)
    string = string.replace("{display_name}", ctx.author.name)
    string = string.replace("{time}", f"<t:{int(datetime.datetime.now().timestamp())}>")
    string = string.replace("{server}", ctx.guild.name)
    string = string.replace("{channel}", channel.mention)
    string = string.replace("{prefix}", list(await get_prefix(bot, ctx))[-1])
    return string


async def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(">")(bot, message)

    try:
        prefix = await bot.settings.find_by_id(message.guild.id)
        prefix = prefix["customisation"]["prefix"]
    except:
        return discord.ext.commands.when_mentioned_or(">")(bot, message)

    return commands.when_mentioned_or(prefix)(bot, message)


async def end_break(bot, shift, shift_type, configItem, ctx, msg, member, manage: bool):
    for item in shift["Breaks"]:
        if item["EndEpoch"] == 0:
            item["EndEpoch"] = ctx.message.created_at.timestamp()

    await bot.shift_management.shifts.update_by_id(shift)

    if manage:
        await msg.edit(
            embed=None,
            view=None,
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've ended your break.",
        )
    else:
        await msg.edit(
            embed=None,
            view=None,
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've ended **{member.name}**'s break.",
        )

    nickname_prefix = None
    changed_nick = False
    role = None

    if shift_type:
        if shift_type.get("nickname"):
            nickname_prefix = shift_type.get("nickname")
    else:
        if configItem["shift_management"].get("nickname_prefix"):
            nickname_prefix = configItem["shift_management"].get("nickname_prefix")

    if nickname_prefix:
        current_name = member.nick if member.nick else member.name
        new_name = "{}{}".format(nickname_prefix, current_name)

        try:
            await member.edit(nick=new_name)
            changed_nick = True
        except Exception as e:
            print(e)
            pass

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
            if not rl in member.roles and rl is not None:
                try:
                    await member.add_roles(rl)
                except:
                    await failure_embed(ctx, f"could not add {rl} to {member.mention}")


async def invis_embed(ctx: commands.Context, content: str, **kwargs) -> discord.Message:
    msg = await ctx.send(
        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, {content}",
        **kwargs,
    )
    return msg


async def failure_embed(
    ctx: commands.Context, content: str, **kwargs
) -> discord.Message:
    msg = await ctx.send(
        content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, {content}",
        **kwargs,
    )
    return msg


async def int_failure_embed(interaction, content, **kwargs):
    try:
        await interaction.response.send_message(
            content=f"<:ERMClose:1111101633389146223>  **{interaction.user.name}**, {content}",
            **kwargs,
        )
    except discord.InteractionResponded:
        await interaction.response.send_message(
            content=f"<:ERMClose:1111101633389146223>  **{interaction.user.name}**, {content}",
            **kwargs,
        )


async def int_pending_embed(interaction, content, **kwargs):
    try:
        await interaction.response.send_message(
            content=f"<:ERMPending:1111097561588183121>  **{interaction.user.name}**, {content}",
            **kwargs,
        )
    except discord.InteractionResponded:
        await interaction.response.send_message(
            content=f"<:ERMPending:1111097561588183121>  **{interaction.user.name}**, {content}",
            **kwargs,
        )


async def pending_embed(
    ctx: commands.Context, content: str, **kwargs
) -> discord.Message:
    msg = await ctx.send(
        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {content}",
        **kwargs,
    )
    return msg


async def int_invis_embed(interaction, content, **kwargs):
    try:
        await interaction.response.send_message(
            content=f"<:ERMCheck:1111089850720976906>  **{interaction.user.name}**, {content}",
            **kwargs,
        )
    except discord.InteractionResponded:
        await interaction.response.send_message(
            content=f"<:ERMCheck:1111089850720976906>  **{interaction.user.name}**, {content}",
            **kwargs,
        )


async def coloured_embed(
    ctx: commands.Context, content: str, **kwargs
) -> discord.Message:
    embed = Embed(color=0xED4348, description=f"{content}")
    msg = await ctx.send(embed=embed, **kwargs)
    return msg


async def int_coloured_embed(interaction, content, **kwargs):
    embed = Embed(color=0xED4348, description=f"{content}")
    try:
        await interaction.response.send_message(embed=embed, **kwargs)
    except discord.InteractionResponded:
        await interaction.edit_original_response(embed=embed, **kwargs)


async def request_response(bot, ctx, question, **kwargs):
    await ctx.send(
        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
        **kwargs,
    )
    try:
        response = await bot.wait_for(
            "message",
            check=lambda message: message.author == ctx.author
            and message.guild.id == ctx.guild.id,
            timeout=300,
        )
    except:
        raise Exception("No response")
    return response


def make_ordinal(n):
    """
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    """
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return str(n) + suffix
