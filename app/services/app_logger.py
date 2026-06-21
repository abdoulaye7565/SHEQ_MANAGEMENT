from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import LOGS_DIR


def get_logger(name: str = "orezone_qhse") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOGS_DIR / "orezone_qhse.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    return logger


def log_exception(message: str, exc: BaseException) -> None:
    get_logger().exception("%s: %s", message, exc)
