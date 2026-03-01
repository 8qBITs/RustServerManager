# Rust Server Manager v2.0
**A modern, feature-rich desktop application for managing Rust dedicated game servers on Windows.**

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

Rust Server Manager v2.0 is a complete modernization of the original lightweight wrapper. While maintaining full backward compatibility, it now features:

- 🎨 **Modern Desktop UI** (PySide6/Qt6) with live monitoring
- 🎮 **Complete Server Control** (install, update, start, stop, restart)
- 💻 **RCON Console** for remote command execution  
- ⚙️ **Configuration Management** with validation and persistence
- 🔄 **Background Automation** with scheduling (auto-update checks, auto-restart, etc.)
- 📊 **Real-time Dashboard** with server status, resource usage, and logs
- 🔐 **Security** with RCON authentication and path validation
- 📝 **Structured Logging** with file and console output

## Quick Start

### Installation (2 minutes)

```bash
# Install Python 3.9+ from https://www.python.org/

# Install dependencies
pip install -r requirements.txt

# Run the modern UI (recommended)
python app_main.py

# OR run the legacy CLI mode (backward compatible)
python app.py
```

### First Time Setup (5 minutes)

1. Open **Settings** tab
2. Verify tool paths (SteamCMD, curl, 7-zip)
3. Configure server parameters (ports, max players, hostname)
4. Set RCON connection details (host, port, password)
5. Click **Save Settings** and **Validate Settings**

### Install & Run Server (10 minutes)

1. Go to **Controls** tab
2. Click **Install/Update Rust Server** (download latest from Steam)
3. Click **Install/Update Oxide** (mod loader - optional)
4. Go to **Dashboard** tab and click **▶ Start Server**
5. Monitor status in Dashboard (refreshes every 2 seconds)

### Remote Access with RCON

1. Go to **RCON Console** tab
2. Enter host, port, password
3. Click **🔗 Connect**
4. Send commands like `say Hello World`, `players.limit 20`, etc.

## Features

### 📊 Dashboard
- Real-time server status (Online/Offline)
- Process ID, memory usage, CPU usage  
- Installation status (executable, Oxide)
- Auto-refreshing every 2 seconds

### 🎮 Controls
- Install/update Rust server from Steam
- Install/update Oxide mod loader
- Install/update RustEdit extension
- Start, stop, restart server
- Progress tracking with real-time status

### ⚙️ Settings
- **Server Configuration**:
  - Game mode selection: **Vanilla**, **Softcore**, **Hardcore**, **Creative**
  - Port, hostname, map, seed, world size, max players, tickrate
- **Paths**: Directories for tools and data
- **RCON**: Connection configuration (host, port, password)
- Validation with error reporting
- JSON persistence with Pydantic validation

### 🔄 Automation (Redesigned)
The Automation tab features an integrated control center with **4 subtabs**:

#### ⚙️ Settings Subtab
- **Feature Toggles**: Enable/disable Scheduler, Console Triggers, and Backups independently
- **Activity Console**: Real-time monitoring of all automation events
- Automatically logs all scheduled jobs, triggers matched, and backups created

#### 📅 Scheduler Subtab
- Schedule background tasks (update checks, auto-updates, restarts)
- **Enable/Disable Individual Jobs**: Toggle schedules on/off without deleting them
- View status: Last run time, next run time, job name
- Thread-safe job management with APScheduler

#### 🔔 Console Triggers Subtab
- **Monitor server console** for specific patterns (regex-based)
- **Webhook Notifications**: Send alerts via Discord or generic webhooks
- **Discord Embeds**: Rich formatted messages with colors and custom fields
- **Template System**: 9 predefined templates for common events:
  - Player join/leave events
  - Server startup/shutdown
  - Kill reports and chat messages
  - Error notifications
  - Plugin loading events
  - Wipe events
- **Pattern Testing**: Real-time validation with capture group display
- **Statistics**: Track match count and last matched values

#### 📦 Backups Subtab
- **Create Backups**: Full server data snapshots with custom names
- **Restore Backups**: One-click deployment of any saved backup
- **Backup History**: View all backups with creation dates and sizes
- **Quick Actions**: Deploy latest backup or delete old backups
- Async backup operations with progress updates

### 💻 RCON Console
- Connect/disconnect from any Rust server
- Send arbitrary RCON commands
- View server responses in real-time
- Command history with dropdown
- Async I/O (non-blocking)

## Console Triggers (Automation Monitoring)

Console triggers allow you to monitor your Rust server's console output and automatically send notifications when specific patterns are detected. This is perfect for:
- **Alert on errors**: Get Discord notifications when critical errors occur
- **Player events**: Be notified when players join/leave
- **Server events**: Track restarts, wipes, or plugin loading
- **Custom patterns**: Define any regex pattern to monitor

### Quick Setup

1. Navigate to **Automation** tab → **🔔 Console Triggers**
2. Click **+ Add Trigger** or select a **Template** from the dropdown
3. Configure **Pattern** (regex), **Webhook Type** (Discord or Generic JSON), and **Message Template**
4. Click **Test Pattern** to verify against actual server output
5. Save and enable the trigger

### Example: Player Join Notification

**Pattern (Regex):**
```
(\w+)\[\d+\/\d+\] joined, joined
```

**Message Template:**
```
Player {0} just joined the server!
```

**Webhook Type:** Discord

**Result:** When a player joins, you'll receive a Discord message like:
```
Player SomePlayer123 just joined the server!
```

### Example: Critical Error Alert

**Pattern (Regex):**
```
\[ERROR\].*Fatal|OutOfMemory|StackOverflow
```

**Webhook:** Discord with red embed color

**Result:** Critical errors trigger immediate Discord alerts with red highlighting

### Webhook Types

**Discord**
- Rich embeds with custom colors
- Timestamp and field support
- Perfect for human-readable alerts

**Generic JSON**
- POST to any webhook endpoint
- Custom JSON payload format
- Flexible for custom integrations

See [docs/CONSOLE_TRIGGERS.md](docs/CONSOLE_TRIGGERS.md) for advanced examples and predefined templates.

## Backup Management

The Backup Management system provides easy full-server backups and one-click restores:

### Features

- **Instant Backups**: Create full server data snapshots
- **Timestamped**: Automatic backup creation dates
- **Size Display**: See backup sizes before restoring
- **Quick Restore**: Deploy any backup with one click
- **Batch Operations**: Create, restore, or delete multiple backups

### Workflow

1. **Create Backup**:
   - Go to **Automation** tab → **📦 Backups**
   - Enter backup name (e.g., "Before_Wipe_2026-03-01")
   - Click **Create Backup**

2. **Restore Backup**:
   - Select backup from **Available Backups** dropdown
   - Click **⚡ Deploy Selected Backup** or **Deploy Latest**
   - Server data is restored (server must be stopped)

3. **View History**:
   - Backup table shows creation date, size, and status
   - Activity log shows all backup operations

### Data Protected

- `/rust_data` directory (maps, inventories, blueprints, wipes)
- Player data and progression
- Custom map configurations
- All Oxide plugins and data

## Building from Source

While pre-built executables are available, you can build your own Windows executable using PyInstaller.

### Requirements

- **Python 3.9+** ([download](https://www.python.org/downloads/))
- **PyInstaller** (installed via requirements-dev.txt)
- **Git** (optional, for cloning the repo)

### Build Steps

1. **Clone or download the repository**:
```bash
git clone https://github.com/8qBITs/RustServerManager.git
cd RustServerManager
```

2. **Create a Python virtual environment** (optional but recommended):
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install pyinstaller
```

4. **Build the executable**:
```bash
pyinstaller --onefile --windowed --icon=icon.ico --name="RustServerManager" app_main.py
```

Or use the provided build batch file (if available):
```bash
build.bat
```

5. **Locate the executable**:
- Single-file executable: `dist/RustServerManager.exe`
- Can be moved anywhere and run independently
- No Python installation required on target machine

### Build Options

For advanced builds, customize the PyInstaller command:

```bash
# Include hidden imports if needed
pyinstaller --onefile --windowed --hidden-import=PySide6 app_main.py

# Build with specific paths
pyinstaller --onefile --distpath=./release --specpath=./build app_main.py

# Add custom icon (place icon.ico in project root)
pyinstaller --onefile --icon=icon.ico app_main.py
```

### Distribution

The built executable in `dist/RustServerManager.exe`:
- Works on any Windows 7+ system
- No dependencies (everything bundled)
- Can be shared, copied, or included in installers
- ~120-150 MB size (includes Python runtime)

## Architecture

```
┌─────────────────────────────────────────────┐
│      PySide6 Desktop UI                     │
│  (Dashboard, Controls, Settings, etc.)      │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────┴───────────────────────┐
│    Core Services (Modular & Reusable)      │
│  - ServerManager (install/update/control)  │
│  - RconClient (RCON protocol)              │
│  - TaskScheduler (background automation)   │
│  - ConfigManager (settings persistence)    │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────┴───────────────────────┐
│         System & Third-Party APIs          │
│  - subprocess (SteamCMD, tools)            │
│  - socket (RCON protocol)                  │
│  - APScheduler (background tasks)          │
│  - psutil (process monitoring)             │
└─────────────────────────────────────────────┘
```

### Project Structure

```
RustServerManager/
├── core/                    # Core server logic
│   ├── server_manager.py   # Install, update, start, stop
│   └── rcon_client.py      # RCON protocol
├── config/                  # Configuration management
│   ├── manager.py          # Load/save/validate config
│   ├── schema.py           # Pydantic config models with GameMode validator
│   └── trigger_templates.py # 9 predefined console trigger templates
├── scheduler/              # Background task scheduling
│   └── task_scheduler.py   # APScheduler wrapper
├── ui/                      # PySide6 desktop UI
│   ├── main_window.py      # Main application window and tab routing
│   ├── tabs/               # Tab implementations
│   │   ├── dashboard.py
│   │   ├── controls.py
│   │   ├── settings.py      # Game mode selection and config UI
│   │   ├── automation.py    # 4-subtab automation control center
│   │   ├── backups.py       # Backup creation/restore/history
│   │   └── console_triggers.py  # Webhook pattern matching
│   └── widgets/            # Reusable UI components
├── utils/                   # Utilities
│   └── logger.py           # Structured logging
├── docs/                    # Documentation
│   └── CONSOLE_TRIGGERS.md  # Advanced trigger patterns and examples
├── app_main.py             # Modern UI entry point
├── app.py                  # Primary UI entry point
├── requirements.txt        # Python dependencies
├── config.yaml             # Auto-created configuration
└── logs/                   # Application logs
    └── app.log
```

**Stats**: 25+ Python files, comprehensive UI components, modular architecture

## Dependencies

All dependencies are in `requirements.txt`:

```
PySide6>=6.6.0          # Qt6 UI framework (modern, cross-platform)
APScheduler>=3.10.0     # Background task scheduling
pydantic>=2.0.0         # Configuration validation
psutil>=5.9.0           # Process and system utilities
python-dotenv>=1.0.0    # Environment variable management
```

Install with:
```bash
pip install -r requirements.txt
```

## Configuration

Configuration is stored in `config.yaml` (auto-created with defaults):

```yaml
server:
  port: 28015
  app_port: 28016
  description: "My Rust Server"
  max_players: 10
  gamemode: "vanilla"  # Options: vanilla, softcore, hardcore, creative

paths:
  rust_data_dir: "./addons/steam/rust_data"
  steamcmd_path: "./addons/steam/steamcmd.exe"

rcon:
  host: "127.0.0.1"
  port: 28016
  password: ""

automation:
  auto_check_rust_updates: false
  auto_update_rust: false
  update_check_interval_minutes: 60
  custom_schedules: []

features:
  scheduler_enabled: true
  triggers_enabled: true
  backups_enabled: true
```

### Game Modes

| Mode | Description | Difficulty |
|------|-------------|-----------|
| **vanilla** | Standard Rust survival mode | Full |
| **softcore** | Reduced difficulty, easier crafting | Medium |
| **hardcore** | Increased difficulty, harsher penalties | Hard |
| **creative** | Creative/building mode, immunity | Creative |

Select your preferred mode in the **Settings** tab under **Game Mode**.

## Logging

Application logs are stored in `logs/app.log`:

- **File**: Full DEBUG-level logs for troubleshooting
- **Console**: INFO-level logs for live feedback

Check `logs/app.log` if you encounter issues.

## Usage

### Running the UI
```bash
python app_main.py
```

### Running via app.py
```bash
python app.py
```

### Stopping the Server
- UI: **Controls** tab → click **⏹ Stop Server**

## Documentation

This README contains all essential documentation. For advanced features, see:

- **[docs/CONSOLE_TRIGGERS.md](docs/CONSOLE_TRIGGERS.md)** - Advanced console trigger patterns and webhook examples

## Troubleshooting

### Application won't start
- Verify Python 3.9+ is installed: `python --version`
- Install dependencies: `pip install -r requirements.txt`
- Check logs: `logs/app.log`

### Server won't start
- Verify paths in Settings tab
- Check `logs/app.log` for detailed errors
- Ensure firewall allows ports 28015 (server) and 28016 (RCON)

### RCON won't connect
- Verify server is running (Dashboard tab)
- Verify correct host/port in Settings
- Check RCON password is correct

### Settings won't save
- Click "Validate Settings" to see errors
- Verify all paths exist and are accessible
- Check file permissions on `config.yaml`

### Console Triggers not firing
- Enable **Console Triggers** toggle in **Automation** → **⚙️ Settings**
- Check trigger pattern with **Test Pattern** button (should show ✅ Match)
- Verify webhook URL is correct (test with curl first)
- Check server console output matches regex pattern exactly
- See logs for trigger execution details

### Backups not working
- Enable **Backups** toggle in **Automation** → **⚙️ Settings**
- Ensure server is **stopped** before restoring
- Verify disk space for backup (typically 1-5 GB)
- Check file permissions on the data directory
- View backup history table to confirm creation

## Performance

- **UI Memory**: ~100-150 MB idle
- **Config Load**: <100ms
- **Dashboard Refresh**: Configurable (default 2 seconds)
- **RCON Response**: Typical <500ms
- **Backup Speed**: Depends on disk I/O (typically 1-5 minutes)

## Security Notes

- RCON password stored in `config.json` (plain text)
- Set proper file permissions: `chmod 600 config.json` (Linux/Mac)
- Don't share `config.json` file
- Paths are validated to prevent traversal attacks

## Future Enhancements

- [ ] Check actual Rust/Oxide versions from APIs
- [ ] Multi-server support
- [ ] Linux and macOS support
- [ ] Plugin management UI
- [ ] Player management commands
- [ ] Server statistics and graphs
- [ ] Crash restart automation
- [x] Backup/restore functionality
- [x] Enable/disable individual schedules
- [x] Console monitoring with webhooks
- [ ] Config encryption
- [ ] Docker support
- [ ] Web dashboard

## Contributing

Contributions are welcome! Please:
1. Test thoroughly before submitting
2. Follow PEP 8 code style
3. Add type hints and docstrings
4. Update documentation
5. Ensure backward compatibility

## Support

- **GitHub**: https://github.com/8qBITs/RustServerManager
- **Discord**: 8qBIT#0101
- **Issues**: Report bugs on GitHub

## Version History

**v2.1** (Current)
- **New Game Modes**: Vanilla, Softcore, Hardcore, Creative options
- **Enhanced Automation Tab**: Reorganized into 4 intuitive subtabs
  - ⚙️ Settings: Feature toggles for modular control
  - 📅 Scheduler: Enable/disable individual scheduled jobs without deleting
  - 🔔 Console Triggers: Webhook notifications for server events (Discord & generic)
  - 📦 Backups: Full server backup/restore with history
- **Console Monitoring**: Regex pattern matching with Discord embeds
- **Improved UX**: Feature toggles show/hide automation subtabs dynamically
- **Build Support**: PyInstaller instructions for creating standalone .exe

**v2.0** (March 1, 2026)
- Complete rewrite with modern architecture
- PySide6 desktop UI
- RCON console
- Background automation with APScheduler
- Configuration management with Pydantic validation
- Modular, maintainable codebase
- Full backward compatibility

**v1.0** (Original)
- Monolithic script for server installation and startup
- Basic installation/update of Rust server, Oxide, RustEdit
- Simple batch file startup

## License

See [LICENSE](LICENSE) file

## Author

**8qBIT**  
Discord: 8qBIT#0101  
GitHub: https://github.com/8qBITs

---

**Note:** This project is independently maintained and is not affiliated with Rust, Oxide/uMod, or Facepunch Studios.

**Last Updated**: March 2, 2026
