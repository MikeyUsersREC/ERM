import json
import logging
import pprint
import time
from dataclasses import MISSING
from pkgutil import iter_modules

import aiohttp
import discord.mentions
import dns.resolver
import motor.motor_asyncio
import sentry_sdk
from decouple import config
from discord import app_commands
from discord.ext import tasks
from roblox import client as roblox
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from snowflake import SnowflakeGenerator
from zuid import ZUID

from menus import LOAMenu, \
    CompleteReminder
from utils.mongo import Document
from utils.utils import *

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

try:
    sentry_url = config('SENTRY_URL')
    bloxlink_api_key = config('BLOXLINK_API_KEY')
except:
    sentry_url = ""
    bloxlink_api_key = ""

discord.utils.setup_logging(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

credentials_dict = {}
scope = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"

]


class Bot(commands.AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id in [459374864067723275,
                       906383042841563167, 877195103335231558]:  # Implement your own conditions here
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
        bot.views = Document(bot.db, 'views')
        bot.synced_users = Document(bot.db, 'synced_users')
        bot.consent = Document(bot.db, 'consent')


        Extensions = [m.name for m in iter_modules(['cogs'], prefix='cogs.')]
        Events = [m.name for m in iter_modules(['events'], prefix='events.')]

        for extension in Extensions:
            try:
                await bot.load_extension(extension)
                logging.info(f'Loaded {extension}')
            except Exception as e:
                logging.error(f'Failed to load extension {extension}.', exc_info=e)


        for extension in Events:
            try:
                await bot.load_extension(extension)
                logging.info(f'Loaded {extension}')
            except Exception as e:
                logging.error(f'Failed to load extension {extension}.', exc_info=e)

        bot.error_list = []
        logging.info('Connected to MongoDB!')

        await bot.load_extension('jishaku')
        # await bot.load_extension('utils.server')

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

        async for document in self.views.db.find({}):
            if document['view_type'] == "LOAMenu":
                for index, item in enumerate(document['args']):
                    if item == "SELF":
                        document['args'][index] = self
                self.add_view(LOAMenu(*document['args']), message_id=document['message_id'])


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
async def AutoDefer(ctx: commands.Context):
    analytics = await bot.analytics.find_by_id(ctx.command.full_parent_name + f" {ctx.command.name}")
    if not analytics:
        await bot.analytics.insert({"_id": ctx.command.full_parent_name + f" {ctx.command.name}", "uses": 1})
    else:
        await bot.analytics.update_by_id(
            {"_id": ctx.command.full_parent_name + f" {ctx.command.name}", "uses": analytics["uses"] + 1})

    if ctx.command:
        if ctx.command.extras.get('ephemeral') is True:
            if ctx.interaction:
                return await ctx.defer(ephemeral=True)
    await ctx.defer()


client = roblox.Client()


def is_staff():
    async def predicate(ctx):
        print(vars(ctx.bot))
        guild_settings = await ctx.bot.settings.find_by_id(ctx.guild.id)
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

async def management_predicate(ctx):
    guild_settings = await ctx.bot.settings.find_by_id(ctx.guild.id)
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

def is_management():
    return commands.check(management_predicate)


async def check_privacy(bot: Bot, guild: int, setting: str):
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
    separation = []
    # Separate the User IDs into bundles of 120
    for value in jsonData['moderations']:
        if len(separation) == 0:
            separation.append([value['userId']])
        else:
            if len(separation[-1]) == 110:
                separation.append([value['userId']])
            else:
                separation[-1].append(value['userId'])

    for sep in separation:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://users.roblox.com/v1/users', json={
                "userIds": sep,
                "excludeBannedUsers": True
            }) as r:
                try:
                    requestJSON = await r.json()
                except Exception as e:
                    print(e)

        print(f'Request JSON: {requestJSON}')
        for user in requestJSON['data']:
            pprint.pprint(user)
            name = user['name']
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


bot.erm_team = {
    "i_imikey": "Bot Developer",
    "mbrinkley": "Community Manager",
    "theoneandonly_5567": "Executive Manager",
    "royalcrests": "Website Developer & Asset Designer",
}


async def staff_field(embed, query):
    flag = await bot.flags.find_by_id(query)
    embed.add_field(name="<:FlagIcon:1035258525955395664> Flags",
                    value=f"<:ArrowRight:1035003246445596774> {flag['rank']}",
                    inline=False)
    return embed


bot.warning_json_to_mongo = warning_json_to_mongo

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
    mongo_url = config('MONGO_URL', default=None)
    github_token = config('GITHUB_TOKEN', default=None)
except:
    mongo_url = ""
    github_token = ""
generator = SnowflakeGenerator(192)
error_gen = ZUID(prefix="error_", length=10)
system_code_gen = ZUID(prefix="erm-systems-", length=7)



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
                    searches = bot.warnings.db.find({'_id': {"$regex": f"{current.lower()}"}})

                    choices = []
                    index = 0
                    async for search in searches:
                        if index >= 25:
                            break
                        else:
                            index += 1
                            choices.append(discord.app_commands.Choice(name=search['_id'], value=search['_id']))
                    if not choices:
                        searches = bot.warnings.db.find().sort(
                            [("$natural", -1)]).limit(25)
                        async for search in searches:
                            choices.append(discord.app_commands.Choice(name=search['_id'], value=search['_id']))
                    return choices







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
        if guild is not None:
            if guild.member_count is not None:
                users += guild.member_count

    status = f"{users:,} users"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))


@tasks.loop(hours=24)
async def GDPR():
    # if the date in each warning is more than 30 days ago, redact the staff's username and tag
    # using mongodb (warnings)
    # get all warnings
    # iterate through each warning, to check the date via the time variable stored in "d/m/y h:m:s"
    async for userentry in bot.warnings.db.find({}):
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
    async for guildObj in bot.reminders.db.find({}):
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

                    if item.get('completion_ability') and item.get('completion_ability') is True:
                        view = CompleteReminder()
                    else:
                        view = None
                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Notification",
                        description=f"{item['message']}",
                        color=0x2E3136
                    )
                    lastTriggered = tD.timestamp()
                    item['lastTriggered'] = lastTriggered
                    await bot.reminders.update_by_id(guildObj)


                    await channel.send(" ".join(roles), embed=embed, view = view)
            except Exception as e:
                print('Could not send reminder: {}'.format(str(e)))
                pass


@tasks.loop(minutes=1)
async def check_loa():
    loas = bot.loas

    async for loaObject in bot.loas.db.find({}):
        if datetime.datetime.utcnow().timestamp() > loaObject['expiry'] and loaObject["expired"] == False:
            if loaObject['accepted'] is True:
                loaObject['expired'] = True
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
                                    roles = [
                                        discord.utils.get(guild.roles, id=settings['staff_management']['loa_role'])]
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
                                    for rl in roles and rl is not None:
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



discord.utils.setup_logging(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

scope = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"

]

credentials_dict = {
    "type": config("TYPE", default=None),
    "project_id": config("PROJECT_ID", default=None),
    "private_key_id": config("PRIVATE_KEY_ID", default=None),
    "private_key": config("PRIVATE_KEY", default=None).replace("\\n", '\n'),
    "client_email": config("CLIENT_EMAIL", default=None),
    "client_id": config("CLIENT_ID", default=None),
    "auth_uri": config("AUTH_URI", default=None),
    "token_uri": config("TOKEN_URI", default=None),
    "auth_provider_x509_cert_url": config("AUTH_PROVIDER_X509_CERT_URL", default=None),
    "client_x509_cert_url": config("CLIENT_X509_CERT_URL", default=None),
}

if __name__ == "__main__":
    sentry_sdk.init(
        dsn=sentry_url,
        traces_sample_rate=1.0,
        integrations=[
            PyMongoIntegration()
        ],
        _experiments={
            "profiles_sample_rate": 1.0,
        }
    )

    bot.run(bot_token)
