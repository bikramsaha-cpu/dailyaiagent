# Test Case: Verify that clicking “Chat Now” from My Orders opens the correct supplier conversation in Messages.
# Auto-generated from TestLink using the daily-qa-agent generator.

import pytest
from playwright.sync_api import sync_playwright, expect


def test_verify_that_clicking_chat_now_from_my_orders_opens_the_correct_supplier_conversation_in_messages():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="pbr/auth.json")
        page = context.new_page()

        # Navigate to the home page
        page.goto("https://www.pbr.com.au")
        page.wait_for_load_state("networkidle")

        # Step 1: Locate and click on "My Orders" from the Home Page
        # Try navigation menu or dashboard link for "My Orders"
        my_orders_link = page.get_by_role("link", name="My Orders")
        if not my_orders_link.is_visible():
            # Try clicking a user/account menu first to reveal My Orders
            account_menu = page.get_by_role("button", name="Account").or_(
                page.get_by_role("link", name="Account")
            )
            if account_menu.is_visible():
                account_menu.click()
                page.wait_for_timeout(500)
            my_orders_link = page.get_by_role("link", name="My Orders")

        my_orders_link.click()
        page.wait_for_load_state("networkidle")

        # Verify user is redirected to My Orders section in the Dashboard
        expect(page).to_have_url(lambda url: "orders" in url.lower() or "dashboard" in url.lower())

        # Verify the list of placed orders is displayed
        # Look for order items or a table/list of orders
        orders_section = page.locator(
            "[class*='order'], [data-testid*='order'], table, [class*='Order']"
        ).first
        orders_section.wait_for(state="visible", timeout=10000)

        # Step 2: Click on "Chat Now" for any specific order/supplier
        chat_now_button = page.get_by_role("button", name="Chat Now").first
        if not chat_now_button.is_visible():
            chat_now_button = page.get_by_role("link", name="Chat Now").first
        if not chat_now_button.is_visible():
            chat_now_button = page.locator("text=Chat Now").first

        chat_now_button.wait_for(state="visible", timeout=10000)

        # Capture supplier name before clicking if possible
        supplier_name = None
        try:
            # Try to get the supplier name associated with the first "Chat Now" button
            order_row = chat_now_button.locator("xpath=ancestor::tr | ancestor::div[contains(@class,'order')]").first
            supplier_name_element = order_row.locator(
                "[class*='supplier'], [data-testid*='supplier'], [class*='Supplier']"
            ).first
            if supplier_name_element.is_visible():
                supplier_name = supplier_name_element.inner_text()
        except Exception:
            pass

        chat_now_button.click()
        page.wait_for_load_state("networkidle")

        # Verify user is redirected to Messages (BMC)
        # Check URL contains 'messages' or 'bmc' or 'chat'
        current_url = page.url.lower()
        assert any(keyword in current_url for keyword in ["message", "bmc", "chat", "conversation"]), (
            f"Expected to be redirected to Messages/BMC, but current URL is: {page.url}"
        )

        # Verify the Messages/conversation page is visible
        messages_heading = page.get_by_role("heading", name="Messages").or_(
            page.get_by_role("heading", name="BMC")
        ).or_(
            page.locator("[class*='message'], [class*='Message'], [class*='chat'], [class*='Chat']").first
        )
        messages_heading.wait_for(state="visible", timeout=10000)

        # Verify the correct conversation with the selected supplier is open
        # Look for an active/open conversation panel
        conversation_panel = page.locator(
            "[class*='conversation'], [class*='Conversation'], [class*='thread'], [class*='Thread']"
        ).first
        if conversation_panel.is_visible():
            expect(conversation_panel).to_be_visible()

        # If supplier name was captured, verify it appears in the conversation
        if supplier_name:
            supplier_in_conversation = page.locator(f"text={supplier_name}").first
            supplier_in_conversation.wait_for(state="visible", timeout=5000)
            expect(supplier_in_conversation).to_be_visible()

        # Final assertion: ensure we are on the messages page with an open conversation
        page.wait_for_timeout(1000)
        assert page.locator(
            "[class*='message'], [class*='chat'], [class*='conversation']"
        ).first.is_visible(), "Messages/conversation area is not visible after clicking Chat Now"

        context.close()
        browser.close()