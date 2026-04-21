from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import sys
import os

# Import logger_instance from root level
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger

AUTH_FILE = "/var/log/web_tester_logs/lmslogin.json"
BROWSERS = ["chromium", "firefox"]   # Only Chromium & Firefox
MOBILE_NUMBER = "9643193481"
SELLER_MC_URL = "https://seller.indiamart.com/messagecentre"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Seller Message Centre test on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name} âœ…")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                # continue instead of stopping
                return

        # Step 1: Go to Seller Message Centre
        log_step("Open Seller Message Centre", lambda: page.goto(SELLER_MC_URL, wait_until="domcontentloaded", timeout=60000))

        # Step 2: Wait for left panel to load
        log_step("Wait for Left Panel", lambda: (
            page.wait_for_selector("div.lms_wrapper", timeout=60000),
            page.wait_for_selector("aside#lms_left_listing", timeout=30000)
        ))

        # Step 3: Get contact name from left panel
        def get_left_contact_name():
            contact_name_selector = "aside#lms_left_listing .wrd_elip.fl.fs14.fwb.maxwidth100m200"
            global left_contact_name
            left_contact_name = page.locator(contact_name_selector).first.inner_text().strip()
            print(f"ðŸ‘¤ Contact Name (left): {left_contact_name}")
        log_step("Get Left Contact Name", get_left_contact_name)

        # Step 4: Click on first contact row
        log_step("Click First Contact", lambda: page.click("aside#lms_left_listing .row"))

        # Step 5: Wait for conversation pane
        log_step("Wait for Conversation Pane", lambda: (
            page.wait_for_selector("div.lms_conv", timeout=30000),
            page.wait_for_selector("span.headertext", timeout=15000)
        ))

        # Step 6: Extract right header name
        def get_right_contact_name():
            global right_truncated_name
            right_truncated_name = page.inner_text("span.headertext").strip()
            print(f"ðŸ’¬ Contact Name (right - header): {right_truncated_name}")
        log_step("Get Right Contact Name", get_right_contact_name)

        # Step 7: Verify name consistency
        def verify_names():
            if left_contact_name.lower().startswith(right_truncated_name.lower().replace("...", "")):
                print("âœ… Correct conversation opened (name matches with truncation considered).")
            else:
                raise AssertionError(f"âŒ Name mismatch! Expected: {left_contact_name} | Got: {right_truncated_name}")
        log_step("Verify Name Consistency", verify_names)

        # Step 8: Test Completion
        log_step("Test Completion", lambda: print("ðŸŽ¯ Seller Message Centre test completed."))

        # Close
        context.close()
        browser.close()
        print(f"âœ… {browser_name} Seller MC test completed and browser closed")

    # --- Final Summary ---
    print("\nðŸ“Š Final Test Summary:")
    for browser, results in browser_results.items():
        print(f"  {browser}: âœ… {results['Pass']} passed | âŒ {results['Fail']} failed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
