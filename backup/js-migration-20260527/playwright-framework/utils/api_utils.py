from __future__ import annotations

import json
from urllib.request import Request, urlopen


def get_json(url: str, timeout: int = 30) -> dict:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
