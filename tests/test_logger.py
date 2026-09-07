import logging

from core.logger import reconfigure_log, setup_discord_logging, setup_logger


def test_setup_logger_creates_file_and_stream_handler(tmp_path):
    log_file = tmp_path / "test_run.log"
    logger = setup_logger("TestLoggerUnique", log_file=str(log_file), max_bytes=1024, backup_count=2)

    assert logger.name == "TestLoggerUnique"
    assert logger.level == logging.INFO
    assert len(logger.handlers) >= 2


def test_reconfigure_log_switches_file(tmp_path):
    new_log_file = tmp_path / "reconfigured.log"
    reconfigure_log(str(new_log_file), max_bytes=2048, backup_count=1)

    bot_logger = logging.getLogger("BotManager")
    assert any(str(new_log_file) in getattr(h, "baseFilename", "") for h in bot_logger.handlers)


def test_logger_writes_messages(tmp_path):
    log_file = tmp_path / "write_test.log"
    logger = setup_logger("WriteLogger", log_file=str(log_file))
    logger.info("Test information entry")

    for h in logger.handlers:
        h.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test information entry" in content


def test_setup_discord_logging(tmp_path):
    log_file = tmp_path / "discord.log"
    setup_discord_logging(str(log_file), max_bytes=1024, backup_count=2, level=logging.INFO)
    discord_logger = logging.getLogger("discord")
    assert discord_logger.level == logging.INFO
    assert any(str(log_file) in getattr(h, "baseFilename", "") for h in discord_logger.handlers)
