import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class WebhookUpdate(BaseLogger):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self._webhook_cache = {}

    def _snapshot(self, webhooks: list[discord.Webhook]):
        """
        Turn webhook objects into a simple comparable dict
        """
        return {
            wh.id: {
                "name": wh.name,
                "type": str(wh.type),
                "url": wh.url if wh.type is discord.WebhookType.incoming else None,
                "avatar": wh.avatar.url if wh.avatar else None,
                "channel_id": wh.channel_id,
                "guild_id": wh.guild_id,
                "application_id": wh.application_id,
                "user_id": wh.user.id if wh.user else None,
            }
            for wh in webhooks
        }

    def _diff_webhooks(self, before: dict, after: dict):
        before_ids = set(before.keys())
        after_ids = set(after.keys())

        created = after_ids - before_ids
        deleted = before_ids - after_ids
        possible_updates = before_ids & after_ids

        updated = {}

        for wid in possible_updates:
            if before[wid] != after[wid]:
                updated[wid] = {
                    "before": before[wid],
                    "after": after[wid],
                }

        return {
            "created": {wid: after[wid] for wid in created},
            "deleted": {wid: before[wid] for wid in deleted},
            "updated": updated,
        }

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        guild = channel.guild

        cache_key = (guild.id, channel.id)

        # get previous state, fetch curr state and then diff
        before = self._webhook_cache.get(cache_key, {})
        webhooks = await channel.webhooks()
        after = self._snapshot(webhooks)
        diff = self._diff_webhooks(before, after)

        # update cache immediately so we don't brick ourselves
        self._webhook_cache[cache_key] = after

        if not any(diff.values()):
            # nothing changed, Discord just sneezed
            return

        parts = []

        if diff["created"]:
            parts.append("Created:\n" + "\n".join(
                f"- `{d['name']}` (id={wid})"
                for wid, d in diff["created"].items()
            ))

        if diff["deleted"]:
            parts.append("Deleted:\n" + "\n".join(
                f"- `{d['name']}` (id={wid})"
                for wid, d in diff["deleted"].items()
            ))

        if diff["updated"]:
            parts.append("Updated:\n" + "\n".join(
                f"- `{b['before']['name']}` (id={wid})"
                for wid, b in diff["updated"].items()
            ))

        description = "\n\n".join(parts)

        embed = EmbedBuilder.warning(
            title=f"Webhooks changed in {channel.mention}",
            description=description
        )

        await self.log_event(guild, embed)

async def setup(bot):
    await bot.add_cog(WebhookUpdate(bot))
