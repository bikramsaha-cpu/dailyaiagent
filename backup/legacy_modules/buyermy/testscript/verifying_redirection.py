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
TAB_NAME = "Buyermy"
SHEET_NAME = "Buyer Automation"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


# ----------------------- Helper: Log Step ----------------------- #
def create_logger():
    try:
        sheet_logger = GoogleSheetLogger(SHEET_NAME, TAB_NAME)
        print("âœ… GoogleSheetLogger initialized successfully")
        return sheet_logger
    except Exception as e:
        print("âš ï¸ Google Sheet logging is disabled:", str(e))
        return None


def log_step(page, sheet_logger, browser_name, step_name, status, run_time, message=""):
    full_title = step_name
    if sheet_logger:
        sheet_logger.log_status(
            full_title, status, message, browser_name, MOBILE_NUMBER, run_time
        )
    browser_results[browser_name][status] += 1
    if status == "Pass":
        print(f"âœ… {full_title}")
    else:
        print(f"âŒ {full_title} - {message}")
        screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}.png"
        page.screenshot(path=screenshot_name)


# ----------------------- Flow 1: More For You ----------------------- #
def more_for_you():
    
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logger = create_logger()
    print("\nðŸš€ Starting: 'More For You' flow")

    if not os.path.exists(SESSION_FILE_PATH):
        print(f"âŒ Session file '{SESSION_FILE_PATH}' not found!")
        print("ðŸ‘‰ Please run 'save_session.py' to create it.")
        return

    with sync_playwright() as playwright:
        for browser_name in BROWSERS:
            print(f"\nðŸ§ª Running on: {browser_name}")
            try:
                browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=300)
                context = browser.new_context(storage_state=SESSION_FILE_PATH)
                page = context.new_page()

                # Step 1: Navigate to More For You
                try:
                    page.goto("https://buyer.indiamart.com")
                    log_step(page, sheet_logger, browser_name, "Navigate to More For You Section", "Pass", run_time)
                except Exception as e:
                    log_step(page, sheet_logger, browser_name, "Navigate to Buyer More For You Section", "Fail", run_time, str(e))

                


                # Step 3: Click "Get Verified Seller"
                try:
                    print("âž¡ï¸ Clicking 'Get Verified Seller'")
                    with page.expect_popup() as popup_info:
                        page.click('//*[@id="root"]/div[1]/div[2]/div[2]/div[5]/div[2]/div/div/div/div[1]/div[2]/a[2]')
                        
                    popup = popup_info.value
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Verified Seller", "Pass", run_time)
                    popup.close()
                except Exception as e:
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Verified Seller", "Fail", run_time, str(e))

                # Step 4: Click IndiaMART Logo
                try:
                    print("âž¡ï¸ Clicking 'IndiaMART Logo'")
                    page.locator('//*[@id="header"]/div/a').click()
                    
                    
                except Exception as e:
                    print(f"[Fail] Click on indiamart logo: {browser_name} | Time: {run_time} | Error: {str(e)}")

                # Step 5: Click "Start Selling"
                try:
                    print("âž¡ï¸ Clicking 'Start Selling'")
                    with page.expect_popup() as popup_info:
                        page.locator('//*[@id="root"]/div[1]/div[2]/div[2]/div[5]/div[2]/div/div/div/div[2]/div[2]/a[2]').click()
                    popup = popup_info.value
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Start Selling", "Pass", run_time)
                    popup.close()
                except Exception as e:
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Start Selling", "Fail", run_time, str(e))

                # Step 6: Click "Download App"
                try:
                    print("âž¡ï¸ Clicking 'IndiaMART Logo'")
                    page.locator('//*[@id="header"]/div/a').click()

                    print("âž¡ï¸ Clicking 'Download App'")
                    page.locator('//*[@id="root"]/div[1]/div[2]/div[2]/div[5]/div[2]/div/div/div/div[3]/div[2]/button').click()

                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Download App Pop-up", "Pass", run_time)

                    page.locator('//*[@id="rgt_snd_lnk1"]').click()
                    page.locator('//*[@id="dialog"]/p').click()

                except Exception as e:
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Download App", "Fail", run_time, str(e))

                # Step 7: Click "Know More"
                try:

                    print("âž¡ï¸ Clicking 'IndiaMART Logo'")
                    page.locator('//*[@id="header"]/div/a').click()

                    print("âž¡ï¸ Clicking 'Know More'")
                    with page.expect_popup() as popup_info:
                        page.locator('//*[@id="root"]/div[1]/div[2]/div[2]/div[5]/div[2]/div/div/div/div[4]/div[2]/a[2]').click()
                        

                    popup = popup_info.value
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Know More", "Pass", run_time)
                    popup.close()
                except Exception as e:
                    log_step(page, sheet_logger, browser_name, "Verify Navigation of Know More", "Fail", run_time, str(e))

            finally:
                browser.close()
                print(f"ðŸ Completed {browser_name}: {browser_results[browser_name]}")

    print("\nðŸŽ¯ 'More For You' Flow Results:")
    for b, result in browser_results.items():
        print(f"{b}: {result['Pass']} Passed, {result['Fail']} Failed")



# ----------------------- Main Execution ----------------------- #
def main():
    
    more_for_you()
    


if __name__ == "__main__":
    main()

