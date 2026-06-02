from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]  # Add more if needed

MOBILE_NUMBER = "9643193481"  # You can update if needed
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"

def run(playwright):
    logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_url = "https://docs.google.com/spreadsheets/d/1t_kEjtyZQ_xcOqJ3v5_apcyCEmi8V6wi5w1KjXNEyqg/edit?gid=415313835#gid=415313835"
    tab_name = "PBR"
    try:
        # logger = GoogleSheetLogger("Buyer Automation", tab_name)  # Uncomment if you have GoogleSheetLogger
        pass
    except Exception as e:
        print(f"âš ï¸ Could not initialize GoogleSheetLogger: {e}")
        logger = None

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
        # context = browser.new_context(storage_state="auth.json")  # Requires logged-in storage
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}.png"
                page.screenshot(path=screenshot_name)
                print(f"[Fail] {step_name} â†’ {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            log_step("Navigate to Buyer Homepage", lambda: page.goto("https://buyer.indiamart.com/"))

            log_step("Click 'Hi User' dropdown", lambda: (
                page.wait_for_selector("a:has-text('Hi')", timeout=8000),
                page.click("a:has-text('Hi')")
            ))

            log_step("Click 'My Orders'", lambda: (
                page.wait_for_selector("a:has-text('My Orders')", timeout=8000),
                page.click("a:has-text('My Orders')")
            ))

            log_step("Click '+ Post a New Requirement'", lambda: (
                page.wait_for_selector("div:text('+ Post a New Requirement')", timeout=8000),
                page.click("div:text('+ Post a New Requirement')")
            ))

            log_step("Enter product name 'chairs'", lambda: (
                page.wait_for_selector("input#prodtitle0901", timeout=8000),
                page.fill("input#prodtitle0901", "chairs")
            ))

            log_step("Enter requirement details 'Urgent Need'", lambda: (
                page.wait_for_selector("textarea.slbox.ber-txt", timeout=8000),
                page.fill("textarea.slbox.ber-txt", "Urgent Need")
            ))

            log_step("Click 'Next' CTA", lambda: (
                page.wait_for_selector("input.form-btn[value='Next']", timeout=8000),
                page.click("input.form-btn[value='Next']")
            ))

            log_step("Click 'Submit' CTA", lambda: (
                page.wait_for_selector("input#t0901_submit", timeout=8000),
                page.click("input#t0901_submit")
            ))

            print("â³ Waiting 10 seconds to observe...")
            time.sleep(10)

            print(f"[Pass] Test Completion: PBR form submitted successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass", "PBR form submitted successfully", browser_name, MOBILE_NUMBER, run_time)

        except PlaywrightTimeoutError as te:
            print(f"âŒ TimeoutError: {te}")
            if logger:
                logger.log_status(f"[{browser_name}] TimeoutError", "Fail", str(te), browser_name, MOBILE_NUMBER, run_time)
        except Exception as e:
            print(f"âŒ Unexpected Error: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Unexpected Error", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)
        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

