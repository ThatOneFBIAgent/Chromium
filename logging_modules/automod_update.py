import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class AutoModUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_auto_moderation_rule_create(self, rule):
        embed = EmbedBuilder.success(
            title="AutoMod Rule Created",
            description=f"Rule **{rule.name}** was created.",
            fields=[
                ("Creator", rule.creator.mention if rule.creator else "Unknown", True),
                ("Trigger Type", rule.trigger_type.name, True)
            ]
        )
        await self.log_event(rule.guild, embed)

    @commands.Cog.listener()
    async def on_auto_moderation_rule_delete(self, rule):
        embed = EmbedBuilder.error(
            title="AutoMod Rule Deleted",
            description=f"Rule **{rule.name}** was deleted."
        )
        await self.log_event(rule.guild, embed)

    @commands.Cog.listener()
    async def on_auto_moderation_rule_update(self, rule):
        embed = EmbedBuilder.warning(
            title="AutoMod Rule Updated",
            description=f"Rule **{rule.name}** was updated."
        )
        await self.log_event(rule.guild, embed)

    @commands.Cog.listener()
    async def on_auto_moderation_action_execution(self, payload):

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        user = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)

        if not await self.should_log(guild, user=user):
            return

        trigger = payload.matched_keyword or payload.rule_trigger_type.name

        description = f"**User:** {user.mention if user else payload.user_id}\n"

        if channel:
            description += f"**Channel:** {channel.mention}\n"

        description += f"**Trigger:** {trigger}\n"

        if payload.content:
            content = payload.content
            if len(content) > 1000:
                content = content[:1000] + "..."
            description += f"\n**Content:**\n{content}"

        embed = EmbedBuilder.error(
            title="AutoMod Action Executed",
            description=description,
            footer=f"Rule ID: {payload.rule_id}"
        )

        await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModUpdate(bot))
