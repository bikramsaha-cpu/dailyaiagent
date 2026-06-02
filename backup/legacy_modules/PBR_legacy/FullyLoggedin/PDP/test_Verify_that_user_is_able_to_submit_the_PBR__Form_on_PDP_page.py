from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger
from core.healing import attach_healing
from core.step_runner import run_step

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium"]  # Add more if you want
MOBILE_NUMBER = "9643193481"
session_file_path = "/var/log/web_tester_logs/pbrlogin.json"

PDP_URL = (
    "https://www.indiamart.com/proddetail/round-folding-table-2849008344212.html"
    "?pos=3&kwd=table&tags=rk:B|plc:1|dt:0|db:01||dtp:p|pfs:1|sv:T|rsf:gd-|-res:RC4|ktp:N0|mtp:SP"
    "|wc:1|lcf:5|cq:hyderabad|qr_nm:gl-gd|cs:14073|com-cf:nl|ptrs:na|mc:2897|cat:93|qry_typ:P"
    "|lang:en|rtn:1-0-0-0-1-7-1|tyr:1|qrd:250702|mrd:250701|prdt:250702|msf:ls|v=4|crs=bp|r=4"
)

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
        context = browser.new_context(storage_state=session_file_path)
        # context = browser.new_context(storage_state="auth.json")  # Remove if not logged in
        page = attach_healing(
            context.new_page(),
            suite_name="PBR",
            module_name="PDP",
            test_name="submit_requirement_pdp",
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
                mobile_number="",
            )

        try:
            log_step("Navigate to PDP", lambda: page.goto(PDP_URL, wait_until="load", timeout=60000))
            # Handle localization popup if present
            def close_localization_popup():
                try:
                    page.wait_for_selector("span#closeCityPopup.close-btn26", timeout=3000)
                    close_btn = page.locator("span#closeCityPopup.close-btn26").first
                    if close_btn.is_visible():
                        close_btn.click()
                        print("[Info] Localization popup closed.")
                        page.wait_for_timeout(500)  # allow popup to disappear
                except PlaywrightTimeoutError:
                    print("[Info] No localization popup appeared.")

            log_step("Close Localization Popup", close_localization_popup)


            def click_submit_requirement():
                submit_clicked = False
                for i in range(10):
                    try:
                        page.wait_for_selector("input#t0102_submit", timeout=3000)
                        btn = page.locator("input#t0102_submit").first
                        if btn.is_visible():
                            btn.scroll_into_view_if_needed()
                            btn.click()
                            submit_clicked = True
                            print(f"[Pass] 'Submit Requirement' clicked on attempt {i+1}.")
                            break
                    except PlaywrightTimeoutError:
                        pass
                    print(f"   [Info] Scroll attempt {i+1}")
                    page.mouse.wheel(0, 1000)
                    page.wait_for_timeout(800)
                if not submit_clicked:
                    raise Exception("Could not find 'Submit Requirement' CTA")
                page.wait_for_timeout(1000)  # allow form animation

            log_step("Click 'Submit Requirement'", click_submit_requirement)

            log_step("Enter Quantity", lambda: (
                page.wait_for_selector("input#ttxtbx_option1", timeout=10000),
                page.fill("input#ttxtbx_option1", "2")
            ))

            def select_wooden():
                wooden_selected = False
                for sel in ["label:has-text('Wooden')", "span:has-text('Wooden')"]:
                    try:
                        loc = page.locator(sel)
                        if loc.count() and loc.first.is_visible():
                            loc.first.scroll_into_view_if_needed()
                            loc.first.click()
                            wooden_selected = True
                            print("[Pass] 'Wooden' selected via label/span text.")
                            break
                    except Exception:
                        pass
                if not wooden_selected:
                    try:
                        rg = page.locator("div.beradio-sl, div.berdio-sl")
                        if rg.count():
                            rg.first.scroll_into_view_if_needed()
                            rg.first.click()
                            wooden_selected = True
                            print("[Warn] 'Wooden' selected via radio graphic fallback.")
                    except Exception:
                        print("[Fail] Could not select 'Wooden'. Continuingâ€¦")

                page.wait_for_timeout(300)

            log_step("Select 'Wooden' option", select_wooden)

            def click_next1():
                next1_clicked = False
                try:
                    n1 = page.locator("button.submit-button")
                    if n1.count() and n1.first.is_visible():
                        n1.first.click()
                        next1_clicked = True
                except Exception:
                    pass
                if not next1_clicked:
                    try:
                        page.locator("button:has-text('Next')").first.click()
                        next1_clicked = True
                    except Exception:
                        pass
                if not next1_clicked:
                    raise Exception("Next (1) button not found.")
                page.wait_for_timeout(500)

            log_step("Click Next (1)", click_next1)

            def click_next2():
                next2_clicked = False
                try:
                    n2 = page.locator("input.form-btn[value='Next']")
                    if n2.count() and n2.first.is_visible():
                        n2.first.click()
                        next2_clicked = True
                except Exception:
                    pass
                if not next2_clicked:
                    try:
                        page.locator("input.form-btn").first.click()
                        next2_clicked = True
                    except Exception:
                        pass
                if not next2_clicked:
                    raise Exception("Next (2) button not found.")
                page.wait_for_timeout(500)

            log_step("Click Next (2)", click_next2)

            def final_submit():
                submitted = False
                try:
                    s = page.locator("input#t0901_submit")
                    if s.count() and s.first.is_visible():
                        s.first.click()
                        submitted = True
                except Exception:
                    pass
                if not submitted:
                    try:
                        page.locator("input.befstgo2.hovsub.mdSub[value='Submit']").first.click()
                        submitted = True
                    except Exception:
                        pass
                if not submitted:
                    raise Exception("Final Submit button not found.")
                page.wait_for_timeout(3000)

            log_step("Click Final Submit", final_submit)

            print("[Pass] Test Completion: PBR form submitted successfully")

        except Exception as e:
            print(f"ðŸ”¥ Critical error on {browser_name}: {e}")

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

