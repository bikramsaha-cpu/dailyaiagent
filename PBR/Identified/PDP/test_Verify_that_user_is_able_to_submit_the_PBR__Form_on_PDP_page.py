from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

PDP_URL = (
    "https://www.indiamart.com/proddetail/round-folding-table-2849008344212.html"
    "?pos=3&kwd=table&tags=rk:B|plc:1|dt:0|db:01||dtp:p|pfs:1|sv:T|rsf:gd-|-res:RC4|ktp:N0|mtp:SP"
    "|wc:1|lcf:5|cq:hyderabad|qr_nm:gl-gd|cs:14073|com-cf:nl|ptrs:na|mc:2897|cat:93|qry_typ:P"
    "|lang:en|rtn:1-0-0-0-1-7-1|tyr:1|qrd:250702|mrd:250701|prdt:250702|msf:ls|v=4|crs=bp|r=4"
)

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium","firefox"]
MOBILE_NUMBER = "9643193481"

def run(playwright):
    # logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "PBR"
    # try:
    #     logger = GoogleSheetLogger("Buyer Automation", tab_name)
    # except Exception as e:
    #     print(f"⚠️ Could not initialize GoogleSheetLogger: {e}")
    #     logger = None

    for browser_name in BROWSERS:
        print(f"\n🧪 Running automation on: {browser_name}")
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
            log_step("Navigate to PDP", lambda: page.goto(PDP_URL, wait_until="load", timeout=60000))

            def enter_mobile():
                for _ in range(5):
                    try:
                        page.wait_for_selector("input#mobile-inline-bl", timeout=3000)
                        mobile_input = page.locator("input#mobile-inline-bl").first
                        if mobile_input.is_visible():
                            mobile_input.scroll_into_view_if_needed()
                            mobile_input.fill(MOBILE_NUMBER)
                            return
                    except PlaywrightTimeoutError:
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(600)
                raise Exception("Could not find mobile number input field")

            log_step("Enter Mobile Number", enter_mobile)

            def click_submit():
                for _ in range(10):
                    try:
                        page.wait_for_selector("input#t0102_submit", timeout=3000)
                        btn = page.locator("input#t0102_submit").first
                        if btn.is_visible():
                            btn.scroll_into_view_if_needed()
                            btn.click()
                            return
                    except PlaywrightTimeoutError:
                        pass
                    page.mouse.wheel(0, 1000)
                    page.wait_for_timeout(800)
                raise Exception("Could not find 'Submit Requirement' CTA")

            log_step("Click 'Submit Requirement'", click_submit)

            log_step("Enter Quantity", lambda: (page.wait_for_selector("input#ttxtbx_option1", timeout=10000),
                                              page.fill("input#ttxtbx_option1", "2")))

            def select_wooden():
                wooden_selected = False
                for sel in ["label:has-text('Wooden')", "span:has-text('Wooden')"]:
                    loc = page.locator(sel)
                    if loc.count() and loc.first.is_visible():
                        loc.first.scroll_into_view_if_needed()
                        loc.first.click()
                        wooden_selected = True
                        break
                if not wooden_selected:
                    rg = page.locator("div.beradio-sl, div.berdio-sl")
                    if rg.count():
                        rg.first.scroll_into_view_if_needed()
                        rg.first.click()
                        wooden_selected = True
                if not wooden_selected:
                    raise Exception("Could not confirm Wooden selection")

            log_step("Select 'Wooden'", select_wooden)

            log_step("Click 'Next' (Step 1)", lambda: (
                page.locator("button.submit-button").first.click()
                if page.locator("button.submit-button").count() and page.locator("button.submit-button").first.is_visible()
                else page.locator("button:has-text('Next')").first.click()
            ))

            log_step("Click 'Next' (Step 2)", lambda: (
                page.locator("input.form-btn[value='Next']").first.click()
                if page.locator("input.form-btn[value='Next']").count() and page.locator("input.form-btn[value='Next']").first.is_visible()
                else page.locator("input.form-btn").first.click()
            ))

            log_step("Click 'Submit'", lambda: (
                page.locator("input#t0901_submit").first.click()
                if page.locator("input#t0901_submit").count() and page.locator("input#t0901_submit").first.is_visible()
                else page.locator("input.befstgo2.hovsub.mdSub[value='Submit']").first.click()
            ))

            print(f"[Pass] Test Completion: PBR form submitted successfully")
            if logger:
                logger.log_status(f"[{browser_name}] Test Completion", "Pass", "PBR form submitted successfully", browser_name, MOBILE_NUMBER, run_time)

        except Exception as e:
            print(f"🔥 Critical error on {browser_name}: {e}")
            if logger:
                logger.log_status(f"[{browser_name}] Overall Script Failure", "Fail", str(e), browser_name, MOBILE_NUMBER, run_time)

        finally:
            context.close()
            browser.close()
            print(f"✅ {browser_name} test completed and browser closed")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
