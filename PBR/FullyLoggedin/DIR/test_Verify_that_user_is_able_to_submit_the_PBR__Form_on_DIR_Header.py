from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
from collections import defaultdict
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium","firefox"]
MOBILE_NUMBER = "9643193481"  # reuse if needed
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"


def run(playwright):
    # sheet_logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"
    # try:
    #     sheet_logger = GoogleSheetLogger("Buyer Automation", tab_name)
    #     print("âœ… GoogleSheetLogger initialized successfully")
    # except Exception as e:
    #     print(f"âš ï¸ Could not initialize GoogleSheetLogger: {e}")
    #     sheet_logger = None

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False)
        context = browser.new_context(storage_state=session_file_path)
        # context = browser.new_context(storage_state="auth.json")
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
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            log_step("Navigate to Buyer Dashboard", lambda: page.goto("https://buyer.indiamart.com/"))
            log_step("Click 'Hi Arka' dropdown", lambda: (page.wait_for_selector("a:has-text('Hi')", timeout=10000), page.click("a:has-text('Hi')")))
            log_step("Click 'Products/Services Directory'", lambda: (
                page.wait_for_selector("a:has-text('Products/Services Directory')", timeout=8000),
                page.click("a:has-text('Products/Services Directory')"),
                page.wait_for_load_state("load")
            ))
            log_step("Click 'Get Best Price'", lambda: (page.wait_for_selector("a#pstBuy", timeout=8000), page.click("a#pstBuy")))
            log_step("Enter Product Name", lambda: (page.wait_for_selector("input#t0901prodtitle", timeout=10000), page.fill("input#t0901prodtitle", "mouse")))
            log_step("Click 'Next' (Step 1)", lambda: page.click("input#t0901_submit"))
            log_step("Enter Quantity", lambda: (page.wait_for_selector("input#t0901txtbx_option12", timeout=8000), page.fill("input#t0901txtbx_option12", "3")))

            # Uncomment this if you want wireless step back in
            '''
            log_step("Select 'Wireless' option", lambda: page.locator("div.berdio-sl.bedsnone").nth(0).click())
            '''

            log_step("Click 'Next' (Step 2)", lambda: page.click("input#t0901_submit"))
            log_step("Click 'Next' (Step 3)", lambda: page.click("input#t0901_submit"))
            log_step("Click 'Submit'", lambda: page.click("input#t0901_submit"))

            print("[Pass] Test Completion: PBR form submitted successfully")
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

