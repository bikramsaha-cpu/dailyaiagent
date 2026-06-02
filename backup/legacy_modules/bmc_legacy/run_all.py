import subprocess
import os
import sys
from collections import defaultdict
from datetime import datetime
from google_logger import GoogleSheetLogger
from mailer import send_summary_email

sys.stdout.reconfigure(encoding='utf-8')

# Google Sheet details
SHEET_NAME = "Buyer Automation"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1t_kEjtyZQ_xcOqJ3v5_apcyCEmi8V6wi5w1KjXNEyqg/edit?gid=1819244150#gid=1819244150"

# Base folder where scripts are stored
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Scripts and their corresponding Google Sheet tab names
scripts_to_run = [
    ("buyer_login.py", None),
    (os.path.join("testscript", "test_verify_landing_from_buyermy.py"), "BMC"),
    (os.path.join("testscript", "test_verify_open_conversation.py"), "BMC"),    (os.path.join("testscript", "test_verify_search_by_city.py"), "BMC"),
    (os.path.join("testscript", "test_verify_verifydetails.py"), "BMC"),
    (os.path.join("testscript", "test_verify_backtotop_cta.py"), "BMC"),
    (os.path.join("testscript", "test_verify_sendmessage.py"), "BMC"),
    (os.path.join("testscript", "test_verify_sendattachment.py"), "BMC"),
    (os.path.join("testscript", "test_verify_block_contact.py"), "BMC"),
    (os.path.join("testscript", "test_verify_hide_contact.py"), "BMC"),
    (os.path.join("testscript", "test_verify_giverating.py"), "BMC"),
]

# ---------------- Track browser-wise and total results ---------------- #
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
first_start_time = None
last_end_time = None
failed_cases = []
login_failed = False

# ---------------- Step 1: Run all test scripts ---------------- #
for script_rel_path, _ in scripts_to_run:
    script_path = os.path.join(BASE_DIR, script_rel_path)
    start_now = datetime.now()

    if first_start_time is None:
        first_start_time = start_now

    print(f"\n=== Running {script_path} at {start_now.strftime('%H:%M:%S')} ===")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"}
    )

    print(result.stdout)
    if result.stderr:
        print(f"❌ Error in {script_rel_path}:\n{result.stderr}")

    last_end_time = datetime.now()
    if script_rel_path == "buyer_login.py" and result.returncode != 0:
        login_failed = True
        print("Login step failed. Aborting remaining BMC scripts to avoid cascading false failures.")
        break

if login_failed:
    print("\nBMC run stopped because the login/session setup failed.")
    raise SystemExit(1)

# ---------------- Step 2: Fetch counts and failed cases ---------------- #
print(f"\n🕒 Using run time range: {first_start_time} → {last_end_time}")

total_passed = 0
total_failed = 0
total_tests = 0

unique_tabs = sorted({tab for _, tab in scripts_to_run if tab})

for tab_name in unique_tabs:
    try:
        logger = GoogleSheetLogger(SHEET_NAME, tab_name)

        # summary counts
        passed, failed, total = logger.get_summary_counts(
            start_time=first_start_time,
            end_time=last_end_time
        )
        total_passed += passed
        total_failed += failed
        total_tests += total

        # browser-wise counts
        tab_browser_counts = logger.get_browser_wise_counts(
            start_time=first_start_time,
            end_time=last_end_time
        )
        for browser, counts in tab_browser_counts.items():
            browser_results[browser]["Pass"] += counts.get("Pass", 0)
            browser_results[browser]["Fail"] += counts.get("Fail", 0)

        # failed cases
        tab_failed_cases = logger.get_failed_cases(
            start_time=first_start_time,
            end_time=last_end_time
        )
        failed_cases.extend(tab_failed_cases)

    except Exception as e:
        print(f"❌ Could not fetch summary for {tab_name}: {e}")

# ---------------- Step 3: Print nicely aligned results ---------------- #
print("\n📝 Test Summary:")
print(f"✅ Passed: {total_passed}")
print(f"❌ Failed: {total_failed}")
print(f"📊 Total:  {total_tests}")

print("\n🧪 Browser-wise Breakdown")
print(f"{'Browser':<12}{'✅ Passed':<12}{'❌ Failed':<12}{'📊 Total':<8}")
for browser, counts in browser_results.items():
    total_browser = counts['Pass'] + counts['Fail']
    print(f"{browser:<12}{counts['Pass']:<12}{counts['Fail']:<12}{total_browser:<8}")

# ---------------- Step 4: Run pdf_report.py to generate PDF ---------------- #
print("\n🔹 Generating PDF report after all tests...")
result = subprocess.run(
    [
        sys.executable,
        os.path.join(BASE_DIR, "pdf_report.py"),
        first_start_time.strftime("%Y-%m-%d %H:%M:%S"),
        last_end_time.strftime("%Y-%m-%d %H:%M:%S")
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    env={**os.environ, "PYTHONUTF8": "1"}
)

# Safely parse PDF URL from stdout
pdf_drive_url = None
for line in result.stdout.strip().splitlines():
    if "PDF uploaded to Google Drive:" in line:
        pdf_drive_url = line.split("PDF uploaded to Google Drive:")[1].strip()
        break

if not pdf_drive_url:
    print("⚠ Could not find PDF URL in pdf_report.py output")
else:
    print("✅ Latest PDF Drive URL:", pdf_drive_url)

# ---------------- Step 5: Send summary email ---------------- #
send_summary_email(
    passed=total_passed,
    failed=total_failed,
    total=total_tests,
    sheet_url=SHEET_URL,
    tab_name="Desktop BMC",
    browser_results=browser_results,
    failed_cases=failed_cases,
    pdf_drive_url=pdf_drive_url
)

raise SystemExit(0 if total_failed == 0 else 1)
