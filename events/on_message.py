import copy
import datetime
import logging
import string

import aiohttp
import discord
import num2words
from discord.ext import commands
from reactionmenu import Page, ViewButton, ViewMenu, ViewSelect

from erm import generator
from menus import CustomSelectMenu
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
        moderation_sync = False
        sync_channel = None

        if "game_security" in dataset.keys() or "moderation_sync" in dataset.keys():
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
            if "moderation_sync" in dataset.keys():
                if dataset["moderation_sync"].get("enabled"):
                    if "webhook_channel" in dataset["moderation_sync"].keys():
                        sync_channel = dataset["moderation_sync"]["webhook_channel"]
                        sync_channel = discord.utils.get(
                            message.guild.channels, id=sync_channel
                        )

                        kick_ban_sync_channel = dataset["moderation_sync"][
                            "kick_ban_webhook_channel"
                        ]
                        kick_ban_sync_channel = discord.utils.get(
                            message.guild.channels, id=kick_ban_sync_channel
                        )

                        sync_channels = []
                        if sync_channel:
                            sync_channels.append(sync_channel.id)
                        if kick_ban_sync_channel:
                            sync_channels.append(kick_ban_sync_channel.id)

                        moderation_sync = True

        if moderation_sync is True:
            if sync_channels is not None:
                if message.channel.id in sync_channels:
                    for embed in message.embeds:
                        if embed.description not in ["", None] and embed.title not in [
                            "",
                            None,
                        ]:
                            if ":logs" in embed.description:
                                if "Command Usage" in embed.title:
                                    raw_content = embed.description
                                    user, command = raw_content.split(
                                        'used the command: "'
                                    )

                                    profile_link = user.split("(")[1].split(")")[0]
                                    user = (
                                        user.split("(")[0]
                                        .replace("[", "")
                                        .replace("]", "")
                                    )
                                    person = command.split(" ")[1]

                                    # and any([(' ' + cmd.qualified_name.lower() + ' ') in command[0:len(cmd.qualified_name.split(' ')) + 1] for cmd in bot.commands])
                                    if " for " not in command:
                                        combined = ""
                                        for word in command.split(" ")[1:]:
                                            if not bot.get_command(combined.strip()):
                                                combined += word + " "
                                                print(f"not found : {combined.strip()}")
                                            else:
                                                print(combined)
                                                item = bot.get_command(combined.strip())
                                                if isinstance(
                                                    item, commands.HybridCommand
                                                ) and not isinstance(
                                                    item, commands.HybridGroup
                                                ):
                                                    print("about to break 2405")
                                                    break
                                                else:
                                                    combined += word + " "
                                                    print(
                                                        f"not found : {combined.strip()}"
                                                    )
                                        invoked_command = " ".join(
                                            combined.replace('"', "").split(" ")[:-1]
                                        )
                                        print(invoked_command)
                                        print(command.split(" "))
                                        args = [
                                            i.replace('"', "")
                                            for i in command.split(" ")
                                        ][
                                            [
                                                i.replace('"', "")
                                                for i in command.split(" ")
                                            ].index(invoked_command.split(" ")[-1])
                                            + 1 :
                                        ]
                                        print(args)

                                        _cmd = command

                                        discord_user = 0
                                        async for document in bot.synced_users.db.find(
                                            {"roblox": str(profile_link.split("/")[4])}
                                        ):
                                            discord_user = document["_id"]

                                        print(f"Discord User: {discord_user}")
                                        if discord_user == 0:
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("6️⃣")

                                        user = discord.utils.get(
                                            message.guild.members, id=discord_user
                                        )
                                        if not user:
                                            user = await message.guild.fetch_member(
                                                discord_user
                                            )
                                            if not user:
                                                await message.add_reaction("❌")
                                                return await message.add_reaction("7️⃣")

                                        print(invoked_command)
                                        command = bot.get_command(
                                            invoked_command.lower().strip()
                                        )
                                        if not command:
                                            if not any(
                                                [
                                                    i in invoked_command.lower().strip()
                                                    for i in ["duty on", "duty off"]
                                                ]
                                            ):
                                                await message.add_reaction("❌")
                                                return await message.add_reaction("8️⃣")

                                        new_message = copy.copy(message)
                                        new_message.channel = await user.create_dm()
                                        new_message.author = user
                                        new_message.content = (
                                            (await get_prefix(bot, message))[-1]
                                        ) + _cmd.split(":logs ")[1].split('"')[0]

                                        new_ctx = await bot.get_context(new_message)
                                        print(invoked_command)
                                        if "duty on" in invoked_command.lower().strip():
                                            ctx = new_ctx
                                            predetermined_shift_type = None
                                            settings = await bot.settings.find_by_id(
                                                ctx.guild.id
                                            )
                                            shift_types = settings.get("shift_types")
                                            shift_types = (
                                                shift_types.get("types")
                                                if shift_types.get("types")
                                                not in [None, []]
                                                else []
                                            )
                                            if args:
                                                combined = ""
                                                for arg in args:
                                                    if combined.strip() not in [
                                                        shift_type["name"]
                                                        .lower()
                                                        .strip()
                                                        if isinstance(shift_type, dict)
                                                        else shift_type.lower().strip()
                                                        for shift_type in shift_types
                                                    ]:
                                                        combined += arg + " "
                                                    else:
                                                        break
                                                combined = combined.strip()
                                                predetermined_shift_type = shift_types[
                                                    [
                                                        shift_type["name"]
                                                        .lower()
                                                        .strip()
                                                        if isinstance(shift_type, dict)
                                                        else shift_type.lower().strip()
                                                        for shift_type in shift_types
                                                    ].index(combined.lower().strip())
                                                ]

                                            configItem = await bot.settings.find_by_id(
                                                ctx.guild.id
                                            )
                                            if configItem is None:
                                                return await invis_embed(
                                                    ctx,
                                                    "The server has not been set up yet. Please run `/setup` to set up the server.",
                                                )

                                            try:
                                                shift_channel = discord.utils.get(
                                                    ctx.guild.channels,
                                                    id=configItem["shift_management"][
                                                        "channel"
                                                    ],
                                                )

                                                if not shift_channel:
                                                    raise Exception()
                                            except:
                                                return await invis_embed(
                                                    ctx,
                                                    f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.',
                                                )

                                            if not configItem["shift_management"][
                                                "enabled"
                                            ]:
                                                return await invis_embed(
                                                    ctx,
                                                    "Shift management is not enabled on this server.",
                                                )

                                            shift = None
                                            if await bot.shifts.find_by_id(
                                                ctx.author.id
                                            ):
                                                if (
                                                    "data"
                                                    in (
                                                        await bot.shifts.find_by_id(
                                                            ctx.author.id
                                                        )
                                                    ).keys()
                                                ):
                                                    var = (
                                                        await bot.shifts.find_by_id(
                                                            ctx.author.id
                                                        )
                                                    )["data"]
                                                    print(var)

                                                    for item in var:
                                                        if (
                                                            item["guild"]
                                                            == ctx.guild.id
                                                        ):
                                                            parent_item = await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                            shift = item
                                                else:
                                                    if (
                                                        "guild"
                                                        in (
                                                            await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                        ).keys()
                                                    ):
                                                        if (
                                                            await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                        )["guild"] == ctx.guild.id:
                                                            shift = await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                            if shift:
                                                if "on_break" in shift.keys():
                                                    if shift["on_break"]:
                                                        status = "break"
                                                    else:
                                                        status = "on"
                                                else:
                                                    status = "on"
                                            else:
                                                status = "off"

                                            if shift:
                                                if "type" in shift.keys():
                                                    if shift["type"]:
                                                        raw_shift_type: int = shift[
                                                            "type"
                                                        ]
                                                        settings = await bot.settings.find_by_id(
                                                            ctx.guild.id
                                                        )
                                                        shift_types = settings.get(
                                                            "shift_types"
                                                        )
                                                        shift_types = (
                                                            shift_types.get("types")
                                                            if shift_types.get("types")
                                                            not in [None, []]
                                                            else []
                                                        )
                                                        if shift_types:
                                                            sh_typelist = [
                                                                item
                                                                for item in shift_types
                                                                if item["id"]
                                                                == raw_shift_type
                                                            ]
                                                            if len(sh_typelist) > 0:
                                                                shift_type = (
                                                                    sh_typelist[0]
                                                                )
                                                            else:
                                                                shift_type = {
                                                                    "name": "Unknown",
                                                                    "id": 0,
                                                                    "role": settings[
                                                                        "shift_management"
                                                                    ].get("role"),
                                                                }
                                                        else:
                                                            shift_type = {
                                                                "name": "Default",
                                                                "id": 0,
                                                                "role": settings[
                                                                    "shift_management"
                                                                ].get("role"),
                                                            }
                                                    else:
                                                        shift_type = None
                                                else:
                                                    shift_type = None

                                                if shift_type:
                                                    if shift_type.get("channel"):
                                                        temp_shift_channel = (
                                                            discord.utils.get(
                                                                ctx.guild.channels,
                                                                id=shift_type.get(
                                                                    "channel"
                                                                ),
                                                            )
                                                        )
                                                        if temp_shift_channel:
                                                            shift_channel = (
                                                                temp_shift_channel
                                                            )

                                            if status == "on":
                                                return await invis_embed(
                                                    ctx,
                                                    "You are already on-duty. You can go off-duty by selecting **Off-Duty**.",
                                                )
                                            elif status == "break":
                                                for item in shift["breaks"]:
                                                    if item["ended"] is None:
                                                        item[
                                                            "ended"
                                                        ] = ctx.message.created_at.replace(
                                                            tzinfo=None
                                                        ).timestamp()
                                                for data in parent_item["data"]:
                                                    if (
                                                        shift["startTimestamp"]
                                                        == data["startTimestamp"]
                                                        and shift["guild"]
                                                        == data["guild"]
                                                    ):
                                                        data["breaks"] = shift["breaks"]
                                                        data["on_break"] = False
                                                        break
                                                await bot.shifts.update_by_id(
                                                    parent_item
                                                )

                                                if shift_type:
                                                    if shift_type.get("role"):
                                                        role = [
                                                            discord.utils.get(
                                                                ctx.guild.roles,
                                                                id=shift_type.get(
                                                                    "role"
                                                                ),
                                                            )
                                                        ]
                                                else:
                                                    if shift_type:
                                                        if shift_type.get("role"):
                                                            role = [
                                                                discord.utils.get(
                                                                    ctx.guild.roles,
                                                                    id=role,
                                                                )
                                                                for role in shift_type.get(
                                                                    "role"
                                                                )
                                                            ]
                                                    else:
                                                        if configItem[
                                                            "shift_management"
                                                        ]["role"]:
                                                            if not isinstance(
                                                                configItem[
                                                                    "shift_management"
                                                                ]["role"],
                                                                list,
                                                            ):
                                                                role = [
                                                                    discord.utils.get(
                                                                        ctx.guild.roles,
                                                                        id=configItem[
                                                                            "shift_management"
                                                                        ]["role"],
                                                                    )
                                                                ]
                                                            else:
                                                                role = [
                                                                    discord.utils.get(
                                                                        ctx.guild.roles,
                                                                        id=role,
                                                                    )
                                                                    for role in configItem[
                                                                        "shift_management"
                                                                    ][
                                                                        "role"
                                                                    ]
                                                                ]
                                                if role:
                                                    for rl in role:
                                                        if (
                                                            rl not in ctx.author.roles
                                                            and rl is not None
                                                        ):
                                                            try:
                                                                await ctx.author.add_roles(
                                                                    rl
                                                                )
                                                            except:
                                                                await invis_embed(
                                                                    ctx,
                                                                    f"Could not add {rl} to {ctx.author.mention}",
                                                                )

                                                success = discord.Embed(
                                                    title="<:CheckIcon:1035018951043842088> Break Ended",
                                                    description="<:ArrowRight:1035003246445596774> You are no longer on break.",
                                                    color=0x71C15F,
                                                )
                                                await ctx.send(embed=success, view=None)
                                            else:
                                                settings = (
                                                    await bot.settings.find_by_id(
                                                        ctx.guild.id
                                                    )
                                                )
                                                shift_type = None
                                                if settings.get("shift_types"):
                                                    if predetermined_shift_type:
                                                        shift_type = [
                                                            item
                                                            for item in settings[
                                                                "shift_types"
                                                            ]["types"]
                                                            if item["name"]
                                                            .lower()
                                                            .strip()
                                                            == predetermined_shift_type[
                                                                "name"
                                                            ]
                                                            .lower()
                                                            .strip()
                                                        ]
                                                        if len(shift_type) == 1:
                                                            shift_type = shift_type[0]
                                                    elif (
                                                        len(
                                                            settings["shift_types"].get(
                                                                "types"
                                                            )
                                                            or []
                                                        )
                                                        > 1
                                                        and settings["shift_types"].get(
                                                            "enabled"
                                                        )
                                                        is True
                                                    ):
                                                        embed = discord.Embed(
                                                            title="<:Clock:1035308064305332224> Shift Types",
                                                            description=f"<:ArrowRight:1035003246445596774> You have {num2words.num2words(len(settings['shift_types']['types']))} shift types, {', '.join([f'`{i}`' for i in [item['name'] for item in settings['shift_types']['types']]])}. Select one of these options.",
                                                            color=0x2E3136,
                                                        )
                                                        view = CustomSelectMenu(
                                                            ctx.author.id,
                                                            [
                                                                discord.SelectOption(
                                                                    label=item["name"],
                                                                    value=item["id"],
                                                                    description=item[
                                                                        "name"
                                                                    ],
                                                                    emoji="<:Clock:1035308064305332224>",
                                                                )
                                                                for item in settings[
                                                                    "shift_types"
                                                                ]["types"]
                                                            ],
                                                        )
                                                        msg = await ctx.send(
                                                            embed=embed, view=view
                                                        )
                                                        timeout = await view.wait()
                                                        if timeout:
                                                            return
                                                        if view.value:
                                                            shift_type = [
                                                                item
                                                                for item in settings[
                                                                    "shift_types"
                                                                ]["types"]
                                                                if item["id"]
                                                                == int(view.value)
                                                            ]
                                                            if len(shift_type) == 1:
                                                                shift_type = shift_type[
                                                                    0
                                                                ]
                                                            else:
                                                                return await invis_embed(
                                                                    ctx,
                                                                    "Something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).",
                                                                )
                                                        else:
                                                            return
                                                    else:
                                                        if (
                                                            settings["shift_types"].get(
                                                                "enabled"
                                                            )
                                                            is True
                                                            and len(
                                                                settings[
                                                                    "shift_types"
                                                                ].get("types")
                                                                or []
                                                            )
                                                            == 1
                                                        ):
                                                            shift_type = settings[
                                                                "shift_types"
                                                            ]["types"][0]
                                                        else:
                                                            shift_type = None

                                                nickname_prefix = None
                                                changed_nick = False
                                                if shift_type:
                                                    if shift_type.get("nickname"):
                                                        nickname_prefix = (
                                                            shift_type.get("nickname")
                                                        )
                                                else:
                                                    if configItem[
                                                        "shift_management"
                                                    ].get("nickname"):
                                                        nickname_prefix = configItem[
                                                            "shift_management"
                                                        ].get("nickname")

                                                if nickname_prefix:
                                                    current_name = (
                                                        ctx.author.nick
                                                        if ctx.author.nick
                                                        else ctx.author.name
                                                    )
                                                    new_name = "{}{}".format(
                                                        nickname_prefix, current_name
                                                    )

                                                    try:
                                                        await ctx.author.edit(
                                                            nick=new_name
                                                        )
                                                        changed_nick = True
                                                    except Exception as e:
                                                        print(e)
                                                        pass

                                                try:
                                                    if shift_type:
                                                        if changed_nick:
                                                            await bot.shifts.insert(
                                                                {
                                                                    "_id": ctx.author.id,
                                                                    "name": ctx.author.name,
                                                                    "data": [
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                            "type": shift_type[
                                                                                "id"
                                                                            ],
                                                                            "nickname": {
                                                                                "old": current_name,
                                                                                "new": new_name,
                                                                            },
                                                                        }
                                                                    ],
                                                                }
                                                            )
                                                        else:
                                                            await bot.shifts.insert(
                                                                {
                                                                    "_id": ctx.author.id,
                                                                    "name": ctx.author.name,
                                                                    "data": [
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                            "type": shift_type[
                                                                                "id"
                                                                            ],
                                                                        }
                                                                    ],
                                                                }
                                                            )
                                                    else:
                                                        if changed_nick:
                                                            await bot.shifts.insert(
                                                                {
                                                                    "_id": ctx.author.id,
                                                                    "name": ctx.author.name,
                                                                    "data": [
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                            "nickname": {
                                                                                "old": current_name,
                                                                                "new": new_name,
                                                                            },
                                                                        }
                                                                    ],
                                                                }
                                                            )
                                                        else:
                                                            await bot.shifts.insert(
                                                                {
                                                                    "_id": ctx.author.id,
                                                                    "name": ctx.author.name,
                                                                    "data": [
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                        }
                                                                    ],
                                                                }
                                                            )
                                                except:
                                                    if await bot.shifts.find_by_id(
                                                        ctx.author.id
                                                    ):
                                                        shift = (
                                                            await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                        )
                                                        if "data" in shift.keys():
                                                            if shift_type:
                                                                newData = shift["data"]
                                                                if changed_nick:
                                                                    newData.append(
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                            "type": shift_type[
                                                                                "id"
                                                                            ],
                                                                            "nickname": {
                                                                                "new": new_name,
                                                                                "old": current_name,
                                                                            },
                                                                        }
                                                                    )
                                                                else:
                                                                    newData.append(
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                            "type": shift_type[
                                                                                "id"
                                                                            ],
                                                                        }
                                                                    )
                                                                await bot.shifts.update_by_id(
                                                                    {
                                                                        "_id": ctx.author.id,
                                                                        "name": ctx.author.name,
                                                                        "data": newData,
                                                                    }
                                                                )
                                                            else:
                                                                newData = shift["data"]
                                                                if changed_nick:
                                                                    newData.append(
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                            "nickname": {
                                                                                "old": current_name,
                                                                                "new": new_name,
                                                                            },
                                                                        }
                                                                    )
                                                                else:
                                                                    newData.append(
                                                                        {
                                                                            "guild": ctx.guild.id,
                                                                            "startTimestamp": ctx.message.created_at.replace(
                                                                                tzinfo=None
                                                                            ).timestamp(),
                                                                        }
                                                                    )
                                                                await bot.shifts.update_by_id(
                                                                    {
                                                                        "_id": ctx.author.id,
                                                                        "name": ctx.author.name,
                                                                        "data": newData,
                                                                    }
                                                                )
                                                        elif "data" not in shift.keys():
                                                            if shift_type:
                                                                if changed_nick:
                                                                    await bot.shifts.update_by_id(
                                                                        {
                                                                            "_id": ctx.author.id,
                                                                            "name": ctx.author.name,
                                                                            "data": [
                                                                                {
                                                                                    "guild": ctx.guild.id,
                                                                                    "startTimestamp": ctx.message.created_at.replace(
                                                                                        tzinfo=None
                                                                                    ).timestamp(),
                                                                                    "type": shift_type[
                                                                                        "id"
                                                                                    ],
                                                                                    "nickname": {
                                                                                        "old": current_name,
                                                                                        "new": new_name,
                                                                                    },
                                                                                },
                                                                                {
                                                                                    "guild": shift[
                                                                                        "guild"
                                                                                    ],
                                                                                    "startTimestamp": shift[
                                                                                        "startTimestamp"
                                                                                    ],
                                                                                },
                                                                            ],
                                                                        }
                                                                    )
                                                                else:
                                                                    await bot.shifts.update_by_id(
                                                                        {
                                                                            "_id": ctx.author.id,
                                                                            "name": ctx.author.name,
                                                                            "data": [
                                                                                {
                                                                                    "guild": ctx.guild.id,
                                                                                    "startTimestamp": ctx.message.created_at.replace(
                                                                                        tzinfo=None
                                                                                    ).timestamp(),
                                                                                    "type": shift_type[
                                                                                        "id"
                                                                                    ],
                                                                                },
                                                                                {
                                                                                    "guild": shift[
                                                                                        "guild"
                                                                                    ],
                                                                                    "startTimestamp": shift[
                                                                                        "startTimestamp"
                                                                                    ],
                                                                                },
                                                                            ],
                                                                        }
                                                                    )
                                                            else:
                                                                if changed_nick:
                                                                    await bot.shifts.update_by_id(
                                                                        {
                                                                            "_id": ctx.author.id,
                                                                            "name": ctx.author.name,
                                                                            "data": [
                                                                                {
                                                                                    "guild": ctx.guild.id,
                                                                                    "startTimestamp": ctx.message.created_at.replace(
                                                                                        tzinfo=None
                                                                                    ).timestamp(),
                                                                                    "nickname": {
                                                                                        "old": current_name,
                                                                                        "new": new_name,
                                                                                    },
                                                                                },
                                                                                {
                                                                                    "guild": shift[
                                                                                        "guild"
                                                                                    ],
                                                                                    "startTimestamp": shift[
                                                                                        "startTimestamp"
                                                                                    ],
                                                                                },
                                                                            ],
                                                                        }
                                                                    )
                                                                else:
                                                                    await bot.shifts.update_by_id(
                                                                        {
                                                                            "_id": ctx.author.id,
                                                                            "name": ctx.author.name,
                                                                            "data": [
                                                                                {
                                                                                    "guild": ctx.guild.id,
                                                                                    "startTimestamp": ctx.message.created_at.replace(
                                                                                        tzinfo=None
                                                                                    ).timestamp(),
                                                                                },
                                                                                {
                                                                                    "guild": shift[
                                                                                        "guild"
                                                                                    ],
                                                                                    "startTimestamp": shift[
                                                                                        "startTimestamp"
                                                                                    ],
                                                                                },
                                                                            ],
                                                                        }
                                                                    )
                                                successEmbed = discord.Embed(
                                                    title="<:CheckIcon:1035018951043842088> Success",
                                                    description="<:ArrowRight:1035003246445596774> Your shift is now active.",
                                                    color=0x71C15F,
                                                )

                                                role = None

                                                if shift_type:
                                                    if shift_type.get("role"):
                                                        role = [
                                                            discord.utils.get(
                                                                ctx.guild.roles, id=role
                                                            )
                                                            for role in shift_type.get(
                                                                "role"
                                                            )
                                                        ]
                                                else:
                                                    if configItem["shift_management"][
                                                        "role"
                                                    ]:
                                                        if not isinstance(
                                                            configItem[
                                                                "shift_management"
                                                            ]["role"],
                                                            list,
                                                        ):
                                                            role = [
                                                                discord.utils.get(
                                                                    ctx.guild.roles,
                                                                    id=configItem[
                                                                        "shift_management"
                                                                    ]["role"],
                                                                )
                                                            ]
                                                        else:
                                                            role = [
                                                                discord.utils.get(
                                                                    ctx.guild.roles,
                                                                    id=role,
                                                                )
                                                                for role in configItem[
                                                                    "shift_management"
                                                                ]["role"]
                                                            ]

                                                if role:
                                                    for rl in role:
                                                        if (
                                                            not rl in ctx.author.roles
                                                            and rl is not None
                                                        ):
                                                            try:
                                                                await ctx.author.add_roles(
                                                                    rl
                                                                )
                                                            except:
                                                                await invis_embed(
                                                                    ctx,
                                                                    f"Could not add {rl} to {ctx.author.mention}",
                                                                )

                                                embed = discord.Embed(
                                                    title=ctx.author.name,
                                                    color=0x2E3136,
                                                )
                                                try:
                                                    embed.set_thumbnail(
                                                        url=ctx.author.display_avatar.url
                                                    )
                                                    embed.set_footer(
                                                        text="Staff Logging Module"
                                                    )
                                                except:
                                                    pass

                                                if shift_type:
                                                    embed.add_field(
                                                        name="<:MalletWhite:1035258530422341672> Type",
                                                        value=f"<:ArrowRight:1035003246445596774> Clocking in. **({shift_type['name']})**",
                                                        inline=False,
                                                    )
                                                else:
                                                    embed.add_field(
                                                        name="<:MalletWhite:1035258530422341672> Type",
                                                        value="<:ArrowRight:1035003246445596774> Clocking in.",
                                                        inline=False,
                                                    )
                                                embed.add_field(
                                                    name="<:Clock:1035308064305332224> Current Time",
                                                    value=f"<:ArrowRight:1035003246445596774> <t:{int(ctx.message.created_at.timestamp())}>",
                                                    inline=False,
                                                )

                                                await shift_channel.send(embed=embed)
                                                await msg.edit(
                                                    embed=successEmbed, view=None
                                                )
                                            await message.add_reaction("📝")
                                            return
                                        elif (
                                            "duty off"
                                            in invoked_command.lower().strip()
                                        ):
                                            ctx = new_ctx
                                            configItem = await bot.settings.find_by_id(
                                                ctx.guild.id
                                            )
                                            if configItem is None:
                                                return await invis_embed(
                                                    ctx,
                                                    "The server has not been set up yet. Please run `/setup` to set up the server.",
                                                )

                                            try:
                                                shift_channel = discord.utils.get(
                                                    ctx.guild.channels,
                                                    id=configItem["shift_management"][
                                                        "channel"
                                                    ],
                                                )
                                            except:
                                                return await invis_embed(
                                                    ctx,
                                                    f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.',
                                                )

                                            if not configItem["shift_management"][
                                                "enabled"
                                            ]:
                                                return await invis_embed(
                                                    ctx,
                                                    "Shift management is not enabled on this server.",
                                                )

                                            shift = None
                                            if await bot.shifts.find_by_id(
                                                ctx.author.id
                                            ):
                                                if (
                                                    "data"
                                                    in (
                                                        await bot.shifts.find_by_id(
                                                            ctx.author.id
                                                        )
                                                    ).keys()
                                                ):
                                                    var = (
                                                        await bot.shifts.find_by_id(
                                                            ctx.author.id
                                                        )
                                                    )["data"]
                                                    print(var)

                                                    for item in var:
                                                        if (
                                                            item["guild"]
                                                            == ctx.guild.id
                                                        ):
                                                            parent_item = await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                            shift = item
                                                else:
                                                    if (
                                                        "guild"
                                                        in (
                                                            await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                        ).keys()
                                                    ):
                                                        if (
                                                            await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                                        )["guild"] == ctx.guild.id:
                                                            shift = await bot.shifts.find_by_id(
                                                                ctx.author.id
                                                            )
                                            if shift:
                                                if "on_break" in shift.keys():
                                                    if shift["on_break"]:
                                                        status = "break"
                                                    else:
                                                        status = "on"
                                                else:
                                                    status = "on"
                                            else:
                                                status = "off"

                                            if shift:
                                                if "type" in shift.keys():
                                                    if shift["type"]:
                                                        raw_shift_type: int = shift[
                                                            "type"
                                                        ]
                                                        settings = await bot.settings.find_by_id(
                                                            ctx.guild.id
                                                        )
                                                        shift_types = settings.get(
                                                            "shift_types"
                                                        )
                                                        shift_types = (
                                                            shift_types.get("types")
                                                            if shift_types.get("types")
                                                            not in [None, []]
                                                            else []
                                                        )
                                                        if shift_types:
                                                            sh_typelist = [
                                                                item
                                                                for item in shift_types
                                                                if item["id"]
                                                                == raw_shift_type
                                                            ]
                                                            if len(sh_typelist) > 0:
                                                                shift_type = (
                                                                    sh_typelist[0]
                                                                )
                                                            else:
                                                                shift_type = {
                                                                    "name": "Unknown",
                                                                    "id": 0,
                                                                    "role": settings[
                                                                        "shift_management"
                                                                    ].get("role"),
                                                                }
                                                        else:
                                                            shift_type = {
                                                                "name": "Default",
                                                                "id": 0,
                                                                "role": settings[
                                                                    "shift_management"
                                                                ].get("role"),
                                                            }
                                                    else:
                                                        shift_type = None
                                                else:
                                                    shift_type = None

                                                if shift_type:
                                                    if shift_type.get("channel"):
                                                        temp_shift_channel = (
                                                            discord.utils.get(
                                                                ctx.guild.channels,
                                                                id=shift_type.get(
                                                                    "channel"
                                                                ),
                                                            )
                                                        )
                                                        if temp_shift_channel:
                                                            shift_channel = (
                                                                temp_shift_channel
                                                            )

                                            break_seconds = 0
                                            if shift:
                                                if "breaks" in shift.keys():
                                                    for item in shift["breaks"]:
                                                        if item["ended"] == None:
                                                            item[
                                                                "ended"
                                                            ] = ctx.message.created_at.replace(
                                                                tzinfo=None
                                                            ).timestamp()
                                                        startTimestamp = item["started"]
                                                        endTimestamp = item["ended"]
                                                        break_seconds += int(
                                                            endTimestamp
                                                            - startTimestamp
                                                        )
                                            else:
                                                return await invis_embed(
                                                    ctx,
                                                    "You are not on-duty. You can go on-duty by selecting **On-Duty**.",
                                                )
                                            if status == "off":
                                                return await invis_embed(
                                                    ctx,
                                                    "You are already off-duty. You can go on-duty by selecting **On-Duty**.",
                                                )

                                            embed = discord.Embed(
                                                title=ctx.author.name, color=0x2E3136
                                            )

                                            embed.set_thumbnail(
                                                url=ctx.author.display_avatar.url
                                            )
                                            embed.set_footer(
                                                text="Staff Logging Module"
                                            )

                                            if shift.get("type"):
                                                settings = (
                                                    await bot.settings.find_by_id(
                                                        ctx.author.id
                                                    )
                                                )
                                                shift_type = None
                                                if settings:
                                                    if "shift_types" in settings.keys():
                                                        for item in (
                                                            settings["shift_types"].get(
                                                                "types"
                                                            )
                                                            or []
                                                        ):
                                                            if (
                                                                item["id"]
                                                                == shift["type"]
                                                            ):
                                                                shift_type = item

                                            if shift_type:
                                                embed.add_field(
                                                    name="<:MalletWhite:1035258530422341672> Type",
                                                    value=f"<:ArrowRight:1035003246445596774> Clocking out. **({shift_type['name']})**",
                                                    inline=False,
                                                )
                                            else:
                                                embed.add_field(
                                                    name="<:MalletWhite:1035258530422341672> Type",
                                                    value=f"<:ArrowRight:1035003246445596774> Clocking out.",
                                                    inline=False,
                                                )

                                            time_delta = ctx.message.created_at.replace(
                                                tzinfo=None
                                            ) - datetime.datetime.fromtimestamp(
                                                shift["startTimestamp"]
                                            ).replace(
                                                tzinfo=None
                                            )

                                            time_delta = (
                                                time_delta
                                                - datetime.timedelta(
                                                    seconds=break_seconds
                                                )
                                            )

                                            added_seconds = 0
                                            removed_seconds = 0
                                            if "added_time" in shift.keys():
                                                for added in shift["added_time"]:
                                                    added_seconds += added

                                            if "removed_time" in shift.keys():
                                                for removed in shift["removed_time"]:
                                                    removed_seconds += removed

                                            try:
                                                time_delta = (
                                                    time_delta
                                                    + datetime.timedelta(
                                                        seconds=added_seconds
                                                    )
                                                )
                                                time_delta = (
                                                    time_delta
                                                    - datetime.timedelta(
                                                        seconds=removed_seconds
                                                    )
                                                )
                                            except OverflowError:
                                                await invis_embed(
                                                    ctx,
                                                    f"{ctx.author.mention}'s added or removed time has been voided due to it being an unfeasibly massive numeric value. If you find a vulnerability in ERM, please report it via our Support Server.",
                                                )

                                            if break_seconds > 0:
                                                embed.add_field(
                                                    name="<:Clock:1035308064305332224> Elapsed Time",
                                                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                                                    inline=False,
                                                )
                                            else:
                                                embed.add_field(
                                                    name="<:Clock:1035308064305332224> Elapsed Time",
                                                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                                                    inline=False,
                                                )

                                            successEmbed = discord.Embed(
                                                title="<:CheckIcon:1035018951043842088> Shift Ended",
                                                description="<:ArrowRight:1035003246445596774> Your shift has now ended.",
                                                color=0x71C15F,
                                            )

                                            await ctx.send(
                                                embed=successEmbed, view=None
                                            )

                                            if shift.get("nickname"):
                                                if (
                                                    shift["nickname"]["new"]
                                                    == ctx.author.display_name
                                                ):
                                                    try:
                                                        await ctx.author.edit(
                                                            nick=shift["nickname"][
                                                                "old"
                                                            ]
                                                        )
                                                    except Exception as e:
                                                        print(e)
                                                        pass

                                            await shift_channel.send(embed=embed)

                                            embed = discord.Embed(
                                                title="<:MalletWhite:1035258530422341672> Shift Report",
                                                description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                color=0x2E3136,
                                            )

                                            moderations = len(
                                                shift.get("moderations")
                                                if shift.get("moderations")
                                                else []
                                            )
                                            synced_moderations = len(
                                                [
                                                    moderation
                                                    for moderation in (
                                                        shift.get("moderations")
                                                        if shift.get("moderations")
                                                        else []
                                                    )
                                                    if moderation.get("synced")
                                                ]
                                            )

                                            moderation_list = (
                                                shift.get("moderations")
                                                if shift.get("moderations")
                                                else []
                                            )
                                            synced_moderation_list = [
                                                moderation
                                                for moderation in (
                                                    shift.get("moderations")
                                                    if shift.get("moderations")
                                                    else []
                                                )
                                                if moderation.get("synced")
                                            ]

                                            embed.set_author(
                                                name=f"You have made {moderations} moderations during your shift.",
                                                icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless",
                                            )

                                            embed.add_field(
                                                name="<:Clock:1035308064305332224> Elapsed Time",
                                                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                                                inline=False,
                                            )

                                            embed.add_field(
                                                name="<:Search:1035353785184288788> Total Moderations",
                                                value=f"<:ArrowRightW:1035023450592514048> **Warnings:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'warning'])}\n<:ArrowRightW:1035023450592514048> **Kicks:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'kick'])}\n<:ArrowRightW:1035023450592514048> **Bans:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'ban'])}\n<:ArrowRightW:1035023450592514048> **BOLO:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'bolo'])}\n<:ArrowRightW:1035023450592514048> **Custom:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() not in ['warning', 'kick', 'ban', 'bolo']])}",
                                                inline=False,
                                            )
                                            new_ctx = copy.copy(ctx)
                                            dm_channel = (
                                                await new_ctx.author.create_dm()
                                            )

                                            new_ctx.guild = None
                                            new_ctx.channel = dm_channel

                                            menu = ViewMenu(
                                                new_ctx,
                                                menu_type=ViewMenu.TypeEmbed,
                                                timeout=None,
                                            )
                                            menu.add_page(embed)

                                            moderation_embed = discord.Embed(
                                                title="<:MalletWhite:1035258530422341672> Shift Report",
                                                description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                color=0x2E3136,
                                            )

                                            moderation_embed.set_author(
                                                name=f"You have made {moderations} moderations during your shift.",
                                                icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless",
                                            )

                                            moderation_embeds = []
                                            moderation_embeds.append(moderation_embed)
                                            print("9867")

                                            for moderation in moderation_list:
                                                if (
                                                    len(moderation_embeds[-1].fields)
                                                    >= 10
                                                ):
                                                    moderation_embeds.append(
                                                        discord.Embed(
                                                            title="<:MalletWhite:1035258530422341672> Shift Report",
                                                            description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                            color=0x2E3136,
                                                        )
                                                    )

                                                    moderation_embeds[-1].set_author(
                                                        name=f"You have made {moderations} moderations during your shift.",
                                                        icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless",
                                                    )

                                                moderation_embeds[-1].add_field(
                                                    name=f"<:WarningIcon:1035258528149033090> {moderation['Type'].title()}",
                                                    value=f"<:ArrowRightW:1035023450592514048> **ID:** {moderation['id']}\n<:ArrowRightW:1035023450592514048> **Type:** {moderation['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {moderation['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(moderation['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(moderation['Time'], str) else int(moderation['Time'])}>\n<:ArrowRightW:1035023450592514048> **Synced:** {str(moderation.get('synced')) if moderation.get('synced') else 'False'}",
                                                    inline=False,
                                                )

                                            synced_moderation_embed = discord.Embed(
                                                title="<:MalletWhite:1035258530422341672> Shift Report",
                                                description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                color=0x2E3136,
                                            )

                                            synced_moderation_embed.set_author(
                                                name=f"You have made {synced_moderations} synced moderations during your shift.",
                                                icon_url="https://cdn.discordapp.com/emojis/1071821068551073892.webp?size=128&quality=lossless",
                                            )

                                            synced_moderation_embeds = []
                                            synced_moderation_embeds.append(
                                                moderation_embed
                                            )
                                            print("9895")

                                            for moderation in synced_moderation_list:
                                                if (
                                                    len(
                                                        synced_moderation_embeds[
                                                            -1
                                                        ].fields
                                                    )
                                                    >= 10
                                                ):
                                                    moderation_embeds.append(
                                                        discord.Embed(
                                                            title="<:MalletWhite:1035258530422341672> Shift Report",
                                                            description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                            color=0x2E3136,
                                                        )
                                                    )

                                                    synced_moderation_embeds[
                                                        -1
                                                    ].set_author(
                                                        name=f"You have made {synced_moderations} synced moderations during your shift.",
                                                        icon_url="https://cdn.discordapp.com/emojis/1071821068551073892.webp?size=128&quality=lossless",
                                                    )

                                                synced_moderation_embeds[-1].add_field(
                                                    name=f"<:WarningIcon:1035258528149033090> {moderation['Type'].title()}",
                                                    value=f"<:ArrowRightW:1035023450592514048> **ID:** {moderation['id']}\n<:ArrowRightW:1035023450592514048> **Type:** {moderation['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {moderation['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(moderation['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(moderation['Time'], str) else int(moderation['Time'])}>",
                                                    inline=False,
                                                )

                                            time_embed = discord.Embed(
                                                title="<:MalletWhite:1035258530422341672> Shift Report",
                                                description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                color=0x2E3136,
                                            )

                                            time_embed.set_author(
                                                name=f"You were on-shift for {td_format(time_delta)}.",
                                                icon_url="https://cdn.discordapp.com/emojis/1035308064305332224.webp?size=128&quality=lossless",
                                            )
                                            print("9919")

                                            time_embed.add_field(
                                                name="<:Resume:1035269012445216858> Shift Start",
                                                value=f"<:ArrowRight:1035003246445596774> <t:{int(shift['startTimestamp'])}>",
                                                inline=False,
                                            )

                                            time_embed.add_field(
                                                name="<:ArrowRightW:1035023450592514048> Shift End",
                                                value=f"<:ArrowRight:1035003246445596774> <t:{int(datetime.datetime.now().timestamp())}>",
                                                inline=False,
                                            )

                                            time_embed.add_field(
                                                name="<:SConductTitle:1053359821308567592> Added Time",
                                                value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=added_seconds))}",
                                                inline=False,
                                            )

                                            time_embed.add_field(
                                                name="<:FlagIcon:1035258525955395664> Removed Time",
                                                value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=removed_seconds))}",
                                                inline=False,
                                            )

                                            time_embed.add_field(
                                                name="<:LinkIcon:1044004006109904966> Total Time",
                                                value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                                                inline=False,
                                            )

                                            menu.add_select(
                                                ViewSelect(
                                                    title="Shift Report",
                                                    options={
                                                        discord.SelectOption(
                                                            label="Moderations",
                                                            emoji="<:MalletWhite:1035258530422341672>",
                                                            description="View all of your moderations during this shift",
                                                        ): [
                                                            Page(embed=embed)
                                                            for embed in moderation_embeds
                                                        ],
                                                        discord.SelectOption(
                                                            label="Synced Moderations",
                                                            emoji="<:SyncIcon:1071821068551073892>",
                                                            description="View all of your synced moderations during this shift",
                                                        ): [
                                                            Page(embed=embed)
                                                            for embed in synced_moderation_embeds
                                                        ],
                                                        discord.SelectOption(
                                                            label="Shift Time",
                                                            emoji="<:Clock:1035308064305332224>",
                                                            description="View your shift time",
                                                        ): [Page(embed=time_embed)],
                                                    },
                                                )
                                            )

                                            menu.add_button(ViewButton.back())
                                            menu.add_button(ViewButton.next())
                                            try:
                                                await menu.start()
                                            except:
                                                pass

                                            print("9960")

                                            if not await bot.shift_storage.find_by_id(
                                                ctx.author.id
                                            ):
                                                await bot.shift_storage.insert(
                                                    {
                                                        "_id": ctx.author.id,
                                                        "shifts": [
                                                            {
                                                                "name": ctx.author.name,
                                                                "startTimestamp": shift[
                                                                    "startTimestamp"
                                                                ],
                                                                "endTimestamp": ctx.message.created_at.replace(
                                                                    tzinfo=None
                                                                ).timestamp(),
                                                                "totalSeconds": time_delta.total_seconds(),
                                                                "guild": ctx.guild.id,
                                                                "moderations": shift[
                                                                    "moderations"
                                                                ]
                                                                if "moderations"
                                                                in shift.keys()
                                                                else [],
                                                                "type": shift["type"]
                                                                if "type"
                                                                in shift.keys()
                                                                else None,
                                                            }
                                                        ],
                                                        "totalSeconds": time_delta.total_seconds(),
                                                    }
                                                )
                                            else:
                                                data = (
                                                    await bot.shift_storage.find_by_id(
                                                        ctx.author.id
                                                    )
                                                )

                                                if "shifts" in data.keys():
                                                    if data["shifts"] is None:
                                                        data["shifts"] = []

                                                    if data["shifts"] == []:
                                                        shifts = [
                                                            {
                                                                "name": ctx.author.name,
                                                                "startTimestamp": shift[
                                                                    "startTimestamp"
                                                                ],
                                                                "endTimestamp": ctx.message.created_at.replace(
                                                                    tzinfo=None
                                                                ).timestamp(),
                                                                "totalSeconds": time_delta.total_seconds(),
                                                                "guild": ctx.guild.id,
                                                                "moderations": shift[
                                                                    "moderations"
                                                                ]
                                                                if "moderations"
                                                                in shift.keys()
                                                                else [],
                                                                "type": shift["type"]
                                                                if "type"
                                                                in shift.keys()
                                                                else None,
                                                            }
                                                        ]
                                                    else:
                                                        object = {
                                                            "name": ctx.author.name,
                                                            "startTimestamp": shift[
                                                                "startTimestamp"
                                                            ],
                                                            "endTimestamp": ctx.message.created_at.replace(
                                                                tzinfo=None
                                                            ).timestamp(),
                                                            "totalSeconds": time_delta.total_seconds(),
                                                            "guild": ctx.guild.id,
                                                            "moderations": shift[
                                                                "moderations"
                                                            ]
                                                            if "moderations"
                                                            in shift.keys()
                                                            else [],
                                                            "type": shift["type"]
                                                            if "type" in shift.keys()
                                                            else None,
                                                        }
                                                        shiftdata = data["shifts"]
                                                        shifts = shiftdata + [object]

                                                    await bot.shift_storage.update_by_id(
                                                        {
                                                            "_id": ctx.author.id,
                                                            "shifts": shifts,
                                                            "totalSeconds": sum(
                                                                [
                                                                    shifts[i][
                                                                        "totalSeconds"
                                                                    ]
                                                                    for i in range(
                                                                        len(shifts)
                                                                    )
                                                                    if shifts[i]
                                                                    is not None
                                                                ]
                                                            ),
                                                        }
                                                    )
                                                else:
                                                    await bot.shift_storage.update_by_id(
                                                        {
                                                            "_id": ctx.author.id,
                                                            "shifts": [
                                                                {
                                                                    "name": ctx.author.name,
                                                                    "startTimestamp": shift[
                                                                        "startTimestamp"
                                                                    ],
                                                                    "endTimestamp": ctx.message.created_at.replace(
                                                                        tzinfo=None
                                                                    ).timestamp(),
                                                                    "totalSeconds": time_delta.total_seconds(),
                                                                    "guild": ctx.guild.id,
                                                                    "moderations": shift[
                                                                        "moderations"
                                                                    ]
                                                                    if "moderations"
                                                                    in shift.keys()
                                                                    else [],
                                                                    "type": shift[
                                                                        "type"
                                                                    ]
                                                                    if "type"
                                                                    in shift.keys()
                                                                    else None,
                                                                }
                                                            ],
                                                            "totalSeconds": time_delta.total_seconds(),
                                                        }
                                                    )

                                            if await bot.shifts.find_by_id(
                                                ctx.author.id
                                            ):
                                                dataShift = await bot.shifts.find_by_id(
                                                    ctx.author.id
                                                )
                                                if "data" in dataShift.keys():
                                                    if isinstance(
                                                        dataShift["data"], list
                                                    ):
                                                        for item in dataShift["data"]:
                                                            if (
                                                                item["guild"]
                                                                == ctx.guild.id
                                                            ):
                                                                dataShift[
                                                                    "data"
                                                                ].remove(item)
                                                                break
                                                await bot.shifts.update_by_id(dataShift)

                                            role = None
                                            if shift_type:
                                                if shift_type.get("role"):
                                                    role = [
                                                        discord.utils.get(
                                                            ctx.guild.roles, id=role
                                                        )
                                                        for role in shift_type.get(
                                                            "role"
                                                        )
                                                    ]
                                            else:
                                                if configItem["shift_management"][
                                                    "role"
                                                ]:
                                                    if not isinstance(
                                                        configItem["shift_management"][
                                                            "role"
                                                        ],
                                                        list,
                                                    ):
                                                        role = [
                                                            discord.utils.get(
                                                                ctx.guild.roles,
                                                                id=configItem[
                                                                    "shift_management"
                                                                ]["role"],
                                                            )
                                                        ]
                                                    else:
                                                        role = [
                                                            discord.utils.get(
                                                                ctx.guild.roles, id=role
                                                            )
                                                            for role in configItem[
                                                                "shift_management"
                                                            ]["role"]
                                                        ]

                                            if role:
                                                for rl in role:
                                                    if (
                                                        rl in ctx.author.roles
                                                        and rl is not None
                                                    ):
                                                        try:
                                                            await ctx.author.remove_roles(
                                                                rl
                                                            )
                                                        except:
                                                            await invis_embed(
                                                                ctx,
                                                                f"Could not remove {rl} from {ctx.author.mention}",
                                                            )
                                            await message.add_reaction("📝")
                                            return

                                        await bot.process_commands(new_message)
                                        print("Processed commands")

                                        await message.add_reaction("📝")
                                        return

                                    try:
                                        type, reason = (
                                            " ".join(command.split(" ")[2:])
                                        ).split(" for ")
                                    except:
                                        await message.add_reaction("❌")
                                        return await message.add_reaction("1️⃣")

                                    reason = reason.replace('"', "")
                                    type = type.strip()

                                    generic_warning_types = [
                                        "Warning",
                                        "Kick",
                                        "Ban",
                                        "BOLO",
                                    ]

                                    warning_types = (
                                        await bot.punishment_types.find_by_id(
                                            message.guild.id
                                        )
                                    )
                                    if warning_types is None:
                                        warning_types = {
                                            "_id": message.guild.id,
                                            "types": generic_warning_types,
                                        }
                                        await bot.punishment_types.insert(warning_types)
                                        warning_types = warning_types["types"]
                                    else:
                                        warning_types = warning_types["types"]

                                    print("2619")
                                    t_lowered = type.lower()
                                    print(t_lowered)

                                    if person.count(",") > 0:
                                        persons = person.split(",")
                                    else:
                                        persons = [person]

                                    print("2406")

                                    for person in persons:
                                        roblox_user = {}

                                        if not any(
                                            [
                                                i in person.lower()
                                                for i in string.ascii_lowercase
                                            ]
                                        ):
                                            # Is a Roblox ID
                                            async with aiohttp.ClientSession() as session:
                                                async with session.post(
                                                    "https://users.roblox.com/v1/users",
                                                    json={
                                                        "userIds": [person],
                                                        "excludeBannedUsers": False,
                                                    },
                                                ) as resp:
                                                    print(resp)
                                                    print("USER ID VERSION!!!")
                                                    if resp.status == 200:
                                                        data = await resp.json()
                                                        if data["data"]:
                                                            roblox_user = data["data"][
                                                                0
                                                            ]
                                        else:
                                            # Is a Roblox Username
                                            async with aiohttp.ClientSession() as session:
                                                async with session.post(
                                                    "https://users.roblox.com/v1/usernames/users",
                                                    json={
                                                        "usernames": [person],
                                                        "excludeBannedUsers": False,
                                                    },
                                                ) as resp:
                                                    print(resp)
                                                    if resp.status == 200:
                                                        data = await resp.json()
                                                        if data["data"]:
                                                            roblox_user = data["data"][
                                                                0
                                                            ]

                                        print(roblox_user)
                                        if not roblox_user:
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("2️⃣")

                                        designated_channel = None
                                        settings = await bot.settings.find_by_id(
                                            message.guild.id
                                        )
                                        if settings:
                                            warning_type = None
                                            for warning in warning_types:
                                                if isinstance(warning, str):
                                                    if warning.lower() == type.lower():
                                                        warning_type = warning
                                                elif isinstance(warning, dict):
                                                    if (
                                                        warning["name"].lower()
                                                        == type.lower()
                                                    ):
                                                        warning_type = warning

                                            if isinstance(warning_type, str):
                                                if settings["customisation"].get(
                                                    "kick_channel"
                                                ):
                                                    if (
                                                        settings["customisation"][
                                                            "kick_channel"
                                                        ]
                                                        != "None"
                                                    ):
                                                        if (
                                                            warning_type.lower()
                                                            == "kick"
                                                        ):
                                                            designated_channel = (
                                                                bot.get_channel(
                                                                    settings[
                                                                        "customisation"
                                                                    ]["kick_channel"]
                                                                )
                                                            )
                                                if settings["customisation"].get(
                                                    "ban_channel"
                                                ):
                                                    if (
                                                        settings["customisation"][
                                                            "ban_channel"
                                                        ]
                                                        != "None"
                                                    ):
                                                        if (
                                                            warning_type.lower()
                                                            == "ban"
                                                        ):
                                                            designated_channel = (
                                                                bot.get_channel(
                                                                    settings[
                                                                        "customisation"
                                                                    ]["ban_channel"]
                                                                )
                                                            )
                                                if settings["customisation"].get(
                                                    "bolo_channel"
                                                ):
                                                    if (
                                                        settings["customisation"][
                                                            "bolo_channel"
                                                        ]
                                                        != "None"
                                                    ):
                                                        if (
                                                            warning_type.lower()
                                                            == "bolo"
                                                        ):
                                                            designated_channel = (
                                                                bot.get_channel(
                                                                    settings[
                                                                        "customisation"
                                                                    ]["bolo_channel"]
                                                                )
                                                            )
                                            else:
                                                if isinstance(warning_type, dict):
                                                    if "channel" in warning_type.keys():
                                                        if (
                                                            warning_type["channel"]
                                                            != "None"
                                                        ):
                                                            designated_channel = (
                                                                bot.get_channel(
                                                                    warning_type[
                                                                        "channel"
                                                                    ]
                                                                )
                                                            )

                                        print(
                                            "2706 - Designated channel {}".format(
                                                designated_channel
                                            )
                                        )
                                        if designated_channel is None:
                                            try:
                                                designated_channel = discord.utils.get(
                                                    message.guild.channels,
                                                    id=settings["punishments"][
                                                        "channel"
                                                    ],
                                                )
                                            except KeyError:
                                                print(
                                                    "2713 - Designated channel {}".format(
                                                        designated_channel
                                                    )
                                                )
                                                await message.add_reaction("❌")
                                                return await message.add_reaction("3️⃣")
                                        if designated_channel is None:
                                            print(
                                                "2715 - Designated channel {}".format(
                                                    designated_channel
                                                )
                                            )
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("4️⃣")

                                        if not warning_type:
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("5️⃣")

                                        discord_user = 0
                                        async for document in bot.synced_users.db.find(
                                            {"roblox": str(profile_link.split("/")[4])}
                                        ):
                                            discord_user = document["_id"]

                                        print(f"Discord User: {discord_user}")
                                        if discord_user == 0:
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("6️⃣")

                                        user = discord.utils.get(
                                            message.guild.members, id=discord_user
                                        )
                                        if not user:
                                            user = await message.guild.fetch_member(
                                                discord_user
                                            )
                                            if not user:
                                                await message.add_reaction("❌")
                                                return await message.add_reaction("7️⃣")

                                        async with aiohttp.ClientSession() as session:
                                            async with session.get(
                                                f'https://thumbnails.roblox.com/v1/users/avatar?userIds={roblox_user["id"]}&size=420x420&format=Png'
                                            ) as f:
                                                if f.status == 200:
                                                    avatar = await f.json()
                                                    Headshot_URL = avatar["data"][0][
                                                        "imageUrl"
                                                    ]
                                                else:
                                                    Headshot_URL = ""

                                        default_warning_item = {
                                            "_id": roblox_user["name"].lower(),
                                            "warnings": [
                                                {
                                                    "id": next(generator),
                                                    "Type": f"{type.lower().title()}",
                                                    "Reason": reason,
                                                    "Moderator": [user.name, user.id],
                                                    "Time": message.created_at.strftime(
                                                        "%m/%d/%Y, %H:%M:%S"
                                                    ),
                                                    "Guild": message.guild.id,
                                                }
                                            ],
                                        }

                                        singular_warning_item = {
                                            "id": next(generator),
                                            "Type": f"{type.lower().title()}",
                                            "Reason": reason,
                                            "Moderator": [user.name, user.id],
                                            "Time": message.created_at.strftime(
                                                "%m/%d/%Y, %H:%M:%S"
                                            ),
                                            "Guild": message.guild.id,
                                        }

                                        configItem = await bot.settings.find_by_id(
                                            message.guild.id
                                        )

                                        embed = discord.Embed(
                                            title=roblox_user["name"], color=0x2E3136
                                        )
                                        embed.set_thumbnail(url=Headshot_URL)

                                        try:
                                            embed.set_footer(
                                                text="Staff Logging Module"
                                            )
                                        except:
                                            pass
                                        embed.add_field(
                                            name="<:staff:1035308057007230976> Staff Member",
                                            value=f"<:ArrowRight:1035003246445596774> {user.mention}",
                                            inline=False,
                                        )
                                        embed.add_field(
                                            name="<:WarningIcon:1035258528149033090> Violator",
                                            value=f"<:ArrowRight:1035003246445596774> {person}",
                                            inline=False,
                                        )
                                        embed.add_field(
                                            name="<:MalletWhite:1035258530422341672> Type",
                                            value=f"<:ArrowRight:1035003246445596774> {type.lower().title()}",
                                            inline=False,
                                        )
                                        embed.add_field(
                                            name="<:QMark:1035308059532202104> Reason",
                                            value=f"<:ArrowRight:1035003246445596774> {reason}",
                                            inline=False,
                                        )

                                        if not await bot.warnings.find_by_id(
                                            roblox_user["name"].lower()
                                        ):
                                            await bot.warnings.insert(
                                                default_warning_item
                                            )
                                        else:
                                            dataset = await bot.warnings.find_by_id(
                                                roblox_user["name"].lower()
                                            )
                                            dataset["warnings"].append(
                                                singular_warning_item
                                            )
                                            await bot.warnings.update_by_id(dataset)

                                        shift = await bot.shifts.find_by_id(user.id)

                                        if shift is not None:
                                            if "data" in shift.keys():
                                                for index, item in enumerate(
                                                    shift["data"]
                                                ):
                                                    if isinstance(item, dict):
                                                        if (
                                                            item["guild"]
                                                            == message.guild.id
                                                        ):
                                                            if (
                                                                "moderations"
                                                                in item.keys()
                                                            ):
                                                                item[
                                                                    "moderations"
                                                                ].append(
                                                                    {
                                                                        "id": next(
                                                                            generator
                                                                        ),
                                                                        "Type": f"{type.lower().title()}",
                                                                        "Reason": reason,
                                                                        "Moderator": [
                                                                            user.name,
                                                                            user.id,
                                                                        ],
                                                                        "Time": message.created_at.strftime(
                                                                            "%m/%d/%Y, %H:%M:%S"
                                                                        ),
                                                                        "Guild": message.guild.id,
                                                                        "synced": True,
                                                                    }
                                                                )
                                                            else:
                                                                item["moderations"] = [
                                                                    {
                                                                        "id": next(
                                                                            generator
                                                                        ),
                                                                        "Type": f"{type.lower().title()}",
                                                                        "Reason": reason,
                                                                        "Moderator": [
                                                                            user.name,
                                                                            user.id,
                                                                        ],
                                                                        "Time": message.created_at.strftime(
                                                                            "%m/%d/%Y, %H:%M:%S"
                                                                        ),
                                                                        "Guild": message.guild.id,
                                                                        "synced": True,
                                                                    }
                                                                ]
                                                            shift["data"][index] = item
                                                            await bot.shifts.update_by_id(
                                                                shift
                                                            )

                                        await designated_channel.send(embed=embed)

                                    discord_user = None
                                    async for document in bot.synced_users.db.find(
                                        {"roblox": str(roblox_user["id"])}
                                    ):
                                        discord_user = document["_id"]

                                    if discord_user:
                                        try:
                                            member = await message.guild.fetch_member(
                                                discord_user
                                            )
                                        except discord.NotFound:
                                            member = None

                                        if member:
                                            should_dm = True
                                            if document.get("consent"):
                                                if (
                                                    document["consent"].get(
                                                        "punishments"
                                                    )
                                                    is False
                                                ):
                                                    should_dm = False

                                            if should_dm:
                                                try:
                                                    personal_embed = discord.Embed(
                                                        title="<:WarningIcon:1035258528149033090> You have been moderated!",
                                                        description=f"***{message.guild.name}** has moderated you in-game*",
                                                        color=0x2E3136,
                                                    )
                                                    personal_embed.add_field(
                                                        name="<:MalletWhite:1035258530422341672> Moderation Details",
                                                        value=f"<:ArrowRightW:1035023450592514048> **Username:** {person}\n<:ArrowRightW:1035023450592514048> **Reason:** {reason}\n<:ArrowRightW:1035023450592514048> **Type:** {type.lower().title()}",
                                                        inline=False,
                                                    )

                                                    try:
                                                        personal_embed.set_author(
                                                            name=message.guild.name,
                                                            icon_url=message.guild.icon.url,
                                                        )
                                                    except:
                                                        personal_embed.set_author(
                                                            name=message.guild.name
                                                        )

                                                    await member.send(
                                                        embed=personal_embed
                                                    )

                                                except:
                                                    pass

                                    await message.add_reaction("📝")

                            if ":m " in embed.description:
                                if "Command Usage" in embed.title:
                                    raw_content = embed.description
                                    user, command = raw_content.split(
                                        'used the command: "'
                                    )

                                    profile_link = user.split("(")[1].split(")")[0]

                                    msg = "".join(command.split(":m ")[1:]).replace(
                                        '"', ""
                                    )

                                    discord_user = 0
                                    async for document in bot.synced_users.db.find(
                                        {"roblox": str(profile_link.split("/")[4])}
                                    ):
                                        discord_user = document["_id"]

                                    print(f"Discord User: {discord_user}")
                                    if discord_user == 0:
                                        await message.add_reaction("❌")
                                        return await message.add_reaction("6️⃣")

                                    user = discord.utils.get(
                                        message.guild.members, id=discord_user
                                    )
                                    if not user:
                                        user = await message.guild.fetch_member(
                                            discord_user
                                        )
                                        if not user:
                                            await message.add_reaction("❌")
                                            return await message.add_reaction("7️⃣")

                                    new_message = copy.copy(message)
                                    new_message.channel = await user.create_dm()
                                    new_message.author = user

                                    new_ctx = await bot.get_context(new_message)
                                    ctx = new_ctx

                                    configItem = await bot.settings.find_by_id(
                                        ctx.guild.id
                                    )
                                    if not configItem:
                                        return

                                    if not configItem.get("game_logging"):
                                        return
                                    if not configItem["game_logging"].get("message"):
                                        return

                                    if (
                                        not configItem["game_logging"]
                                        .get("message")
                                        .get("enabled")
                                    ):
                                        return
                                    if (
                                        not configItem["game_logging"]
                                        .get("message")
                                        .get("channel")
                                    ):
                                        return
                                    channel = ctx.guild.get_channel(
                                        configItem["game_logging"]["message"]["channel"]
                                    )
                                    if not channel:
                                        return
                                    embed = discord.Embed(
                                        title="<:LinkIcon:1044004006109904966> Message Logging",
                                        description=f"<:ArrowRight:1035003246445596774> Please enter the message you would like to log.",
                                        color=0x2E3136,
                                    )

                                    announcement = msg

                                    embed = discord.Embed(
                                        title="<:MessageIcon:1035321236793860116> Message Logged",
                                        description="*A new message has been logged in the server.*",
                                        color=0x2E3136,
                                    )

                                    embed.set_author(
                                        name=ctx.author.name,
                                        icon_url=ctx.author.display_avatar.url,
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

        if aa_detection == True:
            if webhook_channel != None:
                print("webhook channel")
                if message.channel.id == webhook_channel.id:
                    for embed in message.embeds:
                        print("embed found")
                        if embed.description not in ["", None] and embed.title not in [
                            "",
                            None,
                        ]:
                            print("embed desc")
                            if (
                                ":kick" in embed.description
                                or ":ban" in embed.description
                            ):
                                print("used kick/ban command")
                                if (
                                    "Command Usage" in embed.title
                                    or "Kick/Ban Command Usage" in embed.title
                                ):
                                    print("command usage")
                                    raw_content = embed.description
                                    user, command = raw_content.split(
                                        "used the command: "
                                    )
                                    code = embed.footer.text.split("Server: ")[1]
                                    if command.count(",") + 1 >= 5:
                                        embed = discord.Embed(
                                            title="<:WarningIcon:1035258528149033090> Excessive Moderations Detected",
                                            description="*ERM has detected that a staff member has kicked/banned an excessive amount of players in the in-game server.*",
                                            color=0x2E3136,
                                        )

                                        embed.add_field(
                                            name="<:Search:1035353785184288788> Staff Member:",
                                            value=f"<:ArrowRight:1035003246445596774> {user}",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:MalletWhite:1035258530422341672> Trigger:",
                                            value=f"<:ArrowRight:1035003246445596774> **{command.count(',') + 1}** kicks/bans in a single command.",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:EditIcon:1042550862834323597> Explanation",
                                            value=f"<:ArrowRight:1035003246445596774> On <t:{int(message.created_at.timestamp())}>, {user.split(']')[0].replace('[', '').replace(']', '')} simultaneously kicked/banned {command.count(',') + 1} people from **{code}**",
                                            inline=False,
                                        )

                                        pings = []
                                        if "role" in dataset["game_security"].keys():
                                            if (
                                                dataset["game_security"]["role"]
                                                is not None
                                            ):
                                                if isinstance(
                                                    dataset["game_security"]["role"],
                                                    list,
                                                ):
                                                    for role in dataset[
                                                        "game_security"
                                                    ]["role"]:
                                                        role = discord.utils.get(
                                                            message.guild.roles, id=role
                                                        )
                                                        pings.append(role.mention)

                                        await aa_detection_channel.send(
                                            ",".join(pings) if pings != [] else "",
                                            embed=embed,
                                        )
                                    if " all" in command:
                                        embed = discord.Embed(
                                            title="<:WarningIcon:1035258528149033090> Excessive Moderations Detected",
                                            description="*ERM has detected that a staff member has kicked/banned an excessive amount of players in the in-game server.*",
                                            color=0x2E3136,
                                        )

                                        embed.add_field(
                                            name="<:Search:1035353785184288788> Staff Member:",
                                            description=f"<:ArrowRight:1035003246445596774> {user}",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:MalletWhite:1035258530422341672> Trigger:",
                                            value=f"<:ArrowRight:1035003246445596774> Kicking/banning everyone in the server.",
                                            inline=False,
                                        )

                                        embed.add_field(
                                            name="<:EditIcon:1042550862834323597> Explanation",
                                            value=f"<:ArrowRight:1035003246445596774> On <t:{int(message.created_at.timestamp())}>, {user.split(']')[0].replace('[').replace(']')} kicked/banned everyone from **{code}**",
                                            inline=False,
                                        )

                                        pings = []
                                        if "role" in dataset["game_security"].keys():
                                            if (
                                                dataset["game_security"]["role"]
                                                is not None
                                            ):
                                                if isinstance(
                                                    dataset["game_security"]["role"],
                                                    list,
                                                ):
                                                    for role in dataset[
                                                        "game_security"
                                                    ]["role"]:
                                                        role = discord.utils.get(
                                                            message.guild.roles, id=role
                                                        )
                                                        pings.append(role.mention)

                                        await aa_detection_channel.send(
                                            ",".join(pings) if pings != [] else "",
                                            embed=embed,
                                        )

        if message.author.bot:
            return

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
            logging.info(isStaffPermitted)

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
                    print(antiping_roles)
                    print(role)
                    if dataset["antiping"].get("use_hierarchy") in [True, None]:
                        if role is not None:
                            if mention.top_role > role or mention.top_role == role:
                                embed = discord.Embed(
                                    title=f"Do not ping {role.name} or above!",
                                    color=discord.Color.red(),
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
                                except:
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
                                except:
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
