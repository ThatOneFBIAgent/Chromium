import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from logging_modules.base import BaseLogger

# Configurable Test Table
# Format: (Description, UserID, ChannelID, UserRoles, DB_Items, Expected_Result)
TEST_SCENARIOS = [
    (
        "No Blacklists/Whitelists - Should Log",
        100, 200, [], 
        [], 
        True
    ),
    (
        "User Blacklisted - Should Block",
        100, 200, [],
        [{'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'user', 'entity_id': 100}],
        False
    ),
    (
        "Channel Blacklisted - Should Block",
        100, 200, [],
        [{'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'channel', 'entity_id': 200}],
        False
    ),
    (
        "Role Blacklisted - Should Block",
        100, 200, [555],
        [{'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555}],
        False
    ),
    (
        "User Whitelisted (Override Channel BL) - Should Log",
        100, 200, [],
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'channel', 'entity_id': 200},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100}
        ],
        True
    ),
    (
        "Role Whitelisted (Override Role BL) - Should Log",
        100, 200, [555, 777], # 555 is BL, 777 is WL
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'role', 'entity_id': 777}
        ],
        True
    ),
    (
        "User Whitelisted (Override Role BL) - Should Log",
        100, 200, [555], # 555 is BL
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100}
        ],
        True
    )
]

@pytest.mark.asyncio
@pytest.mark.parametrize("desc, uid, cid, roles, db_items, expected", TEST_SCENARIOS)
async def test_should_log_scenarios(mocker, mock_guild, mock_user, mock_channel, desc, uid, cid, roles, db_items, expected):
    """
    Data-driven test for BaseLogger.should_log
    """
    # Setup Mock Data
    mock_user.id = uid
    mock_channel.id = cid
    
    mock_roles = []
    for r_id in roles:
        r = MagicMock(spec=discord.Role)
        r.id = r_id
        mock_roles.append(r)
    mock_user.roles = mock_roles
    
    # Mock the DB call in BaseLogger
    # mock_db_items needs to behave like aiosqlite.Row or dict
    # We used dict access in BaseLogger (item['entity_id']), so dicts work fine if the code supports it.
    mock_get_all = mocker.patch("logging_modules.base.get_all_list_items", new_callable=AsyncMock)
    mock_get_all.return_value = db_items
    
    # Mock isinstance to allow role checks
    # Because mock_user is a MagicMock, isinstance(mock_user, discord.Member) might fail unless we configure spec properly or mock isinstance/class checks.
    # BaseLogger uses: if user and isinstance(user, discord.Member):
    # We can rely on spec=discord.Member working for isinstance checks in modern mock if we are careful, 
    # OR we can just test assuming it is a member.
    # Actually, MagicMock(spec=discord.Member) usually satisfies isinstance checks ig.
    
    # Initialize Logger
    bot = MagicMock()
    logger = BaseLogger(bot)
    
    # Act
    result = await logger.should_log(mock_guild, user=mock_user, channel=mock_channel)
    
    # Assert
    assert result == expected, f"Failed Scenario: {desc}"
