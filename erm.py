import datetime
import json
import logging
import os
import pprint
import random
import subprocess
import time
from io import BytesIO
from reactionmenu import ViewButton, ViewMenu
import DiscordUtils
import discord
import dns.resolver
import motor.motor_asyncio
import pytz
import requests
import sentry_sdk
from decouple import config
from discord import app_commands
from discord.ext import commands, tasks
from roblox import client as roblox
from sentry_sdk import capture_exception, push_scope
from snowflake import SnowflakeGenerator
from zuid import ZUID
from utils.utils import *

from menus import CustomSelectMenu, SettingsSelectMenu, Setup, YesNoMenu, RemoveWarning, LOAMenu, ShiftModify, \
    AddReminder, RemoveReminder
from utils.mongo import Document
from utils.timestamp import td_format

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

sentry_url = config('SENTRY_URL')

sentry_sdk.init(
    sentry_url,
    traces_sample_rate=1.0
)

discord.utils.setup_logging()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True


class AutoShardedBot(commands.AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id in [459374864067723275, 713899230183424011]:  # Implement your own conditions here
            return True

        # Else fall back to the original
        return await super().is_owner(user)


bot = AutoShardedBot(command_prefix=get_prefix, case_insensitive=True, intents=intents, help_command=None)
bot.is_synced = False
environment = config('ENVIRONMENT', default='DEVELOPMENT')


@bot.before_invoke
async def DeferInteraction(ctx):
    if isinstance(ctx.interaction, discord.Interaction):
        await ctx.interaction.defer()


@bot.event
async def on_ready():

    # load IPC extension
    try:
        # await bot.load_extension('utils.routes')
        logging.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{} is online!'.format(bot.user.name))
        global startTime
        startTime = time.time()
        bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(mongo_url))
        if environment == 'DEVELOPMENT':
            bot.db = bot.mongo['beta']
        elif environment == "PRODUCTION":
            bot.db = bot.mongo["erm"]
        else:
            raise Exception("Invalid environment")

        bot.start_time = time.time()
        bot.warnings = Document(bot.db, "warnings")
        bot.settings = Document(bot.db, "settings")
        bot.shifts = Document(bot.db, "shifts")
        bot.errors = Document(bot.db, "errors")
        bot.shift_storage = Document(bot.db, "shift_storage")
        bot.loas = Document(bot.db, "leave_of_absences")
        bot.reminders = Document(bot.db, "reminders")
        bot.privacy = Document(bot.db, "privacy")
        bot.flags = Document(bot.db, "flags")


        bot.error_list = []
        logging.info('Connected to MongoDB!')

        await bot.load_extension('jishaku')
        await bot.load_extension('utils.server')

        if not bot.is_synced:  # check if slash commands have been synced
            bot.tree.copy_global_to(guild=discord.Object(id=987798554972143728))
            for item in bot.tree._get_all_commands():
                logging.info(item.name)
        if environment == 'DEVELOPMENT':
            await bot.tree.sync(guild=discord.Object(id=987798554972143728))
        else:
            await bot.tree.sync()  # guild specific: leave blank if global (global registration can take 1-24 hours)
        bot.is_synced = True


        # change_status.start()
        # update_bot_status.start()
        # GDPR.start()
        # check_loa.start()
        # check_reminders.start()
    except commands.errors.ExtensionAlreadyLoaded:
        logging.info('Already loaded extensions + bot. (Sharded)')


client = roblox.Client()


def is_staff():
    async def predicate(ctx):
        guild_settings = await bot.settings.find_by_id(ctx.guild.id)
        if guild_settings:
            if 'role' in guild_settings['staff_management'].keys():
                if guild_settings['staff_management']['role'] != "":
                    if isinstance(guild_settings['staff_management']['role'], list):
                        for role in guild_settings['staff_management']['role']:
                            if role in [role.id for role in ctx.author.roles]:
                                return True
                    elif isinstance(guild_settings['staff_management']['role'], int):
                        if guild_settings['staff_management']['role'] in [role.id for role in ctx.author.roles]:
                            return True
        if ctx.author.guild_permissions.manage_messages:
            return True
        return False

    return commands.check(predicate)


def is_management():
    async def predicate(ctx):
        guild_settings = await bot.settings.find_by_id(ctx.guild.id)
        if guild_settings:
            if 'management_role' in guild_settings['staff_management'].keys():
                if guild_settings['staff_management']['management_role'] != "":
                    if guild_settings['staff_management']['management_role'] in [role.id for role in ctx.author.roles]:
                        return True
        if ctx.author.guild_permissions.manage_guild:
            return True
        return False

    return commands.check(predicate)


async def check_privacy(guild: int, setting: str):
    privacySettings = await bot.privacy.find_by_id(guild)
    if not privacySettings:
        return True
    if not setting in privacySettings.keys():
        return True
    return privacySettings[setting]


async def warning_json_to_mongo(jsonName: str, guildId: int):
    f = None
    with open(f'{jsonName}', 'r') as f:
        logging.info(f)
        f = json.load(f)

    logging.info(f)

    for key, value in f.items():
        structure = {
            '_id': key.lower(),
            'warnings': []
        }
        logging.info([key, value])
        logging.info(key.lower())

        if await bot.warnings.find_by_id(key.lower()):
            data = await bot.warnings.find_by_id(key.lower())
            for item in data['warnings']:
                structure['warnings'].append(item)

        for item in value:
            item.pop('ID', None)
            item['id'] = next(generator)
            item['Guild'] = guildId
            structure['warnings'].append(item)

        logging.info(structure)

        if await bot.warnings.find_by_id(key.lower()) == None:
            await bot.warnings.insert(structure)
        else:
            await bot.warnings.update(structure)


async def crp_data_to_mongo(jsonName: str, guildId: int):
    f = None
    with open(f'{jsonName}.json', 'r') as f:
        logging.info(f)
        f = json.load(f)

    logging.info(f)
    users = {}

    for value in f["moderations"]:
        # get user
        if value['userId'] not in users.keys():
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post('https://users.roblox.com/v1/users', data={
                    "userIds":
                        [
                            value["userId"]
                        ]
                }) as r:
                    requestJSON = await r.json()
                    name = requestJSON['data'][0]["name"].lower()
        else:
            name = users[value["userId"]]
        users[value["userId"]] = name
        userItem = None
        user = discord.utils.get(bot.users, id=int(value['staffId']))
        if user is not None:
            userItem = [user.name, user.id]
        else:
            userItem = ["-", int(value['staffId'])]

        timeObject = datetime.datetime.fromtimestamp(int(value['time']) / 1000)
        types = {
            "other": "Warning",
            "warn": "Warning",
            "kick": "Kick",
            "ban": "Ban"
        }

        default_warning_item = {
            'id': next(generator),
            "Type": types[value['type']],
            "Reason": value['reason'],
            "Moderator": userItem,
            "Time": timeObject.strftime('%m/%d/%Y, %H:%M:%S'),
            "Guild": guildId
        }

        pprint.pprint(default_warning_item)

        parent_structure = {
            "_id": name,
            "warnings": []
        }

        if await bot.warnings.find_by_id(name):
            data = await bot.warnings.find_by_id(name)
            data["warnings"].append(default_warning_item)
            await bot.warnings.update_by_id(data)
        else:
            data = parent_structure
            data['warnings'].append(default_warning_item)
            await bot.warnings.insert(data)

    os.remove(f"{jsonName}.json")


bot.staff_members = {
    "i_imikey": "Bot Developer",
    "kiper4k": "Support Team",
    "mbrinkley": "Lead Support",
    "ruru0303": "Support Team",
    "myles_cbcb1421": "Support Team",
    "theoneandonly_5567": "Manager",
    "l0st_nations": "Junior Support",
    "royalcrests": "Developer",
    "quiverze": "Junior Support"
}


async def staff_field(embed, query):
    embed.add_field(name="<:FlagIcon:1035258525955395664> Flags",
                    value="<:ArrowRight:1035003246445596774> ERM Staff",
                    inline=False)
    return embed


bot.warning_json_to_mongo = warning_json_to_mongo

bot.colors = {
    "WHITE": 0xFFFFFF,
    "AQUA": 0x1ABC9C,
    "GREEN": 0x2ECC71,
    "BLUE": 0x3498DB,
    "PURPLE": 0x9B59B6,
    "LUMINOUS_VIVID_PINK": 0xE91E63,
    "GOLD": 0xF1C40F,
    "ORANGE": 0xE67E22,
    "RED": 0xE74C3C,
    "NAVY": 0x34495E,
    "DARK_AQUA": 0x11806A,
    "DARK_GREEN": 0x1F8B4C,
    "DARK_BLUE": 0x206694,
    "DARK_PURPLE": 0x71368A,
    "DARK_VIVID_PINK": 0xAD1457,
    "DARK_GOLD": 0xC27C0E,
    "DARK_ORANGE": 0xA84300,
    "DARK_RED": 0x992D22,
    "DARK_NAVY": 0x2C3E50,
}
bot.color_list = [c for c in bot.colors.values()]


async def generate_random(ctx) -> int:
    if await bot.settings.find_by_id(ctx.guild.id):
        settings = await bot.settings.find_by_id(ctx.guild.id)
        if settings['customisation']['color'] != "":
            return settings['customisation']['color']

    return 0x2E3136


bot.generate_random = generate_random

# include environment variables
if environment == "PRODUCTION":
    bot_token = config('PRODUCTION_BOT_TOKEN')
    logging.info('Using production token...')
elif environment == "DEVELOPMENT":
    bot_token = config('DEVELOPMENT_BOT_TOKEN')
    logging.info('Using development token...')
else:
    raise Exception("Invalid environment")
mongo_url = config('MONGO_URL')
github_token = config('GITHUB_TOKEN')
generator = SnowflakeGenerator(192)
error_gen = ZUID(prefix="error_", length=10)


@bot.hybrid_group(
    name="punishments",
    description="Punishment commands [Punishments]"
)
async def punishments(ctx):
    pass


# @bot.hybrid_command(
#     name="debug"
# )
# @commands.is_owner()
# async def debug(ctx):
#     if isinstance(ctx, discord.Interaction):
#         return await ctx.send('Interaction')
#     else:
#         return await ctx.send('Context')

# status change discord.ext.tasks
@tasks.loop(hours=1)
async def change_status():
    mcl = [guild.member_count for guild in bot.guilds]
    member_count = sum(mcl)

    status = [
        "[N] Version [R]"
    ]

    chosen = random.choice(status)
    requestResponse = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    chosen = chosen.replace('[R]', requestResponse)
    chosen = chosen[4:]
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=chosen))


# status change discord.ext.tasks
@tasks.loop(seconds=30)
async def update_bot_status():
    try:
        # get channel from bot
        channel = bot.get_channel(988082136542236733)
        # get last message from channel
        last_message = None
        async for message in channel.history(limit=1):
            last_message = message
        # get last message content
        if last_message == None:
            embed = discord.Embed(
                title='Bot Status',
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=bot.user.display_avatar.url)
            embed.add_field(name='Last ping', value=f'<t:{int(datetime.datetime.now().timestamp())}:R>')
            embed.add_field(name='Status', value='<:online:989218581764014161> Online')
            embed.add_field(name='Pings', value='1')
            embed.add_field(name='Note',
                            value=f'This is updated every 30 seconds. If you see the last ping was over 30 seconds ago, contact {discord.utils.get(channel.guild.members, id=635119023918415874).mention}',
                            inline=False)

            await channel.send(embed=embed)
        else:
            last_embed = last_message.embeds[0]
            pings = None

            for field in last_embed.fields:
                if field.name == 'Pings':
                    pings = int(field.value)

            embed = discord.Embed(
                title='Bot Status',
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=bot.user.display_avatar.url)
            embed.add_field(name='Last ping', value=f'<t:{int(datetime.datetime.now().timestamp())}:R>')
            embed.add_field(name='Status', value='<:online:989218581764014161> Online')
            embed.add_field(name='Pings', value=str(pings + 1))
            embed.add_field(name='Note',
                            value=f'This is updated every 30 seconds. If you see the last ping was over 30 seconds ago, contact {discord.utils.get(channel.guild.members, id=635119023918415874).mention}',
                            inline=False)

            await last_message.edit(embed=embed)
    except:
        logging.info('Failing updating the status.')


@tasks.loop(hours=24)
async def GDPR():
    try:
        if bot.reminders is not None:
            pass
    except:
        return
    # if the date in each warning is more than 30 days ago, redact the staff's username and tag
    # using mongodb (warnings)
    # get all warnings
    warnings = await bot.warnings.get_all()
    # iterate through each warning, to check the date via the time variable stored in "d/m/y h:m:s"
    for userentry in warnings:
        for warning in userentry['warnings']:
            try:
                date = datetime.datetime.strptime(warning['Time'], '%m/%d/%Y, %H:%M:%S')
                now = datetime.datetime.now()
                diff = now - date
                diff_days = diff.days
                if diff_days > 30:
                    # get the staff's id
                    if type(warning['Moderator']) == list:
                        warning['Moderator'][0] = "[redacted ~ GDPR]"
                    else:
                        warning['Moderator'] = "[redacted ~ GDPR]"

                        await bot.warnings.update_by_id(userentry)
            except:
                pass


@tasks.loop(minutes=1)
async def check_reminders():
    for guildObj in await bot.reminders.get_all():
        for item in guildObj['reminders']:
            try:
                dT = datetime.datetime.now()
                interval = item['interval']
                full = None
                num = None

                tD = dT + datetime.timedelta(seconds=interval)

                if tD.timestamp() - item['lastTriggered'] >= interval:
                    guild = bot.get_guild(int(guildObj['_id']))
                    channel = guild.get_channel(int(item['channel']))
                    roles = []
                    try:
                        for role in item['role']:
                            roles.append(guild.get_role(int(role)).mention)
                    except:
                        roles = [""]

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Notification",
                        description=f"{item['message']}",
                        color=0x2E3136
                    )
                    lastTriggered = tD.timestamp()
                    item['lastTriggered'] = lastTriggered
                    await bot.reminders.update_by_id(guildObj)
                    await channel.send(" ".join(roles), embed=embed)
            except:
                pass


@tasks.loop(minutes=1)
async def check_loa():
    try:
        if bot.reminders is not None:
            pass
    except:
        return
    loas = bot.loas

    for loaObject in await loas.get_all():
        if datetime.datetime.now(tz=None).timestamp() > loaObject['expiry'] and loaObject["expired"] == False:
            loaObject['expired'] = True
            print(loaObject)
            await bot.loas.update_by_id(loaObject)
            guild = bot.get_guild(loaObject['guild_id'])
            if guild:
                embed = discord.Embed(
                    title=f'<:Clock:1035308064305332224> {loaObject["type"]} Expired',
                    description=f"<:ArrowRight:1035003246445596774> Your {loaObject['type']} in {guild.name} has expired.",
                    color=0x2E3136
                )
                member = guild.get_member(loaObject['user_id'])
                settings = await bot.settings.find_by_id(guild.id)
                roles = [None]
                if settings is not None:
                    if "loa_role" in settings['staff_management']:
                        try:
                            if isinstance(settings['staff_management']['loa_role'], int):
                                roles = [discord.utils.get(guild.roles, id=settings['staff_management']['loa_role'])]
                            elif isinstance(settings['staff_management']['loa_role'], list):
                                roles = [discord.utils.get(guild.roles, id=role) for role in
                                         settings['staff_management']['loa_role']]
                        except:
                            pass
                if roles is not [None]:
                    for role in roles:
                        if role in member.roles:
                            await member.remove_roles(role)
                await member.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    error_id = error_gen()
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(title="<:ErrorIcon:1035000018165321808> Permissions Error", color=0xff3c3c,
                              description="You do not have permission to use this command.")
        return await ctx.send(embed=embed)
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title="<:ErrorIcon:1035000018165321808> Error", color=0xff3c3c,
                              description="You are missing a required argument to run this command.")
        embed.add_field(name="Error ID", value=f"`{error_id}`", inline=False)
        return await ctx.send(embed=embed)
    try:
        embed = discord.Embed(
            title='<:ErrorIcon:1035000018165321808> Bot Error',
            color=discord.Color.red()
        )

        try:
            error_bef = str(error).split(':')[0]
            error_beftwo = str(error).split(':')[1:]
            error_after = error_bef + ":\n" + ':'.join(error_beftwo)
        except:
            error_after = str(error)

        embed.add_field(name="Error Details", value=error_after, inline=False)
        embed.add_field(name="Support Server", value="[Click here](https://discord.gg/5pMmJEYazQ)", inline=False)
        embed.add_field(name='Error ID', value=f"`{error_id}`", inline=False)

        if not isinstance(error, (commands.CommandNotFound, commands.CheckFailure, commands.MissingRequiredArgument)):
            await ctx.send(embed=embed)
    except Exception as e:
        logging.info(e)
    finally:
        with push_scope() as scope:
            scope.set_tag('error_id', error_id)
            scope.level = 'error'
            await bot.errors.insert({
                "_id": error_id,
                "error": str(error),
                "time": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                "channel": ctx.channel.id,
                "guild": ctx.guild.id
            })
            capture_exception(error)


@bot.hybrid_command(
    name="import",
    description="Import CRP Moderation data [Miscellaneous]"
)
@is_management()
async def _import(ctx):
    try:
        attachments = await request_response(bot, ctx,
                                             "Please send your CRP export file.\n*Note: You can find this by doing `/export` with the CRP bot.*")
        attachments = attachments.attachments
    except:
        return await invis_embed(ctx, 'Cancelled.')

    if attachments:
        await attachments[0].save(f'cache/{ctx.guild.id}.json')
        await crp_data_to_mongo(f"cache/{ctx.guild.id}", ctx.guild.id)
        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Data Merged",
            description=f"<:ArrowRightW:1035023450592514048>**{ctx.guild.name}**'s data has been merged.",
            color=0x71c15f
        )
        await ctx.send(embed=success)
    else:
        return await invis_embed(ctx, 'Cancelled.')


@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(f'{bot.user.name} has been added to a new server!')
    logging.info('List of servers the bot is in: ')

    for guild in bot.guilds:
        logging.info(f'  - {guild.name}')

    try:
        await guild.system_channel.send(
            'Hello! I am the Emergency Response Management bot!\n\nFor me to work properly, you need to set me using `/setup`. If you need help, contact me on Discord at Mikey#0008 or at the support server below. Other than that, have a good day! :wave:\n\nhttps://discord.gg/BGfyfqU5fx'
        )
    except:
        await guild.owner.send(
            'Hello! I am the Emergency Response Management bot!\n\nFor me to work properly, you need to set me using `/setup`. If you need help, contact me on Discord at Mikey#0008. Other than that, have a good day! :wave:\n\nhttps://discord.gg/BGfyfqU5fx'
        )
    finally:
        channel = bot.get_channel(1033021466381398086)
        embed = discord.Embed(color=0x2E3136)
        embed.description = f"""
        <:ArrowRightW:1035023450592514048> **Server Name:** {guild.name}
        <:ArrowRightW:1035023450592514048> **Guild ID:** {guild.id}
        <:ArrowRightW:1035023450592514048> **Bots:** {len([member for member in guild.members if member.bot == True])}
        <:ArrowRightW:1035023450592514048> **Member Count:** {guild.member_count}
        <:ArrowRightW:1035023450592514048> **Guild Count:** {len(bot.guilds)}        
        """
        embed.set_footer(icon_url=guild.icon.url, text=guild.name)
        await channel.send(embed=embed)
        logging.info('Server has been sent welcome sequence.')


# @bot.event
# async def on_message(message: discord.Message):
#     bypass_role = None
#
#     if not hasattr(bot, 'settings'):
#         return
#
#     if message.author == bot.user:
#         return
#
#     if message.author.bot:
#         return
#
#     if not message.guild:
#         await bot.process_commands(message)
#         return
#
#     dataset = await bot.settings.find_by_id(message.guild.id)
#     if dataset == None:
#         await bot.process_commands(message)
#         return
#
#     antiping_roles = None
#     bypass_roles = None
#
#     if "bypass_role" in dataset['antiping'].keys():
#         bypass_role = dataset['antiping']['bypass_role']
#
#     if dataset['antiping']['enabled'] is False or dataset['antiping']['role'] is None:
#         await bot.process_commands(message)
#         return
#
#     if isinstance(bypass_role, list):
#         bypass_roles = [discord.utils.get(message.guild.roles, id=role) for role in bypass_role]
#     else:
#         bypass_roles = [discord.utils.get(message.guild.roles, id=bypass_role)]
#
#     if isinstance(dataset['antiping']['role'], list):
#         antiping_roles = [discord.utils.get(message.guild.roles, id=role) for role in bypass_role]
#     else:
#         antiping_roles = [discord.utils.get(message.guild.roles, id=dataset['antiping']['role'])]
#
#     if antiping_roles is None:
#         await bot.process_commands(message)
#         return
#
#     if bypass_roles is not None:
#         for role in bypass_roles:
#             if bypass_role in message.author.roles:
#                 await bot.process_commands(message)
#                 return
#
#     for mention in message.mentions:
#         isStaffPermitted = False
#         logging.info(isStaffPermitted)
#
#         if mention.bot:
#             await bot.process_commands(message)
#             return
#
#         if mention == message.author:
#             await bot.process_commands(message)
#             return
#
#         for role in antiping_roles:
#             if message.author.top_role.position > role.position or message.author.top_role.position == role.position:
#                 await bot.process_commands(message)
#                 return
#
#         if message.author == message.guild.owner:
#             await bot.process_commands(message)
#             return
#
#         if not isStaffPermitted:
#             for role in antiping_roles:
#                 if mention.top_role.position > role.position:
#                     Embed = discord.Embed(
#                         title=f'Do not ping {role.name} or above!',
#                         color=discord.Color.red(),
#                         description=f'Do not ping {role.name} or above!\nIt is a violation of the rules, and you will be punished if you continue.'
#                     )
#                     try:
#                         msg = await message.channel.fetch_message(message.reference.message_id)
#                         if msg.author == mention:
#                             Embed.set_image(url="https://i.imgur.com/pXesTnm.gif")
#                     except:
#                         pass
#
#                     Embed.set_footer(text=f'Thanks, {dataset["customisation"]["brand_name"]}',
#                                      icon_url=get_guild_icon(bot, message.guild))
#
#                     ctx = await bot.get_context(message)
#                     await ctx.reply(f'{message.author.mention}', embed=Embed)
#                     return
#                 await bot.process_commands(message)
#                 return
#     await bot.process_commands(message)


@bot.hybrid_command(
    name='setup',
    description='Sets up the bot for use.',
    brief='Sets up the bot for use. [Configuration]',
    aliases=['setupbot'],
    with_app_command=True,
)
@is_management()
async def setup(ctx):
    settingContents = {
        '_id': 0,
        'verification': {
            'enabled': False,
            'role': None,
        },
        'antiping': {
            'enabled': False,
            'role': None,
            "bypass_role": "None"
        },

        'staff_management': {
            'enabled': False,
            'channel': None
        },
        'punishments': {
            'enabled': False,
            'channel': None
        },
        'shift_management': {
            'enabled': False,
            'channel': None,
            'role': None
        },
        'customisation': {
            'color': '',
            'prefix': '>',
            'brand_name': 'Emergency Response Management',
            'thumbnail_url': '',
            'footer_text': 'Staff Logging Systems',
            'ban_channel': None
        }
    }

    welcome = discord.Embed(title="<:Setup:1035006520817090640> Which features would you like enabled?", color=0xffffff)
    welcome.description = "Toggle which modules of ERM you would like to use.\n\n<:ArrowRight:1035003246445596774> All *(default)*\n*All features of the bot*\n\n<:ArrowRight:1035003246445596774> Staff Management\n*Manage your staff members, LoAs, and more!*\n\n<:ArrowRight:1035003246445596774> Punishments\n*Roblox moderation, staff logging systems, and more!*\n\n<:ArrowRight:1035003246445596774> Shift Management\n*Manage staff member's shifts, view who's in game!*"

    view = Setup(ctx.author.id)
    await ctx.send(embed=welcome, view=view)

    await view.wait()
    if view.value == 'all' or view.value == 'default':
        settingContents['staff_management']['enabled'] = True
        settingContents['punishments']['enabled'] = True
        settingContents['shift_management']['enabled'] = True
    elif view.value == 'punishments':
        settingContents['punishments']['enabled'] = True
    elif view.value == 'shift management':
        settingContents['shift_management']['enabled'] = True
    elif view.value == 'staff management':
        settingContents['staff_management']['enabled'] = True
    else:
        return await invis_embed(ctx, ':gear: You have took too long to respond. Please try again.')

    if settingContents['staff_management']['enabled']:
        question = 'What channel do you want to use for staff management?'
        content = (await request_response(bot, ctx, question)).content
        convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
        settingContents['staff_management']['channel'] = convertedContent.id

        question = 'What role would you like to use for your staff role? (e.g. @Staff)\n*You can separate multiple roles by using a comma.*'
        content = (await request_response(bot, ctx, question)).content
        if ',' in content:
            convertedContent = []
            for role in content.split(','):
                role = role.strip()
                convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
        else:
            convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
        settingContents['staff_management']['role'] = [role.id for role in convertedContent]

        question = 'What role would you like to use for your Management role? (e.g. @Management)\n*You can separate multiple roles by using a comma.*'
        content = (await request_response(bot, ctx, question)).content
        if ',' in content:
            convertedContent = []
            for role in content.split(','):
                role = role.strip()
                convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
        else:
            convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
        settingContents['staff_management']['management_role'] = [role.id for role in convertedContent]

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be assigned to staff members when they are on LoA (Leave of Absence)?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                content = (await request_response(bot, ctx,
                                                  'What role(s) would you like to be given?\n*You can separate multiple roles by using a comma.*')).content

                if ',' in content:
                    convertedContent = []
                    for role in content.split(','):
                        role = role.strip()
                        convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
                else:
                    convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]

                settingContents['staff_management']['loa_role'] = [role.id for role in convertedContent]

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be assigned to staff members when they are on RA (Reduced Activity)?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                content = (await request_response(bot, ctx,
                                                  'What role(s) would you like to be given?\n*You can separate multiple roles by using a comma.*')).content

                if ',' in content:
                    convertedContent = []
                    for role in content.split(','):
                        role = role.strip()
                        convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
                else:
                    convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]

                settingContents['staff_management']['ra_role'] = [role.id for role in convertedContent]
    if settingContents['punishments']['enabled']:
        content = (await request_response(bot, ctx, 'What channel do you want to use for punishments?')).content
        convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
        settingContents['punishments']['channel'] = convertedContent.id
    if settingContents['shift_management']['enabled']:
        content = (await request_response(bot, ctx,
                                          'What channel do you want to use for shift management? (e.g. shift signups, etc.)')).content
        convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
        settingContents['shift_management']['channel'] = convertedContent.id

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be assigned to staff members when they are in game?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                content = (await request_response(bot, ctx,
                                                  'What role(s) would you like to be given?\n*You can separate multiple roles by using a comma.*')).content

                if ',' in content:
                    convertedContent = []
                    for role in content.split(','):
                        role = role.strip()
                        convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
                else:
                    convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]

                settingContents['shift_management']['role'] = [role.id for role in convertedContent]

    privacyDefault = {
        "_id": ctx.guild.id,
        "global_warnings": True
    }

    view = YesNoMenu(ctx.author.id)
    question = 'Do you want your server\'s warnings to be able to be queried across the bot? (e.g. `globalsearch`)'
    embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")
    await ctx.send(embed=embed, view=view)
    await view.wait()
    if view.value is not None:
        if view.value == True:
            privacyDefault['global_warnings'] = True
        else:
            privacyDefault['global_warnings'] = False

    if not await bot.privacy.find_by_id(ctx.guild.id):
        await bot.privacy.insert(privacyDefault)
    else:
        await bot.privacy.update_by_id(privacyDefault)

    settingContents['_id'] = ctx.guild.id
    if not await bot.settings.find_by_id(ctx.guild.id):
        await bot.settings.insert(settingContents)
    else:
        await bot.settings.update_by_id(settingContents)

    embed = discord.Embed(title="<:CheckIcon:1035018951043842088> Setup Complete", color=0x69cc5e,
                          description="<:ArrowRight:1035003246445596774>ERM has been set up and is ready for use!\n*If you want to change these settings, run the command again!*")
    await ctx.send(embed=embed)


@bot.hybrid_command(
    name='quicksetup',
    description='Sets up the bot for use. Not recommended for non-experienced users. [Configuration]',
    aliases=['qsetup'],
    with_app_command=True,
)
@is_management()
async def quicksetup(ctx, featuresenabled='default', staffmanagementchannel: discord.TextChannel = None,
                     punishmentschannel: discord.TextChannel = None,
                     shiftmanagementchannel: discord.TextChannel = None):
    settingContents = {
        '_id': 0,
        'verification': {
            'enabled': False,
            'role': None,
        },
        'antiping': {
            'enabled': False,
            'role': None,
            "bypass_role": "None"
        },

        'staff_management': {
            'enabled': False,
            'channel': None
        },
        'punishments': {
            'enabled': False,
            'channel': None
        },
        'shift_management': {
            'enabled': False,
            'channel': None,
            'role': None
        },
        'customisation': {
            'color': '',
            'prefix': '>',
            'brand_name': 'Emergency Response Management',
            'thumbnail_url': '',
            'footer_text': 'Staff Logging Systems',
            'ban_channel': None,
            "server_code": None
        }
    }

    view = YesNoMenu(ctx.author.id)
    embed = discord.Embed(
        title="Quick Setup",
        description='<:ArrowRight:1035003246445596774> Running this command will override any already configured settings with ERM.\nAre you sure you would like to run this command?',
        color=0x2E3136
    )
    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value != True:
        success = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774> Quick setup has been cancelled.",
            color=0xff3c3c
        )
        return await ctx.send(embed=success)

    if featuresenabled == 'all' or featuresenabled == 'default':
        settingContents['staff_management']['enabled'] = True
        settingContents['punishments']['enabled'] = True
        settingContents['shift_management']['enabled'] = True
    elif featuresenabled == 'punishments':
        settingContents['punishments']['enabled'] = True
    elif featuresenabled == 'shift_management':
        settingContents['shift_management']['enabled'] = True
    elif featuresenabled == 'staff_management':
        settingContents['staff_management']['enabled'] = True
    else:
        await invis_embed(ctx,
                          'Invalid argument 0. Please pick one of the options. `staff_management`, `punishments`, `shift_management`, `default`, `all`.')

    if settingContents['staff_management']['enabled']:
        if staffmanagementchannel != None:
            settingContents['staff_management']['channel'] = staffmanagementchannel.id
            await invis_embed(ctx, 'Successfully set the staff management channel to `{}`.'.format(
                staffmanagementchannel.name))

    if settingContents['punishments']['enabled']:
        if punishmentschannel != None:
            settingContents['punishments']['channel'] = punishmentschannel.id
            await invis_embed(ctx, 'Successfully set the punishments channel to `{}`.'.format(punishmentschannel.name))
    if settingContents['shift_management']['enabled']:
        if shiftmanagementchannel != None:
            settingContents['shift_management']['channel'] = shiftmanagementchannel.id
            await invis_embed(ctx, 'Successfully set the shift management channel to `{}`.'.format(
                shiftmanagementchannel.name))

    settingContents['_id'] = ctx.guild.id
    if not await bot.settings.find_by_id(ctx.guild.id):
        await bot.settings.insert(settingContents)
    else:
        await bot.settings.update_by_id(settingContents)

    await invis_embed(ctx,
                      'Quicksetup is now completed. You can now use it as usual. If you ever want to change any of these settings, feel free to run the `/config` command.')


@bot.hybrid_group(
    name='config'
)
@is_management()
async def config(ctx):
    await ctx.invoke(bot.get_command('config view'))


@config.command(
    name='view',
    description='View the current configuration of the server.'
)
@is_management()
async def viewconfig(ctx):
    if not await bot.settings.find_by_id(ctx.guild.id):
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    settingContents = await bot.settings.find_by_id(ctx.guild.id)
    privacyConfig = await bot.privacy.find_by_id(ctx.guild.id)
    antiping_role = None
    bypass_role = None

    try:
        verification_role = ctx.guild.get_role(settingContents['staff_management']['verification_role']).mention
    except:
        verification_role = 'None'
    try:
        if isinstance(settingContents['shift_management']['role'], int):
            shift_role = ctx.guild.get_role(settingContents['shift_management']['role']).mention
        elif isinstance(settingContents['shift_management']['role'], list):
            shift_role = ''
            for role in settingContents['shift_management']['role']:
                shift_role += ctx.guild.get_role(role).mention + ', '
            shift_role = shift_role[:-2]
    except:
        shift_role = 'None'
    try:
        if isinstance(settingContents['antiping']['role'], int):
            antiping_role = ctx.guild.get_role(settingContents['antiping']['role']).mention
        elif isinstance(settingContents['antiping']['role'], list):
            antiping_role = ''
            for role in settingContents['antiping']['role']:
                antiping_role += ctx.guild.get_role(role).mention + ', '
            antiping_role = shift_role[:-2]
    except:
        antiping_role = 'None'

    try:
        if isinstance(settingContents['antiping']['bypass_role'], int):
            bypass_role = ctx.guild.get_role(settingContents['antiping']['bypass_role']).mention
        elif isinstance(settingContents['antiping']['bypass_role'], list):
            bypass_role = ''
            for role in settingContents['antiping']['bypass_role']:
                bypass_role += ctx.guild.get_role(role).mention + ', '
            bypass_role = shift_role[:-2]
    except:
        bypass_role = 'None'

    # staff management channel
    try:
        staff_management_channel = ctx.guild.get_channel(settingContents['staff_management']['channel']).mention
    except:
        staff_management_channel = 'None'

    try:
        if isinstance(settingContents['staff_management']['role'], int):
            staff_role = ctx.guild.get_role(settingContents['staff_management']['role']).mention
        elif isinstance(settingContents['staff_management']['role'], list):
            staff_role = ''
            for role in settingContents['staff_management']['role']:
                staff_role += ctx.guild.get_role(role).mention + ', '
            staff_role = staff_role[:-2]
    except:
        staff_role = 'None'

    try:
        if isinstance(settingContents['staff_management']['management_role'], int):
            management_role = ctx.guild.get_role(settingContents['staff_management']['management_role']).mention
        elif isinstance(settingContents['staff_management']['management_role'], list):
            management_role = ''
            for role in settingContents['staff_management']['management_role']:
                management_role += ctx.guild.get_role(role).mention + ', '
            management_role = management_role[:-2]
    except:
        management_role = 'None'

    # punishments channel
    try:
        punishments_channel = ctx.guild.get_channel(settingContents['punishments']['channel']).mention
    except:
        punishments_channel = 'None'

    # shift management channel
    try:
        shift_management_channel = ctx.guild.get_channel(settingContents['shift_management']['channel']).mention
    except:
        shift_management_channel = 'None'

    try:
        ban_channel = ctx.guild.get_channel(settingContents['customisation']['ban_channel']).mention
    except:
        ban_channel = 'None'

    try:
        kick_channel = ctx.guild.get_channel(settingContents['customisation']['kick_channel']).mention
    except:
        kick_channel = 'None'

    try:
        bolo_channel = ctx.guild.get_channel(settingContents['customisation']['bolo_channel']).mention
    except:
        bolo_channel = 'None'

    try:
        if isinstance(settingContents['staff_management']['loa_role'], int):
            loa_role = ctx.guild.get_role(settingContents['staff_management']['loa_role']).mention
        elif isinstance(settingContents['staff_management']['loa_role'], list):
            loa_role = ''
            for role in settingContents['staff_management']['loa_role']:
                loa_role += ctx.guild.get_role(role).mention + ', '
            loa_role = loa_role[:-2]
    except:
        loa_role = 'None'

    try:
        if isinstance(settingContents['staff_management']['ra_role'], int):
            ra_role = ctx.guild.get_role(settingContents['staff_management']['ra_role']).mention
        elif isinstance(settingContents['staff_management']['ra_role'], list):
            ra_role = ''
            for role in settingContents['staff_management']['ra_role']:
                ra_role += ctx.guild.get_role(role).mention + ', '
            ra_role = ra_role[:-2]
    except:
        ra_role = 'None'

    embed = discord.Embed(
        title='<:support:1035269007655321680> Server Configuration',
        description=f'<:ArrowRight:1035003246445596774> Here are the current settings for **{ctx.guild.name}**:',
        color=await generate_random(ctx)
    )
    embed.add_field(
        name='<:SettingIcon:1035353776460152892>Verification',
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}'
        .format(
            settingContents['verification']['enabled'],
            verification_role
        ),
        inline=False
    )

    embed.add_field(
        name='<:MessageIcon:1035321236793860116> Anti-ping',
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}\n<:ArrowRightW:1035023450592514048>**Bypass Role:** {}'
        .format(
            settingContents['antiping']['enabled'],
            antiping_role,
            bypass_role
        ),
        inline=False
    )

    embed.add_field(
        name='<:staff:1035308057007230976> Staff Management',
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Staff Role:** {}\n<:ArrowRightW:1035023450592514048>**Management Role:** {}\n<:ArrowRightW:1035023450592514048>**LOA Role:** {}\n<:ArrowRightW:1035023450592514048>**RA Role:** {}'
        .format(
            settingContents['staff_management']['enabled'],
            staff_management_channel,
            staff_role,
            management_role,
            loa_role,
            ra_role
        ),
        inline=False
    )
    embed.add_field(
        name='<:MalletWhite:1035258530422341672> Punishments',
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}'
        .format(
            settingContents['punishments']['enabled'],
            punishments_channel
        ),
        inline=False
    )
    embed.add_field(
        name='<:Search:1035353785184288788> Shift Management',
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}'
        .format(
            settingContents['shift_management']['enabled'],
            shift_management_channel,
            shift_role
        ),
        inline=False
    )
    embed.add_field(
        name='<:FlagIcon:1035258525955395664> Customisation',
        value='<:ArrowRightW:1035023450592514048>**Color:** {}\n<:ArrowRightW:1035023450592514048>**Prefix:** `{}`\n<:ArrowRightW:1035023450592514048>**Brand Name:** {}\n<:ArrowRightW:1035023450592514048>**Thumbnail URL:** {}\n<:ArrowRightW:1035023450592514048>**Footer Text:** {}\n<:ArrowRightW:1035023450592514048>**Ban Channel:** {}\n<:ArrowRightW:1035023450592514048>**Kick Channel:** {}\n<:ArrowRightW:1035023450592514048>**BOLO Channel:** {}'
        .format(
            settingContents['customisation']['color'],
            settingContents['customisation']['prefix'],
            settingContents['customisation']['brand_name'],
            settingContents['customisation']['thumbnail_url'],
            settingContents['customisation']['footer_text'],
            ban_channel,
            kick_channel,
            bolo_channel
        ),
        inline=False
    )

    embed.add_field(
        name='<:staff:1035308057007230976> Privacy',
        value='<:ArrowRightW:1035023450592514048>**Global Warnings:** {}'
        .format(
            await check_privacy(ctx.guild.id, "global_warnings")
        ),
        inline=False
    )

    for field in embed.fields:
        field.inline = False

    await ctx.send(embed=embed)


@config.command(
    name='change',
    description='Change the configuration of the server.'
)
@is_management()
async def changeconfig(ctx):
    if not await bot.settings.find_by_id(ctx.guild.id):
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    settingContents = await bot.settings.find_by_id(ctx.guild.id)

    # category = await requestResponse(ctx, 'Please pick one of the options. `verification`, `antiping`, `staff_management`, `punishments`, `shift_management`, `customisation`.')
    category = SettingsSelectMenu(ctx.author.id)

    await invis_embed(ctx, 'Please select which category you would like to modify.', view=category)
    await category.wait()
    category = category.value

    if category == 'verification':
        question = 'What do you want to do with verification?'
        customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "role"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['verification']['enabled'] = True
        elif content == 'disable':
            settingContents['verification']['enabled'] = False
        elif content == 'role':
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use for verification? (e.g. `@Verified`)')).content
            convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
            settingContents['verification']['role'] = convertedContent.id
        else:
            return await invis_embed(ctx,
                                     'Please pick one of the options. `enable`, `disable`, `role`. Please run this command again with correct parameters.')
    elif category == 'antiping':
        question = 'What do you want to do with antiping?'
        customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "role", "bypass_role"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['antiping']['enabled'] = True
        elif content == 'disable':
            settingContents['antiping']['enabled'] = False
        elif content == 'role':
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use for anti-ping? (e.g. `@Anti-ping`)\n*You can separate roles with commas.*')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['antiping']['role'] = [role.id for role in convertedContent]
        elif content == "bypass_role" or content == "bypass" or content == "bypass-role":
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use as a bypass role? (e.g. `@Antiping Bypass`)\n*You can separate roles with commas.*')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['antiping']['bypass_role'] = [role.id for role in convertedContent]
        else:
            return await invis_embed(ctx, 'You have not selected one of the options. Please run this command again.')
    elif category == 'staff_management':
        question = 'What do you want to do with staff management?'
        customselect = CustomSelectMenu(ctx.author.id,
                                        ["enable", "disable", "channel", "role", "management_role", "loa_role",
                                         "ra_role"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['staff_management']['enabled'] = True
        elif content == 'disable':
            settingContents['staff_management']['enabled'] = False
        elif content == 'channel':
            content = (await request_response(bot, ctx,
                                              'What channel do you want to use for staff management? (e.g. `#staff-management`)')).content
            convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
            settingContents['staff_management']['channel'] = convertedContent.id
        elif content == 'role':
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use as a staff role? (e.g. `@Staff`\n**Note:** All members you want to be able to run advanced permission commands (punishments, staff management, shift management) must have this role. You can separate multiple roles by commas.')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['staff_management']['role'] = [role.id for role in convertedContent]
        elif content == 'management_role':
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use as a management role? (e.g. `@Community Management`\n**Note:** All members you want to be able to run **elevated** permission commands (removing warnings, setting up he bot, shift management, configurations) must have this role. You can separate multiple roles by commas.')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['staff_management']['management_role'] = [role.id for role in convertedContent]
        elif content == 'loa_role':
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use as a LOA role? (e.g. `@LOA`)\n*You can separate multiple roles by a comma.*')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['staff_management']['loa_role'] = [role.id for role in convertedContent]
        elif content == 'ra_role':
            content = (
                await request_response(bot, ctx,
                                       'What role do you want to use as a RA role? (e.g. `@RA`)')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['staff_management']['ra_role'] = [role.id for role in convertedContent]
        else:
            return await invis_embed(ctx, 'You have not selected one of the options. Please run this command again.')
    elif category == 'punishments':
        question = 'What do you want to do with punishments?'
        customselect = CustomSelectMenu(ctx.author.id,
                                        ["enable", "disable", "channel", "ban_channel", "kick_channel", "bolo_channel"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['punishments']['enabled'] = True
        elif content == 'disable':
            settingContents['punishments']['enabled'] = False
        elif content == 'channel':
            content = (await request_response(bot, ctx,
                                              'What channel do you want to use for punishments? (e.g. `#punishments`)')).content
            convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
            settingContents['punishments']['channel'] = convertedContent.id
        elif content == 'ban_channel':
            content = (
                await request_response(bot, ctx, 'What channel do you want to use for banning? (e.g. `#bans`)')).content
            convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
            settingContents['customisation']['ban_channel'] = convertedContent.id
        elif content == 'kick_channel':
            content = (
                await request_response(bot, ctx,
                                       'What channel do you want to use for kicking? (e.g. `#kicks`)')).content
            convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
            settingContents['customisation']['kick_channel'] = convertedContent.id
        elif content == 'bolo_channel':
            content = (
                await request_response(bot, ctx, 'What channel do you want to use for BOLOs? (e.g. `#bolos`)')).content
            convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
            settingContents['customisation']['bolo_channel'] = convertedContent.id
        else:
            return await invis_embed(ctx, 'You have not selected one of the options. Please run this command again.')
    elif category == 'shift_management':
        question = 'What do you want to do with shift management?'
        customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "channel", "role"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['shift_management']['enabled'] = True
        elif content == 'disable':
            settingContents['shift_management']['enabled'] = False
        elif content == 'channel':
            content = (await request_response(bot, ctx,
                                              'What channel do you want to use for shift management? (e.g. `#shift-management`)')).content
            convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
            settingContents['shift_management']['channel'] = convertedContent.id
        elif content == 'role':
            content = (await request_response(bot, ctx,
                                              'What role do you want to use for "Currently in game moderating"? (e.g. `@Currently In-game moderating`)\n*You can separate multiple roles by commas.*')).content
            if ',' in content:
                convertedContent = []
                for role in content.split(','):
                    role = role.strip()
                    convertedContent.append(await discord.ext.commands.RoleConverter().convert(ctx, role))
            else:
                convertedContent = [await discord.ext.commands.RoleConverter().convert(ctx, content)]
            settingContents['shift_management']['role'] = [role.id for role in convertedContent]
        else:
            return await invis_embed(ctx,
                                     'Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.')
    elif category == 'customisation':
        # color, prefix, brand name, thumbnail url, footer text, ban channel
        question = 'What would you like to customize?'
        customselect = CustomSelectMenu(ctx.author.id, ["color", "prefix", "brand_name", "thumbnail_url", "footer_text",
                                                        "server_code"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'color':
            content = (
                await request_response(bot, ctx,
                                       'What color do you want to use for the server? (e.g. `#00FF00`)')).content
            convertedContent = await discord.ext.commands.ColourConverter().convert(ctx, content)
            settingContents['customisation']['color'] = convertedContent.value
        elif content == 'prefix':
            content = (
                await request_response(bot, ctx, 'What prefix do you want to use for the server? (e.g. `!`)')).content
            settingContents['customisation']['prefix'] = content
        elif content == 'brand_name':
            content = (await request_response(bot, ctx,
                                              'What brand name do you want to use for the server? (e.g. `My Server`)')).content
            settingContents['customisation']['brand_name'] = content
        elif content == 'thumbnail_url':
            content = (await request_response(bot, ctx,
                                              'What thumbnail url do you want to use for the server? (e.g. `https://i.imgur.com/...`)')).content
            settingContents['customisation']['thumbnail_url'] = content
        elif content == 'footer_text':
            content = (await request_response(bot, ctx,
                                              'What footer text do you want to use for the server? (e.g. `My Server`)')).content
            settingContents['customisation']['footer_text'] = content
        elif content == 'server_code':
            content = (await request_response(bot, ctx, 'What server code do you use for your ER:LC server?')).content
            settingContents['customisation']['server_code'] = content
        else:
            return await invis_embed(ctx,
                                     'You did not pick any of the options. Please run this command again with correct parameters.')
    elif category == 'privacy':
        privacyConfig = await bot.privacy.find_by_id(ctx.guild.id)
        if privacyConfig is None:
            privacyConfig = {
                "_id": ctx.guild.id,
                "global_warnings": True
            }
        question = 'What would you like to change?'
        customselect = CustomSelectMenu(ctx.author.id, ["enable_global_warnings", "disable_global_warnings"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == "enable_global_warnings":
            privacyConfig['global_warnings'] = True
        if content == "disable_global_warnings":
            privacyConfig["global_warnings"] = False
        await bot.privacy.upsert(privacyConfig)
        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description="<:ArrowRight:1035003246445596774> Your configuration has been changed.",
            color=0x71c15f
        )
        return await ctx.send(embed=successEmbed)
    else:
        return await invis_embed(ctx,
                                 'You did not pick any of the options. Please run this command again with correct parameters.')

    await bot.settings.update_by_id(settingContents)
    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Success!",
        description="<:ArrowRight:1035003246445596774> Your configuration has been changed.",
        color=0x71c15f
    )
    await ctx.send(embed=successEmbed)


# support server invite command
@bot.hybrid_command(name='support', aliases=['support-server'],
                    description="Information about the ERM Support Server [Utility]")
async def support_server(ctx):
    # using an embed
    embed = discord.Embed(title='<:support:1035269007655321680> Support Server',
                          description='<:ArrowRight:1035003246445596774> Join the [**Support Server**](https://discord.gg/5pMmJEYazQ) to get help with the bot!',
                          color=0x2E3136)
    embed.set_footer(text=f"Shard {str(ctx.guild.shard_id)} | Guild ID: {str(ctx.guild.id)}")
    await ctx.send(embed=embed)


# uptime command
# * Finally works, basic and uses the bot on_ready event
@bot.hybrid_command(name='uptime', description="Shows the uptime of the bot [Utility]")
async def uptime(ctx):
    # using an embed
    current_time = time.time()
    difference = int(round(current_time - bot.start_time))
    text = datetime.timedelta(seconds=difference)
    embed = discord.Embed(color=0x2E3136)
    embed.add_field(name='<:Resume:1035269012445216858> Started At',
                    value=f"<:ArrowRight:1035003246445596774> <t:{int(bot.start_time)}>")
    embed.add_field(name='<:UptimeIconW:1035269010272550932> Uptime',
                    value=f"<:ArrowRight:1035003246445596774> {td_format(text)}")
    await ctx.send(embed=embed)


@bot.hybrid_command(
    name="warn",
    aliases=['w', 'wa'],
    description="Warns a user. [Punishments]",
    usage="<user> <reason>",
    brief="Warns a user.",
    with_app_command=True,
)
@is_staff()
async def warn(ctx, user, *, reason):
    request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
    if request.status_code != 200:
        oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
        oldRequestJSON = oldRequest.json()
        if not oldRequest.status_code == 200:
            return await invis_embed(ctx, 'User does not exist.')
        Id = oldRequestJSON['Id']
        request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
        requestJson = request.json()

    else:
        requestJson = request.json()
        data = requestJson['data']

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        Embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            Embed.description = """
            <:ArrowRightW:1035023450592514048>**Warnings:** 0
            <:ArrowRightW:1035023450592514048>**Kicks:** 0
            <:ArrowRightW:1035023450592514048>**Bans:** 0
            
            `Banned:` <:ErrorIcon:1035000018165321808>
            """
        else:

            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0
            for warningItem in user['warnings']:
                if warningItem['Guild'] == ctx.guild.id:
                    if warningItem['Type'] == "Warning":
                        warnings += 1
                    elif warningItem['Type'] == "Kick":
                        kicks += 1
                    elif warningItem['Type'] == "Ban":
                        bans += 1
                    elif warningItem['Type'] == "Temporary Ban":
                        bans += 1
                    elif warningItem['Type'] == "BOLO":
                        bolos += 1

            if bans != 0:
                banned = "<:CheckIcon:1035018951043842088>"
            else:
                banned = "<:ErrorIcon:1035000018165321808>"

            if bolos >= 1:
                Embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}
                
                <:WarningIcon:1035258528149033090> **BOLOs:**
                <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.
                
                `Banned:` {banned}
                """
            else:
                Embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}
                                                                                       
                `Banned:` {banned}
                """

        Embed.set_thumbnail(url=Headshot_URL)
        Embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')
        Embeds.append(Embed)

    if ctx.interaction:
        interaction = ctx.interaction
    else:
        interaction = ctx
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, show_page_director=False)

    async def warn_function(ctx, menu):
        user = menu.message.embeds[0].title
        await menu.stop(disable_items=True)
        default_warning_item = {
            '_id': user.lower(),
            'warnings': [{
                'id': next(generator),
                "Type": "Warning",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                "Guild": ctx.guild.id
            }]
        }

        singular_warning_item = {
            'id': next(generator),
            "Type": "Warning",
            "Reason": reason,
            "Moderator": [ctx.author.name, ctx.author.id],
            "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
            "Guild": ctx.guild.id
        }

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if not configItem['punishments']['enabled']:
            return await invis_embed(ctx,
                                     'This server has punishments disabled. Please run `/config change` to enable punishments.')

        embed = discord.Embed(title=user, color=0x2E3136)
        embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
        try:
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:staff:1035308057007230976> Staff Member",
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.name}#{ctx.author.discriminator}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRight:1035003246445596774> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value="<:ArrowRight:1035003246445596774> Warning",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason", value=f"<:ArrowRight:1035003246445596774> {reason}",
                        inline=False)

        channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

        if not channel:
            return await invis_embed(ctx,
                                     'The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.')

        item = None
        if not await bot.warnings.find_by_id(user.lower()):
            item = await bot.warnings.find_by_id(user.lower())
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)

        view = YesNoMenu(ctx.author.id)
        if item is not None:
            for warning in item['warnings']:
                if warning['Guild'] == ctx.guild.id:
                    if warning['Type'] == "BOLO":
                        await invis_embed(ctx,
                                          'This user has a BOLO (Be on the Lookout) active. Are you sure you would like to continue?',
                                          view=view)
                        await view.wait()
                        if view.value is True:
                            continue
                        else:
                            return await invis_embed(ctx, 'Successfully cancelled.')

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Warning Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s warning has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)
        await channel.send(embed=embed)

    async def task():
        await warn_function(ctx, menu)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    async def cancelTask():
        await menu.message.edit(embed=discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        ))
        await menu.stop(disable_items=True)

    def cancelTaskWrapper():
        bot.loop.create_task(
            cancelTask()
        )

    followUp = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            taskWrapper
        )
    )
    cancelFollowup = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            cancelTaskWrapper
        )
    )

    menu.add_buttons([
        ViewButton(
            emoji="✅",
            custom_id=ViewButton.ID_CALLER,
            followup=followUp
        ),
        ViewButton(
            emoji="❎",
            custom_id=ViewButton.ID_CALLER,
            followup=cancelFollowup
        )
    ])

    try:
        menu.add_pages(Embeds)
        await menu.start()
    except:
        return await invis_embed(ctx,
                                 'This user does not exist on the Roblox platform. Please try again with a valid username.')


@bot.hybrid_command(
    name="kick",
    aliases=['k', 'ki'],
    description="Kick a user. [Punishments]",
    usage="<user> <reason>",
    brief="Kicks a user.",
    with_app_command=True,
)
@is_staff()
async def kick(ctx, user, *, reason):
    request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
    if request.status_code != 200:
        oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
        oldRequestJSON = oldRequest.json()
        if not oldRequest.status_code == 200:
            return await invis_embed(ctx, 'User does not exist.')
        Id = oldRequestJSON['Id']
        request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
        requestJson = request.json()

    else:
        requestJson = request.json()
        data = requestJson['data']

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        Embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            Embed.description = """
            <:ArrowRightW:1035023450592514048>**Warnings:** 0
            <:ArrowRightW:1035023450592514048>**Kicks:** 0
            <:ArrowRightW:1035023450592514048>**Bans:** 0

            `Banned:` <:ErrorIcon:1035000018165321808>
            """
        else:
            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0

            for warningItem in user['warnings']:
                if warningItem['Guild'] == ctx.guild.id:
                    if warningItem['Type'] == "Warning":
                        warnings += 1
                    elif warningItem['Type'] == "Kick":
                        kicks += 1
                    elif warningItem['Type'] == "Ban":
                        bans += 1
                    elif warningItem['Type'] == "Temporary Ban":
                        bans += 1
                    elif warningItem['Type'] == "BOLO":
                        bolos += 1
            if bans != 0:
                banned = "<:CheckIcon:1035018951043842088>"
            else:
                banned = "<:ErrorIcon:1035000018165321808>"

            if bolos >= 1:
                Embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                <:WarningIcon:1035258528149033090> **BOLOs:**
                <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                `Banned:` {banned}
                """
            else:
                Embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                `Banned:` {banned}
                """
        Embed.set_thumbnail(url=Headshot_URL)
        Embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')
        Embeds.append(Embed)

    if ctx.interaction:
        interaction = ctx.interaction
    else:
        interaction = ctx
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, show_page_director=False)

    async def kick_function(ctx, menu):
        user = menu.message.embeds[0].title
        await menu.stop(disable_items=True)
        default_warning_item = {
            '_id': user.lower(),
            'warnings': [{
                'id': next(generator),
                "Type": "Kick",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                "Guild": ctx.guild.id
            }]
        }

        singular_warning_item = {
            'id': next(generator),
            "Type": "Kick",
            "Reason": reason,
            "Moderator": [ctx.author.name, ctx.author.id],
            "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
            "Guild": ctx.guild.id
        }

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if not configItem['punishments']['enabled']:
            return await invis_embed(ctx,
                                     'This server has punishments disabled. Please run `/config change` to enable punishments.')

        embed = discord.Embed(title=user, color=0x2E3136)
        embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
        try:
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:staff:1035308057007230976> Staff Member",
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.name}#{ctx.author.discriminator}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRight:1035003246445596774> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type", value="<:ArrowRight:1035003246445596774> Kick",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason", value=f"<:ArrowRight:1035003246445596774> {reason}",
                        inline=False)

        try:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['customisation']['kick_channel'])
        except:
            channel = None
        if not channel:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])
        if not channel:
            return await invis_embed(ctx,
                                     'The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.')

        if not await bot.warnings.find_by_id(user.lower()):
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Kick Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s kick has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)
        await channel.send(embed=embed)

    async def task():
        await kick_function(ctx, menu)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    async def cancelTask():
        await menu.message.edit(embed=discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        ))
        await menu.stop(disable_items=True)

    def cancelTaskWrapper():
        bot.loop.create_task(
            cancelTask()
        )

    followUp = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            taskWrapper
        )
    )
    cancelFollowup = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            cancelTaskWrapper
        )
    )

    menu.add_buttons([
        ViewButton(
            emoji="✅",
            custom_id=ViewButton.ID_CALLER,
            followup=followUp
        ),
        ViewButton(
            emoji="❎",
            custom_id=ViewButton.ID_CALLER,
            followup=cancelFollowup
        )
    ])

    try:
        menu.add_pages(Embeds)
        await menu.start()
    except:
        return await invis_embed(ctx,
                                 'This user does not exist on the Roblox platform. Please try again with a valid username.')


@bot.hybrid_command(
    name="ban",
    aliases=['b', 'ba'],
    description="Bans a user. [Punishments]",
    usage="<user> <reason>",
    brief="Bans a user.",
    with_app_command=True,
)
@is_staff()
async def ban(ctx, user, *, reason):
    request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
    if request.status_code != 200:
        oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
        oldRequestJSON = oldRequest.json()
        if not oldRequest.status_code == 200:
            return await invis_embed(ctx, 'User does not exist.')
        Id = oldRequestJSON['Id']
        request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
        requestJson = request.json()

    else:
        requestJson = request.json()
        data = requestJson['data']

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        Embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            Embed.description = """
                   <:ArrowRightW:1035023450592514048>**Warnings:** 0
                   <:ArrowRightW:1035023450592514048>**Kicks:** 0
                   <:ArrowRightW:1035023450592514048>**Bans:** 0

                   `Banned:` <:ErrorIcon:1035000018165321808>
                   """
        else:

            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0
            for warningItem in user['warnings']:
                if warningItem['Guild'] == ctx.guild.id:
                    if warningItem['Type'] == "Warning":
                        warnings += 1
                    elif warningItem['Type'] == "Kick":
                        kicks += 1
                    elif warningItem['Type'] == "Ban":
                        bans += 1
                    elif warningItem['Type'] == "Temporary Ban":
                        bans += 1
                    elif warningItem['Type'] == "BOLO":
                        bolos += 1

            if bans != 0:
                banned = "<:CheckIcon:1035018951043842088>"
            else:
                banned = "<:ErrorIcon:1035000018165321808>"

            if bolos >= 1:
                Embed.description = f"""
                       <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                       <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                       <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                       <:WarningIcon:1035258528149033090> **BOLOs:**
                       <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                       `Banned:` {banned}
                       """
            else:
                Embed.description = f"""
                       <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                       <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                       <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                       `Banned:` {banned}
                       """

        Embed.set_thumbnail(url=Headshot_URL)
        Embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')
        Embeds.append(Embed)

    if ctx.interaction:
        interaction = ctx.interaction
    else:
        interaction = ctx
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, show_page_director=False)

    async def ban_function(ctx, menu):
        user = menu.message.embeds[0].title
        await menu.stop(disable_items=True)
        default_warning_item = {
            '_id': user.lower(),
            'warnings': [{
                'id': next(generator),
                "Type": "Ban",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                "Guild": ctx.guild.id
            }]
        }

        singular_warning_item = {
            'id': next(generator),
            "Type": "Ban",
            "Reason": reason,
            "Moderator": [ctx.author.name, ctx.author.id],
            "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
            "Guild": ctx.guild.id
        }

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if not configItem['punishments']['enabled']:
            return await invis_embed(ctx,
                                     'This server has punishments disabled. Please run `/config change` to enable punishments.')

        embed = discord.Embed(title=user, color=0x2E3136)
        embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
        try:
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:staff:1035308057007230976> Staff Member",
                        value=f"<:ArrowRightW:1035023450592514048> {ctx.author.name}#{ctx.author.discriminator}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRightW:1035023450592514048> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type", value="<:ArrowRightW:1035023450592514048> Ban",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason",
                        value=f"<:ArrowRightW:1035023450592514048> {reason}",
                        inline=False)

        try:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['customisation']['kick_channel'])
        except:
            channel = None
        if not channel:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

        if not channel:
            return await invis_embed(ctx,
                                     'The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.')

        if not await bot.warnings.find_by_id(user.lower()):
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Ban Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s ban has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)
        await channel.send(embed=embed)

    async def task():
        await ban_function(ctx, menu)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    async def cancelTask():
        await menu.message.edit(embed=discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        ))
        await menu.stop(disable_items=True)

    def cancelTaskWrapper():
        bot.loop.create_task(
            cancelTask()
        )

    followUp = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            taskWrapper
        )
    )
    cancelFollowup = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            cancelTaskWrapper
        )
    )

    menu.add_buttons([
        ViewButton(
            emoji="✅",
            custom_id=ViewButton.ID_CALLER,
            followup=followUp
        ),
        ViewButton(
            emoji="❎",
            custom_id=ViewButton.ID_CALLER,
            followup=cancelFollowup
        )
    ])

    try:
        menu.add_pages(Embeds)
        await menu.start()
    except:
        return await invis_embed(ctx,
                                 'This user does not exist on the Roblox platform. Please try again with a valid username.')


@bot.hybrid_command(
    name="messagelog",
    aliases=['m', 'mlog'],
    description="Logs the in-game :m usage of a staff member. [Staff Management]",
    usage="<message>",
    with_app_command=True,
)
@is_staff()
async def mlog(ctx, *, message):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if not configItem['staff_management']['enabled']:
        return await invis_embed(ctx,
                                 'This server has punishments disabled. Please run `/config change` to enable punishments.')

    embed = discord.Embed(title='<:Resume:1035269012445216858> In-game Message', color=0x2E3136)
    try:
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Staff Logging Module")
    except:
        pass
    embed.add_field(name="<:staff:1035308057007230976> Staff Member",
                    value=f"<:ArrowRightW:1035023450592514048> {ctx.author.name}#{ctx.author.discriminator}",
                    inline=False)
    embed.add_field(name="<:MessageIcon:1035321236793860116> Message", value=message, inline=False)

    if not configItem['staff_management']['channel'] is None:
        channel = ctx.guild.get_channel(configItem['staff_management']['channel'])
    if not channel:
        return await invis_embed(
            'The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.')

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Message Logged",
        description="<:ArrowRight:1035003246445596774> Your message has been logged successfully.",
        color=0x71c15f
    )
    await channel.send(embed=embed)
    await ctx.send(embed=successEmbed)


@bot.hybrid_command(
    name="tempban",
    aliases=['tb', 'tba'],
    description="Tempbans a user. [Punishments]",
    with_app_command=True,
)
@is_staff()
async def tempban(ctx, user, time: str, *, reason):
    reason = ''.join(reason)

    timeObj = list(reason)[-1]
    reason = list(reason)

    if not time.endswith(('h', 'm', 's', 'd', 'w')):
        reason.insert(0, time)
        if not timeObj.endswith(('h', 'm', 's', 'd', 'w')):
            return await invis_embed(ctx,
                                     'A time must be provided at the **start** of your reason. Example: >tban i_iMikey 12h LTAP')
        else:
            time = timeObj
            reason.pop()

    if time.endswith('s'):
        time = int(removesuffix(time, 's'))
    elif time.endswith('m'):
        time = int(removesuffix(time, 'm')) * 60
    elif time.endswith('h'):
        time = int(removesuffix(time, 'h')) * 60 * 60
    elif time.endswith('d'):
        time = int(removesuffix(time, 'd')) * 60 * 60 * 24
    elif time.endswith('w'):
        time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7

    startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
    endTimestamp = int(startTimestamp + time)

    reason = ''.join([str(item) for item in reason])

    request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
    if request.status_code != 200:
        oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
        oldRequestJSON = oldRequest.json()
        if not oldRequest.status_code == 200:
            return await invis_embed(ctx, 'User does not exist.')
        Id = oldRequestJSON['Id']
        request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
        requestJson = request.json()

    else:
        requestJson = request.json()
        data = requestJson['data']

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        Embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            Embed.description = """
                   <:ArrowRightW:1035023450592514048>**Warnings:** 0
                   <:ArrowRightW:1035023450592514048>**Kicks:** 0
                   <:ArrowRightW:1035023450592514048>**Bans:** 0

                   `Banned:` <:ErrorIcon:1035000018165321808>
                   """
        else:

            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0
            for warningItem in user['warnings']:
                if warningItem['Guild'] == ctx.guild.id:
                    if warningItem['Type'] == "Warning":
                        warnings += 1
                    elif warningItem['Type'] == "Kick":
                        kicks += 1
                    elif warningItem['Type'] == "Ban":
                        bans += 1
                    elif warningItem['Type'] == "Temporary Ban":
                        bans += 1
                    elif warningItem['Type'] == "BOLO":
                        bolos += 1

            if bans != 0:
                banned = "<:CheckIcon:1035018951043842088>"
            else:
                banned = "<:ErrorIcon:1035000018165321808>"

            if bolos >= 1:
                Embed.description = f"""
                       <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                       <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                       <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                       <:WarningIcon:1035258528149033090> **BOLOs:**
                       <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                       `Banned:` {banned}
                       """
            else:
                Embed.description = f"""
                       <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                       <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                       <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                       `Banned:` {banned}
                       """

        Embed.set_thumbnail(url=Headshot_URL)
        Embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')
        Embeds.append(Embed)

    async def ban_function(ctx, menu):

        user = menu.message.embeds[0].title
        await menu.stop(disable_items=True)
        default_warning_item = {
            '_id': user.lower(),
            'warnings': [{
                'id': next(generator),
                "Type": "Temporary Ban",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                "Until": endTimestamp,
                "Guild": ctx.guild.id
            }]
        }

        singular_warning_item = {
            'id': next(generator),
            "Type": "Temporary Ban",
            "Reason": reason,
            "Moderator": [ctx.author.name, ctx.author.id],
            "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
            "Until": endTimestamp,
            "Guild": ctx.guild.id
        }

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if not configItem['punishments']['enabled']:
            return await invis_embed(ctx,
                                     'This server has punishments disabled. Please run `/config change` to enable punishments.')

        embed = discord.Embed(title=user, color=0x2E3136)
        embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
        try:
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:staff:1035308057007230976> Staff Member",
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.name}#{ctx.author.discriminator}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRight:1035003246445596774> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value="<:ArrowRight:1035003246445596774> Temporary Ban",
                        inline=False)
        embed.add_field(name="<:Clock:1035308064305332224> Until",
                        value=f"<:ArrowRight:1035003246445596774> <t:{singular_warning_item['Until']}>",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason", value=f"<:ArrowRight:1035003246445596774> {reason}",
                        inline=False)

        try:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['customisation']['ban_channel'])
        except:
            channel = None

        if not channel:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])
        if not channel:
            return await invis_embed(ctx,
                                     'The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.')

        if not await bot.warnings.find_by_id(user.lower()):
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)
        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Ban Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s ban has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)
        await channel.send(embed=embed)

    if ctx.interaction:
        interaction = ctx.interaction
    else:
        interaction = ctx
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, show_page_director=False)

    async def task():
        await ban_function(ctx, menu)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    async def cancelTask():
        await menu.message.edit(embed=discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        ))
        await menu.stop(disable_items=True)

    def cancelTaskWrapper():
        bot.loop.create_task(
            cancelTask()
        )

    followUp = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            taskWrapper
        )
    )
    cancelFollowup = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            cancelTaskWrapper
        )
    )

    menu.add_buttons([
        ViewButton(
            emoji="✅",
            custom_id=ViewButton.ID_CALLER,
            followup=followUp
        ),
        ViewButton(
            emoji="❎",
            custom_id=ViewButton.ID_CALLER,
            followup=cancelFollowup
        )
    ])

    try:
        menu.add_pages(Embeds)
        await menu.start()
    except:
        return await invis_embed(ctx,
                                 'This user does not exist on the Roblox platform. Please try again with a valid username.')


@bot.hybrid_command(
    name="search",
    aliases=["s"],
    description="Searches for a user in the warning database. [Search]",
    usage="<user>",
    with_app_command=True,
)
async def search(ctx, *, query):
    alerts = {
        'NoAlerts': '<:ArrowRight:1035003246445596774> No alerts found for this account!',
        'AccountAge': '<:ArrowRight:1035003246445596774> The account age of the user is less than 100 days.',
        'NoDescription': '<:ArrowRight:1035003246445596774> This account has no description.',
        'SuspiciousUsername': '<:ArrowRight:1035003246445596774> This account could be an alt account.',
        'MassPunishments': '<:ArrowRight:1035003246445596774> This user exceeds the regular amount of warnings that a user should have.',
        'UserDoesNotExist': '<:ArrowRight:1035003246445596774> This user does not exist.',
        'IsBanned': '<:ArrowRight:1035003246445596774> This user is banned from Roblox.',
        'NotManyFriends': '<:ArrowRight:1035003246445596774> This user has less than 30 friends.',
        'NotManyGroups': '<:ArrowRight:1035003246445596774> This user has less than 5 groups.',
        'HasBOLO': '<:ArrowRight:1035003246445596774> This user has a BOLO active.'
    }

    logging.info(query)
    query = query.split('.')
    query = query[0]

    logging.info(query)
    RESULTS = []

    dataset = await bot.warnings.find_by_id(query.lower())
    try:
        logging.info(dataset['warnings'][0])
    except:
        dataset = None
    if dataset:
        logging.info(dataset)
        dataset['warnings'][0]['name'] = query.lower()
        RESULTS.append(dataset['warnings'])

    if len(RESULTS) == 0:

        try:
            User = await client.get_user_by_username(query)
        except:
            return await invis_embed(ctx, 'No user matches your query.')

        triggered_alerts = []

        if User.is_banned:
            triggered_alerts.append('IsBanned')
        if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
            triggered_alerts.append('AccountAge')
        if not User:
            triggered_alerts.append('UserDoesNotExist')
        if len(User.description) < 10:
            triggered_alerts.append('NoDescription')
        if any(x in User.name for x in ['alt', 'alternative', 'account']):
            triggered_alerts.append('SuspiciousUsername')
        if await User.get_friend_count() <= 30:
            triggered_alerts.append('NotManyFriends')
        if len(await User.get_group_roles()) <= 5:
            triggered_alerts.append('NotManyGroups')

        if len(triggered_alerts) == 0:
            triggered_alerts.append('NoAlerts')

        embed1 = discord.Embed(title=query, color=0x2E3136)
        embed1.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.display_avatar.url)
        if query.lower() in bot.staff_members.keys():
            await staff_field(embed1, query.lower())
        embed1.add_field(name='<:MalletWhite:1035258530422341672> Punishments',
                         value=f'<:ArrowRight:1035003246445596774> 0', inline=False)
        string = "\n".join([alerts[i] for i in triggered_alerts])

        embed1.add_field(name='<:WarningIcon:1035258528149033090> Alerts', value=f'{string}', inline=False)
        embed1.set_thumbnail(
            url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
                User.id))
        await ctx.send(embed=embed1)

    if len(RESULTS) > 1:
        return await invis_embed(ctx,
                                 'More than one result match your query. If this is unexpected, join the [support server](https://discord.gg/5pMmJEYazQ) and contact a Support Team member.')

    if len(RESULTS) == 1:

        message = ctx.message

        embed1 = discord.Embed(title=RESULTS[0][0]['name'], color=0x2E3136)
        embed2 = discord.Embed(title=RESULTS[0][0]['name'], color=0x2E3136)

        result_var = None
        logging.info(message.content.lower())

        for result in RESULTS:
            if result[0]['name'] == RESULTS[0][0]['name']:
                result_var = RESULTS[0]

        result = result_var

        triggered_alerts = []

        User = await client.get_user_by_username(result[0]['name'], expand=True, exclude_banned_users=False)

        listOfPerGuild = []
        for item in result:
            if item['Guild'] == ctx.guild.id:
                listOfPerGuild.append(item)

        if User.is_banned:
            triggered_alerts.append('IsBanned')
        if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
            triggered_alerts.append('AccountAge')
        if not User:
            triggered_alerts.append('UserDoesNotExist')
        if len(User.description) < 10:
            triggered_alerts.append('NoDescription')
        if any(x in User.name for x in ['alt', 'alternative', 'account']):
            triggered_alerts.append('SuspiciousUsername')
        if len(listOfPerGuild) > 5:
            triggered_alerts.append('MassPunishments')
        if await User.get_friend_count() <= 30:
            triggered_alerts.append('NotManyFriends')
        if len(await User.get_group_roles()) <= 5:
            triggered_alerts.append('NotManyGroups')

        for warning in listOfPerGuild:
            if warning['Type'] == 'BOLO':
                triggered_alerts.append('HasBOLO')
                break

        if len(triggered_alerts) == 0:
            triggered_alerts.append('NoAlerts')

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if not configItem['punishments']['enabled']:
            return await invis_embed(ctx,
                                     'This server has punishments disabled. Please run `/config change` to enable punishments.')

        embeds = [embed1, embed2]

        if embed1.title in bot.staff_members.keys():
            await staff_field(embeds[0], embed1.title)

        embeds[0].add_field(name='<:MalletWhite:1035258530422341672> Punishments',
                            value=f'<:ArrowRight:1035003246445596774> {len(listOfPerGuild)}', inline=False)
        string = "\n".join([alerts[i] for i in triggered_alerts])
        embeds[0].add_field(name='<:WarningIcon:1035258528149033090> Alerts', value=f'{string}', inline=False)

        del result[0]['name']

        for action in result:
            if action['Guild'] == ctx.guild.id:
                if isinstance(action['Moderator'], list):
                    user = discord.utils.get(ctx.guild.members, id=action['Moderator'][1])
                    if user:
                        action['Moderator'] = user.mention
                    else:
                        action['Moderator'] = action['Moderator'][1]
                if 'Until' in action.keys():
                    if len(embeds[-1].fields) <= 2:
                        embeds[-1].add_field(
                            name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                            inline=False
                        )
                    else:
                        embeds.append(discord.Embed(title=embeds[0].title, color=await generate_random(ctx)))
                        embeds[-1].add_field(
                            name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                            inline=False
                        )
                else:
                    if len(embeds[-1].fields) <= 2:
                        embeds[-1].add_field(
                            name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                            inline=False
                        )
                    else:
                        embeds.append(discord.Embed(title=embeds[0].title, color=0x2E3136))
                        embeds[-1].add_field(
                            name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                            inline=False
                        )

        for index, embed in enumerate(embeds):
            embed.set_thumbnail(
                url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
                    User.id))
            embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                             icon_url=ctx.author.display_avatar.url)
            if index != 0:
                embed.set_footer(text=f"Navigate this page by using the buttons below.")

        if ctx.interaction:
            interaction = ctx.interaction
        else:
            interaction = ctx
        menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        menu.add_pages(embeds)
        await menu.start()


# @search.autocomplete('query')
# async def autocomplete_callback(interaction: discord.Interaction, current: str):
# 	datasets = await bot.warnings.get_all()
# 	applicable_data = []
# 	for item in datasets:
# 		for _item in item['warnings']:
# 			if _item['Guild'] == interaction.guild.id:
# 				if item not in applicable_data:
# 					applicable_data.append(item)

# 	logging.info(applicable_data)
# 	applicable_data = [x['_id'] for x in applicable_data if x['_id'].lower().startswith(current.lower())]
# 	logging.info(applicable_data)

# 	choices = []
# 	for item in applicable_data:
# 		if len(choices) >= 25:
# 			break
# 		choices.append(app_commands.Choice(name = item, value = item))
# 	return choices

@bot.hybrid_command(
    name="globalsearch",
    aliases=["gs"],
    description="Searches for a user in the warning database. This will show warnings from all servers. [Search]",
    usage="<user>",
    with_app_command=True,
)
async def globalsearch(ctx, *, query):
    alerts = {
        'NoAlerts': '<:ArrowRight:1035003246445596774> No alerts found for this account!',
        'AccountAge': '<:ArrowRight:1035003246445596774> The account age of the user is less than 100 days.',
        'NoDescription': '<:ArrowRight:1035003246445596774> This account has no description.',
        'SuspiciousUsername': '<:ArrowRight:1035003246445596774> This account could be an alt account.',
        'MassPunishments': '<:ArrowRight:1035003246445596774> This user exceeds the regular amount of warnings that a user should have.',
        'UserDoesNotExist': '<:ArrowRight:1035003246445596774> This user does not exist.',
        'IsBanned': '<:ArrowRight:1035003246445596774> This user is banned from Roblox.',
        'NotManyFriends': '<:ArrowRight:1035003246445596774> This user has less than 30 friends.',
        'NotManyGroups': '<:ArrowRight:1035003246445596774> This user has less than 5 groups.'
    }

    logging.info(query)
    query = query.split('.')
    query = query[0]

    logging.info(query)
    RESULTS = []

    dataset = await bot.warnings.find_by_id(query.lower())
    if dataset:
        logging.info(dataset)
        logging.info(dataset['warnings'][0])

        dataset['warnings'][0]['name'] = query.lower()
        RESULTS.append(dataset['warnings'])

    if len(RESULTS) == 0:
        try:
            User = await client.get_user_by_username(query)
        except:
            return await invis_embed(ctx, 'No user matches your query.')
        triggered_alerts = []

        if User.is_banned:
            triggered_alerts.append('IsBanned')
        if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
            triggered_alerts.append('AccountAge')
        if not User:
            triggered_alerts.append('UserDoesNotExist')
        if len(User.description) < 10:
            triggered_alerts.append('NoDescription')
        if any(x in User.name for x in ['alt', 'alternative', 'account']):
            triggered_alerts.append('SuspiciousUsername')
        if await User.get_friend_count() <= 30:
            triggered_alerts.append('NotManyFriends')
        if len(await User.get_group_roles()) <= 5:
            triggered_alerts.append('NotManyGroups')

        if len(triggered_alerts) == 0:
            triggered_alerts.append('NoAlerts')

        embed1 = discord.Embed(title=query, color=0x2E3136)
        embed1.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.display_avatar.url)

        if embed1.title in bot.staff_members.keys():
            await staff_field(embed1, embed1.title)

        embed1.add_field(name='<:MalletWhite:1035258530422341672> Punishments',
                         value=f'<:ArrowRight:1035003246445596774> 0', inline=False)
        string = "\n".join([alerts[i] for i in triggered_alerts])
        embed1.add_field(name='<:WarningIcon:1035258528149033090> Alerts', value=f'{string}', inline=False)
        embed1.set_thumbnail(
            url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
                User.id))
        await ctx.send(embed=embed1)
    if len(RESULTS) == 1:

        embed1 = discord.Embed(title=RESULTS[0][0]['name'], color=0x2E3136)
        embed2 = discord.Embed(title=RESULTS[0][0]['name'], color=0x2E3136)

        result_var = None

        for result in RESULTS:
            if result[0]['name'] == RESULTS[0][0]['name']:
                result_var = RESULTS[0]

        result = result_var
        triggered_alerts = []

        for warning in result:
            if not warning['Guild'] == ctx.guild.id:
                privacySettings = await check_privacy(warning['Guild'], 'global_warnings')
                if not privacySettings:
                    result.remove(warning)

        try:
            User = await client.get_user_by_username(result[0]['name'], expand=True, exclude_banned_users=False)
        except IndexError:
            try:
                User = await client.get_user_by_username(query, exclude_banned_users=False, expand=True)
            except:
                return await invis_embed(ctx, 'No user matches your query.')
            triggered_alerts = []

            if User.is_banned:
                triggered_alerts.append('IsBanned')
            if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
                triggered_alerts.append('AccountAge')
            if not User:
                triggered_alerts.append('UserDoesNotExist')
            if len(User.description) < 10:
                triggered_alerts.append('NoDescription')
            if any(x in User.name for x in ['alt', 'alternative', 'account']):
                triggered_alerts.append('SuspiciousUsername')
            if await User.get_friend_count() <= 30:
                triggered_alerts.append('NotManyFriends')
            if len(await User.get_group_roles()) <= 5:
                triggered_alerts.append('NotManyGroups')

            if len(triggered_alerts) == 0:
                triggered_alerts.append('NoAlerts')

            embed1 = discord.Embed(title=query, color=0x2E3136)
            embed1.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                              icon_url=ctx.author.display_avatar.url)

            if embed1.title in bot.staff_members.keys():
                await staff_field(embed1, embed1.title)

            embed1.add_field(name='<:MalletWhite:1035258530422341672> Punishments',
                             value=f'<:ArrowRight:1035003246445596774> 0', inline=False)
            string = "\n".join([alerts[i] for i in triggered_alerts])
            embed1.add_field(name='<:WarningIcon:1035258528149033090> Alerts', value=f'{string}', inline=False)
            embed1.set_thumbnail(
                url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
                    User.id))
            return await ctx.send(embed=embed1)

        if User.is_banned:
            triggered_alerts.append('IsBanned')
        if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
            triggered_alerts.append('AccountAge')
        if not User:
            triggered_alerts.append('UserDoesNotExist')
        if len(User.description) < 10:
            triggered_alerts.append('NoDescription')
        if any(x in User.name for x in ['alt', 'alternative', 'account']):
            triggered_alerts.append('SuspiciousUsername')
        if len(result) > 5:
            triggered_alerts.append('MassPunishments')
        if await User.get_friend_count() <= 30:
            triggered_alerts.append('NotManyFriends')
        if len(await User.get_group_roles()) <= 5:
            triggered_alerts.append('NotManyGroups')

        if len(triggered_alerts) == 0:
            triggered_alerts.append('NoAlerts')

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        embeds = [embed1, embed2]

        if embed1.title in bot.staff_members.keys():
            await staff_field(embeds[0], embed1.title)

        embeds[0].add_field(name='<:MalletWhite:1035258530422341672> Punishments',
                            value=f'<:ArrowRight:1035003246445596774> {len(result)}', inline=False)
        string = "\n".join([alerts[i] for i in triggered_alerts])
        embeds[0].add_field(name='<:WarningIcon:1035258528149033090> Alerts', value=f'{string}', inline=False)

        del result[0]['name']

        for index, action in enumerate(result):
            if 'Until' in action.keys():
                if len(embeds[-1].fields) <= 2:
                    embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator'][0]}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                        inline=False
                    )
                else:
                    embeds.append(discord.Embed(title=embeds[0].title, color=0x2E3136))
                    embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator'][0]}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **Until:** <t:{action['Until']}>\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                        inline=False
                    )
            else:
                if len(embeds[-1].fields) <= 2:
                    embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator'][0]}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                        inline=False
                    )
                else:
                    embeds.append(discord.Embed(title=embeds[0].title, color=0x2E3136))
                    embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {action['Type']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Reason:** {action['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {action['Moderator']}\n<:ArrowRightW:1035023450592514048> **Time:** {action['Time']}\n<:ArrowRightW:1035023450592514048> **ID:** {action['id']}",
                        inline=False
                    )

        for index, embed in enumerate(embeds):
            embed.set_thumbnail(
                url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
                    User.id))
            embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                             icon_url=ctx.author.display_avatar.url)
            if index != 0:
                embed.set_footer(text=f"Navigate this page by using the reactions below.")

        if ctx.interaction:
            interaction = ctx.interaction
        else:
            interaction = ctx
        menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        menu.add_pages(embeds)
        await menu.start()


#
# @globalsearch.autocomplete('query')
# async def autocomplete_callback(interaction: discord.Interaction, current: str):
#     datasets = await bot.warnings.get_all()
#     applicable_data = []
#     for item in datasets:
#         if item not in applicable_data:
#             applicable_data.append(item)
#
#     logging.info(applicable_data)
#     applicable_data = [x['_id'] for x in applicable_data if x['_id'].lower().startswith(current.lower())]
#     logging.info(applicable_data)
#
#     choices = []
#     for item in applicable_data:
#         if len(choices) >= 25:
#             break
#         choices.append(app_commands.Choice(name=item, value=item))
#     return choices


@punishments.command(
    name='void',
    aliases=['rw', 'delwarn', 'dw', 'removewarnings', 'rws', 'dws', 'delwarnings'],
    description='Remove a warning from a user. [Punishments]',
    usage='<user> <warning id>',
    with_app_command=True,
)
@is_staff()
async def removewarning(ctx, id: str):
    try:
        id = int(id)
    except:
        return await invis_embed(ctx, '`id` is not a valid ID.')

    keyStorage = None
    selected_item = None
    selected_items = []
    item_index = 0

    for item in await bot.warnings.get_all():
        for index, _item in enumerate(item['warnings']):
            if _item['id'] == id:
                selected_item = _item
                selected_items.append(_item)
                parent_item = item
                item_index = index
                break

    if selected_item is None:
        return await invis_embed(ctx, 'That warning does not exist.')

    if selected_item['Guild'] != ctx.guild.id:
        return await invis_embed(ctx, 'You are trying to remove a warning that is not apart of this guild.')

    if len(selected_items) > 1:
        return await invis_embed(ctx,
                                 'There is more than one warning associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.')

    Moderator = discord.utils.get(ctx.guild.members, id=selected_item['Moderator'][1])
    if Moderator:
        Moderator = Moderator.mention
    else:
        Moderator = selected_item['Moderator'][0]

    embed = discord.Embed(
        title="<:MalletWhite:1035258530422341672> Remove Warning",
        description=f"<:ArrowRightW:1035023450592514048> **Reason:** {selected_item['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {Moderator}\n<:ArrowRightW:1035023450592514048> **ID:** {selected_item['id']}\n",
        color=0x2E3136
    )

    view = RemoveWarning(ctx.author.id)
    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value:
        parent_item['warnings'].remove(selected_item)
        await bot.warnings.update_by_id(parent_item)


@bot.hybrid_command(
    name='help',
    aliases=['h', 'commands', 'cmds', 'cmd', 'command'],
    description='Get a list of commands. [Utility]',
    usage='<command>',
    with_app_command=True,
)
async def help(ctx, *, command=None):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if command == None:

        embed = discord.Embed(
            title='<:support:1035269007655321680> Command List | Emergency Response Management',
            color=0x2E3136
        )

        categories = []
        commands = []

        category_to_emoji = {
            'Punishments': '<:MalletWhite:1035258530422341672>',
            'Staff Management': "<:staff:1035308057007230976>",
            "Configuration": "<:FlagIcon:1035258525955395664>",
            "Miscellaneous": "<:QMark:1035308059532202104>",
            "Search": "<:Search:1035353785184288788>",
            "Utility": "<:SettingIcon:1035353776460152892>",
            "Shift Management": "<:Clock:1035308064305332224>",
            "Reminders": "<:Resume:1035269012445216858>"
        }

        for command in bot.walk_commands():

            try:
                command.category = command.description.split('[')[1].replace('[', '').replace(']', '')
            except:
                command.category = 'Miscellaneous'

            if isinstance(command, discord.ext.commands.core.Command):
                if command.hidden:
                    continue
                if command.parent is not None:
                    if isinstance(command.parent,
                                  discord.ext.commands.core.Group) and not command.parent.name == "jishaku" and not command.parent.name == "jsk":
                        if command.parent.name not in ['voice']:
                            command.full_name = f"{command.parent.name} {command.name}"
                        else:
                            continue
                    else:
                        continue
                else:
                    command.full_name = f"{command.name}"

            if isinstance(command, discord.ext.commands.core.Group):
                continue

            if command.category not in categories:
                categories.append(command.category)
                commands.append(command)
            else:
                commands.append(command)

        for category in categories:

            full_category = category_to_emoji[category] + ' ' + category

            string = '\n'.join(
                [
                    f'<:ArrowRight:1035003246445596774> `/{command}` | *{command.description.split("[")[0]}*'
                    for
                    command in commands if command.category == category])

            logging.info(len(string))
            if len(string) < 1024:
                embed.add_field(
                    name=full_category,
                    value=string,
                    inline=False
                )

            else:
                embed.add_field(
                    name=category,
                    value=string[:1024].split('\n')[0],
                    inline=False
                )

                embed.add_field(
                    name='\u200b',
                    value=string[1024:].split('\n')[0],
                    inline=False
                )

        embed.set_footer(text="Use /help <command> for specific help on a command.",
                         icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=60&quality=lossless")

        await ctx.send(embed=embed)
    else:
        command = bot.get_command(command)
        if command is None:
            return await invis_embed(ctx, 'That command does not exist.')

        embed = discord.Embed(
            title='<:SettingIcon:1035353776460152892> Command Information | {}'.format(command.name),
            description=f"<:ArrowRight:1035003246445596774> {command.description.split('[')[0]}",
            color=0x2E3136
        )

        embed.set_footer(text="More help with a command can be asked in our support server.")

        embed.add_field(
            name='<:QMark:1035308059532202104> Usage',
            value='<:ArrowRight:1035003246445596774> `{}`'.format(command.usage),
            inline=False
        )

        if command.aliases:
            embed.add_field(
                name='<:Search:1035353785184288788> Aliases',
                value='<:ArrowRight:1035003246445596774> `{}`'.format(', '.join(command.aliases)),
                inline=False
            )

        await ctx.send(embed=embed)


@bot.hybrid_group(
    name='duty'
)
async def duty(ctx):
    await invis_embed(ctx, 'You have not picked a subcommand. Subcommand options: `on`, `off`, `time`, `void`')


@bot.hybrid_group(
    name="bolo"
)
async def bolo(ctx):
    pass


@bolo.command(
    name="create",
    aliases=["add"],
    description="Create a BOLO. [Punishments]",
    with_app_command=True
)
@is_staff()
async def bolo_create(ctx, user, *, reason):
    request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
    if request.status_code != 200:
        oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
        oldRequestJSON = oldRequest.json()
        if not oldRequest.status_code == 200:
            return await invis_embed(ctx, 'User does not exist.')
        Id = oldRequestJSON['Id']
        request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
        requestJson = request.json()

    else:
        requestJson = request.json()
        data = requestJson['data']

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        Embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            Embed.description = """
            <:ArrowRightW:1035023450592514048>**Warnings:** 0
            <:ArrowRightW:1035023450592514048>**Kicks:** 0
            <:ArrowRightW:1035023450592514048>**Bans:** 0

            `Banned:` <:ErrorIcon:1035000018165321808>
            """
        else:
            warnings = 0
            kicks = 0
            bans = 0
            for warningItem in user['warnings']:
                if warningItem['Guild'] == ctx.guild.id:
                    if warningItem['Type'] == "Warning":
                        warnings += 1
                    elif warningItem['Type'] == "Kick":
                        kicks += 1
                    elif warningItem['Type'] == "Ban":
                        bans += 1
                    elif warningItem['Type'] == "Temporary Ban":
                        bans += 1
            if bans != 0:
                banned = "<:CheckIcon:1035018951043842088>"
            else:
                banned = "<:ErrorIcon:1035000018165321808>"
            Embed.description = f"""
            <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
            <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
            <:ArrowRightW:1035023450592514048>**Bans:** {bans}

            `Banned:` {banned}
            """

        Embed.set_thumbnail(url=Headshot_URL)
        Embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')
        Embeds.append(Embed)

    if ctx.interaction:
        interaction = ctx.interaction
    else:
        interaction = ctx
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, show_page_director=False)

    async def bolo_function(ctx, menu):

        user = menu.message.embeds[0].title
        await menu.stop(disable_items=True)

        default_warning_item = {
            '_id': user.lower(),
            'warnings': [{
                'id': next(generator),
                "Type": "BOLO",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                "Guild": ctx.guild.id
            }]
        }

        singular_warning_item = {
            'id': next(generator),
            "Type": "BOLO",
            "Reason": reason,
            "Moderator": [ctx.author.name, ctx.author.id],
            "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
            "Guild": ctx.guild.id
        }

        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(ctx,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.')

        if not configItem['punishments']['enabled']:
            return await invis_embed(ctx,
                                     'This server has punishments disabled. Please run `/config change` to enable punishments.')

        embed = discord.Embed(title=user, color=0x2E3136)
        embed.set_thumbnail(url=menu.message.embeds[0].thumbnail.url)
        try:
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:staff:1035308057007230976> Staff Member",
                        value=f"<:ArrowRightW:1035023450592514048> {ctx.author.name}#{ctx.author.discriminator}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRightW:1035023450592514048> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type", value="<:ArrowRightW:1035023450592514048> BOLO",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason",
                        value=f"<:ArrowRightW:1035023450592514048> {reason}",
                        inline=False)

        try:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['customisation']['bolo_channel'])
        except:
            channel = None
        if not channel:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

        if not channel:
            return await invis_embed(ctx,
                                     'The channel in the configuration does not exist. Please tell the server owner to run `/config change` for the channel to be changed.')

        if not await bot.warnings.find_by_id(user.lower()):
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> BOLO Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s ban has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)
        await channel.send(embed=embed)

    async def task():
        await bolo_function(ctx, menu)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    async def cancelTask():
        await menu.message.edit(embed=discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        ))
        await menu.stop(disable_items=True)

    def cancelTaskWrapper():
        bot.loop.create_task(
            cancelTask()
        )

    followUp = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            taskWrapper
        )
    )
    cancelFollowup = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            cancelTaskWrapper
        )
    )

    menu.add_buttons([
        ViewButton(
            emoji="✅",
            custom_id=ViewButton.ID_CALLER,
            followup=followUp
        ),
        ViewButton(
            emoji="❎",
            custom_id=ViewButton.ID_CALLER,
            followup=cancelFollowup
        )
    ])

    try:
        menu.add_pages(Embeds)
        await menu.start()
    except:
        return await invis_embed(ctx,
                                 'This user does not exist on the Roblox platform. Please try again with a valid username.')


@bolo.command(
    name="lookup",
    aliases=["search", "find"],
    description="Searches for a user's BOLOs. [Punishments]",
    with_app_command=True
)
@is_staff()
async def bolo_lookup(ctx, *, user: str):
    data = requests.get(f'https://api.roblox.com/users/get-by-username?username={user}')
    if 'Id' not in data.json().keys():
        return await invis_embed(ctx,
                                 'This user does not exist on the Roblox platform. Please try again with a valid username.')
    Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
        data.json()['Id'])
    if not await bot.warnings.find_by_id(user.lower()):
        return await invis_embed(ctx, f'**{user}** does not have any BOLOs.')

    dataItem = await bot.warnings.find_by_id(user.lower())

    Embeds = []
    Embed = discord.Embed(title=user, color=0x2E3136)
    Embeds.append(Embed)
    Embed.set_thumbnail(url=Headshot_URL)

    for warningItem in dataItem['warnings']:
        if warningItem['Type'] == "BOLO" and warningItem['Guild'] == ctx.guild.id:
            Embed.add_field(name="<:WarningIcon:1035258528149033090> BOLO",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {warningItem['Reason']}\n<:ArrowRightW:1035023450592514048> **Type:** {warningItem['Type']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {warningItem['Moderator'][0]}\n<:ArrowRightW:1035023450592514048> **Time:** {warningItem['Time']}\n<:ArrowRightW:1035023450592514048> **ID:** {warningItem['id']}",
                            inline=False)
    try:
        await ctx.send(embeds=Embeds)
    except:
        return await invis_embed(ctx, f'**{user}** does not have any BOLOs.')


@duty.command(
    name="on",
    description="Allows for you to clock in. [Shift Management]",
    with_app_command=True,
)
@is_staff()
async def dutyon(ctx):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')
    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if not configItem['shift_management']['enabled']:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    if await bot.shifts.find_by_id(ctx.author.id):
        if 'data' in (await bot.shifts.find_by_id(ctx.author.id)).keys():
            var = (await bot.shifts.find_by_id(ctx.author.id))['data']
            for item in var:
                if item['guild'] == ctx.guild.id:
                    return await invis_embed(ctx, 'You are already on duty.')
        elif 'guild' in (await bot.shifts.find_by_id(ctx.author.id)).keys():
            if (await bot.shifts.find_by_id(ctx.author.id))['guild'] == ctx.guild.id:
                return await invis_embed(ctx, 'You are already on duty.')

    embed = discord.Embed(
        title=ctx.author.name,
        color=0x2E3136
    )

    try:
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text='Staff Logging Module')
    except:
        pass

    embed.add_field(
        name="<:MalletWhite:1035258530422341672> Type",
        value="<:ArrowRight:1035003246445596774> Clocking in.",
        inline=False
    )

    embed.add_field(
        name="<:Clock:1035308064305332224> Current Time",
        value=f"<:ArrowRight:1035003246445596774> <t:{int(ctx.message.created_at.timestamp())}>",
        inline=False
    )

    try:
        await bot.shifts.insert({
            '_id': ctx.author.id,
            'name': ctx.author.name,
            'data': [
                {
                    "guild": ctx.guild.id,
                    "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                }
            ]
        })
    except:
        if await bot.shifts.find_by_id(ctx.author.id):
            shift = await bot.shifts.find_by_id(ctx.author.id)
            if 'data' in shift.keys():
                newData = shift['data']
                newData.append({
                    "guild": ctx.guild.id,
                    "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                })
                await bot.shifts.update_by_id({
                    '_id': ctx.author.id,
                    'name': ctx.author.name,
                    'data': newData
                })
            elif 'data' not in shift.keys():
                await bot.shifts.update_by_id({
                    '_id': ctx.author.id,
                    'name': ctx.author.name,
                    'data': [
                        {
                            "guild": ctx.guild.id,
                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        },
                        {
                            "guild": shift['guild'],
                            "startTimestamp": shift['startTimestamp'],

                        }
                    ]
                })

    await shift_channel.send(embed=embed)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Success",
        description="<:ArrowRight:1035003246445596774> Your shift is now active.",
        color=0x71c15f
    )
    await ctx.send(embed=successEmbed)
    role = None

    if configItem['shift_management']['role']:
        if not isinstance(configItem['shift_management']['role'], list):
            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
        else:
            role = [discord.utils.get(ctx.guild.roles, id=role) for role in configItem['shift_management']['role']]

    if role:
        for rl in role:
            if not rl in ctx.author.roles:
                await ctx.author.add_roles(rl)


@bolo.command(
    name='void',
    description='Remove a warning from a user. [Punishments]',
    with_app_command=True
)
@is_staff()
async def bolo_void(ctx, id: str):
    try:
        id = int(id)
    except:
        return await invis_embed(ctx, '`id` is not a valid ID.')

    keyStorage = None
    selected_item = None
    selected_items = []
    item_index = 0

    for item in await bot.warnings.get_all():
        for index, _item in enumerate(item['warnings']):
            if _item['id'] == id:
                if _item['Type'] == "BOLO":
                    selected_item = _item
                    selected_items.append(_item)
                    parent_item = item
                    item_index = index
                    break

    if selected_item is None:
        return await invis_embed(ctx, 'That BOLO does not exist.')

    if selected_item['Guild'] != ctx.guild.id:
        return await invis_embed(ctx, 'You are trying to remove a BOLO that is not apart of this guild.')

    if len(selected_items) > 1:
        return await invis_embed(ctx,
                                 'There is more than one BOLO associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.')

    Moderator = discord.utils.get(ctx.guild.members, id=selected_item['Moderator'][1])
    if Moderator:
        Moderator = Moderator.mention
    else:
        Moderator = selected_item['Moderator'][0]

    embed = discord.Embed(
        title="<:MalletWhite:1035258530422341672> Remove BOLO",
        description=f"<:ArrowRightW:1035023450592514048> **User:** {parent_item['_id']}\n<:ArrowRightW:1035023450592514048> **Reason:** {selected_item['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {Moderator}\n<:ArrowRightW:1035023450592514048> **ID:** {selected_item['id']}\n",
        color=0x2E3136
    )

    view = RemoveWarning(ctx.author.id)
    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value:
        parent_item['warnings'].remove(selected_item)
        await bot.warnings.update_by_id(parent_item)


@duty.command(
    name="off",
    description="Allows for you to clock out. [Shift Management]",
    with_app_command=True,
)
@is_staff()
async def dutyoff(ctx):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')
    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    global_check = 0
    shift = None

    tempShift = await bot.shifts.find_by_id(ctx.author.id)
    if tempShift:
        if 'data' in tempShift.keys():
            if isinstance(tempShift['data'], list):
                for item in tempShift['data']:
                    if item['guild'] == ctx.guild.id:
                        global_check = 1
                        break
        elif "guild" in tempShift.keys():
            if tempShift['guild'] == ctx.guild.id:
                global_check += 1
    else:
        global_check = 0

    if global_check > 1:
        return await invis_embed(ctx,
                                 'You have more than one concurrent shift. This should be impossible. Contact Mikey for more information.')
    if global_check == 0:
        return await invis_embed(ctx, 'You have no concurrent shifts! Please clock in before clocking out.')

    if global_check == 1:
        tempShift = await bot.shifts.find_by_id(ctx.author.id)
        if tempShift:
            if 'data' in tempShift.keys():
                if isinstance(tempShift['data'], list):
                    for item in tempShift['data']:
                        if item['guild'] == ctx.guild.id:
                            shift = item
                            break
            elif "guild" in tempShift.keys():
                if tempShift['guild'] == ctx.guild.id:
                    shift = tempShift

    embed = discord.Embed(
        title=ctx.author.name,
        color=0x2E3136
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text='Staff Logging Module')

    embed.add_field(
        name="<:MalletWhite:1035258530422341672> Type",
        value="<:ArrowRight:1035003246445596774> Clocking out.",
        inline=False
    )

    embed.add_field(
        name="<:Clock:1035308064305332224> Elapsed Time",
        value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']))}",
        inline=False
    )

    time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
        shift['startTimestamp']).replace(tzinfo=None)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Shift Ended",
        description="<:ArrowRight:1035003246445596774> Your shift has now ended.",
        color=0x71c15f
    )

    await ctx.send(embed=successEmbed)
    await shift_channel.send(embed=embed)

    if not await bot.shift_storage.find_by_id(ctx.author.id):
        await bot.shift_storage.insert({
            '_id': ctx.author.id,
            'shifts': [
                {
                    'name': ctx.author.name,
                    'startTimestamp': shift['startTimestamp'],
                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                    'totalSeconds': time_delta.total_seconds(),
                    'guild': ctx.guild.id
                }],
            'totalSeconds': time_delta.total_seconds()

        })
    else:
        if "shifts" in await bot.shift_storage.find_by_id(ctx.author.id):
            if None not in dict(await bot.shift_storage.find_by_id(ctx.author.id)).values():

                await bot.shift_storage.update_by_id(
                    {
                        '_id': ctx.author.id,
                        'shifts': [(await bot.shift_storage.find_by_id(ctx.author.id))['shifts']].append(

                            {
                                'name': ctx.author.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id
                            }

                        ),
                        'totalSeconds': sum(
                            [(await bot.shift_storage.find_by_id(ctx.author.id))['shifts'][i]['totalSeconds'] for i in
                             range(len((await bot.shift_storage.find_by_id(ctx.author.id))['shifts']))])
                    }
                )
            else:
                await bot.shift_storage.update_by_id({
                    '_id': ctx.author.id,
                    'shifts': [
                        {
                            'name': ctx.author.name,
                            'startTimestamp': shift['startTimestamp'],
                            'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'totalSeconds': time_delta.total_seconds(),
                            'guild': ctx.guild.id
                        }],
                    'totalSeconds': time_delta.total_seconds()

                })

    if await bot.shifts.find_by_id(ctx.author.id):
        dataShift = await bot.shifts.find_by_id(ctx.author.id)
        if 'data' in dataShift.keys():
            if isinstance(dataShift['data'], list):
                for item in dataShift['data']:
                    if item['guild'] == ctx.guild.id:
                        dataShift['data'].remove(item)
                        break
        await bot.shifts.update_by_id(dataShift)

    role = None
    if configItem['shift_management']['role']:
        if not isinstance(configItem['shift_management']['role'], list):
            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
        else:
            role = [discord.utils.get(ctx.guild.roles, id=role) for role in configItem['shift_management']['role']]

    if role:
        for rl in role:
            if rl in ctx.author.roles:
                await ctx.author.remove_roles(rl)


@duty.command(
    name="time",
    description="Allows for you to check your shift time. [Shift Management]",
    with_app_command=True,
)
@is_staff()
async def dutytime(ctx):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if not configItem['shift_management']['enabled']:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')
    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if not configItem['shift_management']['enabled']:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    global_check = 0
    shift = None

    tempShift = await bot.shifts.find_by_id(ctx.author.id)
    if tempShift:
        if 'data' in tempShift.keys():
            if isinstance(tempShift['data'], list):
                for item in tempShift['data']:
                    if item['guild'] == ctx.guild.id:
                        global_check = 1
                        break
        elif "guild" in tempShift.keys():
            if tempShift['guild'] == ctx.guild.id:
                global_check += 1
    else:
        global_check = 0

    if global_check > 1:
        return await invis_embed(ctx,
                                 'You have more than one concurrent shift. This should be impossible. Contact Mikey for more information.')
    if global_check == 0:
        return await invis_embed(ctx,
                                 'You have no concurrent shifts! Please clock in before requesting shift estimation.')

    if global_check == 1:
        tempShift = await bot.shifts.find_by_id(ctx.author.id)
        if tempShift:
            if 'data' in tempShift.keys():
                if isinstance(tempShift['data'], list):
                    for item in tempShift['data']:
                        if item['guild'] == ctx.guild.id:
                            shift = item
                            break
            elif "guild" in tempShift.keys():
                if tempShift['guild'] == ctx.guild.id:
                    shift = tempShift

    embed = discord.Embed(
        title=ctx.author.name,
        color=await generate_random(ctx)
    )

    try:
        embed.set_footer(text="Staff Logging Module")
    except:
        pass

    embed.add_field(
        name="<:Clock:1035308064305332224> Elapsed Time",
        value="<:ArrowRight:1035003246445596774>" +
              str(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                  shift['startTimestamp']).replace(tzinfo=None)).split('.')[0])

    await ctx.send(embed=embed)


@duty.command(
    name="void",
    description="Allows for you to void your shift. [Shift Management]",
    with_app_command=True,
)
@is_staff()
async def dutyvoid(ctx):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if not configItem['shift_management']['enabled']:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')
    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
        role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if not configItem['shift_management']['enabled']:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    global_check = 0
    shift = None

    tempShift = await bot.shifts.find_by_id(ctx.author.id)
    if tempShift:
        if 'data' in tempShift.keys():
            if isinstance(tempShift['data'], list):
                for item in tempShift['data']:
                    if item['guild'] == ctx.guild.id:
                        global_check = 1
                        break
        elif "guild" in tempShift.keys():
            if tempShift['guild'] == ctx.guild.id:
                global_check += 1
    else:
        global_check = 0

    if global_check > 1:
        return await invis_embed(ctx,
                                 'You have more than one concurrent shift. This should be impossible. Contact Mikey for more information.')
    if global_check == 0:
        return await invis_embed(ctx,
                                 'You have no concurrent shifts! Please clock in before requesting shift cancelling.')
    if global_check == 1:
        tempShift = await bot.shifts.find_by_id(ctx.author.id)
        if tempShift:
            if 'data' in tempShift.keys():
                if isinstance(tempShift['data'], list):
                    for item in tempShift['data']:
                        if item['guild'] == ctx.guild.id:
                            shift = item
                            break
            elif "guild" in tempShift.keys():
                if tempShift['guild'] == ctx.guild.id:
                    shift = tempShift

    view = YesNoMenu(ctx.author.id)
    embed = discord.Embed(
        description=f"<:WarningIcon:1035258528149033090> **Are you sure you want to void your shift?** This is irreversible.",
        color=0x2E3136
    )
    embed.set_footer(text="Select 'Yes' to void your shift.")

    msg = await ctx.send(embed=embed, view=view)
    await view.wait()

    if not view.value:
        success = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This shift has not been voided.",
            color=0xff3c3c
        )
        return await ctx.send(embed=success)

    embed = discord.Embed(
        title=ctx.author.name,
        color=0x2E3136
    )

    try:
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
    except:
        pass
    embed.add_field(
        name="<:MalletWhite:1035258530422341672> Type",
        value=f"<:ArrowRight:1035003246445596774> Voided time",
        inline=False
    )

    embed.add_field(
        name="<:Clock:1035308064305332224> Elapsed Time",
        value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp'])).split('.')[0]}",
        inline=False
    )

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Shift Voided",
        description="<:ArrowRight:1035003246445596774> Shift has been voided successfully.",
        color=0x71c15f
    )

    embed.set_footer(text='Staff Logging Module')

    if await bot.shifts.find_by_id(ctx.author.id):
        dataShift = await bot.shifts.find_by_id(ctx.author.id)
        if 'data' in dataShift.keys():
            if isinstance(dataShift['data'], list):
                for item in dataShift['data']:
                    if item['guild'] == ctx.guild.id:
                        dataShift['data'].remove(item)
                        break
            await bot.shifts.update_by_id(dataShift)
        else:
            await bot.shifts.delete_by_id(dataShift)

    await shift_channel.send(embed=embed)
    await msg.edit(embed=successEmbed)
    role = None
    if configItem['shift_management']['role']:
        if not isinstance(configItem['shift_management']['role'], list):
            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
        else:
            role = [discord.utils.get(ctx.guild.roles, id=role) for role in configItem['shift_management']['role']]

    if role:
        for rl in role:
            if rl in ctx.author.roles:
                await ctx.author.remove_roles(rl)


@duty.command(
    name="forcevoid",
    aliases=["cancel"],
    description="Allows for you to void someone else's shift. [Shift Management]",
    with_app_command=True,
)
@is_management()
async def forcevoid(ctx, member: discord.Member):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')
    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    global_check = 0
    shift = None

    tempShift = await bot.shifts.find_by_id(member.id)
    if tempShift:
        if 'data' in tempShift.keys():
            if isinstance(tempShift['data'], list):
                for item in tempShift['data']:
                    if item['guild'] == ctx.guild.id:
                        global_check = 1
                        break
        elif "guild" in tempShift.keys():
            if tempShift['guild'] == ctx.guild.id:
                global_check += 1
    else:
        global_check = 0

    if global_check > 1:
        return await invis_embed(ctx,
                                 f'{member.display_name} has more than one concurrent shift. This should be impossible. Contact Mikey for more information.')
    if global_check == 0:
        return await invis_embed(ctx,
                                 f'{member.display_name} has no concurrent shifts! Please get them to clock in before requesting shift cancelling.')
    if global_check == 1:
        tempShift = await bot.shifts.find_by_id(member.id)
        if tempShift:
            if 'data' in tempShift.keys():
                if isinstance(tempShift['data'], list):
                    for item in tempShift['data']:
                        if item['guild'] == ctx.guild.id:
                            shift = item
                            break
            elif "guild" in tempShift.keys():
                if tempShift['guild'] == ctx.guild.id:
                    shift = tempShift

    view = YesNoMenu(ctx.author.id)
    embed = discord.Embed(
        description=f"<:WarningIcon:1035258528149033090> **Are you sure you want to void {member.display_name}'s shift?** This is irreversible.",
        color=0x2E3136
    )
    embed.set_footer(text="Select 'Yes' to continue.")

    msg = await ctx.send(embed=embed, view=view)
    await view.wait()

    if not view.value:
        success = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This shift has not been voided.",
            color=0xff3c3c
        )
        return await ctx.send(embed=success)

    embed = discord.Embed(
        title=member.name,
        color=0x2E3136
    )

    try:
        embed.set_thumbnail(url=member.display_avatar.url)
    except:
        pass
    embed.add_field(
        name="<:MalletWhite:1035258530422341672> Type",
        value=f"<:ArrowRight:1035003246445596774> Voided time, performed by ({ctx.author.display_name})",
        inline=False
    )

    embed.add_field(
        name="<:Clock:1035308064305332224> Elapsed Time",
        value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp'])).split('.')[0]}",
        inline=False
    )

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Shift Voided",
        description="<:ArrowRight:1035003246445596774> Shift has been voided successfully.",
        color=0x71c15f
    )

    embed.set_footer(text='Staff Logging Module')

    if await bot.shifts.find_by_id(ctx.author.id):
        dataShift = await bot.shifts.find_by_id(ctx.author.id)
        if 'data' in dataShift.keys():
            if isinstance(dataShift['data'], list):
                for item in dataShift['data']:
                    if item['guild'] == ctx.guild.id:
                        dataShift['data'].remove(item)
                        break
            await bot.shifts.update_by_id(dataShift)
        else:
            await bot.shifts.delete_by_id(dataShift)

    await shift_channel.send(embed=embed)
    await msg.edit(embed=successEmbed)
    role = None
    if configItem['shift_management']['role']:
        if not isinstance(configItem['shift_management']['role'], list):
            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
        else:
            role = [discord.utils.get(ctx.guild.roles, id=role) for role in configItem['shift_management']['role']]

    if role:
        for rl in role:
            if rl in ctx.author.roles:
                await ctx.author.remove_roles(rl)


@duty.command(
    name="modify",
    aliases=["mod"],
    description="Allows for you to modify someone else's shift. [Shift Management]",
    with_app_command=True,
)
@is_management()
async def modify(ctx, member: discord.Member):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')
    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if configItem['shift_management']['enabled'] == False:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    global_check = 0
    shift = None

    tempShift = await bot.shifts.find_by_id(member.id)
    if tempShift:
        if 'data' in tempShift.keys():
            if isinstance(tempShift['data'], list):
                for item in tempShift['data']:
                    if item['guild'] == ctx.guild.id:
                        global_check = 1
                        break
        elif "guild" in tempShift.keys():
            if tempShift['guild'] == ctx.guild.id:
                global_check += 1
    else:
        global_check = 0

    if global_check > 1:
        return await invis_embed(ctx,
                                 f'{member.display_name} has more than one concurrent shift. This should be impossible. Contact Mikey for more information.')
    if global_check == 0:
        return await invis_embed(ctx,
                                 f'{member.display_name} has no concurrent shifts! Please get them to clock in before requesting shift cancelling.')
    if global_check == 1:
        tempShift = await bot.shifts.find_by_id(member.id)
        if tempShift:
            if 'data' in tempShift.keys():
                if isinstance(tempShift['data'], list):
                    for item in tempShift['data']:
                        if item['guild'] == ctx.guild.id:
                            shift = item
                            break
            elif "guild" in tempShift.keys():
                if tempShift['guild'] == ctx.guild.id:
                    shift = tempShift

    view = ShiftModify(ctx.author.id)
    embed = discord.Embed(
        description=f"<:Clock:1035308064305332224> **What would you like to do to {member.display_name}'s current shift?**",
        color=0x2E3136
    )
    msg = await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value == "end":
        embed = discord.Embed(
            title=f"{member.name}#{member.discriminator}",
            color=0x2E3136
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text='Staff Logging Module')

        embed.add_field(
            name="<:MalletWhite:1035258530422341672> Type",
            value="<:ArrowRight:1035003246445596774> Clocking out.",
            inline=False
        )
        print(str(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)))
        print(td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)))
        print(ctx.message.created_at.replace(tzinfo=None))
        print(datetime.datetime.fromtimestamp(shift['startTimestamp']).replace(tzinfo=None))
        embed.add_field(
            name="<:Clock:1035308064305332224> Elapsed Time",
            value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']).replace(tzinfo=None))}",
            inline=False
        )

        time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Shift Ended",
            description=f"<:ArrowRight:1035003246445596774> {member.display_name}'s shift has now ended.",
            color=0x71c15f
        )

        await ctx.send(embed=successEmbed)
        await shift_channel.send(embed=embed)

        if not await bot.shift_storage.find_by_id(member.id):
            await bot.shift_storage.insert({
                '_id': member.id,
                'shifts': [
                    {
                        'name': member.name,
                        'startTimestamp': shift['startTimestamp'],
                        'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        'totalSeconds': time_delta.total_seconds(),
                        'guild': ctx.guild.id
                    }],
                'totalSeconds': time_delta.total_seconds()

            })
        else:
            if "shifts" in await bot.shift_storage.find_by_id(member.id):
                if not None in dict(await bot.shift_storage.find_by_id(member.id)).values():

                    await bot.shift_storage.update_by_id(
                        {
                            '_id': member.id,
                            'shifts': [(await bot.shift_storage.find_by_id(member.id))['shifts']].append(

                                {
                                    'name': member.name,
                                    'startTimestamp': shift['startTimestamp'],
                                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    'totalSeconds': time_delta.total_seconds(),
                                    'guild': ctx.guild.id
                                }

                            ),
                            'totalSeconds': sum(
                                [(await bot.shift_storage.find_by_id(member.id))['shifts'][i]['totalSeconds'] for i
                                 in
                                 range(len((await bot.shift_storage.find_by_id(member.id))['shifts']))])
                        }
                    )
                else:
                    await bot.shift_storage.update_by_id({
                        '_id': member.id,
                        'shifts': [
                            {
                                'name': member.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id
                            }],
                        'totalSeconds': time_delta.total_seconds()

                    })

        if await bot.shifts.find_by_id(member.id):
            dataShift = await bot.shifts.find_by_id(member.id)
            if 'data' in dataShift.keys():
                if isinstance(dataShift['data'], list):
                    for item in dataShift['data']:
                        if item['guild'] == ctx.guild.id:
                            dataShift['data'].remove(item)
                            break
                await bot.shifts.update_by_id(dataShift)
            else:
                await bot.shifts.delete_by_id(dataShift)
        role = None
        if configItem['shift_management']['role']:
            if not isinstance(configItem['shift_management']['role'], list):
                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
            else:
                role = [discord.utils.get(ctx.guild.roles, id=role) for role in configItem['shift_management']['role']]

        if role:
            for rl in role:
                if rl in member.roles:
                    await member.remove_roles(rl)
    elif view.value == "void":
        embed = discord.Embed(
            title=f"{member.name}#{member.discriminator}",
            color=0x2E3136
        )

        try:
            embed.set_thumbnail(url=member.display_avatar.url)
        except:
            pass
        embed.add_field(
            name="<:MalletWhite:1035258530422341672> Type",
            value=f"<:ArrowRight:1035003246445596774> Voided time, performed by ({ctx.author.display_name})",
            inline=False
        )

        embed.add_field(
            name="<:Clock:1035308064305332224> Elapsed Time",
            value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp'])).split('.')[0]}",
            inline=False
        )

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Shift Voided",
            description="<:ArrowRight:1035003246445596774> Shift has been voided successfully.",
            color=0x71c15f
        )

        embed.set_footer(text='Staff Logging Module')

        if await bot.shifts.find_by_id(member.id):
            dataShift = await bot.shifts.find_by_id(member.id)
            if 'data' in dataShift.keys():
                if isinstance(dataShift['data'], list):
                    for item in dataShift['data']:
                        if item['guild'] == ctx.guild.id:
                            dataShift['data'].remove(item)
                            break
                await bot.shifts.update_by_id(dataShift)
            else:
                await bot.shifts.delete_by_id(dataShift)

        await shift_channel.send(embed=embed)
        await msg.edit(embed=successEmbed)
        role = None
        if configItem['shift_management']['role']:
            if not isinstance(configItem['shift_management']['role'], list):
                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
            else:
                role = [discord.utils.get(ctx.guild.roles, id=role) for role in configItem['shift_management']['role']]

        if role:
            for rl in role:
                if rl in ctx.author.roles:
                    await ctx.author.remove_roles(rl)
    elif view.value == "add":
        timestamp = shift['startTimestamp']
        dT = datetime.datetime.fromtimestamp(timestamp)
        tD = None
        content = (
            await request_response(bot, ctx, "How much time would you like to add to the shift? (s/m/h/d)")).content
        content = content.strip()
        if content.endswith(('s', 'm', 'h', 'd')):
            full = None
            if content.endswith('s'):
                full = "seconds"
                num = int(content[:-1])
                tD = dT - datetime.timedelta(seconds=num)
            if content.endswith('m'):
                full = "minutes"
                num = int(content[:-1])
                tD = dT - datetime.timedelta(minutes=num)
            if content.endswith('h'):
                full = "hours"
                num = int(content[:-1])
                tD = dT - datetime.timedelta(hours=num)
            if content.endswith('d'):
                full = "days"
                num = int(content[:-1])
                tD = dT - datetime.timedelta(days=num)
            newTimestamp = tD.timestamp()
            shift['startTimestamp'] = newTimestamp
            if await bot.shifts.find_by_id(member.id):
                dataShift = await bot.shifts.find_by_id(member.id)
                if 'data' in dataShift.keys():
                    if isinstance(dataShift['data'], list):
                        for index, item in enumerate(dataShift['data']):
                            if item['guild'] == ctx.guild.id:
                                dataShift['data'][index] = shift
                        await bot.shifts.update_by_id(dataShift)
                else:
                    await bot.shifts.update_by_id(shift)
            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Added time",
                description=f"<:ArrowRight:1035003246445596774> **{num} {full}** have been added to {member.display_name}'s shift.",
                color=0x71c15f
            )
            await ctx.send(embed=successEmbed)
        else:
            return await invis_embed(ctx, "Invalid time format. (e.g. 120m)")
    elif view.value == "remove":
        timestamp = shift['startTimestamp']
        dT = datetime.datetime.fromtimestamp(timestamp)
        tD = None
        content = (
            await request_response(bot, ctx,
                                   "How much time would you like to remove from the shift? (s/m/h/d)")).content
        content = content.strip()
        if content.endswith(('s', 'm', 'h', 'd')):
            full = None
            if content.endswith('s'):
                full = "seconds"
                num = int(content[:-1])
                tD = dT + datetime.timedelta(seconds=num)
            if content.endswith('m'):
                full = "minutes"
                num = int(content[:-1])
                tD = dT + datetime.timedelta(minutes=num)
            if content.endswith('h'):
                full = "hours"
                num = int(content[:-1])
                tD = dT + datetime.timedelta(hours=num)
            if content.endswith('d'):
                full = "days"
                num = int(content[:-1])
                tD = dT + datetime.timedelta(days=num)
            newTimestamp = tD.timestamp()
            shift['startTimestamp'] = newTimestamp
            if await bot.shifts.find_by_id(member.id):
                dataShift = await bot.shifts.find_by_id(member.id)
                if 'data' in dataShift.keys():
                    if isinstance(dataShift['data'], list):
                        for index, item in enumerate(dataShift['data']):
                            if item['guild'] == ctx.guild.id:
                                dataShift['data'][index] = shift
                        await bot.shifts.update_by_id(dataShift)
                else:
                    await bot.shifts.update_by_id(shift)
            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Removed time",
                description=f"<:ArrowRight:1035003246445596774> **{num} {full}** have been removed from {member.display_name}'s shift.",
                color=0x71c15f
            )
            await ctx.send(embed=successEmbed)

        else:
            return await invis_embed(ctx, "Invalid time format. (e.g. 120m)")


@duty.autocomplete('setting')
async def autocomplete_callback(interaction: discord.Interaction, current: str):
    # Do stuff with the "current" parameter, e.g. querying it search results...

    # Then return a list of app_commands.Choice
    return [
        app_commands.Choice(name='Go on duty', value='on'),
        app_commands.Choice(name='Go off duty', value='off'),
        app_commands.Choice(name='Estimate time', value='time'),
        app_commands.Choice(name='Cancel shift', value='cancel'),
    ]


@bot.hybrid_group(
    name='loa',
    description='File a Leave of Absence request [Staff Management]',
    with_app_command=True,
)
async def loa(ctx, time, *, reason):
    await ctx.invoke(bot.get_command('loa request'), time=time, reason=reason)


@loa.command(
    name='request',
    description='File a Leave of Absence request [Staff Management]',
    with_app_command=True
)
async def loarequest(ctx, time, *, reason):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        timeObj = reason.split(' ')[-1]
    except:
        timeObj = ""
    reason = list(reason)

    if not time.endswith(('h', 'm', 's', 'd', 'w')):
        reason.insert(0, time)
        if not timeObj.endswith(('h', 'm', 's', 'd', 'w')):
            return await invis_embed(ctx,
                                     'A time must be provided at the start or at the end of the command. Example: `/loa 12h Going to walk my shark` / `/loa Mopping the ceiling 12h`')
        else:
            time = timeObj
            reason.pop()

    if time.endswith('s'):
        time = int(removesuffix(time, 's'))
    elif time.endswith('m'):
        time = int(removesuffix(time, 'm')) * 60
    elif time.endswith('h'):
        time = int(removesuffix(time, 'h')) * 60 * 60
    elif time.endswith('d'):
        time = int(removesuffix(time, 'd')) * 60 * 60 * 24
    elif time.endswith('w'):
        time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7

    startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
    endTimestamp = int(startTimestamp + time)

    Embed = discord.Embed(
        title="Leave of Absence",
        color=0x2E3136
    )

    try:
        Embed.set_thumbnail(url=ctx.author.display_avatar.url)
        Embed.set_footer(text="Staff Logging Module")

    except:
        pass
    Embed.add_field(
        name="<:staff:1035308057007230976> Staff Member",
        value=f"<:ArrowRight:1035003246445596774>{ctx.author.name}",
        inline=False
    )

    Embed.add_field(
        name="<:Resume:1035269012445216858> Start",
        value=f'<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>',
        inline=False
    )

    Embed.add_field(
        name="<:Pause:1035308061679689859> End",
        value=f'<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>',
        inline=False
    )

    reason = ''.join(reason)

    Embed.add_field(
        name='<:QMark:1035308059532202104> Reason',
        value=f'<:ArrowRight:1035003246445596774>{reason}',
        inline=False
    )

    settings = await bot.settings.find_by_id(ctx.guild.id)
    try:
        management_role = settings['staff_management']['management_role']
    except:
        return await invis_embed(ctx,
                                 "The management role has not been set up yet. Please run `/setup` to set up the server.")
    try:
        loa_role = settings['staff_management']['loa_role']
    except:
        return await invis_embed(ctx,
                                 "The LOA role has not been set up yet. Please run `/config change` to add the LOA role.")

    view = LOAMenu(bot, management_role, loa_role, ctx.author.id)

    channel = discord.utils.get(ctx.guild.channels, id=configItem['staff_management']['channel'])
    msg = await channel.send(embed=Embed, view=view)

    example_schema = {"_id": f"{ctx.author.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
                      "user_id": ctx.author.id, "guild_id": ctx.guild.id, "message_id": msg.id, "type": "LoA",
                      "expiry": int(endTimestamp),
                      "expired": False, "accepted": False, "denied": False, "reason": ''.join(reason)}

    await bot.loas.insert(example_schema)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Sent LoA Request",
        description="<:ArrowRight:1035003246445596774> I've sent your LoA request to a Management member of this server.",
        color=0x71c15f
    )
    await ctx.send(embed=successEmbed)


@loa.command(
    name='void',
    description='Cancel a Leave of Absence request [Staff Management]',
    with_app_command=True
)
@is_management()
async def loavoid(ctx, user: discord.Member = None):
    if user == None:
        user = ctx.author

    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        loa_role = configItem['staff_management']['loa_role']
    except:
        return await invis_embed(ctx,
                                 "The LOA role has not been set up yet. Please run `/config change` to add the LOA role.")

    loa = None
    for l in await bot.loas.get_all():
        if l['user_id'] == user.id and l['guild_id'] == ctx.guild.id and l['type'] == "LoA" and l['expired'] == False:
            loa = l
            break

    if loa is None:
        return await invis_embed(ctx, f"{user.display_name} is currently not on LoA.")

    embed = discord.Embed(
        description=f'<:WarningIcon:1035258528149033090> **Are you sure you would like to clear {user.display_name}\'s LoA?**\n**End date:** <t:{loa["expiry"]}>',
        color=0x2E3136)
    embed.set_footer(text="Staff Management Module")
    view = YesNoMenu(ctx.author.id)
    await ctx.send(embed=embed, view=view)
    await view.wait()
    print(view.value)
    if view.value == True:
        await bot.loas.delete_by_id(loa['_id'])
        await invis_embed(ctx, f'**{user.display_name}\'s** LoA has been voided.')
        success = discord.Embed(
            title=f"<:ErrorIcon:1035000018165321808> {loa['type']} Voided",
            description=f"<:ArrowRightW:1035023450592514048>{ctx.author.mention} has voided your {loa['type']}.",
            color=0xff3c3c
        )
        success.set_footer(text="Staff Management Module")
        try:
            await ctx.guild.get_member(loa['user_id']).send(embed=success)
            if loa_role in [role.id for role in user.roles]:
                await user.remove_roles(discord.utils.get(ctx.guild.roles, id=loa_role))
        except:
            await invis_embed(ctx, 'Could not remove the LOA role from the user.')

    else:
        return await invis_embed(ctx, 'Cancelled.')


@bot.hybrid_group(
    name='ra',
    description='File a Leave of Absence request [Staff Management]',
    with_app_command=True,
)
async def ra(ctx, time, *, reason):
    pass


@ra.command(
    name='request',
    description='File a Reduced Activity request [Staff Management]',
    with_app_command=True
)
async def rarequest(ctx, time, *, reason):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        timeObj = reason.split(' ')[-1]
    except:
        timeObj = ""
    reason = list(reason)

    if not time.endswith(('h', 'm', 's', 'd', 'w')):
        reason.insert(0, time)
        if not timeObj.endswith(('h', 'm', 's', 'd', 'w')):
            return await invis_embed(ctx,
                                     'A time must be provided at the start or at the end of the command. Example: `/ra 12h Going to walk my shark` / `/ra Mopping the ceiling 12h`')
        else:
            time = timeObj
            reason.pop()

    if time.endswith('s'):
        time = int(removesuffix(time, 's'))
    elif time.endswith('m'):
        time = int(removesuffix(time, 'm')) * 60
    elif time.endswith('h'):
        time = int(removesuffix(time, 'h')) * 60 * 60
    elif time.endswith('d'):
        time = int(removesuffix(time, 'd')) * 60 * 60 * 24
    elif time.endswith('w'):
        time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7

    startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
    endTimestamp = int(startTimestamp + time)

    Embed = discord.Embed(
        title="Reduced Activity",
        color=0x2E3136
    )

    try:
        Embed.set_thumbnail(url=ctx.author.display_avatar.url)
        Embed.set_footer(text="Staff Logging Module")

    except:
        pass
    Embed.add_field(
        name="<:staff:1035308057007230976> Staff Member",
        value=f"<:ArrowRight:1035003246445596774>{ctx.author.name}",
        inline=False
    )

    Embed.add_field(
        name="<:Resume:1035269012445216858> Start",
        value=f'<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>',
        inline=False
    )

    Embed.add_field(
        name="<:Pause:1035308061679689859> End",
        value=f'<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>',
        inline=False
    )

    reason = ''.join(reason)

    Embed.add_field(
        name='<:QMark:1035308059532202104> Reason',
        value=f'<:ArrowRight:1035003246445596774>{reason}',
        inline=False
    )

    settings = await bot.settings.find_by_id(ctx.guild.id)
    try:
        management_role = settings['staff_management']['management_role']
    except:
        return await invis_embed(ctx,
                                 "The management role has not been set up yet. Please run `/setup` to set up the server.")
    try:
        loa_role = settings['staff_management']['ra_role']
    except:
        return await invis_embed(ctx,
                                 "The RA role has not been set up yet. Please run `/config change` to add the RA role.")

    view = LOAMenu(bot, management_role, loa_role, ctx.author.id)

    channel = discord.utils.get(ctx.guild.channels, id=configItem['staff_management']['channel'])
    msg = await channel.send(embed=Embed, view=view)

    example_schema = {"_id": f"{ctx.author.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
                      "user_id": ctx.author.id, "guild_id": ctx.guild.id, "message_id": msg.id, "type": "RA",
                      "expiry": int(endTimestamp),
                      "expired": False, "accepted": False, "denied": False, "reason": ''.join(reason)}

    await bot.loas.insert(example_schema)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Sent RA Request",
        description="<:ArrowRight:1035003246445596774> I've sent your LoA request to a Management member of this server.",
        color=0x71c15f
    )
    await ctx.send(embed=successEmbed)


@ra.command(
    name='void',
    description='Cancel a Reduced Activity request [Staff Management]',
    with_app_command=True
)
@is_management()
async def loavoid(ctx, user: discord.Member = None):
    if user == None:
        user = ctx.author

    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        ra_role = configItem['staff_management']['ra_role']
    except:
        return await invis_embed(ctx,
                                 "The RA role has not been set up yet. Please run `/config change` to add the RA role.")

    ra = None
    for l in await bot.loas.get_all():
        if l['user_id'] == user.id and l['guild_id'] == ctx.guild.id and l['type'] == "RA" and l['expired'] == False:
            ra = l
            break

    if ra is None:
        return await invis_embed(ctx, f"{user.display_name} is currently not on RA.")

    embed = discord.Embed(
        description=f'<:WarningIcon:1035258528149033090> **Are you sure you would like to clear {user.display_name}\'s LoA?**\n**End date:** <t:{ra["expiry"]}>',
        color=0x2E3136)
    embed.set_footer(text="Staff Management Module")
    view = YesNoMenu(ctx.author.id)
    await ctx.send(embed=embed, view=view)
    await view.wait()
    print(view.value)
    if view.value == True:
        await bot.loas.delete_by_id(ra['_id'])
        await invis_embed(ctx, f'**{user.display_name}\'s** LoA has been voided.')
        success = discord.Embed(
            title=f"<:ErrorIcon:1035000018165321808> {ra['type']} Voided",
            description=f"<:ArrowRightW:1035023450592514048>{ctx.author.mention} has voided your {ra['type']}.",
            color=0xff3c3c
        )
        success.set_footer(text="Staff Management Module")
        try:
            await ctx.guild.get_member(loa['user_id']).send(embed=success)
            if ra_role in [role.id for role in user.roles]:
                await user.remove_roles(discord.utils.get(ctx.guild.roles, id=ra_role))
        except:
            await invis_embed(ctx, 'Could not remove the RA role from the user.')

    else:
        return await invis_embed(ctx, 'Cancelled.')


# context menus
@bot.tree.context_menu(name='Force end shift')
@is_management()
async def force_end_shift(interaction: discord.Interaction, member: discord.Member):
    try:
        configItem = await bot.settings.find_by_id(interaction.guild.id)
    except:
        return await int_invis_embed(interaction,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.',
                                     ephemeral=True)

    shift = await bot.shifts.find_by_id(member.id)
    if configItem['shift_management']['enabled'] == False:
        return await int_invis_embed(interaction, 'Shift management is not enabled on this server.',
                                     ephemeral=True)
    try:
        shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await int_invis_embed(interaction, 'Shift management channel not found.', ephemeral=True)

    management_role = discord.utils.get(interaction.guild.roles, id=configItem['staff_management']['management_role'])
    if not management_role in interaction.user.roles:
        if not interaction.user.guild_permissions.manage_guild:
            raise discord.ext.commands.CheckFailure

    if shift is None:
        return await int_invis_embed(interaction, 'This member is not currently on shift.', ephemeral=True)

    if 'data' in shift.keys():
        in_guild = False
        for guild in shift['data']:
            if guild['guild'] == interaction.guild.id:
                shift = guild
                in_guild = True
                break

        if in_guild == False:
            return await int_invis_embed(interaction, 'This member is not currently on shift.', ephemeral=True)
    elif shift['guild'] != interaction.guild.id:
        return await int_invis_embed(interaction, 'This member is not currently on shift.', ephemeral=True)

    view = YesNoMenu(interaction.user.id)
    await int_invis_embed(interaction, f'Are you sure you want to force end the shift of {member.mention}?',
                          view=view, ephemeral=True)
    await view.wait()

    if view.value == False:
        return await int_invis_embed(interaction, 'Cancelled.', ephemeral=True)
    elif view.value == None:
        return await int_invis_embed(interaction, 'Timed out.', ephemeral=True)
    elif view.value == True:
        time_delta = interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)

        embed = discord.Embed(title=member.name, color=0x2E3136)
        try:
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value="<:ArrowRight:1035003246445596774> Clocking out.", inline=False)
        embed.add_field(name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']).replace(tzinfo=None)).split('.')[0]}",
                        inline=False)

        if not await bot.shift_storage.find_by_id(member.id):
            await bot.shift_storage.insert({
                '_id': member.id,
                'shifts': [
                    {
                        'name': member.name,
                        'startTimestamp': shift['startTimestamp'],
                        'endTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
                        'totalSeconds': time_delta.total_seconds(),
                        'guild': interaction.guild.id
                    }],
                'totalSeconds': time_delta.total_seconds()

            })
        else:
            logging.info((await bot.shift_storage.find_by_id(member.id))['shifts'])
            await bot.shift_storage.update_by_id(
                {
                    '_id': member.id,
                    'shifts': [(await bot.shift_storage.find_by_id(member.id))['shifts']].append(

                        {
                            'name': member.name,
                            'startTimestamp': shift['startTimestamp'],
                            'endTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
                            'totalSeconds': time_delta.total_seconds(),
                            'guild': interaction.guild.id
                        }

                    ),
                    'totalSeconds': sum(
                        [(await bot.shift_storage.find_by_id(member.id))['shifts'][i]['totalSeconds'] for i in
                         range(len((await bot.shift_storage.find_by_id(member.id))['shifts'] or []))])
                }
            )

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description=f"<:ArrowRight:1035003246445596774> {member.mention}'s shift has now ended.",
            color=0x71c15f
        )

        await interaction.edit_original_response(embed=successEmbed)
        logging.info(await bot.shifts.find_by_id(member.id))
        if await bot.shifts.find_by_id(member.id):
            dataShift = await bot.shifts.find_by_id(member.id)
            if 'data' in dataShift.keys():
                if isinstance(dataShift['data'], list):
                    for item in dataShift['data']:
                        if item['guild'] == interaction.guild.id:
                            dataShift['data'].remove(item)
                            break
                await bot.shifts.update_by_id(dataShift)
            else:
                await bot.shifts.delete_by_id(member.id)
        await shift_channel.send(embed=embed)
        role = None
        if configItem['shift_management']['role']:
            if not isinstance(configItem['shift_management']['role'], list):
                role = [discord.utils.get(interaction.guild.roles, id=configItem['shift_management']['role'])]
            else:
                role = [discord.utils.get(interaction.guild.roles, id=role) for role in
                        configItem['shift_management']['role']]

        if role:
            for rl in role:
                if rl in member.roles:
                    await member.remove_roles(rl)


@bot.hybrid_group(
    name='reminders'
)
@is_management()
async def reminders(ctx):
    pass


@reminders.command(
    name="add",
    description="Add a reminder. [Reminders]",
)
@is_management()
async def add(ctx):
    Data = await bot.reminders.find_by_id(ctx.guild.id)
    if Data is None:
        Data = {
            '_id': ctx.guild.id,
            "reminders": []
        }

    embed = discord.Embed(title="<:Resume:1035269012445216858> Add a reminder", color=0x2E3136)
    for item in Data['reminders']:
        embed.add_field(name=f"<:Clock:1035308064305332224> {item['name']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Interval:** {item['interval']}s\n<:ArrowRightW:1035023450592514048> **Channel:** {item['channel']}\n<:ArrowRightW:1035023450592514048> **Message:** `{item['message']}`\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}\n<:ArrowRightW:1035023450592514048> **Last Completed:** <t:{int(item['lastTriggered'])}>",
                        inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name="<:Clock:1035308064305332224> No reminders",
                        value="<:ArrowRightW:1035023450592514048> No reminders have been added.", inline=False)

    view = AddReminder(ctx.author.id)

    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value == "create":
        name = (await request_response(bot, ctx,
                                       "What would you like to name this reminder?")).content

        time = (await request_response(bot, ctx,
                                       "What would you like you like the interval to be? (e.g. 5m)")).content

        if time.endswith('s'):
            time = int(removesuffix(time, 's'))
        elif time.endswith('m'):
            time = int(removesuffix(time, 'm')) * 60
        elif time.endswith('h'):
            time = int(removesuffix(time, 'h')) * 60 * 60
        elif time.endswith('d'):
            time = int(removesuffix(time, 'd')) * 60 * 60 * 24
        elif time.endswith('w'):
            time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7
        else:
            return await invis_embed(ctx, 'You have not provided a correct suffix. (s/m/h/d)')

        message = (await request_response(bot, ctx,
                                          "What would you like you like the message to be? (e.g. `Get Active!`)")).content

        channel = (await request_response(bot, ctx,
                                          "What would you like you like the channel to be in? (e.g. `#general`)")).content

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be mentioned?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")
        await ctx.send(embed=embed, view=view)
        roleObject = None
        await view.wait()
        if view.value == True:
            role = (await request_response(bot, ctx,
                                           'What role would you like to be mentioned?')).content
            if ',' in role:
                roleObject = []
                for rol in role.split(','):
                    rol = role.strip()
                    roleObject.append(await discord.ext.commands.RoleConverter().convert(ctx, rol))
            else:
                roleObject = [await discord.ext.commands.RoleConverter().convert(ctx, role)]

        try:
            channel = await commands.TextChannelConverter().convert(ctx, channel)
        except:
            return await invis_embed(ctx, 'You have not provided a correct channel.')

        if roleObject:
            Data['reminders'].append({
                "id": next(generator),
                "name": name,
                "interval": time,
                "message": message,
                "channel": channel.id,
                "role": [role.id for role in roleObject],
                "lastTriggered": 0
            })
        else:
            Data['reminders'].append({
                "id": next(generator),
                "name": name,
                "interval": time,
                "message": message,
                "channel": channel.id,
                "role": 0,
                "lastTriggered": 0
            })
        await bot.reminders.upsert(Data)
        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Reminder Added",
            description="<:ArrowRight:1035003246445596774> Your reminder has been added successfully.",
            color=0x71c15f
        )
        await ctx.send(embed=successEmbed)


@reminders.command(
    name="remove",
    description="Remove a reminder. [Reminders]",
)
@is_management()
async def remove(ctx):
    Data = await bot.reminders.find_by_id(ctx.guild.id)
    if Data is None:
        Data = {
            '_id': ctx.guild.id,
            "reminders": []
        }

    embed = discord.Embed(title="<:Resume:1035269012445216858> Add a reminder", color=0x2E3136)
    for item in Data['reminders']:
        embed.add_field(name=f"<:Clock:1035308064305332224> {item['name']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Interval:** {item['interval']}s\n<:ArrowRightW:1035023450592514048> **Channel:** {item['channel']}\n<:ArrowRightW:1035023450592514048> **Message:** `{item['message']}`\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}\n<:ArrowRightW:1035023450592514048> **Last Completed:** <t:{int(item['lastTriggered'])}>",
                        inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name="<:Clock:1035308064305332224> No reminders",
                        value="<:ArrowRightW:1035023450592514048> No reminders have been added.", inline=False)

    view = RemoveReminder(ctx.author.id)

    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value == "delete":
        name = (await request_response(bot, ctx,
                                       "What reminder would you like to delete? (e.g. `1`)\n*Specify the ID to delete the reminder.*")).content

        for item in Data['reminders']:
            if item['id'] == int(name):
                Data['reminders'].remove(item)
                await bot.reminders.upsert(Data)
                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Reminder Removed",
                    description="<:ArrowRight:1035003246445596774> Your reminder has been removed successfully.",
                    color=0x71c15f
                )
                return await ctx.send(embed=successEmbed)


@bot.tree.context_menu(name='Force start shift')
@is_management()
async def force_start_shift(interaction: discord.Interaction, member: discord.Member):
    try:
        configItem = await bot.settings.find_by_id(interaction.guild.id)
    except:
        return await int_invis_embed(interaction,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.',
                                     ephemeral=True)

    shift = await bot.shifts.find_by_id(member.id)
    if configItem['shift_management']['enabled'] == False:
        return await int_invis_embed(interaction, 'Shift management is not enabled on this server.',
                                     ephemeral=True)

    try:
        shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await int_invis_embed(interaction, 'Shift management channel not found.', ephemeral=True)

    management_role = discord.utils.get(interaction.guild.roles, id=configItem['staff_management']['management_role'])
    if not management_role in interaction.user.roles:
        if not interaction.user.guild_permissions.manage_guild:
            raise discord.ext.commands.CheckFailure

    if shift is not None:
        if 'data' in shift.keys():
            in_guild = False
            for guild in shift['data']:
                if guild["guild"] == interaction.guild.id:
                    in_guild = True

            if in_guild:
                return await int_invis_embed(interaction, 'This member is currently on shift.', ephemeral=True)
        else:
            return await int_invis_embed(interaction, 'This member is currently on shift.', ephemeral=True)

    view = YesNoMenu(interaction.user.id)
    await int_invis_embed(interaction, f'Are you sure you want to force start the shift of {member.mention}?',
                          view=view, ephemeral=True)
    await view.wait()

    if view.value == False:
        return await int_invis_embed(interaction, 'Cancelled.', ephemeral=True)
    elif view.value == None:
        return await int_invis_embed(interaction, 'Timed out.', ephemeral=True)
    elif view.value == True:

        embed = discord.Embed(title=member.name, color=0x2E3136)
        try:
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")
        except:
            pass

        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value="<:ArrowRight:1035003246445596774> Clocking in.", inline=False)
        embed.add_field(name="<:Clock:1035308064305332224> Current Time",
                        value=f"<:ArrowRight:1035003246445596774> <t:{int(interaction.created_at.timestamp())}>",
                        inline=False)

        try:
            await bot.shifts.insert({
                '_id': member.id,
                'name': member.name,
                'data': [
                    {
                        "guild": interaction.guild.id,
                        "startTimestamp": interaction.created_at.replace(tzinfo=None).timestamp(),
                    }
                ]
            })
        except:
            if await bot.shifts.find_by_id(member.id):
                shift = await bot.shifts.find_by_id(member.id)
                if 'data' in shift.keys():
                    newData = shift['data']
                    newData.append({
                        "guild": interaction.guild.id,
                        "startTimestamp": interaction.created_at.replace(tzinfo=None).timestamp(),
                    })
                    await bot.shifts.update_by_id({
                        '_id': member.id,
                        'name': member.name,
                        'data': newData
                    })
                elif 'data' not in shift.keys():
                    await bot.shifts.update_by_id({
                        '_id': member.id,
                        'name': member.name,
                        'data': [
                            {
                                "guild": interaction.guild.id,
                                "startTimestamp": interaction.created_at.replace(tzinfo=None).timestamp(),
                            },
                            {
                                "guild": shift['guild'],
                                "startTimestamp": shift['startTimestamp'],

                            }
                        ]
                    })

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description=f"<:ArrowRight:1035003246445596774> {member.mention}'s shift is now active.",
            color=0x71c15f
        )
        await interaction.edit_original_response(embed=successEmbed)

        await shift_channel.send(embed=embed)
        role = None
        if configItem['shift_management']['role']:
            if not isinstance(configItem['shift_management']['role'], list):
                role = [discord.utils.get(interaction.guild.roles, id=configItem['shift_management']['role'])]
            else:
                role = [discord.utils.get(interaction.guild.roles, id=role) for role in
                        configItem['shift_management']['role']]

        if role:
            for rl in role:
                if not rl in member.roles:
                    await member.add_roles(rl)


@bot.tree.context_menu(name='Get shift time')
@is_management()
async def get_shift_time(interaction: discord.Interaction, member: discord.Member):
    try:
        configItem = await bot.settings.find_by_id(interaction.guild.id)
    except:
        return await int_invis_embed(interaction,
                                     'The server has not been set up yet. Please run `/setup` to set up the server.',
                                     ephemeral=True)

    shift = await bot.shifts.find_by_id(member.id)
    if shift:
        in_guild = False
        if 'data' in shift.keys():
            for item in shift['data']:
                if item['guild'] == interaction.guild.id:
                    in_guild = True
                    shift = item

    if configItem['shift_management']['enabled'] == False:
        return await int_invis_embed(interaction, 'Shift management is not enabled on this server.',
                                     ephemeral=True)
    try:
        shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await int_invis_embed(interaction, 'Shift management channel not found.', ephemeral=True)

    management_role = discord.utils.get(interaction.guild.roles, id=configItem['staff_management']['management_role'])
    if not management_role in interaction.user.roles:
        if not interaction.user.guild_permissions.manage_guild:
            raise discord.ext.commands.CheckFailure

    if shift is None:
        return await int_invis_embed(interaction, 'This member is not currently on shift.', ephemeral=True)
    if not in_guild:
        return await int_invis_embed(interaction, 'This member is not currently on shift.', ephemeral=True)

    await int_invis_embed(interaction,
                          f'{member.display_name} has been on-shift for `{td_format(datetime.datetime.now() - datetime.datetime.fromtimestamp(shift["startTimestamp"])).split(".")[0]}`.',
                          ephemeral=True)


# context menus
@bot.tree.context_menu(name='Void shift')
@is_management()
async def force_void_shift(interaction: discord.Interaction, member: discord.Member):
    try:
        configItem = await bot.settings.find_by_id(interaction.guild.id)
    except:
        return await interaction.response.send_message(
            'The server has not been set up yet. Please run `/setup` to set up the server.', ephemeral=True)

    shift = await bot.shifts.find_by_id(member.id)
    if shift:
        in_guild = False
        if 'data' in shift.keys():
            for item in shift['data']:
                if item['guild'] == interaction.guild.id:
                    in_guild = True
                    shift = item

    if configItem['shift_management']['enabled'] == False:
        return await interaction.response.send_message('Shift management is not enabled on this server.',
                                                       ephemeral=True)
    try:
        shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await int_invis_embed(interaction, 'Shift management channel not found.')

    management_role = discord.utils.get(interaction.guild.roles, id=configItem['staff_management']['management_role'])
    if not management_role in interaction.user.roles:
        if not interaction.user.guild_permissions.manage_guild:
            raise discord.ext.commands.CheckFailure

    if shift is None:
        return await int_invis_embed(interaction, 'This member is not currently on shift.')
    if not in_guild:
        return await int_invis_embed(interaction, 'This member is not currently on shift.')

    view = YesNoMenu(interaction.user.id)
    embed = discord.Embed(
        description=f"<:WarningIcon:1035258528149033090> **Are you sure you want to void {member.mention}'s shift?** This is irreversible.",
        color=0x2E3136
    )
    embed.set_footer(text="Select 'Yes' to void the shift.")

    await interaction.response.send_message(embed=embed, view=view)
    await view.wait()

    if view.value == False:
        return await interaction.response.send_message('Cancelled.', ephemeral=True)
    elif view.value == None:
        return await interaction.response.send_message('Timed out.', ephemeral=True)
    elif view.value == True:

        embed = discord.Embed(title=member.name, color=0x2E3136)
        try:
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text='Staff Logging Module')
        except:
            pass

        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value=f"<:ArrowRight:1035003246445596774> Voided time, performed by ({interaction.user.mention}).",
                        inline=False)
        embed.add_field(name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']).replace(tzinfo=None))}",
                        inline=False)

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description=f"<:ArrowRight:1035003246445596774> {member.mention}'s shift has been voided.",
            color=0x71c15f
        )

        await interaction.edit_original_response(embed=successEmbed)
        logging.info(await bot.warnings.find_by_id(member.id))
        if await bot.shifts.find_by_id(member.id):
            dataShift = await bot.shifts.find_by_id(member.id)
            if 'data' in dataShift.keys():
                if isinstance(dataShift['data'], list):
                    for item in dataShift['data']:
                        if item['guild'] == interaction.guild.id:
                            dataShift['data'].remove(item)
                            break
                await bot.shifts.update_by_id(dataShift)
            else:
                await bot.shifts.delete_by_id(dataShift)
        await shift_channel.send(embed=embed)
        role = None
        if configItem['shift_management']['role']:
            if not isinstance(configItem['shift_management']['role'], list):
                role = [discord.utils.get(interaction.guild.roles, id=configItem['shift_management']['role'])]
            else:
                role = [discord.utils.get(interaction.guild.roles, id=role) for role in
                        configItem['shift_management']['role']]

        if role:
            for rl in role:
                if rl in member.roles:
                    await member.remove_roles(rl)


# clockedin, to get all the members of a specific guild currently on duty
@bot.hybrid_command(name='clockedin', description='Get all members of the server currently on shift.',
                    aliases=['on-duty'])
@is_staff()
async def clockedin(ctx):
    try:
        configItem = await bot.settings.find_by_id(ctx.guild.id)
    except:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])

    if shift_channel is None:
        return await invis_embed(ctx, 'Shift management channel not found.')

    embed = discord.Embed(title='<:Resume:1035269012445216858> Currently on Shift', color=0x2E3136)
    try:
        embed.set_footer(text="Staff Logging Module")
    except:
        pass

    for shift in await bot.shifts.get_all():
        if 'data' in shift.keys():
            for s in shift['data']:
                if s['guild'] == ctx.guild.id:
                    member = discord.utils.get(ctx.guild.members, id=shift['_id'])
                    if member:
                        embed.add_field(name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                                        value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(s['startTimestamp']))}",
                                        inline=False)
        elif 'guild' in shift.keys():
            if shift['guild'] == ctx.guild.id:
                member = discord.utils.get(ctx.guild.members, id=shift['_id'])
                if member:
                    embed.add_field(name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                                    value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']))}",
                                    inline=False)

    await ctx.send(embed=embed)


# staff info command, to get total seconds worked on a specific member
@duty.command(name='info', description='Get the total seconds worked on a specific member. [Shift Management]',
              aliases=['i', "stats"])
@is_staff()
async def info(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    try:
        configItem = await bot.settings.find_by_id(ctx.guild.id)
    except:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])

    if shift_channel is None:
        return await invis_embed(ctx, 'Shift management channel not found.')

    embed = discord.Embed(title=f'{member.name}\'s Total Time On-Duty', color=0x2E3136)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Staff Logging Module")

    if not await bot.shift_storage.find_by_id(member.id):
        await invis_embed(ctx, f'{member.name} has not worked on any shifts.')
        return

    total_seconds = 0
    doc = await bot.shift_storage.find_by_id(member.id)

    if "shifts" not in doc.keys():
        doc['shifts'] = ["NONE"]

    if doc['shifts'] is None:
        doc['shifts'] = ["NONE"]

    for shift in doc['shifts']:
        if isinstance(shift, dict):
            if shift['guild'] == ctx.guild.id:
                total_seconds += int(shift['totalSeconds'])

    if td_format(datetime.timedelta(seconds=total_seconds)) not in ["", None]:
        embed.add_field(name='<:Clock:1035308064305332224> Total Time',
                        value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=total_seconds))}",
                        inline=False)
    else:
        embed.add_field(name="<:Clock:1035308064305332224> Total Time",
                        value="<:ArrowRight:1035003246445596774> No shifts found", inline=False)
    await ctx.send(embed=embed)


@duty.command(name='leaderboard',
              description='Get the total time worked for the whole of the staff team. [Shift Management]',
              aliases=['lb'])
@is_staff()
async def shift_leaderboard(ctx):
    try:
        configItem = await bot.settings.find_by_id(ctx.guild.id)
    except:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    all_staff = [{"id": None, "total_seconds": 0}]

    for document in await bot.shift_storage.get_all():
        total_seconds = 0
        if "shifts" in document.keys():
            if isinstance(document['shifts'], list):
                for shift in document['shifts']:
                    if isinstance(shift, dict):
                        if shift['guild'] == ctx.guild.id:
                            total_seconds += int(shift['totalSeconds'])
                            if document['_id'] not in [item['id'] for item in all_staff]:
                                all_staff.append({'id': document['_id'], 'total_seconds': total_seconds})
                            else:
                                for item in all_staff:
                                    if item['id'] == document['_id']:
                                        item['total_seconds'] = item['total_seconds'] + total_seconds

    if len(all_staff) == 0:
        return await invis_embed(ctx, 'No shifts were made in your server.')
    for item in all_staff:
        if item['id'] is None:
            all_staff.remove(item)

    sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

    buffer = None
    for i in sorted_staff:
        member = discord.utils.get(ctx.guild.members, id=i['id'])
        if member:
            if buffer is None:
                buffer = "%s - %s" % (
                    f"{member.name}#{member.discriminator}", td_format(datetime.timedelta(seconds=i['total_seconds'])))
            else:
                buffer = buffer + "\n%s - %s" % (
                    f"{member.name}#{member.discriminator}", td_format(datetime.timedelta(seconds=i['total_seconds'])))

    try:
        bbytes = buffer.encode('utf-8')
    except:
        return await invis_embed(ctx, 'No shift data has been found.')
    await ctx.send(file=discord.File(fp=BytesIO(bbytes), filename='shift_leaderboard.txt'))


@duty.command(name='clear',
              description='Clears all of a member\'s shift data. [Shift Management]',
              aliases=['shift-cl'])
@is_management()
async def clearmember(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    try:
        configItem = await bot.settings.find_by_id(ctx.guild.id)
    except:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    view = YesNoMenu(ctx.author.id)

    if ctx.author == member:
        embed = discord.Embed(
            description=f'<:WarningIcon:1035258528149033090> **Are you sure you would like to clear your shift data?** This is irreversible.',
            color=0x2E3136)
        await ctx.send(embed=embed, view=view)
    else:
        embed = discord.Embed(
            description=f'<:WarningIcon:1035258528149033090> **Are you sure you would like to clear {member.display_name}\'s shift data?** This is irreversible.',
            color=0x2E3136)
        await ctx.send(embed=embed, view=view)
    await view.wait()
    if view.value is False:
        return await invis_embed(ctx, 'Successfully cancelled.')

    document = await bot.shift_storage.find_by_id(member.id)
    if "shifts" in document.keys():
        if isinstance(document['shifts'], list):
            for shift in document['shifts']:
                if isinstance(shift, dict):
                    if shift['guild'] == ctx.guild.id:
                        document['shifts'].remove(shift)
            await bot.shift_storage.update_by_id(document)

    await invis_embed(ctx, f'{member.display_name}\'s shift data has been cleared.')


@duty.command(name='clearall',
              description='Clears all of the shift data. [Shift Management]',
              aliases=['shift-cla'])
@is_management()
async def clearall(ctx):
    try:
        configItem = await bot.settings.find_by_id(ctx.guild.id)
    except:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    view = YesNoMenu(ctx.author.id)
    embed = discord.Embed(
        description='<:WarningIcon:1035258528149033090> **Are you sure you would like to clear ALL shift data?** This is irreversible.',
        color=0x2E3136)
    await ctx.send(view=view, embed=embed)
    await view.wait()
    if view.value is False:
        return await invis_embed(ctx, 'Successfully cancelled.')

    for document in await bot.shift_storage.get_all():
        if "shifts" in document.keys():
            if isinstance(document['shifts'], list):
                for shift in document['shifts']:
                    if isinstance(shift, dict):
                        if shift['guild'] == ctx.guild.id:
                            document['shifts'].remove(shift)
                await bot.shift_storage.update_by_id(document)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Success!",
        description="<:ArrowRight:1035003246445596774> All shift data has been cleared.",
        color=0x71c15f
    )

    await ctx.send(embed=successEmbed)


if __name__ == "__main__":
    bot.run(bot_token)
