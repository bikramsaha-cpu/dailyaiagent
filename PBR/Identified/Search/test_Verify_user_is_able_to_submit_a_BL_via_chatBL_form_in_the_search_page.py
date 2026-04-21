from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

SEARCH_URL = (
    "https://dir.indiamart.com/search.mp?ss=shoes&search_type=p&src=adv-srch"
    "&mcatid=569&catid=145&q-quantity-unit=pair&v=4&crs=xnh-city&sref=adv-srch"
    "&trc=xium&tags=res:RC6|ktp:N0|stype:attr=1|mtp:SP|wc:2|lcf:-1|cq:null"
    "|qr_nm:gl-splt-gd|cs:15530|com-cf:nl|ptrs:na|mc:569|cat:145|qry_typ=P"
    "|lang=en|rtn=0-0-0-0-6-4-0|qrd:250717|mrd:250717|prdt:250717|msf=ls|gli=G1I2"
)

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium","firefox"]  # Add other browsers if needed
MOBILE_NUMBER = "9643193481"

def run(playwright):
    # logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"
    # try:
    #     logger = GoogleSheetLogger("Buyer Automation", tab_name)
    # except Exception as e:
    #     print(f"âš ï¸ Could not initialize GoogleSheetLogger: {e}")
    #     logger = None

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

        def navigate_to_search():
            def action():
                page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_selector(
                    "#t0802_bl_form_wrapper_cta, .prd-card, .prd, .cardlinks",
                    timeout=15000
                )
            try:
                log_step("Navigate to Search City Results", action)
                return True
            except Exception:
                page.screenshot(path="nav_error.png", full_page=True)
                return False

        try:
            if not navigate_to_search():
                browser.close()
                return

            # Find and click chat popup
            popup_found = False
            for _ in range(5):
                page.mouse.wheel(0, 300)
                page.wait_for_timeout(2000)
                try:
                    chat_popup = page.locator("#t0802_bl_form_wrapper_cta")
                    for _ in range(6):  # try for ~6 seconds
                        if chat_popup.is_visible():
                            chat_popup.click()
                            popup_found = True
                            break
                        page.wait_for_timeout(1000)
                    if popup_found:
                        break
                except TimeoutError:
                    continue

            if not popup_found:
                print("[Fail] Open Chat Popup: 'Chat with us' popup not found")
                browser.close()
                return

            # Test steps using log_step
            log_step(
                "Enter Quantity",
                lambda: (
                    page.wait_for_selector("input#t0802txtbx_option1", timeout=8000),
                    page.fill("input#t0802txtbx_option1", "2")
                )
            )

            log_step(
                "Click 'Next' (Step 1)",
                lambda: page.locator("button#t0802_submit").click()
            )

            log_step(
                "Select 'Formal Shoe'",
                lambda: (
                    page.wait_for_selector("#t0802_rad_chk3_option2", timeout=8000),
                    page.click("#t0802_rad_chk3_option2")
                )
            )
            
            log_step(
                "Select 'Nike Shoes'",
                lambda: (
                    page.wait_for_selector("#t0802_rad_chk4_option2", timeout=8000),
                    page.click("#t0802_rad_chk4_option2")
                )
            )

            log_step(
                "Enter Mobile Number",
                lambda: (
                    page.wait_for_selector("input#t0802_login_field", timeout=8000),
                    page.fill("input#t0802_login_field", MOBILE_NUMBER)
                )
            )

            log_step(
                "Click 'Next' (Step 2)",
                lambda: page.locator("button#t0802_submit").click()
            )

            log_step(
                "Click 'Submit'",
                lambda: page.locator("button#t0802_submit").click()
            )

            print(f"[Pass] Test Completion: PBR form submitted successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass", "PBR form submitted successfully", browser_name, MOBILE_NUMBER, run_time)

        except Exception as e:
            print(f"[Fail] Test Completion: Unexpected error â€” {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

