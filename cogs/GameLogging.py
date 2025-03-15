import datetime

import discord
import pytz
from bson import ObjectId
from discord import app_commands
from discord.ext import commands

from erm import is_staff, admin_predicate, management_predicate, staff_predicate
from menus import CustomModalView, UserSelect
from utils.constants import BLANK_COLOR, GREEN_COLOR
from utils.timestamp import td_format
from utils.utils import invis_embed, require_settings, time_converter


class GameLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def check_missing(self, settings, section):
        if not settings:
            return False

        if not settings.get("game_logging"):
            return False

        if not settings.get("game_logging").get(section):
            return False

        if not settings.get("game_logging").get(section).get("enabled"):
            return False
        if not settings.get("game_logging").get(section).get("channel"):
            return False

        return True

    @commands.guild_only()
    @commands.hybrid_group(
        name="staff",
        description="Request more staff to be in-game!",
        extras={"category": "Game Logging"},
    )
    async def staff(self, ctx: commands.Context):
        pass

    @staff.command(
        name="request",
        description="Send a Staff Request to get more staff in-game!",
        extras={"category": "Game Logging"},
    )
    @app_commands.describe(reason="Reason for your Staff Request!")
    @require_settings()
    async def staff_request(self, ctx: commands.Context, *, reason: str):
        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        game_logging = settings.get("game_logging", {})
        if game_logging == {}:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Configured",
                    description="Game Logging is not configured within this server.",
                    color=BLANK_COLOR,
                )
            )

        staff_requests = game_logging.get("staff_requests", {})
        if staff_requests == {}:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Configured",
                    description="Staff Requests is not configured within this server.",
                    color=BLANK_COLOR,
                )
            )
        enabled = staff_requests.get("enabled", False)
        if not enabled:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Staff Requests are not enabled within this server.",
                    color=BLANK_COLOR,
                )
            )

        permission_level = staff_requests.get("permission_level", 4)
        has_permission = True
        if permission_level == 3:
            if not await admin_predicate(ctx):
                has_permission = False
            else:
                has_permission = True
        if permission_level == 2:
            if not await management_predicate(ctx):
                has_permission = False
            else:
                has_permission = True
        if permission_level == 1:
            if not await staff_predicate(ctx):
                has_permission = False
            else:
                has_permission = True
        if not has_permission:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Permitted",
                    description=f"You are missing the **{ {1: 'Staff', 2: 'Management', 3: 'Admin'}.get(permission_level) }** permission to make a Staff Request.",
                    color=BLANK_COLOR,
                )
            )

        last_submitted_staff_request = [
            i
            async for i in self.bot.staff_requests.db.find(
                {"user_id": ctx.author.id, "guild_id": ctx.guild.id}
            )
            .sort({"_id": -1})
            .limit(1)
        ]
        if len(last_submitted_staff_request) != 0:
            last_submitted_staff_request = last_submitted_staff_request[0]
            document_id: ObjectId = last_submitted_staff_request["_id"]
            timestamp = document_id.generation_time.timestamp()
            if (
                timestamp + staff_requests.get("cooldown", 0)
                > datetime.datetime.now(tz=pytz.UTC).timestamp()
            ):
                return await ctx.send(
                    embed=discord.Embed(
                        title="Cooldown",
                        description="You are on cooldown from making Staff Requests.",
                        color=BLANK_COLOR,
                    )
                )

        staff_clocked_in = await self.bot.shift_management.shifts.db.count_documents(
            {"EndEpoch": 0, "Guild": ctx.guild.id}
        )
        if (
            staff_requests.get("min_staff") is not None
            and staff_requests.get("min_staff") > 0
        ):
            if staff_clocked_in <= staff_requests.get("min_staff", 0):
                return await ctx.send(
                    embed=discord.Embed(
                        title="Minimum Staff",
                        description=f"**{staff_requests.get('min_staff')}** members of staff are required to be in-game for a Staff Request!",
                        color=BLANK_COLOR,
                    )
                )

        if (
            staff_requests.get("max_staff") is not None
            and staff_requests.get("max_staff") > 0
        ):
            if staff_clocked_in > staff_requests.get("max_staff", 0):
                return await ctx.send(
                    embed=discord.Embed(
                        title="Maximum Staff",
                        description="There are more than the maximum number of staff online for a Staff Request!",
                        color=BLANK_COLOR,
                    )
                )

        document = {
            "user_id": ctx.author.id,
            "guild_id": ctx.guild.id,
            "username": ctx.author.name,
            "avatar": ctx.author.display_avatar.url.split("/")[-1].split(".")[0],
            "reason": reason,
            "active": True,
            "created_at": datetime.datetime.now(tz=pytz.UTC),
            "acked": [],
        }
        result = await self.bot.staff_requests.db.insert_one(document)
        o_id = result.inserted_id
        self.bot.dispatch("staff_request_send", o_id)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.bot.emoji_controller.get_emoji('success')} Sent Staff Request",
                description="Your Staff Request has been sent successfully.",
                color=GREEN_COLOR,
            )
        )

    @commands.guild_only()
    @commands.hybrid_group(
        name="game",
        description="Manage your game with logging such as messages, and events",
        extras={"category": "Game Logging"},
    )
    async def game(self, ctx):
        pass

    @commands.guild_only()
    @game.command(
        name="message",
        description="Log all announcements and messages in your game",
        extras={"category": "Game Logging"},
    )
    @app_commands.describe(announcement="The game message you are going to log.")
    @is_staff()
    @require_settings()
    async def game_message(self, ctx: commands.Context, *, announcement: str):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)

        check_settings = self.check_missing(configItem, "message")
        if check_settings is False:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Configured",
                    description="Game Announcement Logging is not configured.",
                    color=BLANK_COLOR,
                )
            )

        channel = ctx.guild.get_channel(
            configItem["game_logging"]["message"]["channel"]
        )
        if not channel:
            return await ctx.reply(
                embed=discord.Embed(
                    title="Invalid Channel",
                    description="The Game Announcement logging channel is invalid.",
                    color=BLANK_COLOR,
                )
            )

        embed = discord.Embed(
            title="Message Logged",
            color=BLANK_COLOR,
        )

        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)

        embed.add_field(
            name="Announcement Information",
            value=(
                f"> **Staff:** {ctx.author.mention}\n"
                f"> **Announcement:** {announcement}\n"
                f"> **At:** <t:{int(datetime.datetime.now(tz=pytz.UTC).timestamp())}>"
            ),
            inline=False,
        )
        if channel is None:
            return
        await channel.send(embed=embed)
        await ctx.send(
            embed=discord.Embed(
                title=f"{self.bot.emoji_controller.get_emoji('success')} Logged Announcement",
                description="Your Game Announcement has been successfully logged!",
                color=GREEN_COLOR,
            )
        )

    @commands.guild_only()
    @game.command(
        name="sts",
        description="Log a Shoulder-to-Shoulder in your game",
        extras={"category": "Game Logging"},
    )
    async def game_sts(self, ctx: commands.Context, duration: str, *, reason: str):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)

        settings_value = self.check_missing(configItem, "sts")
        if not settings_value:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Configured",
                    description="Game STS Logging is not configured.",
                    color=BLANK_COLOR,
                )
            )

        channel = ctx.guild.get_channel(configItem["game_logging"]["sts"]["channel"])
        if not channel:
            return await ctx.reply(
                embed=discord.Embed(
                    title="Invalid Channel",
                    description="The Game STS logging channel is invalid.",
                    color=BLANK_COLOR,
                )
            )
        view = UserSelect(ctx.author.id)

        sts_msg = await ctx.reply(
            embed=discord.Embed(
                title="Participants",
                description="What staff members took part in this STS?",
                color=BLANK_COLOR,
            ),
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.value:
            members = view.value
        else:
            return

        embed = discord.Embed(
            title="STS Logged",
            color=BLANK_COLOR,
        )

        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)

        embed.add_field(
            name="Staff Members",
            value="\n".join(
                [
                    (f"**{index+1}.** " + member.mention)
                    for index, member in enumerate(members)
                ]
            ),
            inline=False,
        )

        try:
            duration = time_converter(duration)
        except ValueError:
            return await ctx.send(
                embed=discord.Embed(
                    title="Invalid Time",
                    description="This is an invalid duration format.",
                    color=BLANK_COLOR,
                )
            )

        embed.add_field(
            name="STS Information",
            value=(
                f"> **Host:** {ctx.author.mention}\n"
                f"> **Duration:** {td_format(datetime.timedelta(seconds=duration))}\n"
                f"> **Hosted At:** <t:{int(ctx.message.created_at.timestamp())}>\n"
                f"> **Reason:** {reason}"
            ),
            inline=False,
        )

        if channel is None:
            return
        await channel.send(embed=embed)

        await sts_msg.edit(
            embed=discord.Embed(
                title=f"{self.bot.emoji_controller.get_emoji('success')} Logged STS",
                description="I have successfully logged your STS!",
                color=GREEN_COLOR,
            ),
            view=None,
        )

    @commands.guild_only()
    @game.command(
        name="priority",
        description="Log Roleplay Permissions and Priorities in your game",
        extras={"category": "Game Logging"},
    )
    @is_staff()
    async def game_priority(self, ctx: commands.Context, duration: str, *, reason):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)

        check_settings = self.check_missing(configItem, "priority")
        if not check_settings:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Configured",
                    description="Game Priority Logging is not configured.",
                    color=BLANK_COLOR,
                )
            )

        channel = ctx.guild.get_channel(
            configItem["game_logging"]["priority"]["channel"]
        )
        if not channel:
            return await ctx.reply(
                embed=discord.Embed(
                    title="Invalid Channel",
                    description="The Game Priority logging channel is invalid.",
                    color=BLANK_COLOR,
                )
            )

        view = CustomModalView(
            ctx.author.id,
            "User List",
            "User List",
            [
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
            embed=discord.Embed(
                title="Users Involved",
                description="What users are going to be involved with this priority?",
                color=BLANK_COLOR,
            ),
            view=view,
        )
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.users:
            users = view.modal.users.value
        else:
            return

        users = users.split("\n")

        embed = discord.Embed(
            title="Priority Logged",
            color=BLANK_COLOR,
        )

        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)

        embed.add_field(
            name="Players",
            value="\n".join(
                [(f"**{index+1}.** " + player) for index, player in enumerate(users)]
            ),
            inline=False,
        )

        try:
            duration = time_converter(duration)
        except ValueError:
            return await prio_msg.edit(
                embed=discord.Embed(
                    title="Invalid Time",
                    description="This time is not a valid duration.",
                    color=BLANK_COLOR,
                )
            )

        embed.add_field(
            name="Priority Information",
            value=(
                f"> **Staff:** {ctx.author.mention}\n"
                f"> **Duration:** {td_format(datetime.timedelta(seconds=duration))}\n"
                f"> **Reason:** {reason}\n"
                f"> **At:** <t:{int(ctx.message.created_at.timestamp())}>"
            ),
            inline=False,
        )

        if channel is None:
            return

        await channel.send(embed=embed)

        await prio_msg.edit(
            view=None,
            embed=discord.Embed(
                title=f"{self.bot.emoji_controller.get_emoji('success')} Logged Priority",
                description="I have successfully logged the priority request.",
                color=GREEN_COLOR,
            ),
        )


async def setup(bot):
    await bot.add_cog(GameLogging(bot))
