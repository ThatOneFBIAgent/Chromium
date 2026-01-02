import pytest
import discord
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_guild():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 1
    guild.owner_id = 999999
    return guild

@pytest.fixture
def mock_user():
    user = MagicMock(spec=discord.Member)
    user.id = 111111
    user.name = "TestUser"
    user.discriminator = "0000"
    user.roles = []
    # Mock isinstance to always return False by default unless patched, 
    # but for simple logic usage we treat it as an object with .id
    return user

@pytest.fixture
def mock_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 222222
    channel.name = "general"
    return channel

@pytest.fixture
def mock_db(mocker):
    # Mock the database.queries imports in the modules we test
    # We will likely mock specific query functions in the test files
    pass
