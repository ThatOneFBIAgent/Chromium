import discord
from discord import app_commands
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder
from utils.logger import get_logger

log = get_logger()

class ErrorLogger(BaseLogger):
    def __init__(self, bot):
        super().__init__(bot)
        # Register global error handler for app commands
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Permission Denied", "You do not have the required permissions to run this command."),
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Guild Only", "This command cannot be used in Direct Messages."),
                ephemeral=True
            )
            return

        if isinstance(error, app_commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Bot Missing Permissions", f"I do not have the required permissions to execute this command.\nMissing: `{missing}`"),
                ephemeral=True
            )
            return

        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                embed=EmbedBuilder.error("Cooldown", f"Please wait {error.retry_after:.1f}s before using this command again."),
                ephemeral=True
            )
            return

        log.error(f"App Command Error in {interaction.command.name if interaction.command else 'Unknown'}", exc_info=error)
        
        if interaction.guild:
            # Try to log to guild channel
            embed = EmbedBuilder.error(
                title="Command Error",
                description=f"An error occurred while executing `/{interaction.command.name if interaction.command else 'command'}`.",
                fields=[("Error", str(error)[:1024], False)]
            )
            try:
                await self.log_event(interaction.guild, embed)
            except Exception:
                pass # Fail silently if we can't log the error itself
            
        # Reply to user if possible
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
        else:
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorLogger(bot))
