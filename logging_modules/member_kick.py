import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.suspicious import suspicious_detector
import asyncio

class MemberKick(BaseLogger):
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not await self.should_log(member.guild, user=member):
            return    
        
        await asyncio.sleep(1)

        try:
            async for entry in member.guild.audit_logs(
                limit=5,
                action=discord.AuditLogAction.kick
            ):
                if entry.target.id == member.id:
                    embed = EmbedBuilder.error(
                        title="Member Kicked",
                        description=f"{member.mention} was kicked.",
                        fields=[
                            ("By", entry.user.mention, True),
                            ("Reason", entry.reason or "No reason provided", False)
                        ]
                    )
                    
                    suspicious = suspicious_detector.check_member_kick(member.guild.id, entry.user.id)
                    await self.log_event(member.guild, embed, suspicious=suspicious)
                    return
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(MemberKick(bot))
