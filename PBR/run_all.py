import subprocess
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google_logger import GoogleSheetLogger
from mailer import send_summary_email
from core.reporting import write_html_report
from core.store import ExecutionStore, RunSummary

sys.stdout.reconfigure(encoding='utf-8')

# Google Sheet details
SHEET_NAME = "Buyer Automation"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1t_kEjtyZQ_xcOqJ3v5_apcyCEmi8V6wi5w1KjXNEyqg/edit?gid=415313835#gid=415313835"

# Base folder where scripts are stored
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Scripts and their corresponding Google Sheet tab names
scripts_to_run = [
    ("buyer_login.py", None),
    (os.path.join("FullyLoggedin", "CompanyPage", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_Company_Page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "DIR", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_DIR_Header.py"), "PBR"),
    #(os.path.join("FullyLoggedin", "DIR", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_DIR_Home_Page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "DIR", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_MCAT_Page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "Other", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_BuyerMy_Home_page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "Other", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_BuyerMy_My_Orders_Page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "Other", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_BuyerMy_My_Orders_Recommended_Categories.py"), "PBR"),
    #(os.path.join("FullyLoggedin", "PDP", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_PDP_page.py"), "PBR"),
    #(os.path.join("FullyLoggedin", "PDP", "test_Verify_user_is_able_to_submit_a_BL_via_chatBL_form_in_PDP_page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "Search", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_Search_All_india_Page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "Search", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_Search_City_page.py"), "PBR"),
    (os.path.join("FullyLoggedin", "Search", "test_Verify_user_is_able_to_submit_a_BL_via_chatBL_form_in_the_search_page.py"), "PBR"),
    (os.path.join("Identified", "CompanyPage", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_Company_Page.py"), "PBR"),
    (os.path.join("Identified", "DIR", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_DIR_Header.py"), "PBR"),
    (os.path.join("Identified", "DIR", "test_Verify_that_user_is_able_to_submit_the_PBR__Form_on_DIR_Home_Page.py"), "PBR"),
    (os.path.join("Identified", "Search", "test_Verify_user_is_able_to_submit_a_BL_via_chatBL_form_in_the_search_page.py"), "PBR")
]
# Track browser-wise and total results
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

first_start_time = None
last_end_time = None

# Step 1: Run all scripts
for script_rel_path, _ in scripts_to_run:
    script_path = os.path.join(BASE_DIR, script_rel_path)
    start_now = datetime.now()

    if first_start_time is None:
        first_start_time = start_now

    print(f"\n=== Running {script_path} at {start_now.strftime('%H:%M:%S')} ===")
    child_env = dict(os.environ)
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONPATH"] = ROOT_DIR + os.pathsep + child_env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=child_env
    )

    print(result.stdout)
    if result.stderr:
        print(f"Error in {script_rel_path}:\n{result.stderr}")

    last_end_time = datetime.now()

# Step 2: Fetch counts only once per tab_name
print(f"\n🕒 Using run time range: {first_start_time} → {last_end_time}")

total_passed = 0
total_failed = 0
total_tests = 0

unique_tabs = sorted({tab for _, tab in scripts_to_run if tab})

for tab_name in unique_tabs:
    try:
        logger = GoogleSheetLogger(SHEET_NAME, tab_name)

        passed, failed, total = logger.get_summary_counts(
            start_time=first_start_time,
            end_time=last_end_time
        )
        total_passed += passed
        total_failed += failed
        total_tests += total

        tab_browser_counts = logger.get_browser_wise_counts(
            start_time=first_start_time,
            end_time=last_end_time
        )
        for browser, counts in tab_browser_counts.items():
            browser_results[browser]["Pass"] += counts.get("Pass", 0)
            browser_results[browser]["Fail"] += counts.get("Fail", 0)

    except Exception as e:
        print(f"❌ Could not fetch summary for {tab_name}: {e}")

# Step 3: Print nicely aligned results
print("\n📝 Test Summary:")
print(f"✅ Passed: {total_passed}")
print(f"❌ Failed: {total_failed}")
print(f"📊 Total:  {total_tests}")

print("\n🧪 Browser-wise Breakdown")
print(f"{'Browser':<12}{'✅ Passed':<12}{'❌ Failed':<12}{'📊 Total':<8}")
for browser, counts in browser_results.items():
    total_browser = counts['Pass'] + counts['Fail']
    print(f"{browser:<12}{counts['Pass']:<12}{counts['Fail']:<12}{total_browser:<8}")

summary_payload = {
    "suite_name": "PBR",
    "module_name": "Desktop PBR",
    "started_at": first_start_time.isoformat(timespec="seconds") if first_start_time else datetime.now().isoformat(timespec="seconds"),
    "finished_at": last_end_time.isoformat(timespec="seconds") if last_end_time else datetime.now().isoformat(timespec="seconds"),
    "passed": total_passed,
    "failed": total_failed,
    "total": total_tests,
    "status": "Pass" if total_failed == 0 else "Fail",
    "sheet_url": SHEET_URL,
    "browser_breakdown": {browser: dict(counts) for browser, counts in browser_results.items()},
}
summary_payload["report_path"] = str(write_html_report(summary_payload))
ExecutionStore().record_run(RunSummary(**summary_payload))

try:
    send_summary_email(
        passed=total_passed,
        failed=total_failed,
        total=total_tests,
        sheet_url=SHEET_URL,
        tab_name="Desktop PBR",
        browser_results=browser_results
    )
except Exception as email_error:
    print(f"Email step skipped or failed: {email_error}")

sys.exit(0 if total_tests > 0 and total_failed == 0 else 1)
