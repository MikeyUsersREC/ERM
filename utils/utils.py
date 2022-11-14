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

def strip_string(value: str):
    import re
    emojis = re.findall("<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>", str(value))
    for emoji in emojis:
        emoji_full = '<:' + list(emoji)[1] + ":" + list(emoji)[2] + ">"

        if 'Check' not in emoji_full and 'Error' not in emoji_full:
            print(2)
            value = value.replace(str(emoji_full), "")
    return value
async def compact(embed, bot: typing.Union[discord.ext.commands.Bot, discord.ext.commands.AutoShardedBot], guild: int):
    settings = bot.settings
    guild_settings = await settings.find_by_id(guild)
    if guild_settings != None:
        if 'compact_mode' in guild_settings['customisation']:
            if guild_settings['customisation']['compact_mode'] == True:
                embed.title = strip_string(embed.title)
                embed.description = strip_string(embed.description)
                for index, field in enumerate(embed.fields):
                    name = strip_string(field.name)
                    value = strip_string(field.value)
                    field.name = name
                    field.value = value
                    embed.fields[index] = field
                    print(embed.fields)

async def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or('>')(bot, message)

    try:
        prefix = await bot.settings.find_by_id(message.guild.id)
        prefix = prefix['customisation']['prefix']
    except:
        return discord.ext.commands.when_mentioned_or('>')(bot, message)

    return commands.when_mentioned_or(prefix)(bot, message)

async def invis_embed(bot: typing.Union[commands.AutoShardedBot, commands.Bot], ctx: commands.Context, content: str, **kwargs):
    embed = Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {content}")
    await compact(embed, bot, ctx.guild.id)
    await ctx.send(embed=embed, **kwargs)


async def int_invis_embed(bot, interaction, content, **kwargs):
    embed = Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {content}")
    await compact(embed, bot, interaction.guild.id)
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
