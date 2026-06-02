from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str


class OpenAICompatibleLLM:
    def __init__(self, config: LLMConfig):
        self.config = config

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key and self.config.base_url and self.config.model)

    def suggest_selectors(self, locator_name: str, current_selectors: list[str], context: dict[str, Any] | None = None) -> list[str]:
        if not self.enabled:
            return []

        prompt = self._build_prompt(locator_name, current_selectors, context or {})
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "You help heal flaky Playwright selectors."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            return []

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return self._parse_selectors(content)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        timeout: int = 30,
    ) -> str:
        if not self.enabled:
            return ""

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            return ""

        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    @staticmethod
    def _build_prompt(locator_name: str, current_selectors: list[str], context: dict[str, Any]) -> str:
        return (
            f"Suggest 5 resilient Playwright selectors for locator '{locator_name}'.\n"
            f"Existing selectors: {current_selectors}\n"
            f"Page context: {json.dumps(context, ensure_ascii=True)}\n"
            "Return one selector per line. Prefer role, label, text, or stable attributes."
        )

    @staticmethod
    def _parse_selectors(content: str) -> list[str]:
        selectors: list[str] = []
        for line in content.splitlines():
            item = line.strip().lstrip("-").strip()
            if not item:
                continue
            if item not in selectors:
                selectors.append(item)
        return selectors
