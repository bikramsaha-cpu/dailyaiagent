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
SESSION_FILE_PATH = "/var/log/web_tester_logs/buyermy_session.json"
BUYER_DASHBOARD_URL = "https://buyer.indiamart.com"
TEST_CASE_NAME = os.path.basename(__file__).replace(".py", "")
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


# ----------------------- Helper Functions ----------------------- #
def navigate_to_dashboard(page):
    """Go to Buyer Dashboard"""
    page.goto(BUYER_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    print("âœ… Navigated to Buyer Dashboard")
    time.sleep(2)


def search_product(page):
    """Search for a product and submit advanced search"""
    page.fill('xpath=//*[@id="search_string"]', "Wooden Bed")
    page.click('xpath=//*[@id="root"]/div[1]/div[2]/div[1]/div/div/div[4]/span')
    page.fill(
        'xpath=//*[@id="root"]/div[1]/div[2]/div[1]/div/div[2]/div[2]/div/div[1]/div[2]/div/div[1]/div/div[1]/input',
        "10",
    )
    with page.context.expect_page() as new_page_info:
        page.click("button.adv-search-button:text('Submit')")
    new_page = new_page_info.value
    time.sleep(2)
    new_page.close()
    page.bring_to_front()
    page.click('xpath=//*[@id="header"]/div/a')
    print("âœ… Search product flow completed successfully")


def open_past_searches(page):
    """Open past search item and return"""
    page.click('xpath=//*[@id="IM_User_History"]/div/div/div[2]/div/div/div/div/div[4]')
    with page.context.expect_page() as new_page_info:
        page.click('xpath=//*[@id="IM_User_History"]/div/div/div[2]/div/div/div/div/div[4]/div[2]/a[1]')
    product_page = new_page_info.value
    time.sleep(2)
    page.bring_to_front()
    page.click('xpath=//*[@id="header"]/div/a')
    print("âœ… Past searches flow completed successfully")


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

    # Validate session
    if not os.path.exists(SESSION_FILE_PATH):
        print(f"âŒ Session file not found: {SESSION_FILE_PATH}")
        return

    # Screenshot folder
    screenshot_dir = "screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

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
        log_step("Navigate to Buyer Dashboard", lambda: navigate_to_dashboard(page))
        log_step("Verify Navigation of Search Product Flow", lambda: search_product(page))
        log_step("Verify Navigation of Past Searches Flow", lambda: open_past_searches(page))

        # Close context
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

