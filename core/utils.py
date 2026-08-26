import logging
from core.icons import Icons

__all__ = [
    "get_feedback",
    "format_desc",
]

# Setup logger for utilities
log = logging.getLogger("BotManager")

def get_feedback(i18n, key: str, **kwargs) -> str:
    """
    Returns a translated string prefixed with the appropriate emoji.
    Compatible with the Watcher Bot system.
    """
    # Mapping keys to Icons (consistent with Watcher Bot logic)
    icons_map = {
        # --- Errors (❌) : Critical / Blocking failures ---
        "error_generic": Icons.ERROR,
        "error_git_update_failed": Icons.ERROR,
        "error_update_failed_output": Icons.ERROR,
        "error_update_general": Icons.ERROR,
        "error_no_token": Icons.ERROR,
        "error_rollback": Icons.ERROR,
        "error_log_fetch": Icons.ERROR,
        "error_log_not_found": Icons.ERROR,
        "error_manager_log_not_found": Icons.ERROR,
        "pip_error": Icons.ERROR,
        "purge_error": Icons.ERROR,
        "status_failed": Icons.ERROR,
        "status_error_prefix": Icons.ERROR,
        "status_error": Icons.ERROR,

        # --- Warnings (⚠️) : Non-blocking/User input errors ---
        "warning_generic": Icons.WARNING,
        "update_available": Icons.WARNING,
        "error_no_requirements": Icons.WARNING,
        "error_no_bots_configured": Icons.WARNING,
        "error_log_empty": Icons.WARNING,
        "error_manager_log_empty": Icons.WARNING,
        "error_id_not_found": Icons.WARNING,
        "error_unknown_bot": Icons.WARNING,
        "update_no_changes": Icons.WARNING,
        "status_refreshed": Icons.WARNING,

        # --- Alerts (🚨) : Urgent state changes ---
        "bot_stopped_alert": Icons.ALERT,
        "status_uncertain": Icons.ALERT,

        # --- Success (🚀/✅) : Positive feedback ---
        "success_generic": Icons.SUCCESS,
        "update_success": Icons.ROCKET,
        "restart_success": Icons.ROCKET,
        "status_ok": Icons.SUCCESS,
        "sync_success_global": Icons.SUCCESS,
        "sync_success_copy": Icons.SUCCESS,
        "sync_success_guild": Icons.SUCCESS,
        "clear_commands_success": Icons.SUCCESS,
        "purge_success": Icons.SUCCESS,
        "manager_update_success": Icons.SUCCESS,
        "logs_rotate_success": Icons.SUCCESS,
        "logs_rotate_no_need": Icons.WARNING,

        # --- Headers & UI Labels ---
        "manager_status_header": "",
        "bots_status_header": "",
        "logs_header": Icons.LOG,
        "logs_full_header": Icons.LOG,
        "manager_logs_header": Icons.LOG,
        "manager_logs_full_header": Icons.LOG,
        "update_result_title": Icons.SUCCESS,
        "manager_updated_title": Icons.SUCCESS,
        "bot_updated_title": Icons.SUCCESS,
        "bot_rollback_title": Icons.ROLLBACK,
        "update_footer": Icons.SUCCESS,

        # --- Administrative (🛡️) : Permissions / Protection ---
        "error_admin_only": Icons.SHIELD_LIGHT,
        "error_admin_context": Icons.SHIELD_LIGHT,
        "error_admin_channel_only": Icons.SHIELD_LIGHT,
        "error_inspector_only": Icons.SHIELD_LIGHT,
        "error_command_failed": Icons.ERROR,
        "sync_in_progress": Icons.WRENCH,
        "clear_commands_in_progress": Icons.WRENCH,
        "ping_pong": "",
        "manager_online_log": Icons.SHIELD_LIGHT,
        "activity_status": Icons.SHIELD,

        # --- Functional Icons (Buttons / System) ---
        "RESTART": Icons.RESTART,
        "UPDATE": Icons.UPDATE,
        "STOP": Icons.STOP,
        "UP": Icons.UP,
        "DOWN": Icons.DOWN,
        "ROCKET": Icons.ROCKET,
        "CONTROLLER": Icons.CONTROLLER,
        "LOG": Icons.LOG,
        "PACKAGE": Icons.PACKAGE,
        "WRENCH": Icons.WRENCH,
        "GEAR": Icons.GEAR,
        "WAVE": Icons.WAVE,
        "ACTIVITY_UP": Icons.ACTIVITY_UP,
        "ACTIVITY_DOWN": Icons.ACTIVITY_DOWN,
        "DOT_GREEN": Icons.DOT_GREEN,
        "DOT_RED": Icons.DOT_RED,
        "DOT_YELLOW": Icons.DOT_YELLOW,

        # --- Bot & Manager States ---
        "manager_restart_msg": Icons.SHIELD_LIGHT,
        "manager_updating": Icons.UPDATE,
        "pip_updated": Icons.PACKAGE,
        "pip_deps": "",
        "bot_restarted_log": Icons.ROCKET,
        "bot_online_log": Icons.ROCKET,
        "status_restarting": Icons.RESTART,
        "status_stopping": Icons.STOP,
        "status_running": Icons.DOT_GREEN,
        "status_stopped": Icons.DOT_RED,
        "activity_text": Icons.CONTROLLER,
        "activity_maintenance": Icons.WRENCH,
        "activity_resource": Icons.GEAR,
        "activity_network": Icons.WAVE,
    }

    # Key normalization: try exact match first, then lowercase match
    emoji = icons_map.get(key)
    if not emoji:
        emoji = icons_map.get(key.lower(), "")

    # Fallback heuristic: match by keyword if no direct map
    if not emoji:
        lower_key = key.lower()
        if "error" in lower_key:
            emoji = Icons.ERROR
        elif "success" in lower_key:
            emoji = Icons.SUCCESS
        elif "warning" in lower_key:
            emoji = Icons.WARNING

    # Inject all icons into kwargs so they can be used as placeholders like {WRENCH} or {UP}
    for attr in dir(Icons):
        if not attr.startswith("__") and not callable(getattr(Icons, attr)):
            icon_val = getattr(Icons, attr)
            if icon_val is not None:
                kwargs.setdefault(attr, str(icon_val))

    text = i18n.get(key, **kwargs)

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
