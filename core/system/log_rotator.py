import os
import shutil

from core.config.models import BotConfig
from core.logger import log


class LogRotator:
    """Handles rotation, archiving, and size limiting for child bot log files."""

    def __init__(self, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 3):
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def rotate_file(self, file_path: str, force: bool = False) -> tuple[bool, str]:
        """Rotates a single log file using the safe copy-truncate strategy.

        This strategy allows rotating active log files even while the child process
        holds an open file descriptor on Windows and Linux.
        """
        if not os.path.exists(file_path):
            return False, "File does not exist"

        try:
            file_size = os.path.getsize(file_path)
            if not force and file_size < self.max_bytes:
                return (
                    False,
                    f"Size ({file_size / (1024 * 1024):.2f} MB) is below threshold ({self.max_bytes / (1024 * 1024):.2f} MB)",
                )

            # 1. Shift existing backups: file.N -> file.(N+1)
            for i in range(self.backup_count - 1, 0, -1):
                sfn = f"{file_path}.{i}"
                dfn = f"{file_path}.{i + 1}"
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        try:
                            os.remove(dfn)
                        except (PermissionError, OSError) as e:
                            log.debug(f"[LogRotator] Could not pre-clean target backup {dfn}: {e}")
                    try:
                        os.rename(sfn, dfn)
                    except (PermissionError, OSError) as e:
                        log.warning(f"[LogRotator] Failed to rename {sfn} -> {dfn}: {e}")

            # 2. Copy current log to file.1 and truncate safely without race-condition data loss
            backup_1 = f"{file_path}.1"
            if os.path.exists(backup_1):
                try:
                    os.remove(backup_1)
                except (PermissionError, OSError) as e:
                    log.debug(f"[LogRotator] Could not pre-clean backup_1 {backup_1}: {e}")

            # Perform safe stream copy and truncate:
            # Opening the source file in binary read/write mode ("r+b") avoids O_TRUNC lock errors
            # (WinError 32) on Windows and captures any trailing lines written during copying.
            try:
                with open(file_path, "r+b") as src_f, open(backup_1, "wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)
                    trailing = src_f.read()
                    src_f.seek(0)
                    src_f.truncate(0)
                    if trailing:
                        src_f.write(trailing)
                    src_f.flush()
            except (PermissionError, OSError) as lock_err:
                log.debug(f"[LogRotator] Direct r+b stream failed ({lock_err}), attempting copy2 fallback")
                shutil.copy2(file_path, backup_1)
                with open(file_path, "r+b") as fallback_f:
                    fallback_f.seek(0)
                    fallback_f.truncate(0)

            log.info(
                f"[LogRotator] Successfully rotated '{file_path}' (Original size: {file_size / (1024 * 1024):.2f} MB)"
            )
            return True, f"{file_size / (1024 * 1024):.2f} MB"

        except (PermissionError, OSError) as e:
            log.error(f"[LogRotator] File system permission or I/O error rotating '{file_path}': {e}")
            return False, str(e)
        except Exception as e:
            log.error(f"[LogRotator] Unexpected error rotating log file '{file_path}': {e}")
            return False, str(e)

    def rotate_bot_log(self, bot_cfg: BotConfig, force: bool = False) -> tuple[bool, str]:
        """Rotates the log file for a specific bot."""
        log_path = os.path.join(bot_cfg.path, bot_cfg.log)
        return self.rotate_file(log_path, force=force)

    def rotate_all_bots(self, bots: dict[str, BotConfig], force: bool = False) -> list[tuple[BotConfig, bool, str]]:
        """Scans and rotates log files for all configured bots."""
        results = []
        for _bot_id, bot_cfg in bots.items():
            success, msg = self.rotate_bot_log(bot_cfg, force=force)
            results.append((bot_cfg, success, msg))
        return results

    async def rotate_file_async(self, file_path: str, force: bool = False) -> tuple[bool, str]:
        """Asynchronously rotates a single log file in a worker thread."""
        import asyncio

        return await asyncio.to_thread(self.rotate_file, file_path, force)

    async def rotate_bot_log_async(self, bot_cfg: BotConfig, force: bool = False) -> tuple[bool, str]:
        """Asynchronously rotates a bot's log file in a worker thread."""
        import asyncio

        return await asyncio.to_thread(self.rotate_bot_log, bot_cfg, force)

    async def rotate_all_bots_async(
        self, bots: dict[str, BotConfig], force: bool = False
    ) -> list[tuple[BotConfig, bool, str]]:
        """Asynchronously rotates log files for all configured bots in a worker thread."""
        import asyncio

        return await asyncio.to_thread(self.rotate_all_bots, bots, force)


__all__ = ["LogRotator"]
