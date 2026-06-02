from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import sys
import os
import time

# Import logger_instance safely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from logger_instance import logger
except ImportError:
    logger = None

# --- Config ---
AUTH_FILE = "/var/log/web_tester_logs/lmslogin.json"
BROWSERS = ["chromium", "firefox"]   # Run on Chromium & Firefox
MOBILE_NUMBER = "9643193481"
SEARCH_QUERY = "Raj Furnitures"
SELLER_MC_URL = "https://seller.indiamart.com/messagecentre"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Seller MC Search-by-Name test on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=50)
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name} âœ…")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                # Do not raise -> continue test

        # Step 1: Open Seller Message Centre
        log_step("Open Seller Message Centre", lambda: page.goto(SELLER_MC_URL, wait_until="domcontentloaded", timeout=60000))

        # Step 2: Wait for search box and search
        def perform_search():
            search_input_selector = "input#searchauto"
            page.wait_for_selector(search_input_selector, timeout=15000)
            page.click(search_input_selector)
            page.fill(search_input_selector, SEARCH_QUERY)
            page.keyboard.press("Enter")
            time.sleep(3)
        log_step(f"Search for Contact: {SEARCH_QUERY}", perform_search)

        # Step 3: Validate contact names in left panel
        def check_contact_names():
            contact_name_selector = "aside#lms_left_listing .wrd_elip.fl.fs14.fwb.maxwidth100m200"
            page.wait_for_selector(contact_name_selector, timeout=10000)
            names = page.locator(contact_name_selector)
            name_count = names.count()
            print(f"ðŸ” Total contacts found: {name_count}")

            found = False
            for i in range(name_count):
                name = names.nth(i).inner_text().strip()
                print(f"  #{i + 1}: {name}")
                if SEARCH_QUERY.lower() in name.lower():
                    found = True
                    break

            if not found:
                raise AssertionError(f"âŒ Contact '{SEARCH_QUERY}' NOT found in the left panel.")
            print(f"âœ… Contact '{SEARCH_QUERY}' found in the left panel.")
        log_step("Validate Contact Name in Left Panel", check_contact_names)

        # Step 4: Test completion
        log_step("Test Completion", lambda: print("ðŸŽ¯ Seller MC Search-by-Name test completed."))

        # Cleanup
        context.close()
        browser.close()
        print(f"âœ… {browser_name} Seller MC test completed and browser closed")

    # --- Final Summary ---
    print("\nðŸ“Š Test Summary:")
    for browser, results in browser_results.items():
        print(f"  {browser}: âœ… {results['Pass']} passed | âŒ {results['Fail']} failed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
