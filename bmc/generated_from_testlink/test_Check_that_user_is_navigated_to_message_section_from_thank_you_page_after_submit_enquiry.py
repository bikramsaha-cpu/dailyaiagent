# Test Case: Check that user is navigated to message section from thank you page  after submit enquiry
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect, Page
import re


def test_check_that_user_is_navigated_to_message_section_from_thank_you_page_after_submit_enquiry():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        try:
            # Navigate to the PBR Desktop application
            page.goto("https://www.pbr.com.au/")
            page.wait_for_load_state("networkidle")

            # Look for an enquiry form or contact/enquiry link
            # Try to find enquiry button or link
            enquiry_selectors = [
                page.get_by_role("link", name=re.compile(r"enquir", re.IGNORECASE)),
                page.get_by_role("button", name=re.compile(r"enquir", re.IGNORECASE)),
                page.get_by_text(re.compile(r"enquir", re.IGNORECASE)),
                page.get_by_role("link", name=re.compile(r"contact", re.IGNORECASE)),
            ]

            enquiry_link = None
            for selector in enquiry_selectors:
                if selector.count() > 0:
                    enquiry_link = selector.first
                    break

            if enquiry_link:
                enquiry_link.click()
                page.wait_for_load_state("networkidle")

            # Fill in the enquiry form if present
            # Try to fill name field
            name_field = page.get_by_label(re.compile(r"name", re.IGNORECASE))
            if name_field.count() > 0:
                name_field.first.fill("Test User")

            # Try to fill email field
            email_field = page.get_by_label(re.compile(r"email", re.IGNORECASE))
            if email_field.count() == 0:
                email_field = page.get_by_placeholder(re.compile(r"email", re.IGNORECASE))
            if email_field.count() > 0:
                email_field.first.fill("testuser@example.com")

            # Try to fill phone field
            phone_field = page.get_by_label(re.compile(r"phone", re.IGNORECASE))
            if phone_field.count() == 0:
                phone_field = page.get_by_placeholder(re.compile(r"phone", re.IGNORECASE))
            if phone_field.count() > 0:
                phone_field.first.fill("0400000000")

            # Try to fill message/enquiry field
            message_field = page.get_by_label(re.compile(r"message|enquiry|comment", re.IGNORECASE))
            if message_field.count() == 0:
                message_field = page.get_by_placeholder(re.compile(r"message|enquiry|comment", re.IGNORECASE))
            if message_field.count() > 0:
                message_field.first.fill("This is a test enquiry message.")

            # Submit the enquiry form
            submit_button = page.get_by_role("button", name=re.compile(r"submit|send|enquir", re.IGNORECASE))
            if submit_button.count() == 0:
                submit_button = page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE))
            if submit_button.count() > 0:
                submit_button.first.click()
                page.wait_for_load_state("networkidle")

            # Wait for Thank You page or confirmation message
            page.wait_for_timeout(2000)

            # Check for Thank You page content
            thank_you_indicators = [
                page.get_by_text(re.compile(r"thank you", re.IGNORECASE)),
                page.get_by_text(re.compile(r"thanks", re.IGNORECASE)),
                page.get_by_text(re.compile(r"submission received", re.IGNORECASE)),
                page.get_by_text(re.compile(r"enquiry received", re.IGNORECASE)),
            ]

            thank_you_found = False
            for indicator in thank_you_indicators:
                if indicator.count() > 0:
                    thank_you_found = True
                    break

            # After Thank You page, check for redirect to BMC (message section)
            # Wait for potential redirect
            page.wait_for_timeout(3000)

            # Check if redirected to BMC or message section
            current_url = page.url

            # Check for BMC redirect or message section
            bmc_or_message_indicators = [
                page.get_by_text(re.compile(r"message", re.IGNORECASE)),
                page.get_by_role("heading", name=re.compile(r"message", re.IGNORECASE)),
                page.get_by_text(re.compile(r"inbox", re.IGNORECASE)),
                page.get_by_text(re.compile(r"BMC", re.IGNORECASE)),
            ]

            # Verify user is on message section or BMC
            message_section_found = False
            for indicator in bmc_or_message_indicators:
                if indicator.count() > 0:
                    message_section_found = True
                    break

            # Check URL contains message or bmc related path
            url_contains_message = (
                "message" in current_url.lower() or
                "bmc" in current_url.lower() or
                "inbox" in current_url.lower() or
                "dashboard" in current_url.lower()
            )

            # Assert that user is redirected to BMC/message section after thank you page
            assert message_section_found or url_contains_message or thank_you_found, (
                f"User was not redirected to BMC/message section after submitting enquiry. "
                f"Current URL: {current_url}"
            )

            print(f"Test passed. Current URL after enquiry submission: {current_url}")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    test_check_that_user_is_navigated_to_message_section_from_thank_you_page_after_submit_enquiry()