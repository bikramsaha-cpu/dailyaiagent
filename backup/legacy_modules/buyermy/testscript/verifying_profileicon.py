from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import os
import sys
import time

# âœ… Path setup for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from google_logger import GoogleSheetLogger  # Custom Google Sheet logger

# ----------------------- Configuration ----------------------- #
MOBILE_NUMBER = "9643193481"
BROWSERS = ["chromium", "firefox"]
SESSION_FILE_PATH = "/var/log/web_tester_logs/buyermylogin.json"
BUYER_DASHBOARD_URL = "https://buyer.indiamart.com"
TEST_CASE_NAME = os.path.basename(__file__).replace(".py", "")
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

# ----------------------- Helper Functions ----------------------- #
def navigate_to_dashboard(page):
    """Go to Buyer Dashboard"""
    page.goto(BUYER_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    print("âœ… Navigated to Buyer Dashboard")
    time.sleep(2)


def click_profile_icon(page):
    """Click on Profile Icon"""
    page.click('xpath=//*[@id="lshead"]/a/span')
    print("âœ… Clicked on Profile Icon")


def click_home_icon(page):
    """Click on Home Icon"""
    page.click('xpath=//*[@id="sntid"]/a[1]')
    print("âœ… Clicked on Home Icon")


def post_your_requirement(page, context):
    """Post Your Requirement flow"""
    page.click('xpath=//*[@id="lshead"]/a/span')
    page.click('xpath=//*[@id="sntid"]/a[2]')
    page.fill('xpath=//*[@id="t0601prodtitle"]', "laptop bags")
    page.click('xpath=//*[@id="t0601_submit"]')

    # Open Manage Your Requirement in new tab
    with context.expect_page() as new_tab_event:
        page.get_by_role("link", name="Manage Your Requirement").click()
    new_tab = new_tab_event.value
    time.sleep(2)
    new_tab.close()
    page.bring_to_front()
    page.click('xpath=//*[@id="t0601_cls"]')
    page.click('xpath=//*[@id="header"]/div/a')
    print("âœ… Post Your Requirement flow completed successfully")


def featured_categories_flow(page):
    """Featured Categories flow"""
    page.click('xpath=//*[@id="lshead"]/a/span')
    page.click('xpath=//*[@id="sntid"]/a[2]')
    page.click('xpath=//*[@id="rec_item_mainnew_mcat"]')
    page.click('xpath=//*[@id="rec_itemnew_mcat"]/li[1]/div[2]/div/a[2]')
    page.click('//button[@type="submit" and contains(@class,"submit-button")]')
    page.click('//input[@class="form-btn" and @type="submit"]')
    page.click('xpath=//*[@id="t0901_submit"]')
    page.click('//div[@id="t0901_cls" and contains(@class,"ber-cls-rec") and text()="X"]')
    page.click('xpath=//*[@id="header"]/div/a')
    print("âœ… Featured Categories flow completed successfully")

# You can similarly add more flows here for:
# Verified Business Buyer, Product Directory, My Orders, Business Loan, Settings, Ship With Indiamart, Download App, etc.


# ----------------------- Main Run Function ----------------------- #
def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logger = None
    tab_name = "Buyermy"

    # Initialize Google Sheet logger
    try:
        sheet_logger = GoogleSheetLogger("Buyer Automation", tab_name)
        print("âœ… GoogleSheetLogger initialized successfully")
    except Exception as e:
        print(f"âš ï¸ Google Sheet logging disabled: {e}")

    # Validate session file
    if not os.path.exists(SESSION_FILE_PATH):
        print(f"âŒ Session file not found: {SESSION_FILE_PATH}")
        return

    # Screenshot folder
    screenshot_dir = "/var/log/web_tester_logs" 

    # ----------------------- Test Execution per Browser ----------------------- #
    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Buyer Dashboard automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=200)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
        page = context.new_page()

        def log_step(step_name, func):
            """Unified logging for each step"""
            full_title = step_name
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}")
                if sheet_logger:
                    sheet_logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                try:
                    screenshot_path = os.path.join(
                        screenshot_dir, f"{browser_name}_{step_name.replace(' ', '_')}.png"
                    )
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[Fail] {step_name}: {error_msg} (Screenshot saved: {screenshot_path})")
                except Exception as se:
                    print(f"[Fail] {step_name}: {error_msg} (Screenshot failed: {se})")

                if sheet_logger:
                    sheet_logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        # ----------------------- Test Steps ----------------------- #
        log_step("Navigate to Profile Section", lambda: navigate_to_dashboard(page))
        log_step("Verify Navigation of Profile", lambda: click_profile_icon(page))
        log_step("Verify Navigation of Home from profile", lambda: click_home_icon(page))
        log_step("Verify Navigation of Post Your Requirement Flow", lambda: post_your_requirement(page, context))
       # log_step("Verify Navigation of Featured Categories Flow", lambda: featured_categories_flow(page))
        context.close()
        browser.close()
        print(f"âœ… {browser_name} test completed and browser closed")

    # ----------------------- Final Summary ----------------------- #
    print("\nðŸŽ¯ Final Results Summary:")
    for browser, results in browser_results.items():
        print(f"{browser}: âœ… {results['Pass']} Passed | âŒ {results['Fail']} Failed")


# ----------------------- Entry Point ----------------------- #
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

