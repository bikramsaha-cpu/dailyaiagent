from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

session_file_path = "/var/log/web_tester_logs/pbrlogin.json"

COMPANY_URL = (
    "https://www.indiamart.com/newramdevstationery-sportsgifts/"
    "?pos=10&kwd=football&tags=rk:T|plc:1|dt=0|db:01|prc:1|dtp:p||sv:VGP|rsf=gd|ri:VGP_T_0_P-"
    "|-res:RC2|ktp=N0|stype=attr=1|mtp=G|wc=1|lcf=3|cq=hyderabad|qr_nm=gl-gd|cs=16159|com-cf=nl"
    "|ptrs=na|mc=6542|cat=533|qry_typ=P|lang=en|rtn=0-0-0-1-4-5-0|tyr=1|qrd=250717|mrd=250717"
    "|prdt=250717|msf=ms|gli=G1I0|v=4|crs=cs-city"
)

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}: {step_name} completed successfully")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}.png"
                page.screenshot(path=screenshot_name)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            # Step 1: Navigate to Company Page
            log_step("Navigate to Company Page", lambda: page.goto(COMPANY_URL, wait_until="domcontentloaded", timeout=60000))

            # Step 2: Enter Mobile Number
            def enter_mobile():
                page.wait_for_selector("input#t0101_login_field", timeout=15000)
                mobile_field = page.locator("input#t0101_login_field")
                mobile_field.scroll_into_view_if_needed()
                mobile_field.fill(MOBILE_NUMBER)
            log_step("Enter Mobile Number", enter_mobile)

            # Step 3: Enter Product Name
            def enter_product_name():
                page.wait_for_selector("input#t0101prodtitle", timeout=10000)
                product_field = page.locator("input#t0101prodtitle")
                product_field.scroll_into_view_if_needed()
                product_field.fill("bags")  # <-- Change product name as needed
            log_step("Enter Product Name", enter_product_name)

            # Step 4: Click 'Submit Requirement'
            def click_submit_requirement():
                page.wait_for_selector("input#t0101_submit", timeout=15000)
                btn = page.locator("input#t0101_submit").first
                btn.scroll_into_view_if_needed()
                btn.click()
            log_step("Click 'Submit Requirement'", click_submit_requirement)

            # # Step 5: Fill Quantity
            # qty_selectors = [
            #     "input#t0101txtbx_option1",
            #     "input#ttxtbx_option1",
            #     "input[name*='text_name1']",
            #     "input[name*='quantity']",
            #     "input[id*='txtbx_option1']"
            # ]
            # def fill_quantity():
            #     page.wait_for_selector(",".join(qty_selectors), timeout=10000)
            #     for sel in qty_selectors:
            #         el = page.locator(sel)
            #         if el.count() > 0 and el.first.is_visible():
            #             el.first.fill("2")
            #             return
            #     raise Exception("Quantity input not found")
            # log_step("Fill Quantity", fill_quantity)

            # # Step 6: Select Material 'Plastic'
            # def select_plastic():
            #     plastic_label = page.locator("label:has-text('Plastic')")
            #     if plastic_label.count() > 0:
            #         plastic_label.first.click()
            #     else:
            #         raise Exception("Plastic option not found")
            # log_step("Select Material", select_plastic)

            # Step 7: Click Next buttons and Submit
            log_step("Click 'Next' (Step 1)", lambda: page.locator("input#t0101_submit[value='Next']").first.click())
            log_step("Click 'Next' (Step 2)", lambda: page.locator("input#t0101_submit[value='Next']").first.click())
            log_step("Click 'Submit'", lambda: page.locator("input#t0101_submit[value='Submit']").first.click())

            print(f"[Pass] Test Completion: PBR form submitted successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass", "PBR form submitted successfully", browser_name, MOBILE_NUMBER, run_time)

        except Exception as e:
            print(f"ðŸ”¥ Critical error on {browser_name}: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Overall Script Failure", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

