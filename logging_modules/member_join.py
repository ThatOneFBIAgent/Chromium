import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.suspicious import suspicious_detector
import datetime

class MemberJoin(BaseLogger):
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        
        # Suspicious check (raid detection)
        is_suspicious = suspicious_detector.check_member_join(guild.id)
        
        # Account age calculation
        created_at = member.created_at
        now = datetime.datetime.now(datetime.timezone.utc)
        age = now - created_at
        
        is_new_account = age.days < 7
        
        description = f"{member.mention} {member.name} has joined the server."
        
        color = discord.Color.green()
        if is_suspicious or is_new_account:
            color = discord.Color.orange()
            description += "\n⚠️ **Potential Risk:** "
            if is_suspicious: description += "High join rate detected. "
            if is_new_account: description += "Account is less than 7 days old."

        embed = EmbedBuilder.build(
            title="Member Joined",
            description=description,
            color=color,
            author=member,
            footer=f"ID: {member.id}",
            fields=[
                ("Account Created", f"<t:{int(created_at.timestamp())}:R>", True),
                ("Member Count", str(guild.member_count), True)
            ]
        )
        
        await self.log_event(guild, embed, suspicious=is_suspicious)

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberJoin(bot))
