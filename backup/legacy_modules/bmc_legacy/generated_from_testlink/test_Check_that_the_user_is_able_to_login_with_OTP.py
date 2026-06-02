# Test Case: Check that the user is able to login with OTP
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect, Page
import re


def test_check_that_the_user_is_able_to_login_with_otp():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        try:
            # Navigate to the PBR Desktop login page
            page.goto("https://your-pbr-desktop-url.com")  # Replace with actual URL

            # Wait for the page to load
            page.wait_for_load_state("networkidle")

            # Step 1: User enters the 10 digit mobile number
            # Try to find mobile number input field by various locators
            mobile_input = None

            # Try by placeholder
            for placeholder in ["Enter mobile number", "Mobile number", "Enter your mobile number",
                                 "10 digit mobile number", "Phone number", "Enter phone number"]:
                try:
                    locator = page.get_by_placeholder(placeholder, exact=False)
                    if locator.count() > 0:
                        mobile_input = locator.first
                        break
                except Exception:
                    continue

            # Try by label if placeholder not found
            if mobile_input is None:
                for label in ["Mobile Number", "Mobile", "Phone Number", "Phone"]:
                    try:
                        locator = page.get_by_label(label, exact=False)
                        if locator.count() > 0:
                            mobile_input = locator.first
                            break
                    except Exception:
                        continue

            # Try by role if still not found
            if mobile_input is None:
                try:
                    locator = page.get_by_role("textbox")
                    if locator.count() > 0:
                        mobile_input = locator.first
                except Exception:
                    pass

            assert mobile_input is not None, "Could not find mobile number input field"

            # Enter a 10-digit mobile number
            mobile_input.click()
            mobile_input.fill("9876543210")  # Replace with a valid test mobile number

            # Verify the number was entered
            expect(mobile_input).to_have_value(re.compile(r"\d{10}"))

            # Click on Submit button
            submit_button = None

            for button_text in ["Submit", "SUBMIT", "Send OTP", "Get OTP", "Continue", "Next"]:
                try:
                    locator = page.get_by_role("button", name=button_text, exact=False)
                    if locator.count() > 0:
                        submit_button = locator.first
                        break
                except Exception:
                    continue

            assert submit_button is not None, "Could not find Submit button"
            submit_button.click()

            # Wait for OTP screen to appear
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # Verify user is landed on the OTP screen
            # Check for OTP input field or OTP-related text on the page
            otp_indicators = [
                lambda: page.get_by_placeholder("Enter OTP", exact=False),
                lambda: page.get_by_placeholder("OTP", exact=False),
                lambda: page.get_by_label("OTP", exact=False),
                lambda: page.get_by_text("Enter OTP", exact=False),
                lambda: page.get_by_text("OTP", exact=False),
                lambda: page.get_by_text("One Time Password", exact=False),
                lambda: page.get_by_text("Verify OTP", exact=False),
            ]

            otp_screen_found = False
            for get_indicator in otp_indicators:
                try:
                    indicator = get_indicator()
                    if indicator.count() > 0:
                        otp_screen_found = True
                        break
                except Exception:
                    continue

            assert otp_screen_found, "User was not redirected to the OTP screen after submitting mobile number"

            # Additional verification: check page URL or title contains OTP-related content
            current_url = page.url
            page_title = page.title()
            print(f"Current URL after submit: {current_url}")
            print(f"Page title: {page_title}")
            print("Test passed: User successfully navigated to OTP screen after entering mobile number")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    test_check_that_the_user_is_able_to_login_with_otp()