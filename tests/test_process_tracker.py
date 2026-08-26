import os
from unittest.mock import MagicMock
from core.system.process_tracker import ProcessTracker
from core.config.models import BotConfig

def test_process_tracker_registration_and_is_running():
    tracker = ProcessTracker()
    current_pid = os.getpid()

    assert tracker.is_running("my_bot") is False
    tracker.register("my_bot", current_pid)
    assert tracker.is_running("my_bot") is True

    tracker.unregister("my_bot")
    assert tracker.is_running("my_bot") is False

def test_process_tracker_manual_stop_flags():
    tracker = ProcessTracker()
    assert "bot1" not in tracker.manual_stop

    tracker.mark_manual_stop("bot1")
    assert "bot1" in tracker.manual_stop

    tracker.clear_manual_stop("bot1")
    assert "bot1" not in tracker.manual_stop

def test_process_tracker_get_stats_live_process():
    tracker = ProcessTracker()
    current_pid = os.getpid()
    tracker.register("self_bot", current_pid)

    stats = tracker.get_stats("self_bot")
    assert stats is not None
    assert stats["pid"] == current_pid
    assert isinstance(stats["cpu"], (int, float))
    assert isinstance(stats["ram_mb"], (int, float))
    assert stats["uptime_sec"] > 0

def test_process_tracker_get_stats_non_existent():
    tracker = ProcessTracker()
    assert tracker.get_stats("ghost_bot") is None

def test_process_tracker_fetch_unexpected_stops():
    tracker = ProcessTracker()
    dead_mock_proc = MagicMock()
    dead_mock_proc.is_running.return_value = False

    tracker.managed_processes["crashed_bot"] = dead_mock_proc

    bots = {
        "crashed_bot": BotConfig(id="crashed_bot", name="Crashed", path="C:\\crashed", cmd="python app.py"),
        "normal_bot": BotConfig(id="normal_bot", name="Normal", path="C:\\normal", cmd="python app.py")
    }

    stopped = tracker.fetch_unexpected_stops(bots)
    assert len(stopped) == 1
    assert stopped[0][0] == "crashed_bot"
    assert stopped[0][1].name == "Crashed"

    # Suppressed if manual stop
    tracker.managed_processes["manual_stopped_bot"] = dead_mock_proc
    tracker.mark_manual_stop("manual_stopped_bot")
    bots["manual_stopped_bot"] = BotConfig(id="manual_stopped_bot", name="Manual", path="C:\\m", cmd="cmd")

    stopped_again = tracker.fetch_unexpected_stops(bots)
    # manual_stopped_bot should not trigger crash alert
    assert "manual_stopped_bot" not in [s[0] for s in stopped_again]
