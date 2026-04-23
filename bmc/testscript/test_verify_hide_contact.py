from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    CONTACT_NAME_SELECTOR,
    build_page,
    empty_browser_results,
    first_contact_name,
    make_log_step,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
MESSAGE_CENTRE_URL = "https://buyer.indiamart.com/enquiry/messagecentre/"
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning hide contact automation on: {browser_name}")
        browser = launch_browser(playwright, browser_name)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
        page = build_page(context.new_page(), test_name=test_case_name)
        log_step = make_log_step(
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=MOBILE_NUMBER,
        )

        contact_name = {"value": None}

        def hierarchical_log_step(step_name, func):
            full_step = f"{test_case_name} -> {step_name}"
            return make_log_step(
                page=page,
                browser_name=browser_name,
                run_time=run_time,
                browser_results=browser_results,
                logger=logger,
                mobile_number=MOBILE_NUMBER,
            )(full_step, func)

        hierarchical_log_step("Open Message Centre", lambda: page.goto(MESSAGE_CENTRE_URL, wait_until="domcontentloaded", timeout=60000))

        def step_get_first_contact():
            contact_name["value"] = first_contact_name(page, timeout=15000)

        hierarchical_log_step("Get First Contact Name", step_get_first_contact)

        def hide_first_contact():
            page.wait_for_selector(CONTACT_NAME_SELECTOR, timeout=15000)
            page.locator(CONTACT_NAME_SELECTOR).first.hover()
            time.sleep(1)
            page.click(
                "#contactopts0, [id*='contactopts'], [aria-label*='options']",
                intent="open first contact options menu",
                keywords=["contact", "options", "menu"],
            )
            page.wait_for_selector("#hide0, [id*='hide'], text=Hide", timeout=10000)
            page.click(
                "#hide0, [id*='hide'], text=Hide",
                intent="hide first contact from message centre",
                text="Hide",
                role="button",
                role_name="Hide",
                keywords=["hide", "contact"],
            )
            time.sleep(2)

        hierarchical_log_step("Hide First Contact", hide_first_contact)

        def navigate_to_hidden_contacts():
            page.click("#opts, [id*='opts'], text=More")
            page.click("#hidden_contacts, [id*='hidden_contacts'], text=Hidden")
            time.sleep(3)

        hierarchical_log_step("Navigate to Hidden Contacts", navigate_to_hidden_contacts)

        def verify_hidden_contact():
            page.wait_for_selector(f".left_det_show .c_name, {CONTACT_NAME_SELECTOR}", timeout=10000)
            hidden_contacts = page.locator(f".left_det_show .c_name, {CONTACT_NAME_SELECTOR}")
            hidden_names = [hidden_contacts.nth(i).inner_text().strip() for i in range(hidden_contacts.count())]
            if contact_name["value"] not in hidden_names:
                raise Exception(f"{contact_name['value']} not found in Hidden Contacts")

        hierarchical_log_step("Verify Hidden Contact", verify_hidden_contact)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

