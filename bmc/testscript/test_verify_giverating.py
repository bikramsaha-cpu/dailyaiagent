from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    CONTACT_NAME_SELECTOR,
    build_page,
    empty_browser_results,
    make_log_step,
    open_message_centre,
    wait_for_conversation_header,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()


def rate_contact_if_widget_visible(page):
    widget = page.locator("#box1, [id*='rating']").first
    if not widget.is_visible(timeout=3000):
        print("Rating widget not visible for this contact")
        return False

    page.click(
        "label.star-4, label[for*='star-4']",
        intent="choose 4 star rating in buyer message centre",
        text="4",
        keywords=["rating", "4 star", "review"],
    )
    page.wait_for_selector("#box2, [id*='review']", timeout=7000)

    for selector in ("#R1", "#Q1", "#D1"):
        try:
            page.click(selector)
        except Exception:
            pass

    comment_box = page.locator("#addComment, textarea").first
    if comment_box.is_visible():
        comment_box.fill("Good experience and timely response!")

    page.click(
        "input#submit.rating_submit, button:has-text('Submit'), input[value='Submit']",
        intent="submit rating review in buyer message centre",
        text="Submit",
        role="button",
        role_name="Submit",
        keywords=["submit", "rating", "review"],
    )
    try:
        page.wait_for_selector("#box2, [id*='review']", state="detached", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    return True


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning give rating automation on: {browser_name}")
        browser = launch_browser(playwright, browser_name)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
        page = build_page(context.new_page(), test_name=test_case_name)
        base_log_step = make_log_step(
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=MOBILE_NUMBER,
        )

        def log_step(step_name, func):
            return base_log_step(f"{test_case_name} -> {step_name}", func)

        log_step("Open Message Centre", lambda: open_message_centre(page))

        def rate_first_contact_with_widget():
            contacts = page.locator(CONTACT_NAME_SELECTOR)
            total_contacts = contacts.count()
            if total_contacts == 0:
                raise Exception("No contacts found in message centre")

            for index in range(total_contacts):
                contact = page.locator(CONTACT_NAME_SELECTOR).nth(index)
                contact_name = contact.inner_text().strip()
                print(f"Checking contact {index + 1}: {contact_name}")
                contact.click(
                    intent="open contact conversation for rating",
                    text=contact_name,
                    role="button",
                    role_name=contact_name,
                    keywords=["contact", "conversation", "rating", contact_name],
                )
                wait_for_conversation_header(page, timeout=10000)
                time.sleep(1.5)
                if rate_contact_if_widget_visible(page):
                    print("Rating submitted successfully")
                    return
            raise Exception("Rating widget was not available for any visible contact")

        log_step("Rate First Contact With Widget", rate_first_contact_with_widget)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

