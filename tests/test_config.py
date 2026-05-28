import importlib

import pattern_vista.config as cfg
from pattern_vista.constants import API_KEY_ENV


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    importlib.reload(cfg)
    return cfg


def test_set_and_resolve_from_file(tmp_path, monkeypatch):
    c = _isolate(tmp_path, monkeypatch)
    c.set_api_key("pv_live_fromfile")
    assert c.resolve_api_key() == "pv_live_fromfile"
    assert c.config_path().exists()


def test_env_overrides_file(tmp_path, monkeypatch):
    c = _isolate(tmp_path, monkeypatch)
    c.set_api_key("pv_live_fromfile")
    monkeypatch.setenv(API_KEY_ENV, "pv_live_fromenv")
    assert c.resolve_api_key() == "pv_live_fromenv"


def test_explicit_overrides_all(tmp_path, monkeypatch):
    c = _isolate(tmp_path, monkeypatch)
    c.set_api_key("pv_live_fromfile")
    monkeypatch.setenv(API_KEY_ENV, "pv_live_fromenv")
    assert c.resolve_api_key("pv_live_explicit") == "pv_live_explicit"


def test_no_key_returns_none(tmp_path, monkeypatch):
    c = _isolate(tmp_path, monkeypatch)
    assert c.resolve_api_key() is None
