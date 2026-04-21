from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.settings import ARTIFACTS_DIR


REGISTRY_PATH = ARTIFACTS_DIR / "locator_registry.json"


@dataclass(slots=True)
class RegistryEntry:
    selector: str
    strategy: str
    page_url: str | None = None
    page_title: str | None = None
    html_snapshot: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] | None = None


class LocatorRegistry:
    def __init__(self, path: str | Path = REGISTRY_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, locator_name: str) -> RegistryEntry | None:
        payload = self._data.get(locator_name)
        if not payload:
            return None
        return RegistryEntry(**payload)

    def set(self, locator_name: str, entry: RegistryEntry | dict[str, Any]) -> RegistryEntry:
        payload = asdict(entry) if isinstance(entry, RegistryEntry) else dict(entry)
        self._data[locator_name] = payload
        self._save()
        return RegistryEntry(**payload)

    def items(self) -> dict[str, dict[str, Any]]:
        return dict(self._data)
