import os
import io
from unittest.mock import patch, MagicMock
from core.config.models import AppConfig, BotConfig
from core.system.log_rotator import LogRotator
from core.system.process_spawner import ProcessSpawner
from core.logger import setup_logger, reconfigure_log

def test_e2e_spawner_with_rotator_auto_rotation(tmp_path):
    # Setup oversized log file (> 100 bytes)
    log_file = tmp_path / "app.log"
    log_file.write_text("A" * 500, encoding="utf-8")

    rotator = LogRotator(max_bytes=100, backup_count=2)
    spawner = ProcessSpawner(log_rotator=rotator)

    bot_cfg = BotConfig(
        id="rot_bot",
        name="Rot Bot",
        path=str(tmp_path),
        cmd="python main.py",
        log=str(log_file)
    )

    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        # Spawn bot - should trigger automatic pre-rotation of app.log
        pid = spawner.spawn(bot_cfg, env={})
        assert pid == 9999

        # Backup file app.log.1 exists
        backup_file = tmp_path / "app.log.1"
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == "A" * 500

def test_e2e_slash_logs_file_stream_generation(tmp_path):
    # Setup sample bot log file
    log_file = tmp_path / "stream.log"
    lines = [f"2026-08-26 12:00:{i:02d} Info message {i}\n" for i in range(50)]
    log_file.write_text("".join(lines), encoding="utf-8")

    # Simulate /logs command stream extraction
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        file_lines = f.readlines()
        last_lines = file_lines[-20:]
        content = "".join(last_lines)
        file_stream = io.BytesIO(content.encode("utf-8"))

    assert len(last_lines) == 20
    assert "Info message 49" in content
    assert file_stream.getvalue() is not None

def test_e2e_rotate_all_bots_cluster_pipeline(tmp_path):
    log1 = tmp_path / "bot1.log"
    log2 = tmp_path / "bot2.log"
    log1.write_text("X" * 300, encoding="utf-8")
    log2.write_text("Y" * 300, encoding="utf-8")

    b1 = BotConfig(id="b1", name="Bot 1", path=str(tmp_path), cmd="python b1.py", log=str(log1))
    b2 = BotConfig(id="b2", name="Bot 2", path=str(tmp_path), cmd="python b2.py", log=str(log2))
    app_cfg = AppConfig(bots={"b1": b1, "b2": b2})

    rotator = LogRotator(max_bytes=100, backup_count=1)
    results = rotator.rotate_all_bots(app_cfg.bots)

    res_dict = {b_cfg.id: success for b_cfg, success, _ in results}
    assert res_dict["b1"] is True
    assert res_dict["b2"] is True
    assert os.path.exists(str(log1) + ".1")
    assert os.path.exists(str(log2) + ".1")

def test_e2e_manager_logging_and_reconfiguration(tmp_path):
    mgr_log = tmp_path / "custom_mgr.log"
    logger = setup_logger("MgrPipeline", log_file=str(mgr_log), max_bytes=1024, backup_count=2)
    logger.info("Manager started in integration test")

    for h in logger.handlers:
        h.flush()

    assert mgr_log.exists()
    assert "Manager started in integration test" in mgr_log.read_text(encoding="utf-8")

    # Reconfigure
    new_log = tmp_path / "switched_mgr.log"
    reconfigure_log(str(new_log), max_bytes=2048, backup_count=1)
    logger.info("After reconfiguration")

    for h in logger.handlers:
        h.flush()

    assert new_log.exists()
