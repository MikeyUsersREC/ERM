import datetime
import typing

import discord
from discord import Embed
from discord.ext import commands


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


async def invis_embed(ctx: commands.Context, content: str, **kwargs) -> discord.Message:
    embed = Embed(
        color=0x2A2D31, description=f"<:ArrowRight:1035003246445596774> {content}"
    )
    msg = await ctx.send(embed=embed, **kwargs)
    return msg


async def int_invis_embed(interaction, content, **kwargs):
    embed = Embed(
        color=0x2A2D31, description=f"<:ArrowRight:1035003246445596774> {content}"
    )
    try:
        await interaction.response.send_message(embed=embed, **kwargs)
    except discord.InteractionResponded:
        await interaction.edit_original_response(embed=embed, **kwargs)


def create_invis_embed(content: str, **kwargs) -> discord.Embed:
    embed = Embed(
        color=0x2A2D31, description=f"<:ArrowRight:1035003246445596774> {content}"
    )
    return embed


async def coloured_embed(
    ctx: commands.Context, content: str, **kwargs
) -> discord.Message:
    embed = Embed(color=0x2A2D31, description=f"{content}")
    msg = await ctx.send(embed=embed, **kwargs)
    return msg


async def int_coloured_embed(interaction, content, **kwargs):
    embed = Embed(color=0x2A2D31, description=f"{content}")
    try:
        await interaction.response.send_message(embed=embed, **kwargs)
    except discord.InteractionResponded:
        await interaction.edit_original_response(embed=embed, **kwargs)


async def request_response(bot, ctx, question, **kwargs):
    embed = discord.Embed(
        color=0x2A2D31, description=f"<:ArrowRight:1035003246445596774> {question}"
    )
    await ctx.send(embed=embed, **kwargs)
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
