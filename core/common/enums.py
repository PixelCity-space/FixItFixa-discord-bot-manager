from enum import Enum, IntEnum

class AccessLevel(IntEnum):
    """Hierarchy of user access levels."""
    USER = 0        # Normal user
    INSPECTOR = 1   # Can view stats, logs, run ping, and restart bots
    MECHANIC = 2    # Can stop, update, purge messages, force refresh
    BOSS = 3        # Full control anywhere (Admin/Server Owner)

class BotStatus(str, Enum):
    """Runtime statuses for child bots."""
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    UPDATING = "updating"

class ActionType(str, Enum):
    """Interactive control actions."""
    RESTART = "restart"
    UPDATE = "update"
    STOP = "stop"
