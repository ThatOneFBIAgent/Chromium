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
    await bot.add_cog(MessageEdit(bot))                else:
                    for line in before_lines[max(i2 - context, i1 + context):i2]:
                        current_hunk.append(f"  {line}")
            else:
                last_end = i2
        else:
            if not current_hunk:
                ctx_start = max((last_end or 0), i1 - context)
                if ctx_start < i1:
                    if ctx_start > 0:
                        current_hunk.append("  ...")
                    for line in before_lines[ctx_start:i1]:
                        current_hunk.append(f"  {line}")

            if tag in ("replace", "delete"):
                for line in before_lines[i1:i2]:
                    current_hunk.append(f"- {line}")
            if tag in ("replace", "insert"):
                for line in after_lines[j1:j2]:
                    current_hunk.append(f"+ {line}")

    if current_hunk:
        hunks.append(current_hunk)

    if not hunks:
        return ""

    all_lines = []
    for i, hunk in enumerate(hunks):
        if i > 0:
            all_lines.append("  ...")
        all_lines.extend(hunk)

    return "```diff\n" + "\n".join(all_lines) + "\n```"


def _split_to_fields(content: str, limit: int = FIELD_LIMIT, max_fields: int = 3) -> list[str]:
    fields = []
    remaining = content
    for _ in range(max_fields):
        if len(remaining) <= limit:
            fields.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        fields.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    else:
        if remaining:
            fields[-1] = fields[-1][:-1] + "…"
    return fields


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
        after_files  = {a.filename for a in after.attachments}
        removed = before_files - after_files

        if removed:
            embed = EmbedBuilder.warning(
                title="Message Attachment Removed",
                description=(
                    f"Attachment removed from a message in {after.channel.mention} "
                    f"[Jump to Message]({after.jump_url})"
                ),
                fields=[("Removed Files", "\n".join(removed), False)],
                author=after.author,
                footer=f"User ID: {after.author.id} | Message ID: {after.id}",
            )
            await self.log_event(after.guild, embed, suspicious=True)
            if before.content == after.content:
                return

        if before.content == after.content:
            return

        is_suspicious = suspicious_detector.check_message_edit(
            before.guild.id, before.author.id
        )

        before_text = before.content or ""
        after_text  = after.content  or ""

        diff = _build_diff_hunks(before_text, after_text)

        description = (
            f"**Message edited in {before.channel.mention}** "
            f"[Jump to Message]({after.jump_url})"
        )

        fields = []

        if diff:
            diff_chunks = _split_to_fields(diff)
            for i, chunk in enumerate(diff_chunks):
                label = "Changes (cont.)" if i else "Changes"
                fields.append((label, chunk, False))
        else:
            fields.append(("Before", f"```\n{_truncate(before_text)}\n```", False))
            fields.append(("After",  f"```\n{_truncate(after_text)}\n```",  False))

        embed = EmbedBuilder.warning(
            title="Message Edited",
            description=description,
            author=before.author,
            footer=f"User ID: {before.author.id} | Message ID: {before.id}",
            fields=fields,
        )

        await self.log_event(before.guild, embed, suspicious=is_suspicious)


async def setup(bot):
    await bot.add_cog(MessageEdit(bot))
