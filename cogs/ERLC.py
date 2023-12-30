import datetime

import discord
import roblox
from discord.ext import commands

from erm import is_staff
from menus import ReloadView
from utils.constants import *
from utils.prc_api import Player, ServerStatus, KillLog


class ERLC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(
        name="erlc"
    )
    async def server(self, ctx: commands.Context):
        pass

    @server.command(
        name="info",
        description="Get information about the current players in your ER:LC server."
    )
    @is_staff()
    async def server_info(self, ctx: commands.Context, guild_id: str):
        guild_id = int(guild_id)
        status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        players: list[Player] = await self.bot.prc_api.get_server_players(guild_id)
        queue: list[Player] = await self.bot.prc_api.get_server_queue(guild_id)
        client = roblox.Client()

        embeds = []
        embed1 = discord.Embed(
            title=f"{status.name}",
            color=GREEN_COLOR
        )
        embed1.add_field(
            name="Basic Info",
            value=(
                f"<:replytop:1138257149705863209> **Join Code:** {status.join_key}\n"
                f"<:replymiddle:1138257195121791046> **Current Players:** `{status.current_players}/{status.max_players}`\n"
                f"<:replybottom:1138257250448855090> **Queue:** `{len(queue)}`\n"
            ),
            inline=False
        )
        embed1.add_field(
            name="Server Ownership",
            value=(
                f"<:replytop:1138257149705863209> **Owner:** [{(await client.get_user(status.owner_id)).name}](https://roblox.com/users/{status.owner_id}/profile)\n"
                f"<:replybottom:1138257250448855090> **Co-Owners:** {f', '.join([f'[{(await client.get_user(plr_id)).name}](https://roblox.com/users/{plr_id}/profile)' for plr_id in status.co_owner_ids[:3]])}"
            )
        )

        await ctx.send(embed=embed1)


    @server.command(
        name="staff",
        description="See the online staff members in your ERLC server!"
    )
    @is_staff()
    async def server_staff(self, ctx: commands.Context, guild_id: str):
        guild_id = int(guild_id)
        status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        players: list[Player] = await self.bot.prc_api.get_server_players(guild_id)
        embed2 = discord.Embed(
            title="Current Staff Members",
            color=BLANK_COLOR
        )
        actual_players = []
        key_maps = {}
        for item in players:
            if item.permission == "Normal":
                actual_players.append(item)
            else:
                if item.permission not in key_maps:
                    key_maps[item.permission] = [item]
                else:
                    key_maps[item.permission].append(item)

        new_maps = [
            "Server Owner",
            "Server Co-Owner",
            "Server Administrator",
            "Server Moderator"
        ]
        new_vals = [
            key_maps.get('Server Owner', []),
            key_maps.get('Server Co-Owner', []),
            key_maps.get('Server Administrator', []),
            key_maps.get('Server Moderator', [])
        ]
        new_keymap = dict(zip(new_maps, new_vals))

        for key, value in new_keymap.items():
            embed2.add_field(
                name=key,
                value='\n'.join([f'- [{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in value]),
                inline=False
            )
        await ctx.send(embed=embed2)

    @server.command(
        name="kills",
        description="See the Kill Logs of your server."
    )
    @is_staff()
    async def kills(self, ctx: commands.Context, guild_id: str):
        async def operate_and_reload_kills(msg, guild_id: str):
            guild_id = int(guild_id)
            status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
            kill_logs: list[KillLog] = await self.bot.prc_api.fetch_kill_logs(guild_id)
            embed = discord.Embed(
                color=BLANK_COLOR,
                title="<:serverplayers:1176997968478470206> Server Kill Logs",
                description=""
            )
            for item in kill_logs:
                if item.timestamp < (datetime.datetime.now() - datetime.timedelta(minutes=15)).timestamp():
                    kill_logs.remove(item)

            embed.description += f"Past 15 Minutes [{len(kill_logs)}]\n"
            sorted_kill_logs = sorted(kill_logs, key=lambda log: log.timestamp, reverse=True)
            for log in sorted_kill_logs:
                if len(embed.description) >= 4000:
                   new = '\n'.join(embed.description.splitlines()[:-1])
                   embed.description = new
                   break
                embed.description += f"- [{log.killer_username}](https://roblox.com/users/{log.killer_user_id}/profile) killed [{log.killed_username}](https://roblox.com/users/{log.killed_user_id}/profile) • <t:{int(log.timestamp)}:R>\n"

            line0 = embed.description.splitlines()[0]
            line0 = f"**Past 15 Minutes [{len(embed.description.splitlines())-1}]**"
            print(embed.description)
            lines = [line0, *[line for index, line in enumerate(embed.description.split('\n')) if index != 0]]
            embed.description = '\n'.join(lines)



            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url
            )


                # embed.set_footer(icon_url="https://cdn.discordapp.com/emojis/1176999148084535326.webp?size=128&quality=lossless",
                #                   text="Last updated 5 seconds ago")
            if msg is None:
                view = ReloadView(ctx.author.id, operate_and_reload_kills, [None, guild_id])
                msg = await ctx.send(embed=embed, view=view)
                view.message = msg
                view.callback_args[0] = msg
            else:
                await msg.edit(embed=embed)

        await operate_and_reload_kills(None, guild_id)
    @server.command(
        name="players",
        description="See all players in the server."
    )
    @is_staff()
    async def server_players(self, ctx: commands.Context, guild_id: str):
        guild_id = int(guild_id)
        status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        players: list[Player] = await self.bot.prc_api.get_server_players(guild_id)
        embed2 = discord.Embed(
            title="<:serverplayers:1176997968478470206> Server Players",
            color=BLANK_COLOR,
            description=""
        )
        actual_players = []
        key_maps = {}
        staff = []
        for item in players:
            if item.permission == "Normal":
                actual_players.append(item)
            else:
                staff.append(item)

        embed2.description += (
            f"Server Staff [{len(staff)}]\n"
            '\n'.join([f'- [{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in staff])
        )

        embed2.description += (
            f"\n\nOnline Players [{len(actual_players)}]"
            '\n'.join([f'- [{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in actual_players])

        )

        embed2.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url
        )

        embed2.set_footer(icon_url="https://cdn.discordapp.com/emojis/1176999148084535326.webp?size=128&quality=lossless",
                          text="Last updated 5 seconds ago")
        await ctx.send(embed=embed2)


async def setup(bot):
    await bot.add_cog(ERLC(bot))