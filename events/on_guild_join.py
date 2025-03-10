import logging

import discord
from discord.ext import commands


class OnGuildJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        bot = self.bot
        if self.bot.environment != "CUSTOM":
            channel = bot.get_channel(1033021466381398086)
            embed = discord.Embed(title=guild.name, color=0xED4348)
            embed.description = f"""
            > **Server Membercount:** {guild.member_count}
            > **Bots:** {len([member for member in guild.members if member.bot == True])}
            > **Guild Count:** {len(bot.guilds)}
            > **Guild Owner:** <@{guild.owner.id}> `({guild.owner.id})`    
            """
            try:
                embed.set_footer(icon_url=guild.icon, text=f"Guild ID: {guild.id}")
                embed.set_thumbnail(url=guild.icon)
            except AttributeError:
                pass
            await channel.send(embed=embed)
            logging.info("Server has been sent welcome sequence.")


async def setup(bot):
    await bot.add_cog(OnGuildJoin(bot))
