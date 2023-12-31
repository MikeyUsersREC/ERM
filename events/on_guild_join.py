import logging

import discord
from discord.ext import commands


class OnGuildJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        bot = self.bot
        embed = discord.Embed(
            color=0xED4348,
            title="<:ERMWhite:1044004989997166682> Emergency Response Management",
        )
        embed.description = f"Thanks for adding ERM to **{guild.name}**"
        embed.add_field(
            name="<:Setup:1035006520817090640> Getting Started",
            value=f"<:ArrowRight:1035003246445596774> Run `/setup` to go through the setup. \n<:ArrowRight:1035003246445596774> Run `/config change` to change any configuration.",
            inline=False,
        )

        embed.add_field(
            name="<:MessageIcon:1035321236793860116> Simple Commands",
            value=f"<:ArrowRight:1035003246445596774> Run `/duty manage` to manage your shift. \n<:ArrowRight:1035003246445596774> Run `/punish` to punish a roblox user.",
            inline=False,
        )

        embed.add_field(
            name="<:LinkIcon:1044004006109904966> Important Links",
            value=f"<:ArrowRight:1035003246445596774> [Our Website](https://ermbot.xyz)\n<:ArrowRight:1035003246445596774> [Support Server](https://discord.gg/FAC629TzBy)\n<:ArrowRight:1035003246445596774> [Status Page](https://status.ermbot.xyz)",
            inline=False,
        )


        channel = bot.get_channel(1033021466381398086)
        embed = discord.Embed(color=0xED4348)
        embed.description = f"""
        <:ArrowRightW:1035023450592514048> **Server Name:** {guild.name}
        <:ArrowRightW:1035023450592514048> **Guild ID:** {guild.id}
        <:ArrowRightW:1035023450592514048> **Bots:** {len([member for member in guild.members if member.bot == True])}
        <:ArrowRightW:1035023450592514048> **Member Count:** {guild.member_count}
        <:ArrowRightW:1035023450592514048> **Guild Count:** {len(bot.guilds)}        
        """
        try:
            embed.set_footer(icon_url=guild.icon.url, text=guild.name)
        except AttributeError:
            pass
        await channel.send(embed=embed)
        logging.info("Server has been sent welcome sequence.")


async def setup(bot):
    await bot.add_cog(OnGuildJoin(bot))
