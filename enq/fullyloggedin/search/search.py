from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import time
import sys
import os

# Path setup for logger (adjust if needed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger  # Your custom logger

# Config
BROWSERS = ["chromium", "firefox"]
SEARCH_TERM = "headphones"
MOBILE_NUMBER = "9643193481"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\n🧪 Running Search + Enquiry Flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
        context = browser.new_context()
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        # Step 1: Go to dir.indiamart.com
        log_step("Open Homepage", lambda: page.goto("https://dir.indiamart.com/", timeout=60000))

        # Step 2: Enter search term
        log_step("Enter Search Term", lambda: page.fill("input#search_string", SEARCH_TERM))

        # Step 3: Click Search
        log_step("Click Search Button", lambda: page.click("input#btnSearch"))

        # Step 4: Select 'All India'
        log_step("Click All India Chip", lambda: page.click("ul#city-scrollbar1 li.newcitychip"))

        # Step 5: Click Contact Supplier (first result)
        log_step("Click Contact Supplier", lambda: page.click("button.contactsupplier"))

        # Step 6: Handle Enquiry Form flow
        def enquiry_form_flow():
            # First 2 clicks → button.submit-button
            for i in range(2):
                page.wait_for_selector("button.submit-button", timeout=10000)
                page.click("button.submit-button")
                print(f"➡️ Clicked Button CTA ({i+1}/2)")
                time.sleep(1)

            # Third click → input#t0901_submit[value="Next"]
            page.wait_for_selector("input#t0901_submit[value='Next']", timeout=10000)
            page.click("input#t0901_submit[value='Next']")
            print("➡️ Clicked Input Next (3rd CTA)")
            time.sleep(1)

            # Fourth click → input#t0901_submit[value="Submit"]
            page.wait_for_selector("input#t0901_submit[value='Submit']", timeout=10000)
            page.click("input#t0901_submit[value='Submit']")
            print("➡️ Clicked Submit (Final CTA)")
            time.sleep(2)

        log_step("Complete Enquiry Form", enquiry_form_flow)

        context.close()
        browser.close()
        print(f"✅ {browser_name} Search + Enquiry Flow completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
