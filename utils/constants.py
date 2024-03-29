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
    "use_hierarchy": False 
  },                      
  "staff_management": {    
    "enabled": False,     
    "role": [],     
    "management_role": [],
    "channel": None,      
    "loa_role": [],      
    "ra_role": []        
  },                    
  "punishments": {      
    "enabled": False,   
    "channel": None,    
    "kick_channel": None,
    "ban_channel": None, 
    "bolo_channel": None 
  },                    
  "shift_management": {  
    "enabled": False,   
    "role": [],        
    "channel": None,
    "quota": 0,
    "nickname_prefix": "",
    "maximum_staff": 0,
    "role_quotas": []
  },
  "customisation": {
    "prefix": ">"
  },
  "shift_types": {
    "types": []
  },
  "game_security": {
    "enabled": False,
    "webhook_channel": None,
    "channel": None,
    "role": []
  },
  "game_logging": {
    "message": {
      "enabled": False,
      "channel": None
    },
    "sts": {
      "enabled": False,
      "channel": None
    },
    "priority": {
      "enabled": False,
      "channel": None
    }
  },
  "ERLC": {
    "player_logs": None,
    "kill_logs": None,
    "elevation_required": None,
    "rdm_mentionables": [],
    "rdm_channel": None,
    "automatic_shifts": {
      "enabled": False,
      "shift_type": None
    }
  }
}

"""
    Colour constants
"""

BLANK_COLOR = 0x2b2d31
blank_color = BLANK_COLOR # Redundancy


GREEN_COLOR = discord.Colour.brand_green()
RED_COLOR = 0xd12f32
ORANGE_COLOR = discord.Colour.orange()