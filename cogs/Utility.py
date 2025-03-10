import datetime
import logging
import aiohttp
import os
from decouple import config

import discord
from discord import app_commands
from discord.app_commands import AppCommandGroup
from discord.ext import commands

from menus import LinkView, CustomSelectMenu, MultiPaginatorMenu, APIKeyConfirmation
from utils.constants import BLANK_COLOR, GREEN_COLOR
from utils.timestamp import td_format
from utils.utils import invis_embed, failure_embed, require_settings
from erm import is_staff, is_management


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="staff_sync",
        description="Internal Use Command, used for connection staff privileged individuals to their Roblox counterparts.",
        extras={"category": "Utility"},
        hidden=True,
        with_app_command=False,
    )
    @commands.has_role(988055417907200010)
    async def staff_sync(self, ctx: commands.Context, discord_id: int, roblox_id: int):
        from bson import ObjectId
        from datamodels.StaffConnections import StaffConnection

        await self.bot.staff_connections.insert_connection(
            StaffConnection(
                roblox_id=roblox_id, discord_id=discord_id, document_id=ObjectId()
            )
        )
        roblox_user = await self.bot.roblox.get_user(roblox_id)
        await ctx.send(
            embed=discord.Embed(
                title="Staff Sync",
                description=f"Successfully synced <@{discord_id}> to {roblox_user.name}",
                color=BLANK_COLOR,
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
            title="Bot Status",
            color=BLANK_COLOR,
        )

        if ctx.guild is not None:
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon,
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
                f"> **Latency:** `{latency}ms`\n"
                f"> **Uptime:** <t:{int(self.bot.start_time)}:R>\n"
                f"> **Database Connection:** {status}\n"
                f"> **Shards:** `{self.bot.shard_count-1}`\n"
            ),
            inline=False,
        )

        embed.set_footer(
            text=f"Shard {ctx.guild.shard_id if ctx.guild else 0}/{self.bot.shard_count-1}"
        )
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_thumbnail(url=ctx.guild.icon)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="modpanel",
        aliases=["panel"],
        description="Get the link to this server's mod panel.",
        extras={"category": "Website"},
    )
    @is_staff()
    @require_settings()
    async def mod_panel(self, ctx: commands.Context):
        guild_icon = ctx.guild.icon.url if ctx.guild.icon else None

        await ctx.send(
            embed=discord.Embed(
                color=BLANK_COLOR,
                description="Visit your server's Moderation Panel using the button below.",
            ).set_author(name=ctx.guild.name, icon_url=guild_icon),
            view=LinkView(
                label="Mod Panel", url=f"https://ermbot.xyz/{ctx.guild.id}/panel"
            ),
        )

    @commands.hybrid_command(
        name="dashboard",
        aliases=["dash", "applications"],
        description="Get the link to manage your server through the dashboard.",
        extras={"category": "Website"},
    )
    @is_management()
    async def dashboard(self, ctx: commands.Context):
        guild_icon = ctx.guild.icon.url if ctx.guild.icon else None

        await ctx.send(
            embed=discord.Embed(
                color=BLANK_COLOR,
                description="Visit your server's Dashboard using the button below.",
            ).set_author(name=ctx.guild.name, icon_url=guild_icon),
            view=LinkView(
                label="Dashboard", url=f"https://ermbot.xyz/{ctx.guild.id}/dashboard"
            ),
        )

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
                color=BLANK_COLOR,
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
            title="About ERM",
            color=BLANK_COLOR,
            description="ERM is the all-in-one approach to game moderation logging, shift logging and more.",
        )

        embed.add_field(
            name=f"Bot Information",
            value=(
                "> **Website:** [View Website](https://ermbot.xyz)\n"
                "> **Support:** [Join Server](https://discord.gg/FAC629TzBy)\n"
                f"> **Invite:** [Invite Bot](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands)\n"
                "> **Documentation:** [View Documentation](https://docs.ermbot.xyz)\n"
                "> **Desktop:** [Download ERM Desktop](https://ermbot.xyz/download)"
            ),
            inline=False,
        )
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.display_avatar.url,
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_group(name="api")
    async def api(self, ctx):
        pass

    @commands.guild_only()
    @api.command(
        name="generate",
        description="Generate an API key for your server",
        extras={"category": "Utility"},
    )
    @is_management()
    @require_settings()
    async def api_generate(self, ctx: commands.Context):
        view = APIKeyConfirmation(ctx.author.id)
        msg = await ctx.send(
            embed=discord.Embed(
                title="Generate API Key",
                description="Are you sure you want to generate an API key? This will invalidate any existing keys.",
                color=BLANK_COLOR,
            ),
            view=view,
            ephemeral=isinstance(ctx.interaction, discord.Interaction),
        )

        await view.wait()
        if not view.value:
            return

        api_url = f"{config('OPENERM_API_URL')}/api/v1/auth/token"
        auth_token = config("OPENERM_AUTH_TOKEN")
        full_url = f"{api_url}?guild_id={ctx.guild.id}&auth_token={auth_token}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(full_url) as response:

                    response_text = await response.text()

                    if response.status == 200:
                        api_key = response_text

                        if isinstance(ctx.interaction, discord.Interaction):
                            await ctx.send(
                                embed=discord.Embed(
                                    title="API Key Generated",
                                    description="Here is your API key. Please save it somewhere safe - we won't show it again.",
                                    color=BLANK_COLOR,
                                ).add_field(name="API Key", value=f"```{api_key}```"),
                                ephemeral=True,
                            )
                        else:
                            await ctx.author.send(
                                embed=discord.Embed(
                                    title="API Key Generated",
                                    description="Here is your API key. Please save it somewhere safe - we won't show it again.",
                                    color=BLANK_COLOR,
                                ).add_field(name="API Key", value=f"```{api_key}```")
                            )
                            await msg.edit(
                                embed=discord.Embed(
                                    title=f"{self.bot.emoji_controller.get_emoji('success')} API Key Generated",
                                    description="I have successfully generated an API key and sent it to your DMs!",
                                    color=GREEN_COLOR,
                                ),
                                view=None,
                            )
                    else:
                        error_msg = f"API returned non-200 status: {response.status}"
                        logging.error(error_msg)
                        await ctx.send(
                            embed=discord.Embed(
                                title="Error",
                                description="Failed to generate API key. Please try again later.",
                                color=BLANK_COLOR,
                            ),
                            ephemeral=isinstance(ctx.interaction, discord.Interaction),
                        )
            except aiohttp.ClientError as e:
                error_msg = f"API request failed: {str(e)}"
                logging.error(error_msg)
                await ctx.send(
                    embed=discord.Embed(
                        title="Error",
                        description="Failed to connect to API. Please try again later.",
                        color=BLANK_COLOR,
                    ),
                    ephemeral=isinstance(ctx.interaction, discord.Interaction),
                )


async def setup(bot):
    await bot.add_cog(Utility(bot))
