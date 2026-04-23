from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    CONTACT_NAME_SELECTOR,
    build_page,
    empty_browser_results,
    first_contact_name,
    make_log_step,
    open_message_centre,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning block contact automation on: {browser_name}")
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

        contact_name = {"value": None}

        log_step("Open Message Centre", lambda: open_message_centre(page))

        def step_get_first_contact():
            contact_name["value"] = first_contact_name(page, timeout=15000)
            print(f"First contact name: {contact_name['value']}")

        log_step("Get First Contact Name", step_get_first_contact)

        def block_first_contact():
            page.locator(CONTACT_NAME_SELECTOR).first.hover()
            time.sleep(1)
            page.click(
                "#contactopts0, [id*='contactopts'], [aria-label*='options']",
                intent="open first contact options menu in message centre",
                text="Options",
                keywords=["contact", "options", "menu", "buyer"],
            )
            page.click(
                "#block0, [id*='block'], text=Block",
                intent="block first contact in message centre",
                text="Block",
                role="button",
                role_name="Block",
                keywords=["block", "contact", "buyer"],
            )
            page.click(
                "#blockconfirm, button:has-text('Block'), button:has-text('Confirm')",
                intent="confirm blocking the selected contact",
                text="Confirm",
                role="button",
                role_name="Confirm",
                keywords=["confirm", "block", "contact"],
            )
            time.sleep(2)

        log_step("Block First Contact", block_first_contact)

        def navigate_to_blocked_contacts():
            page.click(
                "#opts, [id*='opts'], text=More",
                intent="open more tabs in message centre",
                text="More",
                keywords=["more", "tabs", "message centre"],
            )
            page.click(
                "#block_contacts, [id*='block_contacts'], text=Blocked",
                intent="open blocked contacts tab in message centre",
                text="Blocked",
                keywords=["blocked", "contacts", "message centre"],
            )
            time.sleep(3)

        log_step("Navigate to Blocked Contacts", navigate_to_blocked_contacts)

        def verify_blocked_contact():
            page.wait_for_selector(f".left_det_show .c_name, {CONTACT_NAME_SELECTOR}", timeout=10000)
            blocked_contacts = page.locator(f".left_det_show .c_name, {CONTACT_NAME_SELECTOR}")
            blocked_names = [blocked_contacts.nth(i).inner_text().strip() for i in range(blocked_contacts.count())]
            if contact_name["value"] not in blocked_names:
                raise Exception(f"{contact_name['value']} not found in Blocked Contacts")

        log_step("Verify Blocked Contact", verify_blocked_contact)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

