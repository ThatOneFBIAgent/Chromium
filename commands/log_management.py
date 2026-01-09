import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from database.queries import get_guild_settings, upsert_guild_settings
from utils.embed_builder import EmbedBuilder
from utils.permissions import MODULE_PERMISSIONS, PERMISSION_DISPLAY_NAMES

# List of all available modules for autocomplete/validation
MODULES = [
    "MessageDelete", "MessageEdit", "MemberJoin", "MemberLeave", 
    "VoiceState", "RoleUpdate", "ChannelUpdate", "ErrorLogger",
    "MemberBan", "GuildUpdate", "EmojiUpdate", "MemberKick", "NicknameUpdate",
    "TimeoutUpdate", "WebhookUpdate", "InviteUpdate", "AutoModUpdate"
]

# Module information for /log info command
MODULE_INFO = {
    "MessageDelete": {
        "description": "Logs when messages are deleted, including content, author, and attachments.",
        "events": ["on_message_delete", "on_bulk_message_delete"],
        "channel": "message-logs"
    },
    "MessageEdit": {
        "description": "Logs when messages are edited, showing before/after content.",
        "events": ["on_message_edit"],
        "channel": "message-logs"
    },
    "MemberJoin": {
        "description": "Logs when new members join the server, including account age.",
        "events": ["on_member_join"],
        "channel": "member-logs"
    },
    "MemberLeave": {
        "description": "Logs when members leave the server, showing their roles.",
        "events": ["on_member_remove"],
        "channel": "member-logs"
    },
    "VoiceState": {
        "description": "Logs voice channel activity: joins, leaves, moves, mutes, and deafens.",
        "events": ["on_voice_state_update"],
        "channel": "member-logs"
    },
    "RoleUpdate": {
        "description": "Logs role changes: creation, deletion, and modifications (name, color, permissions).",
        "events": ["on_guild_role_create", "on_guild_role_delete", "on_guild_role_update", "on_member_update"],
        "channel": "server-logs"
    },
    "ChannelUpdate": {
        "description": "Logs channel changes: creation, deletion, and modifications.",
        "events": ["on_guild_channel_create", "on_guild_channel_delete", "on_guild_channel_update"],
        "channel": "server-logs"
    },
    "ErrorLogger": {
        "description": "Logs command errors and sends user-friendly error messages.",
        "events": ["on_command_error", "on_app_command_error"],
        "channel": "N/A"
    },
    "MemberBan": {
        "description": "Logs when members are banned or unbanned, with executor from audit log.",
        "events": ["on_member_ban", "on_member_unban"],
        "channel": "member-logs"
    },
    "GuildUpdate": {
        "description": "Logs server setting changes (name, icon, verification level, etc.).",
        "events": ["on_guild_update"],
        "channel": "server-logs"
    },
    "EmojiUpdate": {
        "description": "Logs emoji additions, removals, and changes.",
        "events": ["on_guild_emojis_update"],
        "channel": "server-logs"
    },
    "MemberKick": {
        "description": "Logs kick events using audit log to identify the executor.",
        "events": ["on_member_remove"],
        "channel": "member-logs"
    },
    "NicknameUpdate": {
        "description": "Logs when members change their nicknames.",
        "events": ["on_member_update"],
        "channel": "member-logs"
    },
    "TimeoutUpdate": {
        "description": "Logs when members are timed out or timeout is removed.",
        "events": ["on_member_update"],
        "channel": "member-logs"
    },
    "WebhookUpdate": {
        "description": "Logs webhook creation, deletion, and modifications.",
        "events": ["on_webhooks_update"],
        "channel": "server-logs"
    },
    "InviteUpdate": {
        "description": "Logs invite creation and deletion.",
        "events": ["on_invite_create", "on_invite_delete"],
        "channel": "server-logs"
    },
    "AutoModUpdate": {
        "description": "Logs AutoMod rule changes and action executions.",
        "events": ["on_auto_moderation_rule_create", "on_auto_moderation_rule_delete", "on_auto_moderation_action_execution"],
        "channel": "server-logs"
    }
}

class LogManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    log_group = app_commands.Group(name="log", description="Manage logging modules")

    @log_group.command(name="list", description="List all modules and their status")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 40, key=lambda i: (i.guild_id, i.user.id))
    async def list_modules(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        # Unpack all 9 values
        res = await get_guild_settings(interaction.guild_id)
        if not res or not res[0]: # Check if log_id is set
             await interaction.followup.send(
                embed=EmbedBuilder.error("Not Configured", "This server does not have Chromium configured! Run `/setup` first.")
            )
             return
             
        # Extract enabled_modules (last item in 7-value tuple)
        enabled_modules = res[6] 


        status_text = ""
        for module in MODULES:
            is_enabled = enabled_modules.get(module, False)
            icon = "✅" if is_enabled else "❌"
            status_text += f"{icon} **{module}**\n"
            
        embed = EmbedBuilder.build(
            title="Logging Modules",
            description=status_text
        )
        await interaction.followup.send(embed=embed)

    @log_group.command(name="info", description="Show detailed information about a logging module")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def module_info(self, interaction: discord.Interaction, module: str):
        if module not in MODULES:
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    "Module Not Found",
                    f"`{module}` is not a valid module.\n\n**Troubleshooting:**\n• Use the autocomplete suggestions\n• Run `/log list` to see all modules"
                ),
                ephemeral=True
            )
            return
        
        info = MODULE_INFO.get(module, {})
        perms = MODULE_PERMISSIONS.get(module, [])
        
        # Format permissions
        if perms:
            perm_names = [PERMISSION_DISPLAY_NAMES.get(p, p) for p in perms]
            perm_text = ", ".join(perm_names)
        else:
            perm_text = "None required"
        
        # Format events
        events = info.get("events", [])
        events_text = ", ".join(f"`{e}`" for e in events) if events else "N/A"
        
        embed = EmbedBuilder.build(
            title=f"📋 {module}",
            description=info.get("description", "No description available."),
            fields=[
                ("Required Permissions", perm_text, False),
                ("Discord Events", events_text, False),
                ("Default Channel", info.get("channel", "server-logs"), True)
            ]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @module_info.autocomplete('module')
    async def module_info_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=m, value=m)
            for m in MODULES if current.lower() in m.lower()
        ][:25]

    @log_group.command(name="enable", description="Enable a logging module")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 40, key=lambda i: (i.guild_id, i.user.id))
    async def enable_module(self, interaction: discord.Interaction, module: str):
        await interaction.response.defer()
        if module not in MODULES:
            await interaction.followup.send(f"Invalid module: {module}", ephemeral=True)
            return
            
        await upsert_guild_settings(interaction.guild_id, enabled_modules={module: True})
        
        await interaction.followup.send(
            embed=EmbedBuilder.success("Module Enabled", f"**{module}** is now enabled.")
        )
        
    @enable_module.autocomplete('module')
    async def enable_module_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=m, value=m)
            for m in MODULES if current.lower() in m.lower()
        ]

    @log_group.command(name="disable", description="Disable a logging module")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 40, key=lambda i: (i.guild_id, i.user.id))
    async def disable_module(self, interaction: discord.Interaction, module: str):
        await interaction.response.defer()
        if module not in MODULES:
            await interaction.followup.send(f"Invalid module: {module}", ephemeral=True)
            return

        await upsert_guild_settings(interaction.guild_id, enabled_modules={module: False})
        
        await interaction.response.send_message(
            embed=EmbedBuilder.success("Module Disabled", f"**{module}** is now disabled.")
        )

    @disable_module.autocomplete('module')
    async def disable_module_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=m, value=m)
            for m in MODULES if current.lower() in m.lower()
        ]

    @log_group.command(name="channel", description="Move all logging to a new channel (Simple Setup only)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def change_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        res = await get_guild_settings(interaction.guild_id)
        log_id = res[0]
        
        # Check if configured
        if not log_id:
             await interaction.response.send_message(
                embed=EmbedBuilder.error("Not Configured", "This server does not have Chromium configured! Run `/setup` first."),
                ephemeral=True
            )
             return

        # Check if Simple or Complex
        # In simple setup, log_id, msg_id, and mem_id are usually the same (or at least log_id is the main driver).
        # We'll check if they are all identical OR if only log_id is set.
        # If they are different, it implies a complex setup (or manual tinkering).
        
        # Helper to get unique non-None IDs
        ids = {x for x in res[0:3] if x is not None} # log_id, msg_id, mem_id
        
        is_simple = len(ids) == 1
        
        if not is_simple:
            await interaction.response.send_message(
                embed=EmbedBuilder.error(
                    "Complex Setup Detected", 
                    "This server uses a custom/complex channel configuration.\n"
                    "You cannot use `/channel` to move everything at once.\n"
                    "Please rename or move the individual channels manually in your server settings."
                ),
                ephemeral=True
            )
            return
            
        # Create Webhook for the new channel to maintain webhook functionality
        webhook_url = None
        try:
             # Prepare Avatar
            avatar_bytes = None
            if self.bot.user.display_avatar:
                avatar_bytes = await self.bot.user.display_avatar.read()
                
            webhook = await channel.create_webhook(name=self.bot.user.name, avatar=avatar_bytes)
            webhook_url = webhook.url
        except Exception:
            # If webhook creation fails, we just won't update the URL fields
            pass

        # Update All to New Channel
        await upsert_guild_settings(
            guild_id=interaction.guild_id,
            log_channel_id=channel.id,
            message_log_id=channel.id,
            member_log_id=channel.id,
            log_webhook_url=webhook_url,
            message_webhook_url=webhook_url,
            member_webhook_url=webhook_url
        )
        
        await interaction.response.send_message(
            embed=EmbedBuilder.success(
                "Channel Updated",
                f"All logging has been moved to {channel.mention}."
            )
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LogManagement(bot))
