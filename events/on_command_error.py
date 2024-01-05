import datetime
import logging

import discord
import httpcore
import pytz
import roblox
from discord.ext import commands
from sentry_sdk import capture_exception, push_scope

from utils.constants import BLANK_COLOR, RED_COLOR
from utils.utils import error_gen, GuildCheckFailure

class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx, error):
        bot = self.bot
        error_id = error_gen()

        if 'Invalid Webhook Token' in str(error) or 'Unknown Message' in str(error):
            return

        if isinstance(error, httpcore.ConnectTimeout):
            await ctx.reply(embed=discord.Embed(
                title="HTTP Error",
                description="Could not connect to the ROBLOX API. Please try again later.",
                color=BLANK_COLOR
            ))

        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=discord.Embed(
                title="Invalid Argument",
                description="You provided an invalid argument to this command.",
                color=BLANK_COLOR
            ))

        if 'Invalid username' in str(error) or isinstance(error, roblox.UserNotFound):
            await ctx.reply(embed=discord.Embed(
                title="Player not found",
                description="Could not find a ROBLOX player with that username.",
                color=BLANK_COLOR
            ))

        if isinstance(error, discord.Forbidden) and "Cannot send messages to this user" in str(error):
            return

        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=discord.Embed(
                title="Direct Messages",
                description="I can't talk to you in DMs. Please use me in a server.",
                color=BLANK_COLOR
            ))

        if isinstance(error, GuildCheckFailure):
            await ctx.send(embed=discord.Embed(
                title="Not Setup",
                description="This command requires the bot to be configured. Please use `/setup` first.",
                color=BLANK_COLOR
            ))

        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(
                title="Missing Argument",
                description="You are missing a required argument to run this command.",
                color=BLANK_COLOR
            ))

        embed = discord.Embed(
            title="Support Server",
            value="[Click here](https://discord.gg/FAC629TzBy)",
            inline=False,
            color=0xED4348,
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
                embed=discord.Embed(
                    title="<:error:1164666124496019637> Command Failure",
                    description="The command you were attempting to run failed.\nPlease go to [ERM Support](https://discord.gg/FAC629TzBy) for details.",
                    color=RED_COLOR
                ).add_field(
                    name="Error ID",
                    value=f"`{error_id}`",
                    inline=False
                )
            )

            with push_scope() as scope:
                scope.set_tag("error_id", error_id)
                scope.set_tag("guild_id", ctx.guild.id)
                scope.set_tag('user_id', ctx.author.id)
                scope.set_tag('shard_id', ctx.guild.shard_id)
                scope.set_level('error')
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

                capture_exception(error)


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
