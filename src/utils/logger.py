"""Rotating file logger and thread-safe GUI queue handler."""

import logging
from logging.handlers import RotatingFileHandler
import queue
from typing import Optional
from src.utils.config import get_app_log_level, get_log_file_path


class QueueLogHandler(logging.Handler):
    """Thread-safe logging handler that pushes formatted log records to a queue."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_queue.put_nowait(msg)
        except Exception:
            self.handleError(record)


_LOGGER_NAME = "invoice_receipt_parser"
_GUI_QUEUE: queue.Queue[str] = queue.Queue(maxsize=500)


def get_gui_log_queue() -> queue.Queue[str]:
    """Returns the shared thread-safe queue for GUI status bar log updates."""
    return _GUI_QUEUE


def setup_logger(name: str = _LOGGER_NAME, custom_queue: Optional[queue.Queue] = None) -> logging.Logger:
    """Configures and returns the application logger with rotating file and queue handlers."""
    logger = logging.getLogger(name)
    level_name = get_app_log_level()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        try:
            log_file = get_log_file_path()
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass

        q_target = custom_queue if custom_queue is not None else _GUI_QUEUE
        queue_handler = QueueLogHandler(q_target)
        queue_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(queue_handler)

    return logger


def get_logger() -> logging.Logger:
    """Returns the singleton application logger."""
    return setup_logger(_LOGGER_NAME)
