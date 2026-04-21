from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import build_page, empty_browser_results, make_log_step, open_first_contact, open_message_centre

session_file_path = "/var/log/web_tester_logs/bmclogin.json"
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
ATTACHMENT_PATH = "C:/Users/Lenovo/Pictures/Screenshots/Screenshot (28).png"
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning send attachment automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
        page = build_page(context.new_page(), test_name=test_case_name)
        base_log_step = make_log_step(
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=MOBILE_NUMBER,
        )

        def log_step(step_name, func):
            return base_log_step(f"{test_case_name} -> {step_name}", func)

        log_step("Open Message Centre", lambda: open_message_centre(page))

        def step_open_first_contact():
            contact_name = open_first_contact(page, timeout=15000)
            print(f"Opening first contact: {contact_name}")
            page.wait_for_selector("#massage-text, textarea, [contenteditable='true']", timeout=10000)
            time.sleep(2)

        log_step("Open First Contact", step_open_first_contact)

        log_step(
            "Click Attachment Button",
            lambda: page.click(
                "#sendbox-icn-li, [id*='attch'], [aria-label*='Attach']",
                intent="open attachment picker in buyer message centre",
                text="Attach",
                keywords=["attach", "attachment", "message", "buyer"],
            ),
        )

        def upload_file():
            page.locator("input[type='file']").first.set_input_files(ATTACHMENT_PATH)
            time.sleep(2)

        log_step("Upload File", upload_file)

        log_step(
            "Send Attachment",
            lambda: page.click(
                "div#msg-attch-send, button:has-text('Send'), [id*='attch-send']",
                intent="send uploaded attachment in buyer message centre",
                text="Send",
                role="button",
                role_name="Send",
                keywords=["send", "attachment", "message"],
            ),
        )

        def verify_attachment():
            page.wait_for_selector(".inner_msg_div pre, .inner_msg_div, [class*='attachment']", timeout=10000)
            if page.locator(".inner_msg_div pre, .inner_msg_div, [class*='attachment']").count() == 0:
                raise Exception("Attachment verification failed: no sent content found")

        log_step("Verify Attachment Sent", verify_attachment)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
