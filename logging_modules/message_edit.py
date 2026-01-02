import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.suspicious import suspicious_detector

class MessageEdit(BaseLogger):
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return

        if not before.guild:
            return

        if not await self.should_log(before.guild, before.author, before.channel):
            return    

        before_files = {a.filename for a in before.attachments}
        after_files = {a.filename for a in after.attachments}

        removed = before_files - after_files
        if removed:
            embed = EmbedBuilder.warning(
                title="Message Attachment Removed",
                description=f"Attachment removed from a message in {after.channel.mention}",
                fields=[
                    ("Removed Files", "\n".join(removed), False)
                ],
                author=after.author,
                footer=f"User ID: {after.author.id} | Message ID: {after.id}"
            )

            await self.log_event(after.guild, embed, suspicious=True)

            # if only attachments changed, stop here
            if before.content == after.content:
                return

        # content didnt change, nothing else to log
        if before.content == after.content:
            return

        is_suspicious = suspicious_detector.check_message_edit(
            before.guild.id,
            before.author.id
        )

        description = (
            f"**Message edited in {before.channel.mention}** "
            f"[Jump to Message]({after.jump_url})"
        )

        embed = EmbedBuilder.warning(
            title="Message Edited",
            description=description,
            author=before.author,
            footer=f"User ID: {before.author.id} | Message ID: {before.id}",
            fields=[
                ("Before", before.content or "*Empty*", False),
                ("After", after.content or "*Empty*", False)
            ]
        )

        await self.log_event(before.guild, embed, suspicious=is_suspicious)

async def setup(bot):
    await bot.add_cog(MessageEdit(bot))