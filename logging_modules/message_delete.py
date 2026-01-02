import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.suspicious import suspicious_detector

class MessageDelete(BaseLogger):
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not await self.should_log(message.guild, message.author, message.channel):
            return

        if message.author.bot:
            footer = " | (Bot)"

        if not message.guild:
            return

        # Suspicious check
        is_suspicious = suspicious_detector.check_message_delete(message.guild.id, message.author.id)
        
        description = f"**Message sent by {message.author.mention} deleted in {message.channel.mention}**\n"
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
        
        # Try to find who purged via Audit Log
        executor = None
        reason = None
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
                # We can't perfectly match, but if it happened just now, it's likely this one
                # Checking target channel might help, but bulk delete entry structure is specific
                if entry.extra.count == count and entry.target.id == channel.id:
                    executor = entry.user
                    reason = entry.reason
                    break
        except discord.Forbidden:
            pass

        description = f"**{count} messages were bulk deleted in {channel.mention}**"
        
        embed = EmbedBuilder.error(
            title="Bulk Message Delete",
            description=description,
            footer=f"Channel ID: {channel.id}",
            fields=[]
        )
        
        if executor:
            embed.add_field(name="Purged By", value=executor.mention, inline=True)
        if reason:
             embed.add_field(name="Reason", value=reason, inline=True)
            
        # TODO: Save deleted contents (or what we can scrape) to a text file 
        
        await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MessageDelete(bot))
