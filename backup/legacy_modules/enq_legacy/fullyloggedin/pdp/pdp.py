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
PDP_URL = "https://www.indiamart.com/proddetail/oppo-mobile-phones-2851972054933.html?pos=1&kwd=oppo%20mobile%20phone&tags=rk:C|plc:1|dt:0|db:01|prc:1|dtp:p||sv:VGP|rsf:gd|ri:VGP_C_0_P-|-res:RC3|ktp:N0|stype:attr=1-br|mtp:Brn|wc:3|lcf:3|cq:hyderabad|qr_nm:gl-gd|cs:17525|com-cf:nl|ptrs:na|mc:184317|cat:750|qry_typ:P|lang:en|rtn:5-0-1-2-1-1-0|tyr:1|qrd:250819|mrd:250812|prdt:250820|pfen:1|gli:G0I0|v=4|crs=city-landing"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running PDP Enquiry Flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
        context = browser.new_context(storage_state=session_file_path)
        page = attach_healing(
            context.new_page(),
            suite_name="ENQ",
            module_name="PDP",
            test_name="chat_bl_pdp",
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

        # Step 1: Open PDP Page
        log_step("Open PDP Page", lambda: page.goto(PDP_URL, timeout=60000))

        # Step 2: Click Contact Supplier
        log_step(
            "Click Contact Supplier",
            lambda: page.click(
                "button:has-text('Contact Supplier'), a:has-text('Contact Supplier'), span:has-text('Contact Supplier')",
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )

        # Step 3: Handle 5-step CTA flow
        def click_next_cta():
            for i in range(5):
                if i < 3:
                    # First 3 clicks â†’ <button class="submit-button">Next</button>
                    page.wait_for_selector("button.submit-button, button:has-text('Next')", timeout=10000)
                    page.click("button.submit-button, button:has-text('Next')")
                elif i == 3:
                    # 4th click â†’ <input id="t0901_submit" value="Next">
                    page.wait_for_selector("input#t0901_submit[value='Next'], input#t0901_submit", timeout=10000)
                    page.click("input#t0901_submit[value='Next'], input#t0901_submit")
                else:
                    # 5th click â†’ <input id="t0901_submit" value="Submit">
                    page.wait_for_selector("input#t0901_submit[value='Submit'], input#t0901_submit", timeout=10000)
                    page.click("input#t0901_submit[value='Submit'], input#t0901_submit")

                print(f"âž¡ï¸ Clicked CTA ({i+1}/5)")
                time.sleep(1)  # give UI some time

        log_step("Click Next CTA 5 Times", click_next_cta)

        # Step 4: Wait on Thank You / Final Screen
        log_step("Wait for Thank You Page", lambda: page.wait_for_timeout(5000))

        context.close()
        browser.close()
        print(f"âœ… {browser_name} PDP Enquiry Flow completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

