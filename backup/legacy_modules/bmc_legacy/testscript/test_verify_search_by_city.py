from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    CONTACT_CARD_SELECTOR,
    CONTACT_NAME_SELECTOR,
    MESSAGE_SEARCH_INPUT_SELECTOR,
    build_page,
    empty_browser_results,
    make_log_step,
    open_message_centre,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
CITY_NAME = "Pune"
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def load_all_contacts(page):
    previous_count = -1
    max_tries = 25

    for _ in range(max_tries):
        cards = page.locator(CONTACT_CARD_SELECTOR)
        current_count = cards.count()
        if current_count == previous_count:
            break
        previous_count = current_count
        page.evaluate(
            """
            () => {
                const container = document.querySelector('.ReactVirtualized__Grid__innerScrollContainer');
                if (container) {
                    container.scrollBy(0, 400);
                }
            }
            """
        )
        time.sleep(1)

    return page.locator(CONTACT_CARD_SELECTOR)


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning city verification automation on: {browser_name}")
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

        log_step("Open Message Centre", lambda: open_message_centre(page))

        def search_and_verify_contacts():
            search_input = page.locator(MESSAGE_SEARCH_INPUT_SELECTOR).first
            search_input.click()
            search_input.fill(CITY_NAME)
            time.sleep(3)
            page.wait_for_selector(CONTACT_CARD_SELECTOR, timeout=15000)
            cards = load_all_contacts(page)

            mismatched_contacts = []
            for index in range(cards.count()):
                card = cards.nth(index)
                try:
                    name_locator = card.locator(CONTACT_NAME_SELECTOR).first
                    city_locator = card.locator("div.prdct_dsply.wrd_elip, div[class*='prdct_dsply'], div[class*='city']").first
                    name = name_locator.inner_text().strip()
                    city = city_locator.inner_text().strip()
                    if CITY_NAME.lower() not in city.lower():
                        mismatched_contacts.append((name, city))
                except Exception:
                    continue

            if mismatched_contacts:
                raise Exception(f"Mismatched contacts found: {mismatched_contacts}")

        log_step(f"Search And Verify Contacts Are From {CITY_NAME}", search_and_verify_contacts)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

