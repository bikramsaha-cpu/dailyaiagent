from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FRAMEWORK_ROOT.parent
for path in (str(FRAMEWORK_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest
from playwright.sync_api import sync_playwright

from core.healing import attach_healing
from core.settings import RUNS_DIR
from test_data.config import (
    DEFAULT_BROWSERS,
    AUTH_SESSION_FILE,
    BMC_LOGIN_PHONE,
    ENQ_SHEET_NAME,
    ENQ_SHEET_TAB,
    HEADLESS,
    SLOW_MO,
)
from utils.google import build_google_logger


def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="append",
        choices=["chromium", "firefox", "webkit"],
        help="Browser to run. Can be passed multiple times.",
    )
    parser.addoption("--headed", action="store_true", help="Run browsers in headed mode.")
    parser.addoption("--slow-mo", type=int, default=None, help="Slow browser actions by N milliseconds.")


def pytest_configure(config):
    config._automation_started_at = datetime.now()
    config._automation_results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "browser_breakdown": defaultdict(lambda: {"Pass": 0, "Fail": 0}),
    }


def pytest_generate_tests(metafunc):
    if "browser_name" not in metafunc.fixturenames:
        return
    configured = metafunc.config.getoption("--browser") or DEFAULT_BROWSERS
    metafunc.parametrize("browser_name", configured, scope="function")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return

    results = item.config._automation_results
    browser_name = "unknown"
    if hasattr(item, "callspec"):
        browser_name = item.callspec.params.get("browser_name", "unknown")

    if report.passed:
        results["passed"] += 1
        results["browser_breakdown"][browser_name]["Pass"] += 1
    elif report.failed:
        results["failed"] += 1
        results["browser_breakdown"][browser_name]["Fail"] += 1
    elif report.skipped:
        results["skipped"] += 1


def pytest_sessionfinish(session, exitstatus):
    started_at = session.config._automation_started_at
    finished_at = datetime.now()
    results = session.config._automation_results
    passed = int(results["passed"])
    failed = int(results["failed"])
    skipped = int(results["skipped"])
    total = passed + failed + skipped
    payload = {
        "suite_name": "ENQ",
        "module_name": "Desktop ENQ",
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "status": "Pass" if failed == 0 else "Fail",
        "browser_breakdown": {key: dict(value) for key, value in results["browser_breakdown"].items()},
        "exitstatus": exitstatus,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "enq_pytest_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def enq_run_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture(scope="session")
def enq_browser_results():
    return defaultdict(lambda: {"Pass": 0, "Fail": 0})


@pytest.fixture(scope="session")
def enq_logger():
    return build_google_logger(ENQ_SHEET_NAME, ENQ_SHEET_TAB)


@pytest.fixture
def browser(playwright_instance, browser_name, request):
    headed = request.config.getoption("--headed")
    slow_mo = request.config.getoption("--slow-mo")
    launch_options = {
        "headless": False if headed else HEADLESS,
        "slow_mo": SLOW_MO if slow_mo is None else slow_mo,
    }
    browser_obj = getattr(playwright_instance, browser_name).launch(**launch_options)
    yield browser_obj
    browser_obj.close()


@pytest.fixture
def context(browser, request):
    context_options = {}
    if request.node.get_closest_marker("loggedin"):
        if not AUTH_SESSION_FILE.exists():
            pytest.fail(
                f"Shared BMC auth session file not found at {AUTH_SESSION_FILE}. "
                "Run `python -m pytest playwright-framework/tests/enq/smoke/test_auth.py --browser chromium --headed` first."
            )
        context_options["storage_state"] = str(AUTH_SESSION_FILE)
    context_obj = browser.new_context(**context_options)
    yield context_obj
    context_obj.close()


@pytest.fixture
def page(context, browser_name, request):
    marker = request.node.get_closest_marker("module")
    module_name = marker.args[0] if marker and marker.args else "ENQ"
    healing_page = attach_healing(
        context.new_page(),
        suite_name="ENQ",
        module_name=module_name,
        test_name=request.node.name,
    )
    healing_page._context["test_file"] = request.node.path.name
    return healing_page


@pytest.fixture
def page_context(browser_name, enq_run_time, enq_browser_results, enq_logger):
    return {
        "browser_name": browser_name,
        "run_time": enq_run_time,
        "browser_results": enq_browser_results,
        "logger": enq_logger,
        "mobile_number": BMC_LOGIN_PHONE,
    }
