from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import random
import string
import sys
import os
import time

# Import logger_instance from root level (if available)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from logger_instance import logger
except ImportError:
    logger = None

AUTH_FILE = "/var/log/web_tester_logs/lmslogin.json"
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"   # Will run on Chromium and Firefox
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def generate_random_note(length=20):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Seller MC â†’ Add & Delete Note test on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(
            headless=False,  # âœ… Run fully in background
            slow_mo=0
        )
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
            # Step 1: Go to Message Centre
            log_step("Open Seller MC", lambda: (
                page.goto("https://seller.indiamart.com/messagecentre", timeout=60000),
                page.wait_for_selector("div.lms_wrapper", timeout=60000)
            ))

            # Step 2: Get first contact
            def get_first_contact():
                selector = "aside#lms_left_listing .wrd_elip.fl.fs14.fwb.maxwidth100m200"
                global first_contact_name
                first_contact_name = page.locator(selector).first.inner_text().strip()
                print(f"ðŸ‘¤ Contact name (left): {first_contact_name}")
            log_step("Get First Contact Name", get_first_contact)

            # Step 3: Click contact row
            def click_contact():
                page.click("aside#lms_left_listing .row")
                page.wait_for_selector("div.lms_conv", timeout=30000)
                page.wait_for_selector("span.headertext", timeout=15000)
            log_step("Click Contact", click_contact)

            # Step 4: Verify contact
            def verify_contact():
                header_name = page.inner_text("span.headertext").strip()
                if not first_contact_name.lower().startswith(header_name.lower().replace("...", "")):
                    raise AssertionError(f"âŒ Mismatch: Left={first_contact_name} | Header={header_name}")
                print("âœ… Correct contact opened. Proceeding to add note.")
            log_step("Verify Contact", verify_contact)

            # Step 5: Click Note trigger (new UI)
            def click_note_trigger():
                page.wait_for_selector("div.w40p.bgF0F0F0.h40", state="visible", timeout=20000)
                page.locator("div.w40p.bgF0F0F0.h40").click()
                page.wait_for_selector("div.fwb.txt_lft.mb10.fs15", timeout=10000)  # "User Defined Labels"
                print("ðŸ“ Notes popup opened.")
            log_step("Click Note Trigger", click_note_trigger)

            # Step 6: Add a new note
            def add_note():
                global note_text
                note_text = generate_random_note()
                page.fill("textarea#messages-notes-txt", note_text)
                page.locator("button.small_btn_filled_std", has_text="Save Note").click()
                print(f"ðŸ“ Note saved: {note_text}")
                page.wait_for_selector(f"text={note_text}", timeout=10000)
            log_step("Add Note", add_note)

            # Step 7: Delete latest note
            def delete_note():
                # Open right-side menu
                page.locator("div.por[style*='right: 10px']").first.click()
                # Click delete
                page.locator("div[title='Delete Note']").click()
                # Confirm delete
                page.locator("button.small_btn_filled_std", has_text="Continue").click()
                print("ðŸ—‘ï¸ Note deleted successfully.")
            log_step("Delete Note", delete_note)

            # Step 8: Completion
            log_step("Test Completion", lambda: print("ðŸŽ¯ Add & Delete Note flow completed."))

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} Seller MC â†’ Add & Delete Note test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

