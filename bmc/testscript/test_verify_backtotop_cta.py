from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import build_page, empty_browser_results, make_log_step, open_message_centre

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning go to top automation on: {browser_name}")
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

        def scroll_contact_list():
            for _ in range(3):
                page.evaluate(
                    """
                    () => {
                        const scrollContainer = document.querySelector('.ReactVirtualized__Grid');
                        if (scrollContainer) {
                            scrollContainer.scrollBy({ top: 500, behavior: 'smooth' });
                        }
                    }
                    """
                )
                time.sleep(2)

        log_step("Scroll Contact List", scroll_contact_list)

        log_step(
            "Click Go To Top Button",
            lambda: page.click(
                "div.goToBtn, button:has-text('Go to Top'), text=Go To Top",
                intent="return to top of the message centre list",
                text="Go To Top",
                keywords=["go to top", "scroll", "message centre"],
            ),
        )

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

