from __future__ import annotations

import json
import os
import re
import time
from urllib.parse import parse_qs, urlparse

from core.llm_client import LLMConfig, OpenAICompatibleLLM
from core.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from core.workspace_settings import load_workspace_settings

DATA_TAB_NAME = "Data"
SHEET_TAB_NAME = "Recommendation"

NEXT_BUTTON_SELECTORS = [
    "button.submit-button:has-text('Next')",
    "button.submit-button",
    "input#t0901_submit[value='Next']",
    "input#t0901_submit[value='Submit']",
    "input#t0901_submit",
    "input[type='submit'][value='Next']",
    "input[type='submit'][value='Submit']",
    "button:has-text('Next')",
    "button:has-text('Submit')",
]
THANK_YOU_SELECTORS = [
    "text=Thank You",
    "text=Thank you",
    "text=Thankyou",
    "text=Thank",
    "text=Your requirement has been posted",
    "text=Your Requirement",
    "text=Requirement Posted",
    "text=Submitted Successfully",
    "text=Recommended Suppliers",
    "text=Recommended Products",
    "text=View More Details",
]
NOT_FOUND_SELECTORS = [
    "text=Oh no! It seems this page is not available",
    "p:has-text('Oh no! It seems this page is not available')",
]
PRODUCT_PICKER_SELECTORS = [
    "ul#productUl li.product-itemz",
    "#productUl li",
    ".product-list li",
    "li.product-itemz",
]
PRODUCT_PICKER_SUBMIT_SELECTORS = [
    "input#scr_submit",
    "input.befstgo2[type='submit']",
    "input[type='submit'][value='Submit']",
]
QUANTITY_INPUT_SELECTORS = [
    "input#ttxtbx_option1",
    "input[name='quantity']",
    "input[placeholder*='Quantity']",
]
UNIT_OPTION_SELECTORS = [
    "#tqt_display li.radio-item",
    "ul:has-text('Piece') li",
    "li.radio-item",
]
CONTACT_SUPPLIER_SELECTORS = [
    "button.contactsupplier",
    "button[id^='dispid']",
    "button[data-click*='CTAContactSupplier']",
    "[data-click*='ContactSupplier']",
    ".template7-get-best-price .contact-supplier-btn",
    "div.contact-supplier-btn:has-text('Contact Supplier')",
    "[id^='dispId']:has-text('Contact Supplier')",
    "#head-suplr",
    "span#head-suplr",
    "span[ctaname='Contact Supplier']",
    "span.enq_click:has-text('Contact Supplier')",
    "button:has-text('Contact Supplier')",
    "a:has-text('Contact Supplier')",
    "span:has-text('Contact Supplier')",
    "[aria-label*='contact supplier' i]",
]
RECOMMENDATION_CARD_SELECTOR = (
    "li:has(a:has-text('View More Details')), "
    "li:has(a.cityadv), "
    "li:has(a[target='_blank'][href]), "
    "div:has(a.cityadv):has-text('Response Rate')"
)
COMPANY_LINK_SELECTORS = [
    "a.cityadv[href]",
    "a:has(.cnmAdv)[href]",
    "a[target='_blank'][href]",
    "a[href^='http']",
]
FORM_CONTEXT_SELECTORS = [
    "#t0901_bewrapper",
    "#t0102_bewrapper",
    ".be-frwrap",
    ".enqFrm",
    "form",
    "[id*='t0901']",
]
SEARCH_CITY_BUTTON_SELECTORS = [
    "button#hdnew_searchPlace",
    "#hd_usercity_new",
    "button:has(#hd_usercity_new)",
    "#drpn button",
    "#drpn",
    "button:has(#hd_usercity)",
    "#hd_usercity",
]
SEARCH_CITY_INPUT_SELECTORS = [
    "input#txt-city-new",
    "input#hd_city_sugg",
    "input[name='city_ss']",
    "#city_hold input.ui-autocomplete-input",
    "#drpn input.ui-autocomplete-input",
    "input[placeholder='Enter City']",
    "input[placeholder='Enter city']",
]
SEARCH_CITY_SUGGESTION_SELECTORS = [
    "div.ui-autocomplete:visible ul.ui-autocomplete li.as_D a",
    "div.ui-autocomplete:visible ul.ui-autocomplete li.ui-menu-item a",
    "div.cls_city:visible li.as_D a",
    "ul.ui-autocomplete li.as_D a",
    "ul.ui-autocomplete li.ui-menu-item a",
    "ul.ui-autocomplete li a",
    ".ui-autocomplete .ui-menu-item a",
]


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def load_sheet_column(
    logger,
    *,
    column_names: list[str],
    fallback_values: list[str],
    value_name: str,
    require_url: bool = False,
) -> list[str]:
    try:
        rows = logger.read_rows(tab_name=DATA_TAB_NAME, include_header=True)
    except Exception as exc:
        print(f"Could not read '{DATA_TAB_NAME}' tab, using fallback {value_name}. Reason: {exc}")
        return fallback_values

    if not rows:
        print(f"'{DATA_TAB_NAME}' tab is empty, using fallback {value_name}")
        return fallback_values

    header = rows[0]
    header_lookup = {normalize_header(name): index for index, name in enumerate(header)}
    target_index = None
    for column_name in column_names:
        target_index = header_lookup.get(normalize_header(column_name))
        if target_index is not None:
            break

    if target_index is None:
        print(
            f"Could not find any of {column_names} in '{DATA_TAB_NAME}' tab, "
            f"using fallback {value_name}"
        )
        return fallback_values

    values: list[str] = []
    seen_values: set[str] = set()
    for row in rows[1:]:
        if target_index >= len(row):
            continue
        value = row[target_index].strip()
        if not value:
            continue
        if require_url and not is_url(value):
            continue
        if value in seen_values:
            continue
        values.append(value)
        seen_values.add(value)

    if values:
        print(f"Loaded {len(values)} {value_name} from '{DATA_TAB_NAME}' tab")
        return values

    print(f"No {value_name} found in '{DATA_TAB_NAME}' tab, using fallback values")
    return fallback_values


def build_item_label(index: int, value: str, prefix: str) -> str:
    if is_url(value):
        parsed = urlparse(value)
        token = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
    else:
        token = re.sub(r"\s+", "_", value.strip())
    token = token.split("?")[0] or prefix.lower()
    return f"{prefix} {index + 1} - {token[:60]}"


def keyword_from_sheet_value(value: str) -> str:
    value = value.strip()
    if not is_url(value):
        return value

    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    for key in ("ss", "q", "search"):
        if query.get(key):
            return query[key][0].strip()

    slug = parsed.path.rstrip("/").split("/")[-1]
    slug = re.sub(r"\.html?$", "", slug, flags=re.IGNORECASE)
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug or value


def raw_page(page):
    return getattr(page, "_page", page)


def requirement_context(page) -> dict:
    base_page = raw_page(page)
    context = getattr(base_page, "_recommendation_requirement_context", None)
    if context is None:
        context = {
            "source_url": "",
            "source_title": "",
            "search_keywords": [],
            "searched_cities": [],
            "selected_products": [],
            "quantities": [],
            "form_snapshots": [],
        }
        setattr(base_page, "_recommendation_requirement_context", context)

    try:
        if not context.get("source_url"):
            context["source_url"] = base_page.url or ""
    except Exception:
        pass

    try:
        if not context.get("source_title"):
            context["source_title"] = base_page.title() or ""
    except Exception:
        pass

    return context


def remember_requirement_value(page, key: str, value: str) -> None:
    value = (value or "").strip()
    if not value:
        return

    context = requirement_context(page)
    current = context.setdefault(key, [])
    if isinstance(current, list) and value not in current:
        current.append(value)
    elif not current:
        context[key] = value


def capture_form_context(page) -> None:
    base_page = raw_page(page)
    context = requirement_context(page)

    snapshots = context.setdefault("form_snapshots", [])
    if len(snapshots) >= 6:
        return

    for selector in FORM_CONTEXT_SELECTORS:
        try:
            loc = base_page.locator(selector).first
            if loc.count() and loc.is_visible(timeout=400):
                text = compact_text(loc.inner_text(timeout=1000), limit=1200)
                if text and text not in snapshots:
                    snapshots.append(text)
                return
        except Exception:
            continue

    try:
        body_text = compact_text(base_page.locator("body").inner_text(timeout=1000), limit=1200)
        if body_text and body_text not in snapshots:
            snapshots.append(body_text)
    except Exception:
        pass


def compact_text(value: str, *, limit: int = 800) -> str:
    return re.sub(r"\s+", " ", value or "").strip()[:limit]


def click_first_visible(page, selectors: list[str], *, timeout_ms: int = 1500) -> str | None:
    base_page = raw_page(page)
    for selector in selectors:
        try:
            try:
                base_page.wait_for_selector(selector, state="attached", timeout=timeout_ms)
            except Exception:
                pass

            all_matches = base_page.locator(selector)
            match_count = all_matches.count()
            if not match_count:
                continue
            for index in range(min(match_count, 8)):
                locator = all_matches.nth(index)
                if not locator.is_visible(timeout=timeout_ms):
                    continue

                locator.scroll_into_view_if_needed(timeout=3000)
                try:
                    locator.click(timeout=5000)
                except Exception:
                    locator.click(timeout=5000, force=True)
                time.sleep(1)
                return selector
        except Exception:
            continue
    return None


def select_search_city(page, city: str) -> str:
    city = compact_text(city, limit=120) or "Delhi"

    base_page = raw_page(page)
    for selector in ("#hd_usercity_new", "#hd_usercity"):
        try:
            current_city = compact_text(
                base_page.locator(selector).first.inner_text(timeout=1000),
                limit=120,
            )
            if current_city and current_city.lower() == city.lower():
                remember_requirement_value(page, "searched_cities", current_city)
                return f"City already selected: {current_city}"
        except Exception:
            pass

    city_panel_opened = False
    for selector in SEARCH_CITY_BUTTON_SELECTORS:
        trigger = base_page.locator(selector).first
        try:
            if trigger.count() and trigger.is_visible(timeout=1200):
                trigger.click(timeout=5000)
                city_panel_opened = True
                break
        except Exception:
            continue

    field = None
    for selector in SEARCH_CITY_INPUT_SELECTORS:
        candidate = base_page.locator(selector).first
        try:
            if not candidate.count():
                continue
            try:
                candidate.wait_for(state="visible", timeout=5000)
            except Exception:
                pass
            if candidate.is_visible(timeout=1200):
                field = candidate
                break
        except Exception:
            continue

    if field is None:
        panel_hint = " after opening city selector" if city_panel_opened else ""
        raise AssertionError(f"City input was not found{panel_hint}")

    try:
        field.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass

    try:
        field.click(timeout=2000)
    except Exception:
        try:
            field.click(timeout=2000, force=True)
        except Exception:
            field.evaluate(
                """(element) => {
                    element.focus();
                    if (typeof element.select === 'function') {
                        element.select();
                    }
                }"""
            )

    field.evaluate(
        """(element) => {
            element.focus();
            if (typeof element.select === 'function') {
                element.select();
            }
        }"""
    )

    try:
        base_page.keyboard.press("Control+A")
        base_page.keyboard.press("Backspace")
        base_page.keyboard.type(city, delay=60)
    except Exception:
        field.evaluate(
            """(element, value) => {
                element.focus();
                element.value = value;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: value.slice(-1) || ' ' }));
                if (typeof window.AlInd_Op === 'function') {
                    window.AlInd_Op();
                }
            }""",
            city,
        )

    fallback_suggestion = None
    deadline = time.time() + 8
    while time.time() < deadline:
        for selector in SEARCH_CITY_SUGGESTION_SELECTORS:
            suggestions = base_page.locator(selector)
            try:
                suggestion_count = min(suggestions.count(), 10)
            except Exception:
                continue

            for index in range(suggestion_count):
                suggestion = suggestions.nth(index)
                try:
                    if not suggestion.is_visible(timeout=500):
                        continue
                    suggestion_text = compact_text(suggestion.inner_text(timeout=1000), limit=160)
                    fallback_suggestion = (suggestion, suggestion_text)
                    suggestion.click(timeout=5000)
                    print(f"Selected first city suggestion: {suggestion_text}")
                    remember_requirement_value(page, "searched_cities", suggestion_text)
                    return suggestion_text
                except Exception:
                    continue
        time.sleep(0.35)

    if fallback_suggestion is not None:
        suggestion, suggestion_text = fallback_suggestion
        suggestion.click(timeout=5000)
        print(f"Selected first available city suggestion: {suggestion_text}")
        remember_requirement_value(page, "searched_cities", suggestion_text)
        return suggestion_text

    raise AssertionError(f"No city autosuggestion appeared for '{city}'")


def click_contact_supplier_cta(page, selectors: list[str] | None = None) -> str:
    selected = click_first_visible(page, selectors or CONTACT_SUPPLIER_SELECTORS, timeout_ms=2500)
    if selected:
        print(f"Clicked Contact Supplier CTA: {selected}")
        return selected
    raise AssertionError("Contact Supplier CTA was not found")


def assert_not_404_page(page) -> None:
    for selector in NOT_FOUND_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=1500):
                raise AssertionError("Page redirected to 404: Oh no! It seems this page is not available")
        except AssertionError:
            raise
        except Exception:
            continue


def is_thank_you_screen_visible(page) -> bool:
    try:
        url = (page.url or "").lower()
        if any(token in url for token in ("thank", "thankyou", "thank-you")):
            return True
    except Exception:
        pass

    for selector in THANK_YOU_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=1000):
                return True
        except Exception:
            continue

    try:
        if page.locator("li:has(a:has-text('View More Details'))").count() > 0:
            return True
    except Exception:
        pass

    return False


def wait_for_thank_you_screen(page, *, timeout_ms: int = 20000) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        if is_thank_you_screen_visible(page):
            return True
        try:
            page.wait_for_load_state("domcontentloaded", timeout=1000)
        except Exception:
            pass
        time.sleep(0.5)
    return is_thank_you_screen_visible(page)


def click_next_button(page) -> str | None:
    return click_first_visible(page, NEXT_BUTTON_SELECTORS, timeout_ms=1200)


def select_product_if_present(page, *, timeout_ms: int = 2500) -> bool:
    capture_form_context(page)
    base_page = raw_page(page)
    try:
        base_page.wait_for_selector("#productUl li, li.product-itemz", timeout=timeout_ms)
    except Exception:
        pass

    for selector in PRODUCT_PICKER_SELECTORS:
        items = base_page.locator(selector)
        try:
            item_count = min(items.count(), 5)
        except Exception:
            continue

        for index in range(item_count):
            item = items.nth(index)
            try:
                if item.is_visible(timeout=700):
                    item.scroll_into_view_if_needed(timeout=3000)
                    selected_text = item.inner_text(timeout=1000).strip()
                    item.click(timeout=5000)
                    print(f"Selected product option: {selected_text or selector}")
                    remember_requirement_value(page, "selected_products", selected_text)
                    time.sleep(0.5)
                    submit_selector = click_first_visible(
                        page,
                        PRODUCT_PICKER_SUBMIT_SELECTORS,
                        timeout_ms=1500,
                    )
                    if submit_selector:
                        print(f"Clicked product picker submit: {submit_selector}")
                    return True
            except Exception:
                continue
    return False


def fill_quantity_and_continue_if_present(page) -> bool:
    capture_form_context(page)
    for selector in QUANTITY_INPUT_SELECTORS:
        field = page.locator(selector).first
        try:
            is_visible = field.count() and field.is_visible(timeout=800)
        except Exception:
            continue

        if not is_visible:
            continue

        field.fill("10")
        remember_requirement_value(page, "quantities", "10")
        for unit_selector in UNIT_OPTION_SELECTORS:
            units = page.locator(unit_selector)
            try:
                if units.count() and units.first.is_visible(timeout=500):
                    units.first.click(timeout=3000)
                    break
            except Exception:
                continue

        clicked = click_next_button(page)
        if not clicked:
            raise RuntimeError("Quantity was filled, but no Next/Submit button was found")
        print(f"Filled quantity and clicked: {clicked}")
        return True
    return False


def complete_form_until_thank_you(page, *, max_actions: int = 10) -> None:
    for _ in range(max_actions):
        capture_form_context(page)
        if is_thank_you_screen_visible(page):
            return

        if select_product_if_present(page, timeout_ms=700):
            continue

        if fill_quantity_and_continue_if_present(page):
            continue

        clicked = click_next_button(page)
        if clicked:
            print(f"Clicked form CTA: {clicked}")
            if wait_for_thank_you_screen(page, timeout_ms=3000):
                return
            continue

        if wait_for_thank_you_screen(page, timeout_ms=15000):
            return
        raise AssertionError("No actionable form CTA was found before Thank You screen")

    if not wait_for_thank_you_screen(page, timeout_ms=15000):
        raise AssertionError("Thank You screen did not appear after completing the form")


def verify_thank_you_screen(page) -> None:
    if not wait_for_thank_you_screen(page, timeout_ms=10000):
        raise AssertionError("Thank You screen is not visible")


def extract_number(card_text: str, pattern: str, label: str) -> float:
    match = re.search(pattern, card_text, re.IGNORECASE)
    if not match:
        raise AssertionError(f"{label} not found in recommendation card")
    return float(match.group(1))


def extract_response_rate(card_text: str) -> float:
    return extract_number(
        card_text,
        r"(\d+(?:\.\d+)?)\s*%\s*Response\s*Rate",
        "Response Rate",
    )


def extract_rating_details(card_text: str) -> tuple[float, int]:
    compact = compact_text(card_text, limit=4000)
    rating_with_count = re.search(
        r"\b([0-5](?:\.\d+)?)\s*\(\s*(\d+)\s*\)",
        compact,
    )
    if rating_with_count:
        return float(rating_with_count.group(1)), int(rating_with_count.group(2))

    rating_match = re.search(r"Rating\s*:?\s*(\d+(?:\.\d+)?)", card_text, re.IGNORECASE)
    if rating_match:
        rating = float(rating_match.group(1))
        rater_count = extract_rater_count(card_text)
        return rating, rater_count

    candidates = re.findall(r"\b[0-5](?:\.\d+)?\b", compact)
    for value in candidates:
        numeric = float(value)
        if 0 <= numeric <= 5:
            rater_count = extract_rater_count(card_text)
            return numeric, rater_count
    raise AssertionError("Rating not found in recommendation card")


def extract_rater_count(card_text: str) -> int:
    compact = compact_text(card_text, limit=4000)
    count_match = re.search(r"\b[0-5](?:\.\d+)?\s*\(\s*(\d+)\s*\)", compact)
    if count_match:
        return int(count_match.group(1))

    label_match = re.search(r"\b(\d+)\s*(?:ratings?|raters?|reviews?)\b", compact, re.IGNORECASE)
    if label_match:
        return int(label_match.group(1))

    raise AssertionError("Rater count not found in recommendation card")


def extract_member_years(card_text: str) -> float:
    year_values = [
        float(value)
        for value in re.findall(
            r"\b(\d+(?:\.\d+)?)\s*(?:yrs?|years?)\b",
            card_text,
            re.IGNORECASE,
        )
    ]
    if year_values:
        return max(year_values)

    month_values = [
        float(value)
        for value in re.findall(
            r"\b(\d+(?:\.\d+)?)\s*months?\b",
            card_text,
            re.IGNORECASE,
        )
    ]
    if month_values:
        return max(month_values) / 12

    raise AssertionError("Member years not found in recommendation card")


def has_gst(card_text: str) -> bool:
    return bool(re.search(r"\bGST\b", card_text, re.IGNORECASE))


def company_info_from_card(card) -> dict:
    for selector in COMPANY_LINK_SELECTORS:
        link = card.locator(selector).first
        try:
            if not link.count():
                continue
            href = link.get_attribute("href") or ""
            name = compact_text(link.inner_text(timeout=1000), limit=160)
            return {
                "name": name or "Unknown company",
                "href": href,
                "selector": selector,
            }
        except Exception:
            continue
    return {"name": "Unknown company", "href": "", "selector": ""}


def inspect_company_page_for_failure(page, card=None) -> dict:
    base_page = raw_page(page)
    source = card if card is not None else base_page
    link = None
    info = {"name": "Unknown company", "href": "", "selector": ""}

    for selector in COMPANY_LINK_SELECTORS:
        candidate = source.locator(selector).first
        try:
            if not candidate.count():
                continue
            info = {
                "name": compact_text(candidate.inner_text(timeout=1000), limit=160) or "Unknown company",
                "href": candidate.get_attribute("href") or "",
                "selector": selector,
            }
            link = candidate
            break
        except Exception:
            continue

    if link is None and not info.get("href"):
        return {**info, "opened": False, "reason": "No company page link found on failed card"}

    company_page = None
    opened_by = ""
    try:
        target = ""
        try:
            target = link.get_attribute("target") or ""
        except Exception:
            pass

        if link is not None and target.lower() == "_blank":
            try:
                link.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            try:
                with base_page.context.expect_page(timeout=7000) as page_info:
                    try:
                        link.click(timeout=5000)
                    except Exception:
                        link.click(timeout=5000, force=True)
                company_page = page_info.value
                opened_by = "clicked company link"
            except Exception:
                company_page = None

        if company_page is None and info.get("href"):
            company_page = base_page.context.new_page()
            company_page.goto(info["href"], wait_until="domcontentloaded", timeout=30000)
            opened_by = "opened href fallback"

        if company_page is None:
            return {**info, "opened": False, "reason": "Company page link click did not open a page"}

        try:
            company_page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        try:
            body_text = compact_text(company_page.locator("body").inner_text(timeout=3000), limit=600)
        except Exception:
            body_text = ""

        return {
            **info,
            "opened": True,
            "opened_by": opened_by,
            "page_url": company_page.url,
            "page_title": company_page.title(),
            "page_text": body_text,
        }
    except Exception as exc:
        return {**info, "opened": False, "reason": f"{type(exc).__name__}: {exc}"}
    finally:
        if company_page is not None:
            try:
                company_page.close()
            except Exception:
                pass


def target_terms_from_context(context: dict) -> set[str]:
    priority_chunks = [
        " ".join(context.get("search_keywords", [])),
        " ".join(context.get("selected_products", [])),
    ]
    parsed = urlparse(context.get("source_url", ""))
    query = parse_qs(parsed.query)
    for key in ("ss", "kwd", "q", "pn", "search"):
        if query.get(key):
            priority_chunks.append(" ".join(query[key]))

    fallback_chunks = [
        context.get("source_title", ""),
        " ".join(context.get("form_snapshots", [])[-1:]),
        re.sub(r"[-_/.?=&|:]+", " ", parsed.path),
    ]

    stopwords = {
        "the", "and", "for", "with", "from", "this", "that", "your", "you",
        "are", "what", "want", "need", "have", "quantity", "submit", "next",
        "price", "latest", "supplier", "contact", "indiamart", "html", "www",
        "com", "https", "http", "proddetail", "impcat", "search",
        "city", "near", "in", "dist", "district", "india", "pan", "made",
        "new", "old", "greater", "noida", "delhi", "ghaziabad", "gurugram",
        "gurgaon", "faridabad", "mumbai", "thane", "pune", "bengaluru",
        "bangalore", "hyderabad", "chennai", "kolkata", "ahmedabad",
        "jaipur", "indore", "lucknow", "kanpur", "surat", "nagpur",
        "red", "blue", "green", "black", "white", "yellow", "orange",
        "pink", "purple", "brown", "grey", "gray", "silver", "golden",
        "square", "round", "small", "medium", "large",
    }

    def extract_terms(chunks: list[str]) -> set[str]:
        terms = set()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", " ".join(chunks).lower()):
            if token not in stopwords:
                terms.add(token)
        return terms

    terms = extract_terms(priority_chunks)
    if terms:
        return terms
    return extract_terms(fallback_chunks)


def heuristic_relevance_analysis(context: dict, card_infos: list[dict]) -> dict:
    target_terms = target_terms_from_context(context)
    card_results = []
    for card in card_infos:
        card_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", card["text"].lower()))
        overlap = sorted(target_terms.intersection(card_terms))
        if not target_terms:
            verdict = "Needs Review"
            reason = "Could not extract enough product/requirement terms for a strict relevance check."
            confidence = 35
            relevant = None
        elif overlap:
            verdict = "Pass"
            reason = f"Matched requirement terms: {', '.join(overlap[:8])}."
            confidence = min(85, 45 + (len(overlap) * 10))
            relevant = True
        else:
            verdict = "Needs Review"
            reason = "No direct keyword overlap found; AI relevance check was unavailable."
            confidence = 55
            relevant = None
        card_results.append(
            {
                "index": card["index"],
                "company": card["company"],
                "verdict": verdict,
                "relevant": relevant,
                "confidence": confidence,
                "reason": reason,
            }
        )

    return {
        "source": "heuristic",
        "overall_verdict": "Needs Review" if any(item["verdict"] == "Needs Review" for item in card_results) else "Pass",
        "summary": "AI relevance check unavailable; used keyword/context heuristic.",
        "cards": card_results,
    }


def parse_ai_json(content: str) -> dict | None:
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def runtime_llm_config() -> LLMConfig:
    workspace_settings = load_workspace_settings()

    def setting(primary_key: str, fallback_key: str, default: str) -> str:
        return (
            os.getenv(primary_key, "").strip()
            or os.getenv(fallback_key, "").strip()
            or str(workspace_settings.get(primary_key, "")).strip()
            or str(workspace_settings.get(fallback_key, "")).strip()
            or default
        )

    return LLMConfig(
        api_key=setting("AUTOMATION_LLM_API_KEY", "LITELLM_API_KEY", LLM_API_KEY),
        base_url=setting("AUTOMATION_LLM_BASE_URL", "LITELLM_API_BASE", LLM_BASE_URL),
        model=setting("AUTOMATION_LLM_MODEL", "LITELLM_MODEL", LLM_MODEL),
    )


def ai_relevance_analysis(context: dict, card_infos: list[dict]) -> dict:
    llm_config = runtime_llm_config()
    llm = OpenAICompatibleLLM(llm_config)
    if not llm.enabled:
        fallback = heuristic_relevance_analysis(context, card_infos)
        missing = []
        if not llm_config.api_key:
            missing.append("api_key")
        if not llm_config.base_url:
            missing.append("base_url")
        if not llm_config.model:
            missing.append("model")
        fallback["summary"] = (
            "AI relevance check unavailable "
            f"(missing {', '.join(missing) or 'unknown config'}); used keyword/context heuristic."
        )
        print(
            "AI relevance analysis disabled; "
            f"api_key={'set' if llm_config.api_key else 'missing'}, "
            f"base_url={'set' if llm_config.base_url else 'missing'}, "
            f"model={llm_config.model or 'missing'}."
        )
        return fallback

    print(f"AI relevance analysis enabled with model: {llm_config.model}")
    prompt = {
        "requirement_context": {
            "source_url": context.get("source_url", ""),
            "source_title": context.get("source_title", ""),
            "selected_products": context.get("selected_products", []),
            "quantities": context.get("quantities", []),
            "visible_form_context": context.get("form_snapshots", [])[-3:],
        },
        "recommendation_cards": [
            {
                "index": item["index"],
                "company": item["company"],
                "card_text": item["text"][:1200],
            }
            for item in card_infos
        ],
    }
    content = llm.complete(
        [
            {
                "role": "system",
                "content": (
                    "You evaluate if a supplier recommendation is RELEVANT to a buyer's enquiry. "
                    "FOCUS: Does the supplier/company likely sell products matching the buyer's requirement? "
                    "IGNORE card structure, UI elements, or formatting issues - only evaluate product relevance. "
                    "Return JSON with keys: overall_verdict (Pass/Fail/Needs Review), summary, cards. "
                    "Each card must have: index, company, verdict, relevant (bool), confidence (0-100), reason. "
                    "Verdict=Pass if supplier likely sells the required product. Verdict=Fail only if clearly irrelevant."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
        temperature=0.1,
        timeout=30,
    )
    if not content:
        fallback = heuristic_relevance_analysis(context, card_infos)
        fallback["summary"] = "AI relevance check returned no content; used keyword/context heuristic."
        print("AI relevance analysis returned no content; using keyword/context heuristic.")
        return fallback

    parsed = parse_ai_json(content)
    if not parsed:
        fallback = heuristic_relevance_analysis(context, card_infos)
        fallback["summary"] = "AI relevance response could not be parsed; used keyword/context heuristic."
        print("AI relevance analysis response could not be parsed; using keyword/context heuristic.")
        return fallback

    parsed.setdefault("source", "ai")
    parsed.setdefault("overall_verdict", "Needs Review")
    parsed.setdefault("summary", "AI relevance analysis completed.")
    parsed.setdefault("cards", [])
    print(f"AI relevance analysis completed: {parsed.get('overall_verdict')}")
    return parsed


def card_relevance_failures(analysis: dict, card_index: int) -> list[str]:
    failures = []
    for card_result in analysis.get("cards", []):
        if int(card_result.get("index", -1)) != card_index:
            continue
        verdict = str(card_result.get("verdict", "")).strip().lower()
        relevant = card_result.get("relevant")
        
        # Convert confidence to int, handling both numeric and string values
        confidence_raw = card_result.get("confidence") or 0
        if isinstance(confidence_raw, str):
            confidence_map = {"high": 85, "medium": 55, "low": 35}
            confidence = confidence_map.get(confidence_raw.lower(), 0)
        else:
            try:
                confidence = int(confidence_raw)
            except (ValueError, TypeError):
                confidence = 0
        
        reason = card_result.get("reason") or "AI marked this recommendation as not relevant."
        
        # Only fail if AI explicitly says product is irrelevant (not due to card structure/UI issues)
        # Ignore rejections based on "card is not genuine", "UI elements", "page structure" etc.
        is_structure_complaint = any(phrase in reason.lower() for phrase in [
            "ui element", "page structure", "navigation", "filter", "scraped",
            "not a genuine", "not genuine", "dumped content", "page content"
        ])
        
        if verdict == "fail" and not is_structure_complaint and (relevant is False and confidence >= 70):
            failures.append(f"Product not relevant: {reason[:100]}")
        break
    return failures


def format_analysis_summary(analysis: dict) -> str:
    verdict = analysis.get('overall_verdict', 'Needs Review')
    summary = analysis.get('summary', '')
    # Extract first reason if available
    first_reason = ""
    for card_result in analysis.get("cards", [])[:1]:
        reason = card_result.get('reason', '').split('. ')[0]
        if reason:
            first_reason = f" - {reason[:200]}"
    return f"AI Analysis: {verdict}{first_reason}"


def build_card_failure_message(
    *,
    card_index: int,
    failures: list[str],
    company_details: dict,
    analysis: dict,
) -> str:
    company_name = company_details.get("name") or "Unknown company"
    primary_failure = failures[0] if failures else "Recommendation quality check failed"
    # Limit to main reason only
    if len(primary_failure) > 120:
        primary_failure = primary_failure[:117] + "..."
    
    relevance_summary = format_analysis_summary(analysis)
    
    return compact_text(
        f"❌ Card {card_index}: {company_name}\n"
        f"Issue: {primary_failure}\n"
        f"{relevance_summary}",
        limit=500,
    )


def validate_recommendation_cards(page) -> str:
    base_page = raw_page(page)
    context = requirement_context(page)
    try:
        base_page.wait_for_selector(RECOMMENDATION_CARD_SELECTOR, timeout=15000)
    except Exception:
        pass

    cards = base_page.locator(RECOMMENDATION_CARD_SELECTOR)
    card_count = cards.count()
    if card_count < 3:
        company_details = inspect_company_page_for_failure(page)
        raise AssertionError(
            build_card_failure_message(
                card_index=1,
                failures=[f"Expected at least 3 recommendation cards, found {card_count}"],
                company_details=company_details,
                analysis=heuristic_relevance_analysis(context, []),
            )
        )

    card_infos = []
    for index in range(3):
        card = cards.nth(index)
        card_text = card.inner_text(timeout=5000)
        company_info = company_info_from_card(card)
        card_infos.append(
            {
                "index": index + 1,
                "company": company_info.get("name", "Unknown company"),
                "text": card_text,
            }
        )

    analysis = ai_relevance_analysis(context, card_infos)

    for index in range(3):
        card = cards.nth(index)
        card_text = card_infos[index]["text"]
        failures = []

        try:
            response_rate = extract_response_rate(card_text)
            if response_rate < 65:
                failures.append(
                    f"Response Rate is {response_rate}, expected at least 65"
                )
        except AssertionError as exc:
            failures.append(str(exc))

        try:
            rating, rater_count = extract_rating_details(card_text)
            if rating < 3.5:
                failures.append(f"Rating is {rating}, expected at least 3.5")
            if rater_count < 5:
                failures.append(f"Rater count is {rater_count}, expected at least 5")
        except AssertionError as exc:
            failures.append(str(exc))

        if not has_gst(card_text):
            failures.append("Missing GST")

        try:
            member_years = extract_member_years(card_text)
            if member_years < 1:
                failures.append(
                    f"Member age is {member_years:.1f} years, expected at least 1"
                )
        except AssertionError as exc:
            failures.append(str(exc))

        failures.extend(card_relevance_failures(analysis, index + 1))

        if failures:
            company_details = inspect_company_page_for_failure(page, card)
            raise AssertionError(
                build_card_failure_message(
                    card_index=index + 1,
                    failures=failures,
                    company_details=company_details,
                    analysis=analysis,
                )
            )

    return format_analysis_summary(analysis)
