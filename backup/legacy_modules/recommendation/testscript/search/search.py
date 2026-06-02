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
    DATA_TAB_NAME,
    SHEET_TAB_NAME,
    build_item_label,
    click_contact_supplier_cta,
    complete_form_until_thank_you,
    keyword_from_sheet_value,
    load_sheet_column,
    normalize_header,
    remember_requirement_value,
    select_search_city,
    validate_recommendation_cards,
    verify_thank_you_screen,
)

session_file_path = str(SESSION_DIR / "enqlogin.json")
BROWSERS = ["chromium"]
MOBILE_NUMBER = "8335017702"
SEARCH_HOME_URL = "https://dir.indiamart.com/"
SEARCH_VALUES = ["headphones"]
SEARCH_COLUMN_NAMES = ["Search URL", "Search Keyword", "Keyword", "Search"]
SEARCH_FALLBACK_COLUMN_NAMES = ["DIR URL", "DIR URLs", "IMPCAT URL", "PDP URL"]
SEARCH_CITY_COLUMN_NAMES = ["searched_city", "Searched City", "Search City", "City"]
SEARCH_INPUT_SELECTORS = [
    "input#search_string1",
    "input[name='ss']",
    "input#search_string",
]
SEARCH_CONTACT_SUPPLIER_SELECTORS = [
    "button.contactsupplier",
    "button[id^='dispid']",
    "button[data-click*='CTAContactSupplier']",
    "button:has-text('Contact Supplier')",
    "[aria-label*='contact supplier' i]",
    *CONTACT_SUPPLIER_SELECTORS,
]

browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})


def column_index(header_lookup, column_names):
    for column_name in column_names:
        index = header_lookup.get(normalize_header(column_name))
        if index is not None:
            return index
    return None


def load_search_values():
    search_values = load_sheet_column(
        logger,
        column_names=SEARCH_COLUMN_NAMES,
        fallback_values=[],
        value_name="search keywords",
        require_url=False,
    )
    if search_values:
        return search_values

    return load_sheet_column(
        logger,
        column_names=SEARCH_FALLBACK_COLUMN_NAMES,
        fallback_values=SEARCH_VALUES,
        value_name="search keywords derived from sheet URLs",
        require_url=False,
    )


def load_search_cases():
    try:
        rows = logger.read_rows(tab_name=DATA_TAB_NAME, include_header=True)
    except Exception as exc:
        print(f"Could not read '{DATA_TAB_NAME}' tab for searched_city, using search fallback. Reason: {exc}")
        rows = []

    if rows:
        header_lookup = {
            normalize_header(name): index
            for index, name in enumerate(rows[0])
        }
        search_index = column_index(header_lookup, SEARCH_COLUMN_NAMES)
        if search_index is None:
            search_index = column_index(header_lookup, SEARCH_FALLBACK_COLUMN_NAMES)
        city_index = column_index(header_lookup, SEARCH_CITY_COLUMN_NAMES)

        if search_index is not None:
            cases = []
            seen_cases = set()
            for row in rows[1:]:
                if search_index >= len(row):
                    continue
                search_value = row[search_index].strip()
                if not search_value:
                    continue

                keyword = keyword_from_sheet_value(search_value)
                city = row[city_index].strip() if city_index is not None and city_index < len(row) else ""
                dedupe_key = (keyword.lower(), city.lower())
                if dedupe_key in seen_cases:
                    continue

                cases.append(
                    {
                        "sheet_value": search_value,
                        "keyword": keyword,
                        "city": city,
                    }
                )
                seen_cases.add(dedupe_key)

            if cases:
                city_status = "with searched_city" if city_index is not None else "without searched_city"
                print(f"Loaded {len(cases)} search row(s) {city_status} from '{DATA_TAB_NAME}' tab")
                return cases

        print(
            f"Could not find usable search rows in '{DATA_TAB_NAME}' tab, "
            "using search keyword fallback."
        )

    return [
        {
            "sheet_value": value,
            "keyword": keyword_from_sheet_value(value),
            "city": "",
        }
        for value in load_search_values()
    ]


def fill_search_and_submit(page, keyword):
    remember_requirement_value(page, "search_keywords", keyword)
    for selector in SEARCH_INPUT_SELECTORS:
        field = page.locator(selector).first
        try:
            if field.count() and field.is_visible(timeout=2000):
                field.fill(keyword)
                field.press("Enter")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                return selector
        except Exception:
            continue
    raise AssertionError("Search input was not found on dir.indiamart.com")


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    search_cases = load_search_cases()

    for browser_name in BROWSERS:
        print(f"\nRunning Search enquiry flow on: {browser_name}")
        browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)

        for value_index, search_case in enumerate(search_cases):
            keyword = search_case["keyword"]
            city = search_case.get("city", "")
            label_value = f"{keyword} in {city}" if city else keyword
            value_label = build_item_label(value_index, label_value, "Search")
            print(f"\nRunning {value_label}")
            context = browser.new_context(storage_state=session_file_path)
            page = attach_healing(
                context.new_page(),
                suite_name="Recommendation",
                module_name="Search",
                test_name=f"search_{value_index + 1}",
            )

            def log_step(step_name, func):
                return run_step(
                    step_name=f"{value_label} | {step_name}",
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
                log_step("Open DIR Homepage", lambda: page.goto(SEARCH_HOME_URL, timeout=60000))
                log_step("Select Search City", lambda: select_search_city(page, city))
                log_step("Search Keyword", lambda: fill_search_and_submit(page, keyword))
                log_step(
                    "Click Contact Supplier CTA",
                    lambda: click_contact_supplier_cta(page, SEARCH_CONTACT_SUPPLIER_SELECTORS),
                )
                log_step("Complete Form Until Thank You", lambda: complete_form_until_thank_you(page))
                log_step("Verify Thank You Screen", lambda: verify_thank_you_screen(page))
                log_step("Validate Recommendation Cards", lambda: validate_recommendation_cards(page))
                print(f"{browser_name} flow completed for {value_label}")
            except Exception as exc:
                print(f"{browser_name} flow failed for {value_label}: {type(exc).__name__}: {exc}")
            finally:
                context.close()

        browser.close()
        print(f"{browser_name} Search flow completed and browser closed")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
