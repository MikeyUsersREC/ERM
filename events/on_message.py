import copy
import datetime
import logging
import string

import aiohttp
import discord
import num2words
import roblox
from discord.ext import commands
from reactionmenu import Page, ViewButton, ViewMenu, ViewSelect

from utils.constants import BLANK_COLOR
from utils.utils import generator
from menus import CustomSelectMenu, GameSecurityActions
from utils.timestamp import td_format
from utils.utils import get_guild_icon, get_prefix, invis_embed


class OnMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        bot = self.bot
        bypass_role = None

        if not hasattr(bot, "settings"):
            return

        if message.author == bot.user:
            return

        if not message.guild:
            return

        if isinstance(message.author, discord.User):
            msg = copy(message)
            msg.author = await message.guild.fetch_member(message.author.id)
            message = msg
        
        dataset = await bot.settings.find_by_id(message.guild.id)
        if dataset == None:
            return

        antiping_roles = None
        bypass_roles = None

        if "bypass_role" in dataset["antiping"].keys():
            bypass_role = dataset["antiping"]["bypass_role"]

        if isinstance(bypass_role, list):
            bypass_roles = [
                discord.utils.get(message.guild.roles, id=role) for role in bypass_role
            ]
        else:
            bypass_roles = [discord.utils.get(message.guild.roles, id=bypass_role)]

        if isinstance(dataset["antiping"]["role"], list):
            antiping_roles = [
                discord.utils.get(message.guild.roles, id=role)
                for role in dataset["antiping"]["role"]
            ]
        elif isinstance(dataset["antiping"]["role"], int):
            antiping_roles = [
                discord.utils.get(message.guild.roles, id=dataset["antiping"]["role"])
            ]
        else:
            antiping_roles = None

        aa_detection = False
        aa_detection_channel = None
        webhook_channel = None
        remote_commands = False
        remote_command_channel = None

        if dataset.get('ERLC', {}).get('remote_commands'):
            remote_commands = True
            remote_command_channel = dataset["ERLC"]["remote_commands"]["webhook_channel"] if dataset["ERLC"]["remote_commands"].get("webhook_channel", None) else None

        if "game_security" in dataset.keys():
            if "enabled" in dataset["game_security"].keys():
                if (
                    "channel" in dataset["game_security"].keys()
                    and "webhook_channel" in dataset["game_security"].keys()
                ):
                    if dataset["game_security"]["enabled"] is True:
                        aa_detection = True
                        webhook_channel = dataset["game_security"][
                            "webhook_channel"
                        ]
                        webhook_channel = discord.utils.get(
                            message.guild.channels, id=webhook_channel
                        )
                        aa_detection_channel = dataset["game_security"]["channel"]
                        aa_detection_channel = discord.utils.get(
                            message.guild.channels, id=aa_detection_channel
                        )


                        if webhook_channel != None:
                            if message.channel.id == webhook_channel.id:
                                for embed in message.embeds:
                                    if embed.description not in ["", None] and embed.title not in [
                                        "",
                                        None,
                                    ]:
                                        if (
                                            "kicked" in embed.description
                                            or "banned" in embed.description
                                        ):
                                            # # print("used kick/ban command")
                                            if (
                                                "Players Kicked" in embed.title
                                                or "Players Banned" in embed.title
                                            ):
                                                # # print("command usage")
                                                raw_content = embed.description

                                                if "kicked" in raw_content:
                                                    user, command = raw_content.split(" kicked `")
                                                else:
                                                    user, command = raw_content.split(" banned `")

                                                command = command.replace("`", "")
                                                code = embed.footer.text.split("Server: ")[1]
                                                if command.count(",") + 1 >= 5:
                                                    people_affected = command.count(',') + 1
                                                    roblox_user = user.split(':')[0].replace('[', '')
                                                    # print(roblox_user)

                                                    roblox_client = roblox.Client()
                                                    roblox_player = await roblox_client.get_user_by_username(roblox_user)
                                                    if not roblox_player:
                                                        return
                                                    thumbnails = await roblox_client.thumbnails.get_user_avatar_thumbnails([roblox_player], size=(420, 420))
                                                    thumbnail = thumbnails[0].image_url

                                                    embed = discord.Embed(
                                                        title="<:security:1169804198741823538> Abuse Detected",
                                                        color=BLANK_COLOR
                                                    ).add_field(
                                                        name="Staff Information",
                                                        value=(
                                                            f"> **Username:** {roblox_player.name}\n"
                                                            f"> **User ID:** {roblox_player.id}\n"
                                                            f"> **Profile Link:** [Click here](https://roblox.com/users/{roblox_player.id}/profile)\n"
                                                            f"> **Account Created:** <t:{int(roblox_player.created.timestamp())}>"
                                                        ),
                                                        inline=False
                                                    ).add_field(
                                                        name="Abuse Information",
                                                        value=(
                                                            f"> **Type:** {'Mass-Kick' if 'kicked' in raw_content else 'Mass-Ban'}\n"
                                                            f"> **Individuals Affected [{command.count(',')+1}]:** {command}\n"
                                                            f"> **At:** <t:{int(message.created_at.timestamp())}>"
                                                        ),
                                                        inline=False
                                                    ).set_thumbnail(
                                                        url=thumbnail
                                                    )
                                                    view = GameSecurityActions(bot)


                                                    pings = []
                                                    pings = [(message.guild.get_role(role_id)).mention if message.guild.get_role(role_id) else None for role_id in dataset.get('game_security', {}).get('role', [])]
                                                    pings = list(filter(lambda x: x is not None, pings))

                                                    await aa_detection_channel.send(
                                                        ",".join(pings) if pings != [] else "",
                                                        embed=embed,
                                                        allowed_mentions=discord.AllowedMentions(
                                                            everyone=True,
                                                            users=True,
                                                            roles=True,
                                                            replied_user=True,
                                                        ),
                                                        view=view
                                                    )
    
    
        if remote_commands and remote_command_channel is not None and message.channel.id in [remote_command_channel]:
            for embed in message.embeds:
                if embed.description in ["", None] and embed.title in ["", None]:
                    break

                if not ":log" in embed.description:
                    break     
                            
                if 'Command Usage' not in embed.title:
                    break
                                
                raw_content = embed.description
                user, command = raw_content.split('used the command: ')

                profile_link = user.split('(')[1].split(')')[0]
                user = user.split('(')[0].replace('[', '').replace(']', '')
                person = command.split(' ')[1]

                combined = ""
                for word in command.split(' ')[1:]:
                    if not bot.get_command(combined.strip()):
                        combined += word + " "
                    else:
                        item = bot.get_command(combined.strip())
                        if isinstance(item, commands.HybridCommand) and not isinstance(item, commands.HybridGroup):
                            break
                        else:
                            combined += word + " "

                invoked_command = ' '.join(combined.replace('`', '').split(' ')[:-1])
                args = [i.replace('"', '') for i in command.split(' ')][[i.replace('"', '') for i in command.split(' ')].index(invoked_command.split(' ')[-1]) + 1:]

                _cmd = command

                discord_user = 0
                async for document in bot.oauth2_users.db.find(
                        {"roblox_id": int(profile_link.split('/')[4])}):
                    discord_user = document['discord_id']

                print(f'Discord User: {discord_user}')
                if discord_user == 0:
                    await message.add_reaction('❌')
                    return await message.add_reaction('6️⃣')

                user = discord.utils.get(message.guild.members, id=discord_user)
                if not user:
                    user = await message.guild.fetch_member(discord_user)
                    if not user:
                        await message.add_reaction('❌')
                        return await message.add_reaction('7️⃣')

                print(invoked_command)
                command = bot.get_command(invoked_command.lower().strip())
                if not command:
                    await message.add_reaction('❌')
                    return await message.add_reaction('8️⃣')

                

                new_message = copy.copy(message)
                new_message.channel = await user.create_dm()
                new_message.author = user
                new_message.content =  ((await get_prefix(bot, message))[-1]) + _cmd.split(':log ')[1].split('`')[0]
                print(new_message)
                await bot.process_commands(new_message)

        if antiping_roles is None:
            return

        if (
            dataset["antiping"]["enabled"] is False
            or dataset["antiping"]["role"] is None
        ):
            return

        if bypass_roles is not None:
            for role in bypass_roles:
                if role in message.author.roles:
                    return

        for mention in message.mentions:
            isStaffPermitted = False

            if mention.bot:
                return

            if dataset["antiping"].get("use_hierarchy") in [True, None]:
                for role in antiping_roles:
                    if role != None:
                        if (
                            message.author.top_role > role
                            or message.author.top_role == role
                        ):
                            return

            if message.author == message.guild.owner:
                return

            if not isStaffPermitted:
                for role in antiping_roles:
                    # # print(antiping_roles)
                    # # print(role)
                    if dataset["antiping"].get("use_hierarchy") in [True, None]:
                        if role is not None:
                            if mention.top_role > role or mention.top_role == role:
                                embed = discord.Embed(
                                    title=f"Do not ping {role.name} or above!",
                                    color=BLANK_COLOR,
                                    description=f"Do not ping {role.name} or above!\nIt is a violation of the rules, and you will be punished if you continue.",
                                )
                                try:
                                    msg = await message.channel.fetch_message(
                                        message.reference.message_id
                                    )
                                    if msg.author == mention:
                                        embed.set_image(
                                            url="https://i.imgur.com/pXesTnm.gif"
                                        )
                                except AttributeError:
                                    pass

                                embed.set_footer(
                                    text=f'Thanks, ERM',
                                    icon_url=get_guild_icon(bot, message.guild),
                                )

                                ctx = await bot.get_context(message)
                                await ctx.reply(
                                    f"{message.author.mention}", embed=embed, delete_after=15
                                )
                                return
                            return
                        return
                    else:
                        if role is not None:
                            if (
                                role in mention.roles
                                and not role in message.author.roles
                            ):
                                embed = discord.Embed(
                                    title=f"Do not ping {role.name}!",
                                    color=discord.Color.red(),
                                    description=f"Do not ping those with {role.name}!\nIt is a violation of the rules, and you will be punished if you continue.",
                                )
                                try:
                                    msg = await message.channel.fetch_message(
                                        message.reference.message_id
                                    )
                                    if msg.author == mention:
                                        embed.set_image(
                                            url="https://i.imgur.com/pXesTnm.gif"
                                        )
                                except discord.NotFound:
                                    pass

                                embed.set_footer(
                                    text=f'Thanks, {dataset["customisation"]["brand_name"]}',
                                    icon_url=get_guild_icon(bot, message.guild),
                                )

                                ctx = await bot.get_context(message)
                                await ctx.reply(
                                    f"{message.author.mention}", embed=embed
                                )
                                return

                            return

                        return


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
