import asyncio
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
from utils.prc_api import ServerStatus, Player
import utils.prc_api as prc_api
import requests
import json

class ArgumentMockingInstance:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.key = value


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
                # print(bl_user_data)
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
        if ctx.guild is None:
            return True
        settings = await ctx.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            raise GuildCheckFailure()
        else:
            return True

    return commands.check(predicate)

async def update_ics(bot, ctx, channel, return_val: dict, ics_id: int):
    try:
        status: ServerStatus = await bot.prc_api.get_server_status(ctx.guild.id)
    except prc_api.ResponseFailure:
        status = None
    if not isinstance(status, ServerStatus):
        return return_val # Invalid key
    
    queue: int = await bot.prc_api.get_server_queue(ctx.guild.id, minimal=True)
    players: list[Player] = await bot.prc_api.get_server_players(ctx.guild.id)
    mods: int = len(list(filter(lambda x: x.permission == "Server Moderator", players)))
    admins: int = len(list(filter(lambda x: x.permission == "Server Administrator", players)))
    total_staff: int = len(list(filter(lambda x: x.permission != 'Normal', players)))

    if await bot.ics.db.count_documents({'_id': ics_id}):
        await bot.ics.db.update_one({
            '_id': ics_id,
            "guild": ctx.guild.id
        }, {'$set': {
            'data': {
                'join_code': status.join_key,
                'players': status.current_players,
                'max_players': status.max_players,
                'queue': queue,
                'staff': total_staff,
                'admins': admins,
                'mods': mods
            }
        }})
    else:
        await bot.ics.insert({
            '_id': ics_id,
            "guild": ctx.guild.id,
            'data': {
                'join_code': status.join_key,
                'players': status.current_players,
                'max_players': status.max_players,
                'queue': queue,
                'staff': total_staff,
                'admins': admins,
                'mods': mods
            },
            'associated_messages': []
        })

    return return_val


async def interpret_embed(bot, ctx, channel, embed: dict, ics_id: int):
    embed = discord.Embed.from_dict(embed)
    try:
        embed.title = await sub_vars(bot, ctx, channel, embed.title)
    except AttributeError:
        pass
    try:
        embed.set_author(name=await sub_vars(bot, ctx, channel, embed.author.name))
    except AttributeError:
        pass
    try:
        embed.description = await sub_vars(bot, ctx, channel, embed.description)
    except AttributeError:
        pass
    try:
        embed.set_footer(
            text=await sub_vars(bot, ctx, channel, embed.footer.text),
            icon_url=embed.footer.icon_url,
        )
    except AttributeError:
        pass
    for i in embed.fields:
        i.name = await sub_vars(bot, ctx, channel, i.name)
        i.value = await sub_vars(bot, ctx, channel, i.value)

    if await bot.server_keys.db.count_documents({'_id': ctx.guild.id}) == 0:
        return embed # end here no point
    
    return await update_ics(bot, ctx, channel, embed, ics_id)

async def interpret_content(bot, ctx, channel, content: str, ics_id):
    await update_ics(bot, ctx, channel, content, ics_id)
    return await sub_vars(bot, ctx, channel, content)


async def sub_vars(bot, ctx: commands.Context, channel, string, **kwargs):
    try:
        string = string.replace("{user}", ctx.author.mention)
        string = string.replace("{username}", ctx.author.name)
        string = string.replace("{display_name}", ctx.author.display_name)
        string = string.replace("{time}", f"<t:{int(datetime.datetime.now().timestamp())}>")
        string = string.replace("{server}",  ctx.guild.name)
        string = string.replace("{channel}", channel.mention)
        string = string.replace("{prefix}", list(await get_prefix(bot, ctx))[-1])
        
        onduty: int = len([i async for i in bot.shift_management.shifts.db.find({
            "Guild": ctx.guild.id, "EndEpoch": 0
        })])

        string = string.replace("{onduty}", str(onduty))

        #### CUSTOM ERLC VARS
        # Fetch whether they should even be allowed to use ERLC vars
        if await bot.server_keys.db.count_documents({'_id': ctx.guild.id}) == 0:
            return string # end here no point
        
        status: ServerStatus = await bot.prc_api.get_server_status(ctx.guild.id)
        if not isinstance(status, ServerStatus):
            return string # Invalid key
        queue: int = await bot.prc_api.get_server_queue(ctx.guild.id, minimal=True)
        players: list[Player] = await bot.prc_api.get_server_players(ctx.guild.id)
        mods: int = len(list(filter(lambda x: x.permission == "Server Moderator", players)))
        admins: int = len(list(filter(lambda x: x.permission == "Server Administrator", players)))
        total_staff: int = len(list(filter(lambda x: x.permission != 'Normal', players)))
        
        string = string.replace("{join_code}", status.join_key)
        string = string.replace("{players}", str(status.current_players))
        string = string.replace("{max_players}", str(status.max_players))
        string = string.replace("{queue}", str(queue))
        string = string.replace("{staff}", str(total_staff))
        string = string.replace("{admins}", str(admins))
        string = string.replace("{mods}", str(mods))

        return string
    except:
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
        prefix = (prefix or {})["customisation"]["prefix"]
    except KeyError:
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
    except ValueError:
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
            # # # print(e)
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
                except discord.HTTPException:
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
    except asyncio.TimeoutError:
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

async def get_discord_by_roblox(bot,username):
    api_url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        data = response.json()["data"][0]
        id = data["id"]
        linked_account = await bot.oauth2_users.db.find_one({"roblox_id": id})
        if linked_account:
            return linked_account["discord_id"]
        else:
            return None
        
async def log_command_usage(bot, guild, member, command_name):
    settings = await bot.settings.find_by_id(guild.id)
    if not settings:
        return
    if not settings.get('staff_management', {}).get('erm_log_channel'):
        return
    try:
        log_channel_id = settings.get('staff_management', {}).get('erm_log_channel')
    except (ValueError, TypeError):
        return
    log_channel = guild.get_channel(log_channel_id)
    if log_channel is None:
        return
    if not log_channel.permissions_for(guild.me).send_messages:
        return
    embed = discord.Embed(
        title="ERM Command Log",
        description=f"Command `{command_name}` used by {member.mention}",
        color=BLANK_COLOR
    )
    embed.set_footer(text=f"User ID: {member.id}")
    embed.set_author(name=member.name, icon_url=member.display_avatar.url)
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    await log_channel.send(embed=embed)

async def config_change_log(bot,guild,member,data):
    setting = await bot.settings.find_by_id(guild.id)
    if not setting:
        return
    if not setting.get('staff_management', {}).get('erm_log_channel'):
        return
    try:
        log_channel_id = setting.get('staff_management', {}).get('erm_log_channel')
    except (ValueError,TypeError) as e:
        return
    log_channel = guild.get_channel(log_channel_id)
    if log_channel is None:
        return
    if not log_channel.permissions_for(guild.me).send_messages:
        return
    embed = discord.Embed(
        title="ERM Config Change Log",
        description=f"Configuration change made by {member.mention}",
        color=BLANK_COLOR
    ).add_field(name="Configuration Change",value=data)
    embed.set_footer(text=f"User ID: {member.id}")
    embed.set_author(name=member.name, icon_url=member.display_avatar.url)
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    await log_channel.send(embed=embed)
