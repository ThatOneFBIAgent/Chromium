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
    "MemberBan", "GuildUpdate", "EmojiUpdate", "RolePermissionUpdate", "MemberKick", "NicknameUpdate",
    "TimeoutUpdate", "WebhookUpdate", "InviteUpdate"
]

class LogManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    log_group = app_commands.Group(name="log", description="Manage logging modules")

    @log_group.command(name="list", description="List all modules and their status")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_modules(self, interaction: discord.Interaction):
        log_id, msg_id, mem_id, susp_id, enabled_modules = await get_guild_settings(interaction.guild_id)
        
        # Check configuration
        if not log_id and not msg_id and not mem_id:
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Not Configured", "This server does not have Chromium configured! Run `/setup` first."),
                ephemeral=True
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
        await interaction.response.send_message(embed=embed)

    @log_group.command(name="enable", description="Enable a logging module")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable_module(self, interaction: discord.Interaction, module: str):
        if module not in MODULES:
            await interaction.response.send_message(f"Invalid module: {module}", ephemeral=True)
            return
            
        await upsert_guild_settings(interaction.guild_id, enabled_modules={module: True})
        
        await interaction.response.send_message(
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
        if module not in MODULES:
            await interaction.response.send_message(f"Invalid module: {module}", ephemeral=True)
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

async def setup(bot: commands.Bot):
    await bot.add_cog(LogManagement(bot))
