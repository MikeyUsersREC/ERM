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
from menus import CompleteReminder, LOAMenu
from utils.mongo import Document
from utils.utils import *
from erm import run

run()