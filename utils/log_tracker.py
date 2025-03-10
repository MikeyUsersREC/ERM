from collections import defaultdict
from discord.ext import commands


class LogTracker:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Initialize last_timestamps with a starting time
        self.last_timestamps = defaultdict(
            lambda: defaultdict(lambda: int(self.bot.start_time))
        )

    def get_last_timestamp(self, guild_id: int, log_type: str) -> int:
        # Get the last timestamp for the given guild and log type
        return self.last_timestamps[guild_id][log_type]

    def update_timestamp(self, guild_id: int, log_type: str, timestamp: int):
        # Update the timestamp if the provided one is more recent
        self.last_timestamps[guild_id][log_type] = max(
            timestamp, self.last_timestamps[guild_id][log_type]
        )
