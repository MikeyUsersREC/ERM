import os

default_emojis = {
    "check": 1163142000271429662,
    "xmark": 1166139967920164915,
    "success": 1163149118366040106,
    "error": 1164666124496019637,
    "WarningIcon": 1035258528149033090,
    "loa": 1169799727143977090,
    "log": 1163524830319104171,
    "shift": 1169801400545452033,
    "Clock": 1035308064305332224,
    "ShiftStarted": 1178033763477889175,
    "ShiftBreak": 1178034531702411375,
    "ShiftEnded": 1178035088655646880,
}

class EmojiController:
    def __init__(self, environment, bot):
        self.environment = environment
        self.bot = bot
        self.emojis = {}

    async def prefetch_emojis(self):
        if self.environment == "PRODUCTION":
            return

        application_emojis = await self.bot.fetch_application_emojis()
        for item in os.listdir("assets/emojis"):
            if item.endswith(".png"):
                if item.replace(".png", "") not in [i.name for i in application_emojis]:
                    emoji_name = item.replace(".png", "")
                    await self.bot.create_application_emoji(name=emoji_name, image=f"assets/emojis/{item}")

        new_application_emojis = await self.bot.fetch_application_emojis()
        for emoji in new_application_emojis:
            self.emojis[emoji.name] = emoji.id

    async def get_emoji(self, emoji_name):
        if self.environment == "PRODUCTION":
            return "<:{}:{}>".format(emoji_name, default_emojis[emoji_name])

        if not self.emojis:
            await self.prefetch_emojis()

        return "<:{}:{}>".format(emoji_name, default_emojis[emoji_name])