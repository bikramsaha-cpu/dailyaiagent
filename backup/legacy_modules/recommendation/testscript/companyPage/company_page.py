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
    CONTACT_SUPPLIER_SELECTORS,
    SHEET_TAB_NAME,
    assert_not_404_page,
    build_item_label,
    click_contact_supplier_cta,
    complete_form_until_thank_you,
    load_sheet_column,
    select_product_if_present,
    validate_recommendation_cards,
    verify_thank_you_screen,
)

session_file_path = str(SESSION_DIR / "enqlogin.json")
BROWSERS = ["chromium"]
MOBILE_NUMBER = "8335017702"
COMPANY_URLS = [
    "https://www.indiamart.com/raghavendraagency-hyderabad/?pid=2851972054933&c_id=750&mid=184317&pn=Oppo%20Mobile%20Phones",
]
COMPANY_CONTACT_SUPPLIER_SELECTORS = [
    "#head-suplr",
    "span#head-suplr",
    "span[ctaname='Contact Supplier']",
    "span.enq_click:has-text('Contact Supplier')",
    "span:has-text('Contact Supplier')",
    *CONTACT_SUPPLIER_SELECTORS,
]

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def load_company_urls():
    return load_sheet_column(
        logger,
        column_names=["Company URL", "Company URLs", "Company"],
        fallback_values=COMPANY_URLS,
        value_name="Company URLs",
        require_url=True,
    )


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    company_urls = load_company_urls()

    for browser_name in BROWSERS:
        print(f"\nRunning Company Page enquiry flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)

        for url_index, company_url in enumerate(company_urls):
            url_label = build_item_label(url_index, company_url, "Company URL")
            print(f"\nRunning {url_label}")
            context = browser.new_context(storage_state=session_file_path)
            page = attach_healing(
                context.new_page(),
                suite_name="Recommendation",
                module_name="CompanyPage",
                test_name=f"company_page_{url_index + 1}",
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
                log_step("Open Company Page", lambda: page.goto(company_url, timeout=60000))
                log_step("Verify Company Page Is Not 404", lambda: assert_not_404_page(page))
                log_step(
                    "Click Contact Supplier CTA",
                    lambda: click_contact_supplier_cta(page, COMPANY_CONTACT_SUPPLIER_SELECTORS),
                )
                log_step("Select Product If Present", lambda: select_product_if_present(page))
                log_step("Complete Form Until Thank You", lambda: complete_form_until_thank_you(page))
                log_step("Verify Thank You Screen", lambda: verify_thank_you_screen(page))
                log_step("Validate Recommendation Cards", lambda: validate_recommendation_cards(page))
                print(f"{browser_name} flow completed for {url_label}")
            except Exception as exc:
                print(f"{browser_name} flow failed for {url_label}: {type(exc).__name__}: {exc}")
            finally:
                context.close()

        browser.close()
        print(f"{browser_name} Company Page flow completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
