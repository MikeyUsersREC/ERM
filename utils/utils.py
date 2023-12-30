import datetime
import typing
import aiohttp
import discord
import pytz
import roblox.users
from decouple import config
from discord import Embed, InteractionResponse, Webhook
from discord.ext import commands
from snowflake import SnowflakeGenerator
from zuid import ZUID
from utils.constants import BLANK_COLOR

tokenGenerator = ZUID(
    prefix="",
    length=64,
    timestamped=True,
    charset="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_",
)

generator = SnowflakeGenerator(192)
error_gen = ZUID(prefix="error_", length=10)
system_code_gen = ZUID(prefix="erm-systems-", length=7)


class BaseDataClass:
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


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


async def generalised_interaction_check_failure(responder: InteractionResponse | Webhook | typing.Callable):
    if isinstance(responder, typing.Callable):
        responder = responder()

    if isinstance(responder, InteractionResponse):
        await responder.send_message(
            embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=BLANK_COLOR
            ), ephemeral=True
        )
    else:
        await responder.send(
            embed=discord.Embed(
                title="Not Permitted",
                description="You are not permitted to interact with these buttons.",
                color=BLANK_COLOR
            )
        )


async def get_roblox_by_username(user: str, bot, ctx: commands.Context):
    if '<@' in user:
        try:
            member_converted = await (discord.ext.commands.MemberConverter()).convert(
                ctx, user
            )
            if member_converted:
                bl_user_data = await bot.bloxlink.find_roblox(member_converted.id)
                print(bl_user_data)
                roblox_user = await bot.bloxlink.get_roblox_info(bl_user_data['robloxID'])
                return roblox_user
        except KeyError:
            return {
                "errors": ["Member could not be found in Discord."]
            }

    client = roblox.Client()
    roblox_user = await client.get_user_by_username(user)
    if not roblox_user:
        return {
            "errors": [
                "Could not find user"
            ]
        }
    else:
        return await bot.bloxlink.get_roblox_info(roblox_user.id)


def time_converter(parameter: str) -> int:
    conversions = {
        ("s", "minutes", "seconds", " seconds"): 1,
        ("m", "minute", "minutes", " minutes"): 60,
        ("h", "hour", "hours", " hours"): 60 * 60,
        ("d", "day", "days", " days"): 24 * 60 * 60,
        ("w", "week", " weeks"): 7 * 24 * 60 * 60
    }

    for aliases, multiplier in conversions.items():
        parameter = parameter.strip()
        for alias in aliases:
            print(f"{alias} - {(parameter[(len(parameter) - len(alias)):])=}")
            if parameter[(len(parameter) - len(alias)):].lower() == alias.lower():
                alias_found = parameter[(len(parameter) - len(alias)):]
                number = parameter.split(alias_found)[0]
                if not number.strip()[-1].isdigit():
                    continue
                return int(number.strip()) * multiplier

    raise ValueError("Invalid time format")


class GuildCheckFailure(commands.CheckFailure):
    pass


def require_settings():
    async def predicate(ctx: commands.Context):
        settings = await ctx.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            raise GuildCheckFailure()
        else:
            return True

    return commands.check(predicate)


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


def get_elapsed_time(document):
    from datamodels.ShiftManagement import ShiftItem

    if isinstance(document, ShiftItem):
        new_document = {
            "Breaks": [{'StartEpoch': item.start_epoch, 'EndEpoch': item.end_epoch} for item in document.breaks],
            "StartEpoch": document.start_epoch,
            "EndEpoch": document.end_epoch,
            "AddedTime": document.added_time,
            "RemovedTime": document.removed_time
        }
        document = new_document
    total_seconds = 0
    break_seconds = 0
    for br in document["Breaks"]:
        if br['EndEpoch'] != 0:
            break_seconds += int(br["EndEpoch"]) - int(br["StartEpoch"])
        else:
            break_seconds += int(datetime.datetime.now(tz=pytz.UTC).timestamp() - int(br["StartEpoch"]))

    total_seconds += (
            (int(
                (
                    document["EndEpoch"]
                    if document["EndEpoch"] != 0
                    else datetime.datetime.now(tz=pytz.UTC).timestamp()
                )
            )
             - int(document["StartEpoch"])
             + document["AddedTime"]
             - document["RemovedTime"])
            - break_seconds
    )

    return total_seconds


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

    try:
        url_var = config("BASE_API_URL")
        if url_var in ["", None]:
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"{url_var}/Internal/SyncEndBreak/{shift['_id']}", headers={
                        "Authorization": config('INTERNAL_API_AUTH')
                    }):
                pass
    except:
        pass

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
            # # print(e)
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


async def new_failure_embed(
        ctx: commands.Context, title: str, description: str, **kwargs
) -> discord.Message:
    msg = await ctx.send(
        embed=discord.Embed(
            title=title,
            description=description,
            color=BLANK_COLOR
        )
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
