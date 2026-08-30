"""Centralized mappings between localization keys and visual emoji icons."""
from typing import Optional, Any
from core.icons import Icons

# Mapping keys to Icons attribute names (or direct string icon)
ICON_KEY_MAP = {
    # --- Errors (❌) : Critical / Blocking failures ---
    "error_generic": "ERROR",
    "error_git_update_failed": "ERROR",
    "error_update_failed_output": "ERROR",
    "error_update_general": "ERROR",
    "error_no_token": "ERROR",
    "error_rollback": "ERROR",
    "error_log_fetch": "ERROR",
    "error_log_not_found": "ERROR",
    "error_manager_log_not_found": "ERROR",
    "pip_error": "ERROR",
    "purge_error": "ERROR",
    "status_failed": "ERROR",
    "status_error_prefix": "ERROR",
    "status_error": "ERROR",

    # --- Warnings (⚠️) : Non-blocking / User input errors ---
    "warning_generic": "WARNING",
    "update_available": "WARNING",
    "error_no_requirements": "WARNING",
    "error_no_bots_configured": "WARNING",
    "error_log_empty": "WARNING",
    "error_manager_log_empty": "WARNING",
    "error_id_not_found": "WARNING",
    "error_unknown_bot": "WARNING",
    "update_no_changes": "WARNING",
    "status_refreshed": "WARNING",

    # --- Alerts (🚨) : Urgent state changes ---
    "bot_stopped_alert": "ALERT",
    "status_uncertain": "ALERT",

    # --- Success (🚀/✅) : Positive feedback ---
    "success_generic": "SUCCESS",
    "update_success": "ROCKET",
    "restart_success": "ROCKET",
    "status_ok": "SUCCESS",
    "sync_success_global": "SUCCESS",
    "sync_success_copy": "SUCCESS",
    "sync_success_guild": "SUCCESS",
    "clear_commands_success": "SUCCESS",
    "purge_success": "SUCCESS",
    "manager_update_success": "SUCCESS",
    "logs_rotate_success": "SUCCESS",
    "logs_rotate_no_need": "WARNING",

    # --- Headers & UI Labels ---
    "manager_status_header": "",
    "bots_status_header": "",
    "page_indicator": "",
    "page_number": "",
    "cluster": "",
    "net": "",
    "db": "",
    "logs_header": "LOG",
    "logs_full_header": "LOG",
    "manager_logs_header": "LOG",
    "manager_logs_full_header": "LOG",
    "update_result_title": "SUCCESS",
    "manager_updated_title": "SUCCESS",
    "bot_updated_title": "SUCCESS",
    "bot_rollback_title": "ROLLBACK",
    "update_footer": "SUCCESS",

    # --- Administrative (🛡️) : Permissions / Protection ---
    "error_admin_only": "SHIELD_LIGHT",
    "error_admin_context": "SHIELD_LIGHT",
    "error_admin_channel_only": "SHIELD_LIGHT",
    "error_inspector_only": "SHIELD_LIGHT",
    "error_command_failed": "ERROR",
    "sync_in_progress": "WRENCH",
    "clear_commands_in_progress": "WRENCH",
    "ping_pong": "",
    "manager_online_log": "SHIELD_LIGHT",
    "activity_status": "SHIELD",

    # --- Functional Icons (Buttons / System) ---
    "RESTART": "RESTART",
    "UPDATE": "UPDATE",
    "STOP": "STOP",
    "UP": "UP",
    "DOWN": "DOWN",
    "ROCKET": "ROCKET",
    "CONTROLLER": "CONTROLLER",
    "LOG": "LOG",
    "PACKAGE": "PACKAGE",
    "WRENCH": "WRENCH",
    "GEAR": "GEAR",
    "WAVE": "WAVE",
    "ACTIVITY_UP": "ACTIVITY_UP",
    "ACTIVITY_DOWN": "ACTIVITY_DOWN",
    "DOT_GREEN": "DOT_GREEN",
    "DOT_RED": "DOT_RED",
    "DOT_YELLOW": "DOT_YELLOW",
    "CARET_LEFT": "CARET_LEFT",
    "CARET_RIGHT": "CARET_RIGHT",

    # --- Bot & Manager States ---
    "manager_restart_msg": "SHIELD_LIGHT",
    "manager_updating": "UPDATE",
    "pip_updated": "PACKAGE",
    "pip_deps": "",
    "bot_restarted_log": "ROCKET",
    "bot_online_log": "ROCKET",
    "status_restarting": "RESTART",
    "status_stopping": "STOP",
    "status_running": "DOT_GREEN",
    "status_stopped": "DOT_RED",
    "activity_text": "CONTROLLER",
    "activity_maintenance": "WRENCH",
    "activity_resource": "GEAR",
    "activity_network": "WAVE",
}

def resolve_icon_for_key(key: str) -> Optional[Any]:
    """Resolves an icon partial emoji or string corresponding to a feedback key."""
    icon_attr = ICON_KEY_MAP.get(key)
    if icon_attr is None:
        icon_attr = ICON_KEY_MAP.get(key.lower())

    if icon_attr == "":
        return ""

    if icon_attr and hasattr(Icons, icon_attr):
        return getattr(Icons, icon_attr)

    # Fallback heuristic: match by keyword if no direct map
    lower_key = key.lower()
    if "error" in lower_key:
        return Icons.ERROR
    elif "success" in lower_key:
        return Icons.SUCCESS
    elif "warning" in lower_key:
        return Icons.WARNING

    return ""

__all__ = [
    "ICON_KEY_MAP",
    "resolve_icon_for_key",
]
