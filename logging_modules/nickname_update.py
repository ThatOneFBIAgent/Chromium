import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class NicknameUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_name = before.nick or before.name
        after_name = after.nick or after.name

        if before_name == after_name:
            return

        embed = EmbedBuilder.info(
            title="Nickname Changed",
            description=f"{after.mention} changed nickname.",
            fields=[
                ("Before", before_name, True),
                ("After", after_name, True)
            ]
        )

        await self.log_event(after.guild, embed)

async def setup(bot):
    await bot.add_cog(NicknameUpdate(bot))
