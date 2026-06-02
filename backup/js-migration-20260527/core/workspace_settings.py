from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
UI_SETTINGS_PATH = ROOT_DIR / "artifacts" / "ui_settings.json"


def load_workspace_settings() -> dict[str, str]:
    if not UI_SETTINGS_PATH.exists():
        return {}
    try:
        payload = json.loads(UI_SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in payload.items()
        if value is not None
    }


def save_workspace_settings(values: dict[str, Any]) -> dict[str, str]:
    UI_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {
        str(key): str(value)
        for key, value in values.items()
        if value is not None
    }
    UI_SETTINGS_PATH.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    return cleaned
