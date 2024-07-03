import datetime
import json
import logging
import time
from dataclasses import MISSING
from pkgutil import iter_modules
import re
try:
    import Levenshtein
    from fuzzywuzzy import fuzz, process
except ImportError:
    from fuzzywuzzy import fuzz, process

import aiohttp
import decouple
import discord.mentions
import dns.resolver
import motor.motor_asyncio
import asyncio
import pytz
import sentry_sdk
from decouple import config
from discord import app_commands
from discord.ext import tasks
from roblox import client as roblox
from sentry_sdk import push_scope, capture_exception
from sentry_sdk.integrations.pymongo import PyMongoIntegration

from datamodels.CustomFlags import CustomFlags
from datamodels.ServerKeys import ServerKeys
from datamodels.ShiftManagement import ShiftManagement
from datamodels.ActivityNotice import ActivityNotices
from datamodels.Analytics import Analytics
from datamodels.Consent import Consent
from datamodels.CustomCommands import CustomCommands
from datamodels.Errors import Errors
from datamodels.FiveMLinks import FiveMLinks
from datamodels.LinkStrings import LinkStrings
from datamodels.PunishmentTypes import PunishmentTypes
from datamodels.Reminders import Reminders
from datamodels.Settings import Settings
from datamodels.APITokens import APITokens
from datamodels.StaffConnections import StaffConnections
from datamodels.Views import Views
from datamodels.Actions import Actions
from datamodels.Warnings import Warnings
from datamodels.ProhibitedUseKeys import ProhibitedUseKeys
from datamodels.PendingOAuth2 import PendingOAuth2
from datamodels.OAuth2Users import OAuth2Users
from datamodels.IntegrationCommandStorage import IntegrationCommandStorage
from menus import CompleteReminder, LOAMenu, RDMActions
from utils.viewstatemanger import ViewStateManager
from utils.bloxlink import Bloxlink
from utils.prc_api import PRCApiClient
from utils.prc_api import ResponseFailure
from utils.utils import *
from utils.constants import *
import utils.prc_api

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8"]
setup = False

try:
    sentry_url = config("SENTRY_URL")
    bloxlink_api_key = config("BLOXLINK_API_KEY")
except decouple.UndefinedValueError:
    sentry_url = ""
    bloxlink_api_key = ""

discord.utils.setup_logging(level=logging.DEBUG)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

credentials_dict = {}
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


class Bot(commands.AutoShardedBot):

    async def close(self):
        for session in self.external_http_sessions:
            if session is not None and session.closed is False:
                await session.close()
        await super().close()

    async def is_owner(self, user: discord.User):
        # Only developers of the bot on the team should have
        # full access to Jishaku commands. Hard-coded
        # IDs are a security vulnerability.

        # Else fall back to the original
        if user.id == 1165311055728226444:
            return True
        
        return await super().is_owner(user)

    async def setup_hook(self) -> None:
        self.external_http_sessions: list[aiohttp.ClientSession] = []
        self.view_state_manager: ViewStateManager = ViewStateManager()

        global setup
        if not setup:
            # await bot.load_extension('utils.routes')
            logging.info(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{} is online!".format(
                    self.user.name
                )
            )
            self.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(mongo_url))
            if environment == "DEVELOPMENT":
                self.db = self.mongo["beta"]
            elif environment == "PRODUCTION":
                self.db = self.mongo["erm"]
            elif environment == "ALPHA":
                self.db = self.mongo['alpha']
            else:
                raise Exception("Invalid environment")

            self.start_time = time.time()
            self.shift_management = ShiftManagement(self.db, "shift_management")
            self.errors = Errors(self.db, "errors")
            self.loas = ActivityNotices(self.db, "leave_of_absences")
            self.reminders = Reminders(self.db, "reminders")
            self.custom_commands = CustomCommands(self.db, "custom_commands")
            self.analytics = Analytics(self.db, "analytics")
            self.punishment_types = PunishmentTypes(self.db, "punishment_types")
            self.custom_flags = CustomFlags(self.db, "custom_flags")
            self.views = Views(self.db, "views")
            self.api_tokens = APITokens(self.db, "api_tokens")
            self.link_strings = LinkStrings(self.db, "link_strings")
            self.fivem_links = FiveMLinks(self.db, "fivem_links")
            self.consent = Consent(self.db, "consent")
            self.punishments = Warnings(self)
            self.settings = Settings(self.db, "settings")
            self.server_keys = ServerKeys(self.db, "server_keys")
            self.staff_connections = StaffConnections(self.db, "staff_connections")
            self.ics = IntegrationCommandStorage(self.db, 'logged_command_data')
            self.actions = Actions(self.db, "actions")
            self.prohibited = ProhibitedUseKeys(self.db, "prohibited_keys")

            self.pending_oauth2 = PendingOAuth2(self.db, "pending_oauth2")
            self.oauth2_users = OAuth2Users(self.db, "oauth2")

            self.roblox = roblox.Client()
            self.prc_api = PRCApiClient(self, base_url=config('PRC_API_URL'), api_key=config('PRC_API_KEY'))
            self.bloxlink = Bloxlink(self, config('BLOXLINK_API_KEY'))

            Extensions = [m.name for m in iter_modules(["cogs"], prefix="cogs.")]
            Events = [m.name for m in iter_modules(["events"], prefix="events.")]
            BETA_EXT = ["cogs.StaffConduct"]
            EXTERNAL_EXT = ["utils.api"]
            [Extensions.append(i) for i in EXTERNAL_EXT]


            for extension in Extensions:
                try:
                    if extension not in BETA_EXT:
                        await self.load_extension(extension)
                        logging.info(f"Loaded {extension}")
                    elif environment == "DEVELOPMENT" or environment == "ALPHA":
                        await self.load_extension(extension)
                        logging.info(f"Loaded {extension}")
                except Exception as e:
                    logging.error(f"Failed to load extension {extension}.", exc_info=e)

            for extension in Events:
                try:
                    await self.load_extension(extension)
                    logging.info(f"Loaded {extension}")
                except Exception as e:
                    logging.error(f"Failed to load extension {extension}.", exc_info=e)

            bot.error_list = []
            logging.info("Connected to MongoDB!")

            # await bot.load_extension("jishaku")
            await bot.load_extension("utils.hot_reload")
            # await bot.load_extension('utils.server')

            if not bot.is_synced:  # check if slash commands have been synced
                bot.tree.copy_global_to(guild=discord.Object(id=987798554972143728))
            if environment == "DEVELOPMENT":
                await bot.tree.sync(guild=discord.Object(id=987798554972143728))
            else:
                pass
                # Prevent auto syncing
                # await bot.tree.sync()
                # guild specific: leave blank if global (global registration can take 1-24 hours)
            bot.is_synced = True
            check_reminders.start()
            check_loa.start()
            iterate_ics.start()
            # GDPR.start()
            iterate_prc_logs.start()
            statistics_check.start()
            tempban_checks.start()
            check_whitelisted_car.start()
            change_status.start()
            logging.info("Setup_hook complete! All tasks are now running!")

            async for document in self.views.db.find({}):
                if document["view_type"] == "LOAMenu":
                    for index, item in enumerate(document["args"]):
                        if item == "SELF":
                            document["args"][index] = self
                    loa_id = document['args'][3]
                    if isinstance(loa_id, dict):
                        loa_expiry = loa_id['expiry']
                        if loa_expiry < datetime.datetime.now().timestamp():
                            await self.views.delete_by_id(document['_id'])
                            continue
                    self.add_view(
                        LOAMenu(*document["args"]), message_id=document["message_id"]
                    )
            setup = True


bot = Bot(
    command_prefix=get_prefix,
    case_insensitive=True,
    intents=intents,
    help_command=None,
    allowed_mentions=discord.AllowedMentions(
        replied_user=False, everyone=False, roles=False
    ),
)
bot.debug_servers = [987798554972143728]
bot.is_synced = False
bot.shift_management_disabled = False
bot.punishments_disabled = False
bot.bloxlink_api_key = bloxlink_api_key
environment = config("ENVIRONMENT", default="DEVELOPMENT")
internal_command_storage = {}

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
    analytics = await bot.analytics.find_by_id(
        ctx.command.full_parent_name + f" {ctx.command.name}"
    )
    if not analytics:
        await bot.analytics.insert(
            {"_id": ctx.command.full_parent_name + f" {ctx.command.name}", "uses": 1}
        )
    else:
        await bot.analytics.update_by_id(
            {
                "_id": ctx.command.full_parent_name + f" {ctx.command.name}",
                "uses": analytics["uses"] + 1,
            }
        )

    internal_command_storage[ctx] = datetime.datetime.now(tz=pytz.UTC).timestamp()
    if ctx.command:
        if ctx.command.extras.get("ephemeral") is True:
            if ctx.interaction:
                return await ctx.defer(ephemeral=True)
        if ctx.command.extras.get("ignoreDefer") is True:
            return
        await ctx.defer()

@bot.after_invoke
async def loggingCommandExecution(ctx: commands.Context):
    if ctx in internal_command_storage.keys():
        logging.info("Command " + ctx.command.name + " was run by " + ctx.author.name + " (" + str(ctx.author.id) + ")" + " and lasted {} seconds".format(str(float(datetime.datetime.now(tz=pytz.UTC).timestamp() - internal_command_storage[ctx]))))
        logging.info(("Shard ID ::: " + str(ctx.guild.shard_id)) if ctx.guild is not None else 'Shard ID ::: {}'.format("-1, Direct Messages"))
    else:
        logging.info("Command could not be found in internal context storage. Please report.")
    del internal_command_storage[ctx]


client = roblox.Client()


async def staff_check(bot_obj, guild, member):
    guild_settings = await bot_obj.settings.find_by_id(guild.id)
    if guild_settings:
        if "role" in guild_settings["staff_management"].keys():
            if guild_settings["staff_management"]["role"] != "":
                if isinstance(guild_settings["staff_management"]["role"], list):
                    for role in guild_settings["staff_management"]["role"]:
                        if role in [role.id for role in member.roles]:
                            return True
                elif isinstance(guild_settings["staff_management"]["role"], int):
                    if guild_settings["staff_management"]["role"] in [
                        role.id for role in member.roles
                    ]:
                        return True
    if member.guild_permissions.manage_messages:
        return True
    return False


async def management_check(bot_obj, guild, member):
    guild_settings = await bot_obj.settings.find_by_id(guild.id)
    if guild_settings:
        if "management_role" in guild_settings["staff_management"].keys():
            if guild_settings["staff_management"]["management_role"] != "":
                if isinstance(
                    guild_settings["staff_management"]["management_role"], list
                ):
                    for role in guild_settings["staff_management"]["management_role"]:
                        if role in [role.id for role in member.roles]:
                            return True
                elif isinstance(
                    guild_settings["staff_management"]["management_role"], int
                ):
                    if guild_settings["staff_management"]["management_role"] in [
                        role.id for role in member.roles
                    ]:
                        return True
    if member.guild_permissions.manage_guild:
        return True
    return False

async def admin_check(bot_obj, guild, member):
    guild_settings = await bot_obj.settings.find_by_id(guild.id)
    if guild_settings:
        if "admin_role" in guild_settings["staff_management"].keys():
            if guild_settings["staff_management"]["admin_role"] != "":
                if isinstance(guild_settings["staff_management"]["admin_role"], list):
                    for role in guild_settings["staff_management"]["admin_role"]:
                        if role in [role.id for role in member.roles]:
                            return True
                elif isinstance(guild_settings["staff_management"]["admin_role"], int):
                    if guild_settings["staff_management"]["admin_role"] in [role.id for role in member.roles]:
                        return True
        if "management_role" in guild_settings["staff_management"].keys():
            if guild_settings["staff_management"]["management_role"] != "":
                if isinstance(guild_settings["staff_management"]["management_role"], list):
                    for role in guild_settings["staff_management"]["management_role"]:
                        if role in [role.id for role in member.roles]:
                            return True
                elif isinstance(guild_settings["staff_management"]["management_role"], int):
                    if guild_settings["staff_management"]["management_role"] in [role.id for role in member.roles]:
                        return True
    if member.guild_permissions.administrator:
        return True
    return False


async def staff_predicate(ctx):
    if ctx.guild is None:
        return True
    else:
        return await staff_check(ctx.bot, ctx.guild, ctx.author)


def is_staff():
    return commands.check(staff_predicate)

async def admin_predicate(ctx):
    if ctx.guild is None:
        return True
    else:
        return await admin_check(ctx.bot, ctx.guild, ctx.author)
    
def is_admin():
    return commands.check(admin_predicate)

async def management_predicate(ctx):
    if ctx.guild is None:
        return True
    else:
        return await management_check(ctx.bot, ctx.guild, ctx.author)


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
    with open(f"{jsonName}", "r") as f:
        logging.info(f)
        f = json.load(f)

    logging.info(f)

    for key, value in f.items():
        structure = {"_id": key.lower(), "warnings": []}
        logging.info([key, value])
        logging.info(key.lower())

        if await bot.warnings.find_by_id(key.lower()):
            data = await bot.warnings.find_by_id(key.lower())
            for item in data["warnings"]:
                structure["warnings"].append(item)

        for item in value:
            item.pop("ID", None)
            item["id"] = next(generator)
            item["Guild"] = guildId
            structure["warnings"].append(item)

        logging.info(structure)

        if await bot.warnings.find_by_id(key.lower()) == None:
            await bot.warnings.insert(structure)
        else:
            await bot.warnings.update(structure)


bot.erm_team = {
    "i_imikey": "Bot Developer",
    "mbrinkley": "First Community Manager - Removed",
    "theoneandonly_5567": "Executive Manager",
    "royalcrests": "Website Developer & Asset Designer",
    "1friendlydoge": "Data Scientist - a friendly doge",
}


async def staff_field(bot: Bot, embed, query):
    flag = await bot.flags.find_by_id(query)
    embed.add_field(
        name="<:ERMAdmin:1111100635736187011> Flags",
        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{flag['rank']}",
        inline=False,
    )
    return embed


bot.warning_json_to_mongo = warning_json_to_mongo

# include environment variables
if environment == "PRODUCTION":
    bot_token = config("PRODUCTION_BOT_TOKEN")
    logging.info("Using production token...")
elif environment == "DEVELOPMENT":
    try:
        bot_token = config("DEVELOPMENT_BOT_TOKEN")
    except decouple.UndefinedValueError:
        bot_token = ""
    logging.info("Using development token...")
elif environment == "ALPHA":
    try:
        bot_token = config('ALPHA_BOT_TOKEN')
    except decouple.UndefinedValueError:
        bot_token = ""
    logging.info('Using ERM V4 Alpha token...')
else:
    raise Exception("Invalid environment")
try:
    mongo_url = config("MONGO_URL", default=None)
except decouple.UndefinedValueError:
    mongo_url = ""


# status change discord.ext.tasks


@tasks.loop(hours=1)
async def change_status():
    await bot.wait_until_ready()
    logging.info("Changing status")
    status = "⚡️ /about | ermbot.xyz"
    await bot.change_presence(
        activity=discord.CustomActivity(name=status)
    )

@tasks.loop(minutes=1)
async def check_reminders():
    try:
        async for guildObj in bot.reminders.db.find({}):
            new_go = await bot.reminders.db.find_one(guildObj)
            g_id = new_go['_id']
            for item in new_go["reminders"].copy():
                try:
                    if item.get("paused") is True:
                        continue

                    if not new_go.get('_id'):
                        new_go['_id'] = g_id
                    dT = datetime.datetime.now()
                    interval = item["interval"]

                    tD = dT + datetime.timedelta(seconds=interval)

                    if tD.timestamp() - item["lastTriggered"] >= interval:
                        guild = bot.get_guild(int(guildObj["_id"]))
                        if not guild:
                            continue
                        channel = guild.get_channel(int(item["channel"]))
                        if not channel:
                            continue

                        roles = []
                        try:
                            for role in item["role"]:
                                roles.append(guild.get_role(int(role)).mention)
                        except TypeError:
                            roles = [""]

                        if (
                            item.get("completion_ability")
                            and item.get("completion_ability") is True
                        ):
                            view = CompleteReminder()
                        else:
                            view = None
                        embed = discord.Embed(
                            title="Notification",
                            description=f"{item['message']}",
                            color=BLANK_COLOR,
                        )
                        lastTriggered = tD.timestamp()
                        item["lastTriggered"] = lastTriggered
                        await bot.reminders.update_by_id(new_go)


                        if isinstance(item.get('integration'), dict):
                            # This has the ERLC integration enabled
                            command = 'h' if item['integration']['type'] == 'Hint' else ('m' if item['integration']['type'] == 'Message' else None)
                            content = item['integration']['content']
                            total = ':' + command + ' ' + content
                            if await bot.server_keys.db.count_documents({'_id': channel.guild.id}) != 0:
                                do_not_complete = False
                                try:
                                    status = await bot.prc_api.get_server_status(channel.guild.id)
                                except prc_api.ResponseFailure as e:
                                    do_not_complete = True
                                print(status)
                                
                                if not do_not_complete:
                                    resp = await bot.prc_api.run_command(channel.guild.id, total)
                                    if resp[0] != 200:
                                        print('Failed reaching PRC due to {} status code'.format(resp))
                                    else:
                                        print('Integration success with 200 status code')
                                else:
                                    print(f'Cancelled execution of reminder for {channel.guild.id} - {e.status_code}')

                        if not view:
                            await channel.send(" ".join(roles), embed=embed,
                                allowed_mentions = discord.AllowedMentions(
                                    replied_user=True, everyone=True, roles=True, users=True
                            ))
                        else:
                            await channel.send(" ".join(roles), embed=embed, view=view,
                                               allowed_mentions=discord.AllowedMentions(
                                                   replied_user=True, everyone=True, roles=True, users=True
                                               ))
                except Exception as e:
                    # print(e)
                    pass
    except Exception as e:
        # print(e)
        pass

@tasks.loop(minutes=1, reconnect=True)
async def tempban_checks():
    # This will check for expired time bans
    # and for servers which have this feature enabled
    # to automatically remove the ban in-game
    # using POST /server/command

    # This will also use a GET request before
    # sending that POST request, particularly
    # GET /server/bans

    # We also check if the punishment item is 
    # before the update date, because else we'd
    # have too high influx of invalid
    # temporary bans

    # For diagnostic purposes, we also choose to
    # capture the amount of time it takes for this
    # event to run, as it may cause issues in
    # time registration.

    cached_servers = {}
    initial_time = time.time()
    async for punishment_item in bot.punishments.db.find({
        "Epoch": {"$gt": 1709164800},
        "CheckExecuted": {"$exists": False},
        "UntilEpoch": {"$lt": int(datetime.datetime.now(tz=pytz.UTC).timestamp())},
        "Type": "Temporary Ban"
    }):
        try:
            await bot.fetch_guild(punishment_item['Guild'])
        except discord.HTTPException:
            continue
        
        if not cached_servers.get(punishment_item['Guild']):
            try:
                cached_servers[punishment_item['Guild']] = await bot.prc_api.fetch_bans(punishment_item['Guild'])
            except:
                continue


        punishment_item['CheckExecuted'] = True
        await bot.punishments.update_by_id(punishment_item)

        if punishment_item['UserID'] not in [i.user_id for i in cached_servers[punishment_item['Guild']]]:
            continue

        sorted_punishments = sorted([i async for i in bot.punishments.db.find({"UserID": punishment_item['UserID'], "Guild": punishment_item['Guild']})], key=lambda x: x['Epoch'], reverse=True)
        new_sorted_punishments = []
        for item in sorted_punishments:
            if item == punishment_item:
                break
            new_sorted_punishments.append(item)
        
        if any([i['Type'] in ["Ban", "Temporary Ban"] for i in new_sorted_punishments]):
            continue
            
        await bot.prc_api.unban_user(punishment_item['Guild'], punishment_item['user_id'])
    del cached_servers
    end_time = time.time()
    logging.warning('Event tempban_checks took {} seconds'.format(str(end_time - initial_time)))

async def fetch_get_channel(target, identifier):
    channel = target.get_channel(identifier)
    if not channel:
        try:
            channel = await target.fetch_channel(identifier)
        except discord.HTTPException as e:
            channel = None
    return channel

@tasks.loop(minutes=5, reconnect=True)
async def statistics_check():
    initial_time = time.time()

    guilds = bot.settings.db.find({})
    async for guild in guilds:
        guild_id = guild['_id']
        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.errors.NotFound:
            continue

        settings = await bot.settings.find_by_id(guild_id)
        if not settings:
            continue
        try:
            statistics = settings["ERLC"]["statistics"]
        except KeyError:
            continue

        try:
            players: list[Player] = await bot.prc_api.get_server_players(guild_id)
            status: ServerStatus = await bot.prc_api.get_server_status(guild_id)
            queue: int = await bot.prc_api.get_server_queue(guild_id, minimal=True)
        except prc_api.ResponseFailure:
            continue


        on_duty = await bot.shift_management.shifts.db.count_documents({'Guild': guild_id, 'EndEpoch': 0})
        moderators = {len(list(filter(lambda x: x.permission == 'Server Moderator', players)))}
        admins = {len(list(filter(lambda x: x.permission == 'Server Administrator', players)))}
        staff_ingame = {len(list(filter(lambda x: x.permission != 'Normal', players)))}
        current_player = {status.current_players}
        join_code = {status.join_key}
        max_players = {status.max_players}

        tasks = []

        if statistics.get("onduty"):
            tasks.append(update_channel(guild, statistics["onduty"], on_duty, "onduty"))
        if statistics.get("join_code"):
            tasks.append(update_channel(guild, statistics["join_code"], join_code, "join_code"))
        if statistics.get("current_players"):
            tasks.append(update_channel(guild, statistics["current_players"], current_player, "players"))
        if statistics.get("total_players"):
            tasks.append(update_channel(guild, statistics["total_players"], max_players, "max_players"))
        if statistics.get("queue"):
            tasks.append(update_channel(guild, statistics["queue"], queue, "queue"))
        if statistics.get("ingame_staff"):
            tasks.append(update_channel(guild, statistics["ingame_staff"], staff_ingame, "staff"))
        if statistics.get("ingame_mods"):
            tasks.append(update_channel(guild, statistics["ingame_mods"], moderators, "mods"))
        if statistics.get("ingame_admins"):
            tasks.append(update_channel(guild, statistics["ingame_admins"], admins, "admins"))

        await asyncio.gather(*tasks)

    end_time = time.time()
    logging.warning(f"Event statistics_check took {end_time - initial_time} seconds")

async def update_channel(guild, stat, value, placeholder):
    try:
        channel_id = stat["channel"]
        format_string = stat["format"]
        channel = await fetch_get_channel(guild, channel_id)
        if channel:
            format_string = format_string.replace(f"{{{placeholder}}}", str(value))
            await channel.edit(name=format_string)
    except KeyError:
        pass


pm_counter = {}
@tasks.loop(minutes=2, reconnect=True)
async def check_whitelisted_car():
    initial_time = time.time()
    async for items in bot.settings.db.find({'ERLC': {'$exists': True}}):
        guild_id = items['_id']
        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.errors.NotFound:
            continue

        enable_vehicle_restrictions = items['ERLC'].get('enable_vehicle_restrictions', False)
        if not enable_vehicle_restrictions:
            continue

        players: list[Player] = await bot.prc_api.get_server_players(guild_id)
        vehicles: list[prc_api.ActiveVehicle] = await bot.prc_api.get_server_vehicles(guild_id)
        whitelisted_vehicle_roles = items['ERLC'].get('whitelisted_vehicles_roles', [])
        alert_channel_id = items['ERLC'].get('whitelisted_vehicle_alert_channel', 0)
        whitelisted_vehicles = items['ERLC'].get('whitelisted_vehicles', [])
        alert_message = items["ERLC"].get("alert_message", "You do not have the required role to use this vehicle. Switch it or risk being moderated.")

        enable_vehicle_restrictions = items['ERLC'].get('enable_vehicle_restrictions', False)
        if not enable_vehicle_restrictions:
            continue

        if not whitelisted_vehicle_roles or not alert_channel_id:
            continue

        if isinstance(whitelisted_vehicle_roles, int):
            exotic_roles = [guild.get_role(whitelisted_vehicle_roles)]
        elif isinstance(whitelisted_vehicle_roles, list):
            exotic_roles = [guild.get_role(role_id) for role_id in whitelisted_vehicle_roles if guild.get_role(role_id)]
        else:
            continue

        alert_channel = bot.get_channel(alert_channel_id)
        if not alert_channel:
            try:
                alert_channel = await bot.fetch_channel(alert_channel_id)
            except discord.HTTPException:
                alert_channel = None
                continue

        if not exotic_roles or not alert_channel:
            continue
        matched = {}
        for item in vehicles:
            for x in players:
                if x.username == item.username:
                    matched[item] = x

        for vehicle, player in matched.items():
            if any(is_whitelisted(vehicle.vehicle, whitelisted_vehicle) for whitelisted_vehicle in whitelisted_vehicles):
                pattern = re.compile(re.escape(player.username), re.IGNORECASE)
                member_found = False
                for member in guild.members:
                    if pattern.search(member.name) or pattern.search(member.display_name) or (hasattr(member, 'global_name') and member.global_name and pattern.search(member.global_name)):
                        member_found = True
                        has_exotic_role = False
                        for role in exotic_roles:
                            if role in member.roles:
                                has_exotic_role = True
                                break
                        
                        if not has_exotic_role:
                            await run_command(guild_id, player.username, alert_message)

                            if player.username not in pm_counter:
                                pm_counter[player.username] = 1
                            else:
                                pm_counter[player.username] += 1

                            if pm_counter[player.username] >= 4:
                                try:
                                    avatar_url = await get_player_avatar_url(player.id)
                                    embed = discord.Embed(
                                        title="Whitelisted Vehicle Warning",
                                        description=f"""
                                        > Player [{player.username}](https://roblox.com/users/{player.id}/profile) has been PMed 3 times to obtain the required role for their whitelisted vehicle.
                                        """,
                                        color=discord.Color.red(),
                                        timestamp=datetime.datetime.now(tz=pytz.UTC)
                                    ).set_footer(
                                        text=f"Powered by ERM Systems",
                                    ).set_thumbnail(url=avatar_url)
                                    await alert_channel.send(embed=embed)
                                except discord.HTTPException:
                                    pass
                                pm_counter.pop(player.username)
                        break
                    elif member_found == False:
                        await run_command(guild_id, player.username, alert_message)

                        if player.username not in pm_counter:
                            pm_counter[player.username] = 1
                        else:
                            pm_counter[player.username] += 1

                        if pm_counter[player.username] >= 4:
                            try:
                                embed = discord.Embed(
                                    title="Whitelisted Vehicle Warning",
                                    description=f"""
                                    > Player [{player.username}](https://roblox.com/users/{player.id}/profile) has been PMed 3 times to obtain the required role for their whitelisted vehicle.
                                    """,
                                    color=discord.Color.red(),
                                    timestamp=datetime.datetime.now(tz=pytz.UTC)
                                ).set_footer(
                                    text=f"Guild: {guild.name}",
                                )
                                await alert_channel.send(embed=embed)
                            except discord.HTTPException:
                                pass
                            pm_counter.pop(player.username)
            else:
                if player.username in pm_counter.keys():
                    pm_counter.pop(player.username)

    end_time = time.time()
    logging.warning(f"Event check_whitelisted_car took {end_time - initial_time} seconds")
    
async def run_command(guild_id, username, message):
    while True:
        command = f":pm {username} {message}"
        command_response = await bot.prc_api.run_command(guild_id, command)
        if command_response[0] == 200:
            logging.info(f"Sent PM to {username} in guild {guild_id}")
            break
        elif command_response[0] == 429:
            retry_after = int(command_response[1].get('Retry-After', 5))
            logging.warning(f"Rate limited. Retrying after {retry_after} seconds.")
            await asyncio.sleep(retry_after)
        else:
            logging.error(f"Failed to send PM to {username} in guild {guild_id}")
            break

def is_whitelisted(vehicle_name, whitelisted_vehicle):
    vehicle_year_match = re.search(r'\d{4}$', vehicle_name)
    whitelisted_year_match = re.search(r'\d{4}$', whitelisted_vehicle)
    if vehicle_year_match and whitelisted_year_match:
        vehicle_year = vehicle_year_match.group()
        whitelisted_year = whitelisted_year_match.group()
        if vehicle_year != whitelisted_year:
            return False
        vehicle_name_base = vehicle_name[:vehicle_year_match.start()].strip()
        whitelisted_vehicle_base = whitelisted_vehicle[:whitelisted_year_match.start()].strip()
        return fuzz.ratio(vehicle_name_base.lower(), whitelisted_vehicle_base.lower()) > 80
    return False

async def get_guild(guild_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.HTTPException:
            return None
    return guild

async def get_player_avatar_url(player_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={player_id}&size=180x180&format=Png&isCircular=false"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data['data'][0]['imageUrl']

async def fetch_logs(guild_id):
    try:
        kill_logs = await bot.prc_api.fetch_kill_logs(guild_id)
        player_logs = await bot.prc_api.fetch_player_logs(guild_id)
        return kill_logs, player_logs
    except Exception as e:
        channel = await bot.fetch_channel(1213523576603410452)
        await channel.send(content=f"[3] {(str(e) or repr(e))=}")
        await asyncio.sleep(1)
        return None, None
    
async def process_kill_logs(guild, kill_logs_channel, kill_logs, current_timestamp):
    players = {}
    if kill_logs_channel:
        for item in kill_logs:
            if (current_timestamp - item.timestamp) > 75:
                continue

            if item.killer_username not in players:
                players[item.killer_username] = [1, [item]]
            else:
                players[item.killer_username][0] += 1
                players[item.killer_username][1].append(item)

            embed = discord.Embed(
                title="Kill Log",
                color=BLANK_COLOR,
                description=f"[{item.killer_username}](https://roblox.com/users/{item.killer_user_id}/profile) killed [{item.killed_username}](https://roblox.com/users/{item.killed_user_id}/profile) • <t:{int(item.timestamp)}:T>"
            )
            await kill_logs_channel.send(embed=embed)

    return players

async def notify_rdm(guild, players):
    settings = await bot.settings.find_by_id(guild.id)
    channel = await fetch_get_channel(guild, (settings or {}).get('ERLC', {}).get('rdm_channel', 0))    
    if channel:
        for username, value in players.items():
            count, items = value
            if count > 3:
                roblox_player = await bot.roblox.get_user_by_username(username)
                thumbnails = await bot.roblox.thumbnails.get_user_avatar_thumbnails([roblox_player], size=(420, 420))
                thumbnail = thumbnails[0].image_url
                pings = [guild.get_role(role_id).mention for role_id in (settings or {}).get('ERLC', {}).get('rdm_mentionables', []) if guild.get_role(role_id)]

                embed = discord.Embed(
                    title="<:security:1169804198741823538> RDM Detected",
                    color=BLANK_COLOR
                ).add_field(
                    name="User Information",
                    value=(
                        f"> **Username:** {roblox_player.name}\n"
                        f"> **User ID:** {roblox_player.id}\n"
                        f"> **Profile Link:** [Click here](https://roblox.com/users/{roblox_player.id}/profile)\n"
                        f"> **Account Created:** <t:{int(roblox_player.created.timestamp())}>"
                    ),
                    inline=False
                ).add_field(
                    name="Abuse Information",
                    value=(
                        f"> **Type:** Mass RDM\n"
                        f"> **Individuals Affected [{count}]:** {', '.join([f'[{i.killed_username}](https://roblox.com/users/{i.killed_user_id}/profile)' for i in items])}\n"
                        f"> **At:** <t:{int(items[0].timestamp)}>"
                    ),
                    inline=False
                ).set_thumbnail(
                    url=thumbnail
                )

                await channel.send(
                    ', '.join(pings) if pings else '',
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(
                        everyone=True,
                        users=True,
                        roles=True,
                        replied_user=True,
                    ),
                    view=RDMActions(bot)
                )

async def handle_shifts(guild, player_logs, current_timestamp, player_logs_channel):
    settings = await bot.settings.find_by_id(guild.id)
    automatic_shifts_enabled = ((settings.get('ERLC', {}) or {}).get('automatic_shifts', {}) or {}).get('enabled', False)
    automatic_shift_type = ((settings.get('ERLC', {}) or {}).get('automatic_shifts', {}) or {}).get('shift_type', '')

    staff_roles = await get_staff_roles(guild, settings)
    perm_staff = [member for member in guild.members if member.guild_permissions.manage_messages or member.guild_permissions.manage_guild or member.guild_permissions.administrator and not member.bot]

    roblox_to_discord = {int((await bot.oauth2_users.db.find_one({"discord_id": member.id}) or {}).get("roblox_id", 0)): member for member in perm_staff}

    if player_logs_channel:
        for item in player_logs:
            if (current_timestamp - item.timestamp) > 75:
                continue

            if item.user_id in roblox_to_discord:
                if automatic_shifts_enabled:
                    consent_item = await bot.consent.find_by_id(roblox_to_discord[item.user_id].id)
                    if (consent_item or {}).get('auto_shifts', True):
                        shift = await bot.shift_management.get_current_shift(roblox_to_discord[item.user_id], guild.id)
                        if item.type == 'join' and not shift:
                            await bot.shift_management.add_shift_by_user(roblox_to_discord[item.user_id], automatic_shift_type, [], guild.id, timestamp=item.timestamp)
                        elif item.type == 'leave' and shift:
                            await bot.shift_management.end_shift(shift['_id'], guild.id, timestamp=item.timestamp)
            embed = discord.Embed(
                title=f"Player {'Join' if item.type == 'join' else 'Leave'} Log",
                description=f"[{item.username}](https://roblox.com/users/{item.user_id}/profile) {'joined the server' if item.type == 'join' else 'left the server'} • <t:{int(item.timestamp)}:T>",
                color=GREEN_COLOR if item.type == 'join' else RED_COLOR
            )
            await player_logs_channel.send(embed=embed)

async def get_staff_roles(guild, settings):
    staff_roles = []
    if settings["staff_management"].get("role"):
        if isinstance(settings["staff_management"]["role"], int):
            staff_roles.append(settings["staff_management"]["role"])
        elif isinstance(settings["staff_management"]["role"], list):
            staff_roles.extend(settings["staff_management"]["role"])

    if settings["staff_management"].get("management_role"):
        if isinstance(settings["staff_management"]["management_role"], int):
            staff_roles.append(settings["staff_management"]["management_role"])
        elif isinstance(settings["staff_management"]["management_role"], list):
            staff_roles.extend(settings["staff_management"]["management_role"])

    staff_roles = [guild.get_role(role) for role in staff_roles if guild.get_role(role)]
    return staff_roles

async def handle_guild_logs(item):
    guild = await get_guild(item['_id'])
    if not guild:
        return

    kill_logs_channel = await fetch_get_channel(guild, item['ERLC'].get('kill_logs'))
    player_logs_channel = await fetch_get_channel(guild, item['ERLC'].get('player_logs'))

    if not kill_logs_channel and not player_logs_channel:
        return

    kill_logs, player_logs = await fetch_logs(guild.id)
    if kill_logs is None or player_logs is None:
        return

    sorted_kill_logs = sorted(kill_logs, key=lambda x: x.timestamp)
    sorted_player_logs = sorted(player_logs, key=lambda x: x.timestamp)

    current_timestamp = int(datetime.datetime.now().timestamp())

    players = await process_kill_logs(guild, kill_logs_channel, sorted_kill_logs, current_timestamp)
    await notify_rdm(guild, players)
    await handle_shifts(guild, sorted_player_logs, current_timestamp, player_logs_channel)

@tasks.loop(seconds=75, reconnect=True)
async def iterate_prc_logs():
    # This will aim to constantly update the PRC Logs
    # and the relevant storage data.
    async for item in bot.settings.db.find({'ERLC': {'$exists': True}}):
        await handle_guild_logs(item)


@iterate_prc_logs.before_loop
async def anti_fetch_measure():
    # This CANNOT be called in the main loop
    # (as discord.py taught me) since it'll
    # deadlock the main setup_hook as this
    # loop is called on startup.
    await bot.wait_until_ready()

@tasks.loop(minutes=5, reconnect=True)
async def iterate_ics():
    # This will aim to constantly update the Integration Command Storage
    # and the relevant storage data.
    # print('ICS')
    async for item in bot.ics.db.find({}):
        try:
            guild = await bot.fetch_guild(item['guild'])
        except discord.HTTPException:
            continue

        selected = None
        custom_command_data = await bot.custom_commands.find_by_id(item['guild']) or {}
        for command in custom_command_data.get('commands', []):
            if command['id'] == item['_id']:
                selected = command

        if not selected:
            continue
            
        try:
            status: ServerStatus = await bot.prc_api.get_server_status(guild.id)
        except prc_api.ResponseFailure:
            status = None
        if not isinstance(status, ServerStatus):
            continue # Invalid key
        
        queue: int = await bot.prc_api.get_server_queue(guild.id, minimal=True)
        players: list[Player] = await bot.prc_api.get_server_players(guild.id)
        mods: int = len(list(filter(lambda x: x.permission == "Server Moderator", players)))
        admins: int = len(list(filter(lambda x: x.permission == "Server Administrator", players)))
        total_staff: int = len(list(filter(lambda x: x.permission != 'Normal', players)))
        onduty: int = len([i async for i in bot.shift_management.shifts.db.find({
            "Guild": guild.id, "EndEpoch": 0
        })])

        new_data = {
                'join_code': status.join_key,
                'players': status.current_players,
                'max_players': status.max_players,
                'queue': queue,
                'staff': total_staff,
                'admins': admins,
                'mods': mods,
                "onduty": onduty
            }
        # print(json.dumps(new_data, indent=4))
        
        if new_data != item['data']:
            # Updated data
            for arr in item['associated_messages']:
                channel, message_id = arr[0], arr[1]
                try:
                    channel = await guild.fetch_channel(channel)
                    message = await channel.fetch_message(message_id)
                except discord.HTTPException:
                    continue

                if not message or not channel:
                    continue

                await message.edit(content=await interpret_content(bot, await bot.get_context(message), channel, selected['message']['content'], item['_id']), embeds=[
                    (await interpret_embed(bot, await bot.get_context(message), channel, embed, item['_id'])) for embed in selected['message']['embeds']
                ] if selected['message']['embeds'] is not None else [])



@tasks.loop(minutes=1, reconnect=True)
async def check_loa():
    try:
        loas = bot.loas

        async for loaObject in bot.loas.db.find({}):
            if (
                datetime.datetime.now().timestamp() > loaObject["expiry"]
                and loaObject["expired"] == False
            ):
                if loaObject["accepted"] is True:
                    loaObject["expired"] = True
                    await bot.loas.update_by_id(loaObject)
                    guild = bot.get_guild(loaObject["guild_id"])
                    if guild:

                        member = guild.get_member(loaObject["user_id"])
                        settings = await bot.settings.find_by_id(guild.id)
                        roles = [None]
                        if settings is not None:
                            if "loa_role" in settings["staff_management"]:
                                try:
                                    if isinstance(
                                        settings["staff_management"]["loa_role"], int
                                    ):
                                        roles = [
                                            discord.utils.get(
                                                guild.roles,
                                                id=settings["staff_management"][
                                                    "loa_role"
                                                ],
                                            )
                                        ]
                                    elif isinstance(
                                        settings["staff_management"]["loa_role"], list
                                    ):
                                        roles = [
                                            discord.utils.get(guild.roles, id=role)
                                            for role in settings["staff_management"][
                                                "loa_role"
                                            ]
                                        ]
                                except KeyError:
                                    pass

                        docs = bot.loas.db.find(
                            {
                                "user_id": loaObject["user_id"],
                                "guild_id": loaObject["guild_id"],
                                "accepted": True,
                                "expired": False,
                                "denied": False,
                            }
                        )
                        should_remove_roles = True
                        expired_doc = None

                        async for doc in docs:
                            if doc["type"] == loaObject["type"]:
                                if not doc["expired"]:
                                    if not doc == loaObject:
                                        should_remove_roles = False
                                        break
                                expired_doc = doc

                        if should_remove_roles:
                            for role in roles:
                                if role is not None:
                                    if member:
                                        if role in member.roles:
                                            try:
                                                await member.remove_roles(
                                                    role,
                                                    reason="LOA Expired",
                                                    atomic=True,
                                                )
                                            except discord.HTTPException as e:
                                                logging.error(f"Failed to remove role {role.id} from {member.id} in {guild.id} due to {e}")
                                                pass
                        if member:
                            try:
                                await member.send(embed=discord.Embed(
                                    title=f"{expired_doc['type']} Expired",
                                    description=f"Your {expired_doc['type']} has expired in **{guild.name}**.",
                                    color=BLANK_COLOR
                                ))
                            except discord.Forbidden:
                                pass
    except ValueError:
        pass



intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

credentials_dict = {
    "type": config("TYPE", default=""),
    "project_id": config("PROJECT_ID", default=""),
    "private_key_id": config("PRIVATE_KEY_ID", default=""),
    "private_key": config("PRIVATE_KEY", default="").replace("\\n", "\n"),
    "client_email": config("CLIENT_EMAIL", default=""),
    "client_id": config("CLIENT_ID", default=""),
    "auth_uri": config("AUTH_URI", default=""),
    "token_uri": config("TOKEN_URI", default=""),
    "auth_provider_x509_cert_url": config("AUTH_PROVIDER_X509_CERT_URL", default=""),
    "client_x509_cert_url": config("CLIENT_X509_CERT_URL", default=""),
}

def run():
    sentry_sdk.init(
        dsn=sentry_url,
        traces_sample_rate=1.0,
        integrations=[PyMongoIntegration()],
        _experiments={
            "profiles_sample_rate": 1.0,
        },
    )

    try:
        bot.run(bot_token)
    except Exception as e:
        with push_scope() as scope:
            scope.level = "error"
            capture_exception(e)


if __name__ == "__main__":
    run()
