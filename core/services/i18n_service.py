import os
import json
import re
from typing import Optional, Dict, Any
from core.logger import log

class LocalizationService:
    """Manages multi-language translations, pluralization rules, and dynamic icon placeholder substitution."""
    def __init__(self, default_lang: str = "hu"):
        self.default_lang = default_lang
        self.current_lang = default_lang
        self.translations: Dict[str, Any] = {}
        log.debug(f"[LocalizationService] Initializing for {default_lang}")
        self.load_translations(default_lang)
        log.debug(f"[LocalizationService] Initialization for {default_lang} complete.")

    def load_translations(self, lang: str) -> None:
        """Loads translations from locales/{lang}.json with fallbacks."""
        self.current_lang = lang

        try:
            # Resolves repository root directory (../../ from core/services/)
            current_file_path = os.path.abspath(__file__)
            services_dir = os.path.dirname(current_file_path)
            core_dir = os.path.dirname(services_dir)
            base_dir = os.path.dirname(core_dir)

            locales_dir = os.path.join(base_dir, "locales")
            file_path = os.path.normpath(os.path.join(locales_dir, f"{lang}.json"))

            log.info(f"[Localization] Initializing {lang} from: {file_path}")

            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        new_data = json.load(f)
                        self.translations.clear()
                        self.translations.update(new_data)
                    log.info(f"[Localization] Successfully loaded {len(self.translations)} keys from {file_path}")
                except Exception as e:
                    log.error(f"[Localization] Error reading {file_path}: {e}")
                    if lang != "hu":
                        self.load_translations("hu")
            else:
                log.warning(f"[Localization] File NOT FOUND at: {file_path}")
                root_fallback = os.path.join(base_dir, f"{lang}.json")
                if os.path.exists(root_fallback):
                    log.info(f"[Localization] Found fallback in root: {root_fallback}")
                    with open(root_fallback, "r", encoding="utf-8") as f:
                        self.translations.clear()
                        self.translations.update(json.load(f))
                elif lang != "hu":
                    self.load_translations("hu")

        except Exception as e:
            log.error(f"[Localization] Fatal error in load_translations: {e}")

    def get_plural_category(self, lang: str, count: int | float) -> str:
        """Determines the Unicode CLDR plural category for the given language and count.
        
        Supported categories: 'zero', 'one', 'two', 'few', 'many', 'other'.
        """
        lang_prefix = lang.lower().split("-")[0].split("_")[0]

        try:
            n = abs(float(count))
            is_int = n.is_integer()
            i = int(n)
        except (ValueError, TypeError):
            return "other"

        # Hungarian (numbers are followed by singular nouns: 1 nap, 5 nap)
        if lang_prefix == "hu":
            return "other"

        # English and Germanic/Romance standard rule
        if lang_prefix in ("en", "de", "nl", "sv", "da", "no", "it", "es", "pt"):
            return "one" if (is_int and i == 1) else "other"

        # French (0 and 1 take singular)
        if lang_prefix == "fr":
            return "one" if (is_int and 0 <= i <= 1) else "other"

        return "one" if (is_int and i == 1) else "other"

    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Gets a translated string, resolving plural forms, icons, and dynamic kwargs."""
        raw_val = self.translations.get(key, default if default is not None else key)

        if isinstance(raw_val, dict):
            # Resolve count from kwargs
            count_val = None
            if "count" in kwargs:
                count_val = kwargs["count"]
            else:
                # Look for common numeric parameter names
                for k, v in kwargs.items():
                    if isinstance(v, (int, float)):
                        count_val = v
                        break

            category = self.get_plural_category(self.current_lang, count_val if count_val is not None else 1)
            text = raw_val.get(category) or raw_val.get("other") or raw_val.get("one") or (list(raw_val.values())[0] if raw_val else key)
        elif not isinstance(raw_val, str):
            text = str(raw_val)
        else:
            text = raw_val

        # Support Icon placeholders like {SUCCESS} or {ERROR}
        if "{" in text:
            try:
                from core.icons import Icons
                placeholders = re.findall(r"\{([A-Z0-9_]+)\}", text)
                for p in placeholders:
                    if hasattr(Icons, p):
                        icon_val = getattr(Icons, p)
                        text = text.replace(f"{{{p}}}", str(icon_val))
            except Exception as e:
                log.error(f"[Localization] Icon replacement failed for '{key}': {e}")

        # Support for dynamic variables (.format(**kwargs))
        try:
            return text.format(**kwargs)
        except Exception as e:
            log.error(f"Error formatting translation key '{key}': {e}")
            return text

    def get_plural(self, key: str, count: int | float, default: Optional[str] = None, **kwargs) -> str:
        """Explicit helper method for pluralized translations."""
        return self.get(key, default=default, count=count, **kwargs)

    def localize_commands(self, tree, guild=None) -> None:
        """Translates slash command descriptions dynamically."""
        try:
            commands = tree.get_commands(guild=guild)
            for cmd in commands:
                key = f"desc_{cmd.name.replace('-', '_')}"
                if key in self.translations:
                    desc_val = self.translations[key]
                    if isinstance(desc_val, str):
                        cmd.description = desc_val
        except Exception as e:
            log.error(f"Error during command localization: {e}")

__all__ = ["LocalizationService"]
