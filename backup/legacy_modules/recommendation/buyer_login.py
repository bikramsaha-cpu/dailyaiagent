import os
import shutil
import sys
import time
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.settings import DEFAULT_LOGIN_OTP, DEFAULT_LOGIN_PHONE, SESSION_DIR
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


SESSION_FILE_PATH = SESSION_DIR / "enqlogin.json"
LEGACY_SESSION_FILE_PATH = Path("/var/log/web_tester_logs/enqlogin.json")
LOGIN_HEADLESS = os.getenv("AUTOMATION_RECOMMENDATION_HEADLESS", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}
LOGIN_SLOW_MO = int(os.getenv("AUTOMATION_RECOMMENDATION_SLOW_MO", "100"))


def get_active_page(context, current_page):
    try:
        if current_page and not current_page.is_closed():
            return current_page
    except Exception:
        pass

    for candidate in reversed(context.pages):
        try:
            if not candidate.is_closed():
                return candidate
        except Exception:
            continue
    return current_page


def wait_for_login_success(context, page, timeout_ms=20000):
    success_selectors = [
        "text=Dashboard",
        "text=My Orders",
        "text=Messages",
        "text=My Profile",
        "text=Post RFQ",
        "text=Hi ",
    ]
    deadline = time.time() + (timeout_ms / 1000)

    while time.time() < deadline:
        page = get_active_page(context, page)
        try:
            for selector in success_selectors:
                loc = page.locator(selector)
                if loc.count() and loc.first.is_visible():
                    return page
        except Exception:
            pass

        try:
            url = page.url or ""
            if "buyer.indiamart.com" in url and "login" not in url:
                return page
        except Exception:
            pass

        time.sleep(0.5)

    raise PlaywrightTimeoutError("Login success indicators not found")


def fill_otp_boxes(page, otp: str) -> bool:
    otp_digits = otp.strip()
    if not otp_digits:
        return False

    preferred_groups = [
        "div.nrp-otp-boxes input.nrp-otp-input",
        ".nrp-otp-boxes input[maxlength='1']",
        "input.nrp-otp-input",
        "input[maxlength='1']",
    ]

    for selector in preferred_groups:
        boxes = page.locator(selector)
        try:
            count = boxes.count()
        except Exception:
            continue
        if count < len(otp_digits):
            continue

        for index, digit in enumerate(otp_digits):
            box = boxes.nth(index)
            try:
                box.wait_for(state="visible", timeout=5000)
                box.click()
                box.fill("")
                box.type(digit, delay=50)
            except Exception:
                try:
                    box.fill(digit)
                except Exception:
                    return False
        return True

    return False


def fill_single_otp_input(page, otp: str) -> bool:
    otp_locators = [
        "input[placeholder='----']",
        "input[autocomplete='one-time-code']",
        "input[name='otp']",
        "input[id*='otp']",
        "input[maxlength='4']",
    ]

    for selector in otp_locators:
        loc = page.locator(selector)
        try:
            if loc.count() and loc.first.is_visible():
                loc.first.click()
                loc.first.fill(otp)
                return True
        except Exception:
            continue
    return False


def click_verify_if_present(page):
    verify_selectors = [
        "input#signInSubmitButton[value='Verify OTP']",
        "button:has-text('Verify OTP')",
        "button:has-text('Verify')",
        "input[value='Verify OTP']",
    ]

    for selector in verify_selectors:
        loc = page.locator(selector)
        try:
            if loc.count() and loc.first.is_visible(timeout=1000):
                loc.first.click()
                return True
        except Exception:
            continue
    return False


def save_session(context):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(SESSION_FILE_PATH))

    print(f"Login session saved to {SESSION_FILE_PATH}")
    try:
        LEGACY_SESSION_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SESSION_FILE_PATH, LEGACY_SESSION_FILE_PATH)
        print(f"Login session copied to {LEGACY_SESSION_FILE_PATH}")
    except OSError as exc:
        print(f"Legacy session copy skipped: {exc}")


def login_and_save_session():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=LOGIN_HEADLESS, slow_mo=LOGIN_SLOW_MO)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("Navigating to buyer login page...")
            page.goto("https://buyer.indiamart.com/login", timeout=60000)

            print("Entering mobile number...")
            page.wait_for_selector("input#mobilemy, input[type='tel'], input[name='mobile']", timeout=15000)
            mobile_locator = page.locator("input#mobilemy, input[type='tel'], input[name='mobile']").first
            mobile_locator.fill(DEFAULT_LOGIN_PHONE)

            print("Clicking Send OTP...")
            page.locator(
                "#signInSubmitButton, button#signInSubmitButton, button:has-text('Send OTP'), input[value='Send OTP']"
            ).first.click()

            print("Entering configured OTP...")
            page.wait_for_selector(
                "div.nrp-otp-boxes, input.nrp-otp-input, input[maxlength='1'], "
                "input[autocomplete='one-time-code'], input[name='otp'], input[id*='otp']",
                timeout=15000,
            )
            if not fill_otp_boxes(page, DEFAULT_LOGIN_OTP) and not fill_single_otp_input(
                page,
                DEFAULT_LOGIN_OTP,
            ):
                raise PlaywrightTimeoutError("OTP input not found")

            page.wait_for_timeout(1500)
            click_verify_if_present(page)

            print("Waiting for post-login confirmation...")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightError:
                page = get_active_page(context, page)

            page = get_active_page(context, page)
            wait_for_login_success(context, page, timeout_ms=20000)
            print("OTP verified and login successful.")

            save_session(context)
            return 0
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"Login failed: {type(exc).__name__}: {exc}")
            try:
                page = get_active_page(context, page)
                page.screenshot(path="login_not_confirmed.png", full_page=True)
            except Exception:
                pass
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(login_and_save_session())
