import discord
from core.utils import get_feedback

class UpdateResultEmbed(discord.Embed):
    """A premium embed for displaying git update and rollback results."""
    def __init__(self, i18n, title, details, ui_settings=None, is_rollback=False):
        color_val = 0x2ecc71  # Green default
        if is_rollback:
            color_val = 0xe67e22  # Orange default

        if ui_settings:
            if is_rollback:
                color_val = ui_settings.get("update_rollback_color", color_val)
            else:
                color_val = ui_settings.get("update_success_color", color_val)

        super().__init__(
            title=title,
            description=f"**{details['message']}**" if details else get_feedback(i18n, "update_success"),
            color=discord.Color(color_val),
            timestamp=discord.utils.utcnow()
        )

        if details:
            if "hash" in details:
                self.add_field(name=get_feedback(i18n, "hash"), value=f"`{details['hash']}`", inline=True)
            if "date" in details:
                self.add_field(name=get_feedback(i18n, "date"), value=f"<t:{details['date']}:R>", inline=True)

            if details.get("pip_status"):
                self.add_field(name=get_feedback(i18n, "pip_deps"), value=f"`{details['pip_status']}`", inline=False)

            if details.get("repo_url"):
                label = get_feedback(i18n, "open_on_web")
                self.add_field(name=get_feedback(i18n, "git_repo"), value=f"[{label}]({details['repo_url']})", inline=False)

        self.set_footer(text=get_feedback(i18n, "update_footer"))
