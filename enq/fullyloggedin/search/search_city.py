from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import time
import sys
import os

# Path setup for logger
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger  # Your custom logger
from core.healing import attach_healing
from core.step_runner import run_step

# Config
session_file_path = "/var/log/web_tester_logs/enqlogin.json"
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "8335017702"
SEARCH_URL = "https://dir.indiamart.com"  # Homepage URL
SEARCH_TERM = "hat"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running 'Search City Enquiry Flow' on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
        context = browser.new_context(storage_state=session_file_path)
        page = attach_healing(
            context.new_page(),
            suite_name="ENQ",
            module_name="Search",
            test_name="search_city",
        )

        def log_step(step_name, func):
            return run_step(
                step_name=step_name,
                func=func,
                page=page,
                browser_name=browser_name,
                run_time=run_time,
                browser_results=browser_results,
                logger=logger,
                mobile_number=MOBILE_NUMBER,
            )

        # Step 1: Open Search Page
        log_step("Open Search Page", lambda: page.goto(SEARCH_URL, timeout=60000))

        # Step 2: Enter search term
        log_step("Enter search term", lambda: page.fill("input#search_string", SEARCH_TERM))

        # Step 3: Click Search button
        log_step("Click Search button", lambda: page.click("input#btnSearch"))

        # Step 4: Click first Contact Supplier CTA
        log_step(
            "Click first Contact Supplier CTA",
            lambda: page.click(
                "button.contactsupplier",
                timeout=10000,
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )

        # Step 5: Navigate ISQs
        def navigate_isqs():
            # First Next button
            page.wait_for_selector("button.submit-button", timeout=10000)
            page.click("button.submit-button")
            print("âž¡ï¸ Clicked Next CTA (1)")
            time.sleep(1)

            # Second Next button
            page.click("button.submit-button")
            print("âž¡ï¸ Clicked Next CTA (2)")
            time.sleep(1)

            # Third Next button
            page.wait_for_selector("input#t0901_submit[value='Next']", timeout=10000)
            page.click("input#t0901_submit[value='Next']")
            print("âž¡ï¸ Clicked Next CTA (3)")
            time.sleep(1)

            # Final Submit
            page.wait_for_selector("input#t0901_submit[value='Submit']", timeout=10000)
            page.click("input#t0901_submit[value='Submit']")
            print("âœ… Form submitted")

        log_step("Navigate ISQs & Submit", navigate_isqs)

        # Step 6: Wait for Thank You page
        log_step("Wait for Thank You Page", lambda: page.wait_for_timeout(5000))

        context.close()
        browser.close()
        print(f"âœ… {browser_name} Search City Enquiry Flow completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

