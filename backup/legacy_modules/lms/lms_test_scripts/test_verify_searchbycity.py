from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import sys
import os
import time

# Import logger_instance from root level
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger

AUTH_FILE = "/var/log/web_tester_logs/lmslogin.json"
BROWSERS = ["chromium", "firefox"]
SEARCH_TERM = "pune"   # you can change this dynamically
MOBILE_NUMBER = "9643193481"
SELLER_MC_URL = "https://seller.indiamart.com/messagecentre"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running Seller MC Search test on: {browser_name}")
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
                screenshot_name = f"{browser_name}{step_name.replace(' ', '')}_{datetime.now().strftime('%H%M%S')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                # donâ€™t raise â†’ continue testing other steps

        # Step 1: Open LMS
        log_step("Open Seller Message Centre", lambda: page.goto(SELLER_MC_URL, wait_until="domcontentloaded", timeout=60000))

        # Step 2: Wait for search input
        log_step("Wait for Search Input", lambda: page.wait_for_selector("input#searchauto", timeout=30000))

        # Step 3: Perform search
        def search_city():
            search_input = page.locator("input#searchauto")
            search_input.click()
            search_input.fill(SEARCH_TERM)
            search_input.press("Enter")
            time.sleep(2)
        log_step(f"Search contacts with city {SEARCH_TERM}", search_city)

        # Step 4: Scroll until all contacts loaded
        def scroll_contacts():
            contact_list = page.locator("aside#lms_left_listing")
            prev_count = -1
            while True:
                rows = page.locator("aside#lms_left_listing .row")
                count = rows.count()
                if count == prev_count:
                    break
                prev_count = count
                contact_list.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                time.sleep(1.5)
        log_step("Scroll to load all contacts", scroll_contacts)

        # Step 5: Validate city OR name contains search term
        def validate_contacts():
            total_contacts = page.locator("aside#lms_left_listing .row").count()
            all_valid = True
            search_lower = SEARCH_TERM.lower()

            for i in range(total_contacts):
                row = page.locator("aside#lms_left_listing .row").nth(i)

                # Get city
                city_text = row.locator(".clr77.wrd_elip.wdcalc").inner_text().strip()
                city_only = city_text.split(',')[0].strip().lower()

                # Get contact/company name
                contact_name = row.locator(".wrd_elip.fl.fs14.fwb.maxwidth100m200").inner_text().strip().lower()

                # Rule: Pass if city matches OR contact name contains search term
                if city_only == search_lower or search_lower in contact_name:
                    continue
                else:
                    print(f"âŒ Invalid Contact â†’ Name: {contact_name}, City: {city_only}")
                    all_valid = False
                    break

            if all_valid:
                print(f"ðŸŽ‰ All contacts are valid for search term '{SEARCH_TERM.capitalize()}' âœ…")
            else:
                raise AssertionError(f"âŒ Some contacts donâ€™t match search rule for '{SEARCH_TERM.capitalize()}'")

        log_step("Validate Contact City/Name", validate_contacts)

        # Step 6: Test completion
        log_step("Test Completion", lambda: print("ðŸŽ¯ Seller MC Search test completed."))

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
