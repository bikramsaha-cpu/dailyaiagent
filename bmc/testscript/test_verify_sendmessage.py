from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import build_page, empty_browser_results, make_log_step, open_first_contact

session_file_path = "/var/log/web_tester_logs/bmclogin.json"
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
MESSAGE_CENTRE_URL = "https://buyer.indiamart.com/enquiry/messagecentre/"
MESSAGE_TEXT = "how are you sirr"

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning Send Message automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
        page = build_page(context.new_page(), test_name="test_verify_sendmessage")
        log_step = make_log_step(
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=MOBILE_NUMBER,
        )

        log_step("Open Message Centre", lambda: page.goto(MESSAGE_CENTRE_URL, wait_until="domcontentloaded", timeout=60000))

        contact_name = {"value": None}

        def step_open_first_contact():
            contact_name["value"] = open_first_contact(page, timeout=15000)
            print(f"Opening chat with: {contact_name['value']}")
            time.sleep(2)

        log_step("Open First Contact", step_open_first_contact)

        def send_message():
            page.wait_for_selector("#massage-text, textarea, [contenteditable='true']", timeout=10000)
            input_box = page.locator("#massage-text, textarea, [contenteditable='true']").first
            input_box.fill(MESSAGE_TEXT)
            page.click(
                "#send_button, button:has-text('Send'), [type='submit']",
                intent="send message in buyer message centre",
                text="Send",
                role="button",
                role_name="Send",
                keywords=["send", "message", "chat", "buyer"],
            )
            time.sleep(2)

        log_step("Send Message", send_message)

        def verify_message():
            page.wait_for_selector("div.inner_msg_div > div > div > pre, pre, .inner_msg_div", timeout=8000)
            displayed_msg = page.locator("div.inner_msg_div > div > div > pre, pre, .inner_msg_div").first.inner_text().strip()
            if MESSAGE_TEXT not in displayed_msg:
                raise Exception(f"Sent message not found. Expected '{MESSAGE_TEXT}', found '{displayed_msg}'")

        log_step("Verify Sent Message", verify_message)
        log_step("Test Completion", lambda: print("Message send and verification completed"))

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
