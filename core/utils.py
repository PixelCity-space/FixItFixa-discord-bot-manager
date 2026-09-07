import logging
import os

from core.common.icon_mappings import resolve_icon_for_key
from core.icons import Icons

__all__ = ["get_feedback", "format_desc", "rebuild_icon_cache", "read_file_tail"]

# Setup logger for utilities
log = logging.getLogger("BotManager")

# Predefined icon attributes for fast injection into i18n kwargs
_ICON_ATTRS = [
    "RESTART",
    "UPDATE",
    "STOP",
    "ROCKET",
    "SUCCESS",
    "CONTROLLER",
    "ERROR",
    "WARNING",
    "ALERT",
    "LOG",
    "PACKAGE",
    "SHIELD",
    "ROLLBACK",
    "DOT_GREEN",
    "DOT_RED",
    "DOT_YELLOW",
    "UP",
    "DOWN",
    "WRENCH",
    "GEAR",
    "WAVE",
    "ACTIVITY_UP",
    "ACTIVITY_DOWN",
    "SHIELD_LIGHT",
    "CARET_LEFT",
    "CARET_RIGHT",
]

# Pre-computed cached dictionary to eliminate per-call reflection overhead
_CACHED_ICON_MAP: dict[str, str] = {attr: str(getattr(Icons, attr)) for attr in _ICON_ATTRS if hasattr(Icons, attr)}


def rebuild_icon_cache() -> None:
    """Rebuilds the cached icon dictionary when custom emojis are dynamically reconfigured."""
    global _CACHED_ICON_MAP
    _CACHED_ICON_MAP = {attr: str(getattr(Icons, attr)) for attr in _ICON_ATTRS if hasattr(Icons, attr)}


def get_feedback(i18n, key: str, **kwargs) -> str:
    """
    Returns a translated string prefixed with the appropriate emoji.
    Uses pre-cached icon map for maximum execution speed without reflection loops.
    """
    emoji = resolve_icon_for_key(key)

    # Fast single C-level dict merge with pre-computed icon map
    merged_kwargs = {**_CACHED_ICON_MAP, **kwargs}

    text = i18n.get(key, **merged_kwargs) if i18n else key

    # If emoji is None (failed load), use empty string
    emoji_str = str(emoji) if emoji is not None else ""

    # If the text already contains the emoji (manual placeholder in JSON), don't double it
    if emoji_str and emoji_str in text:
        return text

    if not text:
        return emoji_str.strip()

    return f"{emoji_str} {text}".strip()


def format_desc(bot, text: str, guild=None) -> str:
    """
    Fills placeholders in command descriptions with actual channel and role names.
    Consistent with the Watcher Bot's dynamic description system.
    """
    if not text:
        return text

    # Default values from IDs (use Discord mention syntax for better linking)
    admin_val = f"<#{bot.admin_channel_id}>" if getattr(bot, "admin_channel_id", None) else "N/A"
    public_val = f"<#{bot.public_channel_id}>" if getattr(bot, "public_channel_id", None) else "N/A"
    admin_role_val = f"<@&{bot.admin_role_id}>" if getattr(bot, "admin_role_id", None) else "N/A"
    tester_role_val = f"<@&{bot.tester_role_id}>" if getattr(bot, "tester_role_id", None) else "N/A"

    return text.format(
        admin_channel=admin_val,
        public_channel=public_val,
        admin_role=admin_role_val,
        tester_role=tester_role_val,
        bot_name=getattr(bot, "manager_name", "Bot Manager"),
    )


def read_file_tail(file_path: str, max_lines: int, buffer_size: int = 8192) -> list[str]:
    """Reads the last max_lines from a file by seeking backwards from EOF in buffer chunks.

    Runs in O(lines) time with minimal constant memory, avoiding reading entire multi-GB files.
    """
    if max_lines <= 0 or not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            if file_size == 0:
                return []

            pos = file_size

            # If the file ends with a trailing newline, skip it so we don't return an extra empty line
            f.seek(max(0, file_size - 1), os.SEEK_SET)
            if f.read(1) == b"\n":
                pos = file_size - 1
                if pos > 0:
                    f.seek(pos - 1, os.SEEK_SET)
                    if f.read(1) == b"\r":
                        pos -= 1

            if pos == 0:
                return []

            remainder = b""
            collected: list[bytes] = []

            while pos > 0 and len(collected) < max_lines:
                read_size = min(buffer_size, pos)
                pos -= read_size
                f.seek(pos, os.SEEK_SET)
                chunk = f.read(read_size) + remainder
                chunk_lines = chunk.split(b"\n")
                remainder = chunk_lines[0]
                collected = chunk_lines[1:] + collected

            if remainder and len(collected) < max_lines:
                collected = [remainder] + collected

            selected = collected[-max_lines:]
            result = []
            for raw_line in selected:
                decoded = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                result.append(decoded + "\n")
            return result
    except (PermissionError, OSError) as e:
        log.warning(f"[read_file_tail] Failed to read tail from {file_path}: {e}")
        return []
