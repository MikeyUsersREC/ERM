import typing

import aiohttp
import discord
import roblox
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

async def shift_type_autocomplete(
        interaction: discord.Interaction, _: str
) -> typing.List[app_commands.Choice[str]]:
    bot = interaction.client

    data = await bot.settings.find_by_id(interaction.guild.id)
    if not data:
        return [
            app_commands.Choice(
                name="Default",
                value="Default"
            )
        ]
    shift_types_settings = data.get('shift_types', {})
    types = shift_types_settings.get('types', [])

    if types is not None and len(types or []) != 0:
        return [app_commands.Choice(
            name=shift_type['name'],
            value=shift_type['name']
        ) for shift_type in types]
    else:
        return [
            app_commands.Choice(
                name="Default",
                value="Default"
            )
        ]

async def all_shift_type_autocomplete(
        interaction: discord.Interaction, _: str
) -> typing.List[app_commands.Choice[str]]:
    bot = (await Context.from_interaction(interaction)).bot
    data = await bot.settings.find_by_id(interaction.guild.id)
    if not data:
        return [
            app_commands.Choice(
                name="Default",
                value="Default"
            )
        ]
    shift_types_settings = data.get('shift_types', {})
    types = shift_types_settings.get('types', [])

    if types is not None:
        return [app_commands.Choice(
            name=shift_type['name'],
            value=shift_type['name']
        ) for shift_type in (types+[{"name": "All"}])]
    else:
        return [
            app_commands.Choice(
                name="Default",
                value="Default"
            )
        ]


async def action_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = (await Context.from_interaction(interaction)).bot
    actions = [i async for i in bot.actions.db.find({'Guild': interaction.guild.id})]
    if actions in [None, []]:
        return [
            discord.app_commands.Choice(name="No actions found", value="NULL")
        ]
    
    action_list = []
    for action in actions:
        if current not in ["", " "]:
            if (
                action["ActionName"].startswith(current)
                or current in action["ActionName"]
                or action["ActionName"].endswith(current)
            ):
                action_list.append(action["ActionName"])
        else:
            action_list.append(action["ActionName"])

    if len(action_list) == 0:
        return [
            discord.app_commands.Choice(
                name="No actions found", value="NULL"
            )
        ]

    commandList = []
    for command in action_list:
        commandList.append(
            discord.app_commands.Choice(name=command, value=command)
        )
    return commandList


async def command_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = (await Context.from_interaction(interaction)).bot
    Data = await bot.custom_commands.find_by_id(interaction.guild.id)
    if Data is None:
        return [
            discord.app_commands.Choice(name="No custom commands found", value="NULL")
        ]
    else:
        commands = []
        for command in Data["commands"]:
            if current not in ["", " "]:
                if (
                    command["name"].startswith(current)
                    or current in command["name"]
                    or command["name"].endswith(current)
                ):
                    commands.append(command["name"])
            else:
                commands.append(command["name"])
        if len(commands) == 0:
            return [
                discord.app_commands.Choice(
                    name="No custom commands found", value="NULL"
                )
            ]

       # # # print(commands)
        commandList = []
        for command in commands:
            if command not in [""]:
                commandList.append(
                    discord.app_commands.Choice(name=command, value=command)
                )
            else:
                cmd = None
                for c in Data["commands"]:
                    if c["name"].lower() == command.lower():
                        cmd = c
                commandList.append(
                    discord.app_commands.Choice(
                        name=cmd["message"]["content"][:20].replace(" ", "").lower(),
                        value=cmd["name"],
                    )
                )
        return commandList


async def punishment_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = interaction.client
    Data = await bot.punishment_types.find_by_id(interaction.guild.id)
    if Data is None:
        return [
            app_commands.Choice(name=item, value=item)
            for item in ["Warning", "Kick", "Ban", "BOLO"]
        ]
    else:
        return [
            app_commands.Choice(
                name=(item_identifier := item if isinstance(item, str) else item['name']),
                value=item_identifier
            ) for item in Data['types'] + ["Warning", "Kick", "Ban", "BOLO"]
        ]

async def user_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = interaction.client
    async def fallback_completion():
        choices = []
        async for search in bot.punishments.db.find({}).limit(10):
            if search['Username'] in [choice.name for choice in choices]:
                continue
            choices.append(
                discord.app_commands.Choice(name=search['Username'], value=search["Username"])
            )
        return choices

    if current in [None, ""]:
        return await fallback_completion()

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'https://www.roblox.com/search/users/results?keyword={current}&maxRows=12&startIndex=0') as resp:
                data_json = await resp.json()
                if data_json:
                    # print(data_json)
                    if isinstance(data_json.get('UserSearchResults'), list):
                        items = [item for item in data_json['UserSearchResults'][:25]]
                    else:
                        items = []
                else:
                    items = []
    choices = []
    for item in items:
        choices.append(
            discord.app_commands.Choice(name=item["Name"], value=item["Name"])
        )
    return choices
