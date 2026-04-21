from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import os
import sys
import time

# âœ… Path setup for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from google_logger import GoogleSheetLogger  # Custom Google Sheet logger

# ----------------------- Configuration ----------------------- #
MOBILE_NUMBER = "9643193481"
BROWSERS = ["chromium", "firefox"]
SESSION_FILE_PATH = "/var/log/web_tester_logs/buyermylogin.json"
BUYER_DASHBOARD_URL = "https://buyer.indiamart.com"
TEST_CASE_NAME = os.path.basename(__file__).replace(".py", "")
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

# ----------------------- Helper Functions ----------------------- #

def navigate_to_dashboard(page):
    """Navigate to Buyer Dashboard"""
    page.goto(BUYER_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    print("âœ… Navigated to Buyer Dashboard successfully")
    time.sleep(2)

def click_footer_link(page, description, xpath, new_tab=False):
    """Click a footer link (supports new tab and same tab navigation)"""
    page.locator('xpath=//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div').scroll_into_view_if_needed()
    time.sleep(1)

    if new_tab:
        with page.context.expect_page() as new_page_info:
            page.locator(f'xpath={xpath}').click()
        new_tab_page = new_page_info.value
        new_tab_page.wait_for_load_state("domcontentloaded")
        print(f"ðŸ†• Opened new tab for: {description}")
        time.sleep(2)
        new_tab_page.close()
    else:
        page.locator(f'xpath={xpath}').click()
        print(f"âž¡ï¸ Navigated to: {description}")
        time.sleep(2)
        page.go_back()

    # Return via logo click for stability
    page.locator('xpath=//*[@id="header"]/div/a').click()
    time.sleep(1)
    print(f"âœ… Footer link '{description}' tested successfully")

# ----------------------- Footer Link Groups ----------------------- #
COMPANY_INFO_LINKS = [
    ("About Us", '//*[@id="sag"]/ul/li[1]/a[1]'),
    ("IndiaMART Export", '//*[@id="sag"]/ul/li[1]/a[2]'),
    ("Join Sales", '//*[@id="sag"]/ul/li[1]/a[3]'),
    ("Success Stories", '//*[@id="sag"]/ul/li[1]/a[4]'),
    ("Press Section", '//*[@id="sag"]/ul/li[1]/a[5]'),
    ("Advertise With Us", '//*[@id="sag"]/ul/li[1]/a[6]'),
]

HELP_AND_CONTACT_LINKS = [
    ("Jobs & Careers", '//*[@id="sag"]/ul/li[2]/a[1]'),
    ("Help", '//*[@id="sag"]/ul/li[2]/a[2]'),
    ("Feedback", '//*[@id="sag"]/ul/li[2]/a[3]'),
    ("Complaints", '//*[@id="sag"]/ul/li[2]/a[4]'),
    ("Customer Care", '//*[@id="sag"]/ul/li[2]/a[5]'),
    ("Contact Us", '//*[@id="sag"]/ul/li[2]/a[6]'),
]

SELLER_TOOLKIT_LINKS = [
    ("Seller Toolkit", '//*[@id="sag"]/ul/li[3]/div/a'),
    ("Sell on IndiaMART", '//*[@id="ch_free_web"]/a'),
    ("Latest BuyLeads", '//*[@id="sag"]/ul/li[3]/a[1]'),
    ("Learning Center", '//*[@id="sag"]/ul/li[3]/a[2]'),
]

BUYER_TOOLKIT_LINKS = [
    ("Buyer Toolkit", '//*[@id="sag"]/ul/li[4]/div/a'),
    ("Post Your Requirement", '//*[@id="sag"]/ul/li[4]/a[1]'),
    ("Product You Buy", '//*[@id="sag"]/ul/li[4]/a[2]'),
    ("Search Products & Suppliers", '//*[@id="sag"]/ul/li[4]/a[3]'),
]

ACCOUNTING_SOLUTIONS_LINKS = [
    ("Accounting Software", '//*[@id="sag"]/ul/li[5]/a[1]', True),
    ("Tally on Mobile", '//*[@id="sag"]/ul/li[5]/a[2]', True),
]

MOBILE_APPS_LINKS = [
    ("Apple App Store", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div/div[2]/a[1]', True),
    ("Google Play Store", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div/div[2]/a[2]', True),
    ("Mobile Buyer Page", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div/div[2]/a[3]', True),
]

SOCIAL_LINKS = [
    ("Facebook", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div/div[1]/a[1]', True),
    ("X (Twitter)", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div/div[1]/a[2]', True),
    ("LinkedIn", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[1]/div/div[1]/a[3]', True),
]

TERMS_AND_POLICIES_LINKS = [
    ("Terms of Use", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[3]/div/span[1]/a[1]'),
    ("Privacy Policy", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[3]/div/span[1]/a[2]'),
    ("Link With Us", '//*[@id="root"]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[3]/div/span[1]/a[3]'),
]

# ----------------------- Section Test Functions ----------------------- #
def test_company_info_links(page, log_step):
    for desc, xpath in COMPANY_INFO_LINKS:
        log_step(f"Verify Navigation of {desc}", lambda: click_footer_link(page, desc, xpath))

def test_help_and_contact_links(page, log_step):
    for desc, xpath in HELP_AND_CONTACT_LINKS:
        log_step(f"Verify Navigation of {desc}", lambda: click_footer_link(page, desc, xpath))

def test_seller_toolkit_links(page, log_step):
    for desc, xpath in SELLER_TOOLKIT_LINKS:
        log_step(f"Verify Navigation of {desc}", lambda: click_footer_link(page, desc, xpath))

def test_buyer_toolkit_links(page, log_step):
    for desc, xpath in BUYER_TOOLKIT_LINKS:
        log_step(f"Verify Navigation of {desc}", lambda: click_footer_link(page, desc, xpath))

def test_accounting_solutions_links(page, log_step):
    for desc, xpath, new_tab in ACCOUNTING_SOLUTIONS_LINKS:
        log_step(f"Verify Navigation of {desc}", lambda: click_footer_link(page, desc, xpath, new_tab))

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

    # Validate session file
    if not os.path.exists(SESSION_FILE_PATH):
        print(f"âŒ Session file not found: {SESSION_FILE_PATH}")
        print("ðŸ‘‰ Please run the 'save_session.py' script first to create it.")
        return

    # Screenshot folder
    screenshot_dir = "/var/log/web_tester_logs" 

    # ----------------------- Browser Loop ----------------------- #
    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Buyer Footer automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=200)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
        page = context.new_page()

        def log_step(step_name, func):
            """Unified logging for each CTA"""
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
                    screenshot_path = os.path.join(screenshot_dir, f"{browser_name}_{step_name.replace(' ', '_')}.png")
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[Fail] {step_name}: {error_msg} (Screenshot saved: {screenshot_path})")
                except Exception as se:
                    print(f"[Fail] {step_name}: {error_msg} (Screenshot failed: {se})")

                if sheet_logger:
                    sheet_logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)

        # ----------------------- Test Steps ----------------------- #
        log_step("Navigate to Footer Section", lambda: navigate_to_dashboard(page))

        # ðŸ§­ Organized Footer Tests
        test_company_info_links(page, log_step)
        test_help_and_contact_links(page, log_step)
        test_seller_toolkit_links(page, log_step)
        test_buyer_toolkit_links(page, log_step)
        test_accounting_solutions_links(page, log_step)


        # Close browser
        context.close()
        browser.close()
        print(f"âœ… {browser_name} footer test completed and browser closed")

    # ----------------------- Final Summary ----------------------- #
    print("\nðŸŽ¯ Final Results Summary:")
    for browser, results in browser_results.items():
        print(f"{browser}: âœ… {results['Pass']} Passed | âŒ {results['Fail']} Failed")

# ----------------------- Entry Point ----------------------- #
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

