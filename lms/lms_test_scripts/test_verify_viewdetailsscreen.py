from playwright.sync_api import sync_playwright, TimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os

# Import logger_instance from root level
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from logger_instance import logger
except ImportError:
    logger = None

AUTH_FILE = "/var/log/web_tester_logs/lmslogin.json"

# Only Chromium and Firefox
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Contact Verification test on: {browser_name}")

        # Launch browser
        if browser_name == "chromium":
            browser = playwright.chromium.launch(headless=False, slow_mo=100)
        elif browser_name == "firefox":
            browser = playwright.firefox.launch(headless=False, slow_mo=100)
        else:
            raise ValueError(f"Unsupported browser: {browser_name}")

        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()
        context_data = {}

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
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            # Step 1: Go to Message Centre
            log_step("Open Message Centre", lambda: (
                page.goto("https://seller.indiamart.com/messagecentre", timeout=60000),
                page.wait_for_selector("div.lms_wrapper", timeout=60000),
                page.wait_for_selector("aside#lms_left_listing", timeout=30000),
                print("âŒ› Message Centre loaded")
            ))

            # Step 2: Get first contact's full name
            def get_first_contact():
                selector = "aside#lms_left_listing .wrd_elip.fl.fs14.fwb.maxwidth100m200"
                first_name = page.locator(selector).first.inner_text().strip()
                context_data["first_contact_name"] = first_name
                print(f"ðŸ‘¤ Contact name (left panel): {first_name}")
            log_step("Get First Contact Name", get_first_contact)

            # Step 3: Click the contact
            def click_first_contact():
                page.click("aside#lms_left_listing .row")
                page.wait_for_selector("div.lms_conv", timeout=30000)
                page.wait_for_selector("span.headertext", timeout=15000)
                print("ðŸ–±ï¸ Clicked on contact.")
            log_step("Click First Contact", click_first_contact)

            # Step 4: Verify correct contact opened
            def verify_contact_opened():
                header_name = page.inner_text("span.headertext").strip()
                if context_data["first_contact_name"].lower().startswith(header_name.lower().replace("...", "")):
                    print("âœ… Correct contact opened.")
                else:
                    raise AssertionError(
                        f"âŒ Name mismatch! Left - {context_data['first_contact_name']} | Header - {header_name}"
                    )
            log_step("Verify Contact Opened", verify_contact_opened)

            # Step 5: Click on "View More"
            log_step("Click View More", lambda: (
                page.locator("div#viewDetails").click(),
                print("ðŸ‘ï¸ Clicked 'View More'.")
            ))

            # Step 6: Wait for seller details popup
            log_step("Wait For Seller Popup", lambda: (
                page.wait_for_selector("span.fl.mxwdt75.ml5.mt2.wbbw", timeout=10000),
                print("âœ… Seller details popup appeared.")
            ))

            # Step 7: Extract Seller Name
            def extract_seller_name():
                seller_name = page.locator("span.fl.mxwdt75.ml5.mt2.wbbw").nth(0).inner_text().strip()
                context_data["seller_name"] = seller_name
                print(f"ðŸ¢ Seller Name: {seller_name}")
            log_step("Extract Seller Name", extract_seller_name)

            # Step 8: Test completion
            log_step("Test Completion", lambda: print("ðŸŽ¯ Contact verification test completed."))

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} Contact verification test completed and browser closed")

    # Print summary
    print("\nðŸ“Š Test Summary:")
    for browser, results in browser_results.items():
        print(f" - {browser}: {results['Pass']} Pass | {results['Fail']} Fail")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
