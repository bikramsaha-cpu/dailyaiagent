from playwright.sync_api import sync_playwright
import time
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger
from core.healing import attach_healing
from core.step_runner import run_step

# Path where login session is stored (must be generated beforehand)
session_file_path = "/var/log/web_tester_logs/enqlogin.json"

# Result tracking
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

# Browsers you want to run on
BROWSERS = ["chromium", "firefox"]

# Test mobile number
MOBILE_NUMBER = "8335017702"

# Impact page URL
IMPCAT_URL = "https://dir.indiamart.com/impcat/denim-clothing.html"

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Impact Page Enquiry Flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
        context = browser.new_context(storage_state=session_file_path)
        page = attach_healing(
            context.new_page(),
            suite_name="ENQ",
            module_name="DIR",
            test_name="impcat",
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

        # Step 1: Open Impact Page
        log_step("Open Impact Page", lambda: page.goto(IMPCAT_URL, timeout=60000))

        # Step 2: Click Contact Supplier button
        log_step(
            "Click Contact Supplier CTA",
            lambda: page.click(
                "button[data-click='^CTAContactSupplier']",
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )

        # Step 3: Navigate ISQs (4 Next + 1 Submit)
        def navigate_isqs():
            for i in range(4):  # 4 Next clicks
                page.click("input#t0901_submit[value='Next']")
                print(f"âž¡ï¸ Clicked Next CTA ({i+1})")
                time.sleep(1)
            
            # Final Submit
            page.click("input#t0901_submit[value='Submit']")
            print("âœ… Clicked Submit CTA")

        log_step("Navigate ISQs & Submit", navigate_isqs)

        # Step 4: Wait on Thank You Page
        log_step("Wait for Thank You Page", lambda: page.wait_for_timeout(5000))

        context.close()
        browser.close()
        print(f"âœ… {browser_name} Impact Page Enquiry Flow completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

