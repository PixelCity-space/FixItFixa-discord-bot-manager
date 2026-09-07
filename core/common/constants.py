"""System-wide constants and message formatting helpers."""

# Discord Message Limits
DISCORD_MAX_MESSAGE_LENGTH = 2000
DISCORD_TRUNCATE_LIMIT = 1900
DISCORD_TRUNCATE_OUTPUT_LIMIT = 1500
DISCORD_TRUNCATE_HEAD_CHARS = 1000
DISCORD_TRUNCATE_TAIL_CHARS = 800
DISCORD_TRUNCATE_OUTPUT_HEAD = 700
DISCORD_TRUNCATE_OUTPUT_TAIL = 700


def truncate_message(
    text: str,
    max_len: int = DISCORD_TRUNCATE_LIMIT,
    head_len: int = DISCORD_TRUNCATE_HEAD_CHARS,
    tail_len: int = DISCORD_TRUNCATE_TAIL_CHARS,
    separator: str = "\n\n... [TRUNCATED] ...\n\n",
) -> str:
    """Safely truncates long text payloads to fit within Discord message limits."""
    if not text or len(text) <= max_len:
        return text
    return f"{text[:head_len]}{separator}{text[-tail_len:]}"


__all__ = [
    "DISCORD_MAX_MESSAGE_LENGTH",
    "DISCORD_TRUNCATE_LIMIT",
    "DISCORD_TRUNCATE_OUTPUT_LIMIT",
    "DISCORD_TRUNCATE_HEAD_CHARS",
    "DISCORD_TRUNCATE_TAIL_CHARS",
    "DISCORD_TRUNCATE_OUTPUT_HEAD",
    "DISCORD_TRUNCATE_OUTPUT_TAIL",
    "truncate_message",
]
