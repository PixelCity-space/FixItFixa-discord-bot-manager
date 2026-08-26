# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] - 2026-08-26

### Added
* **Formal Interfaces & Protocols (`core/interfaces/`)**: Introduced `IProcessSpawner`, `IProcessTracker`, `IGitClient`, `ILogRotator`, `IConfigRepository`, `IStateRepository`, `ILocalizationService`, `IBotLifecycleService`, `IUpdateService`, `IHealthService`, and `ITelemetryService` for complete testability and decoupling.
* **ServiceContainer (`core/container.py`)**: Centralized Dependency Injection & Service Registry container, eliminating the God Object pattern from `BotManager`.
* **Configuration Schema Validation (`core/config/validator.py`)**: Semantic and schema validation for `config.json` with human-readable error messages and save-time integrity enforcement.
* **Structured JSON Logging (`core/logger.py`)**: Added `JsonFormatter` (ELK, Datadog, Loki compatible) alongside standard human-readable console/file loggers.
* **Correlation ID & Trace Context (`core/logger.py`)**: `contextvars`-based request/interaction tracking with `trace_context()` and `CorrelationFilter`.
* **Prometheus & JSON Metrics Exporters (`core/services/metrics_exporter.py`)**: Real-time Prometheus metrics export (`fixitfixa_bot_cpu_percent`, `fixitfixa_bot_running`, `fixitfixa_manager_ram_mb`, etc.).
* **Security Hardening**:
  * Shell injection protection and forbidden metacharacter validation in `ProcessSpawner`.
  * Git branch/ref regex sanitization in `GitClient`.
  * Interaction rate limiting (`InteractionRateLimiter`) on Discord control buttons.
  * Sudo / systemctl privilege checking and diagnostics for Linux hosts.
* **Concurrency & Thread Safety**:
  * `threading.RLock()` protection for `StateRepository` and `ConfigRepository`.
  * Atomic file persistence via temporary file flush + `os.replace`.
  * Tracked background task execution in `MonitoringCog` (`create_tracked_task`) with unhandled exception callbacks.
* **Cross-Platform Path Normalization (`core/system/path_utils.py`)**:
  * `normalize_path_cross_platform()`, `paths_are_equivalent()`, and `is_subpath_or_equal()` handling UNC shares, drive mappings, symlinks, and case-insensitivity.
* **Type Safety**:
  * `TypedDict` schemas (`UiSettingsDict`, `BotConfigDict`, `AppConfigDict`).
  * Dedicated `UiConfig` dataclass.
  * `ClassVar` typing on `Icons`.
  * `mypy.ini` and `pyproject.toml` tool configuration.
* **Pluralization Support**: Added numeric count rules and plural dictionaries for Hungarian (`hu`) and English (`en`).

### Changed
* Refactored inline magic numbers and 100+ icon mappings to dedicated `constants.py` and `icon_mappings.py`.
* Modernized test suite with `conftest.py`, shared fixtures, and native async pytest execution (229+ unit & integration tests, 90% coverage).
* Tuned Discord logger to `INFO` level to eliminate heartbeat debug noise.

---

## [2.0.0] - 2026-08-20

### Added
* 4-Layer decoupled Clean Architecture structure (`bot/`, `core/system/`, `core/services/`, `core/config/`).
* Discord Components V2 interactive dashboard with live status cards.
* Multi-process cluster coordination support.
* Non-locking `LogRotator` with copytruncate mechanics.
* Dual Hungarian / English localization engine (`locales/hu.json`, `locales/en.json`).

---

## [1.0.0] - 2026-08-01

### Added
* Initial release of Discord Bot Manager.
* Basic subprocess spawn, stop, and restart functionality.
* Git pull and automatic pip dependency installation.
