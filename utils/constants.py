"""
    This configuration is used in setup as a base configuration before modification.
"""
import discord

base_configuration = {
    "_id": 0,
    "verification": {
        "enabled": False,
        "role": None,
    },
    "antiping": {"enabled": False, "role": None, "bypass_role": "None"},
    "staff_management": {"enabled": False, "channel": None},
    "punishments": {"enabled": False, "channel": None},
    "shift_management": {"enabled": False, "channel": None, "role": None},
    "customisation": {
        "color": "",
        "prefix": ">",
        "brand_name": "Emergency Response Management",
        "thumbnail_url": "",
        "footer_text": "Staff Logging Systems",
        "ban_channel": None,
    },
}

"""
    Colour constants
"""

BLANK_COLOR = 0x2b2d31
blank_color = BLANK_COLOR # Redundancy


GREEN_COLOR = discord.Colour.brand_green()
RED_COLOR = 0xd12f32
ORANGE_COLOR = discord.Colour.orange()