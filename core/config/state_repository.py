import os
import json
import threading
from typing import Any, Dict
from core.logger import log

class StateRepository:
    """Handles thread-safe, atomic persistent storage of dynamic runtime state."""
    def __init__(self, state_path: str = "state.json"):
        self.state_path = os.path.abspath(state_path)
        self._lock = threading.RLock()
        self._state: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        """Loads state from state.json under lock."""
        with self._lock:
            if os.path.exists(self.state_path):
                try:
                    with open(self.state_path, "r", encoding="utf-8") as f:
                        self._state = json.load(f)
                        return dict(self._state)
                except json.JSONDecodeError as e:
                    log.error(f"[StateRepository] Corrupt JSON in state file {self.state_path} (line {e.lineno}, col {e.colno}): {e.msg}")
                except (PermissionError, OSError) as e:
                    log.error(f"[StateRepository] I/O or permission error accessing {self.state_path}: {e}")
                except Exception as e:
                    log.error(f"[StateRepository] Unexpected error loading state from {self.state_path}: {e}")
            self._state = {}
            return dict(self._state)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a state value under lock."""
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Sets a state value and optionally persists it under lock."""
        with self._lock:
            self._state[key] = value
            if auto_save:
                self.save()

    def save(self) -> bool:
        """Persists the in-memory state dictionary to state.json atomically."""
        with self._lock:
            tmp_path = f"{self.state_path}.tmp"
            try:
                # 1. Write to temporary file with flush & fsync
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self._state, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())

                # 2. Atomically replace target file
                os.replace(tmp_path, self.state_path)
                return True
            except (PermissionError, OSError) as e:
                log.error(f"[StateRepository] I/O or permission error saving state to {self.state_path}: {e}")
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                return False
            except Exception as e:
                log.error(f"[StateRepository] Unexpected error saving state to {self.state_path}: {e}")
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                return False

    async def save_async(self) -> bool:
        """Asynchronously persists state in a worker thread without blocking the event loop."""
        import asyncio
        return await asyncio.to_thread(self.save)

    @property
    def raw(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state)

__all__ = ["StateRepository"]
