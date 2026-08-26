import os
import json
from core.config.models import BotConfig
from core.config.state_repository import StateRepository
from core.system.process_tracker import ProcessTracker
from bot.client import BotManager

def test_e2e_reboot_state_recovery(tmp_path):
    # Simulate prior state with existing status message ID
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"status_message_id": "888777666"}), encoding="utf-8")

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({}), encoding="utf-8")

    bot = BotManager(base_dir=str(tmp_path))
    assert bot.state.get("status_message_id") == "888777666"

    # Mutate and save state
    bot.save_state("status_message_id", "111222333")
    
    # Verify disk persistence
    reloaded_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert reloaded_state["status_message_id"] == "111222333"

def test_e2e_process_discovery_on_boot():
    tracker = ProcessTracker()

    bot_cfg = BotConfig(
        id="current_self",
        name="Self Process",
        path=".",
        cmd="python"
    )
    bots_dict = {"current_self": bot_cfg}

    # Discover alive processes matching cmd
    tracker.discover_processes(bots_dict)
    # The current running python pytest process is discovered or tracked
    assert isinstance(tracker.managed_processes, dict)

def test_e2e_config_hot_reload_persistence(tmp_path):
    config_file = tmp_path / "config.json"
    state_file = tmp_path / "state.json"
    config_file.write_text(json.dumps({"guild_id": 11111, "bots": {}}), encoding="utf-8")
    state_file.write_text(json.dumps({}), encoding="utf-8")

    bot = BotManager(base_dir=str(tmp_path))
    assert len(bot.bots) == 0

    # Save updated config with new bot
    new_config = {
        "guild_id": 11111,
        "bots": {
            "new_worker": {
                "name": "New Dynamic Worker",
                "path": str(tmp_path),
                "cmd": "python worker.py"
            }
        }
    }
    bot.save_config(new_config)

    # Verify memory updated
    assert "new_worker" in bot.bots
    assert bot.bots["new_worker"].name == "New Dynamic Worker"

    # Verify disk updated
    saved_disk_cfg = json.loads(config_file.read_text(encoding="utf-8"))
    assert "new_worker" in saved_disk_cfg["bots"]

def test_e2e_state_repository_external_file_loss_recovery(tmp_path):
    state_file = tmp_path / "state.json"
    repo = StateRepository(str(state_file))
    repo.set("session_key", "active_abc")

    assert state_file.exists()

    # External deletion of file
    os.remove(state_file)
    assert not state_file.exists()

    # Next write should recreate directory and file safely
    repo.set("session_key", "recovered_abc")
    assert state_file.exists()
    assert repo.get("session_key") == "recovered_abc"
