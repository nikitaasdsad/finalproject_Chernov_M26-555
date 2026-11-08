import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._settings = SettingsLoader()
        self._initialized = True

    def read_json(self, file_path: str | Path, default: Any = None) -> Any:
        path = Path(file_path)

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8-sig") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"Некорректный JSON-файл: {path}") from error
        except OSError as error:
            raise OSError(f"Не удалось прочитать файл {path}: {error}") from error

    def write_json(self, file_path: str | Path, data: Any) -> None:
        path = Path(file_path)
        temporary_path = path.with_suffix(path.suffix + ".tmp")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

            temporary_path.replace(path)

        except OSError as error:
            if temporary_path.exists():
                temporary_path.unlink()

            raise OSError(f"Не удалось записать файл {path}: {error}") from error
