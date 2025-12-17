import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class InviteUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        embed = EmbedBuilder.success(
            title="Invite Created",
            description=f"Invite `{invite.code}` created for {invite.channel.mention}",
            fields=[
                ("Max Uses", invite.max_uses or "Unlimited", True),
                ("Expires", invite.expires_at or "Never", True)
            ]
        )
        await self.log_event(invite.guild, embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        embed = EmbedBuilder.error(
            title="Invite Deleted",
            description=f"Invite `{invite.code}` was deleted."
        )
        await self.log_event(invite.guild, embed)

async def setup(bot):
    await bot.add_cog(InviteUpdate(bot))
