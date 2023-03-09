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
            return await invis_embed(
                ctx,
                "This server is currently not setup. Please tell a server administrator to run `/setup` to allow the usage of this command.",
            )

        if not settings["verification"]["enabled"]:
            return await invis_embed(
                ctx,
                "This server has verification disabled. Please tell a server administrator to enable verification in `/config change`.",
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
            embed = discord.Embed(
                title="<:LinkIcon:1044004006109904966> ERM Verification",
                description="<:ArrowRight:1035003246445596774> Click `Verify` and input your ROBLOX username.",
                color=0x2E3136,
            )
            embed.set_footer(text="ROBLOX Verification provided by ERM")
            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.modal:
                try:
                    user = view.modal.name.value
                except:
                    return await invis_embed(
                        ctx, "You have not submitted a username. Please try again."
                    )
            else:
                return await invis_embed(
                    ctx, "You have not submitted a username. Please try again."
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
            success_embed = discord.Embed(
                title=f"<:ERMWhite:1044004989997166682> Welcome {roblox_user['name']}!",
                color=0x2E3136,
            )
            success_embed.description = f"<:ArrowRight:1035003246445596774> You've been verified as <:LinkIcon:1044004006109904966> **{roblox_user['name']}** in **{ctx.guild.name}**."
            success_embed.set_footer(
                text="ROBLOX Verification provided to you by Emergency Response Management (ERM)"
            )
            return await ctx.send(embed=success_embed)

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
                                return await invis_embed(
                                    ctx,
                                    "That is not a valid roblox username. Please try again.",
                                )

                else:
                    roblox_user = await r.json()
                    roblox_user = roblox_user["data"][0]
                    roblox_id = roblox_user["id"]

        if not verified:
            await bot.verification.upsert(
                {
                    "_id": ctx.author.id,
                    "roblox": roblox_id,
                    "isVerified": False,
                }
            )

            embed = discord.Embed(color=0x2E3136)
            embed.title = f"<:LinkIcon:1044004006109904966> {roblox_user['name']}, let's get you verified!"
            embed.description = f"<:ArrowRight:1035003246445596774> Go to our [ROBLOX game](https://www.roblox.com/games/11747455621/Verification)\n<:ArrowRight:1035003246445596774> Click on <:Resume:1035269012445216858>\n<:ArrowRight:1035003246445596774> Verify your ROBLOX account in the game.\n<:ArrowRight:1035003246445596774> Click **Done**!"
            embed.set_footer(
                text=f"ROBLOX Verification provided by Emergency Response Management"
            )
            view = VerifyView(ctx.author.id)
            await ctx.send(embed=embed, view=view)
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
                    print(new_data)
                    if "isVerified" in new_data.keys():
                        if new_data["isVerified"]:
                            return await after_verified(roblox_user)
                        else:
                            return await invis_embed(
                                ctx,
                                "You have not verified using the verification game. Please retry by running `/verify` again.",
                            )
                    else:
                        return await invis_embed(
                            ctx,
                            "You have not verified using the verification game. Please retry by running `/verify` again.",
                        )


async def setup(bot):
    await bot.add_cog(Verification(bot))
