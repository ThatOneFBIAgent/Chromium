import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class NicknameUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # display_name handles both server nicknames and global names (if no nick is set)
        if before.display_name == after.display_name:
            return
        
        if not await self.should_log(before.guild, user=before):
            return    
        
        # Helper to format nickname display
        def get_name_display(member, nick):
            if nick:
                return f"{nick} (Nickname)"
            return f"{member.name} (Global)"

        embed = EmbedBuilder.build(
            title="Name/Nickname Changed",
            description=f"{after.mention} updated their name.",
            fields=[
                ("Before", get_name_display(before, before.nick), True),
                ("After", get_name_display(after, after.nick), True)
            ]
        )

        await self.log_event(after.guild, embed)

async def setup(bot):
    await bot.add_cog(NicknameUpdate(bot))
