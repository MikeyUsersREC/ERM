import discord
from discord.ext import commands


class DutyManageOptions(commands.FlagConverter, delimiter="=", prefix="/"):
    onduty: bool = False
    togglebreak: bool = False
    offduty: bool = False
    without_command_execution: bool = False


class PunishOptions(commands.FlagConverter, delimiter="=", prefix="/"):
    without_command_execution: bool = False
    ephemeral: bool = False
    noconfirm: bool = False


class SearchOptions(commands.FlagConverter, delimiter="=", prefix="/"):
    without_command_execution: bool = False
    ephemeral: bool = False
