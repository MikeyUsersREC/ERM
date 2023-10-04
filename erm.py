import datetime
import json
import logging
import time
from dataclasses import MISSING
from pkgutil import iter_modules

import aiohttp
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

from datamodels.ShiftManagement import ShiftManagement
from datamodels.APITokens import APITokens
from datamodels.ActivityNotices import ActivityNotices
from datamodels.Analytics import Analytics
from datamodels.Consent import Consent
from datamodels.CustomCommands import CustomCommands
from datamodels.Errors import Errors
from datamodels.FiveMLinks import FiveMLinks
from datamodels.Flags import Flags
from datamodels.LinkStrings import LinkStrings
from datamodels.Privacy import Privacy
from datamodels.PunishmentTypes import PunishmentTypes
from datamodels.Reminders import Reminders
from datamodels.Settings import Settings
from datamodels.OldShiftManagement import OldShiftManagement
from datamodels.SyncedUsers import SyncedUsers
from datamodels.Verification import Verification
from datamodels.Views import Views
from datamodels.Warnings import Warnings
from datamodels.StaffConductConfig import StaffConductConfig
from menus import CompleteReminder, LOAMenu
from utils.mongo import Document
from utils.utils import *

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8"]
setup = False

try:
    sentry_url = config("SENTRY_URL")
    bloxlink_api_key = config("BLOXLINK_API_KEY")
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
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


class Bot(commands.AutoShardedBot):
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
        global setup
        if not setup:
            bot = self
            # await bot.load_extension('utils.routes')
            logging.info(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{} is online!".format(
                    bot.user.name
                )
            )
            global startTime
            startTime = time.time()
            bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(mongo_url))
            if environment == "DEVELOPMENT":
                bot.db = bot.mongo["beta"]
            elif environment == "PRODUCTION":
                bot.db = bot.mongo["erm"]
            else:
                raise Exception("Invalid environment")

            bot.start_time = time.time()
            # bot.warnings = Warnings(bot.db, "warnings")
            bot.old_shift_management = OldShiftManagement(bot.db, "shifts", "shift_storage")
            bot.shift_management = ShiftManagement(bot.db, "shift_management")
            bot.errors = Errors(bot.db, "errors")
            bot.loas = ActivityNotices(bot.db, "leave_of_absences")
            bot.reminders = Reminders(bot.db, "reminders")
            bot.custom_commands = CustomCommands(bot.db, "custom_commands")
            bot.staff_conduct = StaffConductConfig(bot.db, "staff_conduct")
            bot.analytics = Analytics(bot.db, "analytics")
            bot.punishment_types = PunishmentTypes(bot.db, "punishment_types")
            bot.privacy = Privacy(bot.db, "privacy")
            bot.verification = Verification(bot.db, "verification")
            bot.flags = Flags(bot.db, "flags")
            bot.views = Views(bot.db, "views")
            bot.synced_users = SyncedUsers(bot.db, "synced_users")
            bot.api_tokens = APITokens(bot.db, "api_tokens")
            bot.link_strings = LinkStrings(bot.db, "link_strings")
            bot.fivem_links = FiveMLinks(bot.db, "fivem_links")
            bot.consent = Consent(bot.db, "consent")
            bot.punishments = Warnings(bot)
            bot.settings = Settings(bot.db, "settings")

            Extensions = [m.name for m in iter_modules(["cogs"], prefix="cogs.")]
            Events = [m.name for m in iter_modules(["events"], prefix="events.")]
            BETA_EXT = ["cogs.StaffConduct"]


            for extension in Extensions:
                try:
                    if extension not in BETA_EXT:
                        await bot.load_extension(extension)
                        logging.info(f"Loaded {extension}")
                except Exception as e:
                    logging.error(f"Failed to load extension {extension}.", exc_info=e)

            for extension in Events:
                try:
                    await bot.load_extension(extension)
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
                await bot.tree.sync()
                # guild specific: leave blank if global (global registration can take 1-24 hours)
            bot.is_synced = True
            check_reminders.start()
            check_loa.start()
            # GDPR.start()
            change_status.start()
            logging.info("Setup_hook complete! All tasks are now running!")

            async for document in self.views.db.find({}):
                if document["view_type"] == "LOAMenu":
                    for index, item in enumerate(document["args"]):
                        if item == "SELF":
                            document["args"][index] = self
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
    return await staff_check(ctx.bot, ctx.guild, ctx.author)


def is_staff():
    return commands.check(staff_predicate)


async def management_predicate(ctx):
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


async def crp_data_to_mongo(jsonData, guildId: int):
    separation = []
    # Separate the User IDs into bundles of 120
    for value in jsonData["moderations"]:
        if len(separation) == 0:
            separation.append([value["userId"]])
        else:
            if len(separation[-1]) == 110:
                separation.append([value["userId"]])
            else:
                separation[-1].append(value["userId"])

    for sep in separation:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://users.roblox.com/v1/users",
                json={"userIds": sep, "excludeBannedUsers": True},
            ) as r:
                try:
                    requestJSON = await r.json()
                except Exception as e:
                    pass

       # # print(f"Request JSON: {requestJSON}")
        for user in requestJSON["data"]:
            name = user["name"]
            userItem = None
            user = discord.utils.get(bot.users, id=int(value["staffId"]))
            if user is not None:
                userItem = [user.name, user.id]
            else:
                userItem = ["-", int(value["staffId"])]

            timeObject = datetime.datetime.fromtimestamp(int(value["time"]) / 1000)
            types = {
                "other": "Warning",
                "warn": "Warning",
                "kick": "Kick",
                "ban": "Ban",
            }

            default_warning_item = {
                "id": next(generator),
                "Type": types[value["type"]],
                "Reason": value["reason"],
                "Moderator": userItem,
                "Time": timeObject.strftime("%m/%d/%Y, %H:%M:%S"),
                "Guild": guildId,
            }

            parent_structure = {"_id": name, "warnings": []}

            if await bot.warnings.find_by_id(name):
                data = await bot.warnings.find_by_id(name)
                data["warnings"].append(default_warning_item)
                await bot.warnings.update_by_id(data)
            else:
                data = parent_structure
                data["warnings"].append(default_warning_item)
                await bot.warnings.insert(data)


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
    except:
        bot_token = ""
    logging.info("Using development token...")
else:
    raise Exception("Invalid environment")
try:
    mongo_url = config("MONGO_URL", default=None)
except:
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
                    full = None
                    num = None

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
                        except:
                            roles = [""]

                        if (
                            item.get("completion_ability")
                            and item.get("completion_ability") is True
                        ):
                            view = CompleteReminder()
                        else:
                            view = None
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Notification",
                            description=f"{item['message']}",
                            color=0xED4348,
                        )
                        lastTriggered = tD.timestamp()
                        item["lastTriggered"] = lastTriggered
                        await bot.reminders.update_by_id(new_go)

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
                                except:
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
                                            except:
                                                pass
                        if member:
                            try:
                                await member.send(f"<:ERMAlert:1113237478892130324> **{member.name}**, your {loaObject['type']} has expired in **{guild.name}**.")
                            except discord.Forbidden:
                                pass
    except:
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
