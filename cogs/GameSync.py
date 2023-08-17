import aiohttp
import discord
from discord.ext import commands

from menus import EnterRobloxUsername, LinkPathwayMenu, Verification


class GameSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name="link",
        description="Link your external accounts to your Discord account via verification methods",
        extras={"category": "Game Sync"},
        usage="link",
    )
    async def link(self, ctx):
        pass

    @link.command(
        name="roblox",
        description="Link your Roblox account with ERM.",
        extras={"category": "Game Sync"},
        usage="link roblox",
    )
    async def link_roblox(self, ctx: commands.Context):
        bot = self.bot
        is_erm_verified = False
        erm_roblox_id = 0
        async for document in bot.verification.db.find({"_id": ctx.author.id}):
            if document.get("is_verified"):
                is_erm_verified = True
                erm_roblox_id = document.get("roblox")

        if is_erm_verified:
            view = LinkPathwayMenu(ctx.author.id)
            await ctx.reply(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you can link your account with ERM or Bloxlink. Chose an option below. You appear to already be verified with ERM.",
                view=view,
            )
            timeout = await view.wait()
            if timeout:
                return

            pathway = view.value
        else:
            view = LinkPathwayMenu(ctx.author.id)
            verify_msg = await ctx.reply(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you can link your account with ERM or Bloxlink. Chose an option below.",
                view=view,
            )
            timeout = await view.wait()
            if timeout:
                return

            pathway = view.value

        if pathway == "bloxlink":
            ex_code = 0

            async def run_pathway():
                async with aiohttp.ClientSession(
                    headers={"api-key": bot.bloxlink_api_key}
                ) as session:
                    try:
                        async with session.get(
                            f"https://v3.blox.link/developer/discord/{ctx.author.id}"
                        ) as resp:
                            rbx = await resp.json()
                            if rbx["success"]:
                                if rbx["user"]["primaryAccount"] not in [None, 0]:
                                    verified_user = rbx["user"]["primaryAccount"]
                                else:
                                    verified_user = rbx["user"]["robloxId"]
                                status = True
                            else:
                                status = False
                    except:
                        status = None

                if status:
                    if await bot.synced_users.find_by_id(ctx.author.id):
                        await bot.synced_users.update_by_id(
                            {"_id": ctx.author.id, "roblox": verified_user}
                        )
                    else:
                        await bot.synced_users.insert(
                            {"_id": ctx.author.id, "roblox": verified_user}
                        )
                    await verify_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, I've linked your account!",
                        view=None,
                    )
                elif status is False:
                    view = Verification(ctx.author.id)
                    await verify_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, you're not verified with either Bloxlink or ERM! If you have verified, click **Done** below",
                        view=view,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return
                    if view.value == "cancel":
                        return
                    else:
                        await run_pathway()
                elif status is None:
                    ex_code = 1
                    pathway = "erm"

            if ex_code == 0:
                await run_pathway()
        if pathway == "erm":

            async def run_pathway():
                user = None
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
                    await verify_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, click the **Verify** button to start you verification process.",
                        view=view,
                    )
                    await view.wait()
                    if view.modal:
                        try:
                            user = view.modal.name.value
                        except:
                            return await verify_msg.edit(
                                content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you have not submitted a username. Please try again.",
                                view=None,
                            )
                        else:
                            return await verify_msg.edit(
                                content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, you have not submitted a username. Please try again.",
                                view=None,
                            )
                else:
                    if user is None:
                        user = verified_user["roblox"]
                        verified = True
                    else:
                        user = user
                        verified = False

                async def after_verified(roblox_user):
                    if await bot.synced_users.find_by_id(ctx.author.id):
                        await bot.synced_users.update_by_id(
                            {"_id": ctx.author.id, "roblox": str(roblox_user)}
                        )
                    else:
                        await bot.synced_users.insert(
                            {"_id": ctx.author.id, "roblox": str(roblox_user)}
                        )
                    await verify_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, nice! I've verified your account as **{roblox_user}**."
                    )

                if verified:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://users.roblox.com/v1/users/{user}"
                        ) as r:
                            if r.status == 200:
                                roblox_user = await r.json()
                                roblox_id = roblox_user["id"]
                                return await after_verified(roblox_user["id"])

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
                                        return await verify_msg.edit(
                                            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, that's not a valid ROBLOX user."
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

                    embed = discord.Embed(color=0xED4348)
                    embed.title = (
                        f"<:ERMSecurity:1113209656370802879> Prove your Identity"
                    )
                    embed.description = f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Step 1:** Join our [ROBLOX game](https://www.roblox.com/games/11747455621/Verification)\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Step 2:** Wait to be kicked in-game.\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Step 3:** Click on the **Done** button!"

                    embed.set_author(
                        name=ctx.author.name,
                        icon_url=ctx.author.display_avatar.url,
                    )
                    view = Verification(ctx.author.id)
                    await ctx.reply(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** one last step! Join our verification game.",
                        embed=embed,
                        view=view,
                    )
                    await view.wait()
                    if view.value:
                        if view.value == "done":
                            new_data = await bot.verification.find_by_id(ctx.author.id)
                           # #print(new_data)
                            if "isVerified" in new_data.keys():
                                if new_data["isVerified"] is True:
                                    return await after_verified(roblox_user)
                                else:
                                    await ctx.reply(
                                        f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** it doesn't look like you verified! Try again."
                                    )
                                    return await run_pathway()

                        else:
                            await ctx.reply(
                                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** it doesn't look like you verified! Try again."
                            )
                            return await run_pathway()

            await run_pathway()

    # @link.group(
    #     name="fivem",
    #     description="Link your FiveM subsidiaries to ERM.",
    #     extras={
    #         "category": "Game Sync"
    #     },
    #     usage="link fivem"
    # )
    # async def fivem(self, ctx: commands.Context):
    #     pass
    #
    # @fivem.command(
    #     name="account",
    #     description="Link your FiveM account to ERM.",
    #     extras={
    #         "category": "Game Sync",
    #         "ephemeral": True
    #     },
    #     usage="link fivem account"
    # )
    # async def fivem_account(self, ctx: commands.Context):
    #
    #     verification = await self.bot.link_strings.find_one({
    #         "user": ctx.author.id,
    #         "type": "user"
    #     })
    #
    #
    #
    #     embed = discord.Embed(
    #         title="<:SyncIcon:1071821068551073892> FiveM Account Linking",
    #         description=f"<:ArrowRight:1035003246445596774> To link your FiveM account, join a server with the ERM Systems plugin and execute the following command:\n\n",
    #         color=0xED4348,
    #     )


async def setup(bot):
    await bot.add_cog(GameSync(bot))
