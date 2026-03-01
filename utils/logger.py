"""
Structured logging system for RustServerManager.
Provides both file and console logging with level control.
"""

import logging
import os
from pathlib import Path
from typing import Optional


class LogHandler:
    _instance: Optional["LogHandler"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> "LogHandler":
        if cls._instance is None:
            cls._instance = super(LogHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self) -> None:
        """Initialize logger with file and console handlers."""
        self._logger = logging.getLogger("RustServerManager")
        self._logger.setLevel(logging.DEBUG)

        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(log_dir / "app.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)

        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    @property
    def logger(self) -> logging.Logger:
        """Get the logger instance."""
        if self._logger is None:
            self._setup_logger()
        return self._logger

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str, exc_info: bool = False) -> None:
        self.logger.error(msg, exc_info=exc_info)

    def critical(self, msg: str, exc_info: bool = False) -> None:
        self.logger.critical(msg, exc_info=exc_info)


# Singleton instance
log = LogHandler()
