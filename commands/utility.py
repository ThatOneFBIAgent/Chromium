import discord
from discord import app_commands
from discord.ext import commands
import time
import platform
import sys
from utils.embed_builder import EmbedBuilder
from config import shared_config
from database.queries import get_total_logs_count

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="debug", description="Shows the bot's current status and diagnostic information")
    async def debug(self, interaction: discord.Interaction):
        """Displays system metrics, versioning, and shard health."""
        # Calculate Uptime
        uptime_seconds = int(time.time() - self.bot.start_time)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # Shards & Latency
        shards = self.bot.shard_count or 1
        avg_latency = round(self.bot.latency * 1000, 2)
        
        # Statistics
        guild_count = len(self.bot.guilds)
        # Approximate member count (from cache)
        member_count = sum(g.member_count or 0 for g in self.bot.guilds)
        total_logs = await get_total_logs_count()
        
        def format_count(num: int) -> str:
            if num < 1000:
                return str(num)
            for unit in ['K', 'M', 'B', 'T']:
                num /= 1000.0
                if num < 1000.0:
                    return f"{num:.1f}{unit}".replace('.0', '')
            return f"{num:.1f}P"

        # Build fields list
        fields = [
            ("⏱️ Performance", f"**Latency:** `{avg_latency}ms`\n**Uptime:** `{uptime_str}`", True),
            ("📊 Statistics", f"**Guilds:** `{guild_count}`\n**Users:** `{format_count(member_count)}`\n**Total Logs:** `{format_count(total_logs)}`", True),
            ("⚙️ Environment", f"**Node:** `{shared_config.ENVIRONMENT.value.capitalize()}`\n**Railway:** `{'Yes' if shared_config.IS_RAILWAY else 'No'}`", True),
            ("💻 System", f"**Python:** `{platform.python_version()}`\n**Discord.py:** `{discord.__version__}`\n**OS:** `{platform.system()}`", False)
        ]

        # Add per-shard details for multi-shard setups
        if shards > 1:
            shard_details = ""
            for shard_id, shard in self.bot.shards.items():
                shard_details += f"**Shard {shard_id+1}:** `{round(shard.latency * 1000, 2)}ms` | {len([g for g in self.bot.guilds if g.shard_id == shard_id])} Guilds\n"
            fields.append(("📡 Shard Index", shard_details.strip(), False))

        embed = EmbedBuilder.success(
            title="Chromium | System Diagnostic",
            description="The logging engine is operational. All systems are green.",
            fields=fields
        )

        embed.set_footer(text=f"Chromium Core v1.4 | Shard: {interaction.guild.shard_id if interaction.guild else 0}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
