from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]  # Add other browsers if needed
MOBILE_NUMBER = "9643193481"  # Example mobile number
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"

def run(playwright):
    logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        # context = browser.new_context(storage_state="auth.json")
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
            log_step("Navigate to BuyerMy Dashboard", lambda: (
                page.goto("https://buyer.indiamart.com/"),
                page.wait_for_selector("a:has-text('Hi')", timeout=8000)
            ))

            log_step("Click 'Hi Arka' dropdown", lambda: page.click("a:has-text('Hi')"))

            log_step("Click 'My Orders'", lambda: (
                page.wait_for_selector("a:has-text('My Orders')", timeout=8000),
                page.click("a:has-text('My Orders')")
            ))

            log_step("Open Recommended Categories", lambda: (
                page.wait_for_selector("a#recommendedCategories", timeout=8000),
                page.click("a#recommendedCategories")
            ))

            log_step("Click 'Get Quotes'", lambda: (
                page.wait_for_selector("a.btnn", timeout=8000),
                page.click("a.btnn")
            ))

            log_step("Enter Quantity", lambda: (
                page.wait_for_selector("input#ttxtbx_option1", timeout=8000),
                page.fill("input#ttxtbx_option1", "3")
            ))

            log_step("Click 'Next' (Step 1)", lambda: (
                page.wait_for_selector("button.submit-button", timeout=8000),
                page.click("button.submit-button")
            ))

            log_step("Click 'Next' (Step 2)", lambda: (
                page.wait_for_selector("input.form-btn[value='Next']", timeout=8000),
                page.click("input.form-btn[value='Next']")
            ))

            log_step("Click 'Submit'", lambda: (
                page.wait_for_selector("input#t0901_submit", timeout=8000),
                page.click("input#t0901_submit")
            ))

            log_step("Verify Thank You confirmation", lambda: page.wait_for_selector("text=Thank You", timeout=8000))

            print("[Pass] Test Completion: PBR form submitted successfully")

            time.sleep(5)

        except PlaywrightTimeoutError as te:
            print(f"[Fail] Timeout occurred: {te}")
        except Exception as e:
            print(f"[Fail] Unexpected error: {e}")
        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

