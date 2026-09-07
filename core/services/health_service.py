from collections.abc import Callable

from core.config.models import AppConfig, BotConfig
from core.interfaces.system import IProcessSpawner, IProcessTracker
from core.logger import log


class HealthService:
    """Monitors running bot health, detects crashes, and manages alert states."""

    def __init__(
        self,
        config: AppConfig,
        tracker: IProcessTracker,
        spawner: IProcessSpawner,
        alert_callback: Callable | None = None,
    ):
        self.config = config
        self.tracker = tracker
        self.spawner = spawner
        self.alert_callback = alert_callback
        self.alerted_bots: set[str] = set()

    def clear_alert(self, bot_id: str) -> None:
        """Explicitly clears the alert state for a specific bot."""
        if bot_id in self.alerted_bots:
            self.alerted_bots.discard(bot_id)
            log.info(f"[HealthService] Alert state cleared for bot {bot_id}.")

    def reset_alerts(self) -> None:
        """Resets all active alert states."""
        self.alerted_bots.clear()

    async def check_health(self) -> list[tuple[str, BotConfig]]:
        """Scans all managed bots for unexpected crashes or failures."""
        stopped = self.tracker.fetch_unexpected_stops(self.config.bots, self.spawner)
        stopped_ids = {bot_id for bot_id, _ in stopped}

        # 1. Alert for newly stopped bots
        for bot_id, bot_cfg in stopped:
            if bot_id not in self.alerted_bots:
                log.warning(f"[HealthService] Bot '{bot_cfg.name}' ({bot_id}) stopped unexpectedly.")
                self.alerted_bots.add(bot_id)
                if self.alert_callback:
                    try:
                        await self.alert_callback(bot_id, bot_cfg)
                    except Exception as e:
                        log.error(f"[HealthService] Error in alert callback for {bot_id}: {e}")

        # 2. Clear alert flags if bot is no longer in unexpected stopped list (running, manually stopped, or removed)
        for bot_id in list(self.alerted_bots):
            if bot_id not in stopped_ids:
                self.alerted_bots.remove(bot_id)
                log.info(f"[HealthService] Bot {bot_id} is no longer in unexpected stopped state. Alert state cleared.")

        return stopped
