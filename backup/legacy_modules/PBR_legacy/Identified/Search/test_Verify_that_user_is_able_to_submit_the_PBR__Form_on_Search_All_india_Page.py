from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
from collections import defaultdict
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

SEARCH_URL = "https://dir.indiamart.com/search.mp?ss=chairs&search_type=p&mcatid=3712&catid=93&v=4"
MOBILE_NUMBER = "9643193481"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]  # Run in both browsers

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\n🧪 Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context()
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
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            # Step 1: Navigate to Search Results Page
            log_step("Navigate to Search Results Page", lambda: page.goto(SEARCH_URL, wait_until="load", timeout=60000))
            # Scroll once after page loads
            log_step("Scroll page once after navigation", lambda: page.mouse.wheel(0, 1000))  # scroll down 1000px
            page.wait_for_timeout(1000)  # optional short wait after scroll



            def enter_mobile():
                # Escape leading numbers in ID
                page.wait_for_selector("input#\\30 102_mobile-inline-bl", timeout=10000)
                mobile_input = page.locator("input#\\30 102_mobile-inline-bl").first
                mobile_input.scroll_into_view_if_needed()
                mobile_input.fill(MOBILE_NUMBER)


            # Step 3: Click 'Submit Requirement' (first button)
            def click_submit_requirement():
                page.wait_for_selector("button#t0102_submit", timeout=10000)
                btn = page.locator("button#t0102_submit").first
                btn.scroll_into_view_if_needed()
                btn.click()
            log_step("Click 'Submit Requirement'", click_submit_requirement)

            # Step 4: Click first 'Next' button
            log_step("Click 'Next' (Step 1)", lambda: (
                page.wait_for_selector("button.submit-button", timeout=8000),
                page.locator("button.submit-button").first.click()
            ))

            # Step 5: Click second 'Next' button
            log_step("Click 'Next' (Step 2)", lambda: (
                page.wait_for_selector("input.form-btn[value='Next']", timeout=8000),
                page.locator("input.form-btn[value='Next']").first.click()
            ))

            # Step 6: Click 'Submit'
            log_step("Click 'Submit'", lambda: (
                page.wait_for_selector("input#t0901_submit", timeout=8000),
                page.locator("input#t0901_submit").first.click()
            ))

            log_step("Test Completion", lambda: print("✅ PBR form submitted successfully"))

        except Exception as e:
            print(f"🔥 Critical error on {browser_name}: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Overall Script Failure", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)
        finally:
            context.close()
            browser.close()
            print(f"✅ {browser_name} test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
