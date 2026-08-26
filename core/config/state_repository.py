import os
import json
from typing import Any, Dict
from core.logger import log

class StateRepository:
    """Handles persistent storage of dynamic runtime state."""
    def __init__(self, state_path: str = "state.json"):
        self.state_path = os.path.abspath(state_path)
        self._state: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        """Loads state from state.json."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                    return self._state
            except Exception as e:
                log.error(f"[StateRepository] Error loading state from {self.state_path}: {e}")
        self._state = {}
        return self._state

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a state value."""
        return self._state.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Sets a state value and optionally persists it."""
        self._state[key] = value
        if auto_save:
            self.save()

    def save(self) -> bool:
        """Persists the in-memory state dictionary to state.json."""
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=4)
            return True
        except Exception as e:
            log.error(f"[StateRepository] Error saving state to {self.state_path}: {e}")
            return False

    @property
    def raw(self) -> Dict[str, Any]:
        return self._state
