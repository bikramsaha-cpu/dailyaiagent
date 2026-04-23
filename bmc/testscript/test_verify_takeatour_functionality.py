from datetime import datetime
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import build_page, empty_browser_results, make_log_step, open_message_centre

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def verify_step_title(page, expected_title, step_number):
    title_selector = "h1.introjs-tooltip-title"
    page.wait_for_selector(title_selector, timeout=5000)
    actual_title = page.locator(title_selector).first.inner_text().strip()
    print(f"Step {step_number} tooltip: {actual_title}")
    if actual_title.lower() != expected_title.lower():
        raise Exception(f"Step {step_number} title mismatch. Expected: {expected_title}, Got: {actual_title}")


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning take a tour automation on: {browser_name}")
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
        log_step(
            "Click Take A Tour Button",
            lambda: page.click(
                "button.tour-btn, button:has-text('Take a Tour'), text=Take a Tour",
                intent="start message centre guided tour",
                text="Take a Tour",
                keywords=["tour", "help", "message centre"],
            ),
        )

        step_titles = ["Chats", "View Catalog", "Search Bar", "Menu"]
        for index, title in enumerate(step_titles, start=1):
            log_step(
                f"Verify Step {index} {title}",
                lambda title=title, step_number=index: verify_step_title(page, title, step_number),
            )
            if index < len(step_titles):
                log_step(
                    f"Click Next For Step {index}",
                    lambda: page.click("a.introjs-nextbutton", text="Next", intent="move to next tour step"),
                )
            else:
                log_step(
                    "Click Done On Last Step",
                    lambda: page.click("a.introjs-donebutton", text="Done", intent="finish guided tour"),
                )

        log_step(
            "Verify Take A Tour Button After Tour",
            lambda: page.wait_for_selector("button.tour-btn, text=Take a Tour", timeout=10000),
        )

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

