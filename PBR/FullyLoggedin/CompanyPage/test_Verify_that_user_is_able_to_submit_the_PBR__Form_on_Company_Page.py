from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os

# Add parent folder for logger import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger  # custom logger instance

# Path for stored login session (ensure this file exists)
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"

# Company URL
COMPANY_URL = (
    "https://www.indiamart.com/newramdevstationery-sportsgifts/"
    "?pos=10&kwd=football&tags=rk:T|plc:1|dt:0|db:01|prc:1|dtp:p||sv:VGP|rsf:gd|ri:VGP_T_0_P-"
    "|-res:RC2|ktp=N0|stype=attr=1|mtp=G|wc=1|lcf=3|cq=hyderabad|qr_nm=gl-gd|cs=16159|com-cf=nl"
    "|ptrs=na|mc=6542|cat=533|qry_typ=P|lang=en|rtn=0-0-0-1-4-5-0|tyr=1|qrd=250717|mrd=250717"
    "|prdt=250717|msf=ms|gli=G1I0|v=4|crs=cs-city"
)

# Global variables
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name} completed successfully âœ…")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} âŒ (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        submitted = False  # Track final submission status

        try:
            # Step 1: Navigate to Company Page
            log_step("Navigate to Company Page",
                     lambda: page.goto(COMPANY_URL, wait_until="domcontentloaded", timeout=60000))

            # Step 2: Wait for 'Submit Requirement' CTA
            log_step("Wait for 'Submit Requirement' CTA",
                     lambda: page.wait_for_selector("input#t0101_submit", timeout=15000))

            # Step 3: Enter Product Name: "Shirt"
            def enter_product_name():
                prod_input = page.locator("input#t0101prodtitle")
                if prod_input.is_visible():
                    prod_input.fill("Shirt")
                else:
                    raise Exception("Product name input (#t0101prodtitle) not found")
            log_step("Enter Product Name", enter_product_name)

            page.wait_for_timeout(500)

            # Step 4: Click 'Submit Requirement'
            def click_submit_requirement():
                loc = page.locator("input#t0101_submit")
                clicked = False
                for i in range(loc.count()):
                    btn = loc.nth(i)
                    value = btn.get_attribute("value")
                    if btn.is_visible() and btn.is_enabled() and value and "Submit Requirement" in value:
                        btn.scroll_into_view_if_needed()
                        btn.click()
                        clicked = True
                        break
                if not clicked:
                    first_handle = loc.first
                    first_handle.scroll_into_view_if_needed()
                    first_handle.evaluate("el => el.click()")
            log_step("Click 'Submit Requirement'", click_submit_requirement)

            page.wait_for_timeout(2000)

            # Step 5â€“7: Click 'Next' 3 times
            def click_next_cta(step_no):
                nxt = page.locator("input#t0101_submit[value='Next']")
                if nxt.count() > 0 and nxt.first.is_visible():
                    nxt.first.click()
                else:
                    raise Exception(f"'Next' button not found at Step {step_no}")

            for i in range(1, 4):
                log_step(f"Click 'Next' (Step {i})", lambda i=i: click_next_cta(i))
                page.wait_for_timeout(1500)

            # Step 8: Click Final 'Submit'
            def click_submit():
                nonlocal submitted
                submit_btn = page.locator("input#t0101_submit[value='Submit']")
                if submit_btn.count() > 0 and submit_btn.first.is_visible():
                    submit_btn.first.click()
                    submitted = True
                else:
                    raise Exception("Final 'Submit' button not found or not visible")
            log_step("Click 'Submit' (Final)", click_submit)

            page.wait_for_timeout(3000)

        except Exception as e:
            print(f"ðŸ”¥ Critical error on {browser_name}: {e}")

        finally:
            log_step("Test Completion",
                     lambda: print(f"PBR form submitted successfully âœ…" if submitted else "Test ended with failure âŒ"))
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed\n")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)


