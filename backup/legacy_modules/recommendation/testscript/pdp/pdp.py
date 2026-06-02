from collections import defaultdict
from datetime import datetime
import os
import sys

from playwright.sync_api import sync_playwright

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RECOMMENDATION_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
for path in (RECOMMENDATION_DIR, ROOT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from logger_instance import logger
from core.settings import SESSION_DIR
from core.healing import attach_healing
from core.step_runner import run_step
from shared_flow import (
    SHEET_TAB_NAME,
    assert_not_404_page,
    build_item_label,
    click_first_visible,
    complete_form_until_thank_you,
    fill_quantity_and_continue_if_present,
    load_sheet_column,
    validate_recommendation_cards,
    verify_thank_you_screen,
)

session_file_path = str(SESSION_DIR / "enqlogin.json")
BROWSERS = ["chromium"]
MOBILE_NUMBER = "8335017702"
PDP_URLS = [
    "https://www.indiamart.com/proddetail/5-ltr-pet-bottle-2850467614588.html",
    "https://www.indiamart.com/proddetail/5-liter-plastic-pet-bottle-17444403255.html",
]
PRIMARY_CTA_SELECTORS = [
    "button#submit-btn",
    "button:has-text('Submit Requirement')",
]
FALLBACK_CTA_SELECTORS = [
    "#glp_pg-1",
    "button#glp_pg-1",
    "button.pdp_enq#glp_pg-1",
    "button.pdp_enq:has-text('Get Latest Price')",
    "button.actbtn:has-text('Get Latest Price')",
    "button:has-text('Get Latest Price')",
]

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def load_pdp_urls():
    return load_sheet_column(
        logger,
        column_names=["PDP URL", "PDP URLs", "PDP"],
        fallback_values=PDP_URLS,
        value_name="PDP URLs",
        require_url=True,
    )


def click_requirement_cta(page):
    selector = click_first_visible(page, PRIMARY_CTA_SELECTORS, timeout_ms=2500)
    if selector:
        print(f"Clicked primary CTA: {selector}")
        return

    selector = click_first_visible(page, FALLBACK_CTA_SELECTORS, timeout_ms=2500)
    if selector:
        print(f"Clicked fallback CTA: {selector}")
        return

    raise AssertionError("Neither Submit Requirement nor Get Latest Price CTA was found")


def fill_quantity_and_continue(page):
    if not fill_quantity_and_continue_if_present(page):
        raise AssertionError("Quantity field was not found in the requirement form")


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdp_urls = load_pdp_urls()

    for browser_name in BROWSERS:
        print(f"\nRunning PDP Submit Requirement flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)

        for url_index, pdp_url in enumerate(pdp_urls):
            url_label = build_item_label(url_index, pdp_url, "PDP URL")
            print(f"\nRunning {url_label}")
            context = browser.new_context(storage_state=session_file_path)
            page = attach_healing(
                context.new_page(),
                suite_name="Recommendation",
                module_name="PDP",
                test_name=f"submit_requirement_pdp_{url_index + 1}",
            )

            def log_step(step_name, func):
                return run_step(
                    step_name=f"{url_label} | {step_name}",
                    func=func,
                    page=page,
                    browser_name=browser_name,
                    run_time=run_time,
                    browser_results=browser_results,
                    logger=logger,
                    mobile_number=MOBILE_NUMBER,
                    logger_tab_name=SHEET_TAB_NAME,
                )

            try:
                log_step("Open PDP Page", lambda: page.goto(pdp_url, timeout=60000))
                log_step("Verify PDP Is Not 404", lambda: assert_not_404_page(page))
                log_step("Click Requirement CTA", lambda: click_requirement_cta(page))
                log_step("Fill Quantity And Click Next", lambda: fill_quantity_and_continue(page))
                log_step("Complete Form Until Thank You", lambda: complete_form_until_thank_you(page))
                log_step("Verify Thank You Screen", lambda: verify_thank_you_screen(page))
                log_step("Validate Recommendation Cards", lambda: validate_recommendation_cards(page))
                print(f"{browser_name} flow completed for {url_label}")
            except Exception as exc:
                print(f"{browser_name} flow failed for {url_label}: {type(exc).__name__}: {exc}")
            finally:
                context.close()

        browser.close()
        print(f"{browser_name} PDP flow completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
