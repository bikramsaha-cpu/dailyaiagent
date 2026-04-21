from __future__ import annotations

from collections import defaultdict

from core.healing import attach_healing
from core.step_runner import run_step

MESSAGE_CENTRE_URL = "https://buyer.indiamart.com/enquiry/messagecentre/"

CONTACT_CARD_SELECTOR = (
    "div.message-user-name-section, "
    ".message-user-name-section, "
    ".left_det_show, "
    "div[class*='message-user-name']"
)

CONTACT_NAME_SELECTOR = (
    "div.message-user-name-section div.wrd_elip.c_name, "
    "div.message-user-name-section .c_name, "
    "div.wrd_elip.c_name, "
    ".c_name"
)

CONVERSATION_HEADER_SELECTOR = (
    ".header-font, "
    "div[class*='header'][class*='font'], "
    "div[class*='conversation'] h1, "
    "div[class*='conversation'] h2"
)

MESSAGE_SEARCH_INPUT_SELECTOR = (
    "input#searchauto, "
    "input[placeholder*='Search'], "
    "input[placeholder*='search']"
)


def build_page(raw_page, *, test_name: str):
    return attach_healing(
        raw_page,
        suite_name="BMC",
        module_name="MessageCentre",
        test_name=test_name,
    )


def make_log_step(*, page, browser_name, run_time, browser_results, logger, mobile_number):
    def log_step(step_name, func):
        return run_step(
            step_name=step_name,
            func=func,
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=mobile_number,
        )

    return log_step


def open_message_centre(page, timeout: int = 60000):
    page.goto(MESSAGE_CENTRE_URL, wait_until="domcontentloaded", timeout=timeout)
    wait_for_contact_card(page, timeout=15000)


def wait_for_contact_name(page, timeout: int = 15000):
    page.wait_for_selector(
        CONTACT_NAME_SELECTOR,
        timeout=timeout,
        intent="wait for first contact name in message centre",
        text="Contact Name",
        keywords=["contact", "message centre", "conversation", "buyer"],
    )
    return page.locator(CONTACT_NAME_SELECTOR).first


def wait_for_contact_card(page, timeout: int = 15000):
    page.wait_for_selector(
        CONTACT_CARD_SELECTOR,
        timeout=timeout,
        intent="wait for message centre contact list",
        text="Contact",
        keywords=["contact", "message centre", "conversation", "buyer"],
    )
    return page.locator(CONTACT_CARD_SELECTOR).first


def first_contact_name(page, timeout: int = 15000) -> str:
    locator = wait_for_contact_name(page, timeout=timeout)
    return locator.inner_text().strip()


def open_first_contact(page, timeout: int = 15000) -> str:
    locator = wait_for_contact_name(page, timeout=timeout)
    name = locator.inner_text().strip()
    locator.click(
        intent="open first contact in message centre",
        text=name,
        role="button",
        role_name=name,
        keywords=["contact", "message centre", "conversation", name],
    )
    return name


def wait_for_conversation_header(page, timeout: int = 15000):
    page.wait_for_selector(
        CONVERSATION_HEADER_SELECTOR,
        timeout=timeout,
        intent="wait for open conversation header in message centre",
        text="Conversation Header",
        keywords=["conversation", "header", "message centre", "buyer"],
    )
    return page.locator(CONVERSATION_HEADER_SELECTOR).first


def wait_for_search_input(page, timeout: int = 15000):
    page.wait_for_selector(
        MESSAGE_SEARCH_INPUT_SELECTOR,
        timeout=timeout,
        intent="wait for message centre search input",
        text="Search",
        keywords=["search", "message centre", "buyer", "contact"],
    )
    return page.locator(MESSAGE_SEARCH_INPUT_SELECTOR).first


def empty_browser_results():
    return defaultdict(lambda: {"Pass": 0, "Fail": 0})
