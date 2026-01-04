import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from database.queries import get_guild_settings, upsert_guild_settings
from utils.embed_builder import EmbedBuilder

# List of all available modules for autocomplete/validation
MODULES = [
    "MessageDelete", "MessageEdit", "MemberJoin", "MemberLeave", 
    "VoiceState", "RoleUpdate", "ChannelUpdate", "ErrorLogger",
    "MemberBan", "GuildUpdate", "EmojiUpdate", "MemberKick", "NicknameUpdate",
    "TimeoutUpdate", "WebhookUpdate", "InviteUpdate", "AutoModUpdate"
]

class LogManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    log_group = app_commands.Group(name="log", description="Manage logging modules")

    @log_group.command(name="list", description="List all modules and their status")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_modules(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        log_id, msg_id, mem_id, susp_id, enabled_modules = await get_guild_settings(interaction.guild_id)
        
        # Check configuration
        if not log_id and not msg_id and not mem_id:
            await interaction.followup.send(
                embed=EmbedBuilder.error("Not Configured", "This server does not have Chromium configured! Run `/setup` first.")
            )
            return

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

    @log_group.command(name="enable", description="Enable a logging module")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
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
    async def change_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        log_id, msg_id, mem_id, susp_id, enabled_modules = await get_guild_settings(interaction.guild_id)
        
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
        ids = {x for x in [log_id, msg_id, mem_id] if x is not None}
        
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
            
        # Update All to New Channel
        await upsert_guild_settings(
            interaction.guild_id,
            log_channel_id=channel.id,
            message_log_id=channel.id,
            member_log_id=channel.id,
            susp_channel_id=channel.id # Also move suspicious logs for simple setup
        )
        
        await interaction.response.send_message(
            embed=EmbedBuilder.success(
                "Channel Updated",
                f"All logging has been moved to {channel.mention}."
            )
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LogManagement(bot))
