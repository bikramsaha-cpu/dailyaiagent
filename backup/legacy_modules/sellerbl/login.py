import asyncio
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def login_and_save_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()
        # Create directory for session storage
        session_dir = "/var/log/web_tester_logs/"
        os.makedirs(session_dir, exist_ok=True)

        # Fixed filename for reusability
        session_file_path = os.path.join(session_dir, "seller_bllogin.json")

        # Step 1: Go to login page
        print("ðŸ”— Navigating to buyer.indiamart.com...")
        page.goto("https://buyer.indiamart.com/")

        # Step 2: Fill mobile number
        print("ðŸ“± Entering mobile number...")
        page.wait_for_selector("input#mobilemy", timeout=10000)
        page.fill("input#mobilemy", "9643193481")

        # Step 3: Click on Send OTP
        print("ðŸ“¨ Clicking 'Send OTP'...")
        page.click("input#signInSubmitButton")

        # Step 4: Auto-fill OTP instead of waiting manually
        try:
            print("ðŸ”¢ Entering OTP '1956'...")
            otp_input = page.wait_for_selector("input[placeholder='----']", timeout=10000)
            otp_input.fill("1956")
        except PlaywrightTimeoutError:
            print("âŒ OTP input not found.")
            browser.close()
            return

        # Step 5: Click on Verify OTP
        try:
            print("âœ… Clicking 'Verify OTP'...")
            page.click("input#signInSubmitButton[value='Verify OTP']")
        except PlaywrightTimeoutError:
            print("âŒ Could not find 'Verify OTP' button.")
            page.screenshot(path="verify_otp_missing.png", full_page=True)
            browser.close()
            return

        # Step 6: Wait for post-login indicator
        try:
            print("ðŸ” Waiting for post-login confirmation...")
            page.wait_for_selector("text=Hi", timeout=15000)  # Adjust selector if needed
            print("ðŸ” OTP Verified and login successful.")
        except PlaywrightTimeoutError:
            print("âš ï¸ Login not confirmed. Session may not be saved.")
            page.screenshot(path="login_not_confirmed.png", full_page=True)
            browser.close()
            return

        # Step 7: Save session state
        context.storage_state(path=session_file_path)
        print("âœ… Login session saved to login.json")

        browser.close()

login_and_save_session()

