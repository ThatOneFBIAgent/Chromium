import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class RoleUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = EmbedBuilder.success(
            title="Role Created",
            description=f"Role {role.mention} (`{role.name}`) was created."
        )
        await self.log_event(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = EmbedBuilder.error(
            title="Role Deleted",
            description=f"Role `{role.name}` was deleted."
        )
        await self.log_event(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name == after.name and before.color == after.color and before.permissions == after.permissions:
            return 
            
        changes = []
        if before.name != after.name:
            changes.append(f"Name: `{before.name}` -> `{after.name}`")
        if before.color != after.color:
            changes.append(f"Color: `{before.color}` -> `{after.color}`")
        if before.permissions.value != after.permissions.value:
            changes.append("Permissions changed")
            
        if not changes:
            return

        embed = EmbedBuilder.warning(
            title="Role Updated",
            description=f"Role {after.mention} was updated.\n\n" + "\n".join(changes)
        )
        await self.log_event(after.guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(RoleUpdate(bot))
