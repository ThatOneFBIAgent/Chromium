import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class ChannelUpdate(BaseLogger):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        # Queue for position updates: guild_id -> list of (before_channel, after_channel)
        self._pos_update_queue = {}
        self._processing_guilds = set()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not await self.should_log(channel.guild, channel=channel):
            return    
        
        embed = EmbedBuilder.success(
            title="Channel Created",
            description=f"Channel {channel.mention} (`{channel.name}`) was created."
        )
        await self.log_event(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not await self.should_log(channel.guild, channel=channel):
            return    
        
        embed = EmbedBuilder.error(
            title="Channel Deleted",
            description=f"Channel `{channel.name}` was deleted."
        )
        await self.log_event(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if not await self.should_log(before.guild, channel=before):
            return

        fields = []

        # --- Universal changes (all channel types) ---
        if before.name != after.name:
            fields.append(("Name", f"`{before.name}` → `{after.name}`", False))

        if before.category != after.category:
            before_cat = before.category.name if before.category else "No Category"
            after_cat = after.category.name if after.category else "No Category"
            fields.append(("Category", f"`{before_cat}` → `{after_cat}`", False))

        if before.position != after.position:
            fields.append(("Position", f"`{before.position}` → `{after.position}`", False))

        # Permission overwrites diff
        before_overwrites = before.overwrites
        after_overwrites = after.overwrites

        all_targets = set(before_overwrites) | set(after_overwrites)
        perm_changes = []

        for target in all_targets:
            b_overwrite = before_overwrites.get(target, discord.PermissionOverwrite())
            a_overwrite = after_overwrites.get(target, discord.PermissionOverwrite())

            b_allow, b_deny = b_overwrite.pair()
            a_allow, a_deny = a_overwrite.pair()

            if b_allow == a_allow and b_deny == a_deny:
                continue

            target_name = target.name if hasattr(target, "name") else str(target)
            target_type = "Role" if isinstance(target, discord.Role) else "Member"

            added_allow = discord.Permissions(a_allow.value & ~b_allow.value)
            removed_allow = discord.Permissions(b_allow.value & ~a_allow.value)
            added_deny = discord.Permissions(a_deny.value & ~b_deny.value)
            removed_deny = discord.Permissions(b_deny.value & ~a_deny.value)

            change_lines = []
            for perm, val in added_allow:
                if val:
                    change_lines.append(f"✅ `{perm}` allowed")
            for perm, val in removed_allow:
                if val:
                    change_lines.append(f"➖ `{perm}` allow removed")
            for perm, val in added_deny:
                if val:
                    change_lines.append(f"❌ `{perm}` denied")
            for perm, val in removed_deny:
                if val:
                    change_lines.append(f"➖ `{perm}` deny removed")

            if change_lines:
                perm_changes.append(f"**{target_type}: {target_name}**\n" + "\n".join(change_lines))

        if perm_changes:
            chunk = ""
            for entry in perm_changes:
                if len(chunk) + len(entry) + 2 > 1024:
                    fields.append(("Permission Changes", chunk.strip(), False))
                    chunk = ""
                chunk += entry + "\n\n"
            if chunk:
                fields.append(("Permission Changes", chunk.strip(), False))

        # --- Text channel specific ---
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic:
                b_topic = before.topic or "*None*"
                a_topic = after.topic or "*None*"
                fields.append(("Topic", f"**Before:** {b_topic}\n**After:** {a_topic}", False))

            if before.slowmode_delay != after.slowmode_delay:
                fields.append(("Slowmode", f"`{before.slowmode_delay}s` → `{after.slowmode_delay}s`", True))

            if before.nsfw != after.nsfw:
                fields.append(("NSFW", f"`{before.nsfw}` → `{after.nsfw}`", True))

            if before.default_auto_archive_duration != after.default_auto_archive_duration:
                fields.append(("Auto-Archive Duration", f"`{before.default_auto_archive_duration}m` → `{after.default_auto_archive_duration}m`", True))

        # --- Voice channel specific ---
        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if before.bitrate != after.bitrate:
                fields.append(("Bitrate", f"`{before.bitrate // 1000}kbps` → `{after.bitrate // 1000}kbps`", True))

            if before.user_limit != after.user_limit:
                b_limit = str(before.user_limit) if before.user_limit else "Unlimited"
                a_limit = str(after.user_limit) if after.user_limit else "Unlimited"
                fields.append(("User Limit", f"`{b_limit}` → `{a_limit}`", True))

            if before.rtc_region != after.rtc_region:
                b_region = before.rtc_region or "Auto"
                a_region = after.rtc_region or "Auto"
                fields.append(("Region Override", f"`{b_region}` → `{a_region}`", True))

            if before.video_quality_mode != after.video_quality_mode:
                fields.append(("Video Quality", f"`{before.video_quality_mode}` → `{after.video_quality_mode}`", True))

        # --- Forum channel specific ---
        elif isinstance(before, discord.ForumChannel) and isinstance(after, discord.ForumChannel):
            if before.topic != after.topic:
                b_topic = before.topic or "*None*"
                a_topic = after.topic or "*None*"
                fields.append(("Guidelines", f"**Before:** {b_topic}\n**After:** {a_topic}", False))

            if before.slowmode_delay != after.slowmode_delay:
                fields.append(("Slowmode", f"`{before.slowmode_delay}s` → `{after.slowmode_delay}s`", True))

            if before.default_reaction_emoji != after.default_reaction_emoji:
                b_emoji = str(before.default_reaction_emoji) if before.default_reaction_emoji else "*None*"
                a_emoji = str(after.default_reaction_emoji) if after.default_reaction_emoji else "*None*"
                fields.append(("Default Reaction", f"{b_emoji} → {a_emoji}", True))

        if not fields:
            return

        # --- Handle noisy position changes (ripples) ---
        # If ONLY the position changed, it might be a ripple from another channel 
        # being moved. We'll debounce these and check audit logs to find the "active" mover.
        if len(fields) == 1 and fields[0][0] == "Position":
            await self._queue_position_update(before, after)
            return

        embed = EmbedBuilder.warning(
            title="Channel Updated",
            description=f"Channel {after.mention} (`{after.id}`) was updated.",
            fields=fields
        )
        await self.log_event(before.guild, embed)

    async def _queue_position_update(self, before, after):
        """Queues a position change for debounced processing via audit logs."""
        guild_id = before.guild.id
        if guild_id not in self._pos_update_queue:
            self._pos_update_queue[guild_id] = []
        
        self._pos_update_queue[guild_id].append((before, after))

        if guild_id in self._processing_guilds:
            return

        self._processing_guilds.add(guild_id)
        
        # Wait for all ripple events to arrive (Discord usually sends them in a burst)
        import asyncio
        await asyncio.sleep(1.5)
        
        updates = self._pos_update_queue.pop(guild_id, [])
        self._processing_guilds.remove(guild_id)
        
        if not updates:
            return

        # Fetch recent audit logs to identify the "real" movers
        # A single move usually generates ONE audit log entry for the target channel.
        # Ripples do NOT generate audit log entries.
        try:
            # We look for CHANNEL_UPDATE entries
            audit_logs = [
                entry async for entry in before.guild.audit_logs(
                    limit=min(20, len(updates) + 5), 
                    action=discord.AuditLogAction.channel_update
                )
            ]
        except discord.errors.Forbidden:
            # If we can't see audit logs, we'll log them all as a fallback 
            # (though this may flood, it's safer than losing data if bot perm is missing)
            audit_logs = None
        except Exception:
            audit_logs = None

        for b, a in updates:
            should_log = False
            
            if audit_logs is None:
                # Fallback: if we can't verify, log it
                should_log = True
            else:
                # Find if this channel has a corresponding audit log entry with a position change
                for entry in audit_logs:
                    if entry.target and entry.target.id == a.id:
                        # Inspect the audit log differences
                        if hasattr(entry.after, "position"):
                            should_log = True
                            break
            
            if should_log:
                # Re-check should_log settings just in case
                if not await self.should_log(a.guild, channel=a):
                    continue

                embed = EmbedBuilder.warning(
                    title="Channel Moved",
                    description=f"Channel {a.mention} (`{a.id}`) position changed.",
                    fields=[("Position", f"`{b.position}` → `{a.position}`", True)]
                )
                await self.log_event(a.guild, embed)
        
async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelUpdate(bot))
