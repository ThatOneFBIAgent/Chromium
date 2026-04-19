import discord
import asyncio
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.suspicious import suspicious_detector
from database.queries import get_guild_settings

class MessageDelete(BaseLogger):
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not await self.should_log(message.guild, message.author, message.channel):
            return

        if message.author.bot:
            footer = " | (Bot)"
        else:
            footer = ""

        if not message.guild:
            return

        # Check if it was in a log channel
        is_log_channel = False
        try:
            res = await get_guild_settings(message.guild.id)
            if res and res[0]:
                log_channels = {res[0], res[1], res[2]}
                if message.channel.id in log_channels:
                    is_log_channel = True
        except Exception:
            pass

        executor = None
        # Try to find who deleted it via Audit Log
        # If a user deletes someone else's message, it creates an Audit Log entry.
        # This is especially useful if an admin deletes a log message sent by the bot.
        try:
            await asyncio.sleep(0.5) # Give the audit log a moment to populate
            async for entry in message.guild.audit_logs(limit=3, action=discord.AuditLogAction.message_delete):
                if hasattr(entry.extra, "channel") and entry.extra.channel.id == message.channel.id:
                    # In log channels, webhook authors cause target ID mismatches in the API, 
                    # so we loosen the check to rely on the channel & timestamp instead.
                    target_match = getattr(entry.target, "id", None) == message.author.id
                    
                    if is_log_channel or target_match:
                        # Verify it happened recently (within 10 seconds)
                        if abs((discord.utils.utcnow() - entry.created_at).total_seconds()) < 10:
                            executor = entry.user
                            break
        except Exception:
            pass

        # Suspicious check
        is_suspicious = suspicious_detector.check_message_delete(message.guild.id, message.author.id)
        
        if is_log_channel:
            is_suspicious = True
            description = f"**⚠️ WARNING: Log entry deleted in {message.channel.mention}**\n"
        else:
            description = f"**Message sent by {message.author.mention} deleted in {message.channel.mention}**\n"
            
        if executor:
            description += f"\n**Deleted By:** {executor.mention} (`{executor.id}`)\n"

        if message.content:
            description += f"\n**Content:**\n{message.content}"
        
        # Attachments
        def format_attachments(attachments):
            lines = []
            for a in attachments:
                size_kb = round(a.size / 1024, 2)
                spoiler = " (spoiler)" if a.is_spoiler() else ""
                lines.append(
                    f"- `{a.filename}` ({size_kb} KB){spoiler}\n{a.url}"
                )
            return "\n".join(lines)

        if message.attachments:
            description += "\n\n**Attachments:**\n"
            description += format_attachments(message.attachments)

        embed = EmbedBuilder.error(
            title="Message Deleted",
            description=description,
            author=message.author,
            footer=f"User ID: {message.author.id} | Message ID: {message.id}{footer}"
        )
        
        await self.log_event(message.guild, embed, suspicious=is_suspicious)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        if not messages:
            return
            
        channel = messages[0].channel
        guild = channel.guild
        count = len(messages)
        
        is_log_channel = False
        try:
            res = await get_guild_settings(guild.id)
            if res and res[0]:
                log_channels = {res[0], res[1], res[2]}
                if channel.id in log_channels:
                    is_log_channel = True
        except Exception:
            pass

        # Try to find who purged via Audit Log
        executor = None
        reason = None
        try:
            await asyncio.sleep(0.5) # Give audit log a moment
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.message_bulk_delete):
                if entry.extra.count == count and entry.target.id == channel.id:
                    if (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                        executor = entry.user
                        reason = entry.reason
                        break
        except discord.Forbidden:
            pass

        if is_log_channel:
            description = f"**⚠️ WARNING: {count} log entries were bulk deleted in {channel.mention}**"
        else:
            description = f"**{count} messages were bulk deleted in {channel.mention}**"
        
        isbot = " | Bot" if executor and executor.bot else ""

        embed = EmbedBuilder.error(
            title="Bulk Message Delete",
            description=description,
            footer=f"Channel ID: {channel.id}{isbot}",
            fields=[]
        )
        
        if executor:
            embed.add_field(name="Purged By", value=executor.mention, inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=True)
            
        # There was a todo here but due to limitations (and my inability to do shit right) it will not be implemented
        
        await self.log_event(guild, embed, suspicious=is_log_channel)

async def setup(bot: commands.Bot):
    await bot.add_cog(MessageDelete(bot))