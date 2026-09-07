import os

from core.config.models import BotConfig
from core.system.log_rotator import LogRotator


def test_log_rotator_no_rotation_needed_for_small_file(tmp_path):
    bot_dir = tmp_path / "bot_small"
    bot_dir.mkdir()
    log_file = bot_dir / "bot.log"
    log_file.write_text("A" * 100, encoding="utf-8")

    bot = BotConfig(id="1", name="SmallBot", path=str(bot_dir), cmd="python bot.py", log="bot.log")
    rotator = LogRotator(max_bytes=1024, backup_count=3)

    rotated, msg = rotator.rotate_bot_log(bot, force=False)
    assert rotated is False
    assert "below threshold" in msg
    assert os.path.exists(log_file)
    assert os.path.getsize(log_file) == 100


def test_log_rotator_copytruncate_execution(tmp_path):
    bot_dir = tmp_path / "bot_large"
    bot_dir.mkdir()
    log_file = bot_dir / "bot.log"
    log_file.write_text("X" * 2000, encoding="utf-8")

    bot = BotConfig(id="2", name="LargeBot", path=str(bot_dir), cmd="python bot.py", log="bot.log")
    rotator = LogRotator(max_bytes=1000, backup_count=3)

    rotated, msg = rotator.rotate_bot_log(bot, force=False)
    assert rotated is True
    # The active log file is truncated to 0 bytes
    assert os.path.getsize(log_file) == 0
    # The backup file bot.log.1 contains the original contents
    backup_1 = bot_dir / "bot.log.1"
    assert os.path.exists(backup_1)
    assert os.path.getsize(backup_1) == 2000


def test_log_rotator_multi_backup_cascade(tmp_path):
    bot_dir = tmp_path / "bot_cascade"
    bot_dir.mkdir()
    log_file = bot_dir / "bot.log"
    bot = BotConfig(id="3", name="CascadeBot", path=str(bot_dir), cmd="python bot.py", log="bot.log")
    rotator = LogRotator(max_bytes=50, backup_count=2)

    # First rotation
    log_file.write_text("1" * 100, encoding="utf-8")
    rotator.rotate_bot_log(bot, force=True)
    assert os.path.exists(bot_dir / "bot.log.1")
    assert (bot_dir / "bot.log.1").read_text(encoding="utf-8") == "1" * 100

    # Second rotation
    log_file.write_text("2" * 100, encoding="utf-8")
    rotator.rotate_bot_log(bot, force=True)
    assert os.path.exists(bot_dir / "bot.log.1")
    assert (bot_dir / "bot.log.1").read_text(encoding="utf-8") == "2" * 100
    assert os.path.exists(bot_dir / "bot.log.2")
    assert (bot_dir / "bot.log.2").read_text(encoding="utf-8") == "1" * 100

    # Third rotation (backup_count is 2, so bot.log.2 should become the second, bot.log.3 discarded)
    log_file.write_text("3" * 100, encoding="utf-8")
    rotator.rotate_bot_log(bot, force=True)
    assert (bot_dir / "bot.log.1").read_text(encoding="utf-8") == "3" * 100
    assert (bot_dir / "bot.log.2").read_text(encoding="utf-8") == "2" * 100
    assert not os.path.exists(bot_dir / "bot.log.3")


def test_log_rotator_non_existent_file(tmp_path):
    bot_dir = tmp_path / "bot_empty"
    bot_dir.mkdir()
    bot = BotConfig(id="4", name="EmptyBot", path=str(bot_dir), cmd="python bot.py", log="missing.log")
    rotator = LogRotator()
    rotated, msg = rotator.rotate_bot_log(bot, force=False)
    assert rotated is False
    assert "does not exist" in msg


def test_log_rotator_rotate_all_bots(tmp_path):
    b1_dir = tmp_path / "b1"
    b1_dir.mkdir()
    (b1_dir / "b1.log").write_text("A" * 500, encoding="utf-8")

    b2_dir = tmp_path / "b2"
    b2_dir.mkdir()
    (b2_dir / "b2.log").write_text("B" * 500, encoding="utf-8")

    bots = {
        "b1": BotConfig(id="b1", name="Bot 1", path=str(b1_dir), cmd="cmd", log="b1.log"),
        "b2": BotConfig(id="b2", name="Bot 2", path=str(b2_dir), cmd="cmd", log="b2.log"),
    }

    rotator = LogRotator(max_bytes=100, backup_count=2)
    results = rotator.rotate_all_bots(bots, force=False)
    assert len(results) == 2
    assert results[0][0].name == "Bot 1" and results[0][1] is True
    assert results[1][0].name == "Bot 2" and results[1][1] is True


def test_log_rotator_preserves_trailing_appended_bytes(tmp_path, monkeypatch):
    """Simulates child process writing new log lines during copyfileobj stream."""
    import shutil

    bot_dir = tmp_path / "bot_stream"
    bot_dir.mkdir()
    log_file = bot_dir / "bot.log"
    log_file.write_bytes(b"INITIAL_LOG_LINE\n")

    orig_copyfileobj = shutil.copyfileobj

    def mock_copyfileobj(fsrc, fdst):
        res = orig_copyfileobj(fsrc, fdst)
        # Simulate active child appending new bytes after initial read:
        with open(str(log_file), "ab") as append_f:
            append_f.write(b"TRAILING_LOG_LINE_WRITTEN_DURING_COPY\n")
            append_f.flush()
        return res

    monkeypatch.setattr(shutil, "copyfileobj", mock_copyfileobj)

    rotator = LogRotator(max_bytes=10, backup_count=2)
    rotated, msg = rotator.rotate_file(str(log_file), force=True)

    assert rotated is True
    backup_1 = bot_dir / "bot.log.1"
    assert backup_1.read_bytes() == b"INITIAL_LOG_LINE\n"
    # The active log file should preserve the trailing line rather than truncating it to 0!
    assert log_file.read_bytes() == b"TRAILING_LOG_LINE_WRITTEN_DURING_COPY\n"


async def test_log_rotator_async_methods(tmp_path):
    bot_dir = tmp_path / "bot_async"
    bot_dir.mkdir()
    log_file = bot_dir / "bot.log"
    log_file.write_text("X" * 200, encoding="utf-8")

    bot = BotConfig(id="a1", name="AsyncBot", path=str(bot_dir), cmd="python bot.py", log="bot.log")
    rotator = LogRotator(max_bytes=50, backup_count=2)

    res, _ = await rotator.rotate_file_async(str(log_file), force=True)
    assert res is True
    assert (bot_dir / "bot.log.1").exists()

    (bot_dir / "bot.log").write_text("Y" * 200, encoding="utf-8")
    res_b, _ = await rotator.rotate_bot_log_async(bot, force=True)
    assert res_b is True

    (bot_dir / "bot.log").write_text("Z" * 200, encoding="utf-8")
    res_all = await rotator.rotate_all_bots_async({"a1": bot}, force=True)
    assert len(res_all) == 1
    assert res_all[0][1] is True
