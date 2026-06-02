from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import time
from google_logger import GoogleSheetLogger
from mailer import send_summary_email
from collections import defaultdict
import subprocess
import sys

# âœ… Session storage paths
AUTH_FILE = {
    "chromium": "/var/log/web_tester_logs/sellermylogin.json",
    "firefox": "/var/log/web_tester_logs/sellermylogin.json"
}

# âœ… Resolve sellerlogin.py path (always works, even if script run from outside folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SELLERLOGIN_PATH = os.path.join(BASE_DIR, "sellerlogin.py")

def ensure_sessions():
    """Check if session storage exists for all browsers, else run sellerlogin.py once."""
    needs_login = False

    for browser, path in AUTH_FILE.items():
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print(f"âš ï¸ No session found for {browser}.")
            needs_login = True

    if needs_login:
        print("âš ï¸ Running sellerlogin.py to create session file...")

        result = subprocess.run(
            [sys.executable, SELLERLOGIN_PATH],   # âœ… Works on Windows & Linux
            capture_output=True,
            text=True,
            errors="ignore"  # âœ… Prevent UnicodeEncodeError/DecodeError
        )

        print(result.stdout)
        if result.stderr:
            print("âš ï¸ Errors:", result.stderr)

        # Verify again after running sellerlogin
        for browser, path in AUTH_FILE.items():
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                raise RuntimeError(f"âŒ Session file still missing for {browser}: {path}")

        print("âœ… Session stored successfully for all browsers")

# Call this before starting Playwright automation
ensure_sessions()



log_dir = "/var/log/web_tester_logs/"
os.makedirs(log_dir, exist_ok=True)
today = datetime.now().strftime("%Y-%m-%d")
log_file_path = os.path.join(log_dir, f"{today}.log")

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "9643193481"
tab_name = "My Products"
sheet_url = "https://docs.google.com/spreadsheets/d/1s5QtTQ_naNwyg4CVb2Nt1Tg0HpRGxrt11sMNMvjvYVw/edit#gid=0"
run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

def log(message):
    print(message)
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")

def log_step(title, func, sheet_logger, browser_name):
    full_title = f"[{browser_name}] {title}"
    log(full_title)
    try:
        func()
        if sheet_logger:
            sheet_logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
        browser_results[browser_name]["Pass"] += 1
        print(f"âœ… {full_title}")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        if sheet_logger:
            sheet_logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
        browser_results[browser_name]["Fail"] += 1
        print(f"âŒ {full_title} - {error_msg}")


def run(playwright):
    try:
        sheet_logger = GoogleSheetLogger("Seller My Automation", tab_name)
    except:
        log("âš ï¸ Google Sheet logging is disabled")
        sheet_logger = None

    for browser_name in BROWSERS:
        log(f"\nðŸ§ª Running automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=100)

        # âœ… Use saved login session
        auth_file = AUTH_FILE[browser_name]
        context = browser.new_context(storage_state=auth_file)
        page = context.new_page()

        try:
            # âœ… Already logged-in session â†’ go directly to seller portal
            page.goto("https://seller.indiamart.com/", timeout=60000)
            log_step("Session Restored & Seller.IM Opened",
                     lambda: page.wait_for_selector("li#Manageproduct_tab", timeout=15000),
                     sheet_logger, browser_name)

            # Close payment popup if present
            def close_payment_popup_if_present():
                try:
                    popup = page.locator("div.SLC_tac.SLC_pr").first
                    if popup.is_visible():
                        print("âš ï¸ Payment popup detected. Closing...")
                        page.locator("div.SLC_pa.SLC_cp.Rnw-ps").click()
                        time.sleep(1)
                    else:
                        print("âœ… No payment popup detected.")
                except Exception as e:
                    print(f"â„¹ï¸ No payment popup to close: {e}")

            close_payment_popup_if_present()

            # ðŸ”½ Your Manage Product flow continues as-is
            page.click("li#Manageproduct_tab")
            page.wait_for_timeout(2000)

            try:
                page.wait_for_selector("button.popup-close-imcrp", timeout=10000)
                page.click("button.popup-close-imcrp")
                log_step("Popup closed", lambda: None, sheet_logger, browser_name)
            except:
                log_step("No popup shown", lambda: None, sheet_logger, browser_name)

            page.goto("https://seller.indiamart.com/product/manageproducts/", timeout=60000)
            page.wait_for_selector(".addPro.icon-sprite", timeout=20000)
            page.click(".addPro.icon-sprite")
            log_step("Add Product clicked", lambda: None, sheet_logger, browser_name)

            product_name = "Paracetamol" + datetime.now().strftime("%H%M%S")
            page.fill("#nameOfProduct", product_name)
            log_step(f"Product Name entered: {product_name}", lambda: None, sheet_logger, browser_name)

            try:
                if not page.is_visible("div.addPhotoPopupClass"):
                    page.click("img[src*='photo-camera.png']")
                page.wait_for_selector("h2:has-text('Add from Photos and Docs')", timeout=10000)
                page.locator("img.mpmydocsimgs").nth(2).click()
                page.get_by_role("button", name="Add photos").click()
                page.wait_for_selector("button.Crop_gCTA", timeout=10000)
                page.click("button.Crop_gCTA")
                page.wait_for_selector(".crp.multimg.is-visible", state="hidden", timeout=10000)
                log_step("Photo uploaded", lambda: None, sheet_logger, browser_name)
            except Exception as e:
                log_step(f"Photo upload failed: {e}", lambda: None, sheet_logger, browser_name)
                continue

            try:
                page.fill("#priceOfProduct", "100")
                page.wait_for_selector("li.SLC_cp.dynamic-li", timeout=5000)
                unit = page.locator("li.SLC_cp.dynamic-li").first
                unit.click()
                page.locator("#saveBasic").scroll_into_view_if_needed()
                page.click("#saveBasic")
                page.wait_for_selector("text=Specification/Additional Details", timeout=15000)
                log_step("Basic Info Saved", lambda: None, sheet_logger, browser_name)
            except Exception as e:
                log_step(f"Basic info save failed: {e}", lambda: None, sheet_logger, browser_name)

            try:
                isq_sections = page.locator(".keyConfigISQ")
                for i in range(isq_sections.count()):
                    label = isq_sections.nth(i)
                    first_option = label.locator("xpath=following::label[1]")
                    first_option.click()
                log_step("ISQs filled", lambda: None, sheet_logger, browser_name)
            except Exception as e:
                log_step(f"ISQ fill failed: {e}", lambda: None, sheet_logger, browser_name)

            try:
                for _ in range(20):
                    if not page.get_attribute("#save_isq", "disabled") and not page.locator("#saveISQLoader").is_visible():
                        break
                    time.sleep(1)
                page.click("#save_isq", force=True)
                log_step("Finish clicked", lambda: None, sheet_logger, browser_name)
            except Exception as e:
                log_step(f"Finish failed: {e}", lambda: None, sheet_logger, browser_name)

            # Step: Handle MCAT suggestion modal (if shown)
            def close_additional_products_popup():
                try:
                    page.wait_for_timeout(2000)
                    if page.is_visible("div#mpalertmodel7"):
                        heading_text = page.locator("div#mpalertmodel7 h1").inner_text(timeout=3000)
                        if "Additional products you can add" in heading_text:
                            page.click("button#closeLandingPopup", timeout=3000)
                            log("âœ… Additional Products popup closed")
                        else:
                            log("â„¹ï¸ Modal present, but different content â€” skipping close.")
                    else:
                        log("â„¹ï¸ No 'Additional Products' popup shown")
                except Exception as e:
                    log(f"âŒ Failed to close Additional Products popup: {e}")

            log_step("Handle Additional Products popup", close_additional_products_popup, sheet_logger, browser_name)

            try:
                if page.locator("button.save-btn", has_text="Add Selected Products To Catalog").is_visible():
                    page.click("button.save-btn")
                    log_step("Related MCAT clicked", lambda: None, sheet_logger, browser_name)
            except:
                log_step("Related MCAT popup not found", lambda: None, sheet_logger, browser_name)

            try:
                if page.locator("button#closeLandingPopup").is_visible():
                    page.click("button#closeLandingPopup")
                    log_step("MCAT popup closed", lambda: None, sheet_logger, browser_name)
            except:
                log_step("No MCAT close button", lambda: None, sheet_logger, browser_name)

            try:
                page.wait_for_url("**/manageproducts/**", timeout=30000)
                page.wait_for_timeout(3000)
                log_step("Redirected to Manage Products", lambda: None, sheet_logger, browser_name)
            except Exception as e:
                log_step(f"Redirect failed: {e}", lambda: None, sheet_logger, browser_name)

            def add_description():
                log("ðŸ“ Clicking 'Product Description'")
                page.wait_for_selector(".editdescDrop", timeout=10000)
                page.click(".editdescDrop", force=True)
                log("âœï¸ Description box opened")

                page.wait_for_selector(".mceEditor", timeout=10000)
                desc_editable = page.locator(".mceEditor")
                desc_editable.click()
                page.wait_for_timeout(500)

                page.keyboard.type(
                    "Paracetamol is a medicine used to treat mild to moderate pain. "
                    "Paracetamol can also be used to treat fever (high temperature). "
                    "It's dangerous to take more than the recommended dose of paracetamol. "
                    "Paracetamol overdose can damage your liver and cause death."
                )
                log("âœ… Description entered")

                page.click("button.savDesc")
                log("âœ… Description saved successfully")

            log_step("Product Description added", add_description, sheet_logger, browser_name)

        except Exception as e:
            log_step(f"Critical Error: {e}", lambda: None, sheet_logger, browser_name)
        finally:
            context.close()
            browser.close()
            log(f"âœ… {browser_name} test completed and browser closed")

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

