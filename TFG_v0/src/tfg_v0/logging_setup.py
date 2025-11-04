
import logging
import os

def setup_logging(level: str | None = None):
    level = level or os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("tfg_v0")
