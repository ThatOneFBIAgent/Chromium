import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from datetime import datetime

class TimeoutUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.communication_disabled_until == after.communication_disabled_until:
            return

        if after.communication_disabled_until:
            until = after.communication_disabled_until.strftime("%Y-%m-%d %H:%M:%S")
            title = "Member Timed Out"
            desc = f"{after.mention} was timed out until {until}"
        else:
            title = "Timeout Removed"
            desc = f"Timeout removed for {after.mention}"

        embed = EmbedBuilder.warning(
            title=title,
            description=desc
        )

        await self.log_event(after.guild, embed)

async def setup(bot):
    await bot.add_cog(TimeoutUpdate(bot))
