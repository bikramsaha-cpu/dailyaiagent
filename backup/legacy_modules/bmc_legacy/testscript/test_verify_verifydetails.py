from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    build_page,
    empty_browser_results,
    make_log_step,
    open_first_contact,
    open_message_centre,
    wait_for_conversation_header,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning verify details automation on: {browser_name}")
        browser = launch_browser(playwright, browser_name)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
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

        selected_contact = {"value": None}

        log_step("Open Message Centre", lambda: open_message_centre(page))

        def open_and_verify_conversation():
            selected_contact["value"] = open_first_contact(page, timeout=15000)
            print(f"Contact clicked: {selected_contact['value']}")
            time.sleep(2)
            header_name = wait_for_conversation_header(page, timeout=10000).inner_text().strip()
            print(f"Conversation header shows: {header_name}")
            if selected_contact["value"].lower() not in header_name.lower():
                raise Exception("Mismatch in contact name and conversation header")

        log_step("Open and Verify First Conversation", open_and_verify_conversation)

        def verify_view_details_sidebar():
            page.click(
                "#view_detail_icn, [id*='view_detail'], text=View Details",
                intent="open contact details sidebar from conversation screen",
                text="View Details",
                keywords=["view details", "contact details", "sidebar", "buyer"],
            )
            time.sleep(2)
            sidebar = page.locator("div.fs35.cursor-default:has-text('Contact Details'), text=Contact Details").first
            if not sidebar.is_visible():
                raise Exception("Contact Details sidebar not visible")

        log_step("Verify View Details Sidebar", verify_view_details_sidebar)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

