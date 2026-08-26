from discord.ui import LayoutView, Container, TextDisplay, Separator, Section, Thumbnail
from core.utils import get_feedback, format_desc

class ModernInfoView(LayoutView):
    """A premium, modern intro view for FixItFixa using Components V2 layout."""
    def __init__(self, bot, i18n, guild=None):
        ui = getattr(bot, 'ui_settings', {})
        accent = ui.get("accent_color", 0x2b2d31)
        super().__init__(timeout=None)

        container = Container(accent_color=accent)

        # Header with bot name and avatar
        avatar_url = bot.user.display_avatar.url if (bot.user and hasattr(bot.user, 'display_avatar')) else "https://cdn.discordapp.com/embed/avatars/0.png"
        container.add_item(Section(
            f"# {get_feedback(i18n, 'INFO_TITLE', bot_name=bot.manager_name)}",
            accessory=Thumbnail(avatar_url)
        ))

        container.add_item(Separator())

        # Description
        raw_desc = i18n.translations.get("INFO_DESC", "INFO_DESC")
        container.add_item(TextDisplay(format_desc(bot, raw_desc, guild)))

        container.add_item(Separator())

        # Features
        raw_features_title = get_feedback(i18n, 'INFO_FEATURES_TITLE')
        raw_features_desc = i18n.translations.get("INFO_FEATURES_DESC", "INFO_FEATURES_DESC")
        features_combined = f"**{raw_features_title}**\n{raw_features_desc}"
        container.add_item(TextDisplay(format_desc(bot, features_combined, guild)))

        container.add_item(Separator())

        # Footer
        container.add_item(TextDisplay(f"*{get_feedback(i18n, 'INFO_FOOTER')}*"))

        self.add_item(container)
