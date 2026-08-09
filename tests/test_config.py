"""Unit tests for :mod:`app.config` (env + CLI overrides)."""

from __future__ import annotations

import argparse

from app.config import Config


def test_from_env_defaults(monkeypatch):
    monkeypatch.delenv("ADB_API_PORT", raising=False)
    monkeypatch.delenv("ADB_API_HOST", raising=False)
    cfg = Config.from_env()
    assert cfg.port == 8000
    assert cfg.host == "127.0.0.1"


def test_from_env_overrides_port(monkeypatch):
    monkeypatch.setenv("ADB_API_PORT", "9000")
    monkeypatch.delenv("ADB_API_HOST", raising=False)
    cfg = Config.from_env()
    assert cfg.port == 9000


def test_from_env_ignores_non_numeric_port(monkeypatch):
    monkeypatch.setenv("ADB_API_PORT", "not-a-number")
    monkeypatch.delenv("ADB_API_HOST", raising=False)
    cfg = Config.from_env()
    # Non-numeric port must be ignored -> keep default.
    assert cfg.port == 8000


def test_from_env_overrides_host(monkeypatch):
    monkeypatch.setenv("ADB_API_HOST", "0.0.0.0")
    monkeypatch.delenv("ADB_API_PORT", raising=False)
    cfg = Config.from_env()
    assert cfg.host == "0.0.0.0"


def test_load_config_applies_cli_args(monkeypatch):
    monkeypatch.delenv("ADB_API_PORT", raising=False)
    monkeypatch.delenv("ADB_API_HOST", raising=False)
    args = argparse.Namespace(
        host="0.0.0.0",
        port=9999,
        adb_path="/x/adb",
        log_level="DEBUG",
        log_path="x.log",
        auth_enabled=True,
        kill_adb_on_stop=True,
    )
    cfg = Config.load_config(args)
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9999
    assert cfg.adb_path == "/x/adb"
    assert cfg.log_level == "DEBUG"
    assert cfg.log_path == "x.log"
    assert cfg.auth_enabled is True
    assert cfg.kill_adb_on_stop is True


def test_load_config_none_args_uses_env(monkeypatch):
    monkeypatch.setenv("ADB_API_PORT", "7777")
    cfg = Config.load_config(None)
    assert cfg.port == 7777


def test_load_config_env_then_cli_wins(monkeypatch):
    monkeypatch.setenv("ADB_API_PORT", "7777")
    args = argparse.Namespace(port=8888)
    cfg = Config.load_config(args)
    # CLI arg must override env.
    assert cfg.port == 8888
