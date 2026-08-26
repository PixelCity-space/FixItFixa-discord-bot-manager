# FixItFixa System Architecture

FixItFixa is designed following the **Clean Architecture** paradigm, ensuring separation of concerns, testability, and independence from external frameworks (such as Discord API or host OS quirks).

---

## Architectural Layers

```mermaid
graph TD
    subgraph Layer4["Layer 4: Presentation (bot/)"]
        ManagementCog["ManagementCog"]
        MonitoringCog["MonitoringCog"]
        SystemCog["SystemCog"]
        Buttons["UI Buttons / Components V2"]
        Views["Status & Info Views"]
    end

    subgraph Layer3["Layer 3: Business Services (core/services/)"]
        LifecycleService["BotLifecycleService"]
        UpdateService["UpdateService"]
        HealthService["HealthService"]
        TelemetryService["TelemetryService"]
        I18nService["LocalizationService"]
        MetricsExporter["MetricsExporter"]
    end

    subgraph Layer2["Layer 2: System Infrastructure (core/system/)"]
        ProcessSpawner["ProcessSpawner"]
        ProcessTracker["ProcessTracker"]
        GitClient["GitClient"]
        LogRotator["LogRotator"]
        MetricsCollector["MetricsCollector"]
        PathUtils["PathUtils"]
    end

    subgraph Layer1["Layer 1: Configuration & Common (core/config/, core/common/)"]
        ConfigRepo["ConfigRepository"]
        StateRepo["StateRepository"]
        ConfigValidator["ConfigValidator"]
        Models["AppConfig & BotConfig Models"]
        RateLimiter["InteractionRateLimiter"]
        Retry["Retry Mechanisms"]
    end

    subgraph DI["Dependency Injection"]
        ServiceContainer["ServiceContainer"]
    end

    Layer4 --> Layer3
    Layer3 --> Layer2
    Layer3 --> Layer1
    Layer2 --> Layer1
    ServiceContainer -.-> Layer3
    ServiceContainer -.-> Layer2
    ServiceContainer -.-> Layer1
```

---

## 1. Presentation Layer (`bot/`)
* **`BotManager` (`client.py`)**: Responsible solely for Discord client connection, gateway events, command tree syncing, and presence updates.
* **Cogs (`cogs/`)**: Discord slash command and prefix router endpoints.
* **UI Views & Components (`ui/`)**: LayoutViews and interactive action buttons for user interactions.

## 2. Business Services Layer (`core/services/`)
* **`BotLifecycleService`**: Manages start, stop, restart, and synchronized multi-bot actions.
* **`UpdateService`**: Handles Git pulling, dependency installations, rollbacks, and process reloading.
* **`HealthService`**: Background process monitoring and automatic crash recovery callbacks.
* **`TelemetryService`**: Aggregates CPU, RAM, disk, network, and uptime metrics.
* **`LocalizationService`**: Pluralized, key-based multi-language string formatting.
* **`MetricsExporter`**: Generates Prometheus and JSON metric snapshots.

## 3. System Infrastructure Layer (`core/system/`)
* **`ProcessSpawner`**: Spawns isolated background processes (`CREATE_NEW_PROCESS_GROUP`) with shell injection prevention.
* **`ProcessTracker`**: Fast psutil process inspection and live PID tracking.
* **`GitClient`**: Subprocess Git operations with branch/ref security sanitization.
* **`LogRotator`**: Copytruncate log file archival without interrupting running bots.
* **`PathUtils`**: Cross-platform path equivalence, UNC share handling, and subpath validation.

## 4. Configuration & Common Layer (`core/config/`, `core/common/`)
* **`ConfigRepository` & `StateRepository`**: Thread-safe (`RLock`), atomic (`os.replace`) JSON storage.
* **`ConfigValidator`**: Pre-startup and pre-save schema validation.
* **`InteractionRateLimiter`**: Sliding-window cooldown protecting Discord buttons.
