import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class RolePermissionUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.permissions == after.permissions:
            return

        changed = []
        for perm, value in before.permissions:
            if getattr(after.permissions, perm) != value:
                changed.append(f"{perm}: {value} -> {getattr(after.permissions, perm)}")

        embed = EmbedBuilder.warning(
            title="Role Permissions Changed",
            description=f"Role `{after.name}` had permissions updated.",
            fields=[
                ("Changes", "\n".join(changed) or "Unknown", False)
            ]
        )

        suspicious = "administrator" in "".join(changed).lower()
        await self.log_event(after.guild, embed, suspicious=suspicious)

async def setup(bot):
    await bot.add_cog(RolePermissionUpdate(bot))
