import logging
import sys
from pathlib import Path

from src.core.config import settings


def setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper())

    # In production/Docker, we only use stdout logging
    # File logging can cause permission issues in containers
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    # Only add file handler if we can write to the directory
    log_dir = Path("logs")
    try:
        log_dir.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "app.log"))
    except (PermissionError, OSError):
        # If we can't create logs directory, just use stdout
        pass

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if settings.debug else logging.WARNING)

    # Reduce noise from some libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
