import datetime
import logging

import discord
import pytz
from discord.ext import commands
from sentry_sdk import capture_exception, push_scope

from utils.utils import error_gen


class OnError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_error")
    async def on_error(self, error):
        bot = self.bot
        error_id = error_gen()

        if isinstance(error, discord.Forbidden):
            if "Cannot send messages to this user" in str(error):
                return

        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            return
        # # print(error)
        # # print(str(error))
        with push_scope() as scope:
            scope.set_tag("error_id", error_id)
            scope.level = "error"
            await bot.errors.insert(
                {
                    "_id": error_id,
                    "error": str(error),
                    "time": datetime.datetime.now(tz=pytz.UTC).strftime(
                        "%m/%d/%Y, %H:%M:%S"
                    ),
                }
            )

            capture_exception(error)


async def setup(bot):
    await bot.add_cog(OnError(bot))
