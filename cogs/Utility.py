import datetime
import logging

import discord
from discord import app_commands
from discord.app_commands import AppCommandGroup
from discord.ext import commands

from menus import LinkView, CustomSelectMenu, MultiPaginatorMenu
from utils.constants import BLANK_COLOR
from utils.timestamp import td_format
from utils.utils import invis_embed, failure_embed


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="staff_sync",
        description="Internal Use Command, used for connection staff privileged individuals to their Roblox counterparts.",
        extras={"category": "Utility"},
        hidden=True,
        with_app_command=False
    )
    async def staff_sync(self, ctx: commands.Context, discord_id: int, roblox_id: int):
        from bson import ObjectId
        from datamodels.StaffConnections import StaffConnection

        await self.bot.staff_connections.insert_connection(
            StaffConnection(
                roblox_id=roblox_id,
                discord_id=discord_id,
                document_id=ObjectId()
            )
        )
        roblox_user = await self.bot.roblox.get_user(roblox_id)
        await ctx.send(
            embed=discord.Embed(
                title="Staff Sync",
                description=f"Successfully synced <@{discord_id}> to {roblox_user.name}",
                color=BLANK_COLOR
            )
        )

    @commands.hybrid_command(
        name="ping",
        description="Shows information of the bot, such as uptime and latency",
        extras={"category": "Utility"},
    )
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="<:search:1164662425820348536> Bot Status",
            color=BLANK_COLOR,
        )

        if ctx.guild is not None:
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url if ctx.guild.icon else '',
            )
        else:
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )

        data = await self.bot.db.command("ping")

        status: str | None = None

        if list(data.keys())[0] == "ok":
            status = "Connected"
        else:
            status = "Not Connected"

        embed.add_field(
            name="Information",
            value=(
                f"<:replytop:1138257149705863209> **Latency:** `{latency}ms`\n"
                f"<:replymiddle:1138257195121791046> **Uptime:** <t:{int(self.bot.start_time)}:R>\n"
                f"<:replymiddle:1138257195121791046> **Database Connection:** {status}\n"
                f"<:replybottom:1138257250448855090> **Shards:** `{self.bot.shard_count-1}`\n"
            ),
            inline=False,
        )

        embed.set_footer(
            text= f"Shard {ctx.guild.shard_id if ctx.guild else 0}/{self.bot.shard_count-1}"
        )
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else '')
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="support",
        aliases=["support-server"],
        description="Information about the ERM Support Server",
        extras={"category": "Utility"},
    )
    async def support_server(self, ctx):
        # using an embed
        # [**Support Server**](https://discord.gg/5pMmJEYazQ)

        await ctx.reply(
            embed=discord.Embed(
                title="ERM Support",
                description="You can join the ERM Systems Discord server using the button below.",
                color=BLANK_COLOR
            ),
            view=LinkView(label="Support Server", url="https://discord.gg/FAC629TzBy"),
        )

    @commands.hybrid_command(
        name="about",
        aliases=["info"],
        description="Information about ERM",
        extras={"category": "Utility"},
    )
    async def about(self, ctx):
        # using an embed
        # [**Support Server**](https://discord.gg/5pMmJEYazQ)
        embed = discord.Embed(
            title="<:ERMWhite:1044004989997166682> About ERM",
            color=BLANK_COLOR,
            description="ERM is the all-in-one approach to game moderation logging, shift logging and more."
        )

        embed.add_field(
            name=f"Bot Information",
            value=(
                "<:replytop:1138257149705863209> **Website:** [View Website](https://ermbot.xyz)\n"
                "<:replymiddle:1138257195121791046> **Support:** [Join Server](https://discord.gg/FAC629TzBy)\n"
                f"<:replymiddle:1138257195121791046> **Invite:** [Invite Bot](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands)\n"
                "<:replybottom:1138257250448855090> **Documentation:** [View Documentation](https://docs.ermbot.xyz)"
            ),
            inline=False,
        )
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.display_avatar.url,
        )
        await ctx.reply(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Utility(bot))
