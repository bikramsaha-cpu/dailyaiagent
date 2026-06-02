from playwright.sync_api import sync_playwright
import time
from google_logger import GoogleSheetLogger
from datetime import datetime
from mailer import send_summary_email
from collections import defaultdict
import os
import sys
import subprocess

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

MOBILE_NUMBER = "9643193481"
OTP = "1956"
BROWSERS = ["chromium", "firefox"]

AUTH_FILE = {
    "chromium": "/var/log/web_tester_logs/sellermylogin.json",
    "firefox": "/var/log/web_tester_logs/sellermylogin.json"
}

# Optional: Save session after OTP login
SAVE_SESSION = True

def run(playwright):
    sheet_logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_url = "https://docs.google.com/spreadsheets/d/1s5QtTQ_naNwyg4CVb2Nt1Tg0HpRGxrt11sMNMvjvYVw/edit#gid=0"
    tab_name = "Seller Dashboard"

    try:
        sheet_logger = GoogleSheetLogger("Seller My Automation", tab_name)
    except Exception:
        print("âš ï¸ Google Sheet logging is disabled due to initialization failure.")
        sheet_logger = None

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ==== OTP Login Flow ====
            page.goto("https://seller.indiamart.com/", timeout=60000)
            time.sleep(2)
            page.fill("input#mobNo", MOBILE_NUMBER)
            page.click("button.login_btn")
            page.wait_for_selector("input#first", timeout=10000)

            otp_ids = ["first", "second", "third", "fourth_num"]
            for digit, otp_id in zip(OTP, otp_ids):
                page.fill(f"input#{otp_id}", digit)
                time.sleep(0.3)

            page.click("input#sbmtbtnOtp")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                print("âš ï¸ networkidle timeout ignored")
            print(f"âœ… Logged in successfully on {browser_name}")

            # Save session for future runs
            if SAVE_SESSION:
                os.makedirs(os.path.dirname(AUTH_FILE[browser_name]), exist_ok=True)
                context.storage_state(path=AUTH_FILE[browser_name])
                print(f"ðŸ’¾ Session saved to {AUTH_FILE[browser_name]}")

            # ==== Helper functions ====
            def log_step(title, func):
                full_title = f"[{browser_name}] {title}"
                try:
                    func()
                    if sheet_logger:
                        sheet_logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
                    browser_results[browser_name]["Pass"] += 1
                    print(f"âœ… {full_title}")
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    if sheet_logger:
                        sheet_logger.log_status(
                            full_title,
                            "Fail",
                            error_msg,
                            browser_name,
                            MOBILE_NUMBER,
                            run_time
                        )
                    browser_results[browser_name]["Fail"] += 1
                    screenshot_name = f"{browser_name}_{title.replace(' ', '_')}.png"
                    page.screenshot(path=screenshot_name)
                    print(f"âŒ {full_title} - {error_msg}")

            def retry(func, retries=2, delay=1):
                for attempt in range(retries):
                    try:
                        return func()
                    except Exception as e:
                        if attempt == retries - 1:
                            raise
                        time.sleep(delay)
                        print(f"âš ï¸ Retry {attempt + 1} due to: {e}")

            # ==== Dashboard Automation Steps ====
            log_step("Open Seller.IM Dashboard", lambda: page.goto("https://seller.indiamart.com/", timeout=60000))
            time.sleep(2)

            # Close Payment popup if present
            def close_payment_popup_if_present():
                try:
                    popup = page.locator("div.SLC_tac.SLC_pr").first
                    if popup.is_visible():
                        page.locator("div.SLC_pa.SLC_cp.Rnw-ps").click()
                        time.sleep(1)
                except:
                    pass

            close_payment_popup_if_present()

            # Messages
            log_step("Click 'View All' in Messages", lambda: page.click("a#enq_stats_box_footer"))
            time.sleep(3)
            log_step("Return to Dashboard", lambda: page.click("#leftnav_dash_link"))
            time.sleep(3)

            # Relevant BuyLeads
            log_step("Click 'View All' in Relevant BuyLeads", lambda: page.click("a#buyLeadLink[href*='pref=relevant']"))
            log_step("Return to Dashboard", lambda: page.click("#leftnav_dash_link"))
            time.sleep(3)

            # Contact Buyer Flow
            def contact_buyer_flow():
                first_card = page.locator("ul#bl_stats_box_list li").first
                first_card.hover()
                time.sleep(1)
                contact_button = first_card.locator("a.stat_contact_button", has_text="Contact Buyer")
                if contact_button.is_visible():
                    contact_button.click()
                else:
                    raise Exception("Contact Buyer button not visible")
                page.wait_for_selector("div.popup-wrapper", timeout=5000)
                popup_header = page.locator("div.popup-wrapper h2.popup-heading")
                if not popup_header.is_visible() or popup_header.inner_text() != "Buy Lead Credit Low":
                    raise Exception("Expected 'Buy Lead Credit Low' popup not found.")
                credits_link = page.locator("div.popup-wrapper a", has_text="Purchase More Credits")
                credits_link.click()
                page.wait_for_url("**/onlinepayments/Pay/EtoSubscription**", timeout=10000)
                time.sleep(2)
                page.goto("https://seller.indiamart.com/dashboard")

            log_step("Hover, Contact Buyer & Redirect to Subscription", lambda: retry(contact_buyer_flow))
            log_step("Return to Dashboard Again", lambda: page.click("#leftnav_dash_link"))
            time.sleep(3)

            # Recent BuyLeads
            log_step("Click 'View All' in Recent BuyLeads", lambda: page.click("a#buyLeadLink[href*='pref=recent']"))
            time.sleep(3)
            log_step("Return to Dashboard Final", lambda: page.click("#leftnav_dash_link"))
            time.sleep(3)

            # Post Requirement
            log_step("Wait for BL Form to Load", lambda: page.wait_for_selector("#t0102_inlineBL", timeout=10000))
            log_step("Fill Product Name", lambda: page.fill("input#t0102prodtitle", "Jute Bag"))
            log_step("Click 'Submit Requirement'", lambda: page.click("input#t0102_submit"))
            time.sleep(1)
            log_step("Fill Quantity", lambda: page.fill("input#t0102txtbx_option1", "1"))
            log_step("Click First 'Next'", lambda: page.click("input#t0102_submit", force=True))
            time.sleep(2)
            log_step("Wait for 2nd Step", lambda: page.wait_for_selector("#t0102_submit", timeout=10000))
            log_step("Click Second 'Next'", lambda: page.click("#t0102_submit", force=True))
            def optional_final_submit():
                submit_button = page.query_selector("#t0102_submit")
                if submit_button and submit_button.get_attribute("value").strip().lower() == "submit":
                    page.click("#t0102_submit", force=True)
            log_step("Optional Final Submit", optional_final_submit)

        except Exception as e:
            print(f"ðŸ”¥ Critical Error in {browser_name}: {e}")
            if sheet_logger:
                sheet_logger.log_status(
                    f"[{browser_name}] Overall Script Failure",
                    "Fail",
                    str(e),
                    browser_name,
                    MOBILE_NUMBER,
                    run_time
                )
            page.screenshot(path=f"{browser_name}_Overall_Failure.png")

        finally:
            context.close()
            browser.close()
            print(f"âœ… {browser_name} test completed and browser closed")

    # Send Google Sheet summary email
    if sheet_logger:
        passed, failed, total = sheet_logger.get_summary_counts(run_time=run_time)
        send_summary_email(
            passed=passed,
            failed=failed,
            total=total,
            sheet_url=sheet_url,
            tab_name=tab_name,
            browser_results=browser_results
        )


with sync_playwright() as playwright:
    run(playwright)

