from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

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

BMC_HEADLESS = os.getenv("AUTOMATION_BMC_HEADLESS", "1").strip().lower() not in {"0", "false", "no"}
BMC_SLOW_MO = int(os.getenv("AUTOMATION_BMC_SLOW_MO", "100"))
DEFAULT_BMC_LOGIN_PHONE = os.getenv("AUTOMATION_DEFAULT_LOGIN_PHONE", "9643193481")
DEFAULT_BMC_LOGIN_OTP = os.getenv("AUTOMATION_DEFAULT_LOGIN_OTP", "1956")
SESSION_DIR = Path(os.getenv("AUTOMATION_SESSION_DIR", str(Path(__file__).resolve().parents[1] / "artifacts" / "sessions" / "bmc")))
SESSION_FILE_PATH = str(SESSION_DIR / "bmclogin.json")


def ensure_session_dir():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def launch_browser(playwright, browser_name: str, *, slow_mo: int | None = None):
    return getattr(playwright, browser_name).launch(
        headless=BMC_HEADLESS,
        slow_mo=BMC_SLOW_MO if slow_mo is None else slow_mo,
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
