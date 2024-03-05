import datetime

import discord
import roblox
from discord.ext import commands

from erm import is_staff, is_management
from menus import ReloadView
from utils.constants import *
from utils.prc_api import Player, ServerStatus, KillLog, JoinLeaveLog, CommandLog
import utils.prc_api as prc_api
from discord import app_commands
import typing


class ERLC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    def is_server_linked():
        async def predicate(ctx: commands.Context):
            guild_id = ctx.guild.id
            # We're intentionally not handling this error here so that it raises if the server is not linked. actually how about we do
            try:
                await ctx.bot.prc_api.get_server_status(guild_id)
            except prc_api.ResponseFailure as exc:
                raise prc_api.ServerLinkNotFound(str(exc))
            return True
        return commands.check(predicate)

    async def secure_logging(self, guild_id, author_id, interpret_type: typing.Literal['Message', 'Hint', 'Command'], command_string: str, attempted: bool = False):
        settings = await self.bot.settings.find_by_id(guild_id)
        channel = ((settings or {}).get('game_security', {}) or {}).get('channel')
        try:
            channel = await (await self.bot.fetch_guild(guild_id)).fetch_channel(channel)
        except discord.HTTPException:
            channel = None
        bloxlink_user = await self.bot.bloxlink.find_roblox(author_id)
        # # print(bloxlink_user)
        server_status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        if channel is not None:
            if not attempted:
                await channel.send(embed=discord.Embed(
                    title="Remote Server Logs",
                    description=f"[{(await self.bot.bloxlink.get_roblox_info(bloxlink_user['robloxID']))['name']}:{bloxlink_user['robloxID']}](https://roblox.com/users/{bloxlink_user['robloxID']}/profile) used a command: {'`:m {}`'.format(command_string) if interpret_type == 'Message' else ('`:h {}`'.format(command_string) if interpret_type == 'Hint' else '`{}`'.format(command_string))}",
                    color=RED_COLOR
                ).set_footer(text=f"Private Server: {server_status.join_key}"))
            else:
                await channel.send(embed=discord.Embed(
                        title="Attempted Command Execution",
                        description=f"[{(await self.bot.bloxlink.get_roblox_info(bloxlink_user['robloxID']))['name']}:{bloxlink_user['robloxID']}](https://roblox.com/users/{bloxlink_user['robloxID']}/profile) attempted to use the command: {'`:m {}`'.format(command_string) if interpret_type == 'Message' else ('`:h {}`'.format(command_string) if interpret_type == 'Hint' else '`{}`'.format(command_string))}",
                        color=RED_COLOR
                    ).set_footer(text=f"Private Server: {server_status.join_key}")
                )   

    @commands.hybrid_group(
        name="erlc"
    )
    async def server(self, ctx: commands.Context):
        pass

    @server.command(
        name="message",
        description="Send a Message to your ERLC server with ERM!"
    )
    @is_staff()
    @is_server_linked()
    async def erlc_message(self, ctx: commands.Context, *, message: str):
        guild_id = ctx.guild.id
        
        await self.secure_logging(guild_id, ctx.author.id, 'Message', message)

        command_response = await self.bot.prc_api.run_command(guild_id, f":m {message}")
        if command_response[0] == 200:
            return await ctx.send(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Successfully Sent",
                    description="This message has been sent to the server!",
                    color=GREEN_COLOR
                )
            )
        else:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Executed",
                    description="This message has not been sent to the server successfully.",
                    color=BLANK_COLOR
                )
            )
        
    @server.command(
        name="hint",
        description="Send a Hint to your ERLC server with ERM!"
    )
    @is_staff()
    @is_server_linked()
    async def erlc_hint(self, ctx: commands.Context, *, hint: str):
        guild_id = ctx.guild.id

        await self.secure_logging(guild_id, ctx.author.id, 'Hint', hint)

        command_response = await self.bot.prc_api.run_command(guild_id, f":h {hint}")
        if command_response[0] == 200:
            return await ctx.send(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Successfully Sent",
                    description="This Hint has been sent to the server!",
                    color=GREEN_COLOR
                )
            )
        else:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Executed",
                    description="This Hint has not been sent to the server successfully.",
                    color=BLANK_COLOR
                )
            )


    @server.command(
        name="link",
        description="Link your ERLC server with ERM!",
        extras={'ignoreDefer': True}
    )
    @is_management()
    @app_commands.describe(
        key='Your PRC Server Key - check your server settings for details'
    )
    async def server_link(self, ctx: commands.Context, key: str):
        status: int | ServerStatus = await self.bot.prc_api.send_test_request(key)
        if isinstance(status, int):
            await (ctx.send if not ctx.interaction else ctx.interaction.response.send_message)(
                embed=discord.Embed(
                    title="Incorrect Key",
                    description="This Server Key is invalid and nonfunctional. Ensure you've entered it correctly.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )
        else:
            await self.bot.server_keys.upsert({
                "_id": ctx.guild.id,
                "key": key
            })

            await (ctx.send if not ctx.interaction else ctx.interaction.response.send_message)(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Successfully Changed",
                    description="I have changed the Server Key successfully. You can now run ERLC commands on your server.",
                    color=GREEN_COLOR
                ),
                ephemeral=True
            )
            


    @server.command(
        name="command",
        description="Send a direct command to your ERLC server, under \"Remote Server Management\"",
        extras={'ephemeral': True}
    )
    @app_commands.describe(
        command="The command to send to your ERLC server"
    )
    @is_management()
    @is_server_linked()
    async def server_send_command(self, ctx: commands.Context, *, command: str):
        if command[0] != ':':
            command = ':' + command
        elevated_privileges = None
        status: ServerStatus = await self.bot.prc_api.get_server_status(ctx.guild.id)
        for item in (status.co_owner_ids + [status.owner_id]):
            if int(item) == int((await self.bot.bloxlink.find_roblox(ctx.author.id) or {}).get('robloxID') or 0):
                elevated_privileges = True
                break
        else:
            elevated_privileges = False

        if any([i in command for i in [':admin', ':unadmin']]) and not elevated_privileges:
            # REQUIRES ELEVATION
            if ((await self.bot.settings.find_by_id(ctx.guild.id) or {}).get('ERLC', {}) or {}).get('elevation_required', True):
                await self.secure_logging(ctx.guild.id, ctx.author.id, 'Command', command, True)
                if ctx.interaction:
                    await ctx.interaction.followup.send(
                        embed=discord.Embed(
                            title="Not Authorized",
                            description="This command is privileged and requires special elevation.",
                            color=BLANK_COLOR
                        ),
                        ephemeral=True
                    )
                else:
                    await ctx.send(
                        embed=discord.Embed(
                            title="Not Authorized",
                            description="This command is privileged and requires special elevation.",
                            color=BLANK_COLOR
                        )
                    )
                return

        await self.secure_logging(int(ctx.guild.id), ctx.author.id, 'Command', command)

        guild_id = int(ctx.guild.id)
        command_response = await self.bot.prc_api.run_command(guild_id, command)
        if command_response[0] == 200:
            return await ctx.send(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Successfully Ran",
                    description="This command should have now been executed in your server.",
                    color=GREEN_COLOR
                )
            )
        else:
            return await ctx.send(
                embed=discord.Embed(
                    title=f"Not Executed ({command_response[0]})",
                    description="This command has not been sent to the server successfully.",
                    color=BLANK_COLOR
                )
            )

    @server.command(
        name="info",
        description="Get information about the current players in your ER:LC server."
    )
    @is_staff()
    @is_server_linked()
    async def server_info(self, ctx: commands.Context):
        guild_id = int(ctx.guild.id)
        status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        players: list[Player] = await self.bot.prc_api.get_server_players(guild_id) 
        queue: int = await self.bot.prc_api.get_server_queue(guild_id, minimal=True) # this only returns the count
        client = roblox.Client()

        embeds = []
        embed1 = discord.Embed(
            title=f"{status.name}",
            color=BLANK_COLOR
        )
        embed1.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
        )
        embed1.add_field(
            name="Basic Info",
            value=(
                f"> **Join Code:** {status.join_key}\n"
                f"> **Current Players:** `{status.current_players}/{status.max_players}`\n"
                f"> **Queue:** `{queue}`\n"
            ),
            inline=False
        )
        embed1.add_field(
            name="Server Ownership",
            value=(
                f"> **Owner:** [{(await client.get_user(status.owner_id)).name}](https://roblox.com/users/{status.owner_id}/profile)\n"
                f"> **Co-Owners:** {f', '.join([f'[{user.name}](https://roblox.com/users/{user.id}/profile)' for user in await client.get_users(status.co_owner_ids, expand=False)])}"
            ),
            inline=False
        )

        embed1.add_field(
            name="Staff Statistics",
            value=(
                f"> **Moderators:** `{len(list(filter(lambda x: x.permission == 'Server Moderator', players)))}`\n"
                f"> **Administrators:** `{len(list(filter(lambda x: x.permission == 'Server Administrator', players)))}`\n"
                f"> **Staff In-Game:** `{len(list(filter(lambda x: x.permission != 'Normal', players)))}`\n"
                f"> **Staff Clocked In:** `{await self.bot.shift_management.shifts.db.count_documents({'Guild': guild_id, 'EndEpoch': 0})}`"
            ),
            inline=False
        )

        await ctx.send(embed=embed1)


    @server.command(
        name="staff",
        description="See the online staff members in your ERLC server!"
    )
    @is_staff()
    @is_server_linked()
    async def server_staff(self, ctx: commands.Context):
        guild_id = int(ctx.guild.id)
        status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        players: list[Player] = await self.bot.prc_api.get_server_players(guild_id)
        embed2 = discord.Embed(
            title="Online Staff Members",
            color=BLANK_COLOR
        )
        embed2.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
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
            "Server Owners",
            "Server Administrator",
            "Server Moderator"
        ]
        new_vals = [
            key_maps.get('Server Owner', []) + key_maps.get('Server Co-Owner', []),
            key_maps.get('Server Administrator', []),
            key_maps.get('Server Moderator', [])
        ]
        new_keymap = dict(zip(new_maps, new_vals))

        for key, value in new_keymap.items():
            if (value := '\n'.join([f'> [{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in value])) not in ['', '\n']:
                embed2.add_field(
                    name=f'{key}',
                    value=value,
                    inline=False
                )
        await ctx.send(embed=embed2)

    @server.command(
        name="kills",
        description="See the Kill Logs of your server."
    )
    @is_staff()
    @is_server_linked()
    async def kills(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        async def operate_and_reload_kills(msg, guild_id: str):
            guild_id = int(guild_id)
            # status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
            kill_logs: list[KillLog] = await self.bot.prc_api.fetch_kill_logs(guild_id)
            embed = discord.Embed(
                color=BLANK_COLOR,
                title="Server Kill Logs",
                description=""
            )

            sorted_kill_logs = sorted(kill_logs, key=lambda log: log.timestamp, reverse=True)
            for log in sorted_kill_logs:
                embed.description += f"> [{log.killer_username}](https://roblox.com/users/{log.killer_user_id}/profile) killed [{log.killed_username}](https://roblox.com/users/{log.killed_user_id}/profile) • <t:{int(log.timestamp)}:R>\n"

            if embed.description in ['', '\n']:
                embed.description = "> No kill logs found."


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
        name="playerlogs",
        description="See the Join and Leave logs of your server."
    )
    @is_staff()
    @is_server_linked()
    async def playerlogs(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        async def operate_and_reload_playerlogs(msg, guild_id: str):
            guild_id = int(guild_id)
            # status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
            player_logs: list[JoinLeaveLog] = await self.bot.prc_api.fetch_player_logs(guild_id)
            embed = discord.Embed(
                color=BLANK_COLOR,
                title="Player Join/Leave Logs",
                description=""
            )

            sorted_logs = sorted(player_logs, key=lambda log: log.timestamp, reverse=True)
            for log in sorted_logs:
                embed.description += f"> [{log.username}](https://roblox.com/users/{log.user_id}/profile) {'joined the server' if log.type == 'join' else 'left the server'} • <t:{int(log.timestamp)}:R>\n"

                
            if embed.description in ['', '\n']:
                embed.description = "> No player logs found."


            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url
            )


                # embed.set_footer(icon_url="https://cdn.discordapp.com/emojis/1176999148084535326.webp?size=128&quality=lossless",
                #                   text="Last updated 5 seconds ago")
            if msg is None:
                view = ReloadView(ctx.author.id, operate_and_reload_playerlogs, [None, guild_id])
                msg = await ctx.send(embed=embed, view=view)
                view.message = msg
                view.callback_args[0] = msg
            else:
                await msg.edit(embed=embed)

        await operate_and_reload_playerlogs(None, guild_id)

    @server.command(
        name="logs",
        description="See the Command Logs of your server."
    )
    @is_staff()
    @is_server_linked()
    async def commandlogs(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        async def operate_and_reload_commandlogs(msg, guild_id: str):
            guild_id = int(guild_id)
            # status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
            command_logs: list[CommandLog] = await self.bot.prc_api.fetch_server_logs(guild_id)
            embed = discord.Embed(
                color=BLANK_COLOR,
                title="Command Logs",
                description=""
            )

            sorted_logs = sorted(command_logs, key=lambda log: log.timestamp, reverse=True)
            for log in sorted_logs:
                embed.description += f"> [{log.username}](https://roblox.com/users/{log.user_id}/profile) ran the command `{log.command}` • <t:{int(log.timestamp)}:R>\n"

            if embed.description in ['', '\n']:
                embed.description = "> No player logs found."


            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url
            )


                # embed.set_footer(icon_url="https://cdn.discordapp.com/emojis/1176999148084535326.webp?size=128&quality=lossless",
                #                   text="Last updated 5 seconds ago")
            if msg is None:
                view = ReloadView(ctx.author.id, operate_and_reload_commandlogs, [None, guild_id])
                msg = await ctx.send(embed=embed, view=view)
                view.message = msg
                view.callback_args[0] = msg
            else:
                await msg.edit(embed=embed)

        await operate_and_reload_commandlogs(None, guild_id)

    @server.command(
        name="players",
        description="See all players in the server."
    )
    @is_staff()
    @is_server_linked()
    async def server_players(self, ctx: commands.Context):
        guild_id = int(ctx.guild.id)
        # status: ServerStatus = await self.bot.prc_api.get_server_status(guild_id)
        players: list[Player] = await self.bot.prc_api.get_server_players(guild_id)
        queue: list[Player] = await self.bot.prc_api.get_server_queue(guild_id)
        embed2 = discord.Embed(
            title=f"Server Players [{len(players)}]",
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
            f"**Server Staff [{len(staff)}]**\n" + 
            ', '.join([f'[{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in staff])
        )
        if list(embed2.description).index(']') > len(embed2.description) + 5:
            embed2.description += "No players."
        
        
        embed2.description += (
            f"\n\n**Online Players [{len(actual_players)}]**\n" +
            ', '.join([f'[{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in actual_players])
        )
        if list(embed2.description).index(']') > len(embed2.description) + 5:
            embed2.description += "No players."


        embed2.description += (
            f"\n\n**Queue [{len(queue)}]**\n" +
            ', '.join([f'[{plr.username}](https://roblox.com/users/{plr.id}/profile)' for plr in queue])
        )
        if list(embed2.description).index(']') > len(embed2.description) + 5:
            embed2.description += "No players."

        embed2.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url
        )

        await ctx.send(embed=embed2)


async def setup(bot):
    await bot.add_cog(ERLC(bot))