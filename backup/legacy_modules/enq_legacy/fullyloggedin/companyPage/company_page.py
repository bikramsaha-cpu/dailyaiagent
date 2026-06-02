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
MOBILE_NUMBER = "9643193481"
COMPANY_URL = "https://www.indiamart.com/raghavendraagency-hyderabad/?pid=2851972054933&c_id=750&mid=184317&pn=Oppo%20Mobile%20Phones"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running 'Enquiry Flow' automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
        context = browser.new_context(storage_state=session_file_path)
        page = attach_healing(
            context.new_page(),
            suite_name="ENQ",
            module_name="CompanyPage",
            test_name="company_page",
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

        # Step 1: Open Company Page
        log_step("Open Company Page", lambda: page.goto(COMPANY_URL, timeout=60000))

        # Step 2: Click Contact Supplier
        log_step(
            "Click Contact Supplier",
            lambda: page.click(
                "#head-suplr",
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )

        # Step 3: Click Next CTA 4 times
        def click_next_cta():
            for i in range(5):
                page.wait_for_selector("#t0901_submit", timeout=10000)
                page.click("#t0901_submit")
                print(f"âž¡ï¸ Clicked Next CTA ({i+1}/4)")
                time.sleep(1)  # give UI some time

        log_step("Click Next CTA 4 Times", click_next_cta)

        # Step 4: Wait on Thank You Page
        log_step("Wait on Thank You Page", lambda: page.wait_for_timeout(3000))

        context.close()
        browser.close()
        print(f"âœ… {browser_name} 'Enquiry Flow' test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

