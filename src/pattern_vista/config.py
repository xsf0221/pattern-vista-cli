"""Persisted CLI config (the api_key) under ~/.config/pattern-vista/config.json.

Resolution order for the api_key, highest priority first:
  1. explicit value passed on the command line (--api-key)
  2. PATTERN_VISTA_API_KEY environment variable
  3. the config file written by `pv config set-key`
"""

import json
import os
import stat
from pathlib import Path
from typing import Optional

from .constants import API_KEY_ENV


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "pattern-vista"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> Path:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = config_path()
    path.write_text(json.dumps(data, indent=2) + "\n")
    # Secret lives here — keep it owner-readable only.
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return path


def set_api_key(api_key: str) -> Path:
    data = load_config()
    data["api_key"] = api_key
    return save_config(data)


def resolve_api_key(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit
    env = os.environ.get(API_KEY_ENV)
    if env:
        return env
    return load_config().get("api_key")
