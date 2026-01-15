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

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ThatOneFBIAgent/Chromium.git
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your details.
   ```env
   DISCORD_TOKEN=your_token
   BETA_TOKEN=your_token
   DRIVE_CREDS_B64=base64_encoded_service_account_json (Optional)
   DRIVE_FOLDER_ID=your_folder_id (Optional)
   ```
   > [!IMPORTANT]
   > Both BETA_TOKEN and DISCORD_TOKEN **MUST** be the same due to how the code detects the right token to use. Or only use BETA_TOKEN if you don't plan on deploying

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
1. **Deploy from github**
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

- **Issues**: Open a ticket on our [GitHub Issues](https://github.com/ThatOneFBIAgent/chromium/issues) page.
- **Discord**: Contact `_izacarlos` directly for support.

---

## Disclaimer / No Liability

**Important**: This codebase is provided "as is", without warranty of any kind. 

1.  **"as is"**: This bot is built on a caffeine-powered codebase by an AuDHD programmer. While I strive for excellence, quirks and edge cases may exist, but I will try to fix them in due time.
2.  **Data Reliability**: Internally, I try not to lose logs, but I cannot promise a 100% guarantee. Do not rely on this bot as your single source of truth for critical auditing or legal compliance when it comes to reporting.
3.  **Logs & Exports**: Exported logs are provided for convenience. I am not liable for any data loss, corruption, or misuse of the logging data once it leaves the bot's internal systems.
4.  **Usage**: You are installing/adding a bot built by a third party. I am not liable if something goes wrong, sideways, or upside down in your server configuration or data as a result of using this software. Use responsibly.
5.  **Data collection**: No data is shared with third parties, and any data stored is only used for running the bot and it's per-server configurations. I cannot see your logs, and I cannot access your data unless explicitly shared with me. The backups created every two hours are created/updated to my personal Drive account and do not contain sensitive data. (Nor that I care about it, it does not benefit me)