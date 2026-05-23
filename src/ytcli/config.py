import json
import os
import stat
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base) / "ytcli" if base else Path.home() / ".config" / "ytcli"


CONFIG_DIR: Path = _config_dir()
CONFIG_PATH: Path = CONFIG_DIR / "ytcli.config.json"


def load() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r") as f:
        return json.load(f)


def save(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_DIR.chmod(stat.S_IRWXU)
    except OSError:
        pass
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(config, f, indent=2, sort_keys=True)
    tmp.chmod(stat.S_IRUSR | stat.S_IWUSR)
    tmp.replace(CONFIG_PATH)
