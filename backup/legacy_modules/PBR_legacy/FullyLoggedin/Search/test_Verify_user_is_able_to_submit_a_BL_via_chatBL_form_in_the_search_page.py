from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium", "firefox"]

MOBILE_NUMBER = "9643193481"  # Optional if you want to log user info
TAB_NAME = "PBR"

SEARCH_URL = (
    "https://dir.indiamart.com/search.mp?ss=shoes&search_type=p&src=adv-srch"
    "&mcatid=569&catid=145&q-quantity-unit=pair&v=4&crs=xnh-city&sref=adv-srch"
    "&trc=xium&tags=res:RC6|ktp:N0|stype:attr=1|mtp:SP|wc:2|lcf:-1|cq:null"
    "|qr_nm:gl-splt-gd|cs:15530|com-cf:nl|ptrs:na|mc:569|cat:145|qry_typ=P"
    "|lang=en|rtn=0-0-0-0-6-4-0|qrd:250717|mrd:250717|prdt:250717|msf=ls|gli=G1I2"
)
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"


def run(playwright):
    # logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # try:
    #     logger = GoogleSheetLogger("Buyer Automation", TAB_NAME)
    #     print("âœ… GoogleSheetLogger initialized successfully")
    # except Exception as e:
    #     print(f"âš ï¸ Could not initialize GoogleSheetLogger: {e}")
    #     logger = None

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)
        context = browser.new_context(storage_state=session_file_path)
        # context = browser.new_context(storage_state="auth.json")
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}: completed successfully")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_').replace('\'','')}.png"
                page.screenshot(path=screenshot_name)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        def navigate_to_search():
            try:
                page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                print("[Warn] Initial navigation timed out. Retrying...")
                page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_selector(
                "#t0802_bl_form_wrapper_cta, .prd-card, .prd, .cardlinks",
                timeout=15000
            )

        try:
            log_step("Navigate to Search Page", navigate_to_search)

            def click_chat_popup():
                popup_found = False
                for _ in range(5):
                    page.mouse.wheel(0, 300)
                    page.wait_for_timeout(2000)
                    chat_popup = page.locator("#t0802_bl_form_wrapper_cta")
                    if chat_popup.is_visible():
                        chat_popup.click()
                        popup_found = True
                        break
                if not popup_found:
                    raise Exception("Chat popup not found after retries")

            log_step("Click 'Chat with us' popup", click_chat_popup)

            log_step("Enter Quantity", lambda: (
                page.wait_for_selector("input#t0802txtbx_option1", timeout=8000),
                page.fill("input#t0802txtbx_option1", "2")
            ))

            log_step("Click Send (after quantity)", lambda: page.locator("button#t0802_submit").click())

            log_step("Select 'Formal Shoe'", lambda: (
                page.wait_for_selector("#t0802_rad_chk3_option2", timeout=8000),
                page.click("#t0802_rad_chk3_option2")
            ))

            log_step("Click Send (after radio)", lambda: page.locator("button#t0802_submit").click())

            log_step("Click Final Send", lambda: page.locator("button#t0802_submit").click())

            log_step("Close Chat Popup", lambda: (
                page.wait_for_selector("#t0802_cls", timeout=5000),
                page.click("#t0802_cls")
            ))


            print("[Pass] Test Completion: ChatBL form submitted successfully")

        except Exception as e:
            print(f"[Fail] Unexpected Error: {e}")

        finally:
            print(f"âœ… {browser_name} test completed and browser closed")
            context.close()
            browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

