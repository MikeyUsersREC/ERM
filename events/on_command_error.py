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

from utils.constants import BLANK_COLOR, RED_COLOR
from utils.utils import error_gen, GuildCheckFailure
from utils.prc_api import ServerLinkNotFound, ResponseFailure


class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx, error):
        error_id = error_gen()

        if await self.handle_known_errors(ctx, error):
            return

        if await self.handle_custom_errors(ctx, error, error_id):
            return

        await self.handle_general_error(ctx, error, error_id)

    async def handle_known_errors(self, ctx, error):
        if (
            'Invalid Webhook Token' in str(error)
            or 'Unknown Message' in str(error)
            or 'Unknown message' in str(error)
            or isinstance(error, asyncio.TimeoutError)
        ):
            return True
        if isinstance(error, HybridCommandError) and (
            'RemoteProtocolError: Server disconnected without sending a response.'
            in str(error)
        ):
            await self.send_error_message(
                ctx,
                "Connection Error",
                "The server disconnected without sending a response. Your issue will be fixed if you try again."
            )
            return True
        if isinstance(error, httpcore.ConnectTimeout):
            await self.send_error_message(
                ctx,
                "HTTP Error",
                "I could not connect to the ROBLOX API. Please try again later."
            )
            return True
        if isinstance(error, commands.CommandNotFound):
            return True
        return False

    async def handle_custom_errors(self, ctx, error, error_id):
        if isinstance(error, ResponseFailure):
            await self.handle_response_failure(ctx, error, error_id)
            return True
        if isinstance(error, commands.BadArgument):
            await self.send_error_message(
                ctx,
                "Invalid Argument",
                "You provided an invalid argument to this command."
            )
            return True
        if 'Invalid username' in str(error) or isinstance(error, roblox.UserNotFound):
            await self.send_error_message(
                ctx,
                "Player not found",
                "I could not find a ROBLOX player with that corresponding username."
            )
            return True
        if isinstance(error, discord.Forbidden) and (
            "Cannot send messages to this user" in str(error)
        ):
            return True
        if isinstance(error, commands.NoPrivateMessage):
            await self.send_error_message(
                ctx,
                "Direct Messages",
                "I would love to talk to you more personally, "
                "but I can't do that in DMs. Please use me in a server."
            )
            return True
        if isinstance(error, GuildCheckFailure):
            await self.send_error_message(
                ctx,
                "Not Setup",
                "This command requires for the bot to be configured before this command is ran. Please use `/setup` first."
            )
            return True
        if isinstance(error, ServerLinkNotFound):
            await self.send_error_message(
                ctx,
                "Not Linked",
                "This server does not have an ER:LC server connected. \n"
                "To link your ER:LC server, run **/erlc link**."
            )
            return True
        if isinstance(error, commands.CheckFailure):
            await self.send_error_message(
                ctx,
                "Not Permitted",
                "You are not permitted to run this command."
            )
            return True
        if isinstance(error, OverflowError):
            await self.send_error_message(
                ctx,
                "Overflow Error",
                "A user has inputted an arbitrary amount of time into ERM and we were "
                "unable to display the requested data because of this. Please find the "
                "source of this, and remove the excess amount of time."
            )
            return True
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_error_message(
                ctx,
                "Missing Argument",
                "You are missing a required argument to run this command."
            )
            return True
        return False

    async def handle_response_failure(self, ctx, error, error_id):
        await ctx.reply(embed=discord.Embed(
            title=f"PRC Response Failure ({error.status_code})",
            description=(
                "Your server seems to be offline. If this is incorrect, PRC's API may be down."
                if error.status_code == 422
                else "There seems to be issues with the PRC API. Stand by and wait a few minutes before trying again."
            ),
            color=BLANK_COLOR
        ))
        await self.log_error(ctx, error, error_id)
        await self.notify_error_channel(ctx, error, error_id)

    async def handle_general_error(self, ctx, error, error_id):
        embed = discord.Embed(color=RED_COLOR)
        embed.add_field(name="Support Server", value="[Click here](https://discord.gg/FAC629TzBy)", inline=False)
        embed.add_field(name="Error ID", value=f"`{error_id}`", inline=False)
        await ctx.send(embed=discord.Embed(
            title="<:error:1164666124496019637> Command Failure",
            description="The command you were attempting to run failed.\n"
                        "Please go to [ERM Support](https://discord.gg/FAC629TzBy) for details.",
            color=RED_COLOR
        ).add_field(name="Error ID", value=f"`{error_id}`", inline=False))
        await self.log_error(ctx, error, error_id)
        capture_exception(error)

    async def send_error_message(self, ctx, title, description):
        await ctx.reply(embed=discord.Embed(title=title, description=description, color=BLANK_COLOR))

    async def log_error(self, ctx, error, error_id):
        await self.bot.errors.insert({
            "_id": error_id,
            "error": str(error),
            "time": datetime.datetime.now(tz=pytz.UTC).strftime("%m/%d/%Y, %H:%M:%S"),
            "channel": ctx.channel.id,
            "guild": ctx.guild.id,
        })

    async def notify_error_channel(self, ctx, error, error_id):
        channel = await self.bot.fetch_channel(1213731821330894938)
        await channel.send(f'`{error_id}` {str(error)}')


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
