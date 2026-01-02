import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class NicknameUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # We want to track NICKNAME changes, which are reflected in display_name
        # (display_name is nick if present, else name)
        
        if not await self.should_log(before.guild, user=before):
            return    
        
        if before.display_name == after.display_name:
            return

        embed = EmbedBuilder.info(
            title="Nickname Changed",
            description=f"{after.mention} changed nickname.",
            fields=[
                ("Before", before.display_name, True),
                ("After", after.display_name, True)
            ]
        )

        await self.log_event(after.guild, embed)

async def setup(bot):
    await bot.add_cog(NicknameUpdate(bot))
