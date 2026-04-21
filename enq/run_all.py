import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google_logger import GoogleSheetLogger
from mailer import send_summary_email
from core.reporting import write_html_report
from core.store import ExecutionStore, RunSummary

sys.stdout.reconfigure(encoding="utf-8")

SHEET_NAME = "Buyer Automation"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1t_kEjtyZQ_xcOqJ3v5_apcyCEmi8V6wi5w1KjXNEyqg/edit?gid=0#gid=0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

scripts_to_run = [
    ("buyer_login.py", None),
    (os.path.join("fullyloggedin", "dir", "impcat.py"), "ENQ"),
    (os.path.join("fullyloggedin", "pdp", "pdp.py"), "ENQ"),
    (os.path.join("fullyloggedin", "companyPage", "company_page.py"), "ENQ"),
    (os.path.join("fullyloggedin", "search", "search_city.py"), "ENQ"),
]

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
first_start_time = None
last_end_time = None

for script_rel_path, _ in scripts_to_run:
    script_path = os.path.join(BASE_DIR, script_rel_path)
    start_now = datetime.now()
    if first_start_time is None:
        first_start_time = start_now

    print(f"\n=== Running {script_path} ===")
    child_env = dict(os.environ)
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONPATH"] = ROOT_DIR + os.pathsep + child_env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=child_env,
    )

    print(result.stdout)
    if result.stderr:
        print(f"Error in {script_rel_path}:\n{result.stderr}")

    last_end_time = datetime.now()

total_passed = 0
total_failed = 0
total_total = 0

for _, tab_name in scripts_to_run:
    if not tab_name:
        continue
    try:
        logger = GoogleSheetLogger(SHEET_NAME, tab_name)
        passed, failed, total = logger.get_summary_counts(
            start_time=first_start_time,
            end_time=last_end_time,
        )
        total_passed += passed
        total_failed += failed
        total_total += total

        tab_browser_counts = logger.get_browser_wise_counts(
            start_time=first_start_time,
            end_time=last_end_time,
        )
        for browser, counts in tab_browser_counts.items():
            browser_results[browser]["Pass"] += counts.get("Pass", 0)
            browser_results[browser]["Fail"] += counts.get("Fail", 0)

        print(f"ENQ - Passed: {passed}, Failed: {failed}, Total: {total}")
    except Exception as e:
        print(f"Could not fetch summary for {tab_name}: {e}")

summary_payload = {
    "suite_name": "ENQ",
    "module_name": "Desktop ENQ",
    "started_at": first_start_time.isoformat(timespec="seconds") if first_start_time else datetime.now().isoformat(timespec="seconds"),
    "finished_at": last_end_time.isoformat(timespec="seconds") if last_end_time else datetime.now().isoformat(timespec="seconds"),
    "passed": total_passed,
    "failed": total_failed,
    "total": total_total,
    "status": "Pass" if total_failed == 0 else "Fail",
    "sheet_url": SHEET_URL,
    "browser_breakdown": {browser: dict(counts) for browser, counts in browser_results.items()},
}
summary_payload["report_path"] = str(write_html_report(summary_payload))
ExecutionStore().record_run(RunSummary(**summary_payload))

if total_total > 0:
    try:
        send_summary_email(
            passed=total_passed,
            failed=total_failed,
            total=total_total,
            sheet_url=SHEET_URL,
            tab_name="Desktop ENQ",
            browser_results=browser_results,
        )
    except Exception as email_error:
        print(f"Email step skipped or failed: {email_error}")

sys.exit(0 if total_total > 0 and total_failed == 0 else 1)
