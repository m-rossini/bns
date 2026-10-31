"""Logging and gameplay instrumentation.

Two kinds of signal are emitted:

* **operational** — startup, shutdown, strategy wiring, weather rebuilds,
  configuration problems. These are normal `logging` records under the
  ``bean.*`` logger namespace.
* **business** — what the player actually does and how the world reacts:
  start/pause/resume/quit, cell inspections, day and season changes, weather
  system changes. Each event is a single line with ``event=<name>`` followed
  by ``key=value`` fields, so it can be grepped or parsed.

The level is a runtime parameter. Resolution order:

1. ``BEAN_LOG_LEVEL`` environment variable (set by the Makefile)
2. ``SimulationConfig.logging.level``
3. ``INFO``

Set ``BEAN_LOG_LEVEL=DEBUG`` (or ``make run LOG_LEVEL=DEBUG``) to see
per-tick readings and per-front weather details.
"""

from __future__ import annotations

import logging
import os
from typing import Any

DEFAULT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%H:%M:%S"
ROOT_LOGGER = "bean"


def resolve_level(config: Any | None = None) -> str:
    """Return the effective level name."""
    env = os.environ.get("BEAN_LOG_LEVEL", "").strip()
    if env:
        return env.upper()
    configured = getattr(getattr(config, "logging", None), "level", None)
    return str(configured or "INFO").upper()


def configure_logging(config: Any | None = None) -> str:
    """Install the root handler once and return the effective level name.

    ``force=True`` makes repeated calls deterministic (useful in tests and
    when a container entrypoint configures logging twice).
    """
    logging_cfg = getattr(config, "logging", None)
    fmt = getattr(logging_cfg, "format", DEFAULT_FORMAT)
    datefmt = getattr(logging_cfg, "date_format", DEFAULT_DATE_FORMAT)
    level_name = resolve_level(config)
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root = logging.getLogger(ROOT_LOGGER)
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False

    logging.getLogger(ROOT_LOGGER).debug(
        "logging.configured level=%s source=%s",
        level_name,
        "env" if os.environ.get("BEAN_LOG_LEVEL") else "config",
    )
    return level_name


def get_logger(name: str) -> logging.Logger:
    """Namespaced logger, e.g. ``get_logger('weather')`` -> ``bean.weather``."""
    if name == ROOT_LOGGER or name.startswith(ROOT_LOGGER + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    text = str(value)
    if not text or any(ch.isspace() for ch in text):
        return repr(text)
    return text


def format_event(event: str, **fields: Any) -> str:
    """Render ``event=name key=value ...`` with stable ordering."""
    parts = [f"event={event}"]
    for key in sorted(fields):
        value = fields[key]
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")
    return " ".join(parts)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured business event if the logger is enabled."""
    if not logger.isEnabledFor(level):
        return
    logger.log(level, format_event(event, **fields))


class EventLog:
    """Small facade so callers can carry one object instead of a logger."""

    def __init__(self, name: str, enabled: bool = True):
        self._logger = get_logger(name)
        self.enabled = enabled

    def event(self, name: str, level: int = logging.INFO, **fields: Any) -> None:
        if self.enabled:
            log_event(self._logger, name, level=level, **fields)

    def debug(self, name: str, **fields: Any) -> None:
        self.event(name, level=logging.DEBUG, **fields)
