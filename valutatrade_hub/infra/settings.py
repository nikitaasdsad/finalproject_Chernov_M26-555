from pathlib import Path
from typing import Any


class SettingsLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._project_dir = Path(__file__).resolve().parents[2]
        self._config = {
            "data_dir": self._project_dir / "data",
            "users_file": self._project_dir / "data" / "users.json",
            "portfolios_file": self._project_dir / "data" / "portfolios.json",
            "rates_file": self._project_dir / "data" / "rates.json",
            "rates_ttl_seconds": 300,
            "default_base_currency": "USD",
            "log_file": self._project_dir / "logs" / "actions.log",
            "log_level": "INFO",
            "log_format": "text",
        }
        self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def reload(self) -> None:
        self._initialized = False
        self.__init__()
