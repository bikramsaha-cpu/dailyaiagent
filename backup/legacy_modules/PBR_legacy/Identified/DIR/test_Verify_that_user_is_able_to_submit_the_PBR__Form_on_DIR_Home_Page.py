from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium","firefox"]  # Add more browsers if needed

MOBILE_NUMBER = "9643193481"  # Reuse here

def run(playwright):
    # logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"
    # try:
    #     logger = GoogleSheetLogger("Buyer Automation", tab_name)
    # except Exception as e:
    #     print(f"âš ï¸ Could not initialize GoogleSheetLogger: {e}")
    #     logger = None

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}: {step_name} completed successfully")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}.png"
                page.screenshot(path=screenshot_name)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            log_step("Navigate to DIR Home Page", lambda: (page.goto("https://dir.indiamart.com/"), page.wait_for_load_state("load")))
            log_step("Enter Product Name", lambda: (page.wait_for_selector("#t0401prodtitle", timeout=8000), page.fill("#t0401prodtitle", "mouse")))
            log_step("Enter Mobile Number", lambda: (page.wait_for_selector("#t0401_login_field", timeout=8000), page.fill("#t0401_login_field", MOBILE_NUMBER)))
            log_step("Click 'Submit' CTA", lambda: (page.wait_for_selector("#t0401_submit", timeout=8000), page.click("#t0401_submit")))
            log_step("Enter Quantity", lambda: (page.wait_for_selector("#t0401txtbx_option1", timeout=8000), page.fill("#t0401txtbx_option1", "3")))
            log_step("Click 'Next' (Step 1)", lambda: page.click("#t0401_submit"))
            log_step("Click 'Next' (Step 2)", lambda: (page.wait_for_selector("#t0401_submitdiv >> input[value='Next']", timeout=8000), page.click("#t0401_submitdiv >> input[value='Next']")))
            log_step("Click 'Submit' (Final)", lambda: (page.wait_for_selector("#t0401_submitdiv >> input[value='Submit']", timeout=8000), page.click("#t0401_submitdiv >> input[value='Submit']")))

            print(f"[Pass] Test Completion: PBR form submitted successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass", "PBR form submitted successfully", browser_name, MOBILE_NUMBER, run_time)

        except Exception as e:
            print(f"ðŸ”¥ Critical error on {browser_name}: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Overall Script Failure", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

