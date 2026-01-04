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
        changes = []
        
        # 1. Name changes
        if before.name != after.name:
            changes.append(f"Name: `{before.name}` -> `{after.name}`")
            
        # 2. Color changes
        if before.color != after.color:
            changes.append(f"Color: `{before.color}` -> `{after.color}`")
            
        # 3. Icon changes
        if before.icon != after.icon:
             # Icons are assets, just check for presence or difference
             changes.append("Icon updated")

        # 4. Hoist (Displayed separately)
        if before.hoist != after.hoist:
            changes.append(f"Displayed separately: `{before.hoist}` -> `{after.hoist}`")

        # 5. Mentionable
        if before.mentionable != after.mentionable:
            changes.append(f"Mentionable: `{before.mentionable}` -> `{after.mentionable}`")
            
        # 6. Detailed Permission Logic
        perm_changes = []
        if before.permissions.value != after.permissions.value:
            for perm, value in before.permissions:
                if getattr(after.permissions, perm) != value:
                    # Format: administrator: True -> False
                    perm_changes.append(f"{perm}: {value} -> {getattr(after.permissions, perm)}")
            
            if perm_changes:
                # Add a header for permissions
                changes.append(f"**Permissions Changed:**\n" + "\n".join(perm_changes))

        if not changes:
            return

        suspicious = False
        # Check for dangerous permissions being granted
        if perm_changes:
            lower_perms = "".join(perm_changes).lower()
            if "administrator: false -> true" in lower_perms or "manage_guild: false -> true" in lower_perms:
               suspicious = True

        embed = EmbedBuilder.warning(
            title="Role Updated",
            description=f"Role {after.mention} was updated.\n\n" + "\n".join(changes)
        )
        await self.log_event(after.guild, embed, suspicious=suspicious)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not await self.should_log(before.guild, user=before):
             return

        if before.roles == after.roles:
            return

        # Calculate difference
        # set operations: new - old = added, old - new = removed
        new_roles = set(after.roles) - set(before.roles)
        removed_roles = set(before.roles) - set(after.roles)
        
        if not new_roles and not removed_roles:
            return

        changes = []
        for role in new_roles:
            changes.append(f"**Added:** {role.mention}")
        for role in removed_roles:
            changes.append(f"**Removed:** {role.mention}")
            
        embed = EmbedBuilder.build(
            title="Member Roles Updated",
            description=f"Roles updated for {after.mention}.\n\n" + "\n".join(changes),
            footer=f"User ID: {after.id}"
        )
        
        await self.log_event(after.guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(RoleUpdate(bot))
