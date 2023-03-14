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
            return await invis_embed(
                ctx,
                "You have not setup ERM. Please setup ERM via the `/setup` command before running this command.",
            )

        if not configItem.get("game_logging"):
            return await invis_embed(
                ctx,
                "You have not setup game logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("message"):
            return await invis_embed(
                ctx,
                "You have not setup Message logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("message").get("enabled"):
            return await invis_embed(
                ctx,
                "You have not enabled Message logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("message").get("channel"):
            return await invis_embed(
                ctx,
                "You have not set a channel for Message logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        channel = ctx.guild.get_channel(
            configItem["game_logging"]["message"]["channel"]
        )
        if not channel:
            return await invis_embed(
                ctx,
                "The channel you have set for Message logging is invalid. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        embed = discord.Embed(
            title="<:LinkIcon:1044004006109904966> Message Logging",
            description=f"<:ArrowRight:1035003246445596774> Please enter the message you would like to log.",
            color=0x2A2D31,
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

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.announcement:
            announcement = view.modal.announcement.value

            embed = discord.Embed(
                title="<:MessageIcon:1035321236793860116> Message Logged",
                description="*A new message has been logged in the server.*",
                color=0x2A2D31,
            )

            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )

            embed.add_field(
                name="<:staff:1035308057007230976> Staff Member",
                value=f"<:ArrowRight:1035003246445596774> {ctx.author.mention}",
                inline=False,
            )

            embed.add_field(
                name="<:MessageIcon:1035321236793860116> Message",
                value=f"<:ArrowRight:1035003246445596774> `{announcement}`",
                inline=False,
            )

            await channel.send(embed=embed)

            success_embed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description=f"<:ArrowRight:1035003246445596774> The message has been logged.",
                color=0x71C15F,
            )

            await ctx.send(embed=success_embed)
        return

    @game.command(
        name="sts",
        description="Log a Shoulder-to-Shoulder in your game",
        extras={"category": "Game Logging"},
    )
    async def game_sts(self, ctx):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await invis_embed(
                ctx,
                "You have not setup ERM. Please setup ERM via the `/setup` command before running this command.",
            )

        if not configItem.get("game_logging"):
            return await invis_embed(
                ctx,
                "You have not setup game logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("sts"):
            return await invis_embed(
                ctx,
                "You have not setup STS logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("sts").get("enabled"):
            return await invis_embed(
                ctx,
                "You have not enabled STS logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("sts").get("channel"):
            return await invis_embed(
                ctx,
                "You have not set a channel for STS logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        channel = ctx.guild.get_channel(configItem["game_logging"]["sts"]["channel"])
        if not channel:
            return await invis_embed(
                ctx,
                "The channel you have set for STS logging is invalid. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        embed = discord.Embed(
            title="<:LinkIcon:1044004006109904966> STS Logging",
            description=f"<:ArrowRight:1035003246445596774> Which staff members were involved in the Shoulder-to-Shoulder?",
            color=0x2A2D31,
        )

        view = UserSelect(ctx.author.id)

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.value:
            members = view.value
        else:
            return

        embed = discord.Embed(
            title="<:LinkIcon:1044004006109904966> STS Logging",
            description=f"<:ArrowRight:1035003246445596774> What was the reason for the Shoulder-to-Shoulder?",
            color=0x2A2D31,
        )

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

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.reason:
            reason = view.modal.reason.value
        else:
            return

        embed = discord.Embed(
            title="<:LinkIcon:1044004006109904966> STS Logging",
            description=f"<:ArrowRight:1035003246445596774> How long did the Shoulder-to-Shoulder take? (s/m/h/d)\n*Examples: 10s, 15m, 12h, 14m*",
            color=0x2A2D31,
        )

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

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.duration:
            duration = view.modal.duration.value
        else:
            return

        embed = discord.Embed(
            title="<:MessageIcon:1035321236793860116> STS Logged",
            description="*A new STS has been logged in the server.*",
            color=0x2A2D31,
        )

        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.add_field(
            name="<:staff:1035308057007230976> Staff Members",
            value="\n".join(
                [
                    (f"<:ArrowRight:1035003246445596774> " + member.mention)
                    for member in members
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="<:EditIcon:1042550862834323597> Reason",
            value=f"<:ArrowRight:1035003246445596774> {reason}",
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
            name="<:EditIcon:1042550862834323597> Duration",
            value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=duration))}",
            inline=False,
        )

        await channel.send(embed=embed)

        success_embed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description=f"<:ArrowRight:1035003246445596774> This STS has been logged.",
            color=0x71C15F,
        )

        await ctx.send(embed=success_embed)

    @game.command(
        name="priority",
        description="Log Roleplay Permissions and Priorities in your game",
        extras={"category": "Game Logging"},
    )
    async def game_priority(self, ctx):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if not configItem:
            return await invis_embed(
                ctx,
                "You have not setup ERM. Please setup ERM via the `/setup` command before running this command.",
            )

        if not configItem.get("game_logging"):
            return await invis_embed(
                ctx,
                "You have not setup game logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("priority"):
            return await invis_embed(
                ctx,
                "You have not setup Priority logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("priority").get("enabled"):
            return await invis_embed(
                ctx,
                "You have not enabled Priority logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        if not configItem["game_logging"].get("priority").get("channel"):
            return await invis_embed(
                ctx,
                "You have not set a channel for Priority logging. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        channel = ctx.guild.get_channel(
            configItem["game_logging"]["priority"]["channel"]
        )
        if not channel:
            return await invis_embed(
                ctx,
                "The channel you have set for Priority logging is invalid. Please setup relevant game logging configurations via the `/config change` command before running this command.",
            )

        embed = discord.Embed(
            title="<:LinkIcon:1044004006109904966> Priority Logging",
            description=f"<:ArrowRight:1035003246445596774> Please provide some basic information regarding the Priority.",
            color=0x2A2D31,
        )

        view = CustomModalView(
            ctx.author.id,
            "Information",
            "Information",
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

        await ctx.send(embed=embed, view=view)
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

        embed = discord.Embed(
            title="<:LinkIcon:1044004006109904966> Priority Logging",
            description=f"<:ArrowRight:1035003246445596774> How long will the priority take? (s/m/h/d)\n*Examples: 10s, 15m, 12h, 14m*",
            color=0x2A2D31,
        )

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

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.modal.duration:
            duration = view.modal.duration.value
        else:
            return

        embed = discord.Embed(
            title="<:FlagIcon:1035258525955395664> Priority Logged",
            description="*A new priority has been logged in the server.*",
            color=0x2A2D31,
        )

        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        embed.add_field(
            name="<:staff:1035308057007230976> Players",
            value="\n".join(
                [(f"<:ArrowRight:1035003246445596774> " + player) for player in users]
            ),
            inline=False,
        )

        embed.add_field(
            name="<:EditIcon:1042550862834323597> Reason",
            value=f"<:ArrowRight:1035003246445596774> {reason}",
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
            name="<:EditIcon:1042550862834323597> Duration",
            value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=duration))}",
            inline=False,
        )

        await channel.send(embed=embed)

        success_embed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description=f"<:ArrowRight:1035003246445596774> This priority has been logged.",
            color=0x71C15F,
        )

        await ctx.send(embed=success_embed)


async def setup(bot):
    await bot.add_cog(GameLogging(bot))
