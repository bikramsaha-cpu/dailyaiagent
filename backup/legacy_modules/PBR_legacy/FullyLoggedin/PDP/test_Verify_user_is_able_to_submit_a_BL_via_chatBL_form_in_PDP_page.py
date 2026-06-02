from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from collections import defaultdict
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from logger_instance import logger

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
BROWSERS = ["chromium"]  # Add more browsers if needed
MOBILE_NUMBER = "9643193481"  # Optional if you want to log mobile or user info
TAB_NAME = "PBR"
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
        # context = browser.new_context(storage_state="auth.json")  # Remove if no login session
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
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_').replace('\'','')}.png"
                page.screenshot(path=screenshot_name)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        try:
            # Step 1: Navigate to PDP
            log_step("Navigate to PDP", lambda: page.goto(
                "https://www.indiamart.com/proddetail/office-canteen-table-19733578997.html?pos=4&kwd=table",
                timeout=30000,
                wait_until="load"))
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

            # Step 2: Scroll to chat icon
            def scroll_chat_icon():
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(3000)  # sleep 3 seconds for page to settle
            log_step("Scroll to Chat BL icon", scroll_chat_icon)

            # Step 3: Click Chat BL icon
            log_step("Click Chat BL icon", lambda: (
                page.wait_for_selector("i.chat-CinBg.chat-blCin", timeout=10000, state="visible"),
                page.click("i.chat-CinBg.chat-blCin")
            ))

            # Step 4: Enter quantity
            log_step("Enter Quantity", lambda: (
                page.wait_for_selector("input#t0802txtbx_option1", timeout=10000, state="visible"),
                page.fill("input#t0802txtbx_option1", "2")
            ))

            # Step 5: Click send after quantity
            log_step("Click send button after quantity", lambda: page.click("button#t0802_submit"))

            # Step 6: Select 'Wooden'
            log_step("Select 'Wooden' option", lambda: (
                page.wait_for_selector("label[optionid='13532503']", timeout=8000, state="visible"),
                page.click("label[optionid='13532503']")
            ))

            # Step 7: Select '2 Seater'
            log_step("Select '2 Seater' option", lambda: (
                page.wait_for_selector("label[optionid='13532505']", timeout=8000, state="visible"),
                page.click("label[optionid='13532505']")
            ))

            # Step 8: Click send after selections
            log_step("Click send button after selections", lambda: page.click("button#t0802_submit"))

            # Step 9: Final send
            log_step("Click final send button", lambda: page.click("button#t0802_submit"))

            # Step 10: Close chat
            log_step("Close chat window", lambda: (
                page.wait_for_selector("div#t0802_cls", timeout=5000, state="visible"),
                page.click("div#t0802_cls")
            ))

            # Step 11: Open 'Hi Arka' dropdown
            log_step("Open 'Hi Arka' dropdown", lambda: (
                page.wait_for_selector("a.rmv.cpo.ico-usr", timeout=8000, state="visible"),
                page.click("a.rmv.cpo.ico-usr")
            ))

            # Step 12: Click 'My Orders'
            log_step("Click 'My Orders'", lambda: (
                page.wait_for_selector("a.h_ic21[href*='managebl']", timeout=8000, state="visible"),
                page.click("a.h_ic21[href*='managebl']")
            ))

            # Optional wait after navigation
            page.wait_for_timeout(5000)

        except PlaywrightTimeoutError as te:
            print(f"[Fail] TimeoutError during execution: {te}")
        except Exception as e:
            print(f"[Fail] Unexpected Error during execution: {e}")
        finally:
            print(f"âœ… {browser_name} test completed and browser closed")
            context.close()
            browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

