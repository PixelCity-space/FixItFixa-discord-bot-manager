# FixItFixa Developer & API Reference

This document provides technical reference documentation for the core services, interfaces, and utilities in FixItFixa.

---

## 1. Service Container (`core.container.ServiceContainer`)

The centralized Dependency Injection container managing service lifecycles.

### Methods
* `register(key: str, service: Any, service_type: Optional[Type] = None) -> None`: Registers a service instance.
* `get(key_or_type: Any, default: Any = None) -> Any`: Resolves a registered service.
* `has(key_or_type: Any) -> bool`: Checks if a service exists in the container.
* `create_default(base_dir: str, notify_callback=None, alert_callback=None) -> ServiceContainer`: Assembles the full production dependency graph.

---

## 2. Core Interfaces (`core.interfaces`)

Protocols defining the contracts between components:

* `IProcessSpawner`: Process creation, termination, and systemd management.
* `IProcessTracker`: Process liveness, PID discovery, and status inspection.
* `IGitClient`: Git commit inspection, fetch, update, and rollback.
* `ILogRotator`: File rotation with size threshold checks.
* `IConfigRepository`: Configuration loading, validation, and atomic saving.
* `IStateRepository`: Dynamic runtime state get/set/save.
* `ILocalizationService`: Multi-language message formatting and pluralization.
* `IBotLifecycleService`: Bot process start/stop/restart orchestration.
* `IUpdateService`: Full Git update and rollback workflows.
* `IHealthService`: Health checks and crash detection.
* `ITelemetryService`: Real-time system and bot telemetry aggregation.

---

## 3. Configuration Management (`core.config`)

* `ConfigValidator.validate(data: dict) -> List[ValidationError]`: Validates raw dictionary against schema rules.
* `ConfigRepository(config_path: str)`:
  * `load() -> AppConfig`: Thread-safe configuration load and validation.
  * `save(raw_data: Optional[dict] = None) -> bool`: Atomic save using temporary files.
  * `save_async(...) -> Coroutine[bool]`: Non-blocking worker thread save.
* `StateRepository(state_path: str)`:
  * `get(key: str, default: Any = None) -> Any`: Thread-safe state retrieval.
  * `set(key: str, value: Any, auto_save: bool = True) -> None`: Thread-safe state mutation.
  * `save() -> bool`: Atomic state serialization.

---

## 4. Observability & Logging (`core.logger`, `core.services.metrics_exporter`)

* `trace_context(trace_id: Optional[str] = None)`: Context manager generating or binding a trace / correlation ID.
* `JsonFormatter`: Single-line JSON formatter compatible with ELK, Grafana Loki, and Datadog.
* `MetricsExporter.to_prometheus(manager_metrics, bots_metrics) -> str`: Standard Prometheus metric text format.
* `MetricsExporter.to_json_snapshot(manager_metrics, bots_metrics) -> dict`: Structured observability snapshot.

---

## 5. Security & Rate Limiting (`core.common`, `core.system`)

* `ProcessSpawner.validate_command(cmd: str) -> Tuple[bool, Optional[str]]`: Rejects dangerous shell metacharacters (`;&|><$`).
* `GitClient.is_safe_ref(ref: str) -> bool`: Sanitizes Git branch and revision strings.
* `InteractionRateLimiter.is_limited(user_id: int, action: str, cooldown: float) -> Tuple[bool, float]`: Sliding-window interaction cooldown.
* `is_subpath_or_equal(child: str, parent: str) -> bool`: Robust cross-platform path equivalence.
