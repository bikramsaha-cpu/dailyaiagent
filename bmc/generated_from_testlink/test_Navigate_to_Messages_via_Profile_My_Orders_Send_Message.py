# Test Case: Navigate to Messages via Profile > My Orders > Send Message
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect


def test_navigate_to_messages_via_profile_my_orders_send_message():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        # Step 1: Navigate to IndiaMART desktop site
        page.goto("https://www.indiamart.com", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Step 2: Click on the Profile icon at the top right
        profile_icon = page.locator("#header-profile-icon, .profile-icon, [data-label='Profile'], .usr-lgn, #usr-lgn").first
        # Try multiple possible selectors for profile icon
        try:
            profile_icon.click(timeout=5000)
        except Exception:
            # Fallback: look for profile/account related element in header
            page.locator("xpath=//div[contains(@class,'profile') or contains(@id,'profile') or contains(@class,'user-icon')]").first.click()

        page.wait_for_timeout(1000)

        # Step 3: Select "My Orders" from the dropdown
        my_orders_link = page.get_by_role("link", name="My Orders")
        try:
            my_orders_link.wait_for(state="visible", timeout=5000)
            my_orders_link.click()
        except Exception:
            # Fallback using text
            page.get_by_text("My Orders", exact=True).first.click()

        page.wait_for_timeout(2000)

        # Step 4: Verify redirection to My Orders page
        expect(page).to_have_url(lambda url: "order" in url.lower(), timeout=10000)

        # Step 5: Locate an available order entry and find "Send Message" button
        page.wait_for_timeout(2000)

        # Look for "Send Message" button next to an order
        send_message_btn = page.get_by_role("button", name="Send Message").first
        try:
            send_message_btn.wait_for(state="visible", timeout=5000)
            send_message_btn.click()
        except Exception:
            # Fallback: try link with "Send Message" text
            try:
                page.get_by_role("link", name="Send Message").first.click()
            except Exception:
                # Fallback: locate by text
                page.locator("text=Send Message").first.click()

        page.wait_for_timeout(2000)

        # Step 6: Verify user is redirected to the Message module
        current_url = page.url
        assert (
            "message" in current_url.lower()
            or "chat" in current_url.lower()
            or "inbox" in current_url.lower()
            or page.locator("[class*='message'], [class*='chat'], [id*='message'], [id*='chat']").first.is_visible()
        ), f"Expected to be on Messages page, but current URL is: {current_url}"

        print(f"Successfully navigated to Messages module. Current URL: {page.url}")

        context.close()
        browser.close()


if __name__ == "__main__":
    test_navigate_to_messages_via_profile_my_orders_send_message()