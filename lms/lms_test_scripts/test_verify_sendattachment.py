from playwright.sync_api import sync_playwright, TimeoutError
from collections import defaultdict
from datetime import datetime
import time
import sys
import os

# Import logger_instance from root level (if available)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from logger_instance import logger
except ImportError:
    logger = None

AUTH_FILE = "/var/log/web_tester_logs/lmslogin.json"
CONTACT_NAME = "arka"
BROWSERS = ["chromium", "firefox"]   # Only Chromium & Firefox
MOBILE_NUMBER = "9643193481"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Seller MC Attachment test on: {browser_name}")
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
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            # Step 1: Open Seller MC
            log_step("Open Seller MC", lambda: (
                page.goto("https://seller.indiamart.com/messagecentre", timeout=60000),
                page.wait_for_selector("input#searchauto", timeout=30000)
            ))

            # Step 2: Search for contact
            def search_contact():
                search_box = page.locator("input#searchauto")
                search_box.click()
                search_box.fill(CONTACT_NAME)
                time.sleep(2)
            log_step("Search Contact", search_contact)

            # Step 3: Click first contact from search results
            def click_contact():
                first_contact = page.locator("#splitViewContactList .row").first
                global contact_text
                contact_text = first_contact.inner_text().strip()
                first_contact.click()
                page.wait_for_selector("span.headertext", timeout=15000)
                print(f"ðŸ“¨ Opened conversation with: {contact_text}")
            log_step("Click First Contact", click_contact)

            # Step 4: Click on attachments icon
            log_step("Click Attachment Icon", lambda: page.locator("div#attachment").click())

            # Step 5: Select the first attachment
            def select_attachment():
                page.wait_for_selector("div.drive_bx", timeout=15000)
                attachment = page.locator("div.drive_bx").first
                attachment.scroll_into_view_if_needed()
                attachment.click()
            log_step("Select First Attachment", select_attachment)

            # Step 6: Click send button
            def send_attachment():
                send_button = page.locator("button", has_text="Send").first
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        send_button.wait_for(state="visible", timeout=3000)
                        send_button.click()
                        print("ðŸ“¤ Attachment sent")
                        break
                    except TimeoutError:
                        print(f"âš  Send button not ready, retry {attempt + 1}/{max_retries}")
                        time.sleep(1)
                else:
                    raise TimeoutError("Send button not clickable after retries")
            log_step("Send Attachment", send_attachment)

            # Step 7: Verify attachment sent in conversation
            def verify_attachment():
                # Adjusted locator for right side (sent) messages
                last_msg = page.locator("div.right_side_msg").last
                last_msg.wait_for(state="visible", timeout=10000)
                print("âœ… Attachment verified in conversation.")
            log_step("Verify Attachment Sent", verify_attachment)

            # Step 8: Test Completion
            log_step("Test Completion", lambda: print("ðŸŽ¯ Seller MC Attachment test completed."))

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} Seller MC test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
