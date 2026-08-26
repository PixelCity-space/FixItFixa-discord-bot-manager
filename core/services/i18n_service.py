import os
import json
import re
from core.logger import log

class LocalizationService:
    """Manages multi-language translations and dynamic icon placeholder substitution."""
    def __init__(self, default_lang: str = "hu"):
        self.default_lang = default_lang
        self.current_lang = default_lang
        self.translations = {}
        log.info(f"[DEBUG] LocalizationService: Initializing for {default_lang}")
        self.load_translations(default_lang)
        log.info(f"[DEBUG] LocalizationService: Initialization for {default_lang} complete.")

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

    def get(self, key: str, default: str = None, **kwargs) -> str:
        """Gets a translated string and injects icons and dynamic kwargs."""
        text = self.translations.get(key, default or key)

        if not isinstance(text, str):
            text = str(text)

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

    def localize_commands(self, tree, guild=None) -> None:
        """Translates slash command descriptions dynamically."""
        try:
            commands = tree.get_commands(guild=guild)
            for cmd in commands:
                key = f"desc_{cmd.name.replace('-', '_')}"
                if key in self.translations:
                    cmd.description = self.translations[key]
        except Exception as e:
            log.error(f"Error during command localization: {e}")

__all__ = ["LocalizationService"]
