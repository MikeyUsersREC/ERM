import logging

import discord
from discord.ext import commands, tasks
import utils.prc_api
from utils import prc_api
from utils.prc_api import Player
import asyncio
import nest_asyncio
from utils.conditions import *

nest_asyncio.apply()
# this is quite dangerous but we don't really have much of an option

async def handle_erlc_condition(bot, guild_id, condition) -> bool:
    api_client = bot.prc_api
    if await bot.mc_api.get_server_key(guild_id) is not None:
        api_client = bot.mc_api
    try:
        players = await api_client.get_server_players(guild_id)
    except prc_api.ResponseFailure:
        return False

    values = []
    for item in (condition["Variable"], condition["Value"]):
        cond, args = separate_arguments(item)
        futures = await fetch_predetermined_futures(bot, guild_id, condition, item, api_client)
        if cond not in variable_table:
            values.append(int(item) if item.isdigit() else item)  # this means we're comparing a raw constant
        else:
            func, func_args = determine_func_info(cond)
            submitted_arguments = [players]  # change the 1st submitted argument to be our players object
            if func_args[0] != "players":  # we already have players, we can use this
                submitted_arguments = []

            for item in func_args[0 if func_args[0] != "players" else 1:]:
                submitted_arguments.append(futures[item.lower()]())

            if len(func_args) > 1:
                values.append(func(*submitted_arguments, *args))
            else:
                values.append(func(*submitted_arguments))

    return handle_comparison_operations(*values, condition["Operator"])


async def handle_erm_condition(bot, guild_id, condition) -> bool:
    values = []
    for item in (condition["Variable"], condition["Value"]):
        cond, args = separate_arguments(item)
        futures = await fetch_predetermined_futures(bot, guild_id, condition, item)
        if cond not in variable_table:
            values.append(int(item) if item.isdigit() else item)
        else:
            func, func_args = determine_func_info(cond)
            submitted_arguments = []
            for item in func_args:
                submitted_arguments.append(futures[item.lower()]())

            if len(func_args) > 1:
                values.append(func(*submitted_arguments, *args))
            else:
                values.append(func(*submitted_arguments))

    return handle_comparison_operations(*values, condition["Operator"])


@tasks.loop(minutes=1)
async def iterate_conditions(bot):
    actions = [i async for i in bot.actions.db.find({"Conditions": {"$exists": True, "$ne": []}})]
    for action in actions:
        conditions = []
        for condition in action["Conditions"]:
            if condition["Variable"] in value_finder_table.keys() or condition["Value"] in value_finder_table.keys():
                conditions.append(await handle_erlc_condition(bot, action['Guild'], condition))
            else:
                conditions.append(await handle_erm_condition(bot, action['Guild'], condition))

        print(conditions)
    logging.info("[CONDITIONS] Iterated through all conditions.")