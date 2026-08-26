import os
import discord
from discord.ui import LayoutView, ActionRow, Container, TextDisplay, Separator
from core.icons import Icons
from core.utils import get_feedback
from bot.ui.components.buttons import BotControlButton, PageButton

class StatusContainer(Container):
    """A visual container box for the status content (Paginated)."""
    def __init__(self, bot_manager, i18n, manager_stats, bots_stats, parent_view, page=0, page_size=3):
        ui = getattr(bot_manager, 'ui_settings', {})
        accent = ui.get("accent_color", 0x2b2d31)
        super().__init__(accent_color=accent)

        restart_emoji = Icons.RESTART
        update_emoji = Icons.UPDATE
        stop_emoji = Icons.STOP

        # 1. Manager Statistics (Only on Page 1 / index 0)
        if page == 0:
            cpu_label = get_feedback(i18n, "cpu")
            ram_label = get_feedback(i18n, "ram")
            host_label = get_feedback(i18n, "host_os")
            free_label = get_feedback(i18n, "system_free")
            disk_label = get_feedback(i18n, "disk")
            swap_label = get_feedback(i18n, "swap")
            server_up_label = get_feedback(i18n, "server_uptime")

            manager_text = (
                f"**{bot_manager.manager_name}**" + (f" **{get_feedback(i18n, 'update_available')}**" if manager_stats.get("has_update") else "") + "\n"
                f"**{get_feedback(i18n, 'status_running')}** | PID: `{os.getpid()}`\n"
                f"{get_feedback(i18n, 'uptime')}: {manager_stats['uptime']} | {server_up_label}: {manager_stats['host_uptime']}\n"
                f"{get_feedback(i18n, 'branch')}: `{manager_stats['branch']}` | {host_label}: `{manager_stats['os']}`\n"
                f"{get_feedback(i18n, 'resources')}: {cpu_label}: `{manager_stats['cpu']}%` | {ram_label}: `{int(manager_stats['ram'])} MB` | Net: `{manager_stats['net']}`\n"
                f"{free_label}: CPU: `{int(manager_stats['sys_cpu_free'])}%` | {ram_label}: `{int(manager_stats['sys_ram_free'])} MB` | {disk_label}: `{int(manager_stats['sys_disk_free'])} GB` | {swap_label}: `{manager_stats['swap']}%`"
            )
            self.add_item(TextDisplay(manager_text))

            mgr_row = ActionRow()
            mgr_row.add_item(BotControlButton(emoji=restart_emoji, bot_id="manager", action="restart", view=parent_view))
            mgr_row.add_item(BotControlButton(emoji=update_emoji, bot_id="manager", action="update", view=parent_view))
            mgr_row.add_item(BotControlButton(emoji=stop_emoji, bot_id="manager", action="stop", view=parent_view))
            self.add_item(mgr_row)
            self.add_item(Separator(visible=True, spacing=discord.enums.SeparatorSpacing.large))

        # 2. Managed Bots Section
        if bots_stats:
            path_groups = {}
            for b_id, b_info in bots_stats.items():
                path = b_info["path"]
                if path not in path_groups:
                    path_groups[path] = []
                path_groups[path].append((b_id, b_info))

            group_list = list(path_groups.items())

            # Variable pagination: Page 0 has 2 items, other pages have 3 items
            if page == 0:
                start_idx = 0
                end_idx = 2
            else:
                start_idx = 2 + (page - 1) * 3
                end_idx = start_idx + 3
            paged_groups = group_list[start_idx:end_idx]

            for i, (path, members) in enumerate(paged_groups):
                if i == 0:
                    header = f"**{get_feedback(i18n, 'bots_status_header')} (Page {page+1})**"
                    self.add_item(TextDisplay(header))
                    self.add_item(Separator())

                has_update = any(m[1].get("has_update") for m in members)
                up_alert = f" **{get_feedback(i18n, 'update_available')}**" if has_update else ""

                if len(members) > 1:
                    # Cluster View
                    cluster_title = f"**Cluster • {os.path.basename(path)}**{up_alert}\n`Path: {path}`"
                    self.add_item(TextDisplay(cluster_title))

                    cluster_row = ActionRow()
                    primary_id = members[0][0]
                    cluster_row.add_item(BotControlButton(emoji=restart_emoji, bot_id=primary_id, bot_name=members[0][1]["name"], action="restart", view=parent_view))
                    cluster_row.add_item(BotControlButton(emoji=update_emoji, bot_id=primary_id, bot_name=members[0][1]["name"], action="update", view=parent_view))
                    cluster_row.add_item(BotControlButton(emoji=stop_emoji, bot_id=primary_id, bot_name=members[0][1]["name"], action="stop", view=parent_view))
                    self.add_item(cluster_row)

                    member_details = []
                    for m_id, m_info in members:
                        if m_info.get("is_running"):
                            stats = f"CPU: `{m_info['cpu']}%` | RAM: `{int(m_info['ram'])}MB` | Log: `{m_info['log_size']}`"
                        else:
                            stats = f"Log: `{m_info['log_size']}`"
                        member_details.append(f"**{m_info['status']} • {m_info['name']}**\n{stats}")
                    self.add_item(TextDisplay("\n".join(member_details)))
                else:
                    # Single Bot View
                    b_id, b_info = members[0]
                    b_name = b_info["name"]

                    bot_header = f"**{b_info['status']} • {b_name}** ({b_id}){up_alert}"
                    self.add_item(TextDisplay(bot_header))

                    bot_row = ActionRow()
                    bot_row.add_item(BotControlButton(emoji=restart_emoji, bot_id=b_id, bot_name=b_name, action="restart", view=parent_view))
                    bot_row.add_item(BotControlButton(emoji=update_emoji, bot_id=b_id, bot_name=b_name, action="update", view=parent_view))
                    bot_row.add_item(BotControlButton(emoji=stop_emoji, bot_id=b_id, bot_name=b_name, action="stop", view=parent_view))
                    self.add_item(bot_row)

                    if b_info.get("is_running"):
                        details = f"CPU: `{b_info.get('cpu', 0)}%` | RAM: `{int(b_info.get('ram', 0))} MB` | {get_feedback(i18n, 'uptime_short')}: {b_info.get('uptime', '0s')}"
                        details += f"\n`Path: {b_info['path']}`"
                        details += f"\nLog: `{b_info.get('log_size', '0B')}`"
                        if b_info.get("db_sizes"):
                            db_parts = " | ".join([f"`{name}`: `{size}`" for name, size in b_info["db_sizes"].items()])
                            details += f" | DB: {db_parts}"
                    else:
                        details = f"`Path: {b_info['path']}`"
                        details += f"\n{get_feedback(i18n, 'log_size')}: `{b_info.get('log_size', '0B')}`"

                    self.add_item(TextDisplay(details))

                if i < len(group_list) - 1:
                    self.add_item(Separator())
        else:
            self.add_item(TextDisplay(f"*{i18n.get('error_no_bots_configured', 'No bots configured.')}*"))

class ModernStatusView(LayoutView):
    """A modern status view for managed bots using Components V2 layout."""
    def __init__(self, bot_manager, i18n, manager_stats, bots_stats, current_page=0):
        ui = getattr(bot_manager, 'ui_settings', {})
        timeout = ui.get("view_timeout", 300)
        super().__init__(timeout=timeout if timeout else None)
        self.bot_manager = bot_manager
        self.i18n = i18n

        # Calculate total pages
        path_groups = {}
        for b_id, b_info in bots_stats.items():
            path = b_info["path"]
            if path not in path_groups:
                path_groups[path] = []
            path_groups[path].append((b_id, b_info))

        group_list = list(path_groups.items())
        num_groups = len(group_list)
        if num_groups <= 2:
            total_pages = 1
        else:
            total_pages = 1 + (num_groups - 2 + 3 - 1) // 3
        if total_pages == 0:
            total_pages = 1

        container = StatusContainer(bot_manager, i18n, manager_stats, bots_stats, self, page=current_page, page_size=3)

        if total_pages > 1:
            nav_row = ActionRow()
            cog = bot_manager.get_cog("MonitoringCog")

            nav_row.add_item(PageButton(-1, cog, current_page, total_pages, i18n))

            page_label = discord.ui.Button(style=discord.ButtonStyle.secondary, label=f"{current_page + 1} / {total_pages}", disabled=True)
            nav_row.add_item(page_label)

            nav_row.add_item(PageButton(1, cog, current_page, total_pages, i18n))
            container.add_item(nav_row)

        self.add_item(container)
