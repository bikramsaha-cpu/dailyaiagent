# Test Case: Check that on clicking the sign in as a different user the user lands on the enter mobile number
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect


def test_check_that_on_clicking_the_sign_in_as_a_different_user_the_user_lands_on_the_enter_mobile_number():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        # Navigate to the login/home screen
        page.goto("https://your-pbr-desktop-url.com")  # Replace with actual URL
        page.wait_for_load_state("networkidle")

        # Click on "Sign in as a different user" option
        sign_in_different_user = page.get_by_role("button", name="Sign in as a different user")
        if not sign_in_different_user.is_visible():
            sign_in_different_user = page.get_by_text("Sign in as a different user")
        sign_in_different_user.click()

        page.wait_for_load_state("networkidle")

        # Verify user lands on the login screen with mobile number input
        mobile_number_input = (
            page.get_by_placeholder("Enter mobile number")
            or page.get_by_label("Mobile number")
            or page.get_by_role("textbox", name="Mobile number")
        )

        # Try multiple locator strategies for the mobile number field
        mobile_input = page.get_by_placeholder("Enter mobile number")
        if not mobile_input.is_visible():
            mobile_input = page.get_by_label("Mobile number")
        if not mobile_input.is_visible():
            mobile_input = page.get_by_role("textbox", name="Mobile number")
        if not mobile_input.is_visible():
            mobile_input = page.get_by_placeholder("Mobile number")

        expect(mobile_input).to_be_visible()

        # Verify user is able to enter a new number
        mobile_input.click()
        mobile_input.fill("1234567890")
        expect(mobile_input).to_have_value("1234567890")

        context.close()
        browser.close()