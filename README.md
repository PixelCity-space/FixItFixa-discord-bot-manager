# FixItFixa - Discord Bot Manager

FixItFixa is an enterprise-grade, modular Discord Bot Management system built with Python and `discord.py`. It is engineered to monitor, orchestrate, auto-update, and safely supervise multiple independent Discord bots running in background subprocesses on Windows and Linux systems.

---

## Architecture (4-Layer Clean Architecture)

FixItFixa follows a strictly decoupled, 4-tier layered architecture where presentation, business logic, system interactions, and configuration management are completely isolated:

```
fixitfixa/
├── bot/                          # Layer 4: Presentation & Discord UI
│   ├── cogs/
│   │   ├── management_cog.py     # Admin & Bot lifecycle slash commands
│   │   ├── monitoring_cog.py     # Live persistent status dashboard & task loops
│   │   └── system_cog.py         # Maintenance, diagnostics, sync & aliases
│   ├── ui/
│   │   ├── components/buttons.py # Interactive control buttons (Components V2)
│   │   ├── embeds/               # Structured embeds (e.g. UpdateResultEmbed)
│   │   └── views/                # Discord LayoutViews (ModernStatusView, ModernInfoView)
│   ├── autocomplete.py           # Intelligent Bot ID & cluster autocomplete
│   ├── checks.py                 # Type-safe Role-Based Access Control (RBAC)
│   └── client.py                 # BotManager client & Discord lifecycle
│
├── core/                         # Layer 1-3: Core Services, System & Config
│   ├── common/enums.py           # Layer 1: AccessLevel, BotStatus, ActionType enums
│   ├── config/                   # Layer 1: Dataclasses, ConfigRepository, StateRepository
│   │   ├── models.py             # Strongly-typed configuration models
│   │   ├── config_repository.py  # Thread-safe config.json loader & saver
│   │   └── state_repository.py   # Persistent runtime state manager (state.json)
│   ├── services/                 # Layer 3: Pure Business Logic Services
│   │   ├── bot_lifecycle_service.py # Start/Stop/Restart & cluster orchestration
│   │   ├── update_service.py        # Git pull, dependency install & rollback
│   │   ├── health_service.py        # Process heartbeat & crash detection
│   │   ├── telemetry_service.py     # Resource metrics, Uptime & DB/Log size aggregation
│   │   └── i18n_service.py          # Dynamic multi-language localization engine
│   ├── system/                   # Layer 2: Low-Level OS & Process Handlers
│   │   ├── process_spawner.py    # Subprocess creation (hidden console) & graceful shutdown
│   │   ├── process_tracker.py    # PID tracking & psutil metrics inspection
│   │   ├── metrics_collector.py  # System-wide CPU, RAM, Disk (partition) & Network bandwidth
│   │   ├── git_client.py         # Subprocess Git & Pip execution with path validation
│   │   └── log_rotator.py        # Non-locking copytruncate child bot log rotation
│   ├── icons.py                  # Custom Guild Emoji & Fallback emoji mapping
│   ├── logger.py                 # RotatingFileHandler logging setup
│   └── utils.py                  # Formatting utilities & emoji resolution
│
├── locales/                      # 100% Synchronized Localizations
│   ├── hu.json                   # Hungarian translations (115 keys)
│   └── en.json                   # English translations (115 keys)
│
├── .env.example                  # Environment secrets template
├── config.json                   # Application & managed bot configuration
├── manager.py                    # Application bootstrap & selector event loop policy
└── requirements.txt              # Project dependencies
```

---

## Key Features

* **Modern Discord Components V2 UI**: Paginated interactive status panel featuring real-time CPU, RAM, Network speeds, Uptime, and one-click Restart / Update / Stop buttons.
* **Concurrent Non-Blocking Git Checks**: Fast upstream repository status polling across all bots in background threads using `asyncio.gather` (~600ms total execution).
* **In-Memory Log Streaming**: Zero-disk-I/O log inspection via `io.BytesIO` streaming directly to Discord, eliminating temporary files and Windows file-locking race conditions.
* **Non-Locking Log Rotation (`LogRotator`)**: Safe `copytruncate` rotation mechanism for active child bot log files without interrupting running subprocesses.
* **Safe Rollbacks**: Instant one-click or command-driven Git rollback (`HEAD@{1}`) with automatic dependency rollback if an update fails.
* **Multi-Process Cluster Support**: Group multi-process bots under a common cluster key to safely restart all related processes in synchronized sequence.
* **100% i18n Localization**: Zero hardcoded strings. Switch effortlessly between Hungarian (`hu`) and English (`en`).

---

## Role-Based Access Control (RBAC)

FixItFixa enforces strict 4-tier permission checking via [bot/checks.py](file:///e:/projects/repos/bots/fixitfixa/bot/checks.py):

| Access Level | Role / Permission | Permissions Scope |
| :--- | :--- | :--- |
| **`BOSS`** (3) | Server Owner / Discord Administrator | Full access to all commands anywhere on the server. |
| **`MECHANIC`** (2) | Admin Role (`admin_role_id`) | Full management & control in the designated Admin Workshop channel (`admin_channel_id`). |
| **`INSPECTOR`** (1) | Tester Role (`tester_role_id`) | Monitoring, status view, and read-only log inspection. |
| **`EVERYONE`** (0) | Standard Server Member | Basic public info commands (ephemeral). |

---

## Slash Commands Reference

### Bot Management (Mechanic / Boss)
* `/update bot_id:<ID>` - Git pull, pip install, and restart the specified bot (or bot cluster).
* `/restart bot_id:<ID>` - Restart a bot without pulling new code.
* `/rollback bot_id:<ID>` - Revert repository to the previous Git commit (`HEAD@{1}`) and restart.
* `/logs-rotate bot_id:<ID> [force: True/False]` - Rotate and archive a bot's `bot.log` file if size exceeds limits.

### Monitoring & Logs (Inspector / Mechanic / Boss)
* `/logs bot_id:<ID> [lines: N]` - Fetch the last N lines of a child bot's log (streamed in-memory).
* `/manager-logs [lines: N]` - Fetch the last N lines of FixItFixa's own `manager.log`.
* `/info [public: True/False]` - Display system overview card (ephemeral or public for Admins).

### FixItFixa Self-Management (Mechanic / Boss)
* `/manager-restart` - Cleanly restart FixItFixa itself without dropping running child bots.
* `/manager-update` - Pull latest FixItFixa code, install requirements, and self-restart.

### System & Maintenance (Boss)
* `/sync [spec: guild/global/copy]` - Synchronize application slash commands with Discord API.
* `/clear-commands [spec: guild/global]` - Purge registered application commands.
* `/purge limit:<N>` - Bulk delete messages from the current channel.
* `/ping` - Measure Discord Gateway WebSocket latency.

---

## Configuration Guide (`config.json`)

```json
{
    "guild_id": 123456789012345678,
    "access_control": {
        "admin_channel_id": 123456789012345678,
        "public_channel_id": 123456789012345678,
        "roles": {
            "admin": 123456789012345678,
            "tester": 123456789012345678
        }
    },
    "bot_settings": {
        "manager_name": "FixItFixa",
        "language": "hu",
        "git_branch": "origin/main",
        "check_interval_seconds": 3,
        "status_refresh_seconds": 60,
        "status_recreate_minutes": 58,
        "bot_log_max_bytes": 10485760,
        "bot_log_backup_count": 3
    },
    "ui_settings": {
        "accent_color": 2830129,
        "bots_per_page": 3
    },
    "bots": {
        "1234567890": {
            "name": "My Child Bot",
            "path": "E:\\projects\\bots\\my_child_bot",
            "cmd": "python bot.py",
            "log": "bot.log",
            "db_files": ["database.db"],
            "cluster": "optional_cluster_name"
        }
    }
}
```

---

## Quickstart & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/fixitfixa.git
   cd fixitfixa
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Secrets**:
   ```bash
   cp .env.example .env
   ```
   Add your bot token to `.env`:
   ```env
   DISCORD_TOKEN=your_token_here
   ```

4. **Start FixItFixa**:
   ```bash
   python manager.py
   ```

---

## Code Quality & Linter

FixItFixa strictly complies with modern Python type hints and zero-warning linting standards:

```bash
# Run Ruff linter across entire codebase
python -m ruff check .

# Verify bytecode compilation
python -m compileall .
```
