from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import os
import sys
import time

# âœ… Import custom Google Sheet logger
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from google_logger import GoogleSheetLogger  # Custom Google Sheet logger

# ----------------------- Configuration ----------------------- #
MOBILE_NUMBER = "9643193481"
BROWSERS = ["chromium", "firefox"]
session_file_path = "/var/log/web_tester_logs/buyermylogin.json"
BUYER_DASHBOARD_URL = "https://buyer.indiamart.com"
TEST_CASE_NAME = os.path.basename(__file__).replace(".py", "")
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


# ----------------------- Helper Functions ----------------------- #
def navigate_to_dashboard(page):

        """Navigate to Buyer Dashboard"""
        page.goto(BUYER_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
        print("âœ… Navigated to Buyer Dashboard")
        time.sleep(2)


def click_profile_icon(page):
    """Click on Profile Icon"""
    page.click('//*[@id="lshead"]/a/span')
    print("âœ… Profile icon clicked successfully")


def click_my_orders(page):
    """Click on My Orders"""
    page.click('//*[@id="sntid"]/a[5]')
    print("âœ… Navigated to My Orders")

#### start interest ######
def click_product_of_interest(page):
    """Click on Product of Interest"""
    page.click('//*[@id="productofInterest"]')
    print("âœ… Clicked Product of Interest")

    """Click Get Best Price button"""
    page.click("a.btnn")
    page.wait_for_timeout(2000)
    print("âœ… Clicked Get Best Price successfully")

    

    for _ in range(10):
        if page.is_visible('input#t0901_submit'):
            break
        next_buttons = page.locator('//button[contains(text(), "Next")]')
        if next_buttons.count() > 0:
            next_buttons.nth(0).click()
            page.wait_for_timeout(1000)
        else:
            break
    print("âœ… Navigation completed till Submit button")

    page.wait_for_selector('input#t0901_submit', timeout=10000)
    page.click('input#t0901_submit')
    page.wait_for_selector('div#t0901_cls', timeout=5000)
    page.click('div#t0901_cls')
    print("âœ… Submitted form and closed popup")

def chat_with_seller(page, context):
    """Chat with seller in new tab"""
    with context.expect_page() as new_page_info:
        page.click('//*[@id="t0901msglink"]')
    new_tab = new_page_info.value
    new_tab.wait_for_load_state()
    new_tab.close()
    page.bring_to_front()
    print("âœ… Chat with Seller flow executed successfully")

    page.click('div#t0901_cls.ber-cls-rec.cp')
    print("âœ… Closed popup successfully")

    page.click('//*[@id="myOrderTab"]')
    print("âœ… Clicked My Orders again")
#### end interest ######

#### start categories ######

def click_recommended_categories(page):
    """Click Recommended Categories"""
    page.click('//*[@id="recommendedCategories"]')
    print("âœ… Clicked Recommended Categories")
    
    page.click('//a[contains(@class, "btnn") and contains(text(), "Get Quotes")]')
    page.click('//*[@id="t0901_rightsection"]/div/div/div[4]/button')
    page.click('//*[@id="t0901_rightsection"]/div/div[3]/input')
    page.click('//*[@id="t0901_submit"]')
    page.wait_for_selector('div#t0901_cls', timeout=5000)
    page.click('div#t0901_cls')
    print("âœ… Get Quotes flow completed successfully")

#### start categories ######

def click_recent_activity(page):
    """Click Recent Activity"""
    page.click('//*[@id="recentActivities"]')
    page.wait_for_timeout(2000)
    print("âœ… Recent Activity opened")


def open_past_search(page, context):
    """Open product from Past Searches"""
    page.click('//*[@id="pastSearches"]')
    href = page.get_attribute('//*[@id="y_apparel"]/div/a[1]', 'href')
    if href:
        new_page = context.new_page()
        new_page.goto(href)
        new_page.wait_for_load_state()
        new_page.close()
        print("âœ… Past Search opened in new tab")
    else:
        raise Exception("No href found for past search")


def click_indiamart_logo(page):
    """Click IndiaMART logo to return home"""
    page.click('//*[@id="header"]/div/a')
    print("âœ… Returned to home via logo")


# ----------------------- Main Run Function ----------------------- #
def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logger = None
    tab_name = "Buyermy"

    # Initialize Google Sheet logger
    try:
        sheet_logger = GoogleSheetLogger("Buyer Automation", tab_name)
        print("âœ… GoogleSheetLogger initialized successfully")
    except Exception as e:
        print(f"âš ï¸ Google Sheet logging disabled: {e}")

    # Validate session
    if not os.path.exists(session_file_path):
        print(f"âŒ Session file not found: {session_file_path}")
        print("ðŸ‘‰ Please run the 'save_session.py' script first to create it.")
        return

    # Screenshot folder
    screenshot_dir = "/var/log/web_tester_logs" 

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Buyer Dashboard - My Orders Flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=200)
        context = browser.new_context(storage_state=session_file_path)
        page = context.new_page()

        def log_step(step_name, func):
            """Unified logging for each step"""
            full_title = step_name
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name}")
                if sheet_logger:
                    sheet_logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                try:
                    screenshot_path = os.path.join(
                        screenshot_dir, f"{browser_name}_{step_name.replace(' ', '_')}.png"
                    )
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[Fail] {step_name}: {error_msg} (Screenshot saved: {screenshot_path})")
                except Exception as se:
                    print(f"[Fail] {step_name}: {error_msg} (Screenshot failed: {se})")

                if sheet_logger:
                    sheet_logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                # Continue execution even after failure (remove 'raise' if you want to continue)
                # raise

        # ----------------------- Test Steps ----------------------- #
        log_step("Navigate to My order scetion", lambda: navigate_to_dashboard(page))
        log_step("Verify Navigation of Click Profile Icon", lambda: click_profile_icon(page))
        log_step("Verify Navigation of Click My Orders", lambda: click_my_orders(page))
        #log_step("Verify Navigation of Click Recommended Categories", lambda: click_recommended_categories(page))

        
       
       
        log_step("Verify Navigation of Click Recent Activity", lambda: click_recent_activity(page))
        log_step("Verify Navigation of Open Past Search", lambda: open_past_search(page, context))

        # Close context and browser
        context.close()
        browser.close()
        print(f"âœ… {browser_name} test completed and browser closed")

    # ----------------------- Final Summary ----------------------- #
    print("\nðŸŽ¯ Final Results Summary:")
    for browser, results in browser_results.items():
        print(f"{browser}: âœ… {results['Pass']} Passed | âŒ {results['Fail']} Failed")


# ----------------------- Entry Point ----------------------- #
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

