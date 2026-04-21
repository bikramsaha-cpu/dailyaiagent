from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

# --- Configuration ---
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
TAB_NAME = "PBR"
SEARCH_URL = (
    "https://dir.indiamart.com/search.mp?ss=chairs&search_type=p&mcatid=3712&catid=93&v=4&crs=cs-glb&cq=kolkata"
    "&cq_src=city-search_2&tags=res:RC3|ktp:N0|mtp:G|wc:1|lcf:3|cq:kolkata|qr_nm:gl-gd|cs:15041|com-cf:nl|ptrs:na"
    "|mc:3712|cat:93|qry_typ:P|lang:en|rtn=1-1-0-0-1-6-1|tyr=1|qrd=250730|mrd=250730|prdt=250730|msf=ms|pfen=1|gli=G0I0"
)
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
                print(f"[Pass] {step_name}: completed successfully")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_').replace('\'','')}.png"
                page.screenshot(path=screenshot_name)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            # Step 1: Navigate to Search Results page
            log_step("Navigate to Search Results page", lambda: page.goto(SEARCH_URL, wait_until="load", timeout=60000))

            # Step 2: Click first 'Submit Requirement' button (<button id="t0102_submit">)
            def click_submit_req_button():
                page.wait_for_selector("button#t0102_submit", timeout=10000)
                page.locator("button#t0102_submit").first.scroll_into_view_if_needed()
                page.locator("button#t0102_submit").first.click()
                print("âœ… Clicked first 'Submit Requirement' button")

            log_step("Click first 'Submit Requirement' button", click_submit_req_button)

            # Step 3: Enter Quantity
            log_step("Enter Quantity", lambda: (
                page.wait_for_selector("input#ttxtbx_option1", timeout=8000),
                page.fill("input#ttxtbx_option1", "2")
            ))

            # # Step 4: Select dropdown value (random option)
            # def select_random_dropdown():
            #     page.wait_for_selector("select#t0901select_name0", timeout=8000)
            #     options = page.locator("select#t0901select_name0 option").all_text_contents()
            #     options = [o for o in options if o.strip() != "Select a Value"]
            #     selected = random.choice(options)
            #     page.locator("select#t0901select_name0").select_option(selected)
            #     print(f"âœ… Selected dropdown value: {selected}")

            # log_step("Select Dropdown Value", select_random_dropdown)

            # Step 5: Click first 'Next' button
            log_step("Click first 'Next' button", lambda: (
                page.wait_for_selector("button.submit-button", timeout=8000),
                page.click("button.submit-button")
            ))

            # Step 6: Click second 'Next' button
            log_step("Click second 'Next' button", lambda: (
                page.wait_for_selector("input.form-btn[type='submit']", timeout=8000),
                page.click("input.form-btn[type='submit']")
            ))

            # Step 7: Click final 'Submit' button
            log_step("Click 'Submit' button", lambda: (
                page.wait_for_selector("input#t0901_submit", timeout=8000),
                page.click("input#t0901_submit")
            ))

            # Step 8: Verify 'Thank You' message
            try:
                page.wait_for_selector("text=Thank You", timeout=8000)
                print("[Pass] Submission verified: 'Thank You' detected")
                if logger:
                    logger.log_status(f"[{browser_name}] Verify Submission", "Pass",
                                      "Thank You confirmation detected", browser_name, MOBILE_NUMBER, run_time)
            except PlaywrightTimeoutError:
                print("[Fail] Submission verification failed: 'Thank You' not found")
                if logger:
                    logger.log_status(f"[{browser_name}] Verify Submission", "Fail",
                                      "No Thank You text detected", browser_name, MOBILE_NUMBER, run_time)

            page.wait_for_timeout(3000)

        except PlaywrightTimeoutError as te:
            print(f"[Fail] TimeoutError during execution: {te}")
        except Exception as e:
            print(f"[Fail] Unexpected Error during execution: {e}")
        finally:
            print(f"âœ… {browser_name} test completed and browser closed")
            context.close()
            browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

