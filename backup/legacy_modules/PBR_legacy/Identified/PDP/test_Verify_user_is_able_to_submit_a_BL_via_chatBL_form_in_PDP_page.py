from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

MOBILE_NUMBER = "9643193481"
BROWSERS = ["chromium"]
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

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
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            log_step("Navigate to PDP Page", lambda: page.goto(
                "https://www.indiamart.com/proddetail/office-canteen-table-19733578997.html?pos=4&kwd=table&tags=rk:T|plc:1|dt:0|db:01||dtp:p|pfs:1|sv:T|rsf:gd|ri:T_T_0_P-|-res:RC3|ktp:N0|mtp:SP|wc:1|lcf:3|cq:kolkata|qr_nm:gl-gd|cs:15031|com-cf:nl|ptrs:na|mc:2897|cat:93|qry_typ:P|lang:en|rtn:0-0-0-0-3-6-1|tyr:1|qrd:250731|mrd:250731|prdt:250731|msf:ls|pfen:1|gli:G0I0|v=4|crs=cs-glb|r=4",
                timeout=30000
            ))

            log_step("Scroll to Bottom", lambda: (page.mouse.wheel(0, 3000), page.wait_for_timeout(3000)))

            log_step("Click Chat BL Icon", lambda: (
                page.wait_for_selector("i.chat-CinBg.chat-blCin", timeout=10000),
                page.click("i.chat-CinBg.chat-blCin")
            ))

            log_step("Enter Quantity", lambda: (
                page.wait_for_selector("input#t0802txtbx_option1", timeout=10000),
                page.fill("input#t0802txtbx_option1", "2")
            ))

            log_step("Click 'Send' After Quantity", lambda: page.click("button#t0802_submit"))

            log_step("Select 'Wooden'", lambda: (
                page.wait_for_selector("label[optionid='13532503']", timeout=8000),
                page.click("label[optionid='13532503']")
            ))

            log_step("Select '2 Seater'", lambda: (
                page.wait_for_selector("label[optionid='13532505']", timeout=8000),
                page.click("label[optionid='13532505']")
            ))

            log_step("Enter Mobile Number", lambda: (
                page.wait_for_selector("input#t0802_login_field", timeout=15000),
                page.fill("input#t0802_login_field", MOBILE_NUMBER)
            ))

            log_step("Click 'Send' After Mobile Number", lambda: page.click("button#t0802_submit"))

            log_step("Click 'Send' Again", lambda: page.click("button#t0802_submit"))

            log_step("Click 'Final Send'", lambda: page.click("button#t0802_submit"))

            log_step("Close Chat", lambda: (
                page.wait_for_selector("div#t0802_cls", timeout=5000),
                page.click("div#t0802_cls")
            ))

            print("[Pass] Test Completion: PBR form submitted successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass", "PBR form submitted successfully", browser_name, MOBILE_NUMBER, run_time)

            page.wait_for_timeout(5000)

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

