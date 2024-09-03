import datetime
import logging

import asyncio
import discord
import httpcore
import pytz
import roblox
from discord.ext import commands
from discord.ext.commands import HybridCommandError
from sentry_sdk import capture_exception, push_scope
from aiohttp import ClientConnectorSSLError

from utils.constants import BLANK_COLOR, RED_COLOR
from utils.utils import error_gen, GuildCheckFailure
from utils.prc_api import ServerLinkNotFound, ResponseFailure

class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx, error):
        bot = self.bot
        error_id = error_gen()

        if isinstance(error, commands.CommandInvokeError):
            error = error.original
            return await self.on_command_error(ctx, error)
            
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.reply(embed=discord.Embed(
                title="Cooldown",
                description=f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.",
                color=BLANK_COLOR
            ))
        
        if 'Invalid Webhook Token' in str(error) or 'Unknown Message' in str(error) or 'Unknown message' in str(error) or isinstance(error, asyncio.TimeoutError):
            return
        
        if isinstance(error, HybridCommandError) and 'RemoteProtocolError: Server disconnected without sending a response.' in str(error):
            return await ctx.reply(embed=discord.Embed(
                title="Connection Error",
                description="The server disconnected without sending a response. Your issue will be fixed if you try again.",
                color=BLANK_COLOR
            ))

        if isinstance(error, httpcore.ConnectTimeout):
            return await ctx.reply(embed=discord.Embed(
                title="HTTP Error",
                description="I could not connect to the ROBLOX API. Please try again later.",
                color=BLANK_COLOR
            ))

        if isinstance(error, ResponseFailure):
            await ctx.reply(
                embed=discord.Embed(
                    title=f"PRC Response Failure ({error.status_code})",
                    description="Your server seems to be offline. If this is incorrect, PRC's API may be down." if error.status_code == 422 else "There seems to be issues with the PRC API. Stand by and wait a few minutes before trying again.",
                    color=BLANK_COLOR
                )
            )
            channel = await self.bot.fetch_channel(1213731821330894938)
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
            await channel.send(f'`{error_id}` {str(error)}')
            return

        if isinstance(error, commands.BadArgument):
            return await ctx.reply(
                embed=discord.Embed(
                    title="Invalid Argument",
                    description="You provided an invalid argument to this command.",
                    color=BLANK_COLOR
                )
            )

        if 'Invalid username' in str(error):
            return await ctx.reply(embed=discord.Embed(
                title="Player not found",
                description="I could not find a ROBLOX player with that corresponding username.",
                color=BLANK_COLOR
            ))

        if isinstance(error, roblox.UserNotFound):
            return await ctx.reply(embed=discord.Embed(
                title="Player not found",
                description="I could not find a ROBLOX player with that corresponding username.",
                color=BLANK_COLOR
            ))

        if isinstance(error, discord.Forbidden):
            if "Cannot send messages to this user" in str(error):
                return

        if isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(
                title="Direct Messages",
                description=f"I would love to talk to you more personally, "
                            f"but I can't do that in DMs. Please use me in a server.",
                color=BLANK_COLOR
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, GuildCheckFailure):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Setup",
                    description="This command requires for the bot to be configured before this command is ran. Please use `/setup` first.",
                    color=BLANK_COLOR
                )
            )

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, ServerLinkNotFound):
            await ctx.send(
                embed=discord.Embed(
                    title="Not Linked",
                    description="This server does not have an ER:LC server connected. \nTo link your ER:LC server, run **/erlc link**.",
                    color=BLANK_COLOR
                ).set_footer(text=error_id)
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
            return

        if isinstance(error, commands.CheckFailure):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Permitted",
                    description="You are not permitted to run this command.",
                    color=BLANK_COLOR
                )
            )
        if isinstance(error, OverflowError):
            return await ctx.reply(embed=discord.Embed(
                title="Overflow Error",
                description="A user has inputted an arbitrary time amount of time into ERM and we were unable to display the requested data because of this. Please find the source of this, and remove the excess amount of time.",
                color=BLANK_COLOR
            ))
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(embed=discord.Embed(
                title="Missing Argument",
                description="You are missing a required argument to run this command.",
                color=BLANK_COLOR
            ))
        embed = discord.Embed(
            color=0xED4348,
        )

        embed.add_field(
            name="Support Server",
            value="[Click here](https://discord.gg/FAC629TzBy)",
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
