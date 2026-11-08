import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> logging.Logger:
    settings = SettingsLoader()
    log_file = settings.get("log_file")
    log_level = settings.get("log_level", "INFO")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )

        formatter = logging.Formatter(
            fmt="%(levelname)s %(asctime)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
