from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
PLAYWRIGHT_FRAMEWORK_DIR = os.path.join(ROOT_DIR, "playwright-framework")
if PLAYWRIGHT_FRAMEWORK_DIR not in sys.path:
    sys.path.insert(0, PLAYWRIGHT_FRAMEWORK_DIR)

from core.mailer import send_summary_email
from core.reporting import write_html_report
from core.settings import RUNS_DIR
from core.store import ExecutionStore, RunSummary
from test_data.config import DEFAULT_BROWSERS, ENQ_SHEET_URL


def parse_args():
    parser = argparse.ArgumentParser(description="Run the modern ENQ Playwright pytest suite.")
    parser.add_argument("--skip-login", action="store_true", help="Reuse the existing ENQ session file.")
    parser.add_argument("--login-browser", default="chromium", choices=["chromium", "firefox", "webkit"])
    parser.add_argument("--browser", action="append", choices=["chromium", "firefox", "webkit"])
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=None)
    return parser.parse_known_args()


def pytest_common_args(args) -> list[str]:
    common = []
    for browser in args.browser or DEFAULT_BROWSERS:
        common.extend(["--browser", browser])
    if args.headed:
        common.append("--headed")
    if args.slow_mo is not None:
        common.extend(["--slow-mo", str(args.slow_mo)])
    return common


def run_pytest(pytest_args: list[str]) -> subprocess.CompletedProcess:
    command = [sys.executable, "-m", "pytest", *pytest_args]
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        cwd=ROOT_DIR,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result


def latest_summary() -> dict:
    summary_path = RUNS_DIR / "enq_pytest_summary.json"
    if not summary_path.exists():
        return {
            "suite_name": "ENQ",
            "module_name": "Desktop ENQ",
            "started_at": "",
            "finished_at": "",
            "passed": 0,
            "failed": 1,
            "total": 1,
            "status": "Fail",
            "browser_breakdown": {},
        }
    return json.loads(summary_path.read_text(encoding="utf-8"))


def record_portal_summary(summary: dict, command: str, stdout: str, stderr: str) -> dict:
    summary_payload = {
        "suite_name": "ENQ",
        "module_name": "Desktop ENQ",
        "started_at": summary.get("started_at") or "",
        "finished_at": summary.get("finished_at") or "",
        "passed": int(summary.get("passed", 0)),
        "failed": int(summary.get("failed", 0)),
        "total": int(summary.get("total", 0)),
        "status": summary.get("status", "Fail"),
        "command": command,
        "stdout": stdout[-12000:],
        "stderr": stderr[-12000:],
        "sheet_url": ENQ_SHEET_URL,
        "browser_breakdown": summary.get("browser_breakdown", {}),
        "extra": {"runner": "pytest-pom", "summary_file": str(RUNS_DIR / "enq_pytest_summary.json")},
    }
    summary_payload["report_path"] = str(write_html_report(summary_payload))
    ExecutionStore().record_run(RunSummary(**summary_payload))
    return summary_payload


def main() -> int:
    args, extra_pytest_args = parse_args()
    common_args = pytest_common_args(args)
    selected_targets = [
        item
        for item in extra_pytest_args
        if item.endswith(".py") or item.startswith("tests/") or item.startswith("playwright-framework/")
    ]
    passthrough_args = [item for item in extra_pytest_args if item not in selected_targets]
    selected_auth_only = bool(selected_targets) and all(
        os.path.basename(target).lower() == "test_auth.py" for target in selected_targets
    )

    if not args.skip_login:
        login_args = [
            os.path.join("playwright-framework", "tests", "enq", "smoke", "test_auth.py"),
            "--browser",
            args.login_browser,
        ]
        if args.headed:
            login_args.append("--headed")
        if args.slow_mo is not None:
            login_args.extend(["--slow-mo", str(args.slow_mo)])
        if selected_auth_only:
            login_args.extend(passthrough_args)
        login_result = run_pytest(login_args)
        if login_result.returncode != 0:
            summary = latest_summary()
            payload = record_portal_summary(
                summary,
                " ".join([sys.executable, "-m", "pytest", *login_args]),
                login_result.stdout,
                login_result.stderr,
            )
            print(f"ENQ login failed. Report: {payload.get('report_path')}")
            return login_result.returncode
        if selected_auth_only:
            summary = latest_summary()
            payload = record_portal_summary(
                summary,
                " ".join([sys.executable, "-m", "pytest", *login_args]),
                login_result.stdout,
                login_result.stderr,
            )
            print(f"ENQ auth completed. Report: {payload.get('report_path')}")
            return login_result.returncode

    test_targets = selected_targets or [os.path.join("playwright-framework", "tests", "enq")]
    main_args = [
        *test_targets,
        "-m",
        "enq and not auth",
        *common_args,
        *passthrough_args,
    ]
    result = run_pytest(main_args)
    summary = latest_summary()
    payload = record_portal_summary(
        summary,
        " ".join([sys.executable, "-m", "pytest", *main_args]),
        result.stdout,
        result.stderr,
    )

    if int(payload.get("total", 0)) > 0:
        try:
            send_summary_email(
                passed=payload["passed"],
                failed=payload["failed"],
                total=payload["total"],
                sheet_url=ENQ_SHEET_URL,
                tab_name="Desktop ENQ",
                browser_results=payload["browser_breakdown"],
            )
        except Exception as exc:
            print(f"Email step skipped or failed: {type(exc).__name__}: {exc}")

    print(f"ENQ report: {payload.get('report_path')}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
