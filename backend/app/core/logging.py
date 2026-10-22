"""
backend/app/core/logging.py

Centralized, structured logging configuration for Cardiac Deformation Lab.
Provides:
- ISO 8601 timestamps
- Clean formatting for console and file logs
- Automatic sanitization of sensitive keywords (passwords, tokens, keys)
- Configurable log levels via LOG_LEVEL environment variable
"""

import logging
import re
import sys
from typing import Any
from app.core.config import LOG_LEVEL, IS_PRODUCTION

# Sensitive patterns that must never be emitted into logs
SENSITIVE_PATTERNS = [
    re.compile(r"((?:[\"']?(?:password|password_hash|secret|secret_key|token|authorization)[\"']?)\s*[:=]\s*['\"]?(?:Bearer\s+)?)([^\s,'\"}]+)(['\"]?)", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([A-Za-z0-9\-_\.=]+)", re.IGNORECASE),
]


def _redact_match(m: re.Match) -> str:
    groups = m.groups()
    if len(groups) >= 3:
        return f"{groups[0]}***REDACTED***{groups[2]}"
    elif len(groups) == 2:
        return f"{groups[0]}***REDACTED***"
    return "***REDACTED***"


class SanitizingFormatter(logging.Formatter):
    """Logging formatter that redacts passwords, tokens, and secret parameters."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            msg = pattern.sub(_redact_match, msg)
        return msg


def setup_logger(name: str = "cardiac_lab") -> logging.Logger:
    """Create or retrieve a configured logger instance."""
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already initialized
    if logger.handlers:
        return logger

    # Resolve log level from config
    numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(numeric_level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    formatter = SanitizingFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.propagate = False
    return logger


logger = setup_logger("cardiac_lab")
