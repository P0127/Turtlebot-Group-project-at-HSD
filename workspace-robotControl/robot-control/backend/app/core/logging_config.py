"""Logging configuration for the backend."""
from __future__ import annotations

import logging.config


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "std_out",
        },
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "propagate": True,
        },
        "uvicorn.access": {
            "level": "WARNING",
            "propagate": False,
        },
        "backend.core.state_service": {
            "level": "DEBUG",
            "propagate": True,
        },
    },
    "formatters": {
        "std_out": {
            "format": "%(name)s:[%(levelname)s][%(filename)s:%(funcName)s:%(lineno)s] - %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S",
        },
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOG_CONFIG)