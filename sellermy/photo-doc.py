from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import time

# Setup log folder
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
today = datetime.now().strftime("%Y-%m-%d")
log_file_path = os.path.join(log_dir, f"{today}.log")

def log(message):
    print(message)
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")

def navigate_tabs(page):
    try:
        # Tabs to visit in order (starting from Photos, skipping All Files)
        tabs = ["Photos", "PDFs", "Excel Sheets", "Word Docs", "Zip Files", "Other Files"]
        for tab in tabs:
            tab_selector = f"//strong[normalize-space(text())='{tab}']"
            page.wait_for_selector(tab_selector, timeout=5000)
            page.locator(tab_selector).click()
            log(f"📂 Navigated to: {tab}")
            time.sleep(2)  # Small delay to let content load
    except Exception as e:
        log(f"❌ Tab navigation failed: {e}")

def run(playwright):
    browser = playwright.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Step 1: Login
        page.goto("https://seller.indiamart.com/", timeout=60000)
        log("🌐 Opened Seller Portal")
        page.fill("input#mobNo", "9971305703")
        page.click("button.login_btn")
        page.get_by_text("Sign in with Password").nth(1).click(force=True)
        page.fill("input#usr_password", "12345678")
        page.click("input#signWP")
        log("🔐 Logged in successfully")
        page.wait_for_timeout(3000)

        # Step 2: Go to My Drive
        page.goto("https://seller.indiamart.com/workspace/mydrive", timeout=60000)
        log("📂 Navigated to My Photos & Documents")
        page.wait_for_timeout(3000)

        # Step 3: Navigate all tabs one by one
        navigate_tabs(page)

        log("✅ All tabs navigated successfully")

    except Exception as e:
        log(f"❌ Error: {e}")
    finally:
        log("✅ Execution complete")

# Run the script
with sync_playwright() as playwright:
    run(playwright)
