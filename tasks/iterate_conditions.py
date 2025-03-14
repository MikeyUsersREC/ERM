import discord
from discord.ext import commands, tasks
import utils.prc_api
from utils.prc_api import Player
import asyncio
import nest_asyncio

nest_asyncio.apply()
# this is quite dangerous but we don't really have much of an option

'''
Condition Variables
- ERLC_Players
- ERLC_Moderators
- ERLC_Admins
- ERLC_Owner
- ERLC_Staff
- ERLC_Queue
- OnDuty
- OnBreak
- X_InGame
'''

'''
NOTABLE DESIGN LIMITATIONS
::: YOU MUST NOT HAVE SPACES IN YOUR CONSTANTS.
'''

operator_table = {
    "==": equals_operator,
    "<": less_than_operator,
    "<=": less_than_or_equals_to_operator,
    "!=": not_equals_to,
    ">": more_than_operator,
    ">=": more_than_or_equals_to_operator
}

variable_table = [
    "ERLC_Players", # these obviously still work for maple county as well
    "ERLC_Moderators",
    "ERLC_Admins",
    "ERLC_Owner",
    "ERLC_Staff",
    "ERLC_Queue", # this doesnt work for maple county :(
    "OnDuty",
    "OnBreak",
    "ERLC_X_InGame"
]

value_finder_table = {
    "ERLC_Players": count_erlc_players,
    "ERLC_Moderators": count_erlc_moderators,
    "ERLC_Admins": count_erlc_admins,
    "ERLC_Owners": count_erlc_owners,
    "ERLC_Queue": count_erlc_queue,
    "ERLC_X_InGame": x_ingame
}


def function_argument_count(func):
    return func.__code__.co_argcount

def argument_names(func):
    return func.__code__.co_varnames


'''
PREDETERMINED FUTURE FUNCTIONS
- These are asynchronous functions which help in the fetching of variables before passing to a custom function.
'''
async def get_queue(api_client, guild_id):
    return await api_client.get_server_queue(guild_id)

async def online_shifts(bot, guild_id):
    return [i async for i in bot.shift_management.shifts.db.find({"Guild": guild_id, "EndEpoch": 0})]

'''
CUSTOM FUNCTIONS
- The arguments you can provide in these functions are shown in the fetch_predetermined_futures function.
'''

def count_erlc_players(players: list[Player]):
    return len(players)
    
def count_erlc_moderators(players: list[Player]):
    return len(list(filter(lambda x: x.permission == "Server Moderator", players)))

def count_erlc_admins(players: list[Player]):
    return len(list(filter(lambda x: x.permission == "Server Administrator", players)))

def count_erlc_owners(players: list[Player]):
    return len(list(filter(lambda x: x.permission not in ["Server Moderator", "Normal", "Server Administrator"], players)))

def count_erlc_queue(queue: list[Player]): # this one isnt supported for maple county yet
    return len(queue)

def x_ingame(players: list[Player], player: str):
    return player.lower() in [p.username.lower() for p in players]

def filter_online(shifts: list):
    return len(list(filter))

'''
Comparison Operators
(we're not stupid enough to use eval.)
'''
def equals_operator(v1: int, v2: int):
    return v1 == v2

def less_than_operator(v1: int, v2: int):
    return v1 < v2

def less_than_or_equals_to_operator(v1: int, v2: int):
    return v1 <= v2

def more_than_operator(v1: int, v2: int):
    return v1 > v2

def more_than_or_equals_to_operator(v1: int, v2: int):
    return v1 >= v2

def not_equals_to(v1: int, v2: int):
    return v1 != v2

def handle_comparison_operations(v1, v2, operator):
    function = operator_table[operator]
    return function(v1, v2)

def separate_arguments(condition):
    return condition.split(" ")[0], condition.split(" ")[1:] # ERLC_XInGame i_iMikey

async def handle_value(value) -> int:
    condition, args = separate_arguments(value)
    if condition not in variable_table:
        return value # this means we're comparing a raw constant
    else:
        func = value_finder_table[condition]
        argcount = function_argument_count(func)
        first_arg = argument_names(func)[0]
        submitted_argument = players
        if first_arg != "players":
            for k,future in futures:
                if k.lower() in condition.lower():
                    submitted_argument = future()
        if argcount > 1:
            return func(submitted_argument, *args)
        else:
            return func(submitted_argument)

def determine_func_info(cond):
    func = value_finder_table[cond]
    return func, argument_names(func)

async def fetch_predetermined_futures(bot, guild_id, condition, value, api_client=None):
    return {
        "queue": lambda: asyncio.run(get_queue(api_client, guild_id)),
        "shifts": lambda: asyncio.run(online_shifts(bot, guild_id)),
        "bot": lambda: bot,
        "guild_id": lambda: guild_id,
        "condition": lambda: condition,
    }


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
            values.append(int(item) if item.isdigit() else item) # this means we're comparing a raw constant
        else:
            func, args = determine_func_info(cond)
            submitted_arguments = [players] # change the 1st submitted argument to be our players object
            if args[0] != "players": # we already have players, we can use this
                submitted_arguments = []
            
            for item in args[0 if args[0] != "players" else 1:]:
                submitted_arguments.append(futures[item.lower()]())
            
            if len(args) > 1:
                values.append(func(submitted_argument, *args))
            else:
                values.append(func(submitted_argument))

    return handle_comparison_operations(*values, condition["Operator"])
    
async def handle_erm_condition(bot, guild_id, condition) -> bool:
    values = []
    for item in (condition["Variable"], condition["Value"]):
        cond, args = separate_arguments(item)
        futures = await fetch_predetermined_futures(bot, guild_id, condition, item)
        if cond not in variable_table:
            values.append(int(item) if item.isdigit() else item)
        else:
            func, args = determine_func_info(cond)
            submitted_arguments = []
            for item in args:
                submitted_arguments.append(futures[item.lower()]())
            
            if len(args) > 1:
                values.append(func(submitted_argument, *args))
            else:
                values.append(func(submitted_argument))

    return handle_comparison_operations(*values, condition["Operator"])
    

@tasks.loop(minutes=1)
async def iterate_conditions(bot):
    actions = [i async for i in bot.actions.db.find({"Conditions": {"$exists": True, "$ne": []}})]
    for action in actions:
        conditions = []
        for condition in actions["Conditions"]:
            if condition["Variable"] in value_finder_table.keys() or condition["Value"] in value_finder_table.keys():
                conditions.append(await handle_erlc_condition(bot, action['Guild'], condition))
            else:
                conditions.append()