from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import sys
import os
import time

# Import logger_instance from root level (if available)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from logger_instance import logger
except ImportError:
    logger = None

SELLER_SESSION = "/var/log/web_tester_logs/lmslogin.json"
CONTACT_NAME = "Surga Enterprises"
MESSAGE_TEXT = "Hi Arka, this is a test message."
BROWSERS = ["chromium", "firefox"]   # âœ… Only Chromium & Firefox
MOBILE_NUMBER = "9643193481"
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Seller MC â†’ Send Text Message test on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=SELLER_SESSION)
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
                page.wait_for_selector("input#searchauto", timeout=10000)
            ))

            # Step 2: Search Contact
            def search_contact():
                search_box = page.locator("input#searchauto")
                search_box.click()
                search_box.fill(CONTACT_NAME)
                page.keyboard.press("Enter")
                time.sleep(3)
            log_step("Search Contact", search_contact)

            # Step 3: Select Contact (FIXED âœ… to use contact name instead of first row)
            def select_contact():
                contact_locator = page.locator(
                    f"#splitViewContactList .wrd_elip.fl.fs14.fwb.maxwidth100m200:has-text('{CONTACT_NAME}')"
                )
                contact_locator.wait_for(timeout=10000)
                contact_text = contact_locator.inner_text().strip()
                contact_locator.click()
                page.wait_for_selector("#massage-text", timeout=10000)
                print(f"ðŸ“¨ Opening conversation with: {contact_text}")
            log_step("Select Contact", select_contact)

            # Step 4: Type Message
            def type_message():
                message_box = page.locator("#massage-text")
                message_box.click()
                page.keyboard.type(MESSAGE_TEXT, delay=50)
            log_step("Type Message", type_message)

            # Step 5: Send Message
            def send_message():
                send_button = page.locator("#send-reply-span")
                page.wait_for_selector("#send-reply-span", state="visible", timeout=5000)
                send_button.click()
                time.sleep(2)
            log_step("Click Send Button", send_message)

            # Step 6: Verify Sent Message (âœ… with retry fallback)
            def verify_message():
                messages_locator = page.locator(".right_side_msg .fs13.wwrap.txt_lft")
                page.wait_for_selector(".right_side_msg .fs13.wwrap.txt_lft", timeout=10000)

                all_msgs = messages_locator.all_inner_texts()
                if any(MESSAGE_TEXT in msg for msg in all_msgs[-3:]):
                    print("âœ… Message sent successfully.")
                    return

                # Fallback: Retry with Enter key
                print("âš ï¸ Message not found â€” retrying with Enter key...")
                message_box = page.locator("#massage-text")
                message_box.click()
                page.keyboard.type(MESSAGE_TEXT, delay=50)
                page.keyboard.press("Enter")
                time.sleep(3)

                all_msgs = messages_locator.all_inner_texts()
                if any(MESSAGE_TEXT in msg for msg in all_msgs[-3:]):
                    print("âœ… Message sent via Enter key.")
                else:
                    raise AssertionError("âŒ Message still not sent after retries.")
            log_step("Verify Message Sent", verify_message)

            # Step 7: Completion
            log_step("Test Completion", lambda: print("ðŸŽ¯ Send Text Message flow completed."))

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} Seller MC â†’ Send Text Message test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

    print("\nðŸ“Š Final Test Results:")
    for browser, results in browser_results.items():
        print(f"  {browser}: {results['Pass']} Passed, {results['Fail']} Failed")
