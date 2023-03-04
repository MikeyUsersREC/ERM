import datetime
import logging

import discord
from discord.ext import commands
from sentry_sdk import capture_exception, push_scope

from erm import error_gen


class OnCommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener('on_command_error')
    async def on_command_error(self, ctx, error):
        bot = self.bot
        error_id = error_gen()

        if isinstance(error, discord.Forbidden):
            if 'Cannot send messages to this user' in str(error):
                return

        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            embed = discord.Embed(title="<:ErrorIcon:1035000018165321808> Permissions Error", color=0xff3c3c,
                                  description="You do not have permission to use this command.")
            try:
                return await ctx.send(embed=embed)
            except:
                pass
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(title="<:ErrorIcon:1035000018165321808> Error", color=0xff3c3c,
                                  description="You are missing a required argument to run this command.")
            try:
                return await ctx.send(embed=embed)
            except:
                pass
        try:
            embed = discord.Embed(
                title='<:ErrorIcon:1035000018165321808> Bot Error',
                color=discord.Color.red()
            )

            try:
                error_bef = str(error).split(':')[0]
                error_beftwo = str(error).split(':')[1:]
                error_after = error_bef + ":\n" + ':'.join(error_beftwo)
            except:
                error_after = str(error)

            embed.add_field(name="Error Details", value=error_after, inline=False)
            embed.add_field(name="Support Server", value="[Click here](https://discord.gg/5pMmJEYazQ)", inline=False)
            embed.add_field(name='Error ID', value=f"`{error_id}`", inline=False)

            if not isinstance(error, (
                    commands.CommandNotFound, commands.CheckFailure, commands.MissingRequiredArgument,
                    discord.Forbidden)):
                await ctx.send(embed=embed)
        except Exception as e:
            logging.info(e)
        finally:
            with push_scope() as scope:
                scope.set_tag('error_id', error_id)
                scope.level = 'error'
                await bot.errors.insert({
                    "_id": error_id,
                    "error": str(error),
                    "time": datetime.datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S"),
                    "channel": ctx.channel.id,
                    "guild": ctx.guild.id
                })
                capture_exception(error)


async def setup(bot):
    await bot.add_cog(OnCommandError(bot))
