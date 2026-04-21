from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
from collections import defaultdict
import time
import sys
import os

# Add project root path for logger import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

# Configuration
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
        page = context.new_page()

        # --- Helper for logging steps ---
        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}: completed successfully")
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
            # Step 1: Navigate to MCAT Page
            log_step("Navigate to MCAT Page", lambda: page.goto(
                "https://dir.indiamart.com/impcat/pani-puri-making-machine.html",
                timeout=30000
            ))

            # Step 2: Close Popup if Present
            def close_popup():
                try:
                    page.wait_for_selector("span.close-btn", timeout=5000)
                    page.click("span.close-btn")
                    print("âœ… Popup closed successfully")
                except PlaywrightTimeoutError:
                    print("â„¹ï¸ No popup appeared, continuing...")
                except Exception as e:
                    print(f"âš ï¸ Failed to close popup: {e}")

            log_step("Close Popup (if present)", close_popup)

            # Step 3: Click 'Submit Requirement' Button
            def click_submit_requirement():
                page.wait_for_selector("button#t0102_submit", timeout=10000)
                page.locator("button#t0102_submit").first.click()
                print("âœ… Clicked on 'Submit Requirement' button")

            log_step("Click 'Submit Requirement' Button", click_submit_requirement)

            # Step 4: Select Value from Dropdown
            def select_dropdown_value():
                page.wait_for_selector("select#t0901select_name0", timeout=10000)
                dropdown = page.locator("select#t0901select_name0")
                dropdown.select_option("2000 Pcs/Hr")  # You can choose any value
                print("âœ… Selected value '2000 Pcs/Hr' from dropdown")

            log_step("Select Dropdown Value", select_dropdown_value)

            # Step 5: Click First Next Button
            def click_first_next():
                page.wait_for_selector("button.submit-button", timeout=8000)
                page.click("button.submit-button")
                print("âœ… Clicked first 'Next' button")

            log_step("Click First Next Button", click_first_next)

            # Step 6: Click Second Next Button
            def click_second_next():
                page.wait_for_selector("input.form-btn[value='Next']", timeout=8000)
                page.click("input.form-btn[value='Next']")
                print("âœ… Clicked second 'Next' button")

            log_step("Click Second Next Button", click_second_next)

            # Step 7: Click Submit Button
            def click_submit_final():
                page.wait_for_selector("input#t0901_submit", timeout=8000)
                page.click("input#t0901_submit")
                print("âœ… Clicked final 'Submit' button")

            log_step("Click Final Submit Button", click_submit_final)

            # Step 8: Test Completion
            print("[Pass] Test Completion: PBR flow executed successfully")
            if logger:
                logger.log_status(
                    f"[{browser_name}] Test Completion",
                    "Pass",
                    "PBR flow executed successfully",
                    browser_name,
                    MOBILE_NUMBER,
                    run_time
                )

            time.sleep(5)

        except PlaywrightTimeoutError as te:
            print(f"[Fail] Timeout Error: {te}")
            if logger:
                logger.log_status(f"[{browser_name}] Timeout Error", "Fail", str(te), browser_name, MOBILE_NUMBER, run_time)

        except Exception as e:
            print(f"[Fail] Unexpected Error: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Unexpected Error", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

