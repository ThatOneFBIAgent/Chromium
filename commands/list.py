import discord
from discord import app_commands
from discord.ext import commands
import difflib
from datetime import datetime
from typing import List, Literal, Optional
from database.queries import add_list_item, remove_list_item, get_list_items, search_list_items
from utils.embed_builder import EmbedBuilder

class List(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Group: Blacklist
    blacklist = app_commands.Group(name="blacklist", description="Manage the server blacklist")

    # Group: Whitelist
    whitelist = app_commands.Group(name="whitelist", description="Manage the server whitelist")

    # Group: List (don't use 'list' as it's a reserved keyword)
    list_name = app_commands.Group(name="list", description="General list commands")

    # Helper: Resolve entity from query (ID or Name)
    def _resolve_entity(self, guild: discord.Guild, query: str):
        # Try ID resolve first
        if query.isdigit():
            user = guild.get_member(int(query))
            if user: return user, 'user'
            role = guild.get_role(int(query))
            if role: return role, 'role'
            channel = guild.get_channel(int(query))
            if channel: return channel, 'channel'
        
        # Fuzzy Search
        # Collect all candidates
        candidates = []
        candidates.extend([(r, r.name) for r in guild.roles])
        candidates.extend([(m, m.name) for m in guild.members])
        candidates.extend([(c, c.name) for c in guild.channels])
        
        # Use difflib to find best match
        # We process names to simple strings
        names = [x[1] for x in candidates]
        matches = difflib.get_close_matches(query, names, n=1, cutoff=0.6)
        
        if matches:
            # Find the object corresponding to the name
            for obj, name in candidates:
                if name == matches[0]:
                    if isinstance(obj, discord.Member): return obj, 'user'
                    if isinstance(obj, discord.Role): return obj, 'role'
                    if isinstance(obj, discord.abc.GuildChannel): return obj, 'channel'
        
        return None, None

    # Autocomplete for ADD
    async def add_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not interaction.guild:
            return []
        
        if len(current) < 3:
            return []

        # Search Guild Entities
        options = []
        
        # Roles
        for role in interaction.guild.roles:
            if current.lower() in role.name.lower():
                options.append(app_commands.Choice(name=f"Role: {role.name}", value=str(role.id)))
        
        # Channels
        for channel in interaction.guild.channels:
            if current.lower() in channel.name.lower():
                options.append(app_commands.Choice(name=f"Channel: {channel.name}", value=str(channel.id)))
                
        # Members (Limit to avoid massive loops if possible, or rely on cache)
        # Note: Large guilds might need optimization here, but simple logic for now
        count = 0
        for member in interaction.guild.members:
            if current.lower() in member.display_name.lower() or current.lower() in member.name.lower():
                options.append(app_commands.Choice(name=f"User: {member.display_name}", value=str(member.id)))
                count += 1
                if count > 10: break # soft limit for mixed results
                
        return options[:25]

    # Autocomplete for REMOVE
    async def remove_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not interaction.guild:
            return []
            
        # Determine list type from command parent
        # However, interaction.command.parent.name should give 'blacklist' or 'whitelist'
        list_type = interaction.command.parent.name
        
        rows = await search_list_items(interaction.guild_id, list_type, current)
        
        choices = []
        for row in rows:
            name = f"{row['entity_type'].upper()}: {row['entity_name']}"
            choices.append(app_commands.Choice(
                name=name, 
                value=str(row['entity_id'])
            ))
        return choices[:25]

    # shared logic for three commands, just parse list_type
    async def _add_command(self, interaction: discord.Interaction, query: str, list_type: str):
        await interaction.response.defer(ephemeral=True)
        
        # 1. Resolve Entity
        entity, entity_type = self._resolve_entity(interaction.guild, query)
        
        if not entity:
            # If resolve returned None, check if existing by ID was passed directly via selection
            # The autocomplete value sends an ID string.
            if query.isdigit():
                 # Try one last fetch by ID
                try:
                    eid = int(query)
                    entity = interaction.guild.get_member(eid) or interaction.guild.get_role(eid) or interaction.guild.get_channel(eid)
                    if entity:
                        if isinstance(entity, discord.Member): entity_type = 'user'
                        elif isinstance(entity, discord.Role): entity_type = 'role'
                        elif isinstance(entity, discord.abc.GuildChannel): entity_type = 'channel'
                except:
                    pass

        if not entity:
            await interaction.followup.send(
                embed=EmbedBuilder.error("Not Found", f"Could not find role, user, or channel matching: `{query}`")
            )
            return
            
        # 2. Add to DB
        success = await add_list_item(
            interaction.guild_id, 
            list_type, 
            entity_type, 
            entity.id, 
            entity.name if isinstance(entity, discord.Role) or isinstance(entity, discord.abc.GuildChannel) else entity.display_name
        )
        
        if success:
            await interaction.followup.send(
                embed=EmbedBuilder.success("Added", f"Added **{entity.name if hasattr(entity, 'name') else entity.display_name}** ({entity_type}) to {list_type}.")
            )
        else:
            await interaction.followup.send(
                embed=EmbedBuilder.error("Error", "Failed to add item to database. It might already exist.")
            )

    async def _remove_command(self, interaction: discord.Interaction, query: str, list_type: str):
        await interaction.response.defer(ephemeral=True)
        
        # Query might be an ID (from autocomplete) or a name
        # We try to remove by ID first if digit
        
        entity_id = None
        if query.isdigit():
            entity_id = int(query)
        else:
            # Try to resolve name from DB
            rows = await search_list_items(interaction.guild_id, list_type, query)
            for row in rows:
                if row['entity_name'].lower() == query.lower():
                    entity_id = row['entity_id']
                    break
            
            if not entity_id and rows:
                entity_id = rows[0]['entity_id']
            
        if not entity_id:
             await interaction.followup.send(
                embed=EmbedBuilder.error("Invalid Input", "Please select an item from the autocomplete options or provide a valid ID.")
            )
             return

        success = await remove_list_item(interaction.guild_id, list_type, entity_id)
        
        if success:
             await interaction.followup.send(
                embed=EmbedBuilder.success("Removed", f"Removed item {query} from {list_type}.")
            )
        else:
            await interaction.followup.send(
                embed=EmbedBuilder.error("Error", "Failed to remove item. It might not exist.")
            )

    async def _show_command(self, interaction: discord.Interaction, page: int, list_type: str):
        await interaction.response.defer(ephemeral=True)
        
        items = await get_list_items(interaction.guild_id, list_type)
        
        if not items:
            await interaction.followup.send(
                embed=EmbedBuilder.warning(f"{list_type.capitalize()}", f"The {list_type} is empty.")
            )
            return

        # Pagination
        per_page = 8
        pages = [items[i:i + per_page] for i in range(0, len(items), per_page)]
        
        if page < 1 or page > len(pages):
            await interaction.followup.send(embed=EmbedBuilder.error("Error", "Invalid page number."))
            return
            
        current_page_items = pages[page - 1]
        
        description = ""
        for item in current_page_items:
            # item: id, guild_id, list_type, entity_type, entity_id, entity_name, added_at
            # Parse SQLite timestamp
            try:
                dt = datetime.strptime(item['added_at'], "%Y-%m-%d %H:%M:%S")
                timestamp = int(dt.timestamp())
            except (ValueError, TypeError):
                timestamp = int(datetime.utcnow().timestamp())

            description += f"**{item['entity_name']}** (`{item['entity_id']}`)\nType: {item['entity_type'].capitalize()} • Added: <t:{timestamp}:R>\n\n"
            
        embed = discord.Embed(title=f"Server {list_type.capitalize()} (Page {page}/{len(pages)})", description=description, color=discord.Color.blue())
        embed.set_footer(text=f"Total items: {len(items)}")
        
        await interaction.followup.send(embed=embed)

    # Register commands
    @blacklist.command(name="add", description="Add a user, role, or channel to blacklist")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.autocomplete(query=add_autocomplete)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def blacklist_add(self, interaction: discord.Interaction, query: str):
        await self._add_command(interaction, query, "blacklist")

    @blacklist.command(name="remove", description="Remove an item from blacklist")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.autocomplete(query=remove_autocomplete)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def blacklist_remove(self, interaction: discord.Interaction, query: str):
        await self._remove_command(interaction, query, "blacklist")

    @blacklist.command(name="show", description="Show blacklist")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def blacklist_show(self, interaction: discord.Interaction, page: int = 1):
        await self._show_command(interaction, page, "blacklist")

    @whitelist.command(name="add", description="Add a user, role, or channel to whitelist")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.autocomplete(query=add_autocomplete)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def whitelist_add(self, interaction: discord.Interaction, query: str):
        await self._add_command(interaction, query, "whitelist")

    @whitelist.command(name="remove", description="Remove an item from whitelist")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.autocomplete(query=remove_autocomplete)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def whitelist_remove(self, interaction: discord.Interaction, query: str):
        await self._remove_command(interaction, query, "whitelist")

    @whitelist.command(name="show", description="Show whitelist")   
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def whitelist_show(self, interaction: discord.Interaction, page: int = 1):
        await self._show_command(interaction, page, "whitelist")

    @list_name.command(name="help", description="Get help with the list commands")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def help_list(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=EmbedBuilder.info("List Commands", """
            **Commands:**
            • `add`: Adds a user, role, or channel to the specified list.
            • `remove`: Removes an entry from the specified list.
            • `show`: Displays all entries in the specified list with pagination.

            **Order of Operations:**
            1 - User Whitelist (The "Suspicious Person" check-log them no matter where they are).
            2 - User Blacklist (The "Privacy" check-if Joe is blocked, he is blocked everywhere).
            3 - Channel Whitelist (The "Important Room" check-if this room is whitelisted, log everyone, even blacklisted roles).
            4 - Role Whitelist (The "Staff/Fanatic" check-log them even in blacklisted channels).
            5 - Channel Blacklist (The "Private Room" check-don't log unless caught by a higher whitelist).
            6 - Role Blacklist (The "Ignore Bots/Spammers" check-don't log unless caught by a higher whitelist).
            7 - DEFAULT: LOG IT (Since the bot is Opt-Out).
            """
        )
    )

async def setup(bot: commands.Bot):
    await bot.add_cog(List(bot))
