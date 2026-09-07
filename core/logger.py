import contextlib
import contextvars
import datetime
import json
import logging
import os
import sys
import uuid
from logging.handlers import RotatingFileHandler

# Default configuration
LOG_FILE = "manager.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3

# Correlation ID Context Variable
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Returns the correlation ID of the current execution context."""
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Sets the correlation ID for the current execution context."""
    _correlation_id_var.set(correlation_id)


@contextlib.contextmanager
def trace_context(trace_id: str | None = None):
    """Context manager for scoping operations with a correlation / trace ID."""
    token = None
    new_id = trace_id or f"tr_{uuid.uuid4().hex[:8]}"
    try:
        token = _correlation_id_var.set(new_id)
        yield new_id
    finally:
        if token is not None:
            _correlation_id_var.reset(token)


class CorrelationFilter(logging.Filter):
    """Injects correlation_id and formatted correlation prefix into all LogRecords."""

    def filter(self, record: logging.LogRecord) -> bool:
        cid = get_correlation_id()
        record.correlation_id = cid
        record.corr_prefix = f" [{cid}]" if cid else ""
        return True


class JsonFormatter(logging.Formatter):
    """Formats log records as structured, single-line JSON strings (ELK/Loki/Datadog compatible)."""

    def format(self, record: logging.LogRecord) -> str:
        cid = getattr(record, "correlation_id", get_correlation_id())
        log_entry = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": cid or None,
            "process_id": record.process,
            "thread_name": record.threadName,
            "file": record.filename,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(
    name="BotManager",
    log_file=LOG_FILE,
    max_bytes=MAX_BYTES,
    backup_count=BACKUP_COUNT,
    enable_json=False,
    json_file=None,
):
    """Configures the primary application logger with human-readable and optional JSON file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addFilter(CorrelationFilter())

    # Avoid duplicate handlers on reload
    if not logger.handlers:
        std_formatter = logging.Formatter("%(asctime)s - %(name)s%(corr_prefix)s - %(levelname)s - %(message)s")

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(std_formatter)
        console_handler.addFilter(CorrelationFilter())
        logger.addHandler(console_handler)

        # Standard Rotating File Handler
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        file_handler.setFormatter(std_formatter)
        file_handler.addFilter(CorrelationFilter())
        logger.addHandler(file_handler)

        # Optional JSON Rotating File Handler
        if enable_json or json_file:
            target_json_path = json_file or f"{os.path.splitext(log_file)[0]}.json.log"
            json_handler = RotatingFileHandler(
                target_json_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            json_handler.setFormatter(JsonFormatter())
            json_handler.addFilter(CorrelationFilter())
            logger.addHandler(json_handler)

    return logger


def reconfigure_log(log_file, max_bytes, backup_count, enable_json=False, json_file=None):
    """Reconfigures the existing logger with new file settings."""
    logger = logging.getLogger("BotManager")
    logger.addFilter(CorrelationFilter())

    # Remove old file handlers
    for handler in logger.handlers[:]:
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()

    # Add new standard file handler
    std_formatter = logging.Formatter("%(asctime)s - %(name)s%(corr_prefix)s - %(levelname)s - %(message)s")
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    file_handler.setFormatter(std_formatter)
    file_handler.addFilter(CorrelationFilter())
    logger.addHandler(file_handler)

    # Add optional JSON file handler
    if enable_json or json_file:
        target_json_path = json_file or f"{os.path.splitext(log_file)[0]}.json.log"
        json_handler = RotatingFileHandler(
            target_json_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        json_handler.setFormatter(JsonFormatter())
        json_handler.addFilter(CorrelationFilter())
        logger.addHandler(json_handler)

    logger.info(f"Logger reconfigured: {log_file} (Max: {max_bytes}, Backups: {backup_count})")


def setup_discord_logging(log_file, max_bytes, backup_count, level=logging.INFO):
    """Sets up the 'discord' logger with clean default INFO level to prevent debug gateway noise."""
    logger = logging.getLogger("discord")
    logger.setLevel(level)
    logger.addFilter(CorrelationFilter())

    # Remove old handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    std_formatter = logging.Formatter("%(asctime)s - %(name)s%(corr_prefix)s - %(levelname)s - %(message)s")

    # File Handler
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    file_handler.setFormatter(std_formatter)
    file_handler.addFilter(CorrelationFilter())
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(std_formatter)
    console_handler.addFilter(CorrelationFilter())
    logger.addHandler(console_handler)


# Create a default instance for easy import
log = setup_logger()

__all__ = [
    "log",
    "setup_logger",
    "reconfigure_log",
    "setup_discord_logging",
    "get_correlation_id",
    "set_correlation_id",
    "trace_context",
    "CorrelationFilter",
    "JsonFormatter",
]
