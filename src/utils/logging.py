"""Structured logging setup."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path


class SizeSplitFileHandler(logging.Handler):
    """Write logs to a file and split when it exceeds max_bytes."""

    terminator = "\n"

    def __init__(self, base_path: Path, max_bytes: int, encoding: str = "utf-8") -> None:
        super().__init__()
        self._base_path = Path(base_path)
        self._max_bytes = max_bytes
        self._encoding = encoding
        self._stream = None
        self._current_path: Path | None = None
        self._current_size = 0
        self._base_path.parent.mkdir(parents=True, exist_ok=True)
        self._open_stream(self._select_path())

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        data = msg + self.terminator
        encoded = data.encode(self._encoding, errors="replace")
        self.acquire()
        try:
            if self._should_split(len(encoded)):
                self._open_stream(self._next_path())
            if self._stream is None:
                return
            self._stream.write(data)
            self._stream.flush()
            self._current_size += len(encoded)
        finally:
            self.release()

    def close(self) -> None:
        self.acquire()
        try:
            if self._stream:
                self._stream.close()
            self._stream = None
        finally:
            self.release()
        super().close()

    def _should_split(self, incoming_bytes: int) -> bool:
        return self._current_size + incoming_bytes > self._max_bytes

    def _select_path(self) -> Path:
        if not self._base_path.exists():
            return self._base_path
        size = self._base_path.stat().st_size
        if size < self._max_bytes:
            return self._base_path
        return self._next_path()

    def _next_path(self) -> Path:
        ts = time.strftime("%Y%m%d_%H%M%S")
        name = f"{self._base_path.stem}-{ts}{self._base_path.suffix}"
        return self._base_path.with_name(name)

    def _open_stream(self, path: Path) -> None:
        if self._stream:
            self._stream.close()
        self._current_path = path
        self._stream = open(path, "a", encoding=self._encoding)
        try:
            self._current_size = path.stat().st_size
        except FileNotFoundError:
            self._current_size = 0


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger. Call once at application startup."""
    from src.config.settings import settings

    numeric = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s %(levelname)-8s %(name)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    handlers: list[logging.Handler] = []
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if settings.LOG_FILE_ENABLED:
        log_dir = Path(settings.LOG_DIR)
        log_path = log_dir / f"{settings.LOG_FILE_PREFIX}.log"
        file_handler = SizeSplitFileHandler(
            log_path,
            max_bytes=settings.LOG_FILE_MAX_MB * 1024 * 1024,
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root = logging.getLogger()
    root.setLevel(numeric)
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. setup_logging() should be called first."""
    return logging.getLogger(name)
