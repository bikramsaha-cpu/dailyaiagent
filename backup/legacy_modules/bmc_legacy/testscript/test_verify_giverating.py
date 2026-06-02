from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import (
    build_page,
    empty_browser_results,
    make_log_step,
    open_first_contact,
    open_message_centre,
    wait_for_conversation_header,
)

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

FEEDBACK_BANNER_SELECTOR = "li.feedbckBanner"
RATED_BANNER_SELECTOR = ".feedbckBanner"
FEEDBACK_BANNER_TITLE_SELECTOR = "span.fw.db.truncate, span.fw.truncate"
FEEDBACK_STAR_GROUP_SELECTOR = "i.pdmsgcansl svg"
FEEDBACK_MODAL_SELECTOR = "#callBlanket"
FEEDBACK_MODAL_TITLE_SELECTOR = "#callBlanket .handleforpostcalFeedbackHeader span.fs16"
FEEDBACK_MODAL_REVIEW_TEXTAREA_SELECTOR = "#callBlanket textarea.rvwBox2, #callBlanket textarea[maxlength='255']"
FEEDBACK_MODAL_SUBMIT_SELECTOR = "#callBlanket button.bg0aa, #callBlanket button:has-text('Submit')"
FEEDBACK_CATEGORY_ROW_SELECTOR = "#callBlanket .ratBox"
FEEDBACK_CATEGORY_LABEL_SELECTOR = "span.fw.db.fs15"
FEEDBACK_THUMBS_UP_SELECTOR = "span[style*='right: 108px'] svg"
EDIT_REVIEW_BUTTON_SELECTOR = ".editRvwBrd button, button:has-text('Edit Review')"
CONVERSATION_PANEL_SELECTOR = (
    "div[class*='Templates-module__dflx__'][class*='Templates-module__flxdc__']"
    "[class*='Templates-module__ovh__'][class*='Templates-module__bgw__'][class*='Templates-module__w100__']"
)
browser_results = empty_browser_results()


def get_feedback_banner(page):
    panel = page.locator(CONVERSATION_PANEL_SELECTOR).first
    panel.wait_for(state="visible", timeout=15000)
    banner = panel.locator(f"{FEEDBACK_BANNER_SELECTOR}, li[class*='feedbckBanner'], .feedbckBanner").first
    if not banner.is_visible():
        raise AssertionError(
            "Feedback banner is not visible inside the opened conversation details panel."
        )
    banner.scroll_into_view_if_needed(timeout=2000)
    return banner


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

        state = {
            "supplier_name": "",
            "modal_title": "",
            "rated_categories": [],
            "review_text": "Great experience with quick response and smooth delivery.",
            "contact_name": "",
            "entry_mode": "",
        }

        def log_step(step_name, func):
            return base_log_step(f"{test_case_name} -> {step_name}", func)

        log_step("Open Message Centre", lambda: open_message_centre(page))

        def open_conversation_with_feedback_banner():
            try:
                contact_name = open_first_contact(page, timeout=15000)
            except Exception as exc:
                raise AssertionError(f"Could not open the first available contact from the message list: {exc}") from exc

            state["contact_name"] = contact_name
            wait_for_conversation_header(page, timeout=10000)
            time.sleep(1.5)

            banner_locator = page.locator(
                f"{CONVERSATION_PANEL_SELECTOR} {FEEDBACK_BANNER_SELECTOR}, "
                f"{CONVERSATION_PANEL_SELECTOR} li[class*='feedbckBanner'], "
                f"{CONVERSATION_PANEL_SELECTOR} .feedbckBanner"
            ).first
            try:
                if banner_locator.count() and banner_locator.is_visible():
                    print(f"Feedback banner found inside conversation for contact: {contact_name}")
                    return
            except Exception:
                pass

            raise AssertionError(
                f"Opened conversation for contact '{contact_name}', but no feedback banner was visible in the conversation details panel."
            )

        log_step("Open Conversation With Feedback Banner", open_conversation_with_feedback_banner)

        def verify_feedback_banner_is_visible():
            banner = get_feedback_banner(page)
            banner_text = banner.inner_text().strip()
            supplier_name = ""
            try:
                supplier_name = banner.locator(FEEDBACK_BANNER_TITLE_SELECTOR).first.inner_text().strip()
            except Exception:
                supplier_name = ""

            state["supplier_name"] = supplier_name or state["contact_name"]

            if "Your Feedback Matters" in banner_text:
                state["entry_mode"] = "new_review"
                star_count = banner.locator(FEEDBACK_STAR_GROUP_SELECTOR).count()
                if star_count != 5:
                    raise AssertionError(
                        f"Feedback banner should display exactly 5 rating stars, but found {star_count}."
                    )
                print(
                    f"New feedback banner detected for supplier: {state['supplier_name']} "
                    f"inside conversation of contact: {state['contact_name'] or 'unknown'}"
                )
                return

            if "Rating submitted" in banner_text:
                state["entry_mode"] = "edit_review"
                edit_button = banner.locator(EDIT_REVIEW_BUTTON_SELECTOR).first
                if not edit_button.is_visible():
                    raise AssertionError(
                        "Rated feedback banner is visible, but the Edit Review CTA is missing."
                    )
                print(
                    f"Existing rating banner detected for supplier: {state['supplier_name']}. "
                    "The test will continue through Edit Review."
                )
                return

            raise AssertionError(
                "A feedback banner was found in the conversation, but it was neither a new review banner nor a rated banner."
            )

        log_step("Verify Feedback Banner Is Visible", verify_feedback_banner_is_visible)

        def open_rating_popup():
            banner = get_feedback_banner(page)
            if state["entry_mode"] == "edit_review":
                edit_button = banner.locator(EDIT_REVIEW_BUTTON_SELECTOR).first
                edit_button.click(force=True)
            else:
                stars = banner.locator(FEEDBACK_STAR_GROUP_SELECTOR)
                if stars.count() < 5:
                    raise AssertionError(
                        f"Expected 5 feedback stars in the banner, but found only {stars.count()}."
                    )
                stars.nth(4).click(force=True)
            page.wait_for_selector(FEEDBACK_MODAL_SELECTOR, state="visible", timeout=10000)
            time.sleep(1)

        log_step("Open Rating Popup From Feedback Banner", open_rating_popup)

        def verify_rating_popup_content():
            modal = page.locator(FEEDBACK_MODAL_SELECTOR).first
            if not modal.is_visible():
                raise AssertionError("Rating popup did not become visible after clicking the feedback banner.")

            modal_title = modal.locator(FEEDBACK_MODAL_TITLE_SELECTOR).first.inner_text().strip()
            state["modal_title"] = modal_title
            if "My Review for" not in modal_title:
                raise AssertionError(
                    f"Rating popup title is incorrect. Expected it to contain 'My Review for', found '{modal_title}'."
                )
            if state["supplier_name"] and state["supplier_name"].lower() not in modal_title.lower():
                raise AssertionError(
                    "Rating popup opened, but supplier name does not match the feedback banner. "
                    f"Banner='{state['supplier_name']}', Popup='{modal_title}'."
                )

            textarea = modal.locator(FEEDBACK_MODAL_REVIEW_TEXTAREA_SELECTOR).first
            if not textarea.is_visible():
                raise AssertionError("Review textarea is missing in the rating popup.")

            submit_button = modal.locator(FEEDBACK_MODAL_SUBMIT_SELECTOR).first
            if not submit_button.is_visible():
                raise AssertionError("Submit button is missing in the rating popup.")

        log_step("Verify Rating Popup Content", verify_rating_popup_content)

        def choose_positive_category_ratings():
            modal = page.locator(FEEDBACK_MODAL_SELECTOR).first
            rows = modal.locator(FEEDBACK_CATEGORY_ROW_SELECTOR)
            row_count = rows.count()
            if row_count == 0:
                raise AssertionError("No category rating rows were found in the popup.")

            rated_categories: list[str] = []
            for index in range(row_count):
                row = rows.nth(index)
                label = row.locator(FEEDBACK_CATEGORY_LABEL_SELECTOR).first.inner_text().strip()
                if not label:
                    raise AssertionError(f"Category row {index + 1} is missing its label.")

                thumbs_up = row.locator(FEEDBACK_THUMBS_UP_SELECTOR).first
                if not thumbs_up.is_visible():
                    raise AssertionError(f"Thumbs-up icon is not visible for category '{label}'.")

                thumbs_up.click(force=True)
                rated_categories.append(label)
                time.sleep(0.4)

            state["rated_categories"] = rated_categories
            if len(rated_categories) != row_count:
                raise AssertionError(
                    f"Not all categories were rated. Rated={len(rated_categories)}, available={row_count}."
                )
            print(f"Positive ratings applied for categories: {', '.join(rated_categories)}")

        log_step("Rate All Feedback Categories Positively", choose_positive_category_ratings)

        def enter_review_text():
            textarea = page.locator(FEEDBACK_MODAL_REVIEW_TEXTAREA_SELECTOR).first
            textarea.click()
            textarea.fill(state["review_text"])
            entered_text = textarea.input_value().strip()
            if entered_text != state["review_text"]:
                raise AssertionError(
                    "Review text did not persist in the textarea. "
                    f"Expected='{state['review_text']}', Actual='{entered_text}'."
                )

        log_step("Enter Review Text", enter_review_text)

        def submit_rating_popup():
            submit_button = page.locator(FEEDBACK_MODAL_SUBMIT_SELECTOR).first
            submit_button.click(force=True)
            page.wait_for_selector(FEEDBACK_MODAL_SELECTOR, state="hidden", timeout=10000)
            time.sleep(1)

        log_step("Submit Rating Popup", submit_rating_popup)

        def verify_rating_popup_closed():
            modal_visible = page.locator(FEEDBACK_MODAL_SELECTOR).first.is_visible()
            if modal_visible:
                raise AssertionError("Rating popup is still visible after clicking Submit.")
            print(
                "Rating flow completed successfully for supplier "
                f"'{state['supplier_name']}' with categories: {', '.join(state['rated_categories'])}."
            )

        log_step("Verify Rating Submission Completed", verify_rating_popup_closed)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
