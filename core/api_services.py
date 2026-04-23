from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.google_logger import GoogleSheetLogger
from core.mailer import send_filtered_sheet_report_email
from core.module_registry import get_module, load_modules
from core.runner import ModuleRunner
from core.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    ROOT_DIR,
    TESTLINK_API_KEY,
    TESTLINK_CA_BUNDLE,
    TESTLINK_INSECURE_SKIP_VERIFY,
    TESTLINK_URL,
)
from core.store import ExecutionStore
from core.testlink_generator import (
    TestLinkCaseGenerator,
    TestLinkGeneratorConfig,
    default_output_dir_for_module,
)


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
    command = [sys.executable, str((ROOT_DIR / "run_url_agent.py").resolve()), "--url", url, "--slow-mo", str(slow_mo)]
    if headless:
        command.append("--headless")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT_DIR),
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    payload_text = stdout
    json_start = stdout.find("{")
    if json_start >= 0:
        payload_text = stdout[json_start:]
    try:
        payload = json.loads(payload_text) if payload_text else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"URL agent returned non-JSON output.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        ) from exc
    if stderr:
        payload["stderr"] = ((payload.get("stderr") or "") + ("\n" if payload.get("stderr") else "") + stderr).strip()
    if result.returncode != 0:
        payload.setdefault("status", "Fail")
        payload.setdefault("suite_name", "URL Agent")
        payload.setdefault("module_name", url)
        payload.setdefault("passed", 0)
        payload.setdefault("failed", 1)
        payload.setdefault("total", 1)
        payload.setdefault("extra", {})
        payload["extra"].setdefault("human_required", ["URL agent failed before producing a complete report."])
        payload["extra"].setdefault("findings", [])
        payload["extra"].setdefault("test_cases", [])
        payload["extra"].setdefault("case_counts", {"Pass": 0, "Fail": 1, "Needs Review": 0})
        payload["extra"].setdefault("url", url)
    else:
        payload.setdefault("status", "Pass")
    payload.setdefault("command", " ".join(command))
    return payload


def generate_testlink_tests(
    *,
    module_id: str,
    suite_id: int,
    output_dir: str | None = None,
    overwrite: bool = False,
    max_cases: int | None = None,
    testlink_api_key: str | None = None,
    testlink_url: str | None = None,
    testlink_ca_bundle: str | None = None,
    testlink_insecure_skip_verify: bool | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
) -> dict[str, Any]:
    target_dir = Path(output_dir).resolve() if output_dir else default_output_dir_for_module(module_id)
    config = TestLinkGeneratorConfig(
        suite_id=suite_id,
        module_id=module_id,
        output_dir=target_dir,
        testlink_url=testlink_url or TESTLINK_URL,
        testlink_api_key=testlink_api_key or TESTLINK_API_KEY,
        llm_api_key=llm_api_key or LLM_API_KEY,
        llm_base_url=llm_base_url or LLM_BASE_URL,
        llm_model=llm_model or LLM_MODEL,
        ca_bundle=testlink_ca_bundle or TESTLINK_CA_BUNDLE,
        insecure_skip_verify=(
            TESTLINK_INSECURE_SKIP_VERIFY
            if testlink_insecure_skip_verify is None
            else testlink_insecure_skip_verify
        ),
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


def send_sheet_report_email(
    *,
    module_id: str,
    sheet_name: str,
    tab_name: str,
    status: list[str] | None = None,
    browser: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    recipients: list[str] | None = None,
) -> dict[str, Any]:
    module = get_module(module_id)
    records = read_sheet_records(
        sheet_name=sheet_name,
        tab_name=tab_name,
        status=status,
        browser=browser,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    filters = {
        "Module": module.label,
        "Sheet": sheet_name,
        "Tab": tab_name,
        "Status": ", ".join(status or []) or "All",
        "Browser": ", ".join(browser or []) or "All",
        "Search": search or "All",
        "Start Date": start_date or "Any",
        "End Date": end_date or "Any",
    }
    return send_filtered_sheet_report_email(
        module_label=module.label,
        sheet_name=sheet_name,
        tab_name=tab_name,
        records=records,
        filters=filters,
        recipients=recipients,
    )
