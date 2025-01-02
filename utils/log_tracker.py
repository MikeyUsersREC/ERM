from collections import defaultdict


class LogTracker:
    def __init__(self):
        self.last_timestamps = defaultdict(lambda: defaultdict(int))

    def get_last_timestamp(self, guild_id: int, log_type: str) -> int:
        return self.last_timestamps[guild_id][log_type]

    def update_timestamp(self, guild_id: int, log_type: str, timestamp: int):
        self.last_timestamps[guild_id][log_type] = max(
            timestamp,
            self.last_timestamps[guild_id][log_type]
        )
