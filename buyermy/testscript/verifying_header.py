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


def hover_and_click(page, main_xpath, sub_xpath, step_desc):
    """Hover over Help Center and click submenu link"""
    page.wait_for_selector(main_xpath, timeout=10000)
    page.hover(main_xpath)
    time.sleep(1)
    page.wait_for_selector(sub_xpath, timeout=10000)
    page.click(sub_xpath)
    time.sleep(2)
    page.go_back()
    print(f"âœ… {step_desc} completed successfully")


def chat_with_us(page):
    """Open and close chat window"""
    page.hover('//*[@id="help-center"]/a')
    page.wait_for_selector('//*[@id="chatwithus"]', timeout=10000)
    page.click('//*[@id="chatwithus"]')
    time.sleep(2)
    page.wait_for_selector('//span[@id="cht_cross"]', timeout=10000)
    page.click('//span[@id="cht_cross"]')
    time.sleep(2)
    print("âœ… Chat with us opened and closed successfully")


def click_logo(page):
    """Click on Indiamart logo"""
    page.wait_for_selector('//*[@id="header"]/div/a', timeout=10000)
    page.click('//*[@id="header"]/div/a')
    time.sleep(2)
    print("âœ… Indiamart logo clicked successfully")


def message(page):
    """Validate Header icons"""
    page.click("//*[@id='header']/div/a")
    page.click('a[id="messageWid"]')
    page.wait_for_timeout(2000)
    page.go_back()

def export(page):
    page.click("//*[@id='header']/div/a")
    page.click('a.h_ic42.vepticn')
    page.wait_for_timeout(2000)
    page.go_back()

def seller(page):
    page.click("//*[@id='header']/div/a")
    page.click('//*[@id="sellTool"]')
    print("âœ… Header section flow completed successfully")

    


# ----------------------- Main Runner Function ----------------------- #
def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logger = None
    tab_name = "Buyermy"

    # âœ… Initialize Google Sheet Logger
    try:
        sheet_logger = GoogleSheetLogger("Buyer Automation", tab_name)
        print("âœ… GoogleSheetLogger initialized successfully")
    except Exception as e:
        print(f"âš ï¸ Google Sheet logging disabled: {e}")

    # âœ… Validate session file
    if not os.path.exists(SESSION_FILE_PATH):
        print(f"âŒ Session file not found: {SESSION_FILE_PATH}")
        print("ðŸ‘‰ Please run 'save_session.py' to create it.")
        return

    # âœ… Screenshot directory
    screenshot_dir = "/var/log/web_tester_logs" 

    # ----------------------- Run Tests for Each Browser ----------------------- #
    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Help Center & Header Automation on: {browser_name}")
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
        log_step("Navigate to Header Scetion", lambda: navigate_to_dashboard(page))
        log_step("Verify Navigation of Click For Selling under Help", lambda: hover_and_click(page, '//*[@id="help-center"]/a', '//*[@id="help-center"]/div/a[2]/b', "Click For Selling"))
        log_step("Verify Navigation of Click For Buyer under Help", lambda: hover_and_click(page, '//*[@id="help-center"]/a', '//*[@id="help-center"]/div/a[1]', "Click For Buyer"))
        log_step("Verify Navigation of Click Share Your Feedback under Help", lambda: hover_and_click(page, '//*[@id="help-center"]/a', '//*[@id="help-center"]/div/a[3]', "Click Share Your Feedback"))
        log_step("Verify Navigation of Click Raise Your Complaints under Help", lambda: hover_and_click(page, '//*[@id="help-center"]/a', '//*[@id="help-center"]/div/a[4]', "Click Raise Your Complaints"))
        log_step("Verify Navigation of Click Seller Academy under Help", lambda: hover_and_click(page, '//*[@id="help-center"]/a', '//*[@id="help-center"]/div/a[5]', "Click Seller Academy"))
        log_step("Verify Navigation of Chat With Us under Help", lambda: chat_with_us(page))
        log_step("Verify Navigation of message ", lambda: message(page))
        log_step("Verify Navigation of export", lambda: export(page))
        log_step("Verify Navigation of seller", lambda: seller(page))

        # âœ… Close browser context
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

