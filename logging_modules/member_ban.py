import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class MemberBan(BaseLogger):
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        # Initial Embed
        description = f"{user.mention} (`{user.name}`) has been banned."
        
        embed = EmbedBuilder.error(
            title="Member Banned",
            description=description,
            author=user,
            footer=f"ID: {user.id}"
        )
        
        # Enriched Audit Log Lookup
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target and entry.target.id == user.id:
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                    embed.add_field(name="Banned By", value=entry.user.mention, inline=True)
                    break
        except discord.Forbidden:
            pass # Missing permission to view audit logs
            
        await self.log_event(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        description = f"{user.mention} (`{user.name}`) has been unbanned."
        
        embed = EmbedBuilder.success(
            title="Member Unbanned",
            description=description,
            author=user,
            footer=f"ID: {user.id}"
        )

        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                if entry.target and entry.target.id == user.id:
                    embed.add_field(name="Unbanned By", value=entry.user.mention, inline=True)
                    break
        except discord.Forbidden:
            pass
            
        await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberBan(bot))
