from playwright.sync_api import sync_playwright
from collections import defaultdict
from datetime import datetime
import sys
import os
import time

# Add parent folder for logger_instance import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger  # Your custom logger

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = "7385475125"
SELLER_IM_URL = "https://seller.indiamart.com/"
MESSAGE = "Hello, this is an automated test message!"

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})

def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nðŸ§ª Running 'Search OPC 43 Grade Cement' automation on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=200)
        context = browser.new_context()
        page = context.new_page()

        def log_step(step_name, func):
            full_title = f"[{browser_name}] {step_name}"
            try:
                func()
                browser_results[browser_name]["Pass"] += 1
                print(f"[Pass] {step_name} completed successfully")
                if logger:
                    logger.log_status(full_title, "Pass", "", browser_name, MOBILE_NUMBER, run_time)
            except Exception as e:
                browser_results[browser_name]["Fail"] += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                screenshot_name = f"{browser_name}_{step_name.replace(' ', '')}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"[Fail] {step_name}: {error_msg} (Screenshot saved as {screenshot_name})")
                if logger:
                    logger.log_status(full_title, "Fail", error_msg, browser_name, MOBILE_NUMBER, run_time)
                raise

        # Step 1: Open Seller.IM
        log_step("Open Seller.IM", lambda: page.goto(SELLER_IM_URL, timeout=60000))
        time.sleep(2)

        # Step 2: Login with mobile number and password
        page.fill("input#mobNo", "7385475125")
        page.click("button.login_btn")
        page.get_by_text("Sign in with Password").nth(1).click(force=True)
        page.fill("input#usr_password", "imtester123")
        log_step("Click on Signin With Password", lambda: page.click("input#signWP"))
        time.sleep(3)
        page.wait_for_timeout(3000)

        # Step 3: Open Message Centre
        MESSAGE_CENTRE_URL = "https://buyer.indiamart.com/enquiry/messagecentre/"
        log_step(
            "Open Message Centre",
            lambda: page.goto(MESSAGE_CENTRE_URL, wait_until="domcontentloaded", timeout=60000)
        )

        # Step 4: Click Product View Toggle
        def click_product_view():
            page.wait_for_timeout(2000)
            toggle = page.locator("div.react-toggle")
            toggle.click()
            page.wait_for_selector("div.react-toggle.react-toggle--checked", timeout=5000)
            print("âœ… Product View selected")
        log_step("Click Product View Toggle From the Contact List Header", click_product_view)

        # Step 5: Search for OPC 43 Grade Cement
        def search_product():
            cards = page.query_selector_all("div.user-name1")
            print(f"ðŸ” Found {len(cards)} user cards")
            found = False
            for idx, card in enumerate(cards, start=1):
                product = card.query_selector("div.wrd_elip.c_name")
                if product and "Opc 43 Grade Cement" in product.inner_text().strip():
                    product.click()
                    page.wait_for_timeout(7000)
                    print(f"âœ… Clicked 'Opc 43 Grade Cement' in card {idx}")
                    found = True
                    break
            if not found:
                raise Exception("âŒ 'Opc 43 Grade Cement' not found")
        log_step("Search OPC 43 Grade Cement in the Search Box", search_product)

        # Step 6: Chat Now / Say Hi / Send Message
        def click_chat_and_send_message():
            # Click first Chat Now button
            chat_buttons = page.query_selector_all("div.chatnow")
            if not chat_buttons:
                raise Exception("âŒ No 'Chat Now' buttons found")
            chat_buttons[0].click()
            page.wait_for_timeout(2000)
            print("âœ… Clicked Chat Now")
            if logger:
                logger.log_status(f"[{browser_name}] Click Chat Now CTA From Conversation List Screen", "Pass", "", browser_name, MOBILE_NUMBER, run_time)

            # Handle Say Hi if error div exists
            error_div = page.query_selector("div#error_no_enq")
            if error_div and error_div.is_visible():
                say_hi_btn = error_div.query_selector("div.no_chat_dv div.strt_nw_btn")
                if say_hi_btn:
                    say_hi_btn.click()
                    page.wait_for_timeout(2000)
                    print("âœ… Clicked Say Hi")
                    if logger:
                        logger.log_status(f"[{browser_name}] Click Say Hi From the Conversation Detail Screen", "Pass", "", browser_name, MOBILE_NUMBER, run_time)

            # Attempt to send a message
            try:
                textarea = page.query_selector("textarea#massage-text")
                if textarea:
                    textarea.fill(MESSAGE)
                    page.wait_for_timeout(1000)

                    send_button = page.query_selector("div#send_button")
                    if send_button:
                        page.wait_for_function(
                            """(btn) => {
                                const path = btn.querySelector('path#send_btn');
                                return path && path.getAttribute('fill') === 'rgb(2, 136, 125)';
                            }""",
                            arg=send_button,
                            timeout=5000
                        )
                        send_button.click()
                        print("âœ… Message sent successfully")
                        if logger:
                            logger.log_status(f"[{browser_name}] Click on Send Message CTA", "Pass", "", browser_name, MOBILE_NUMBER, run_time)
                    else:
                        raise Exception("Send button not found")
                else:
                    raise Exception("Textarea not found")
            except:
                # Always log custom remark
                remark = "Unable to send message, page becomes unresponsive"
                print(f"âŒ Send Message failed: {remark}")
                if logger:
                    logger.log_status(f"[{browser_name}] Send Message", "Fail", remark, browser_name, MOBILE_NUMBER, run_time)

        # Call Chat / Say Hi / Send Message directly
        click_chat_and_send_message()

        context.close()
        browser.close()
        print(f"âœ… {browser_name} test completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

