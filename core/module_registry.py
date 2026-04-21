from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.settings import DEFAULT_SHEET_NAME, MODULE_REGISTRY_PATH, ROOT_DIR


@dataclass(slots=True)
class ModuleDefinition:
    id: str
    label: str
    suite: str
    runner: str
    description: str = ""
    schedule: str = "daily"
    sheet_name: str = DEFAULT_SHEET_NAME
    default_tab: str = ""

    @property
    def runner_path(self) -> Path:
        return (ROOT_DIR / self.runner).resolve()


def load_modules(path: str | Path = MODULE_REGISTRY_PATH) -> list[ModuleDefinition]:
    registry_path = Path(path)
    if not registry_path.exists():
        return []
    with registry_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [ModuleDefinition(**entry) for entry in raw]


def get_module(module_id: str, path: str | Path = MODULE_REGISTRY_PATH) -> ModuleDefinition:
    for module in load_modules(path):
        if module.id == module_id:
            return module
    raise KeyError(f"Unknown module: {module_id}")
