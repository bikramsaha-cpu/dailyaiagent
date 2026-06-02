# Test Case: Check that the user is displayed an error message when enters an invalid number
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect, Page, BrowserContext
import re

def test_check_that_the_user_is_displayed_an_error_message_when_enters_an_invalid_number():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        page.goto("https://your-pbr-desktop-url.com")  # Replace with actual URL

        invalid_numbers = [
            "0123456789",  # starts with 0
            "2123456",     # starts with 2, less than 10 digits
            "312345",      # starts with 3, less than 10 digits
            "412345",      # starts with 4, less than 10 digits
            "512345",      # starts with 5, less than 10 digits
            "123456789",   # valid start but less than 10 digits
        ]

        for invalid_number in invalid_numbers:
            # Try to find the phone/number input field by common labels or placeholders
            number_input = None

            # Try various locator strategies
            for locator_attempt in [
                page.get_by_label(re.compile(r"number|phone|mobile", re.IGNORECASE)),
                page.get_by_placeholder(re.compile(r"number|phone|mobile|enter", re.IGNORECASE)),
                page.get_by_role("textbox", name=re.compile(r"number|phone|mobile", re.IGNORECASE)),
            ]:
                try:
                    if locator_attempt.count() > 0:
                        number_input = locator_attempt.first
                        break
                except Exception:
                    continue

            if number_input is None:
                # Fallback: use the first visible textbox
                number_input = page.get_by_role("textbox").first

            # Clear and fill the input with invalid number
            number_input.clear()
            number_input.fill(invalid_number)
            number_input.press("Tab")  # Trigger validation

            # Check for error message
            error_message = page.locator(
                "text=/invalid|error|incorrect|not valid|must be|required|digits/i"
            )

            # Also try common error element patterns
            error_locators = [
                page.locator(".error-message"),
                page.locator(".error"),
                page.locator("[class*='error']"),
                page.locator("[class*='invalid']"),
                page.locator("[role='alert']"),
                page.get_by_text(re.compile(r"invalid|error|incorrect|not valid|must be|10 digits", re.IGNORECASE)),
            ]

            error_found = False
            for err_loc in error_locators:
                try:
                    if err_loc.count() > 0 and err_loc.first.is_visible():
                        error_found = True
                        print(f"Error message found for input '{invalid_number}': {err_loc.first.text_content()}")
                        break
                except Exception:
                    continue

            assert error_found, (
                f"Expected an error message for invalid number '{invalid_number}', but none was displayed."
            )

            # Clear input for next iteration
            number_input.clear()

        context.close()
        browser.close()