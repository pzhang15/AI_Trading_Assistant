import logging
import os
import sys


def configure_logging() -> None:
    if getattr(configure_logging, "_configured", False):  # type: ignore[attr-defined]
        return

    log_level = os.getenv("TG_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Reduce noisy loggers if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    setattr(configure_logging, "_configured", True)  # type: ignore[attr-defined]


