from datetime import datetime
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import build_page, empty_browser_results, make_log_step

session_file_path = "/var/log/web_tester_logs/bmclogin.json"
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
LOGIN_CHECK_URL = "https://buyer.indiamart.com/"
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning session check automation on: {browser_name}")
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

        log_step(
            "Open Buyer Homepage",
            lambda: page.goto(LOGIN_CHECK_URL, wait_until="domcontentloaded", timeout=60000),
        )

        def click_messages_icon():
            if page.locator("#messageWid").count() > 0 and page.locator("#messageWid").first.is_visible():
                page.click(
                    "#messageWid",
                    intent="open messages widget from buyer homepage",
                    text="Messages",
                    keywords=["messages", "homepage", "buyer"],
                )

        log_step("Click Messages Icon Optional", click_messages_icon)

        def verify_login():
            page.wait_for_selector("text=Dashboard, text=Messages, text=Post RFQ", timeout=15000)

        log_step("Verify Login", verify_login)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
