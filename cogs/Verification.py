import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from menus import EnterRobloxUsername
from menus import Verification as VerifyView
from utils.utils import invis_embed


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="verify",
        description="Verify with ERM",
        extras={"category": "Verification"},
    )
    @app_commands.describe(user="What's your ROBLOX username?")
    async def verify(self, ctx, user: str = None):
        bot = self.bot
        settings = await bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup."
            )

        if not settings["verification"]["enabled"]:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server has **Verification** disabled."
            )

        verified = False
        verified_user = await bot.verification.find_by_id(ctx.author.id)

        if verified_user:
            if "isVerified" in verified_user.keys():
                if verified_user["isVerified"]:
                    verified = True
                else:
                    verified_user = None
            else:
                verified = True

        if user is None and verified_user is None:
            view = EnterRobloxUsername(ctx.author.id)
            msg = await ctx.reply(
                content=f"<:ERMPending:1111097561588183121> **{ctx.author.name},** let's get you verified! Enter your ROBLOX username.",
                view=view,
            )
            await view.wait()
            if view.modal:
                try:
                    user = view.modal.name.value
                except:
                    return await msg.edit(
                        f":ERMClose:1111101633389146223>  **{ctx.author.name},** you did not submit a username."
                    )
            else:
                return await msg.edit(
                    f":ERMClose:1111101633389146223>  **{ctx.author.name},** you did not submit a username."
                )

        else:
            if user is None:
                user = verified_user["roblox"]
                verified = True
            else:
                user = user
                verified = False

        async def after_verified(roblox_user):
            try:
                await bot.verification.insert(
                    {
                        "_id": ctx.author.id,
                        "roblox": roblox_id,
                        "isVerified": True,
                    }
                )
            except:
                await bot.verification.upsert(
                    {
                        "_id": ctx.author.id,
                        "roblox": roblox_id,
                        "isVerified": True,
                    }
                )
            settings = await bot.settings.find_by_id(ctx.guild.id)
            verification_role = settings["verification"]["role"]
            if isinstance(verification_role, list):
                verification_role = [
                    discord.utils.get(ctx.guild.roles, id=int(role))
                    for role in verification_role
                ]
            elif isinstance(verification_role, int):
                verification_role = [
                    discord.utils.get(ctx.guild.roles, id=int(verification_role))
                ]
            else:
                verification_role = []
            for role in verification_role:
                try:
                    await ctx.author.add_roles(role)
                except:
                    pass
            try:
                await ctx.author.edit(nick=f"{roblox_user['name']}")
            except:
                pass
            embed = discord.Embed(
                description="<:ERMModify:1111100050718867577> **PRO TIP:** You can now run `/link` to get notified of when you're moderated.",
                color=0xED4348,
            )
            return await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** nice job! You've verified that you're **{roblox_user['name']}**",
                embed=embed,
            )

        if verified:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://users.roblox.com/v1/users/{user}"
                ) as r:
                    if r.status == 200:
                        roblox_user = await r.json()
                        roblox_id = roblox_user["id"]
                        return await after_verified(roblox_user)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://users.roblox.com/v1/usernames/users",
                json={"usernames": [user]},
            ) as r:
                if "success" in (await r.json()).keys():
                    if not (await r.json())["success"]:
                        async with session.get(
                            f"https://users.roblox.com/v1/users/{user}"
                        ) as r:
                            if r.status == 200:
                                roblox_user = await r.json()
                                roblox_id = roblox_user["id"]
                            else:
                                return await ctx.reply(
                                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I could not find your ROBLOX account!"
                                )

                else:
                    roblox_user = await r.json()
                    try:
                        roblox_user = roblox_user["data"][0]
                        roblox_id = roblox_user["id"]
                    except:
                        return await ctx.reply(
                            f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I could not find your ROBLOX account!"
                        )
        if not verified:
            await bot.verification.upsert(
                {
                    "_id": ctx.author.id,
                    "roblox": roblox_id,
                    "isVerified": False,
                }
            )

            embed = discord.Embed(color=0xED4348)
            embed.title = f"<:ERMSecurity:1113209656370802879> Prove your Identity"
            embed.description = f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Step 1:** Join our [ROBLOX game](https://www.roblox.com/games/11747455621/Verification)\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Step 2:** Wait to be kicked in-game.\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Step 3:** Click on the **Done** button!"

            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )
            view = VerifyView(ctx.author.id)
            await ctx.reply(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** one last step! Join our verification game.",
                embed=embed,
                view=view,
            )
            await view.wait()
            if view.value:
                if view.value == "done":
                    # async with aiohttp.ClientSession() as session:
                    #     # use https://users.roblox.com/v1/users/{userId} to get description
                    #     async with session.get(f'https://users.roblox.com/v1/users/{roblox_id}') as r:
                    #         if r.status == 200:
                    #             roblox_user = await r.json()
                    #             description = roblox_user['description']
                    #         else:
                    #             return await invis_embed(ctx,
                    #                                      'There was an error fetching your roblox profile. Please try again later.')
                    #
                    # if system_code in description:
                    #     return await after_verified(roblox_user)
                    # else:
                    #     await invis_embed(ctx, 'You have not put the system code in your description. Please try again.')
                    new_data = await bot.verification.find_by_id(ctx.author.id)
                   # # print(new_data)
                    if "isVerified" in new_data.keys():
                        if new_data["isVerified"]:
                            return await after_verified(roblox_user)
                        else:
                            return await ctx.reply(
                                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** it doesn't look like you verified! Try again."
                            )

                else:
                    return await ctx.reply(
                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** it doesn't look like you verified! Try again."
                    )


async def setup(bot):
    await bot.add_cog(Verification(bot))
