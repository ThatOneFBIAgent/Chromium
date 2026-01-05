import discord
from discord import app_commands
from discord.ext import commands
import json
import tempfile
import os
from datetime import datetime
from database.queries import get_recent_logs
from utils.drive import drive_manager
from utils.embed_builder import EmbedBuilder

class Export(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="export", description="Export the last 50 logs")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 10, app_commands.BucketType.guild)
    async def export_logs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Check Configuration First
        from database.queries import get_guild_settings
        log_id, _, _, _, _ = await get_guild_settings(interaction.guild_id)
        
        if not log_id:
             await interaction.followup.send(
                embed=EmbedBuilder.error("Not Configured", "This server does not have Chromium configured! Run `/setup` first.")
            )
             return

        # Fetch logs
        rows = await get_recent_logs(interaction.guild_id, limit=50)
        
        if not rows:
            await interaction.followup.send(
                embed=EmbedBuilder.warning("No Logs", "There are no logs to export for this server.")
            )
            return

        # Format data
        export_data = []
        for row in rows:
            # row is aiosqlite.Row
            export_data.append({
                "id": row['id'],
                "module": row['module_name'],
                "content": row['content'],
                "timestamp": row['timestamp']
            })
            
        json_content = json.dumps(export_data, indent=2, default=str)
        filename = f"export_{interaction.guild_id}_{int(datetime.utcnow().timestamp())}.json"
        
        # Create temp file for Discord upload
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json", encoding='utf-8') as tmp:
            tmp.write(json_content)
            tmp_path = tmp.name
            
        try:
            # Send to Discord
            discord_file = discord.File(tmp_path, filename=filename)
            embed = EmbedBuilder.success("Export Ready", f"Exported {len(rows)} logs.")
            
            await interaction.followup.send(embed=embed, file=discord_file)
            
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

async def setup(bot: commands.Bot):
    await bot.add_cog(Export(bot))
