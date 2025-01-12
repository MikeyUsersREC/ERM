from collections import defaultdict
from discord.ext import commands

class LogTracker:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        def return_start_time():
            return int(self.bot.start_time)
        self.last_timestamps = defaultdict(lambda: defaultdict(return_start_time))

    def get_last_timestamp(self, guild_id: int, log_type: str) -> int:
        return self.last_timestamps[guild_id][log_type]

    def update_timestamp(self, guild_id: int, log_type: str, timestamp: int):
        self.last_timestamps[guild_id][log_type] = max(
            timestamp,
            self.last_timestamps[guild_id][log_type]
        )
