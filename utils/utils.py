from discord.ext import commands
import discord
import typing
from discord import Embed

def removesuffix(input_string: str, suffix: str):
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string


def get_guild_icon(bot: typing.Union[commands.Bot, commands.AutoShardedBot], guild: discord.Guild):
    if guild.icon is None:
        return bot.user.display_avatar.url
    else:
        return guild.icon.url

async def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or('>')(bot, message)

    try:
        prefix = await bot.settings.find_by_id(message.guild.id)
        prefix = prefix['customisation']['prefix']
    except:
        return discord.ext.commands.when_mentioned_or('>')(bot, message)

    return commands.when_mentioned_or(prefix)(bot, message)

async def invis_embed(ctx: commands.Context, content: str, **kwargs):
    embed = Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {content}")
    await ctx.send(embed=embed, **kwargs)


async def int_invis_embed(interaction, content, **kwargs):
    embed = Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {content}")
    await interaction.response.send_message(embed=embed, **kwargs)


async def request_response(bot, ctx, question, **kwargs):
    embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")
    await ctx.send(embed=embed, **kwargs)
    try:
        response = await bot.wait_for('message', check=lambda
            message: message.author == ctx.author and message.guild.id == ctx.guild.id, timeout=300)
    except:
        raise Exception('No response')
    return response
