import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class NicknameUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # We want to track NICKNAME changes, which are reflected in .nick not .display_name
        if before.nick == after.nick:
            return
        
        if not await self.should_log(before.guild, user=before):
            return    
        
        embed = EmbedBuilder.build(
            title="Nickname Changed",
            description=f"{after.mention} changed nickname.",
            fields=[
                ("Before", before.nick, True),
                ("After", after.nick, True)
            ]
        )

        await self.log_event(after.guild, embed)

async def setup(bot):
    await bot.add_cog(NicknameUpdate(bot))
