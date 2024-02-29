import datetime
import json
import logging
import time
from dataclasses import MISSING
from pkgutil import iter_modules

import aiohttp
import decouple
import discord.mentions
import dns.resolver
import motor.motor_asyncio
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
from datamodels.IntegrationCommandStorage import IntegrationCommandStorage
from menus import CompleteReminder, LOAMenu
from utils.bloxlink import Bloxlink
from utils.prc_api import PRCApiClient
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

discord.utils.setup_logging(level=logging.INFO)

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
        if user.id in [
            459374864067723275, # Noah
            877195103335231558, # Larry
            333991360199917568, # Doge
            315336291581558804, # ae453
        ]:  # Implement your own conditions here
            return True

        # Else fall back to the original
        return await super().is_owner(user)

    async def setup_hook(self) -> None:
        self.external_http_sessions: list[aiohttp.ClientSession] = []

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
            tempban_checks.start()
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

async def staff_predicate(ctx):
    if ctx.guild is None:
        return True
    else:
        return await staff_check(ctx.bot, ctx.guild, ctx.author)


def is_staff():
    return commands.check(staff_predicate)


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
    status = f"/help | ermbot.xyz"
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=status)
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
                                resp = await bot.prc_api.run_command(channel.guild.id, total)
                                if resp[0] != 200:
                                    print('Failed reaching PRC due to {} status code'.format(resp))
                                else:
                                    print('Integration success with 200 status code')


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
                    print(e)
    except Exception as e:
        print(e)

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
            cached_servers[punishment_item['Guild']] = await bot.prc_api.fetch_bans(punishment_item['Guild'])

        punishment_item['CheckExecuted'] = True
        await bot.punishments.update_by_id(punishment_item)

        if punishment_item['UserID'] not in [i.user_id for i in cached_servers[punishment_item['Guild']]]:
            continue

        sorted_punishments = sorted([i async for i in await bot.punishments.db.find({"UserID": punishment_item['UserID'], "Guild": punishment_item['Guild']})], key=lambda x: x['Epoch'], reverse=True)
        new_sorted_punishments = []
        for item in sorted_punishments:
            if item == punishment_item:
                break
            new_sorted_punishments.append(item)
        
        if any([i['Type'] in ["Ban", "Temporary Ban"] for i in new_sorted_punishments]):
            continue
            
        await bot.prc_api.unban_user(punishment_item['Guild'], punishment_item['user_id'])
    
    end_time = time.time()
    logging.warning('Event tempban_checks took {} seconds'.format(str(end_time - initial_time)))
        




@tasks.loop(seconds=45, reconnect=True)
async def iterate_prc_logs():
    # This will check every 60 seconds for kill logs and player logs
    # enabled, as well as send all players joined during that time period.
    async for item in bot.settings.db.find({'ERLC': {'$exists': True}}):
        try:
            guild = await bot.fetch_guild(item['_id'])
        except discord.HTTPException:
            continue
        
        try:
            kill_logs_channel = await guild.fetch_channel(item['ERLC'].get('kill_logs'))
        except discord.HTTPException:
            kill_logs_channel = None

        try:
            player_logs_channel = await guild.fetch_channel(item['ERLC'].get('player_logs'))
        except discord.HTTPException:
            player_logs_channel = None


        # if not kill_logs_channel and not player_logs_channel:
        #     continue
            
        try:
            kill_logs: list[prc_api.KillLog] = await bot.prc_api.fetch_kill_logs(guild.id)
            player_logs: list[prc_api.JoinLeaveLog] = await bot.prc_api.fetch_player_logs(guild.id)
        except prc_api.ResponseFailure:
            continue


        sorted_kill_logs = sorted(kill_logs, key=lambda x: x.timestamp, reverse=False)
        sorted_player_logs = sorted(player_logs, key=lambda x: x.timestamp, reverse=False)

        current_timestamp = int(datetime.datetime.now(tz=pytz.UTC).timestamp())

        players = {}


        for item in sorted_kill_logs:
            if (current_timestamp - item.timestamp) > 45:
                continue

            if not players.get(item.killer_username):
                players[item.killer_username] = [1, [item]]
            else:
                players[item.killer_username] = [players[item.killer_username][0]+1, players[item.killer_username][1] + [item]]

            if kill_logs_channel is not None:    
                await kill_logs_channel.send(
                    embed=discord.Embed(
                        title="Kill Log",
                        description=f"[{item.killer_username}](https://roblox.com/users/{item.killer_user_id}/profile) killed [{item.killed_username}](https://roblox.com/users/{item.killed_user_id}/profile) • <t:{int(item.timestamp)}:T>",
                        color=BLANK_COLOR
                    )
                )

        # Check for kill logs amount
        for username, value in players.items():
            count = value[0]
            items = value[1]
            if count > 3:
                settings = await bot.settings.find_by_id(guild.id)
                channel = ((settings or {}).get('ERLC', {}) or {}).get('rdm_channel', 0)
                try:
                    channel = await (await bot.fetch_guild(guild.id)).fetch_channel(channel)
                except discord.HTTPException:
                    channel = None
                    
                if channel:
                    roblox_player = await bot.roblox.get_user_by_username(username)
                    thumbnails = await bot.roblox.thumbnails.get_user_avatar_thumbnails([roblox_player], size=(420, 420))
                    thumbnail = thumbnails[0].image_url
                    pings = []
                    pings = [((guild.get_role(role_id)).mention) if guild.get_role(role_id) else None for role_id in (settings or {}).get('ERLC', {}).get('rdm_mentionables', [])]
                    pings = list(filter(lambda x: x is not None, pings))
                    
                    await channel.send(
                        ', '.join(pings) if pings not in [[], None] else '',
                        embed=discord.Embed(
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
                        ),
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True,
                            users=True,
                            roles=True,
                            replied_user=True,
                        ),
                    )

        for item in sorted_player_logs:
            if (current_timestamp - item.timestamp) > 45:
                continue
                
            if not player_logs_channel:
                break

            await player_logs_channel.send(
                embed=discord.Embed(
                    title="Player Join/Leave Log",
                    description=f"[{item.username}](https://roblox.com/users/{item.user_id}/profile) {'joined the server' if item.type == 'join' else 'left the server'} • <t:{int(item.timestamp)}:T>",
                    color=GREEN_COLOR if item.type == 'join' else RED_COLOR
                )
            )
                




@tasks.loop(minutes=5, reconnect=True)
async def iterate_ics():
    # This will aim to constantly update the Integration Command Storage
    # and the relevant storage data.
    print('ICS')
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
        print(json.dumps(new_data, indent=4))
        
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
                        async for doc in docs:
                            if doc["type"] == loaObject["type"]:
                                if not doc["expired"]:
                                    if not doc == loaObject:
                                        should_remove_roles = False
                                        break

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
                                            except discord.HTTPException:
                                                pass
                        if member:
                            try:
                                await member.send(embed=discord.Embed(
                                    title="LOA Expired",
                                    description=f"Your LOA has expired in **{guild.name}**.",
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
