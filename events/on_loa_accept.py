import discord
from discord.ext import commands

from utils.constants import BLANK_COLOR, GREEN_COLOR


class OnLOAAccept(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_loa_accept(self, s_loa: dict, role_ids: list[int], accepted_by: int):
        guild = self.bot.get_guild(s_loa["guild_id"])
        try:
            user = await guild.fetch_member(int(s_loa["user_id"]))
        except:
            return
        try:
            await user.send(
                embed=discord.Embed(
                    title=f"{self.bot.emoji_controller.get_emoji('success')} Activity Notice Accepted",
                    description=f"Your {s_loa['type']} request in **{guild.name}** was accepted!",
                    color=GREEN_COLOR,
                )
            )
        except:
            pass

        settings = await self.bot.settings.find_by_id(guild.id)
        loa_roles = list(
            filter(
                lambda x: x is not None,
                [
                    discord.utils.get(guild.roles, id=identifier)
                    for identifier in role_ids
                ],
            )
        )
        for rl in loa_roles:
            if rl not in user.roles:
                try:
                    await user.add_roles(rl)
                except discord.HTTPException:
                    pass

        msg = s_loa["message_id"]
        loa_channel_id = settings.get("staff_management", {}).get("channel", 0)
        if not loa_channel_id:
            return
        loa_channel = guild.get_channel(loa_channel_id) or await guild.fetch_channel(
            loa_channel_id
        )
        messg = None
        try:
            messg = await loa_channel.fetch_message(msg)
        except:
            pass
        if not messg:
            return

        embed = messg.embeds[0]
        embed.title = (
            f"{self.bot.emoji_controller.get_emoji('success')} {s_loa['type']} Accepted"
        )
        embed.colour = GREEN_COLOR
        try:
            accepted_by_user = guild.get_member(
                accepted_by
            ) or await guild.fetch_member(accepted_by)
        except:
            pass

        embed.set_footer(
            text=f"Accepted by {accepted_by_user.name if accepted_by_user else 'n/a'}"
        )

        await messg.edit(embed=embed, view=None)

        view_item = await self.bot.views.db.find_one({"message_id": messg.id})

        await self.bot.views.delete_by_id(view_item["_id"])


async def setup(bot):
    await bot.add_cog(OnLOAAccept(bot))
