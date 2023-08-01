import datetime
import logging

import discord
import pytz
from discord.ext import commands
from sentry_sdk import capture_exception, push_scope

from utils.utils import error_gen


class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx, error):
        bot = self.bot
        error_id = error_gen()

        if isinstance(error, discord.Forbidden):
            if "Cannot send messages to this user" in str(error):
                return

        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            try:
                return await ctx.send(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you don't have permission to run that command."
                )
            except:
                pass
        if isinstance(error, commands.MissingRequiredArgument):
            try:
                return await ctx.send(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you're missing a required argument to run this command!"
                )
            except:
                pass
        try:
            embed = discord.Embed(
                color=0xED4348,
            )

            embed.add_field(
                name="Support Server",
                value="[Click here](https://discord.gg/5pMmJEYazQ)",
                inline=False,
            )
            embed.add_field(name="Error ID", value=f"`{error_id}`", inline=False)
            if not isinstance(
                error,
                (
                    commands.CommandNotFound,
                    commands.CheckFailure,
                    commands.MissingRequiredArgument,
                    discord.Forbidden,
                ),
            ):
                await ctx.send(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, an error has occurred! Rest assured, it can probably be solved by going to our support server. **{error_id}**.",
                    embed=embed,
                )
        except Exception as e:
            logging.info(e)
        finally:
            with push_scope() as scope:
                scope.set_tag("error_id", error_id)
                scope.level = "error"
                try:
                    await bot.errors.insert(
                        {
                            "_id": error_id,
                            "error": str(error),
                            "time": datetime.datetime.now(tz=pytz.UTC).strftime(
                                "%m/%d/%Y, %H:%M:%S"
                            ),
                            "channel": ctx.channel.id,
                            "guild": ctx.guild.id,
                        }
                    )
                except:
                    pass

                capture_exception(error)


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
