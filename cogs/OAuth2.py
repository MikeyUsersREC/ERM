import discord
from discord.ext import commands

from menus import YesNoMenu, AccountLinkingMenu
from utils.constants import BLANK_COLOR, GREEN_COLOR
import asyncio
import time


class OAuth2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="link",
        description="Link your Roblox account with ERM.",
        extras={"ephemeral": True},
    )
    async def link_roblox(self, ctx: commands.Context):
        msg = None
        linked_account = await self.bot.oauth2_users.db.find_one(
            {"discord_id": ctx.author.id}
        )
        if linked_account:
            user = await self.bot.roblox.get_user(linked_account["roblox_id"])
            msg = await ctx.send(
                embed=discord.Embed(
                    title="Already Linked",
                    description=f"You have already linked your account with `{user.name}`. Are you sure you would like to relink?",
                    color=BLANK_COLOR,
                ),
                view=(view := YesNoMenu(ctx.author.id)),
            )
            timeout = await view.wait()
            if timeout or not view.value:
                await msg.edit(
                    embed=discord.Embed(
                        title="Cancelled",
                        description="This action was cancelled by the user.",
                        color=BLANK_COLOR,
                    ),
                    view=None,
                )
                return
        timestamp = time.time()
        verification_message = {
            "embed": discord.Embed(
                title="Verify with ERM",
                description="**To link your account with ERM, click the button below.**\nIf you encounter an error, please contact ERM Support by running `/support`.",
                color=BLANK_COLOR,
            ),
            "view": AccountLinkingMenu(self.bot, ctx.author, ctx.interaction),
        }

        await self.bot.pending_oauth2.db.insert_one({"discord_id": ctx.author.id})

        if msg is None:
            await ctx.send(**verification_message)
        else:
            await msg.edit(**verification_message)

        attempts = 0
        while await asyncio.sleep(3):
            if attempts > 60:
                break
            if not linked_account:
                if await self.bot.oauth2_users.db.find_one(
                    {"discord_id": ctx.author.id}
                ):
                    await msg.edit(
                        embed=discord.Embed(
                            title=f"{self.bot.emoji_controller.get_emoji('success')} Linked",
                            description="Your Roblox account has been successfully linked to ERM.",
                            color=GREEN_COLOR,
                        )
                    )
                    break
            else:
                if item := await self.bot.oauth2_users.db.find_one(
                    {"discord_id": ctx.author.id}
                ):
                    if item.get("last_updated", 0) > timestamp:
                        await msg.edit(
                            embed=discord.Embed(
                                title=f"{self.bot.emoji_controller.get_emoji('success')} Linked",
                                description="Your Roblox account has been successfully linked to ERM.",
                                color=GREEN_COLOR,
                            )
                        )
                        break
                else:
                    linked_account = None


async def setup(bot):
    await bot.add_cog(OAuth2(bot))
