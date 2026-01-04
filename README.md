# Chromium: Modular Discord Logger

A production-ready, modular, and sharding-safe Discord logger built with `discord.py` 2.0+.
Key features include per-guild isolated logging, suspicion heuristics, database log rotation (SQLite), and optional Google Drive integration.

## Features

- **Modular Logging**: 8+ distinct logging modules (Message Delete, Edit, Join, Leave, Voice, Role, Channel, Error) that can be enabled/disabled per guild.
- **Per-Guild Isolation**: Configurations and logs are strictly isolated.
- **Log Rotation**: Automatically keeps only the latest 50 logs per guild to save space.
- **Suspicious Activity Detection**: Detects spam deletes/edits/joins and flags them in logs.
- **Slash Commands**: Full setup and management via `/setup`, `/log`, and `/export`.
- **Exports**: Export logs to a JSON file, with optional Google Drive upload.
- **Blacklisting & Whitelisting**: Blacklist/Whitelist users, roles, channels from logging.
- **Sharding**: Built on `AutoShardedBot` for scalability.
- **Docker Ready**: Includes production-grade Dockerfile with non-root user.

## Structure

```
.
├── bot.py                  # Entry point
├── config.py               # Configuration management
├── database/               # Database layer (SQLite + Rotation Logic)
├── logging_modules/        # Independent logging modules
├── commands/               # Slash commands
├── utils/                  # Utilities (Logger, Drive, Suspicion)
├── Dockerfile              # Deployment
└── requirements.txt        # Dependencies
```

## Setup

### Prerequisites
- Python 3.11+
- Discord Bot Token (with Message Content, Server Members, and Presence Intents enabled)

### Local Run

1. **Clone the repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your details.
   ```env
   DISCORD_TOKEN=your_token
   DRIVE_CREDS_B64=base64_encoded_service_account_json (Optional)
   DRIVE_FOLDER_ID=your_folder_id (Optional)
   ```
   ###### Technically it's meant to be an OAuth2 token, in json form. Despite it saying "service account" in the name. And detection of which is not very reliable. But switching to using a service account auth is possible but not recommended due to quota limits and etc.
4. **Run the bot**:
   ```bash
   python bot.py
   ```

### Docker Run

1. **Build the image**:
   ```bash
   docker build -t chromium-bot .
   ```
2. **Run the container**:
   ```bash
   docker run -d \
     --name chromium \
     --env-file .env \
     -v $(pwd)/data:/app/data \
     --restart unless-stopped \
     chromium-bot
   ```
   *Note: volume mapping `./data` is critical for ensuring logs and the database persist across restarts.*

### Railway
1.R **Deploy from github**
   Make sure it's uploaded a public or private repo, and that railway has access to it (by logging in with Github).
   Deploying should be as easy as adding the ENV variables and making sure `RAILPACK` is set.

   If any problems occur, check the logs and open an issue on github. I'll try my best to help you.

## Permissions

The bot requires the following permissions to function fully:
- **Manage Channels**: For `/setup complex`.
- **View Audit Log**: For more detailed logging (future expansion).
- **Send Messages / Embed Links**: For logging.
- **Manage Webhooks**: (Optional) if using webhook logging in future.
- **View Channels**: For server-wide logging unless otherwise specified.
- **Send Messages**: For the bot to log to channels properly.

## Google Drive Integration

To enable export uploads:

1. **Get Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com).
   - Create a project and enable "Google Drive API".
   - Go to "Credentials" and create a OAuth Client ID credential (Web Application).
   - Set the authorized redirect URI to `http://localhost:8080`.
   - Download the `client_secret.json` file after creating the secret (should be a download button when configuring said secret).

2. **Generate Token**:
   Run the included helper script (requires `google-auth-oauthlib`):
   ```bash
   pip install google-auth-oauthlib
   python utils/drivehelper.py
   ```
   Follow the on-screen instructions to authenticate and automatically update your `.env` file.

3. **Configure Folder**:
   - Share a Google Drive folder with the account you authenticated.
   - Copy the Folder ID from the URL and set `DRIVE_FOLDER_ID` in `.env`.

## Sharding

The bot automatically uses `AutoShardedBot`. You can force a specific shard count using the `SHARD_COUNT` env var, but leaving it to default is recommended for most use cases.

### TODO:
- N/a

## License

This project is licensed under the GNUv3 License - see the [LICENSE](LICENSE) file for details.

## Contact/Support

If you have any questions, encounter bugs, or need help with setup:

- **Issues**: Open a ticket on our [GitHub Issues](https://github.com/yourusername/chromium/issues) page.
- **Discord**: Contact `_izacarlos` directly for support.
