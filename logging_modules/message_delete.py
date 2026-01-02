import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.suspicious import suspicious_detector

class MessageDelete(BaseLogger):
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):

        msg = payload.cached_message

        guild = None
        channel = None
        author = None
        is_bot = None

        if payload.guild_id:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                channel = guild.get_channel(payload.channel_id)

        # If message was cached, extract data
        if msg is not None:
            author = msg.author
            is_bot = author.bot

        # Decide whether to log
        author_id = author.id if author else None

        if not await self.should_log(payload.guild_id, author_id, payload.channel_id):
            return

        # Skip bot deletions if desired
        if is_bot:
            footer = "| (Bot)"
            return

        # Suspicious detector fallback
        is_suspicious = suspicious_detector.check_message_delete(payload.guild_id, author_id)

        # Build description safely
        description = ""

        if author:
            description += f"**Message sent by {author.mention} deleted"
        else:
            description += f"**Message deleted"

        if channel:
            description += f" in {channel.mention}**\n"
        else:
            description += "**\n"

        # Content if available
        if msg and msg.content:
            description += f"\n**Content:**\n{msg.content}"
        else:
            description += "\n**Content:**\nNo content available"

        # Attachments if available
        if msg and msg.attachments:
            def format_attachments(attachments):
                lines = []
                for a in attachments:
                    size_kb = round(a.size / 1024, 2)
                    spoiler = " (spoiler)" if a.is_spoiler() else ""
                    lines.append(
                        f"- `{a.filename}` ({size_kb} KB){spoiler}\n{a.url}"
                    )
                return "\n".join(lines)

            description += "\n\n**Attachments:**\n"
            description += format_attachments(msg.attachments)

        embed = EmbedBuilder.error(
            title="Message Deleted",
            description=description,
            author=author,
            footer=f"User ID: {author.id if author else 'Unknown'} "
                f"| Message ID: {payload.message_id}"
        )

        if guild:
            await self.log_event(guild, embed, suspicious=is_suspicious)

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
