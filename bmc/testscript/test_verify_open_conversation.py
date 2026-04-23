from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    CONVERSATION_HEADER_SELECTOR,
    build_page,
    empty_browser_results,
    make_log_step,
    open_first_contact,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
MESSAGE_CENTRE_URL = "https://buyer.indiamart.com/enquiry/messagecentre/"

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning automation on: {browser_name}")
        browser = launch_browser(playwright, browser_name)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
        page = build_page(context.new_page(), test_name="test_verify_open_conversation")
        log_step = make_log_step(
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=MOBILE_NUMBER,
        )

        log_step("Open Message Centre", lambda: page.goto(MESSAGE_CENTRE_URL, wait_until="domcontentloaded", timeout=60000))

        def open_and_verify_conversation():
            contact_name = open_first_contact(page, timeout=15000)
            print(f"Contact clicked: {contact_name}")
            time.sleep(2)
            page.wait_for_selector(CONVERSATION_HEADER_SELECTOR, timeout=10000)
            header_name = page.locator(CONVERSATION_HEADER_SELECTOR).first.inner_text().strip()
            print(f"Conversation header shows: {header_name}")
            if contact_name.lower() not in header_name.lower():
                raise Exception("Mismatch in contact name and conversation header")

        log_step("Open and Verify Conversation", open_and_verify_conversation)
        log_step("Test Completion", lambda: print("Conversation verification completed"))

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

