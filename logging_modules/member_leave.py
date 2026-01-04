import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class MemberLeave(BaseLogger):
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not await self.should_log(member.guild, user=member):
            return    
        
        guild = member.guild
        
        description = f"{member.mention} {member.name} has left the server."
        
        # TODO: truncate to 20 roles or 3000 characters otherwise we get 403's lmao
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        roles = ", ".join(roles)
        
        embed = EmbedBuilder.error(
            title="Member Left",
            description=description,
            author=member,
            footer=f"ID: {member.id}",
            fields=[
                ("Roles", roles, False),
                ("Member Count", str(guild.member_count), True)
            ]
        )
        
        await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberLeave(bot))
