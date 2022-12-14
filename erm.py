import json
import logging
import pprint
import time
from dataclasses import MISSING
from io import BytesIO

import aiohttp
import discord.mentions
import dns.resolver
import motor.motor_asyncio
import pytz
import requests
import sentry_sdk
from dateutil import parser
from decouple import config
from discord import app_commands
from discord.ext import tasks
from reactionmenu import ViewButton
from reactionmenu import ViewMenu
from roblox import client as roblox
from sentry_sdk import capture_exception, push_scope
from snowflake import SnowflakeGenerator
from zuid import ZUID

from menus import CustomSelectMenu, SettingsSelectMenu, YesNoMenu, RemoveWarning, LOAMenu, ShiftModify, \
    AddReminder, RemoveReminder, RoleSelect, ChannelSelect, EnableDisableMenu, MultiSelectMenu, RemoveBOLO, EditWarning, \
    AddCustomCommand, RemoveCustomCommand, CustomisePunishmentType, RobloxUsername, EnterRobloxUsername, Verification, \
    ModificationSelectMenu, PartialShiftModify
from utils.mongo import Document
from utils.timestamp import td_format
from utils.utils import *

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

try:
    sentry_url = config('SENTRY_URL')
    bloxlink_api_key = config('BLOXLINK_API_KEY')
except:
    sentry_url = ""
    bloxlink_api_key = ""
discord.utils.setup_logging()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True


class Bot(commands.AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id in [459374864067723275, 713899230183424011,
                       906383042841563167]:  # Implement your own conditions here
            return True

        # Else fall back to the original
        return await super().is_owner(user)

    async def setup_hook(self) -> None:
        bot = self
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
        bot.custom_commands = Document(bot.db, "custom_commands")
        bot.analytics = Document(bot.db, "analytics")
        bot.punishment_types = Document(bot.db, "punishment_types")
        bot.privacy = Document(bot.db, "privacy")
        bot.verification = Document(bot.db, "verification")
        bot.flags = Document(bot.db, "flags")

        bot.error_list = []
        logging.info('Connected to MongoDB!')

        await bot.load_extension('jishaku')

        if not bot.is_synced:  # check if slash commands have been synced
            bot.tree.copy_global_to(guild=discord.Object(id=987798554972143728))
        if environment == 'DEVELOPMENT':
            await bot.tree.sync(guild=discord.Object(id=987798554972143728))

        else:
            await bot.tree.sync()
            # guild specific: leave blank if global (global registration can take 1-24 hours)
        bot.is_synced = True
        check_reminders.start()
        check_loa.start()
        GDPR.start()
        change_status.start()
        logging.info('Setup_hook complete! All tasks are now running!')


bot = Bot(command_prefix=get_prefix, case_insensitive=True, intents=intents, help_command=None)
bot.is_synced = False
bot.bloxlink_api_key = bloxlink_api_key
environment = config('ENVIRONMENT', default='DEVELOPMENT')


def running():
    if bot:
        if bot._ready != MISSING:
            return 1
        else:
            return -1
    else:
        return -1


@bot.before_invoke
async def Analytics(ctx: commands.Context):
    analytics = await bot.analytics.find_by_id(ctx.command.full_parent_name + f" {ctx.command.name}")
    if not analytics:
        await bot.analytics.insert({"_id": ctx.command.full_parent_name + f" {ctx.command.name}", "uses": 1})
    else:
        await bot.analytics.update_by_id(
            {"_id": ctx.command.full_parent_name + f" {ctx.command.name}", "uses": analytics["uses"] + 1})


@bot.event
async def on_ready():
    logging.info('{} has connected to gateway!'.format(bot.user.name))


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
                    if isinstance(guild_settings['staff_management']['management_role'], list):
                        for role in guild_settings['staff_management']['management_role']:
                            if role in [role.id for role in ctx.author.roles]:
                                return True
                    elif isinstance(guild_settings['staff_management']['management_role'], int):
                        if guild_settings['staff_management']['management_role'] in [role.id for role in
                                                                                     ctx.author.roles]:
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


async def crp_data_to_mongo(jsonData, guildId: int):
    for value in jsonData["moderations"]:
        # get user
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('https://users.roblox.com/v1/users', data={
                "userIds":
                    [
                        value["userId"]
                    ]
            }) as r:
                try:
                    requestJSON = await r.json()
                    name = requestJSON['data'][0]["name"].lower()
                except:
                    name = "placeholder"
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


bot.staff_members = {
    "i_imikey": "Bot Developer",
    "kiper4k": "Support Team",
    "mbrinkley": "Lead Support",
    "ruru0303": "Support Team",
    "myles_cbcb1421": "Support Team",
    "theoneandonly_5567": "Manager",
    "l0st_nations": "Junior Support",
    "royalcrests": "Developer",
    "quiverze": "Junior Support",
    "jonylion": "Trial Support"
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
    try:
        bot_token = config('DEVELOPMENT_BOT_TOKEN')
    except:
        bot_token = ""
    logging.info('Using development token...')
else:
    raise Exception("Invalid environment")
try:
    mongo_url = config('MONGO_URL')
    github_token = config('GITHUB_TOKEN')
except:
    mongo_url = ""
    github_token = ""
generator = SnowflakeGenerator(192)
error_gen = ZUID(prefix="error_", length=10)
system_code_gen = ZUID(prefix="erm-systems-", length=7)


@bot.hybrid_group(
    name="punishment",
    description="Punishment commands [Punishments]"
)
async def punishments(ctx):
    pass


@punishments.command(
    name="types",
    description="List and modify available punishment types [Punishments]"
)
@is_management()
async def punishment_types(ctx):
    Data = await bot.punishment_types.find_by_id(ctx.guild.id)
    if Data is None:
        Data = {
            '_id': ctx.guild.id,
            "types": ["Warning", "Kick", "Ban"]
        }

    embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Punishment Types", color=0x2E3136)
    for item in Data['types']:
        if isinstance(item, str):
            embed.add_field(name=f"<:WarningIcon:1035258528149033090> {item}",
                            value=f"<:ArrowRight:1035003246445596774> Generic: {'<:CheckIcon:1035018951043842088>' if item.lower() in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRight:1035003246445596774> Custom: {'<:CheckIcon:1035018951043842088>' if item.lower() not in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}",
                            inline=False)
        elif isinstance(item, dict):
            embed.add_field(name=f"<:WarningIcon:1035258528149033090> {item['name'].lower().title()}",
                            value=f"<:ArrowRight:1035003246445596774> Generic: {'<:CheckIcon:1035018951043842088>' if item['name'].lower() in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRight:1035003246445596774> Custom: {'<:CheckIcon:1035018951043842088>' if item['name'].lower() not in ['warning', 'kick', 'ban', 'temporary ban', 'bolo'] else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRight:1035003246445596774> Channel: {bot.get_channel(item['channel']).mention if item['channel'] is not None else 'None'}",
                            inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name="<:WarningIcon:1035258528149033090> No types",
                        value="<:ArrowRightW:1035023450592514048> No punishment types are available.", inline=False)

    view = CustomisePunishmentType(ctx.author.id)

    msg = await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value == "create":
        typeName = view.modal.name.value

        # send a view for the channel of the type
        already_types = []
        for item in Data['types']:
            if isinstance(item, dict):
                already_types.append(item['name'].lower())
            else:
                already_types.append(item.lower())

        if typeName.lower() in already_types:
            return await invis_embed(ctx, 'This punishment type already exists.')

        embed = discord.Embed(
            title="<:MalletWhite:1035258530422341672> Create a Punishment Type",
            color=0x2E3136,
            description=f"<:ArrowRight:1035003246445596774> What channel do you want this punishment type to be logged in?"
        )
        newview = ChannelSelect(ctx.author.id, limit=1)
        await msg.edit(embed=embed, view=newview)
        await newview.wait()

        data = {
            "name": typeName.lower().title(),
            "channel": newview.value[0].id
        }

        Data['types'].append(data)
        await bot.punishment_types.upsert(Data)
        success = discord.Embed(
            title=f"<:CheckIcon:1035018951043842088> {typeName.lower().title()} Added",
            description=f"<:ArrowRightW:1035023450592514048>**{typeName.lower().title()}** has been added as a punishment type.",
            color=0x71c15f
        )
        await msg.edit(embed=success, view=None)
    else:
        if view.value == "delete":
            typeName = view.modal.name.value
            already_types = []
            for item in Data['types']:
                if isinstance(item, dict):
                    already_types.append(item['name'].lower())
                else:
                    already_types.append(item.lower())
            if typeName.lower() not in already_types:
                return await invis_embed(ctx, 'This punishment type doesn\'t exist.')
            try:
                Data['types'].remove(typeName.lower().title())
            except ValueError:
                for item in Data['types']:
                    if isinstance(item, dict):
                        if item['name'].lower() == typeName.lower():
                            Data['types'].remove(item)
                    elif isinstance(item, str):
                        if item.lower() == typeName.lower():
                            Data['types'].remove(item)
            await bot.punishment_types.upsert(Data)
            success = discord.Embed(
                title=f"<:CheckIcon:1035018951043842088> {typeName.lower().title()} Removed",
                description=f"<:ArrowRightW:1035023450592514048>**{typeName.lower().title()}** has been removed as a punishment type.",
                color=0x71c15f
            )
            await msg.edit(embed=success)


async def punishment_autocomplete(
        interaction: discord.Interaction,
        current: str) -> typing.List[app_commands.Choice[str]]:
    Data = await bot.punishment_types.find_by_id(interaction.guild.id)
    if Data is None:
        print(current)
        print(Data)
        return [
            app_commands.Choice(name=item, value=item) for item in ["Warning", "Kick", "Ban", "BOLO"]
        ]
    else:
        print(Data)
        commands = []
        for command in Data['types']:
            if current not in ["", " "]:
                print(current)
                if isinstance(command, str):
                    if command.lower().startswith(
                            current.lower()) or current.lower() in command.lower() or command.lower().endswith(
                        current.lower()):
                        commands.append(command)
                elif isinstance(command, dict):
                    if command['name'].lower().startswith(current) or current.lower() in command['name'].lower() or \
                            command['name'].lower().endswith(current.lower()) or current in command['name'].lower():
                        commands.append(command['name'])
            else:
                if isinstance(command, str):
                    commands.append(command)
                elif isinstance(command, dict):
                    commands.append(command['name'])

        if len(commands) == 0:
            return [discord.app_commands.Choice(name='No punishment types found', value="NULL")]

        print(commands)
        commandList = []
        for command in commands:
            if command not in [""]:
                commandList.append(discord.app_commands.Choice(name=command, value=command))
        return commandList


async def user_autocomplete(
        interaction: discord.Interaction,
        current: str) -> typing.List[app_commands.Choice[str]]:
    if current in [None, ""]:
        searches = bot.warnings.db.find().sort([("$natural", -1)]).limit(10)
        choices = []
        async for search in searches:
            choices.append(discord.app_commands.Choice(name=search['_id'], value=search['_id']))
        return choices
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://users.roblox.com/v1/users/search?keyword={current}&limit=25") as resp:
                print(resp.status)
                if resp.status == 200:
                    data = await resp.json()
                    if 'data' in data.keys():
                        choices = []
                        for user in data['data']:
                            choices.append(discord.app_commands.Choice(name=user['name'], value=user['name']))
                        return choices
                else:
                    searches = bot.warnings.db.find({'_id': {'$regex': f'{current.lower()}/i'}}).sort(
                        [("$natural", -1)]).limit(25)

                    choices = []
                    async for search in searches:
                        choices.append(discord.app_commands.Choice(name=search['_id'], value=search['_id']))
                    if not choices:
                        searches = bot.warnings.db.find().sort(
                            [("$natural", -1)]).limit(25)
                        async for search in searches:
                            choices.append(discord.app_commands.Choice(name=search['_id'], value=search['_id']))
                    return choices


@bot.hybrid_command(
    name="punish",
    description="Punish a user [Punishments]",
    usage="punish <user> <type> <reason>",
)
@is_staff()
@app_commands.autocomplete(type=punishment_autocomplete)
@app_commands.autocomplete(user=user_autocomplete)
@app_commands.describe(type="The type of punishment to give.")
@app_commands.describe(user="What's their username? You can mention a Discord user, or provide a ROBLOX username.")
@app_commands.describe(reason="What is your reason for punishing this user?")
async def punish(ctx, user: str, type: str, *, reason: str):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 "<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!",
                                 ephemeral=True, delete_after=3)
    generic_warning_types = [
        "Warning",
        "Kick",
        "Ban",
        "BOLO"
    ]

    warning_types = await bot.punishment_types.find_by_id(ctx.guild.id)
    if warning_types is None:
        warning_types = {
            "_id": ctx.guild.id,
            "types": generic_warning_types
        }
        await bot.punishment_types.insert(warning_types)
        warning_types = warning_types['types']
    else:
        warning_types = warning_types['types']

    designated_channel = None
    settings = await bot.settings.find_by_id(ctx.guild.id)
    if settings:
        warning_type = None
        for warning in warning_types:
            if isinstance(warning, str):
                if warning.lower() == type.lower():
                    warning_type = warning
            elif isinstance(warning, dict):
                if warning['name'].lower() == type.lower():
                    warning_type = warning

        if isinstance(warning_type, str):
            if settings['customisation'].get('kick_channel'):
                if settings['customisation']['kick_channel'] != "None":
                    if type.lower() == "kick":
                        designated_channel = bot.get_channel(settings['customisation']['kick_channel'])
            if settings['customisation'].get('ban_channel'):
                if settings['customisation']['ban_channel'] != "None":
                    if type.lower() == "ban":
                        designated_channel = bot.get_channel(settings['customisation']['ban_channel'])
            if settings['customisation'].get('bolo_channel'):
                if settings['customisation']['bolo_channel'] != "None":
                    if type.lower() == "bolo":
                        designated_channel = bot.get_channel(settings['customisation']['bolo_channel'])
        else:
            if 'channel' in warning_type.keys():
                if warning_type['channel'] != "None":
                    designated_channel = bot.get_channel(warning_type['channel'])

    print(designated_channel)
    if designated_channel is None:
        try:
            designated_channel = bot.get_channel(settings['punishments']['channel'])
        except KeyError:
            return await invis_embed(ctx,
                                     'I could not find a designated channel for logging punishments. Ask a server administrator to use `/config change`.')
    if type.lower() == "tempban":
        return await invis_embed(ctx,
                                 f'Tempbans are currently not possible due to discord limitations. Please use the corresponding command `/tempban` for an alternative.')

    if type.lower() == "warn":
        type = "Warning" if "Warning" in warning_types else "Warning"

    already_types = []
    for item in warning_types:
        if isinstance(item, dict):
            already_types.append(item['name'].lower())
        else:
            already_types.append(item.lower())

    if type.lower() not in already_types:
        return await invis_embed(ctx,
                                 f"`{type}` is an invalid punishment type. Ask your server administrator to add this type via `/punishment types`")

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    print(requestJson)
    try:
        data = requestJson['data']
    except KeyError:
        data = [requestJson]

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            embed.description = """
                <:ArrowRightW:1035023450592514048>**Warnings:** 0
                <:ArrowRightW:1035023450592514048>**Kicks:** 0
                <:ArrowRightW:1035023450592514048>**Bans:** 0
                <:ArrowRightW:1035023450592514048>**Custom:** 0

                `Banned:` <:ErrorIcon:1035000018165321808>
                """
        else:
            warnings = 0
            kicks = 0
            bans = 0
            bolos = 0
            custom = 0

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
                    else:
                        custom += 1
            if bans != 0:
                banned = "<:CheckIcon:1035018951043842088>"
            else:
                banned = "<:ErrorIcon:1035000018165321808>"

            if bolos >= 1:
                embed.description = f"""
                    <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                    <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                    <:ArrowRightW:1035023450592514048>**Bans:** {bans}
                    <:ArrowRightW:1035023450592514048>**Custom:** {custom}
                    
                    <:WarningIcon:1035258528149033090> **BOLOs:**
                    <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                    `Banned:` {banned}
                    """
            else:
                embed.description = f"""
                    <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                    <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                    <:ArrowRightW:1035023450592514048>**Bans:** {bans}
                    <:ArrowRightW:1035023450592514048>**Custom:** {custom}

                    `Banned:` {banned}
                    """
        embed.set_thumbnail(url=Headshot_URL)
        embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')

        Embeds.append(embed)

    menu = ViewMenu(ctx, menu_type=ViewMenu.TypeEmbed, show_page_director=False)

    async def warn_function(ctx, menu, designated_channel=None):
        user = menu.message.embeds[0].title
        await menu.stop(disable_items=True)
        default_warning_item = {
            '_id': user.lower(),
            'warnings': [{
                'id': next(generator),
                "Type": f"{type.lower().title()}",
                "Reason": reason,
                "Moderator": [ctx.author.name, ctx.author.id],
                "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                "Guild": ctx.guild.id
            }]
        }

        singular_warning_item = {
            'id': next(generator),
            "Type": f"{type.lower().title()}",
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
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRight:1035003246445596774> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value=f"<:ArrowRight:1035003246445596774> {type.lower().title()}",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason", value=f"<:ArrowRight:1035003246445596774> {reason}",
                        inline=False)

        if designated_channel is None:
            designated_channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

        if not await bot.warnings.find_by_id(user.lower()):
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)

        shift = await bot.shifts.find_by_id(ctx.author.id)

        if shift is not None:
            if 'data' in shift.keys():
                for index, item in enumerate(shift['data']):
                    if isinstance(item, dict):
                        if item['guild'] == ctx.guild.id:
                            if 'moderations' in item.keys():
                                item['moderations'].append({
                                    'id': next(generator),
                                    "Type": f"{type.lower().title()}",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                })
                            else:
                                item['moderations'] = [{
                                    'id': next(generator),
                                    "Type": f"{type.lower().title()}",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                }]
                            shift['data'][index] = item
                            await bot.shifts.update_by_id(shift)

        success = discord.Embed(
            title=f"<:CheckIcon:1035018951043842088> {type.lower().title()} Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s {type.lower()} has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)

        await designated_channel.send(embed=embed)

    async def task():
        await warn_function(ctx, menu, designated_channel)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    async def cancelTask():
        embed = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This punishment has not been logged.",
            color=0xff3c3c
        )

        await menu.message.edit(embed=embed)

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


# status change discord.ext.tasks
@tasks.loop(minutes=3)
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
                            value=f'This is updated every 3 minutes. If you see the last ping was over 3 minutes ago, contact {discord.utils.get(channel.guild.members, id=635119023918415874).mention}',
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
                            value=f'This is updated every 3 minutes. If you see the last ping was over 3 minutes ago, contact {discord.utils.get(channel.guild.members, id=635119023918415874).mention}',
                            inline=False)

            await last_message.edit(embed=embed)
    except:
        logging.info('Failing updating the status.')


@tasks.loop(minutes=1)
async def change_status():
    logging.info('Changing status')

    users = 0
    for guild in bot.guilds:
        users += guild.member_count

    status = f"{users:,} users"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))


@tasks.loop(hours=24)
async def GDPR():
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
                    if not guild:
                        raise Exception
                    channel = guild.get_channel(int(item['channel']))
                    if not channel:
                        raise Exception

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
            except Exception as e:
                print('Could not send reminder: {}'.format(e))
                pass


@tasks.loop(minutes=1)
async def check_loa():
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

                docs = bot.loas.db.find({'user_id': loaObject['user_id'], 'guild_id': loaObject['guild_id']})
                should_remove_roles = True
                async for doc in docs:
                    if doc['type'] == loaObject['type']:
                        if not doc['expired']:
                            if not doc == loaObject:
                                should_remove_roles = False
                                break

                if should_remove_roles:
                    if roles is not [None]:
                        for role in roles:
                            if role:
                                for rl in roles:
                                    if member:
                                        if rl in member.roles:
                                            try:
                                                await member.remove_roles(rl)
                                            except:
                                                pass
                if member:
                    try:
                        await member.send(embed=embed)
                    except discord.Forbidden:
                        pass


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


#
@bot.hybrid_command(
    name="import",
    description="Import CRP Moderation data [Punishments]"
)
@app_commands.describe(export_file="Your CRP Moderation export file. (.json)")
@is_management()
async def _import(ctx, export_file: discord.Attachment):
    # return await invis_embed(ctx,  '`/import` has been temporarily disabled for performance reasons. We are currently working on a fix as soon as possible.')

    read = await export_file.read()
    decoded = read.decode('utf-8')
    jsonData = json.loads(decoded)
    # except Exception as e:
    #     print(e)
    #     return await invis_embed(ctx,
    #                              "You have not provided a correct CRP export file. You can find this by doing `/export` with the CRP bot.")

    await invis_embed(ctx, 'We are currently processing your export file.')
    await crp_data_to_mongo(jsonData, ctx.guild.id)
    success = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Data Merged",
        description=f"<:ArrowRightW:1035023450592514048>**{ctx.guild.name}**'s data has been merged.",
        color=0x71c15f
    )

    await ctx.send(embed=success)


@bot.hybrid_command(
    name="verify",
    aliases=["link"],
    description="Verify with ERM [Verification]"
)
@app_commands.describe(user="What's your ROBLOX username?")
async def verify(ctx, user: str = None):
    settings = await bot.settings.find_by_id(ctx.guild.id)
    if not settings:
        return await invis_embed(ctx,
                                 'This server is currently not setup. Please tell a server administrator to run `/setup` to allow the usage of this command.')

    if not settings['verification']['enabled']:
        return await invis_embed(ctx,
                                 'This server has verification disabled. Please tell a server administrator to enable verification in `/config change`.')

    verified = False
    verified_user = await bot.verification.find_by_id(ctx.author.id)

    if verified_user:
        if 'isVerified' in verified_user.keys():
            if verified_user['isVerified']:
                verified = True
            else:
                verified_user = None
        else:
            verified = True

    if user is None and verified_user is None:
        if ctx.interaction:
            modal = RobloxUsername()
            await ctx.interaction.response.send_modal(modal)
            await modal.wait()
            try:
                user = modal.name.value
            except:
                return await invis_embed(ctx, 'You have not submitted a username. Please try again.')
        else:
            view = EnterRobloxUsername(ctx.author.id)
            embed = discord.Embed(
                title="<:LinkIcon:1044004006109904966> ERM Verification",
                description="<:ArrowRight:1035003246445596774> Click `Verify` and input your ROBLOX username.",
                color=0x2E3136
            )
            embed.set_footer(text="ROBLOX Verification provided by ERM")
            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.modal:
                try:
                    user = view.modal.name.value
                except:
                    return await invis_embed(ctx, 'You have not submitted a username. Please try again.')
            else:
                return await invis_embed(ctx, 'You have not submitted a username. Please try again.')
    else:
        if user is None:
            user = verified_user['roblox']
            verified = True
        else:
            user = user
            verified = False

    async def after_verified(roblox_user):
        try:
            await bot.verification.insert({
                "_id": ctx.author.id,
                "roblox": roblox_id,
                "isVerified": True,
            })
        except:
            await bot.verification.upsert({
                "_id": ctx.author.id,
                "roblox": roblox_id,
                "isVerified": True,
            })
        settings = await bot.settings.find_by_id(ctx.guild.id)
        verification_role = settings['verification']['role']
        if isinstance(verification_role, list):
            verification_role = [discord.utils.get(ctx.guild.roles, id=int(role)) for role in verification_role]
        elif isinstance(verification_role, int):
            verification_role = [discord.utils.get(ctx.guild.roles, id=int(verification_role))]
        else:
            verification_role = []
        for role in verification_role:
            try:
                await ctx.author.add_roles(role)
            except:
                pass
        try:
            await ctx.author.edit(nick=f"{roblox_user['Username']}")
        except:
            pass
        success_embed = discord.Embed(title=f"<:ERMWhite:1044004989997166682> Welcome {roblox_user['Username']}!",
                                      color=0x2E3136)
        success_embed.description = f"<:ArrowRight:1035003246445596774> You've been verified as <:LinkIcon:1044004006109904966> **{roblox_user['Username']}** in **{ctx.guild.name}**."
        success_embed.set_footer(text="ROBLOX Verification provided to you by Emergency Response Management (ERM)")
        return await ctx.send(embed=success_embed)

    if verified:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://users.roblox.com/v1/users/{user}') as r:
                if r.status == 200:
                    roblox_user = await r.json()
                    roblox_id = roblox_user['id']
                    roblox_user['Username'] = roblox_user['name']
                    return await after_verified(roblox_user)

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.roblox.com/users/get-by-username?username={user}') as r:
            if 'success' in (await r.json()).keys():
                if not (await r.json())['success']:
                    async with session.get(f'https://users.roblox.com/v1/users/{user}') as r:
                        if r.status == 200:
                            roblox_user = await r.json()
                            roblox_id = roblox_user['id']
                            roblox_user['Username'] = roblox_user['name']
                        else:
                            return await invis_embed(ctx, 'That is not a valid roblox username. Please try again.')

            else:
                roblox_user = await r.json()
                roblox_id = roblox_user['Id']

    if not verified:
        await bot.verification.upsert({
            "_id": ctx.author.id,
            "roblox": roblox_id,
            "isVerified": False,
        })

        embed = discord.Embed(color=0x2E3136)
        embed.title = f"<:LinkIcon:1044004006109904966> {roblox_user['Username']}, let's get you verified!"
        embed.description = f"<:ArrowRight:1035003246445596774> Go to our [ROBLOX game](https://www.roblox.com/games/11747455621/Verification)\n<:ArrowRight:1035003246445596774> Click on <:Resume:1035269012445216858>\n<:ArrowRight:1035003246445596774> Verify your ROBLOX account in the game.\n<:ArrowRight:1035003246445596774> Click **Done**!"
        embed.set_footer(text=f'ROBLOX Verification provided by Emergency Response Management')
        view = Verification(ctx.author.id)
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value:
            if view.value == "done":
                # async with aiohttp.ClientSession() as session:
                #     # use https://users.roblox.com/v1/users/{userId} to get description
                #     async with session.get(f'https://users.roblox.com/v1/users/{roblox_id}') as r:
                #         if r.status == 200:
                #             roblox_user = await r.json()
                #             description = roblox_user['description']
                #         else:
                #             return await invis_embed(ctx,
                #                                      'There was an error fetching your roblox profile. Please try again later.')
                #
                # if system_code in description:
                #     return await after_verified(roblox_user)
                # else:
                #     await invis_embed(ctx, 'You have not put the system code in your description. Please try again.')
                new_data = await bot.verification.find_by_id(ctx.author.id)
                print(new_data)
                if 'isVerified' in new_data.keys():
                    if new_data['isVerified']:
                        return await after_verified(roblox_user)
                    else:
                        return await invis_embed(ctx,
                                                 'You have not verified using the verification game. Please retry by running `/verify` again.')
                else:
                    return await invis_embed(ctx,
                                             'You have not verified using the verification game. Please retry by running `/verify` again.')


@bot.event
async def on_guild_join(guild: discord.Guild):
    embed = discord.Embed(color=0x2E3136, title="<:ERMWhite:1044004989997166682> Emergency Response Management")
    embed.description = f"Thanks for adding ERM to **{guild.name}**"
    embed.add_field(
        name="<:Setup:1035006520817090640> Getting Started",
        value=f"<:ArrowRight:1035003246445596774> Run `/setup` to go through the setup. \n<:ArrowRight:1035003246445596774> Run `/config change` to change any configuration.",
        inline=False
    )

    embed.add_field(
        name="<:MessageIcon:1035321236793860116> Simple Commands",
        value=f"<:ArrowRight:1035003246445596774> Run `/duty on` to go on duty. \n<:ArrowRight:1035003246445596774> Run `/punish` to punish a roblox user.",
        inline=False
    )

    embed.add_field(
        name="<:LinkIcon:1044004006109904966> Important Links",
        value=f"<:ArrowRight:1035003246445596774> [Our Website](https://ermbot.xyz)\n<:ArrowRight:1035003246445596774> [Support Server](https://discord.gg/BGfyfqU5fx)\n<:ArrowRight:1035003246445596774> [Status Page](https://status.ermbot.xyz)",
        inline=False
    )

    try:
        await guild.system_channel.send(
            embed=embed
        )
    except:
        await guild.owner.send(
            embed=embed
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
        try:
            embed.set_footer(icon_url=guild.icon.url, text=guild.name)
        except AttributeError:
            pass
        await channel.send(embed=embed)
        logging.info('Server has been sent welcome sequence.')


@bot.hybrid_group(
    name="activity"
)
async def activity(ctx):
    return await invis_embed(ctx, "You have not picked a subcommand.")


@activity.command(
    name="report",
    description="Send an activity report [Activity Management]"
)
@is_management()
async def activity_report(ctx):
    # return await invis_embed(ctx,  "This feature has not been released yet.")
    if ctx.interaction:
        await ctx.interaction.response.defer()

    view = CustomSelectMenu(ctx.author.id, [
        discord.SelectOption(
            label="1 day",
            value="1d",
            description="Shows the activity of staff members within the last day",
            emoji="<:Clock:1035308064305332224>"
        ),
        discord.SelectOption(
            label="7 days",
            value="7d",
            description="Shows the activity of staff members within the last week",
            emoji="<:Clock:1035308064305332224>"
        ),
        discord.SelectOption(
            label="14 days",
            value="14d",
            description="Shows the activity of staff members within the last 2 weeks",
            emoji="<:Clock:1035308064305332224>"
        ),
        discord.SelectOption(
            label="28 days",
            value="28d",
            description="Shows the activity of staff members within the last month",
            emoji="<:Clock:1035308064305332224>"
        ),
        discord.SelectOption(
            label="Custom",
            value="custom",
            description="Choose a custom time period",
            emoji="<:Clock:1035308064305332224>"
        )
    ])
    await invis_embed(ctx, "Choose a period of time you would like to receive a report on.", view=view)
    await view.wait()

    starting_period = None
    ending_period = None
    if view.value.endswith('d'):
        amount_of_days = view.value.removesuffix('d')
        amount = int(amount_of_days)
        datetime_obj = datetime.datetime.now()
        ending_period = datetime_obj
        starting_period = datetime_obj - datetime.timedelta(days=amount)
    elif view.value == "custom":
        msg = await request_response(bot, ctx,
                                     "When do you want this period of time to start?\n*Use a date, example: 5/11/2022*")
        try:
            start_date = parser.parse(msg.content)
        except:
            return await invis_embed(ctx,
                                     'We were unable to translate your date. Please try again in another date format.')

        msg = await request_response(bot, ctx, "When do you want this period of time to end?")
        try:
            end_date = parser.parse(msg.content)
        except:
            return await invis_embed(ctx,
                                     'We were unable to translate your date. Please try again in another date format.')

        starting_period = start_date
        ending_period = end_date

    embeds = []
    embed = discord.Embed(
        title="<:Clock:1035308064305332224> Activity Report",
        color=0x2E3136
    )

    embed.set_footer(text="Click 'Next' to see users who are on LoA.")

    all_staff = [{"id": None, "total_seconds": 0}]

    async for document in bot.shift_storage.db.find({'shifts': {
        '$elemMatch': {'startTimestamp': {'$gte': starting_period.timestamp(), '$lte': ending_period.timestamp()},
                       'guild': ctx.guild.id}}}):
        total_seconds = 0
        if "shifts" in document.keys():
            if isinstance(document['shifts'], list):
                for shift in document['shifts']:
                    if isinstance(shift, dict):
                        if shift['guild'] == ctx.guild.id:
                            if shift['startTimestamp'] >= starting_period.timestamp() and shift[
                                'startTimestamp'] <= ending_period.timestamp():
                                total_seconds += int(shift['totalSeconds'])
                                if document['_id'] not in [item['id'] for item in all_staff]:
                                    all_staff.append({'id': document['_id'], 'total_seconds': total_seconds})
                                else:
                                    for item in all_staff:
                                        if item['id'] == document['_id']:
                                            item['total_seconds'] = total_seconds

    loa_staff = []
    print(all_staff)

    for document in await bot.loas.get_all():
        if document['guild_id'] == ctx.guild.id:
            if document['expiry'] >= starting_period.timestamp():
                if document['denied'] is False and document['accepted'] is True:
                    loa_staff.append(
                        {"member": document['user_id'], "expiry": document['expiry'], "reason": document['reason'],
                         "type": document['type']})

    if len(all_staff) == 0:
        return await invis_embed(ctx, 'No shifts were made in your server.')
    for item in all_staff:
        if item['id'] is None:
            all_staff.remove(item)

    sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

    string = ""
    loa_string = ""
    try:
        settings = await bot.settings.find_by_id(ctx.guild.id)
        quota = settings['shift_management']['quota']
    except:
        quota = 0

    for index, value in enumerate(sorted_staff):
        print(value)
        try:
            member = await ctx.guild.fetch_member(value['id'])
        except discord.NotFound:
            member = None
        if value['total_seconds'] > quota:
            met_quota = "<:CheckIcon:1035018951043842088>"
        else:
            met_quota = "<:ErrorIcon:1035000018165321808>"
        if member:
            string += f"<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.name}#{member.discriminator} - {td_format(datetime.timedelta(seconds=value['total_seconds']))} {met_quota}\n"
        else:
            string += f"<:ArrowRightW:1035023450592514048> **{index + 1}.** `{value['id']}` - {td_format(datetime.timedelta(seconds=value['total_seconds']))} {met_quota}\n"
    for index, value in enumerate(loa_staff):
        if value['member'] in [item['id'] for item in all_staff]:
            item = None
            print(value['member'])

            for i in all_staff:
                print(i)
                if value['member'] == i['id']:
                    print(i)
                    item = i

            print(item)

            formatted_data = td_format(datetime.timedelta(seconds=item['total_seconds']))
        else:
            formatted_data = "0 seconds"

        print(value)

        member = discord.utils.get(ctx.guild.members, id=value['member'])
        if member:
            loa_string += f"<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.name}#{member.discriminator} - {formatted_data}\n*{value['type']} expires <t:{value['expiry']}>*\n"

    loa_str = []
    res = loa_string.splitlines()

    for index, i in enumerate(res):
        if index % 5 == 0:
            loa_str.append(i)
        else:
            loa_str[-1] += f"\n{i}"

    if loa_str == []:
        loa_str.append(loa_string)

    splitted_str = []
    resplit = string.splitlines()

    strAR = ""
    for index, i in enumerate(resplit):
        strAR += f"{i}\n"
        if index % 4 == 0:
            splitted_str.append(i)
        else:
            splitted_str[-1] += f"\n{i}"
    if splitted_str == []:
        splitted_str.append(string)

    try:
        bbytes = strAR.encode('utf-8')
    except:
        return await invis_embed('No shift data has been found.')

    embeds.append(embed)

    for string_obj in splitted_str:
        if len(embeds[-1].fields) == 0:
            embeds[-1].add_field(name="<:Clock:1035308064305332224> Shifts", value=string_obj)
        else:
            if len(embeds[-1].fields) >= 3:
                new_embed = discord.Embed(
                    title="<:Clock:1035308064305332224> Activity Report",
                    color=0x2E3136
                )
                new_embed.add_field(name="<:Clock:1035308064305332224> Shifts", value=string_obj)
                embeds.append(new_embed)
            else:
                embeds[-1].add_field(name="\u200b", value=string_obj, inline=False)

    embed2 = discord.Embed(
        title="<:Clock:1035308064305332224> Activity Report",
        color=0x2E3136
    )

    embed2.set_footer(text="Click 'Next' to see more information.")

    print(loa_str)
    embeds.append(embed2)
    for loa_obj in loa_str:
        if len(embeds[-1].fields) == 0:
            embeds[-1].add_field(name="<:Clock:1035308064305332224> Currently on LoA", value=loa_obj)
        else:
            if len(embeds[-1].fields) >= 3:
                new_embed = discord.Embed(
                    title="<:Clock:1035308064305332224> Activity Notices",
                    color=0x2E3136
                )
                new_embed.add_field(name="<:Clock:1035308064305332224> Currently on LoA", value=loa_obj)
                embeds.append(new_embed)
            else:
                embeds[-1].add_field(name="\u200b", value=loa_obj, inline=False)

    for index, em in enumerate(embeds):
        if len(em.fields) == 0:
            print('0 em fields')
            if em.title == "<:Clock:1035308064305332224> Activity Notices":
                em.add_field(name="<:Clock:1035308064305332224> Currently on LoA",
                             value="<:ArrowRight:1035003246445596774> No Activity Notices found.")
                embeds[index] = em
            else:
                em.add_field(name="<:Clock:1035308064305332224> Shifts",
                             value="<:ArrowRight:1035003246445596774> No shifts found.")
                embeds[index] = em
        elif em.fields[0].value == "":
            print('empty em field')
            if em.title == "<:Clock:1035308064305332224> Activity Notices":
                em.set_field_at(name="<:Clock:1035308064305332224> Currently on LoA",
                                value="No Activity Notices found.", index=0)
                embeds[index] = em
            else:
                em.set_field_at(name="<:Clock:1035308064305332224> Shifts",
                                value="<:ArrowRight:1035003246445596774> No shifts found.", index=0)
                embeds[index] = em

    menu = ViewMenu(ctx, menu_type=ViewMenu.TypeEmbed, show_page_director=True)
    menu.add_pages(embeds)
    menu.add_buttons([ViewButton.back(), ViewButton.next()])
    print(bbytes)
    raw_embed = discord.Embed(title="<:Clock:1035308064305332224> Raw Activity Report", color=0x2E3136)
    file = discord.File(fp=BytesIO(bbytes), filename='raw_activity_report.txt')

    async def task():

        await ctx.send(file=file)

    def taskWrapper():
        bot.loop.create_task(
            task()
        )

    followUp = ViewButton.Followup(
        details=ViewButton.Followup.set_caller_details(
            taskWrapper
        )
    )
    menu.add_button(ViewButton(style=discord.ButtonStyle.secondary, label='Not your expected result?',
                               custom_id=ViewButton.ID_CALLER,
                               followup=followUp))
    await menu.start()


@bot.event
async def on_message(message: discord.Message):
    bypass_role = None

    if not hasattr(bot, 'settings'):
        return

    if message.author == bot.user:
        return

    if not message.guild:
        await bot.process_commands(message)
        return

    dataset = await bot.settings.find_by_id(message.guild.id)
    if dataset == None:
        await bot.process_commands(message)
        return

    antiping_roles = None
    bypass_roles = None

    if "bypass_role" in dataset['antiping'].keys():
        bypass_role = dataset['antiping']['bypass_role']

    if dataset['antiping']['enabled'] is False or dataset['antiping']['role'] is None:
        await bot.process_commands(message)
        return

    if isinstance(bypass_role, list):
        bypass_roles = [discord.utils.get(message.guild.roles, id=role) for role in bypass_role]
    else:
        bypass_roles = [discord.utils.get(message.guild.roles, id=bypass_role)]

    if isinstance(dataset['antiping']['role'], list):
        antiping_roles = [discord.utils.get(message.guild.roles, id=role) for role in dataset['antiping']['role']]
    elif isinstance(dataset['antiping']['role'], int):
        antiping_roles = [discord.utils.get(message.guild.roles, id=dataset['antiping']['role'])]
    else:
        antiping_roles = None

    aa_detection = False
    aa_detection_channel = None
    webhook_channel = None

    if 'game_security' in dataset.keys():
        if 'enabled' in dataset['game_security'].keys():
            if 'channel' in dataset['game_security'].keys() and 'webhook_channel' in dataset['game_security'].keys():
                if dataset['game_security']['enabled'] is True:
                    aa_detection = True
                    webhook_channel = dataset['game_security']['webhook_channel']
                    webhook_channel = discord.utils.get(message.guild.channels, id=webhook_channel)
                    aa_detection_channel = dataset['game_security']['channel']
                    aa_detection_channel = discord.utils.get(message.guild.channels, id=aa_detection_channel)
    print(f"{aa_detection} - {message.guild.name} # This is a temporary test")
    if aa_detection == True:
        if webhook_channel != None:
            print('webhook channel')
            if message.channel.id == webhook_channel.id:
                for embed in message.embeds:
                    print('embed found')
                    if embed.description not in ["", None] and embed.title not in ["", None]:
                        print('embed desc')
                        if ":kick" in embed.description or ":ban" in embed.description:
                            print('used kick/ban command')
                            if 'Command Usage' in embed.title or 'Kick/Ban Command Usage' in embed.title:
                                print('command usage')
                                raw_content = embed.description
                                user, command = raw_content.split('used the command: ')
                                code = embed.footer.text.split('Server: ')[1]
                                if command.count(',') + 1 >= 5:
                                    embed = discord.Embed(
                                        title="<:WarningIcon:1035258528149033090> Excessive Moderations Detected",
                                        description="*ERM has detected that a staff member has kicked/banned an excessive amount of players in the in-game server.*",
                                        color=0x2E3136
                                    )

                                    embed.add_field(
                                        name="<:Search:1035353785184288788> Staff Member:",
                                        value=f"<:ArrowRight:1035003246445596774> {user}",
                                        inline=False
                                    )

                                    embed.add_field(
                                        name="<:MalletWhite:1035258530422341672> Trigger:",
                                        value=f"<:ArrowRight:1035003246445596774> **{command.count(',') + 1}** kicks/bans in a single command.",
                                        inline=False
                                    )

                                    embed.add_field(
                                        name="<:EditIcon:1042550862834323597> Explanation",
                                        value=f"<:ArrowRight:1035003246445596774> On <t:{int(message.created_at.timestamp())}>, {user.split(']')[0].replace('[', '').replace(']', '')} simultaneously kicked/banned {command.count(',') + 1} people from **{code}**",
                                        inline=False
                                    )

                                    pings = []
                                    if 'role' in dataset['game_security'].keys():
                                        if dataset['game_security']['role'] is not None:
                                            if isinstance(dataset['game_security']['role'], list):
                                                for role in dataset['game_security']['role']:
                                                    role = discord.utils.get(message.guild.roles, id=role)
                                                    pings.append(role.mention)

                                    await aa_detection_channel.send(','.join(pings) if pings != [] else '', embed=embed)
                                if " all" in command:
                                    embed = discord.Embed(
                                        title="<:WarningIcon:1035258528149033090> Excessive Moderations Detected",
                                        description="*ERM has detected that a staff member has kicked/banned an excessive amount of players in the in-game server.*",
                                        color=0x2E3136
                                    )

                                    embed.add_field(
                                        name="<:Search:1035353785184288788> Staff Member:",
                                        description=f"<:ArrowRight:1035003246445596774> {user}",
                                        inline=False
                                    )

                                    embed.add_field(
                                        name="<:MalletWhite:1035258530422341672> Trigger:",
                                        value=f"<:ArrowRight:1035003246445596774> Kicking/banning everyone in the server.",
                                        inline=False
                                    )

                                    embed.add_field(
                                        name="<:EditIcon:1042550862834323597> Explanation",
                                        value=f"<:ArrowRight:1035003246445596774> On <t:{int(message.created_at.timestamp())}>, {user.split(']')[0].replace('[').replace(']')} kicked/banned everyone from **{code}**",
                                        inline=False
                                    )

                                    pings = []
                                    if 'role' in dataset['game_security'].keys():
                                        if dataset['game_security']['role'] is not None:
                                            if isinstance(dataset['game_security']['role'], list):
                                                for role in dataset['game_security']['role']:
                                                    role = discord.utils.get(message.guild.roles, id=role)
                                                    pings.append(role.mention)

                                    await aa_detection_channel.send(','.join(pings) if pings != [] else '', embed=embed)

    if message.author.bot:
        return

    if antiping_roles is None:
        await bot.process_commands(message)
        return

    if bypass_roles is not None:
        for role in bypass_roles:
            if role in message.author.roles:
                await bot.process_commands(message)
                return

    for mention in message.mentions:
        isStaffPermitted = False
        logging.info(isStaffPermitted)

        if mention.bot:
            await bot.process_commands(message)
            return

        for role in antiping_roles:
            if role != None:
                if message.author.top_role.position > role.position or message.author.top_role.position == role.position:
                    await bot.process_commands(message)
                    return

        if message.author == message.guild.owner:
            await bot.process_commands(message)
            return

        if not isStaffPermitted:
            for role in antiping_roles:
                print(antiping_roles)
                print(role)
                if role is not None:
                    if mention.top_role.position > role.position:
                        embed = discord.Embed(
                            title=f'Do not ping {role.name} or above!',
                            color=discord.Color.red(),
                            description=f'Do not ping {role.name} or above!\nIt is a violation of the rules, and you will be punished if you continue.'
                        )
                        try:
                            msg = await message.channel.fetch_message(message.reference.message_id)
                            if msg.author == mention:
                                embed.set_image(url="https://i.imgur.com/pXesTnm.gif")
                        except:
                            pass

                        embed.set_footer(text=f'Thanks, {dataset["customisation"]["brand_name"]}',
                                         icon_url=get_guild_icon(bot, message.guild))

                        ctx = await bot.get_context(message)
                        await ctx.reply(f'{message.author.mention}', embed=embed)
                        return
                    await bot.process_commands(message)
                    return
                await bot.process_commands(message)
                return
    await bot.process_commands(message)


@bot.hybrid_command(
    name='setup',
    description='Sets up the bot for use. [Configuration]',
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

    options = [
        discord.SelectOption(
            label="All features",
            value="all",
            emoji="<:Setup:1035006520817090640>",
            description="All features of the bot, contains all of the features below"
        ),
        discord.SelectOption(
            label="Staff Management",
            value="staff_management",
            emoji="<:staff:1035308057007230976>",
            description="Inactivity Notices, and managing staff members"
        ),
        discord.SelectOption(
            label="Punishments",
            value="punishments",
            emoji="<:MalletWhite:1035258530422341672>",
            description="Punishing community members for rule infractions"
        ),
        discord.SelectOption(
            label="Shift Management",
            value="shift_management",
            emoji="<:Search:1035353785184288788>",
            description="Shifts (duty on, duty off), and where logs should go"
        ),
    ]

    welcome = discord.Embed(title="<:Setup:1035006520817090640> Which features would you like enabled?", color=0xffffff)
    welcome.description = "Toggle which modules of ERM you would like to use.\n\n<:ArrowRight:1035003246445596774> All *(default)*\n*All features of the bot*\n\n<:ArrowRight:1035003246445596774> Staff Management\n*Manage your staff members, LoAs, and more!*\n\n<:ArrowRight:1035003246445596774> Punishments\n*Roblox moderation, staff logging systems, and more!*\n\n<:ArrowRight:1035003246445596774> Shift Management\n*Manage staff member's shifts, view who's in game!*"

    view = MultiSelectMenu(ctx.author.id, options)

    await ctx.send(embed=welcome, view=view)

    await view.wait()
    if not view.value:
        return await invis_embed(ctx,
                                 '<:Setup:1035006520817090640> You have took too long to respond. Please try again.')

    if 'all' in view.value:
        settingContents['staff_management']['enabled'] = True
        settingContents['punishments']['enabled'] = True
        settingContents['shift_management']['enabled'] = True
    else:
        if 'punishments' in view.value:
            settingContents['punishments']['enabled'] = True
        if 'shift_management' in view.value:
            settingContents['shift_management']['enabled'] = True
        if 'staff_management' in view.value:
            settingContents['staff_management']['enabled'] = True

    if settingContents['staff_management']['enabled']:
        question = 'What channel do you want to use for staff management?'
        view = ChannelSelect(ctx.author.id, limit=1)
        await invis_embed(ctx, question, view=view)
        await view.wait()
        convertedContent = view.value[0]
        settingContents['staff_management']['channel'] = convertedContent.id

        question = 'What role would you like to use for your staff role? (e.g. @Staff)\n*You can separate multiple roles by using a comma.*'
        view = RoleSelect(ctx.author.id)
        await invis_embed(ctx, question, view=view)
        await view.wait()
        convertedContent = view.value
        settingContents['staff_management']['role'] = [role.id for role in convertedContent]

        question = 'What role would you like to use for your Management role? (e.g. @Management)\n*You can separate multiple roles by using a comma.*'
        view = RoleSelect(ctx.author.id)
        await invis_embed(ctx, question, view=view)
        await view.wait()
        convertedContent = view.value
        settingContents['staff_management']['management_role'] = [role.id for role in convertedContent]

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be assigned to staff members when they are on LoA (Leave of Absence)?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")

        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                question = "What role(s) would you like to be given?\n*You can separate multiple roles by using a comma.*"
                view = RoleSelect(ctx.author.id)
                await invis_embed(ctx, question, view=view)
                await view.wait()
                convertedContent = view.value
                settingContents['staff_management']['loa_role'] = [role.id for role in convertedContent]

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be assigned to staff members when they are on RA (Reduced Activity)?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")

        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                question = "What role(s) would you like to be given?\n*You can separate multiple roles by using a comma.*"
                view = RoleSelect(ctx.author.id)
                await invis_embed(ctx, question, view=view)
                await view.wait()
                convertedContent = view.value
                settingContents['staff_management']['ra_role'] = [role.id for role in convertedContent]
    if settingContents['punishments']['enabled']:
        question = 'What channel do you want to use for punishments?'
        view = ChannelSelect(ctx.author.id, limit=1)
        await invis_embed(ctx, question, view=view)
        await view.wait()
        convertedContent = view.value[0]
        settingContents['punishments']['channel'] = convertedContent.id
    if settingContents['shift_management']['enabled']:
        question = "What channel do you want to use for shift management? (e.g. shift signups, etc.)"
        view = ChannelSelect(ctx.author.id, limit=1)
        await invis_embed(ctx, question, view=view)
        await view.wait()
        convertedContent = view.value[0]
        settingContents['shift_management']['channel'] = convertedContent.id

        view = YesNoMenu(ctx.author.id)
        question = 'Do you want a role to be assigned to staff members when they are in game?'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")

        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                question = "What role(s) would you like to be given?\n*You can separate multiple roles by using a comma.*"
                view = RoleSelect(ctx.author.id, limit=1)
                await invis_embed(ctx, question, view=view)
                await view.wait()
                convertedContent = view.value
                settingContents['shift_management']['role'] = [role.id for role in convertedContent]

        view = YesNoMenu(ctx.author.id)
        question = 'Do you have a weekly quota? (e.g. 2 hours per week)'
        embed = discord.Embed(color=0x2E3136, description=f"<:ArrowRight:1035003246445596774> {question}")

        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value:
                content = (
                    await request_response(bot, ctx, "What would you like the quota to be? (s/m/h/d)")).content
                content = content.strip()
                total_seconds = 0

                if content.endswith(('s', 'm', 'h', 'd')):
                    if content.endswith('s'):
                        total_seconds = int(content.removesuffix('s'))
                    if content.endswith('m'):
                        total_seconds = int(content.removesuffix('m')) * 60
                    if content.endswith('h'):
                        total_seconds = int(content.removesuffix('h')) * 60 * 60
                    if content.endswith('d'):
                        total_seconds = int(content.removesuffix('d')) * 60 * 60 * 24
                else:
                    return await invis_embed(ctx, 'We could not translate your time. Remember to end it with s/m/h/d.')

                settingContents['shift_management']['quota'] = total_seconds

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
    description='View the current configuration of the server. [Configuration]'
)
@is_management()
async def viewconfig(ctx):
    if not await bot.settings.find_by_id(ctx.guild.id):
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    settingContents = await bot.settings.find_by_id(ctx.guild.id)
    privacyConfig = await bot.privacy.find_by_id(ctx.guild.id)
    antiping_role = "None"
    bypass_role = "None"
    verification_role = "None"
    shift_role = "None"
    staff_management_channel = "None"
    staff_role = "None"
    management_role = "None"
    punishments_channel = "None"
    kick_channel = "None"
    ban_channel = "None"
    bolo_channel = "None"
    ra_role = "None"
    loa_role = "None"
    webhook_channel = "None"
    aa_channel = "None"
    aa_role = "None"
    minimum_shift_time = 0

    try:
        if isinstance(settingContents['verification']['role'], int):
            verification_role = ctx.guild.get_role(settingContents['verification']['role']).mention
        elif isinstance(settingContents['verification']['role'], list):
            verification_role = ''
            for role in settingContents['verification']['role']:
                verification_role += ctx.guild.get_role(role).mention + ', '
            verification_role = verification_role[:-2]
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
            antiping_role = antiping_role[:-2]
    except:
        antiping_role = 'None'

    try:
        if isinstance(settingContents['antiping']['bypass_role'], int):
            bypass_role = ctx.guild.get_role(settingContents['antiping']['bypass_role']).mention
        elif isinstance(settingContents['antiping']['bypass_role'], list):
            bypass_role = ''
            for role in settingContents['antiping']['bypass_role']:
                bypass_role += ctx.guild.get_role(role).mention + ', '
            bypass_role = bypass_role[:-2]
    except:
        bypass_role = 'None'

    try:
        if isinstance(settingContents['game_security']['role'], int):
            aa_role = ctx.guild.get_role(settingContents['game_security']['role']).mention
        elif isinstance(settingContents['game_security']['role'], list):
            aa_role = ''
            for role in settingContents['game_security']['role']:
                aa_role += ctx.guild.get_role(role).mention + ', '
            aa_role = aa_role[:-2]
    except:
        aa_role = 'None'

    try:
        staff_management_channel = ctx.guild.get_channel(settingContents['staff_management']['channel']).mention
    except:
        staff_management_channel = 'None'

    try:
        webhook_channel = ctx.guild.get_channel(settingContents['game_security']['webhook_channel']).mention
    except:
        webhook_channel = 'None'

    try:
        aa_channel = ctx.guild.get_channel(settingContents['game_security']['channel']).mention
    except:
        aa_channel = 'None'

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
        compact_mode = settingContents['customisation']['compact_mode']
    except:
        compact_mode = False
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

    try:
        quota = f"{settingContents['shift_management']['quota']} seconds"
    except:
        quota = '0 seconds'

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
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}\n<:ArrowRightW:1035023450592514048>**Quota:** {}'
        .format(
            settingContents['shift_management']['enabled'],
            shift_management_channel,
            shift_role,
            quota
        ),
        inline=False
    )
    embed.add_field(
        name='<:FlagIcon:1035258525955395664> Customisation',
        value='<:ArrowRightW:1035023450592514048>**Color:** {}\n<:ArrowRightW:1035023450592514048>**Prefix:** `{}`\n<:ArrowRightW:1035023450592514048>**Brand Name:** {}\n<:ArrowRightW:1035023450592514048>**Thumbnail URL:** {}\n<:ArrowRightW:1035023450592514048>**Footer Text:** {}\n<:ArrowRightW:1035023450592514048>**Compact Mode:** {}\n<:ArrowRightW:1035023450592514048>**Ban Channel:** {}\n<:ArrowRightW:1035023450592514048>**Kick Channel:** {}\n<:ArrowRightW:1035023450592514048>**BOLO Channel:** {}'
        .format(
            settingContents['customisation']['color'],
            settingContents['customisation']['prefix'],
            settingContents['customisation']['brand_name'],
            settingContents['customisation']['thumbnail_url'],
            settingContents['customisation']['footer_text'],
            compact_mode,
            ban_channel,
            kick_channel,
            bolo_channel
        ),
        inline=False
    )
    game_security_enabled = False
    if 'game_security' in settingContents.keys():
        if 'enabled' in settingContents['game_security'].keys():
            game_security_enabled = settingContents['game_security']['enabled']
        else:
            game_security_enabled = 'False'
    else:
        game_security_enabled = 'False'

    embed.add_field(
        name='<:WarningIcon:1035258528149033090> Game Security',
        value='<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}\n<:ArrowRightW:1035023450592514048>**Webhook Channel:** {}'
        .format(
            game_security_enabled,
            aa_channel,
            aa_role,
            webhook_channel
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
    description='Change the configuration of the server. [Configuration]'
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
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What role do you want to use for verification? (e.g. `@Verified`)', view=view)
            await view.wait()
            settingContents['verification']['role'] = [role.id for role in view.value]
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
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use for antiping? (e.g. `@Don\'t ping`)', view=view)
            await view.wait()
            settingContents['antiping']['role'] = [role.id for role in view.value]
        elif content == "bypass_role" or content == "bypass" or content == "bypass-role":
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use as a bypass role? (e.g. `@Antiping Bypass`)',
                              view=view)
            await view.wait()
            settingContents['antiping']['bypass_role'] = [role.id for role in view.value]
        else:
            return await invis_embed(ctx, 'You have not selected one of the options. Please run this command again.')
    elif category == 'staff_management':
        question = 'What do you want to do with staff management?'
        customselect = CustomSelectMenu(ctx.author.id,
                                        ["enable", "disable", "channel", "staff_role", "management_role", "loa_role",
                                         "ra_role", "m_channel", "privacy_mode"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['staff_management']['enabled'] = True
        elif content == 'disable':
            settingContents['staff_management']['enabled'] = False
        elif content == 'channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel would you like to use for staff management? (e.g. loa requests)',
                              view=view)
            await view.wait()
            settingContents['staff_management']['channel'] = view.value[0].id
        elif content == 'staff_role':
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use as staff roles? (e.g. `@Staff`)', view=view)
            await view.wait()
            settingContents['staff_management']['role'] = [role.id for role in view.value]
        elif content == 'management_role':
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use as management roles? (e.g. `@Management`)', view=view)
            await view.wait()
            settingContents['staff_management']['management_role'] = [role.id for role in view.value]
        elif content == 'loa_role':
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use as a LOA role? (e.g. `@LOA`)', view=view)
            await view.wait()
            settingContents['staff_management']['loa_role'] = [role.id for role in view.value]
        elif content == 'ra_role':
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use as a RA role? (e.g. `@RA`)', view=view)
            await view.wait()
            settingContents['staff_management']['ra_role'] = [role.id for role in view.value]
        elif content == 'm_channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want to use as a Message Logging Channel? (e.g. `#m-logs`)',
                              view=view)
            await view.wait()
            settingContents['staff_management']['m_channel'] = view.value[0].id
        elif content == 'privacy_mode':
            view = EnableDisableMenu(ctx.author.id)
            await invis_embed(ctx,
                              'Do you want to enable Privacy Mode? This will anonymize the person who denies/accepts/voids a LoA/RA.',
                              view=view)
            await view.wait()
            if view.value == True:
                settingContents['staff_management']['privacy_mode'] = True
            elif view.value == False:
                settingContents['customisation']['privacy_mode'] = False
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
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want to use for punishments? (e.g. `#punishments`)', view=view)
            await view.wait()
            settingContents["punishments"]["channel"] = view.value[0].id
        elif content == 'ban_channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want to use for bans? (e.g. `#bans`)', view=view)
            await view.wait()
            settingContents["customisation"]["ban_channel"] = view.value[0].id
        elif content == 'kick_channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want to use for kicks? (e.g. `#kicks`)', view=view)
            await view.wait()
            settingContents["customisation"]["kick_channel"] = view.value[0].id
        elif content == 'bolo_channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want to use for BOLOs? (e.g. `#bolos`)', view=view)
            await view.wait()
            settingContents["customisation"]["bolo_channel"] = view.value[0].id
        else:
            return await invis_embed(ctx, 'You have not selected one of the options. Please run this command again.')
    elif category == 'shift_management':
        question = 'What do you want to do with shift management?'
        customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "quota", "channel", "role"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value
        if content == 'enable':
            settingContents['shift_management']['enabled'] = True
        elif content == 'disable':
            settingContents['shift_management']['enabled'] = False
        elif content == 'quota':
            content = (
                await request_response(bot, ctx, "What would you like the quota to be? (s/m/h/d)")).content
            content = content.strip()
            total_seconds = 0

            if content.endswith(('s', 'm', 'h', 'd')):
                if content.endswith('s'):
                    total_seconds = int(content.removesuffix('s'))
                if content.endswith('m'):
                    total_seconds = int(content.removesuffix('m')) * 60
                if content.endswith('h'):
                    total_seconds = int(content.removesuffix('h')) * 60 * 60
                if content.endswith('d'):
                    total_seconds = int(content.removesuffix('d')) * 60 * 60 * 24
            else:
                return await invis_embed(ctx, 'We could not translate your time. Remember to end it with s/m/h/d.')

            settingContents['shift_management']['quota'] = total_seconds

        elif content == 'channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want to use for shift management? (e.g. shift logons)',
                              view=view)
            await view.wait()
            settingContents["shift_management"]["channel"] = view.value[0].id
        elif content == 'role':
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, 'What roles do you want to use as a On-Duty role? (e.g. `@On-Duty`)', view=view)
            await view.wait()
            settingContents['shift_management']['role'] = [role.id for role in view.value]
        else:
            return await invis_embed(ctx,
                                     'Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.')
    elif category == 'customisation':
        # color, prefix, brand name, thumbnail url, footer text, ban channel
        question = 'What would you like to customize?'
        customselect = CustomSelectMenu(ctx.author.id, ["color", "prefix", "brand_name", "thumbnail_url", "footer_text",
                                                        "server_code", "compact_mode"])
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
        elif content == 'compact_mode':
            view = EnableDisableMenu(ctx.author.id)
            await invis_embed(ctx,
                              'Do you want to enable Compact Mode? This will disable most of the emojis used within the bot.',
                              view=view)
            await view.wait()
            if view.value == True:
                settingContents['customisation']['compact_mode'] = True
            elif view.value == False:
                settingContents['customisation']['compact_mode'] = False

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
    elif category == 'security':
        question = 'What do you want to do with Game Security?'
        customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "role", "channel", "webhook_channel"])
        await invis_embed(ctx, question, view=customselect)
        await customselect.wait()
        content = customselect.value

        if not 'game_security' in settingContents.keys():
            settingContents['game_security'] = {}

        if content == 'enable':
            settingContents['game_security']['enabled'] = True
        elif content == 'disable':
            settingContents['game_security']['enabled'] = False
        elif content == 'role':
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx,
                              'What roles do you want to be mentioned when abuse is detected? (e.g. `@Leadership`)',
                              view=view)
            await view.wait()
            settingContents['game_security']['role'] = [role.id for role in view.value]
        elif content == 'webhook_channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel are ER:LC webhooks sent to? (e.g. `#kicks-and-bans`)', view=view)
            await view.wait()
            settingContents['game_security']['webhook_channel'] = view.value[0].id
        elif content == 'channel':
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, 'What channel do you want Anti-Abuse reports to go to? (e.g. `#admin-abuse`)',
                              view=view)
            await view.wait()
            settingContents['game_security']['channel'] = view.value[0].id
        else:
            return await invis_embed(ctx,
                                     'Please pick one of the options. `enable`, `disable`, `role`, `channel`, `webhook_channel`. Please run this command again with correct parameters.')
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
@app_commands.describe(user="What's their username? You can mention a Discord user, or provide a Roblox username.")
@app_commands.describe(reason="What is your reason for punishing this user?")
@is_staff()
async def warn(ctx, user, *, reason):
    await invis_embed(ctx, 'This command is now a legacy command. We recommend that you now use `/punish` instead.')

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    print(requestJson)
    try:
        data = requestJson['data']
    except KeyError:
        data = [requestJson]

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            embed.description = """
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
                embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                <:WarningIcon:1035258528149033090> **BOLOs:**
                <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                `Banned:` {banned}
                """
            else:
                embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                `Banned:` {banned}
                """
        embed.set_thumbnail(url=Headshot_URL)
        embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')

        Embeds.append(embed)

    if ctx.interaction:
        interaction = ctx
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
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
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

        if not await bot.warnings.find_by_id(user.lower()):
            await bot.warnings.insert(default_warning_item)
        else:
            dataset = await bot.warnings.find_by_id(user.lower())
            dataset['warnings'].append(singular_warning_item)
            await bot.warnings.update_by_id(dataset)
        shift = await bot.shifts.find_by_id(ctx.guild.id)
        if shift is not None:
            if 'data' in shift.keys():
                for item in shift['data']:
                    if isinstance(item, dict):
                        if item['guild'] == ctx.guild.id:
                            if 'moderations' in item.keys():
                                item['moderations'].append({
                                    'id': next(generator),
                                    "Type": "Warning",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                })
                            else:
                                item['moderations'] = [{
                                    'id': next(generator),
                                    "Type": "Warning",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                }]

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
        embed = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This warning has not been logged.",
            color=0xff3c3c
        )

        await menu.message.edit(embed=embed)

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
    except Exception as e:
        print(e)
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
@app_commands.describe(user="What's their ROBLOX username?")
@app_commands.describe(reason="What is your reason for punishing this user?")
async def kick(ctx, user, *, reason):
    await invis_embed(ctx, 'This command is now a legacy command. We recommend that you now use `/punish` instead.')

    request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    print(requestJson)
    try:
        data = requestJson['data']
    except KeyError:
        data = [requestJson]

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            embed.description = """
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
                embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                <:WarningIcon:1035258528149033090> **BOLOs:**
                <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                `Banned:` {banned}
                """
            else:
                embed.description = f"""
                <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                `Banned:` {banned}
                """
        embed.set_thumbnail(url=Headshot_URL)
        embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')

        Embeds.append(embed)

    if ctx.interaction:
        interaction = ctx
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
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
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

        shift = await bot.shifts.find_by_id(ctx.guild.id)
        if shift is not None:
            if 'data' in shift.keys():
                for item in shift['data']:
                    if isinstance(item, dict):
                        if item['guild'] == ctx.guild.id:
                            if 'moderations' in item.keys():
                                item['moderations'].append({
                                    'id': next(generator),
                                    "Type": "Kick",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                })
                            else:
                                item['moderations'] = [{
                                    'id': next(generator),
                                    "Type": "Kick",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                }]

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
        embed = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This kick has not been logged.",
            color=0xff3c3c
        )

        await menu.message.edit(embed=embed)

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
@app_commands.describe(user="What's their ROBLOX username?")
@app_commands.describe(reason="What is your reason for punishing this user?")
async def ban(ctx, user, *, reason):
    await invis_embed(ctx, 'This command is now a legacy command. We recommend that you now use `/punish` instead.')

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    print(requestJson)
    try:
        data = requestJson['data']
    except KeyError:
        data = [requestJson]

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
        interaction = ctx
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
                        value=f"<:ArrowRightW:1035023450592514048> {ctx.author.mention}",
                        inline=False)
        embed.add_field(name="<:WarningIcon:1035258528149033090> Violator",
                        value=f"<:ArrowRightW:1035023450592514048> {menu.message.embeds[0].title}", inline=False)
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type", value="<:ArrowRightW:1035023450592514048> Ban",
                        inline=False)
        embed.add_field(name="<:QMark:1035308059532202104> Reason",
                        value=f"<:ArrowRightW:1035023450592514048> {reason}",
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

        shift = await bot.shifts.find_by_id(ctx.guild.id)
        if shift is not None:
            if 'data' in shift.keys():
                for item in shift['data']:
                    if isinstance(item, dict):
                        if item['guild'] == ctx.guild.id:
                            if 'moderations' in item.keys():
                                item['moderations'].append({
                                    'id': next(generator),
                                    "Type": "Ban",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                })
                            else:
                                item['moderations'] = [{
                                    'id': next(generator),
                                    "Type": "Ban",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                }]

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
        embed = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        )

        await menu.message.edit(embed=embed)

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
@app_commands.describe(message="What was the message you announced?")
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
                    value=f"<:ArrowRightW:1035023450592514048> {ctx.author.mention}",
                    inline=False)
    embed.add_field(name="<:MessageIcon:1035321236793860116> Message",
                    value=f"<:ArrowRight:1035003246445596774> {message}", inline=False)
    channel = None
    if 'm_channel' in configItem['staff_management'].keys():
        if configItem['staff_management']['m_channel'] is not None:
            channel = discord.utils.get(ctx.guild.channels, id=configItem['staff_management']['m_channel'])

    if not channel:
        if not configItem['staff_management']['channel'] is None:
            channel = ctx.guild.get_channel(configItem['staff_management']['channel'])

    if not channel:
        return await invis_embed(
            'The channel in the configuration does not exist. Please tell a server administrator to run `/config change` for the channel to be changed.')

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
@app_commands.describe(user="What's their ROBLOX username?")
@app_commands.describe(reason="How long are you banning them for? (s/m/h/d)")
@app_commands.describe(reason="What is your reason for punishing this user?")
async def tempban(ctx, user, time: str, *, reason):
    reason = ''.join(reason)

    timeObj = list(reason)[-1]
    reason = list(reason)

    if not time.lower().endswith(('h', 'm', 's', 'd', 'w')):
        reason.insert(0, time)
        if not timeObj.lower().endswith(('h', 'm', 's', 'd', 'w')):
            return await invis_embed(ctx,
                                     'A time must be provided at the **start** of your reason. Example: >tban i_iMikey 12h LTAP')
        else:
            time = timeObj
            reason.pop()

    if time.lower().endswith('s'):
        time = int(removesuffix(time.lower(), 's'))
    elif time.lower().endswith('m'):
        time = int(removesuffix(time.lower(), 'm')) * 60
    elif time.lower().endswith('h'):
        time = int(removesuffix(time.lower(), 'h')) * 60 * 60
    elif time.lower().endswith('d'):
        time = int(removesuffix(time.lower(), 'd')) * 60 * 60 * 24
    elif time.lower().endswith('w'):
        time = int(removesuffix(time.lower(), 'w')) * 60 * 60 * 24 * 7

    startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
    endTimestamp = int(startTimestamp + time)

    reason = ''.join([str(item) for item in reason])
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    print(requestJson)
    try:
        data = requestJson['data']
    except KeyError:
        data = [requestJson]

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            embed.description = """
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
                embed.description = f"""
                       <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                       <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                       <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                       <:WarningIcon:1035258528149033090> **BOLOs:**
                       <:ArrowRightW:1035023450592514048> There is currently a BOLO on this user. Please check their reason with `/bolo lookup` before continuing.

                       `Banned:` {banned}
                       """
            else:
                embed.description = f"""
                       <:ArrowRightW:1035023450592514048>**Warnings:** {warnings}
                       <:ArrowRightW:1035023450592514048>**Kicks:** {kicks}
                       <:ArrowRightW:1035023450592514048>**Bans:** {bans}

                       `Banned:` {banned}
                       """

        embed.set_thumbnail(url=Headshot_URL)
        embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')

        Embeds.append(embed)

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
                        value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
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

        shift = await bot.shifts.find_by_id(ctx.guild.id)
        if shift is not None:
            if 'data' in shift.keys():
                for item in shift['data']:
                    if isinstance(item, dict):
                        if item['guild'] == ctx.guild.id:
                            if 'moderations' in item.keys():
                                item['moderations'].append({
                                    'id': next(generator),
                                    "Type": "Temporary Ban",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Until": endTimestamp,
                                    "Guild": ctx.guild.id
                                })
                            else:
                                item['moderations'] = [{
                                    'id': next(generator),
                                    "Type": "Temporary Ban",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Until": endTimestamp,
                                    "Guild": ctx.guild.id
                                }]

        success = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Ban Logged",
            description=f"<:ArrowRightW:1035023450592514048>**{menu.message.embeds[0].title}**'s ban has been logged.",
            color=0x71c15f
        )

        await menu.message.edit(embed=success)
        await channel.send(embed=embed)

    if ctx.interaction:
        interaction = ctx
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
        embed = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This ban has not been logged.",
            color=0xff3c3c
        )

        await menu.message.edit(embed=embed)

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
@is_staff()
@app_commands.autocomplete(query=user_autocomplete)
@app_commands.describe(
    query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username.")
async def search(ctx, *, query):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!',
                                 ephemeral=True, delete_after=5)
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

    user = query
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    RESULTS = []
    query = requestJson['name']

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
        if await bot.flags.find_by_id(query.lower()):
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
            if warning['Type'].upper() == 'BOLO':
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

        if await bot.flags.find_by_id(embed1.title):
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
                        new_embed = discord.Embed(title=embeds[0].title, color=await generate_random(ctx))

                        embeds.append(new_embed)
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
                        new_embed = discord.Embed(title=embeds[0].title, color=await generate_random(ctx))

                        embeds.append(new_embed)
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
            interaction = ctx
        else:
            interaction = ctx
        menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        new_embeds = []
        for embed in embeds:
            new_embeds.append(embed)
        menu.add_pages(new_embeds)
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
@is_staff()
@app_commands.autocomplete(query=user_autocomplete)
@app_commands.describe(
    query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username.")
async def globalsearch(ctx, *, query):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!',
                                 ephemeral=True, delete_after=5)
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
    user = query
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    RESULTS = []
    query = requestJson['name']

    dataset = await bot.warnings.find_by_id(query.lower())
    if dataset:
        logging.info(dataset)
        try:
            logging.info(dataset['warnings'][0])
            dataset['warnings'][0]['name'] = query.lower()
            RESULTS.append(dataset['warnings'])
        except:
            pass

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

        if await bot.flags.find_by_id(embed1.title):
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
        except (IndexError, KeyError):
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

            if await bot.flags.find_by_id(embed1.title):
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

        if await bot.flags.find_by_id(embed1.title):
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
                    new_embed = discord.Embed(title=embeds[0].title, color=await generate_random(ctx))

                    embeds.append(new_embed)

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
                    new_embed = discord.Embed(title=embeds[0].title, color=await generate_random(ctx))

                    embeds.append(new_embed)

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
            interaction = ctx
        else:
            interaction = ctx
        menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        new_embeds = []
        for embed in embeds:
            new_embeds.append(embed)
        menu.add_pages(new_embeds)
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
    description='Remove a punishment from a user. [Punishments]',
    usage='<user> <warning id>',
    with_app_command=True,
)
@is_staff()
@app_commands.describe(
    id="What is the ID of the punishment you would like to void? You can find this by running /search.")
async def removewarning(ctx, id: str):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!',
                                 ephemeral=True, delete_after=5)
    try:
        id = int(id)
    except:
        return await invis_embed(ctx, '`id` is not a valid ID.')

    keyStorage = None
    selected_item = None
    selected_items = []
    item_index = 0

    async for item in bot.warnings.db.find({'warnings': {'$elemMatch': {'id': id}}}):
        for index, _item in enumerate(item['warnings']):
            if _item['id'] == id:
                selected_item = _item
                selected_items.append(_item)
                parent_item = item
                item_index = index
                break

    if selected_item is None:
        return await invis_embed(ctx, 'That punishment does not exist.')

    if selected_item['Guild'] != ctx.guild.id:
        return await invis_embed(ctx, 'You are trying to remove a punishment that is not apart of this guild.')

    if len(selected_items) > 1:
        return await invis_embed(ctx,
                                 'There is more than one punishment associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.')

    Moderator = discord.utils.get(ctx.guild.members, id=selected_item['Moderator'][1])
    if Moderator:
        Moderator = Moderator.mention
    else:
        Moderator = selected_item['Moderator'][0]

    embed = discord.Embed(
        title="<:MalletWhite:1035258530422341672> Remove Punishment",
        description=f"<:ArrowRightW:1035023450592514048> **Reason:** {selected_item['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {Moderator}\n<:ArrowRightW:1035023450592514048> **ID:** {selected_item['id']}\n",
        color=0x2E3136
    )

    view = RemoveWarning(bot, ctx.author.id)
    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value:
        parent_item['warnings'].remove(selected_item)
        await bot.warnings.update_by_id(parent_item)


@punishments.command(
    name='modify',
    aliases=['mw', 'modwarn', 'mod'],
    description='Remove a punishment from a user. [Punishments]',
    usage='<warning id>',
    with_app_command=True,
)
@is_staff()
@app_commands.describe(
    id="What is the ID of the punishment you would like to modify? You can find this by running /search.")
async def punishment_modify(ctx, id: str):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!',
                                 ephemeral=True, delete_after=5)
    try:
        id = int(id)
    except:
        return await invis_embed(ctx, '`id` is not a valid ID.')

    keyStorage = None
    selected_item = None
    selected_items = []
    item_index = 0

    async for item in bot.warnings.db.find({'warnings': {'$elemMatch': {'id': id}}}):
        for index, _item in enumerate(item['warnings']):
            if _item['id'] == id:
                selected_item = _item
                selected_items.append(_item)
                parent_item = item
                item_index = index
                break

    if selected_item is None:
        return await invis_embed(ctx, 'That punishment does not exist.')

    if selected_item['Guild'] != ctx.guild.id:
        return await invis_embed(ctx, 'You are trying to edit a punishment that is not apart of this guild.')

    if len(selected_items) > 1:
        return await invis_embed(ctx,
                                 'There is more than one punishment associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.')

    Moderator = discord.utils.get(ctx.guild.members, id=selected_item['Moderator'][1])
    if Moderator:
        Moderator = Moderator.mention
    else:
        Moderator = selected_item['Moderator'][0]

    embed = discord.Embed(
        title="<:MalletWhite:1035258530422341672> Edit Punishment",
        description=f"<:ArrowRightW:1035023450592514048> **Reason:** {selected_item['Reason']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {Moderator}\n<:ArrowRightW:1035023450592514048> **ID:** {selected_item['id']}\n",
        color=0x2E3136
    )

    punishment_types = await bot.punishment_types.find_by_id(ctx.guild.id)
    if punishment_types:
        punishment_types = punishment_types['types']
    view = EditWarning(bot, ctx.author.id, punishment_types or [])
    msg = await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value == "edit":
        selected_item['Reason'] = view.further_value
        parent_item['warnings'][item_index] = selected_item
        await bot.warnings.update_by_id(parent_item)
    elif view.value == "change":
        if isinstance(view.further_value, list):
            type = view.further_value[0]
            seconds = view.further_value[1]
        else:
            type = view.further_value

        selected_item['Type'] = type
        try:
            selected_item['Until'] = datetime.datetime.now().timestamp() + seconds
        except:
            pass
        parent_item['warnings'][item_index] = selected_item
        await bot.warnings.update_by_id(parent_item)
    elif view.value == "delete":
        parent_item['warnings'].remove(selected_item)
        await bot.warnings.update_by_id(parent_item)
    else:
        return await invis_embed(ctx, "You have not selected an option.")
    success = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Punishment Modified",
        description=f"<:ArrowRightW:1035023450592514048>This punishment has been modified successfully.",
        color=0x71c15f
    )
    await msg.edit(embed=success)


@bot.hybrid_command(
    name='help',
    aliases=['h', 'commands', 'cmds', 'cmd', 'command'],
    description='Get a list of commands. [Utility]',
    usage='<command>',
    with_app_command=True,
)
@app_commands.describe(command="Would you like more information on a command? If so, please enter the command name.")
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
            "Reminders": "<:Resume:1035269012445216858>",
            "Activity Management": "<:Pause:1035308061679689859>",
            "Custom Commands": "<:QMark:1035308059532202104>",
            "Verification": "<:SettingIcon:1035353776460152892>"
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
            print(commands)
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
                splitted_lines = string.splitlines()

                for i in range(0, len(splitted_lines), 5):
                    has_full_category = False
                    for field in embed.fields:
                        if field.name == full_category:
                            has_full_category = True

                    if not has_full_category:
                        embed.add_field(
                            name=full_category,
                            value='\n'.join(splitted_lines[i:i + 5]),
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name='\u200b',
                            value='\n'.join(splitted_lines[i:i + 5]),
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
@app_commands.describe(user="What's their ROBLOX username?")
@app_commands.describe(reason="What is your reason for punishing this user?")
async def bolo_create(ctx, user, *, reason):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10') as r:
            if r.status == 200:
                robloxUser = await r.json()
                if len(robloxUser['data']) == 0:
                    return await invis_embed(ctx, f'No user found with the name `{user}`')
                robloxUser = robloxUser['data'][0]
                Id = robloxUser['id']
                async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                    requestJson = await r.json()
            else:
                async with session.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}') as r:
                    robloxUser = await r.json()
                    if 'success' not in robloxUser.keys():
                        Id = robloxUser['Id']
                        async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                            requestJson = await r.json()
                    else:
                        try:
                            userConverted = await (discord.ext.commands.MemberConverter()).convert(ctx,
                                                                                                   user.replace(' ',
                                                                                                                ''))
                            if userConverted:
                                verified_user = await bot.verification.find_by_id(userConverted.id)
                                if verified_user:
                                    Id = verified_user['roblox']
                                    async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                        requestJson = await r.json()
                                else:
                                    async with aiohttp.ClientSession(headers={
                                        "api-key": bot.bloxlink_api_key
                                    }) as newSession:
                                        async with newSession.get(
                                                f"https://v3.blox.link/developer/discord/{userConverted.id}") as r:
                                            tempRBXUser = await r.json()
                                            if tempRBXUser['success']:
                                                tempRBXID = tempRBXUser['user']['robloxId']
                                            else:
                                                return await invis_embed(ctx,
                                                                         f'No user found with the name `{userConverted.display_name}`')
                                            Id = tempRBXID
                                            async with session.get(f'https://users.roblox.com/v1/users/{Id}') as r:
                                                requestJson = await r.json()
                        except discord.ext.commands.MemberNotFound:
                            return await invis_embed(ctx, f'No member found with the query: `{user}`')

    print(requestJson)
    try:
        data = requestJson['data']
    except KeyError:
        data = [requestJson]

    if not 'data' in locals():
        data = [requestJson]

    Embeds = []

    for dataItem in data:
        embed = discord.Embed(
            title=dataItem['name'],
            color=0x2E3136
        )

        Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
            dataItem['id'])

        user = await bot.warnings.find_by_id(dataItem['name'].lower())
        if user is None:
            embed.description = """<:ArrowRightW:1035023450592514048>**Warnings:** 0\n<:ArrowRightW:1035023450592514048>**Kicks:** 0\n<:ArrowRightW:1035023450592514048>**Bans:** 0\n`Banned:` <:ErrorIcon:1035000018165321808>"""
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
            embed.description = f"""<:ArrowRightW:1035023450592514048>**Warnings:** {warnings}\n<:ArrowRightW:1035023450592514048>**Kicks:** {kicks}\n<:ArrowRightW:1035023450592514048>**Bans:** {bans}\n`Banned:` {banned}"""

        embed.set_thumbnail(url=Headshot_URL)
        embed.set_footer(text=f'Select the Check to confirm that {dataItem["name"]} is the user you wish to punish.')

        Embeds.append(embed)

    if ctx.interaction:
        interaction = ctx
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
                        value=f"<:ArrowRightW:1035023450592514048> {ctx.author.mention}",
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

        shift = await bot.shifts.find_by_id(ctx.guild.id)
        if shift is not None:
            if 'data' in shift.keys():
                for item in shift['data']:
                    if isinstance(item, dict):
                        if item['guild'] == ctx.guild.id:
                            if 'moderations' in item.keys():
                                item['moderations'].append({
                                    'id': next(generator),
                                    "Type": "BOLO",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                })
                            else:
                                item['moderations'] = [{
                                    'id': next(generator),
                                    "Type": "BOLO",
                                    "Reason": reason,
                                    "Moderator": [ctx.author.name, ctx.author.id],
                                    "Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
                                    "Guild": ctx.guild.id
                                }]

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
        embed = discord.Embed(
            title="<:ErrorIcon:1035000018165321808> Cancelled",
            description="<:ArrowRight:1035003246445596774>This BOLO has not been logged.",
            color=0xff3c3c
        )

        await menu.message.edit(embed=embed)
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
@app_commands.describe(user="What is the user you want to search for? This is a ROBLOX username.")
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
    embed = discord.Embed(title=user, color=0x2E3136)
    embed.set_thumbnail(url=Headshot_URL)

    for warningItem in dataItem['warnings']:
        if warningItem['Type'].upper() == "BOLO" and warningItem['Guild'] == ctx.guild.id:
            embed.add_field(name="<:WarningIcon:1035258528149033090> BOLO",
                            value=f"<:ArrowRightW:1035023450592514048> **Reason:** {warningItem['Reason']}\n<:ArrowRightW:1035023450592514048> **Type:** {warningItem['Type']}\n<:ArrowRightW:1035023450592514048> **Moderator:** {warningItem['Moderator'][0]}\n<:ArrowRightW:1035023450592514048> **Time:** {warningItem['Time']}\n<:ArrowRightW:1035023450592514048> **ID:** {warningItem['id']}",
                            inline=False)
    Embeds.append(embed)
    try:
        new_embeds = []
        for i in Embeds:
            print(i)
            if i is not None:
                new_embeds.append(i)
        if new_embeds[0].description in [None, ""]:
            return await invis_embed(ctx, f'**{user}** does not have any BOLOs.')
        await ctx.send(embeds=new_embeds)
    except Exception as e:
        print(e)
        return await invis_embed(ctx, f'**{user}** does not have any BOLOs.')


@duty.command(
    name="on",
    description="Allows for you to clock in. [Shift Management]",
    with_app_command=True,
)
@is_staff()
async def dutyon(ctx):
    await invis_embed(ctx,
                      'This command is now a legacy command. We recommend that you now use `/duty manage` instead.')
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

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
                try:
                    await ctx.author.add_roles(rl)
                except:
                    await invis_embed(ctx, f'Could not add {rl.name} to {ctx.author.mention}')


@bolo.command(
    name='void',
    description='Remove a warning from a user. [Punishments]',
    with_app_command=True
)
@is_staff()
@app_commands.describe(
    id="What is the ID of the BOLO you would like to void? You can find this by running /bolo lookup.")
async def bolo_void(ctx, id: str):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!',
                                 ephemeral=True, delete_after=5)

    try:
        id = int(id)
    except:
        return await invis_embed(ctx, '`id` is not a valid ID.')

    keyStorage = None
    selected_item = None
    selected_items = []
    item_index = 0

    async for item in bot.warnings.db.find({'warnings': {'$elemMatch': {'id': id}}}):
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
                                 'There is more than one BOLO associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this BOLO since it is unsafe to continue.')

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

    view = RemoveBOLO(ctx.author.id)
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
    await invis_embed(ctx,
                      'This command is now a legacy command. We recommend that you now use `/duty manage` instead.')
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

    time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
        shift['startTimestamp']).replace(tzinfo=None)

    break_seconds = 0
    if 'breaks' in shift.keys():
        for item in shift["breaks"]:
            if item['ended'] == None:
                item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
            startTimestamp = item['started']
            endTimestamp = item['ended']
            break_seconds += int(endTimestamp - startTimestamp)

    time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text='Staff Logging Module')

    embed.add_field(
        name="<:MalletWhite:1035258530422341672> Type",
        value="<:ArrowRight:1035003246445596774> Clocking out.",
        inline=False
    )

    embed.add_field(
        name="<:Clock:1035308064305332224> Elapsed Time",
        value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
        inline=False
    )

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
        data = await bot.shift_storage.find_by_id(ctx.author.id)

        if "shifts" in data.keys():
            if data['shifts'] is None:
                data['shifts'] = []

            if data['shifts'] == []:
                shifts = [
                    {
                        'name': ctx.author.name,
                        'startTimestamp': shift['startTimestamp'],
                        'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        'totalSeconds': time_delta.total_seconds(),
                        'guild': ctx.guild.id
                    }
                ]
            else:
                object = {
                    'name': ctx.author.name,
                    'startTimestamp': shift['startTimestamp'],
                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                    'totalSeconds': time_delta.total_seconds(),
                    'guild': ctx.guild.id
                }
                shiftdata = data['shifts']
                shifts = shiftdata + [object]

            await bot.shift_storage.update_by_id(
                {
                    '_id': ctx.author.id,
                    'shifts': shifts,
                    'totalSeconds': sum(
                        [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
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
                try:
                    await ctx.author.remove_roles(rl)
                except:
                    await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')


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

    break_seconds = 0

    if 'breaks' in shift.keys():
        for item in shift["breaks"]:
            if item['ended'] == None:
                item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
            startTimestamp = item['started']
            endTimestamp = item['ended']
            break_seconds += int(endTimestamp - startTimestamp)

    string = str(
        ctx.message.created_at.replace(tzinfo=None) -
        datetime.datetime.fromtimestamp(shift['startTimestamp']).replace(tzinfo=None) +
        (datetime.timedelta(seconds=sum(shift.get('added_time'))) if shift.get(
            'added_time') != None else datetime.timedelta(seconds=0))
        - (datetime.timedelta(seconds=sum(shift.get('removed_time'))) if shift.get(
            'removed_time') != None else datetime.timedelta(seconds=0)
           )
    ).split('.')[0]

    breakstr = "(" + str(datetime.timedelta(seconds=break_seconds)).split('.')[
        0] + " on break)" if break_seconds > 0 else ""

    if break_seconds > 0:
        string += " " + breakstr

    embed.add_field(
        name="<:Clock:1035308064305332224> Elapsed Time",
        value=f"<:ArrowRight:1035003246445596774> {string}"
    )

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
                try:
                    await ctx.author.remove_roles(rl)
                except:
                    await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')


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
                try:
                    await ctx.author.remove_roles(rl)
                except:
                    await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')


@duty.command(
    name="modify",
    aliases=["mod"],
    description="Allows for you to modify someone else's shift. [Shift Management]",
    with_app_command=True,
)
@is_management()
async def modify(ctx, member: discord.Member):
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> Your command is loading! We are currently taking our time to ensure that your ERM experience is bug-free!',
                                 ephemeral=True, delete_after=5)
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    has_started = True
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
        has_started = False
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

    view = None
    print(has_started)
    if has_started:
        view = ShiftModify(ctx.author.id)
    else:
        view = PartialShiftModify(ctx.author.id)

    embed = discord.Embed(color=0x2E3136,
                          title="<:Setup:1035006520817090640> Modify {}#{}'s Shift Data".format(member.name,
                                                                                                member.discriminator))
    embed.description = "*You are currently editing {}'s shift. This is not reversible.*".format(member.name)
    embed.set_thumbnail(url=member.display_avatar.url)

    shifts = []
    storage_item = await bot.shift_storage.find_by_id(member.id)
    if storage_item:
        for s in storage_item['shifts']:
            if isinstance(s, dict):
                if s['guild'] == ctx.guild.id:
                    shifts.append(s)

    all_shift_times = [s['totalSeconds'] for s in shifts]
    total_time = sum(all_shift_times)
    print(all_shift_times)
    print(total_time)
    settings = await bot.settings.find_by_id(ctx.guild.id)
    quota = 0
    metquota = ''
    if settings:
        if 'shift_management' in settings.keys():
            if 'quota' in settings['shift_management'].keys():
                quota = settings['shift_management']['quota']

    if total_time >= quota:
        metquota = "Met"
    else:
        metquota = "Not Met"

    embed.add_field(
        name="<:Clock:1035308064305332224> Total Shift Data",
        value="<:ArrowRight:1035003246445596774> {}\n<:ArrowRight:1035003246445596774> {} Quota ({})".format(
            td_format(datetime.timedelta(seconds=total_time)) if td_format(
                datetime.timedelta(seconds=total_time)) != "" else "0 seconds",
            metquota,
            td_format(datetime.timedelta(seconds=quota)) if td_format(
                datetime.timedelta(seconds=quota)) != '' else '0 seconds'
        ),
        inline=False
    )

    print(shift)
    if has_started:
        embed.add_field(
            name="<:Clock:1035308064305332224> Current Shift Data",
            value="<:ArrowRight:1035003246445596774> {}".format(
                td_format(datetime.timedelta(
                    seconds=ctx.message.created_at.replace(tzinfo=None).timestamp() - shift['startTimestamp'] + (
                        sum(shift.get('added_time')) if shift.get('added_time') != None else 0) - (
                                sum(shift.get('removed_time')) if shift.get(
                                    'removed_time') != None else 0))) if td_format(
                    datetime.timedelta(seconds=ctx.message.created_at.replace(tzinfo=None).timestamp() - shift[
                        'startTimestamp'])) != "" else "0 seconds"
            ),
            inline=False
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

        break_seconds = 0
        if 'breaks' in shift.keys():
            for item in shift["breaks"]:
                if item['ended'] == None:
                    item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                startTimestamp = item['started']
                endTimestamp = item['ended']
                break_seconds += int(endTimestamp - startTimestamp)

        time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)

        time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

        added_seconds = 0
        removed_seconds = 0
        if 'added_time' in shift.keys():
            for added in shift['added_time']:
                added_seconds += added

        if 'removed_time' in shift.keys():
            for removed in shift['removed_time']:
                removed_seconds += removed

        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)

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
        if break_seconds > 0:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                inline=False
            )
        else:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                inline=False
            )

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
            data = await bot.shift_storage.find_by_id(member.id)

            if "shifts" in data.keys():
                if data['shifts'] is None:
                    data['shifts'] = []

                if data['shifts'] == []:
                    shifts = [
                        {
                            'name': member.name,
                            'startTimestamp': shift['startTimestamp'],
                            'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'totalSeconds': time_delta.total_seconds(),
                            'guild': ctx.guild.id
                        }
                    ]
                else:
                    object = {
                        'name': member.name,
                        'startTimestamp': shift['startTimestamp'],
                        'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        'totalSeconds': time_delta.total_seconds(),
                        'guild': ctx.guild.id
                    }
                    shiftdata = data['shifts']
                    shifts = shiftdata + [object]

                await bot.shift_storage.update_by_id(
                    {
                        '_id': member.id,
                        'shifts': shifts,
                        'totalSeconds': sum(
                            [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
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
                    try:
                        await member.remove_roles(rl)
                    except:
                        await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')
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
            value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']))}",
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
                    try:
                        await ctx.author.remove_roles(rl)
                    except:
                        await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')
    elif view.value == "add":
        if not has_started:
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
                print('1')
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
                        print('2')
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
                        print('3')
            shift = {
                "guild": ctx.guild.id,
                "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
            }

        timestamp = shift['startTimestamp']
        print('Timestamp: ', timestamp)
        content = (
            await request_response(bot, ctx, "How much time would you like to add to the shift? (s/m/h/d)")).content
        content = content.strip()
        if content.endswith(('s', 'm', 'h', 'd')):
            full = None
            if content.endswith('s'):
                full = "seconds"
                num = int(content[:-1])
                if shift.get('added_time'):
                    shift['added_time'].append(num)
                else:
                    shift['added_time'] = [num]
                print('seconds')
            if content.endswith('m'):
                full = "minutes"
                num = int(content[:-1])
                if shift.get('added_time'):
                    shift['added_time'].append(num * 60)
                else:
                    shift['added_time'] = [num * 60]
                print('minutes')
            if content.endswith('h'):
                full = "hours"
                num = int(content[:-1])
                if shift.get('added_time'):
                    shift['added_time'].append(num * 60 * 60)
                else:
                    shift['added_time'] = [num * 60 * 60]
                print('hours')
            if content.endswith('d'):
                full = "days"
                num = int(content[:-1])
                if shift.get('added_time'):
                    shift['added_time'].append(num * 60 * 60 * 24)
                else:
                    shift['added_time'] = [num * 60 * 60 * 24]
                print('days')
            if has_started:
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
        if not has_started:
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
            shift = {
                "guild": ctx.guild.id,
                "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
            }

        timestamp = shift['startTimestamp']
        dT = datetime.datetime.fromtimestamp(timestamp)
        content = (
            await request_response(bot, ctx,
                                   "How much time would you like to remove from the shift? (s/m/h/d)")).content
        content = content.strip()
        if content.endswith(('s', 'm', 'h', 'd')):
            full = None
            if content.endswith('s'):
                full = "seconds"
                num = int(content[:-1])
                if shift.get('removed_time'):
                    shift['removed_time'].append(num)
                else:
                    shift['removed_time'] = [num]
            if content.endswith('m'):
                full = "minutes"
                num = int(content[:-1])
                if shift.get('removed_time'):
                    shift['removed_time'].append(num * 60)
                else:
                    shift['removed_time'] = [num * 60]
            if content.endswith('h'):
                full = "hours"
                num = int(content[:-1])
                if shift.get('removed_time'):
                    shift['removed_time'].append(num * 60 * 60)
                else:
                    shift['removed_time'] = [num * 60 * 60]
            if content.endswith('d'):
                full = "days"
                num = int(content[:-1])
                if shift.get('removed_time'):
                    shift['removed_time'].append(num * 60 * 60 * 24)
                else:
                    shift['removed_time'] = [num * 60 * 60 * 24]

            if has_started:
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

    if not has_started:
        if view.value in ["add", "remove"]:
            time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                shift['startTimestamp']).replace(tzinfo=None)

            if shift.get('removed_time'):
                time_delta -= datetime.timedelta(seconds=sum(shift['removed_time']))

            if shift.get('added_time'):
                time_delta += datetime.timedelta(seconds=sum(shift['added_time']))

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
                data = await bot.shift_storage.find_by_id(member.id)

                if "shifts" in data.keys():
                    if data['shifts'] is None:
                        data['shifts'] = []

                    if data['shifts'] == []:
                        shifts = [
                            {
                                'name': member.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id
                            }
                        ]
                    else:
                        object = {
                            'name': member.name,
                            'startTimestamp': shift['startTimestamp'],
                            'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'totalSeconds': time_delta.total_seconds(),
                            'guild': ctx.guild.id
                        }
                        shiftdata = data['shifts']
                        shifts = shiftdata + [object]

                    await bot.shift_storage.update_by_id(
                        {
                            '_id': member.id,
                            'shifts': shifts,
                            'totalSeconds': sum(
                                [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
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
                    role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                            configItem['shift_management']['role']]

            if role:
                for rl in role:
                    if rl in member.roles:
                        try:
                            await member.remove_roles(rl)
                        except:
                            await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')


@bot.hybrid_group(
    name='loa',
    description='File a Leave of Absence request [Staff Management]',
    with_app_command=True,
)
@app_commands.describe(time="How long are you going to be on LoA for? (s/m/h/d)")
@app_commands.describe(reason="What is your reason for going on LoA?")
async def loa(ctx, time, *, reason):
    await ctx.invoke(bot.get_command('loa request'), time=time, reason=reason)


@loa.command(
    name='request',
    description='File a Leave of Absence request [Staff Management]',
    with_app_command=True
)
@app_commands.describe(time="How long are you going to be on LoA for? (s/m/h/d)")
@app_commands.describe(reason="What is your reason for going on LoA?")
async def loarequest(ctx, time, *, reason):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        timeObj = reason.split(' ')[-1]
    except:
        timeObj = ""
    reason = list(reason)

    if not time.lower().endswith(('h', 'm', 's', 'd', 'w')):
        reason.insert(0, time)
        if not timeObj.lower().endswith(('h', 'm', 's', 'd', 'w')):
            return await invis_embed(ctx,
                                     'A time must be provided at the start or at the end of the command. Example: `/loa 12h Going to walk my shark` / `/loa Mopping the ceiling 12h`')
        else:
            time = timeObj
            reason.pop()

    if time.lower().endswith('s'):
        time = int(removesuffix(time.lower(), 's'))
    elif time.lower().endswith('m'):
        time = int(removesuffix(time.lower(), 'm')) * 60
    elif time.lower().endswith('h'):
        time = int(removesuffix(time.lower(), 'h')) * 60 * 60
    elif time.lower().endswith('d'):
        time = int(removesuffix(time.lower(), 'd')) * 60 * 60 * 24
    elif time.lower().endswith('w'):
        time = int(removesuffix(time.lower(), 'w')) * 60 * 60 * 24 * 7

    startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
    endTimestamp = int(startTimestamp + time)

    embed = discord.Embed(
        title="Leave of Absence",
        color=0x2E3136
    )

    try:
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Staff Logging Module")

    except:
        pass
    embed.add_field(
        name="<:staff:1035308057007230976> Staff Member",
        value=f"<:ArrowRight:1035003246445596774>{ctx.author.mention}",
        inline=False
    )

    embed.add_field(
        name="<:Resume:1035269012445216858> Start",
        value=f'<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>',
        inline=False
    )

    embed.add_field(
        name="<:Pause:1035308061679689859> End",
        value=f'<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>',
        inline=False
    )

    reason = ''.join(reason)

    embed.add_field(
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
    msg = await channel.send(embed=embed, view=view)

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

    if ctx.interaction:
        await ctx.interaction.response.send_message(embed=successEmbed, ephemeral=True)
    else:
        await ctx.send(embed=successEmbed)


@loa.command(
    name='void',
    description='Cancel a Leave of Absence request [Staff Management]',
    with_app_command=True
)
@is_management()
@app_commands.describe(user="Who's LoA are you voiding? Specify a Discord user.")
async def loavoid(ctx, user: discord.Member = None):
    if ctx.interaction:
        await ctx.defer()

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

    if 'privacy_mode' in configItem['staff_management'].keys():
        if configItem['staff_management']['privacy_mode'] == True:
            mentionable = "Management"
        else:
            mentionable = ctx.author.mention
    else:
        mentionable = ctx.author.mention
    if view.value == True:
        await bot.loas.delete_by_id(loa['_id'])
        await invis_embed(ctx, f'**{user.display_name}\'s** LoA has been voided.')
        success = discord.Embed(
            title=f"<:ErrorIcon:1035000018165321808> {loa['type']} Voided",
            description=f"<:ArrowRightW:1035023450592514048>{mentionable} has voided your {loa['type']}.",
            color=0xff3c3c
        )
        success.set_footer(text="Staff Management Module")

        try:
            await ctx.guild.get_member(loa['user_id']).send(embed=success)
            if isinstance(loa_role, int):
                if loa_role in [role.id for role in user.roles]:
                    await user.remove_roles(discord.utils.get(ctx.guild.roles, id=loa_role))
            elif isinstance(loa_role, list):
                for role in loa_role:
                    if role in [r.id for r in user.roles]:
                        await user.remove_roles(discord.utils.get(ctx.guild.roles, id=role))

        except:
            await invis_embed(ctx, 'Could not remove the LOA role from the user.')

    else:
        return await invis_embed(ctx, 'Cancelled.')


@duty.command(
    name="manage",
    description="Manage your own shift in an easy way! [Shift Management]"
)
@is_staff()
async def manage(ctx):
    if ctx.interaction:
        await ctx.interaction.response.defer()

    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
    except:
        return await invis_embed(ctx,
                                 f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

    if not configItem['shift_management']['enabled']:
        return await invis_embed(ctx, 'Shift management is not enabled on this server.')

    shift = None
    if await bot.shifts.find_by_id(ctx.author.id):
        if 'data' in (await bot.shifts.find_by_id(ctx.author.id)).keys():
            var = (await bot.shifts.find_by_id(ctx.author.id))['data']
            print(var)

            for item in var:
                if item['guild'] == ctx.guild.id:
                    parent_item = await bot.shifts.find_by_id(ctx.author.id)
                    shift = item
        else:
            if 'guild' in (await bot.shifts.find_by_id(ctx.author.id)).keys():
                if (await bot.shifts.find_by_id(ctx.author.id))['guild'] == ctx.guild.id:
                    shift = (await bot.shifts.find_by_id(ctx.author.id))
    print(shift)
    view = ModificationSelectMenu(ctx.author.id)

    embed = discord.Embed(
        color=0x2E3136,
        title=f"<:Clock:1035308064305332224> {ctx.author.name}#{ctx.author.discriminator}'s Shift Panel"
    )

    quota_seconds = None
    met_quota = None
    member_seconds = 0
    ordinal_place = None
    ordinal_formatted = None

    if 'quota' in configItem['shift_management'].keys():
        quota_seconds = configItem['shift_management']['quota']

    all_staff = [{"id": None, "total_seconds": 0, "quota_seconds": 0}]

    datetime_obj = datetime.datetime.now()
    ending_period = datetime_obj
    starting_period = datetime_obj - datetime.timedelta(days=7)

    async for document in bot.shift_storage.db.find({"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
        total_seconds = 0
        quota_seconds = 0
        for shift_doc in document['shifts']:
            if isinstance(shift_doc, dict):
                if shift_doc['guild'] == ctx.guild.id:
                    total_seconds += int(shift_doc['totalSeconds'])
                    if shift_doc['startTimestamp'] >= starting_period.timestamp():
                        quota_seconds += int(shift_doc['totalSeconds'])
                        if document['_id'] not in [item['id'] for item in all_staff]:
                            all_staff.append({"id": document['_id'], "total_seconds": total_seconds,
                                              "quota_seconds": quota_seconds})
                        else:
                            for item in all_staff:
                                if item['id'] == document['_id']:
                                    item['total_seconds'] = total_seconds
                                    item['quota_seconds'] = quota_seconds
                    else:
                        if document['_id'] not in [item['id'] for item in all_staff]:
                            all_staff.append({'id': document['_id'], 'total_seconds': total_seconds})
                        else:
                            for item in all_staff:
                                if item['id'] == document['_id']:
                                    item['total_seconds'] = total_seconds

    if len(all_staff) == 0:
        return await invis_embed(ctx, 'No shifts were made in your server.')
    for item in all_staff:
        if item['id'] is None:
            all_staff.remove(item)

    sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

    for index, value in enumerate(sorted_staff):
        member = discord.utils.get(ctx.guild.members, id=value['id'])
        if member:
            if member.id == ctx.author.id:
                member_seconds = value['total_seconds']
                if quota_seconds is not None:
                    if value['total_seconds'] > quota_seconds:
                        met_quota = "Met "
                    else:
                        met_quota = "Not met"
                    ordinal_place = index + 1
                else:
                    met_quota = "Not met"
                    ordinal_place = index + 1

    ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])  # NOQA: E731
    ms_delta = datetime.timedelta(seconds=member_seconds)

    if ordinal_place is not None:
        ordinal_formatted = ordinal(ordinal_place)

    if td_format(ms_delta) != "":
        embed.add_field(
            name="<:Search:1035353785184288788> Previous Shift Data",
            value=f"<:ArrowRight:1035003246445596774>{td_format(ms_delta)}\n<:ArrowRight:1035003246445596774>{met_quota} Quota\n<:ArrowRight:1035003246445596774>{ordinal_formatted} Place for Shift Time",
            inline=False
        )
    status = None

    print(shift)
    if shift:
        if 'on_break' in shift.keys():
            if shift['on_break']:
                status = "break"
            else:
                status = "on"
        else:
            status = "on"
    else:
        status = "off"

    embed.add_field(
        name="<:Setup:1035006520817090640> Shift Management",
        value=f"<:CurrentlyOnDuty:1045079678353932398> **On-Duty** {'(Current)' if status == 'on' else ''}\n<:Break:1045080685012062329> **On-Break** {'(Current)' if status == 'break' else ''}\n<:OffDuty:1045081161359183933> **Off-Duty** {'(Current)' if status == 'off' else ''}",
    )
    if status == "on" or status == "break":
        warnings = 0
        kicks = 0
        bans = 0
        ban_bolos = 0
        custom = 0
        if 'moderations' in shift.keys():
            for item in shift['moderations']:
                if item["Type"] == "Warning":
                    warnings += 1
                elif item["Type"] == "Kick":
                    kicks += 1
                elif item["Type"] == "Ban" or item['Type'] == "Temporary Ban":
                    bans += 1
                elif item["Type"] == "BOLO":
                    ban_bolos += 1
                else:
                    custom += 1

        time_delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(shift['startTimestamp'])

        embed2 = discord.Embed(
            title=f"<:Clock:1035308064305332224> {ctx.author.name}#{ctx.author.discriminator}'s Current Shift",
            color=0x2E3136
        )

        embed2.add_field(
            name="<:Search:1035353785184288788> Moderation Details",
            value="<:ArrowRight:1035003246445596774> {} Warnings\n<:ArrowRight:1035003246445596774> {} Kicks\n<:ArrowRight:1035003246445596774> {} Bans\n<:ArrowRight:1035003246445596774> {} Ban BOLOs\n<:ArrowRight:1035003246445596774> {} Custom".format(
                warnings, kicks, bans, ban_bolos, custom),
            inline=False
        )

        break_seconds = 0
        if 'breaks' in shift.keys():
            for item in shift['breaks']:
                if item['ended']:
                    break_seconds += item['ended'] - item['started']
                else:
                    break_seconds += datetime.datetime.now().timestamp() - item['started']

        break_seconds = int(break_seconds)

        embed2.add_field(
            name="<:Setup:1035006520817090640> Shift Status",
            value=f"<:ArrowRight:1035003246445596774> {'On-Duty' if status == 'on' else 'On-Break'} {'<:CurrentlyOnDuty:1045079678353932398>' if status == 'on' else '<:Break:1045080685012062329>'}\n<:ArrowRight:1035003246445596774> {td_format(time_delta)} on shift\n<:ArrowRight:1035003246445596774> {len(shift['breaks']) if 'breaks' in shift.keys() else '0'} breaks\n<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else 0} on break",
        )
        msg = await ctx.send(embeds=[embed, embed2], view=view)
    else:
        msg = await ctx.send(embed=embed, view=view)
    await view.wait()
    if not view.value:
        return

    if view.value == "on":
        if status == "on":
            return await invis_embed(ctx, "You are already on-duty. You can go off-duty by selecting **Off-Duty**.")
        elif status == "break":
            for item in shift['breaks']:
                if item['ended'] is None:
                    item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
            for data in parent_item['data']:
                if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                    data['breaks'] = shift['breaks']
                    data['on_break'] = False
                    break
            await bot.shifts.update_by_id(parent_item)

            if configItem['shift_management']['role']:
                if not isinstance(configItem['shift_management']['role'], list):
                    role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                else:
                    role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                            configItem['shift_management']['role']]

            if role:
                for rl in role:
                    if rl not in ctx.author.roles:
                        try:
                            await ctx.author.add_roles(rl)
                        except:
                            await invis_embed(ctx, f'Could not add {rl.name} to {ctx.author.mention}')

            success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Break Ended",
                description="<:ArrowRight:1035003246445596774> You are no longer on break.",
                color=0x71c15f
            )
            await msg.edit(embed=success, view=None)
        else:
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
            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success",
                description="<:ArrowRight:1035003246445596774> Your shift is now active.",
                color=0x71c15f
            )

            role = None

            if configItem['shift_management']['role']:
                if not isinstance(configItem['shift_management']['role'], list):
                    role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                else:
                    role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                            configItem['shift_management']['role']]

            if role:
                for rl in role:
                    if not rl in ctx.author.roles:
                        try:
                            await ctx.author.add_roles(rl)
                        except:
                            await invis_embed(ctx, f'Could not add {rl.name} to {ctx.author.mention}')

            await msg.edit(embed=successEmbed, view=None)
    elif view.value == "off":
        break_seconds = 0
        if shift:
            if 'breaks' in shift.keys():
                for item in shift["breaks"]:
                    if item['ended'] == None:
                        item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                    startTimestamp = item['started']
                    endTimestamp = item['ended']
                    break_seconds += int(endTimestamp - startTimestamp)
        else:
            return await invis_embed(ctx, "You are not on-duty. You can go on-duty by selecting **On-Duty**.")
        if status == "off":
            return await invis_embed(ctx, "You are already off-duty. You can go on-duty by selecting **On-Duty**.")

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

        time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)

        time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

        added_seconds = 0
        removed_seconds = 0
        if 'added_time' in shift.keys():
            for added in shift['added_time']:
                added_seconds += added

        if 'removed_time' in shift.keys():
            for removed in shift['removed_time']:
                removed_seconds += removed

        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)

        if break_seconds > 0:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                inline=False
            )
        else:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                inline=False
            )

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Shift Ended",
            description="<:ArrowRight:1035003246445596774> Your shift has now ended.",
            color=0x71c15f
        )

        await msg.edit(embed=successEmbed, view=None)

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
            data = await bot.shift_storage.find_by_id(ctx.author.id)

            if "shifts" in data.keys():
                if data['shifts'] is None:
                    data['shifts'] = []

                if data['shifts'] == []:
                    shifts = [
                        {
                            'name': ctx.author.name,
                            'startTimestamp': shift['startTimestamp'],
                            'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'totalSeconds': time_delta.total_seconds(),
                            'guild': ctx.guild.id
                        }
                    ]
                else:
                    object = {
                        'name': ctx.author.name,
                        'startTimestamp': shift['startTimestamp'],
                        'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        'totalSeconds': time_delta.total_seconds(),
                        'guild': ctx.guild.id
                    }
                    shiftdata = data['shifts']
                    shifts = shiftdata + [object]

                await bot.shift_storage.update_by_id(
                    {
                        '_id': ctx.author.id,
                        'shifts': shifts,
                        'totalSeconds': sum(
                            [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
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
                    try:
                        await ctx.author.remove_roles(rl)
                    except:
                        await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')
    elif view.value == "break":
        if status == "off":
            return await invis_embed(ctx,
                                     'You cannot be on break if you are not currently on-duty. If you would like to be on-duty, pick **On-Duty**')
        toggle = "on"

        if 'breaks' in shift.keys():
            for item in shift['breaks']:
                if item['ended'] is None:
                    toggle = "off"

        if toggle == "on":
            if 'breaks' in shift.keys():
                shift['breaks'].append({
                    'started': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                    'ended': None
                })
            else:
                shift['breaks'] = [{
                    'started': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                    'ended': None
                }]
            shift['on_break'] = True
            for data in parent_item['data']:
                if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                    data['breaks'] = shift['breaks']
                    data['on_break'] = True
                    break
            await bot.shifts.update_by_id(parent_item)
            success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Break Started",
                description="<:ArrowRight:1035003246445596774> You are now on break.",
                color=0x71c15f
            )
            await msg.edit(embed=success, view=None)

            if configItem['shift_management']['role']:
                if not isinstance(configItem['shift_management']['role'], list):
                    role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                else:
                    role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                            configItem['shift_management']['role']]

            if role:
                for rl in role:
                    if rl in ctx.author.roles:
                        try:
                            await ctx.author.remove_roles(rl)
                        except:
                            await invis_embed(ctx, f'Could not remove {rl.name} from {ctx.author.mention}')

        else:
            for item in shift['breaks']:
                if item['ended'] is None:
                    item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
            for data in parent_item['data']:
                if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                    data['breaks'] = shift['breaks']
                    data['on_break'] = False
                    break
            await bot.shifts.update_by_id(parent_item)
            success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Break Ended",
                description="<:ArrowRight:1035003246445596774> You are no longer on break.",
                color=0x71c15f
            )
            await msg.edit(embed=success, view=None)
            if configItem['shift_management']['role']:
                if not isinstance(configItem['shift_management']['role'], list):
                    role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                else:
                    role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                            configItem['shift_management']['role']]

            if role:
                for rl in role:
                    if not rl in ctx.author.roles:
                        try:
                            await ctx.author.add_roles(rl)
                        except:
                            await invis_embed(ctx, f'Could not add {rl.name} to {ctx.author.mention}')


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
@app_commands.describe(time="How long are you going to be on LoA for? (s/m/h/d)")
@app_commands.describe(reason="What is your reason for going on LoA?")
async def rarequest(ctx, time, *, reason):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if configItem is None:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    try:
        timeObj = reason.split(' ')[-1]
    except:
        timeObj = ""
    reason = list(reason)

    if not time.lower().endswith(('h', 'm', 's', 'd', 'w')):
        reason.insert(0, time)
        if not timeObj.lower().endswith(('h', 'm', 's', 'd', 'w')):
            return await invis_embed(ctx,
                                     'A time must be provided at the start or at the end of the command. Example: `/ra 12h Going to walk my shark` / `/ra Mopping the ceiling 12h`')
        else:
            time = timeObj
            reason.pop()

    if time.lower().endswith('s'):
        time = int(removesuffix(time.lower(), 's'))
    elif time.lower().endswith('m'):
        time = int(removesuffix(time.lower(), 'm')) * 60
    elif time.lower().endswith('h'):
        time = int(removesuffix(time.lower(), 'h')) * 60 * 60
    elif time.lower().endswith('d'):
        time = int(removesuffix(time.lower(), 'd')) * 60 * 60 * 24
    elif time.lower().endswith('w'):
        time = int(removesuffix(time.lower(), 'w')) * 60 * 60 * 24 * 7

    startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
    endTimestamp = int(startTimestamp + time)

    embed = discord.Embed(
        title="Reduced Activity",
        color=0x2E3136
    )

    try:
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Staff Logging Module")

    except:
        pass
    embed.add_field(
        name="<:staff:1035308057007230976> Staff Member",
        value=f"<:ArrowRight:1035003246445596774>{ctx.author.mention}",
        inline=False
    )

    embed.add_field(
        name="<:Resume:1035269012445216858> Start",
        value=f'<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>',
        inline=False
    )

    embed.add_field(
        name="<:Pause:1035308061679689859> End",
        value=f'<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>',
        inline=False
    )

    reason = ''.join(reason)

    embed.add_field(
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

    msg = await channel.send(embed=embed, view=view)

    example_schema = {"_id": f"{ctx.author.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
                      "user_id": ctx.author.id, "guild_id": ctx.guild.id, "message_id": msg.id, "type": "RA",
                      "expiry": int(endTimestamp),
                      "expired": False, "accepted": False, "denied": False, "reason": ''.join(reason)}

    await bot.loas.insert(example_schema)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Sent RA Request",
        description="<:ArrowRight:1035003246445596774> I've sent your RA request to a Management member of this server.",
        color=0x71c15f
    )

    if ctx.interaction:
        await ctx.interaction.response.send_message(embed=successEmbed, ephemeral=True)
    else:
        await ctx.send(embed=successEmbed)


@ra.command(
    name='void',
    description='Cancel a Reduced Activity request [Staff Management]',
    with_app_command=True
)
@is_management()
@app_commands.describe(user="Who's RA are you trying to void?")
async def ravoid(ctx, user: discord.Member = None):
    if ctx.interaction:
        await ctx.defer()

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

    ra_var = None
    for l in await bot.loas.get_all():
        if l['user_id'] == user.id and l['guild_id'] == ctx.guild.id and l['type'] == "RA" and l['expired'] == False:
            ra_var = l
            break

    if ra_var is None:
        return await invis_embed(ctx, f"{user.display_name} is currently not on RA.")

    embed = discord.Embed(
        description=f'<:WarningIcon:1035258528149033090> **Are you sure you would like to clear {user.display_name}\'s RA?**\n**End date:** <t:{ra_var["expiry"]}>',
        color=0x2E3136)
    embed.set_footer(text="Staff Management Module")
    view = YesNoMenu(ctx.author.id)

    await ctx.send(embed=embed, view=view)
    await view.wait()
    if 'privacy_mode' in configItem['staff_management'].keys():
        if configItem['staff_management']['privacy_mode'] == True:
            mentionable = "Management"
        else:
            mentionable = ctx.author.mention
    else:
        mentionable = ctx.author.mention
    if view.value == True:
        await bot.loas.delete_by_id(ra_var['_id'])
        await invis_embed(ctx, f'**{user.display_name}\'s** RA has been voided.')
        success = discord.Embed(
            title=f"<:ErrorIcon:1035000018165321808> {ra_var['type']} Voided",
            description=f"<:ArrowRightW:1035023450592514048>{mentionable} has voided your {ra_var['type']}.",
            color=0xff3c3c
        )
        success.set_footer(text="Staff Management Module")

        try:
            await ctx.guild.get_member(ra_var['user_id']).send(embed=success)
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
        break_seconds = 0
        if 'breaks' in shift.keys():
            for item in shift["breaks"]:
                if item['ended'] == None:
                    item['ended'] = interaction.message.created_at.replace(tzinfo=None).timestamp()
                startTimestamp = item['started']
                endTimestamp = item['ended']
                break_seconds += int(endTimestamp - startTimestamp)

        time_delta = interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)

        time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

        added_seconds = 0
        removed_seconds = 0
        if 'added_time' in shift.keys():
            for added in shift['added_time']:
                added_seconds += added

        if 'removed_time' in shift.keys():
            for removed in shift['removed_time']:
                removed_seconds += removed

        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)

        embed = discord.Embed(title=member.name, color=0x2E3136)
        try:
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value="<:ArrowRight:1035003246445596774> Clocking out.", inline=False)
        if break_seconds > 0:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                inline=False
            )
        else:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                inline=False
            )

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
            data = await bot.shift_storage.find_by_id(member.id)

            if "shifts" in data.keys():
                if data['shifts'] is None:
                    data['shifts'] = []

                if data['shifts'] == []:
                    shifts = [
                        {
                            'name': member.name,
                            'startTimestamp': shift['startTimestamp'],
                            'endTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
                            'totalSeconds': time_delta.total_seconds(),
                            'guild': interaction.guild.id
                        }
                    ]
                else:
                    object = {
                        'name': member.name,
                        'startTimestamp': shift['startTimestamp'],
                        'endTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
                        'totalSeconds': time_delta.total_seconds(),
                        'guild': interaction.guild.id
                    }
                    shiftdata = data['shifts']
                    shifts = shiftdata + [object]

                await bot.shift_storage.update_by_id(
                    {
                        '_id': member.id,
                        'shifts': shifts,
                        'totalSeconds': sum(
                            [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
                    }
                )
            else:
                await bot.shift_storage.update_by_id({
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
                    try:
                        await member.remove_roles(rl)
                    except:
                        try:
                            await int_invis_embed(interaction, f'Could not remove {rl.name} from {member.mention}')
                        except:
                            pass


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
        if time.lower().endswith('s'):
            time = int(removesuffix(time.lower(), 's'))
        elif time.lower().endswith('m'):
            time = int(removesuffix(time.lower(), 'm')) * 60
        elif time.lower().endswith('h'):
            time = int(removesuffix(time.lower(), 'h')) * 60 * 60
        elif time.lower().endswith('d'):
            time = int(removesuffix(time.lower(), 'd')) * 60 * 60 * 24
        elif time.lower().endswith('w'):
            time = int(removesuffix(time.lower(), 'w')) * 60 * 60 * 24 * 7
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

    embed = discord.Embed(title="<:Resume:1035269012445216858> Remove a reminder", color=0x2E3136)

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


@bot.hybrid_group(
    name='custom'
)
@is_management()
async def custom(ctx):
    pass


@custom.command(
    name="add",
    description="Add a custom command. [Custom Commands]",
)
@is_management()
async def add(ctx):
    Data = await bot.custom_commands.find_by_id(ctx.guild.id)

    view = AddCustomCommand(ctx.author.id)

    await ctx.send(view=view)
    await view.wait()
    await view.view.wait()
    await view.view.newView.wait()

    try:
        name = view.information['name']
    except:
        return await invis_embed(ctx, 'This has been successfully cancelled.')
    embeds = []
    resultingMessage = view.view.newView.msg
    for embed in resultingMessage.embeds:
        embeds.append(embed.to_dict())

    custom_command_data = {
        "_id": ctx.guild.id,
        "commands": [
            {
                "name": name,
                "id": next(generator),
                "message": {
                    "content": resultingMessage.content,
                    "embeds": embeds
                }
            }
        ]
    }

    if Data:
        Data['commands'].append({
            "name": name,
            "id": next(generator),
            "message": {
                "content": resultingMessage.content,
                "embeds": embeds
            }
        })
    else:
        Data = custom_command_data

    await bot.custom_commands.upsert(Data)
    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Success!",
        description=f"<:ArrowRight:1035003246445596774> Your custom command has been added successfully.",
        color=0x71c15f
    )
    await ctx.send(embed=successEmbed)


async def command_autocomplete(
        interaction: discord.Interaction,
        current: str) -> typing.List[app_commands.Choice[str]]:
    Data = await bot.custom_commands.find_by_id(interaction.guild.id)
    if Data is None:
        return [discord.app_commands.Choice(name='No custom commands found', value="NULL")]
    else:
        commands = []
        for command in Data['commands']:
            if current not in ["", " "]:
                if command['name'].startswith(current) or current in command['name'] or command['name'].endswith(
                        current):
                    commands.append(command['name'])
            else:
                commands.append(command['name'])
        if len(commands) == 0:
            return [discord.app_commands.Choice(name='No custom commands found', value="NULL")]

        print(commands)
        commandList = []
        for command in commands:
            if command not in [""]:
                commandList.append(discord.app_commands.Choice(name=command, value=command))
            else:
                cmd = None
                for c in Data['commands']:
                    if c['name'].lower() == command.lower():
                        cmd = c
                commandList.append(
                    discord.app_commands.Choice(name=cmd['message']['content'][:20].replace(' ', '').lower(),
                                                value=cmd['name']))
        return commandList


@custom.command(
    name="run",
    description="Run a custom command. [Custom Commands]",
)
@app_commands.autocomplete(command=command_autocomplete)
@is_management()
@app_commands.describe(command="What custom command would you like to run?")
@app_commands.describe(channel="Where do you want this custom command's output to go? (e.g. #general)")
async def run(ctx, command: str, channel: discord.TextChannel = None):
    if not channel:
        channel = ctx.channel
    Data = await bot.custom_commands.find_by_id(ctx.guild.id)
    if Data is None:
        return await invis_embed(ctx, 'There are no custom commands associated with this server.')
    is_command = False
    selected = None
    if 'commands' in Data.keys():
        if isinstance(Data['commands'], list):
            for cmd in Data['commands']:
                if cmd['name'].lower().replace(' ', '') == command.lower().replace(' ', ''):
                    is_command = True
                    selected = cmd

    if not is_command:
        return await invis_embed(ctx, 'There is no custom command with the associated name.')

    embeds = []
    for embed in selected['message']['embeds']:
        embeds.append(await interpret_embed(bot, ctx, channel, embed))

    await channel.send(content=await interpret_content(bot, ctx, channel, selected['message']['content']),
                       embeds=embeds)
    if ctx.interaction:
        await int_invis_embed(ctx.interaction, "Successfully ran this custom command!", ephemeral=True)
    else:
        await invis_embed(ctx, "Successfully ran this custom command!")


@custom.command(
    name="remove",
    description="Remove a custom command. [Custom Commands]",
)
@is_management()
async def remove(ctx):
    Data = await bot.custom_commands.find_by_id(ctx.guild.id)
    if Data is None:
        Data = {
            '_id': ctx.guild.id,
            "commands": []
        }

    embed = discord.Embed(title="<:Resume:1035269012445216858> Remove a custom command", color=0x2E3136)
    for item in Data['commands']:
        embed.add_field(name=f"<:Clock:1035308064305332224> {item['name']}",
                        value=f"<:ArrowRightW:1035023450592514048> **Name:** {item['name']}\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}",
                        inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name="<:Clock:1035308064305332224> No custom commands",
                        value="<:ArrowRightW:1035023450592514048> No custom commands have been added.", inline=False)
        return await ctx.send(embed=embed)

    view = RemoveCustomCommand(ctx.author.id)

    await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.value == "delete":
        name = (await request_response(bot, ctx,
                                       "What custom command would you like to delete? (e.g. `1`)\n*Specify the ID to delete the custom command.*")).content

        for item in Data['commands']:
            if item['id'] == int(name):
                Data['commands'].remove(item)
                await bot.custom_commands.upsert(Data)
                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Command Removed",
                    description="<:ArrowRight:1035003246445596774> Your custom command has been removed successfully.",
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
                if rl not in member.roles:
                    try:
                        await member.add_roles(rl)
                    except:
                        try:
                            await int_invis_embed(interaction, f'Could not add {rl.name} to {member.mention}')
                        except:
                            pass


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

    timedelta = datetime.datetime.now() - datetime.datetime.fromtimestamp(shift["startTimestamp"])

    if 'added_time' in shift.keys():
        timedelta += datetime.timedelta(seconds=shift['added_time'])

    if 'removed_time' in shift.keys():
        timedelta -= datetime.timedelta(seconds=shift['removed_time'])

    await int_invis_embed(interaction, f'{member.display_name} has been on-shift for {td_format(timedelta)}.',
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

        break_seconds = 0
        if 'breaks' in shift.keys():
            for item in shift["breaks"]:
                if item['ended'] == None:
                    item['ended'] = interaction.message.created_at.replace(tzinfo=None).timestamp()
                startTimestamp = item['started']
                endTimestamp = item['ended']
                break_seconds += int(endTimestamp - startTimestamp)

        time_delta = interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
            shift['startTimestamp']).replace(tzinfo=None)

        time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

        added_seconds = 0
        removed_seconds = 0
        if 'added_time' in shift.keys():
            for added in shift['added_time']:
                added_seconds += added

        if 'removed_time' in shift.keys():
            for removed in shift['removed_time']:
                removed_seconds += removed

        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)

        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                        value=f"<:ArrowRight:1035003246445596774> Voided time, performed by ({interaction.user.mention}).",
                        inline=False)

        if break_seconds > 0:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                inline=False
            )
        else:
            embed.add_field(
                name="<:Clock:1035308064305332224> Elapsed Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                inline=False
            )

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
                    try:
                        await member.remove_roles(rl)
                    except:
                        try:
                            await int_invis_embed(interaction, f'Could not remove {rl.name} from {member.mention}')
                        except:
                            pass


# clockedin, to get all the members of a specific guild currently on duty
@duty.command(name='active', description='Get all members of the server currently on shift. [Shift Management]',
              aliases=['ac', 'ison'])
@is_staff()
async def clockedin(ctx):
    configItem = await bot.settings.find_by_id(ctx.guild.id)
    if not configItem:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    embed = discord.Embed(title='<:Resume:1035269012445216858> Currently on Shift', color=0x2E3136)
    try:
        embed.set_footer(text="Staff Logging Module")
    except:
        pass

    async for shift in bot.shifts.db.find({"data": {"$elemMatch": {"guild": ctx.guild.id}}}):
        if 'data' in shift.keys():
            for s in shift['data']:
                if s['guild'] == ctx.guild.id:
                    member = discord.utils.get(ctx.guild.members, id=shift['_id'])
                    if member:
                        print(s)
                        time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                            s['startTimestamp']).replace(tzinfo=None)
                        break_seconds = 0
                        if 'breaks' in s.keys():
                            for item in s["breaks"]:
                                if item['ended'] == None:
                                    break_seconds = ctx.message.created_at.replace(tzinfo=None).timestamp() - item[
                                        'started']

                        time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

                        added_seconds = 0
                        removed_seconds = 0
                        if 'added_time' in s.keys():
                            for added in s['added_time']:
                                added_seconds += added

                        if 'removed_time' in s.keys():
                            for removed in s['removed_time']:
                                removed_seconds += removed

                        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)

                        if f"<:staff:1035308057007230976> {member.name}#{member.discriminator}" not in [field.name for
                                                                                                        field in
                                                                                                        embed.fields]:
                            if break_seconds > 0:
                                embed.add_field(
                                    name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} (Currently on break: {td_format(datetime.timedelta(seconds=break_seconds))})",
                                    inline=False)
                            else:
                                embed.add_field(
                                    name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                                    inline=False)

        elif 'guild' in shift.keys():
            if shift['guild'] == ctx.guild.id:
                member = discord.utils.get(ctx.guild.members, id=shift['_id'])
                if member:
                    time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                        shift['startTimestamp']).replace(tzinfo=None)
                    break_seconds = 0
                    if 'breaks' in shift.keys():
                        for item in shift["breaks"]:
                            if item['ended'] == None:
                                break_seconds = ctx.message.created_at.replace(tzinfo=None).timestamp() - item[
                                    'started']

                    time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

                    added_seconds = 0
                    removed_seconds = 0
                    if 'added_time' in shift.keys():
                        for added in shift['added_time']:
                            added_seconds += added

                    if 'removed_time' in shift.keys():
                        for removed in shift['removed_time']:
                            removed_seconds += removed

                    time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                    time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)

                    if f"<:staff:1035308057007230976> {member.name}#{member.discriminator}" not in [field.name for field
                                                                                                    in embed.fields]:
                        if break_seconds > 0:
                            embed.add_field(name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                                            value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} (Currently on break: {datetime.timedelta(seconds=break_seconds)})",
                                            inline=False)
                        else:
                            embed.add_field(name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                                            value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                                            inline=False)

    await ctx.send(embed=embed)


# staff info command, to get total seconds worked on a specific member
@duty.command(name='info', description='Get the total seconds worked on a specific member. [Shift Management]',
              aliases=['i', "stats"])
@is_staff()
@app_commands.describe(member="Who's stats do you want to see?")
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
    if ctx.interaction:
        await int_coloured_embed(ctx.interaction,
                                 '<a:Loading:1044067865453670441> We are currently loading the shift leaderboard.',
                                 ephemeral=True, delete_after=10)

    try:
        configItem = await bot.settings.find_by_id(ctx.guild.id)
    except:
        return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

    all_staff = [{"id": None, "total_seconds": 0}]

    async for document in bot.shift_storage.db.find({"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
        total_seconds = 0
        for shift in document['shifts']:
            if isinstance(shift, dict):
                if shift['guild'] == ctx.guild.id:
                    if shift['totalSeconds'] > 0:
                        total_seconds += int(shift['totalSeconds'])
                        if document['_id'] not in [item['id'] for item in all_staff]:
                            all_staff.append({'id': document['_id'], 'total_seconds': total_seconds})
                        else:
                            for item in all_staff:
                                if item['id'] == document['_id']:
                                    item['total_seconds'] = total_seconds

    if len(all_staff) == 0:
        return await invis_embed(ctx, 'No shifts were made in your server.')
    for item in all_staff:
        if item['id'] is None:
            all_staff.remove(item)

    sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

    buffer = None
    embeds = []

    embed = discord.Embed(
        color=0x2E3136,
        title="<:SettingIcon:1035353776460152892> Duty Leaderboard"
    )

    embeds.append(embed)
    print(sorted_staff)
    for i in sorted_staff:
        try:
            member = await ctx.guild.fetch_member(i["id"])
        except:
            member = None
        print(member)
        if member:
            if buffer is None:
                print('buffer none')
                buffer = "%s - %s" % (
                    f"{member.name}#{member.discriminator}", td_format(datetime.timedelta(seconds=i['total_seconds'])))
            else:
                print('buffer not none')
                buffer = buffer + "\n%s - %s" % (
                    f"{member.name}#{member.discriminator}", td_format(datetime.timedelta(seconds=i['total_seconds'])))
            if len(embeds[-1].fields) <= 24:
                print('fields less than 24')
                embeds[-1].add_field(name=f'<:staff:1035308057007230976> {member.name}#{member.discriminator}',
                                     value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=i['total_seconds']))}",
                                     inline=False)
            else:
                print('fields more than 24')
                new_embed = discord.Embed(
                    color=0x2E3136,
                    title="<:SettingIcon:1035353776460152892> Duty Leaderboard"
                )

                print(new_embed)
                new_embed.add_field(name=f'<:staff:1035308057007230976> {member.name}#{member.discriminator}',
                                    value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=i['total_seconds']))}",
                                    inline=False)
                embeds.append(new_embed)
    print(all_staff)
    print(sorted_staff)
    print(buffer)
    try:
        bbytes = buffer.encode('utf-8')
    except Exception as e:
        print(e)
        if len(embeds) == 0:
            return await invis_embed(ctx, 'No shift data has been found.')
        elif embeds[0].description == None:
            return await invis_embed(ctx, 'No shift data has been found.')
        else:
            if ctx.interaction:
                interaction = ctx
            else:
                interaction = ctx

            menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
            for embed in embeds:
                if embed is not None:
                    menu.add_pages([embed])

            if len(menu.pages) == 1:
                return await ctx.send(embed=embed)

            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            await menu.start()

    if len(embeds) == 1:
        new_embeds = []
        for i in embeds:
            new_embeds.append(i)
        await ctx.send(embeds=new_embeds, file=discord.File(fp=BytesIO(bbytes), filename='shift_leaderboard.txt'))
    else:
        file = discord.File(fp=BytesIO(bbytes), filename='shift_leaderboard.txt')
        if ctx.interaction:
            interaction = ctx
        else:
            interaction = ctx

        menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)
        for embed in embeds:
            if embed is not None:
                menu.add_pages([embed])

        if len(menu.pages) == 1:
            return await ctx.send(embed=embed, file=file)

        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        await menu.start()
        await ctx.send(file=file)


@duty.command(name='clear',
              description='Clears all of a member\'s shift data. [Shift Management]',
              aliases=['shift-cl'])
@is_management()
@app_commands.describe(member="Who's shift data would you like to clear?")
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
        doc_shifts = document['shifts']
        if isinstance(document['shifts'], list):
            for shift in document['shifts']:
                print(shift)
                if isinstance(shift, dict):
                    if shift['guild'] == ctx.guild.id:
                        document['shifts'].remove(shift)
                        if '_id' in document.keys():
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

    async for document in bot.shift_storage.db.find({"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
        if 'shifts' in document.keys():
            for shift in document['shifts']:
                if isinstance(shift, dict):
                    if shift['guild'] == ctx.guild.id:
                        document['shifts'].remove(shift)
            await bot.shift_storage.db.replace_one({'_id': document['_id']}, document)

    successEmbed = discord.Embed(
        title="<:CheckIcon:1035018951043842088> Success!",
        description=f"<:ArrowRight:1035003246445596774> All shifts from your server have been cleared.",
        color=0x71c15f
    )

    await ctx.send(embed=successEmbed)


if __name__ == "__main__":
    sentry_sdk.init(
        sentry_url,
        traces_sample_rate=1.0,
        _experiments={
            "profiles_sample_rate": 1.0,
        }
    )

    bot.run(bot_token)
