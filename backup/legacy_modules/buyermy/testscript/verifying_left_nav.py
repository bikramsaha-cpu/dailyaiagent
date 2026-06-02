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
    page.goto(BUYER_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    print("âœ… Navigated to Left Navigation")
    time.sleep(1)

def click_message(page):
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[2]')
    page.click('//*[@id="header"]/div/a')
    print("âœ… Clicked on Message")

    
def click_profile(page):
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[4]')
    page.click('//*[@id="header"]/div/a')
    print("âœ… Clicked on Profile")


def click_finance_loans(page):
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[5]/div/div/span')
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[6]/div/div/span')
    page.go_back()
    print("âœ… Finance Loans Navigate successfully")

def click_finance_creditScore(page):
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[5]/div/div/span')
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[7]')
    page.go_back()
    print("âœ… Finance Credit Score Navigate successfully")


def click_shipwithim(page):
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[5]/div/div/span')
    page.click('//*[@id="root"]/div[1]/div[1]/div/div[1]/nav/button[8]/div/div/span')
    page.wait_for_timeout(1000)
    page.go_back()




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
        log_step("Navigate to Left Nav Panel", lambda: navigate_to_dashboard(page))
        log_step("Verify Navigation of Message", lambda: click_message(page))
        log_step("Verify Navigation of Profile", lambda: click_profile(page))
        log_step("Verify Navigation of Finance Loans", lambda: click_finance_loans(page))
        log_step("Verify Navigation of Finance Credit Score", lambda: click_finance_creditScore(page))
        log_step("Verify Navigation of Ship With IM", lambda: click_shipwithim(page))




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

