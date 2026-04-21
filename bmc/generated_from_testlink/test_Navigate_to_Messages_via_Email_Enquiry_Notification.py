# Test Case: Navigate to Messages via Email Enquiry Notification
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect, Page
import re


def test_navigate_to_messages_via_email_enquiry_notification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        # Navigate to a common email provider inbox - using Gmail as example
        # The test assumes the user's email is accessible via the saved session
        page.goto("https://mail.google.com/mail/u/0/#inbox")
        page.wait_for_load_state("networkidle")

        # Search for IndiaMART enquiry email in inbox
        search_box = page.get_by_role("searchbox", name=re.compile("search", re.IGNORECASE))
        if not search_box.is_visible():
            search_box = page.locator('input[aria-label*="Search"]').first
        
        search_box.click()
        search_box.fill("IndiaMART Enquiry")
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Look for IndiaMART enquiry email in search results
        enquiry_email = page.get_by_role("row").filter(
            has_text=re.compile("enquiry|Enquiry|IndiaMART", re.IGNORECASE)
        ).first

        # If search didn't work, try browsing inbox directly
        if not enquiry_email.is_visible():
            page.goto("https://mail.google.com/mail/u/0/#inbox")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            enquiry_email = page.get_by_role("row").filter(
                has_text=re.compile("enquiry|Enquiry|IndiaMART", re.IGNORECASE)
            ).first

        expect(enquiry_email).to_be_visible(timeout=10000)

        # Open the enquiry email
        enquiry_email.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Verify email content is visible with enquiry details
        email_body = page.locator(".a3s, .gmail_quote, [data-message-id]").first
        if not email_body.is_visible():
            email_body = page.locator("div[role='main']")
        
        expect(email_body).to_be_visible(timeout=10000)

        # Look for "Chat with seller" CTA button inside the email
        chat_with_seller_btn = page.get_by_role("link", name=re.compile("chat with seller", re.IGNORECASE))
        
        if not chat_with_seller_btn.is_visible():
            chat_with_seller_btn = page.get_by_role("button", name=re.compile("chat with seller", re.IGNORECASE))
        
        if not chat_with_seller_btn.is_visible():
            chat_with_seller_btn = page.locator("a", has_text=re.compile("chat with seller", re.IGNORECASE)).first
        
        if not chat_with_seller_btn.is_visible():
            chat_with_seller_btn = page.locator("a", has_text=re.compile("chat|seller|enquiry", re.IGNORECASE)).first

        expect(chat_with_seller_btn).to_be_visible(timeout=10000)

        # Click on "Chat with seller" CTA - handle new tab/window opening
        with context.expect_page() as new_page_info:
            chat_with_seller_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        # Verify user is redirected to IndiaMART website
        expect(new_page).to_have_url(re.compile(r"indiamart\.com", re.IGNORECASE), timeout=15000)

        # Verify messages/chat page is loaded
        messages_indicator = new_page.locator(
            "text=Messages, text=Chat, text=Enquiry, [class*='message'], [class*='chat']"
        ).first
        
        if not messages_indicator.is_visible():
            # Check URL contains messages or chat path
            current_url = new_page.url
            assert re.search(r"message|chat|enquiry", current_url, re.IGNORECASE), \
                f"Expected to be on messages/chat page but got URL: {current_url}"

        print(f"Successfully navigated to IndiaMART via email enquiry. URL: {new_page.url}")

        context.close()
        browser.close()


if __name__ == "__main__":
    test_navigate_to_messages_via_email_enquiry_notification()