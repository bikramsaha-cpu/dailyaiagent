from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
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
            # Step 1: Navigate to BuyerMy Home Page
            log_step("Navigate to BuyerMy Dashboard", lambda: page.goto(
                "https://buyer.indiamart.com/", wait_until="domcontentloaded"
            ))

            # Step 2: Click 4th 'Get Quotes' button
            def click_get_quotes():
                page.wait_for_selector("input.btn.btn-primary-dashboard", timeout=10000)
                page.locator("input.btn.btn-primary-dashboard").nth(3).click()  # 0-indexed, so 4th = nth(3)
                print("âœ… Clicked 4th 'Get Quotes' button")

            log_step("Click 4th Get Quotes", click_get_quotes)

            # # Step 3: Select any value from dropdown
            # def select_dropdown_value():
            #     page.wait_for_selector("select#t0901select_name0", timeout=10000)
            #     page.locator("select#t0901select_name0").select_option("2000 Pcs/Hr")  # can randomize
            #     print("âœ… Selected value '2000 Pcs/Hr' from dropdown")

            # log_step("Select Dropdown Value", select_dropdown_value)

            # Step 4: Click First Next button
            log_step("Click First Next", lambda: (
                page.wait_for_selector("button.submit-button", timeout=8000),
                page.click("button.submit-button")
            ))

            # Step 5: Click Second Next button
            log_step("Click Second Next", lambda: (
                page.wait_for_selector("input.form-btn[value='Next']", timeout=8000),
                page.click("input.form-btn[value='Next']")
            ))

            # Step 6: Click Final Submit button
            log_step("Click Final Submit", lambda: (
                page.wait_for_selector("input#t0901_submit", timeout=8000),
                page.click("input#t0901_submit")
            ))

            # Step 7: Verify Thank You message
            try:
                page.wait_for_selector("text=Thank You", timeout=8000)
                print("[Pass] Verify Submission: Thank You confirmation detected")
                if logger:
                    logger.log_status(f"[{browser_name}] Verify Submission", "Pass",
                                      "Thank You confirmation detected", browser_name, MOBILE_NUMBER, run_time)
            except PlaywrightTimeoutError:
                print("[Fail] Verify Submission: No Thank You text detected")
                if logger:
                    logger.log_status(f"[{browser_name}] Verify Submission", "Fail",
                                      "No Thank You text detected", browser_name, MOBILE_NUMBER, run_time)

            print("[Pass] Test Completion: PBR flow executed successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass",
                                  "PBR flow executed successfully", browser_name, MOBILE_NUMBER, run_time)

            page.wait_for_timeout(3000)

        except Exception as e:
            print(f"[Fail] Test Execution: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Test Execution", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

