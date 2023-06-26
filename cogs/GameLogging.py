import datetime

import discord
from discord.ext import commands

from menus import CustomModalView, UserSelect
from utils.timestamp import td_format
from utils.utils import invis_embed


class GameLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name="game",
        description="Manage your game with logging such as messages, and events",
        extras={"category": "Game Logging"},
    )
    async def game(self, ctx):
        pass

    @game.command(
        name="message",
        description="Log all announcements and messages in your game",
        extras={"category": "Game Logging"},
    )
    async def game_message(self, ctx):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        if not configItem.get("game_logging"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup for game logging! Run `/config change` to setup game logging."
            )

        if not configItem["game_logging"].get("message"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup for message logging! Run `/config change` to setup message logging."
            )

        if not configItem["game_logging"].get("message").get("enabled"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not enabled message logging! Run `/config change` to enable message logging."
            )

        if not configItem["game_logging"].get("message").get("channel"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not set a channel for message logging! Run `/config change` to setup a channel."
            )

        channel = ctx.guild.get_channel(
            configItem["game_logging"]["message"]["channel"]
        )
        if not channel:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not set a valid channel for message logging."
            )

        view = CustomModalView(
            ctx.author.id,
            "Announcement",
            "Announcement",
            [
                (
                    "announcement",
                    discord.ui.TextInput(
                        placeholder="The message you would like to log",
                        label="Message",
                        style=discord.TextStyle.long,
                        min_length=1,
                        max_length=1800,
                    ),
                )
            ],
        )

        message_msg = await ctx.reply(
            f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what message would you like to log?",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.announcement:
            announcement = view.modal.announcement.value

            embed = discord.Embed(
                title="<:ERMCheck:1111089850720976906>  Message Logged",
                color=0xED4348,
            ).set_thumbnail(url=ctx.author.display_avatar.url)

            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )

            embed.add_field(
                name="<:ERMAdmin:1111100635736187011> Staff Member",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{ctx.author.mention}",
                inline=False,
            )

            embed.add_field(
                name="<:ERMList:1111099396990435428> Message",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{announcement}",
                inline=False,
            )

            if channel is None:
                return

            await message_msg.edit(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name}**, I've logged your message.",
                view=None,
            )

    @game.command(
        name="sts",
        description="Log a Shoulder-to-Shoulder in your game",
        extras={"category": "Game Logging"},
    )
    async def game_sts(self, ctx):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        if not configItem.get("game_logging"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup for game logging! Run `/config change` to setup game logging."
            )

        if not configItem["game_logging"].get("message"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup for STS logging! Run `/config change` to setup STS logging."
            )

        if not configItem["game_logging"].get("sts").get("enabled"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not enabled STS logging! Run `/config change` to enable STS logging."
            )

        if not configItem["game_logging"].get("sts").get("channel"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not set a channel for STS logging! Run `/config change` to setup a channel."
            )

        channel = ctx.guild.get_channel(configItem["game_logging"]["sts"]["channel"])
        if not channel:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not set a valid channel for STS logging."
            )
        view = UserSelect(ctx.author.id)

        sts_msg = await ctx.reply(
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** which staff members took part in this STS?",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.value:
            members = view.value
        else:
            return

        view = CustomModalView(
            ctx.author.id,
            "Reason",
            "Reason",
            [
                (
                    "reason",
                    discord.ui.TextInput(
                        placeholder="The reason for the Shoulder-to-Shoulder",
                        label="Reason",
                        style=discord.TextStyle.short,
                        min_length=1,
                        max_length=600,
                    ),
                )
            ],
        )

        await sts_msg.edit(
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what was the reason for this STS?",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.reason:
            reason = view.modal.reason.value
        else:
            return

        view = CustomModalView(
            ctx.author.id,
            "Duration",
            "Duration",
            [
                (
                    "duration",
                    discord.ui.TextInput(
                        placeholder="Example: 10s, 40m, 30s",
                        label="Duration (s/m/h/d)",
                        style=discord.TextStyle.short,
                        min_length=1,
                        max_length=600,
                    ),
                )
            ],
        )

        await sts_msg.edit(
            embed=discord.Embed(
                color=0xED4348,
                description="<:ERMModify:1111100050718867577> **PRO TIP:** Use s/m/d for time formatting.",
            ),
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** how long did this STS last?",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.duration:
            duration = view.modal.duration.value
        else:
            return

        embed = discord.Embed(
            title="<:ERMCheck:1111089850720976906>  STS Logged",
            color=0xED4348,
        ).set_thumbnail(url=ctx.author.display_avatar.url)

        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.add_field(
            name="<:ERMAdmin:1111100635736187011> Staff Members",
            value="\n".join(
                [
                    (
                        f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>"
                        + member.mention
                    )
                    for member in members
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Reason",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{reason}",
            inline=False,
        )

        duration = duration.lower()
        if duration.endswith("s"):
            duration = int(duration[:-1])
        elif duration.endswith("m"):
            duration = int(duration[:-1]) * 60
        elif duration.endswith("h"):
            duration = int(duration[:-1]) * 60 * 60
        elif duration.endswith("d"):
            duration = int(duration[:-1]) * 60 * 60 * 24

        embed.add_field(
            name="<:ERMSchedule:1111091306089939054> Duration",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=duration))}",
            inline=False,
        )

        if channel is None:
            return
        await channel.send(embed=embed)

        await sts_msg.edit(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've logged your STS.",
            view=None,
        )

    @game.command(
        name="priority",
        description="Log Roleplay Permissions and Priorities in your game",
        extras={"category": "Game Logging"},
    )
    async def game_priority(self, ctx):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        if not configItem.get("game_logging"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup for priority logging! Run `/config change` to setup priority logging."
            )

        if not configItem["game_logging"].get("priority"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup for Priority logging! Run `/config change` to setup Priority logging."
            )

        if not configItem["game_logging"].get("priority").get("enabled"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not enabled Priority logging! Run `/config change` to enable Priority logging."
            )

        if not configItem["game_logging"].get("priority").get("channel"):
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not set a channel for Priority logging! Run `/config change` to setup a channel."
            )

        channel = ctx.guild.get_channel(
            configItem["game_logging"]["priority"]["channel"]
        )
        if not channel:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has not set a valid channel for Priority logging."
            )

        view = CustomModalView(
            ctx.author.id,
            "Reason",
            "Reason",
            [
                (
                    "reason",
                    discord.ui.TextInput(
                        placeholder="The reason for the Priority",
                        label="Reason",
                        style=discord.TextStyle.short,
                        min_length=1,
                        max_length=600,
                    ),
                ),
                (
                    "users",
                    discord.ui.TextInput(
                        placeholder="The users involved in the Priority. Separate by lines.\n\nExample:\nRoyalCrests\ni_iMikey\nmbrinkley",
                        label="Players",
                        style=discord.TextStyle.long,
                        min_length=1,
                        max_length=600,
                    ),
                ),
            ],
        )

        prio_msg = await ctx.reply(
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what was the reason for this priority?",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.reason:
            reason = view.modal.reason.value
        else:
            return

        if view.modal.users:
            users = view.modal.users.value
        else:
            return

        users = users.split("\n")

        view = CustomModalView(
            ctx.author.id,
            "Duration",
            "Duration",
            [
                (
                    "duration",
                    discord.ui.TextInput(
                        placeholder="Example: 10s, 40m, 30s",
                        label="Duration (s/m/h/d)",
                        style=discord.TextStyle.short,
                        min_length=1,
                        max_length=600,
                    ),
                )
            ],
        )

        await prio_msg.edit(
            embed=discord.Embed(
                color=0xED4348,
                description="<:ERMModify:1111100050718867577> **PRO TIP:** Use s/m/d for time formatting.",
            ),
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** how long will this priority last?",
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.duration:
            duration = view.modal.duration.value
        else:
            return

        embed = discord.Embed(
            title="<:ERMCheck:1111089850720976906>  Priority Logged",
            color=0xED4348,
        ).set_thumbnail(url=ctx.author.display_avatar.url)

        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.add_field(
            name="<:ERMUser:1111098647485108315>  Players",
            value="\n".join(
                [
                    (
                        f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>"
                        + player
                    )
                    for player in users
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428>  Reason",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{reason}",
            inline=False,
        )

        duration = duration.lower()
        if duration.endswith("s"):
            duration = int(duration[:-1])
        elif duration.endswith("m"):
            duration = int(duration[:-1]) * 60
        elif duration.endswith("h"):
            duration = int(duration[:-1]) * 60 * 60
        elif duration.endswith("d"):
            duration = int(duration[:-1]) * 60 * 60 * 24

        embed.add_field(
            name="<:ERMSchedule:1111091306089939054>  Duration",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.timedelta(seconds=duration))}",
            inline=False,
        )

        if channel is None:
            return

        await channel.send(embed=embed)

        await prio_msg.edit(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've logged your priority.",
            view=None,
            embed=None,
        )


async def setup(bot):
    await bot.add_cog(GameLogging(bot))
