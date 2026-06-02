from __future__ import annotations

import os


def build_google_logger(sheet_name: str, tab_name: str):
    enabled = os.getenv("AUTOMATION_GOOGLE_LOGGING_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return None
    try:
        from core.google_logger import GoogleSheetLogger

        return GoogleSheetLogger(sheet_name, tab_name)
    except Exception as exc:
        print(f"Google logging disabled for this run: {type(exc).__name__}: {exc}")
        return None
