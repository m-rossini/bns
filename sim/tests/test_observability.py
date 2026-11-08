"""Tests for per-run rotating file logging."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from sim.config import SimulationConfig
from sim.observability import active_log_file, configure_logging, get_logger

ROOT = logging.getLogger("bean")


@pytest.fixture(autouse=True)
def _restore_logger():
    saved_handlers = list(ROOT.handlers)
    saved_level = ROOT.level
    saved_propagate = ROOT.propagate
    yield
    for handler in list(ROOT.handlers):
        ROOT.removeHandler(handler)
        if handler not in saved_handlers:
            handler.close()
    for handler in saved_handlers:
        ROOT.addHandler(handler)
    ROOT.setLevel(saved_level)
    ROOT.propagate = saved_propagate


def _flush() -> None:
    for handler in ROOT.handlers:
        handler.flush()


def test_each_run_writes_its_own_file(tmp_path, monkeypatch):
    monkeypatch.setenv("BEAN_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("BEAN_LOG_FILE", raising=False)

    configure_logging(SimulationConfig())
    path = active_log_file()

    assert path is not None
    assert Path(path).parent == tmp_path
    assert Path(path).name.startswith("bean-")

    get_logger("test").info("hello file")
    _flush()

    assert "hello file" in Path(path).read_text(encoding="utf-8")


def test_log_file_override(tmp_path, monkeypatch):
    target = tmp_path / "custom" / "run.log"
    monkeypatch.setenv("BEAN_LOG_FILE", str(target))

    configure_logging(SimulationConfig())

    assert active_log_file() == str(target)
    assert target.parent.is_dir()


def test_rotating_handler_uses_configured_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("BEAN_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("BEAN_LOG_FILE", raising=False)
    config = SimulationConfig()
    config.logging.max_bytes = 1024
    config.logging.backup_count = 2

    configure_logging(config)

    file_handlers = [
        h for h in ROOT.handlers if isinstance(h, RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == 1024
    assert file_handlers[0].backupCount == 2


def test_file_logging_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("BEAN_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("BEAN_LOG_FILE", raising=False)
    config = SimulationConfig()
    config.logging.file_enabled = False

    configure_logging(config)

    assert active_log_file() is None
    assert list(tmp_path.iterdir()) == []
