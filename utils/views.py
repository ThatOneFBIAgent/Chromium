import discord
from typing import Optional

class ConfirmationView(discord.ui.View):
    def __init__(self, timeout: float = 180.0, author_id: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message("This confirmation is not for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        # defer to separate the interaction from the button click, allowing the caller to edit the message
        await interaction.response.defer() 
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()

    async def on_timeout(self):
        self.value = False
        self.stop()
