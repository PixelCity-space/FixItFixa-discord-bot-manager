import discord
from typing import ClassVar, Optional, Union

EmojiType = Optional[Union[str, discord.PartialEmoji, discord.Emoji]]

class Icons:
    RESTART: ClassVar[EmojiType] = None
    UPDATE: ClassVar[EmojiType] = None
    STOP: ClassVar[EmojiType] = None
    
    # Standard UI Icons (consistent with Watcher Bot)
    ROCKET: ClassVar[EmojiType] = None
    SUCCESS: ClassVar[EmojiType] = None
    CONTROLLER: ClassVar[EmojiType] = None
    ERROR: ClassVar[EmojiType] = None
    WARNING: ClassVar[EmojiType] = None
    
    # New Visual Elements
    ALERT: ClassVar[EmojiType] = None
    LOG: ClassVar[EmojiType] = None
    PACKAGE: ClassVar[EmojiType] = None
    SHIELD: ClassVar[EmojiType] = None
    SHIELD_LIGHT: ClassVar[EmojiType] = None
    ROLLBACK: ClassVar[EmojiType] = None
    DOT_GREEN: ClassVar[EmojiType] = None
    DOT_RED: ClassVar[EmojiType] = None
    DOT_YELLOW: ClassVar[EmojiType] = None
    UP: ClassVar[EmojiType] = None
    DOWN: ClassVar[EmojiType] = None
    WRENCH: ClassVar[EmojiType] = None
    GEAR: ClassVar[EmojiType] = None
    WAVE: ClassVar[EmojiType] = None
    ACTIVITY_UP: ClassVar[EmojiType] = None
    ACTIVITY_DOWN: ClassVar[EmojiType] = None
    CARET_LEFT: ClassVar[EmojiType] = None
    CARET_RIGHT: ClassVar[EmojiType] = None
    
    @classmethod
    async def setup_async(cls, bot: discord.Client):
        """Asynchronously fetches application emojis to ensure they are in cache and mapped."""
        from core.logger import log
        try:
            # Application emojis are available via fetch_application_emojis
            app_emojis = await bot.fetch_application_emojis()
            log.info(f"[Icons] Fetched {len(app_emojis)} application emojis.")
            
            # Map them by name if they are in our expected set
            for e in app_emojis:
                if e.name == "arrowclockwise":
                    cls.RESTART = e
                    log.info(f"[Icons]   Mapped {e.name} as RESTART icon (Full Emoji)")
                elif e.name == "arrowsclockwise":
                    cls.UPDATE = e
                    log.info(f"[Icons]   Mapped {e.name} as UPDATE icon (Full Emoji)")
                elif e.name == "power":
                    cls.STOP = e
                    log.info(f"[Icons]   Mapped {e.name} as STOP icon (Full Emoji)")
                    
        except Exception as e:
            log.error(f"[Icons] Failed to fetch/map application emojis: {e}")

    @classmethod
    def setup(cls, config):
        """Initializes all icons from config or defaults."""
        from core.logger import log
        
        # Default emojis (consistent with Watcher Bot where applicable)
        defaults = {
            "restart": "🔄", 
            "update": "🆙", 
            "stop": "⏹️",
            "ROCKET": "🚀", "SUCCESS": "✅",
            "CONTROLLER": "🎮", "ERROR": "❌",
            "WARNING": "⚠️",
            "ALERT": "🚨", "LOG": "📄", "PACKAGE": "📦", "SHIELD": "🛡️", "SHIELD_LIGHT": "🛡️", "ROLLBACK": "⏮️",
            "DOT_GREEN": "🟢", "DOT_RED": "🔴", "DOT_YELLOW": "🟡",
            "UP": "⬆️", "DOWN": "⬇️",
            "WRENCH": "🔧", "GEAR": "⚙️", "WAVE": "📶",
            "ACTIVITY_UP": "⬆️", "ACTIVITY_DOWN": "⬇️",
            "CARET_LEFT": "◀", "CARET_RIGHT": "▶"
        }

        # Extract provided data from config object or dict
        provided_data = {}
        if hasattr(config, "emojis"):
            provided_data = config.emojis
        elif isinstance(config, dict):
            provided_data = config.get("emojis", {})

        # Normalize provided data to uppercase keys for easier mapping
        normalized_data = {k.upper(): v for k, v in provided_data.items()}
        
        log.info(f"[Icons] Setting up with {len(normalized_data)} custom emojis.")
        
        def parse_emoji(name, val):
            # Manual parse for custom emojis if from_str is failing in some environments
            if isinstance(val, str) and val.startswith("<") and ":" in val:
                try:
                    parts = val.strip("<>").split(":")
                    if len(parts) >= 3:
                        # Format is <:name:id> or <a:name:id>
                        eid = int(parts[-1])
                        ename = parts[-2]
                        eanim = parts[0] == "a"
                        pe = discord.PartialEmoji(name=ename, id=eid, animated=eanim)
                        return pe
                except Exception as e:
                    log.error(f"[Icons] Manual parse failed for {val}: {e}")
            
            try:
                return discord.PartialEmoji.from_str(val)
            except Exception as e:
                log.error(f"[Icons] discord.py failed to parse {val}: {e}")
                return discord.PartialEmoji.from_str("❓")

        # Define all supported icon keys (mapping to class attributes)
        # We handle the legacy lowercase ones (restart, update, stop) by mapping them to their uppercase counterparts
        all_keys = [
            "RESTART", "UPDATE", "STOP", "ROCKET", "SUCCESS", 
            "CONTROLLER", "ERROR", "WARNING", "ALERT", "LOG", "PACKAGE", "SHIELD", 
            "ROLLBACK", "DOT_GREEN", "DOT_RED", "DOT_YELLOW", "UP", "DOWN",
            "WRENCH", "GEAR", "WAVE", "ACTIVITY_UP", "ACTIVITY_DOWN", "SHIELD_LIGHT",
            "CARET_LEFT", "CARET_RIGHT"
        ]
        
        for key in all_keys:
            # We check normalized_data (uppercase) first
            val = normalized_data.get(key) or defaults.get(key.lower()) or defaults.get(key)
            if not val:
                val = "❓"
            
            setattr(cls, key, parse_emoji(key, val))
            # log.debug(f"[Icons]   {key} -> {getattr(cls, key)}")

# Default initialization
class DefaultConfig:
    emojis = {}

Icons.setup(DefaultConfig())

