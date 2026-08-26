from typing import List, Tuple, Set, Callable, Optional
from core.logger import log
from core.config.models import AppConfig, BotConfig
from core.interfaces.system import IProcessTracker, IProcessSpawner

class HealthService:
    """Monitors running bot health, detects crashes, and manages alert states."""
    def __init__(
        self,
        config: AppConfig,
        tracker: IProcessTracker,
        spawner: IProcessSpawner,
        alert_callback: Optional[Callable] = None
    ):
        self.config = config
        self.tracker = tracker
        self.spawner = spawner
        self.alert_callback = alert_callback
        self.alerted_bots: Set[str] = set()

    async def check_health(self) -> List[Tuple[str, BotConfig]]:
        """Scans all managed bots for unexpected crashes or failures."""
        stopped = self.tracker.fetch_unexpected_stops(self.config.bots, self.spawner)

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

        # 2. Clear alert flags if bot is running again
        for bot_id in list(self.alerted_bots):
            if self.tracker.is_running(bot_id):
                self.alerted_bots.remove(bot_id)
                log.info(f"[HealthService] Bot {bot_id} is running again. Alert state cleared.")

        return stopped
