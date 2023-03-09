import discord
from discord.ext import commands

from erm import is_management, generator
from menus import ManageReminders, YesNoColourMenu, YesNoMenu, ChannelSelect, RoleSelect
from utils.utils import removesuffix, invis_embed, request_response


class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="reminders")
    @is_management()
    async def reminders(self, ctx):
        pass

    @reminders.command(
        name="manage",
        description="Manage your reminders",
        extras={"category": "Reminders"},
    )
    @is_management()
    async def manage_reminders(self, ctx):
        bot = self.bot
        Data = await bot.reminders.find_by_id(ctx.guild.id)
        if Data is None:
            Data = {"_id": ctx.guild.id, "reminders": []}

        embed = discord.Embed(
            title="<:Resume:1035269012445216858> Manage reminders", color=0x2E3136
        )
        for item in Data["reminders"]:
            if len(item["message"]) > 800:
                embed.add_field(
                    name=f"<:Clock:1035308064305332224> {item['name']}",
                    value=f"<:ArrowRightW:1035023450592514048> **Interval:** {item['interval']} seconds\n<:ArrowRightW:1035023450592514048> **Able to be Completed:** {str(item.get('completion_ability')) if item.get('completion_ability') else 'False'}\n<:ArrowRightW:1035023450592514048> **Channel:** {item['channel']}\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}\n<:ArrowRightW:1035023450592514048> **Last Completed:** <t:{int(item['lastTriggered'])}>",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"<:Clock:1035308064305332224> {item['name']}",
                    value=f"<:ArrowRightW:1035023450592514048> **Interval:** {item['interval']} seconds\n<:ArrowRightW:1035023450592514048> **Able to be Completed:** {str(item.get('completion_ability')) if item.get('completion_ability') else 'False'}\n<:ArrowRightW:1035023450592514048> **Channel:** {item['channel']}\n<:ArrowRightW:1035023450592514048> **Message:** `{item['message']}`\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}\n<:ArrowRightW:1035023450592514048> **Last Completed:** <t:{int(item['lastTriggered'])}>",
                    inline=False,
                )

        if len(embed.fields) == 0:
            embed.add_field(
                name="<:Clock:1035308064305332224> No reminders",
                value="<:ArrowRightW:1035023450592514048> No reminders have been added.",
                inline=False,
            )

        view = ManageReminders(ctx.author.id)

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.value == "create":
            if view.modal:
                timeout = await view.modal.wait()
                if timeout:
                    return

                time = view.modal.time.value
                message = view.modal.content.value
                name = view.modal.name.value

                if time.lower().endswith("s"):
                    time = int(removesuffix(time.lower(), "s"))
                elif time.lower().endswith("m"):
                    time = int(removesuffix(time.lower(), "m")) * 60
                elif time.lower().endswith("h"):
                    time = int(removesuffix(time.lower(), "h")) * 60 * 60
                elif time.lower().endswith("d"):
                    time = int(removesuffix(time.lower(), "d")) * 60 * 60 * 24
                elif time.lower().endswith("w"):
                    time = int(removesuffix(time.lower(), "w")) * 60 * 60 * 24 * 7
                else:
                    return await invis_embed(
                        ctx, "You have not provided a correct suffix. (s/m/h/d)"
                    )

                view = YesNoColourMenu(ctx.author.id)

                embed = discord.Embed(
                    title="<:Resume:1035269012445216858> Reminder Completion",
                    description="Should this reminder be able to be completed? Once it's completed, the embed will be edited appropriately to reflect this.",
                    color=0x2E3136,
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                completed = view.value

                view = ChannelSelect(ctx.author.id, limit=1)
                embed = discord.Embed(
                    title="<:Resume:1035269012445216858> Select a channel",
                    description="Please select a channel for the reminder to be sent in.",
                    color=0x2E3136,
                )
                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                channel = view.value[0] if view.value else None
                if not channel:
                    return await invis_embed(
                        ctx,
                        "You have not selected a channel. A channel is required for for reminder creation.",
                    )

                view = YesNoMenu(ctx.author.id)

                embed = discord.Embed(
                    title="<:Resume:1035269012445216858> Mentioning a Role",
                    description="Do you want a role to be mentioned?",
                    color=0x2E3136,
                )

                await ctx.send(embed=embed, view=view)
                roleObject = None
                timeout = await view.wait()
                if view.value == True:
                    view = RoleSelect(ctx.author.id)
                    embed = discord.Embed(
                        title="<:Resume:1035269012445216858> Select a role",
                        description="Please select a role to be mentioned.",
                        color=0x2E3136,
                    )
                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return
                    roleObject = view.value

                if roleObject:
                    Data["reminders"].append(
                        {
                            "id": next(generator),
                            "name": name,
                            "interval": time,
                            "completion_ability": completed,
                            "message": message,
                            "channel": channel.id,
                            "role": [role.id for role in roleObject]
                            if roleObject
                            else [],
                            "lastTriggered": 0,
                        }
                    )
                else:
                    Data["reminders"].append(
                        {
                            "id": next(generator),
                            "name": name,
                            "interval": time,
                            "completion_ability": completed,
                            "message": message,
                            "channel": channel.id,
                            "role": 0,
                            "lastTriggered": 0,
                        }
                    )
                await bot.reminders.upsert(Data)
                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Reminder Added",
                    description="<:ArrowRight:1035003246445596774> Your reminder has been added successfully.",
                    color=0x71C15F,
                )

                await ctx.send(embed=successEmbed)

        elif view.value == "delete":
            name = (
                await request_response(
                    bot,
                    ctx,
                    "What reminder would you like to delete? (e.g. `1`)\n*Specify the ID to delete the reminder.*",
                )
            ).content

            try:
                for item in Data["reminders"]:
                    if item["id"] == int(name):
                        Data["reminders"].remove(item)
                        await bot.reminders.upsert(Data)
                        successEmbed = discord.Embed(
                            title="<:CheckIcon:1035018951043842088> Reminder Removed",
                            description="<:ArrowRight:1035003246445596774> Your reminder has been removed successfully.",
                            color=0x71C15F,
                        )

                        return await ctx.send(embed=successEmbed)
            except:
                return await invis_embed(
                    ctx,
                    "You have not provided a correct ID. Please try again with an ID from the list.",
                )


async def setup(bot):
    await bot.add_cog(Reminders(bot))
