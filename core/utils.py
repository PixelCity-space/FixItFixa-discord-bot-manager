import logging
from typing import Dict
from core.icons import Icons
from core.common.icon_mappings import resolve_icon_for_key

__all__ = [
    "get_feedback",
    "format_desc",
    "rebuild_icon_cache"
]

# Setup logger for utilities
log = logging.getLogger("BotManager")

# Predefined icon attributes for fast injection into i18n kwargs
_ICON_ATTRS = [
    "RESTART", "UPDATE", "STOP", "ROCKET", "SUCCESS",
    "CONTROLLER", "ERROR", "WARNING", "ALERT", "LOG", "PACKAGE", "SHIELD",
    "ROLLBACK", "DOT_GREEN", "DOT_RED", "DOT_YELLOW", "UP", "DOWN",
    "WRENCH", "GEAR", "WAVE", "ACTIVITY_UP", "ACTIVITY_DOWN", "SHIELD_LIGHT",
    "CARET_LEFT", "CARET_RIGHT"
]

# Pre-computed cached dictionary to eliminate per-call reflection overhead
_CACHED_ICON_MAP: Dict[str, str] = {
    attr: str(getattr(Icons, attr))
    for attr in _ICON_ATTRS
    if hasattr(Icons, attr)
}

def rebuild_icon_cache() -> None:
    """Rebuilds the cached icon dictionary when custom emojis are dynamically reconfigured."""
    global _CACHED_ICON_MAP
    _CACHED_ICON_MAP = {
        attr: str(getattr(Icons, attr))
        for attr in _ICON_ATTRS
        if hasattr(Icons, attr)
    }

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
        bot_name=getattr(bot, 'manager_name', 'Bot Manager')
    )
