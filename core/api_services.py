from __future__ import annotations

from pathlib import Path
from typing import Any

from core.google_logger import GoogleSheetLogger
from core.module_registry import get_module, load_modules
from core.runner import ModuleRunner
from core.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, TESTLINK_API_KEY, TESTLINK_URL
from core.store import ExecutionStore
from core.testlink_generator import (
    TestLinkCaseGenerator,
    TestLinkGeneratorConfig,
    default_output_dir_for_module,
)
from core.url_agent import URLAuditAgent


def list_modules_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": module.id,
            "label": module.label,
            "suite": module.suite,
            "description": module.description,
            "sheet_name": module.sheet_name,
            "default_tab": module.default_tab,
            "runner": module.runner,
        }
        for module in load_modules()
    ]


def get_module_payload(module_id: str) -> dict[str, Any]:
    module = get_module(module_id)
    return {
        "id": module.id,
        "label": module.label,
        "suite": module.suite,
        "description": module.description,
        "sheet_name": module.sheet_name,
        "default_tab": module.default_tab,
        "runner": module.runner,
    }


def get_status_payload() -> dict[str, Any]:
    ai_enabled = bool(LLM_API_KEY and LLM_BASE_URL and LLM_MODEL)
    testlink_enabled = bool(TESTLINK_API_KEY and TESTLINK_URL)
    return {
        "ai": {
            "enabled": ai_enabled,
            "label": "Enabled" if ai_enabled else "Disabled",
            "base_url": LLM_BASE_URL or "",
            "model": LLM_MODEL or "",
        },
        "testlink": {
            "enabled": testlink_enabled,
            "label": "Configured" if testlink_enabled else "Missing Config",
            "url": TESTLINK_URL or "",
        },
    }


def list_sheet_tabs(sheet_name: str, fallback_tab: str) -> list[str]:
    logger = GoogleSheetLogger(sheet_name, fallback_tab)
    return logger.list_tab_names()


def read_sheet_records(
    *,
    sheet_name: str,
    tab_name: str,
    status: list[str] | None = None,
    browser: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
) -> list[dict[str, str]]:
    logger = GoogleSheetLogger(sheet_name, tab_name)
    return logger.filter_records(
        tab_name=tab_name,
        status=status,
        browser=browser,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )


def list_runs(limit: int = 50, suite_name: str | None = None) -> list[dict[str, Any]]:
    return ExecutionStore().list_runs(limit=limit, suite_name=suite_name)


def list_locator_healings(limit: int = 100) -> list[dict[str, Any]]:
    return ExecutionStore().list_locator_healings(limit=limit)


def list_step_events(limit: int = 100) -> list[dict[str, Any]]:
    return ExecutionStore().list_step_events(limit=limit)


def run_module(module_id: str) -> dict[str, Any]:
    return ModuleRunner().run_module(module_id)


def run_url_audit(url: str, *, headless: bool = False, slow_mo: int = 100) -> dict[str, Any]:
    return URLAuditAgent().run(url, headless=headless, slow_mo=slow_mo)


def generate_testlink_tests(
    *,
    module_id: str,
    suite_id: int,
    output_dir: str | None = None,
    overwrite: bool = False,
    max_cases: int | None = None,
) -> dict[str, Any]:
    target_dir = Path(output_dir).resolve() if output_dir else default_output_dir_for_module(module_id)
    config = TestLinkGeneratorConfig(
        suite_id=suite_id,
        module_id=module_id,
        output_dir=target_dir,
        overwrite=overwrite,
        max_cases=max_cases,
    )
    results = TestLinkCaseGenerator(config).run()
    return {
        "module": get_module_payload(module_id),
        "suite_id": suite_id,
        "output_dir": str(target_dir),
        "generated": sum(1 for item in results if item.status == "generated"),
        "skipped": sum(1 for item in results if item.status == "skipped"),
        "failed": sum(1 for item in results if item.status == "failed"),
        "results": [
            {
                "title": item.title,
                "status": item.status,
                "detail": item.detail,
                "output_path": str(item.output_path) if item.output_path else None,
            }
            for item in results
        ],
    }


def latest_run_for_module(module_id: str) -> dict[str, Any] | None:
    module = get_module(module_id)
    runs = ExecutionStore().list_runs(limit=1, suite_name=module.suite)
    return runs[0] if runs else None
