"""
This configuration is used in setup as a base configuration before modification.
"""

import discord

base_configuration = {
    "_id": 0,
    "antiping": {
        "enabled": False,
        "role": [],
        "bypass_role": [],
        "use_hierarchy": False,
    },
    "staff_management": {
        "enabled": False,
        "role": [],
        "management_role": [],
        "channel": None,
        "loa_role": [],
        "ra_role": [],
    },
    "punishments": {
        "enabled": False,
        "channel": None,
        "kick_channel": None,
        "ban_channel": None,
        "bolo_channel": None,
    },
    "shift_management": {
        "enabled": False,
        "role": [],
        "channel": None,
        "quota": 0,
        "nickname_prefix": "",
        "maximum_staff": 0,
        "role_quotas": [],
    },
    "customisation": {"prefix": ">"},
    "shift_types": {"types": []},
    "game_security": {
        "enabled": False,
        "webhook_channel": None,
        "channel": None,
        "role": [],
    },
    "game_logging": {
        "message": {"enabled": False, "channel": None},
        "sts": {"enabled": False, "channel": None},
        "priority": {"enabled": False, "channel": None},
    },
    "ERLC": {
        "player_logs": None,
        "kill_logs": None,
        "elevation_required": None,
        "rdm_mentionables": [],
        "rdm_channel": None,
        "automatic_shifts": {"enabled": False, "shift_type": None},
    },
}

"""
    Colour constants
"""

BLANK_COLOR = 0x2B2D31
blank_color = BLANK_COLOR  # Redundancy


GREEN_COLOR = discord.Colour.brand_green()
RED_COLOR = 0xD12F32
ORANGE_COLOR = discord.Colour.orange()

SERVER_CONDITIONS = {
    "In-Game Players": "ERLC_Players",
    "In-Game Moderators": "ERLC_Moderators",
    "In-Game Admins": "ERLC_Admins",
    "In-Game Owner": "ERLC_Owner",
    "In-Game Staff": "ERLC_Staff",
    "In-Game Queue": "ERLC_Queue",
    "On Duty Staff": "OnDuty",
    "On Break Staff": "OnBreak",
    "Players on Police": "ERLC_Police",
    "Players on Sheriff": "ERLC_Sheriff",
    "Players on Fire": "ERLC_Fire",
    "Players on DOT": "ERLC_DOT",
    "Players on Civilian": "ERLC_Civilian",
    "Players on Jail": "ERLC_Jail",
    "Vehicles Spawned": "ERLC_Vehicles",
    "If ... is in-game": "ERLC_X_InGame",
}

RELEVANT_DESCRIPTIONS = [
    "All players currently in the in-game server.",
    "Number of moderators in the in-game server.",
    "Number of admins in the in-game server.",
    "Number of those with Co-Owner or Owner permission within the server.",
    "Number of staff members in the in-game server.",
    "Number of players in the queue.",
    "All staff members currently on duty.",
    "All staff members currently on break.",
    "Number of players on the Police team.",
    "Number of players on the Sheriff team.",
    "Number of players on the Fire team.",
    "Number of players on the DOT team.",
    "Number of players on the Civilian team.",
    "Number of players on the Jail team.",
    "Number of vehicles spawned in-game.",
    "If a specific user is in-game.",
]

CONDITION_OPTIONS = {
    "Equals": "==",
    "Less Than": "<",
    "Less Than or Equals To": "<=",
    "Not Equals To": "!=",
    "More Than": ">",
    "More Than or Equals To": ">=",
}

OPTION_DESCRIPTIONS = [
    "If the value is equal to the specified value.",
    "If the value is less than the specified value.",
    "If the value is less than or equal to the specified value.",
    "If the value is not equal to the specified value.",
    "If the value is more than the specified value.",
    "If the value is more than or equal to the specified value.",
]
