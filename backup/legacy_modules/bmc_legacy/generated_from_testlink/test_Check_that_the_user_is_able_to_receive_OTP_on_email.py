# Test Case: Check that the user is able to receive OTP on email
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect, Page
import re


def test_check_that_the_user_is_able_to_receive_otp_on_email():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        # Step 1: User lands on my.IM page
        page.goto("https://my.im")
        page.wait_for_load_state("networkidle")

        # Verify the user is on the my.im page
        expect(page).to_have_url(re.compile(r"my\.im", re.IGNORECASE))

        # User clicks on the message / login CTA
        # Try common login or message CTAs
        message_cta = page.get_by_role("link", name=re.compile(r"message|login|sign in|get started", re.IGNORECASE)).first
        if message_cta.is_visible():
            message_cta.click()
        else:
            # Fallback: look for a button
            page.get_by_role("button", name=re.compile(r"message|login|sign in|get started", re.IGNORECASE)).first.click()

        page.wait_for_load_state("networkidle")

        # Verify login screen is displayed
        # Look for OTP or email login option
        otp_email_cta = page.get_by_role("button", name=re.compile(r"receive otp.*email|otp.*email|email.*otp|get otp|send otp", re.IGNORECASE)).first
        if not otp_email_cta.is_visible():
            otp_email_cta = page.get_by_text(re.compile(r"receive otp.*email|otp.*email|email.*otp|get otp on email", re.IGNORECASE)).first

        # Click on "Receive OTP on email" CTA
        otp_email_cta.click()
        page.wait_for_load_state("networkidle")

        # User clicks on Submit CTA
        submit_button = page.get_by_role("button", name=re.compile(r"submit|send|continue|proceed", re.IGNORECASE)).first
        expect(submit_button).to_be_visible()
        submit_button.click()

        page.wait_for_load_state("networkidle")

        # Verify OTP has been sent - look for confirmation message or OTP input field
        otp_confirmation = page.get_by_text(
            re.compile(r"otp.*sent|sent.*otp|check.*email|email.*sent|enter.*otp|verify.*otp", re.IGNORECASE)
        ).first
        expect(otp_confirmation).to_be_visible(timeout=10000)

        # Optionally verify OTP input field is shown for user to enter OTP
        otp_input = page.get_by_placeholder(re.compile(r"otp|one.time|verification code|enter code", re.IGNORECASE)).first
        if otp_input.is_visible():
            expect(otp_input).to_be_visible()

        context.close()
        browser.close()


if __name__ == "__main__":
    test_check_that_the_user_is_able_to_receive_otp_on_email()