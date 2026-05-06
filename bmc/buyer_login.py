import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from shared import (
    DEFAULT_BMC_LOGIN_OTP,
    DEFAULT_BMC_LOGIN_PHONE,
    SESSION_FILE_PATH,
    ensure_session_dir,
    launch_browser,
)


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


def login_and_save_session():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright, "chromium")
        context = browser.new_context()
        page = context.new_page()
        ensure_session_dir()

        print("Navigating to buyer login page...")
        page.goto("https://buyer.indiamart.com/login", timeout=60000)

        print("Entering mobile number...")
        page.wait_for_selector("input#mobilemy, input[type='tel'], input[name='mobile']", timeout=15000)
        mobile_locator = page.locator("input#mobilemy, input[type='tel'], input[name='mobile']").first
        mobile_locator.fill(DEFAULT_BMC_LOGIN_PHONE)

        print("Clicking Send OTP...")
        page.locator(
            "#signInSubmitButton, button#signInSubmitButton, button:has-text('Send OTP'), input[value='Send OTP']"
        ).first.click()

        try:
            print("Entering configured OTP...")
            page.wait_for_selector(
                "div.nrp-otp-boxes, input.nrp-otp-input, input[maxlength='1'], input[autocomplete='one-time-code'], input[name='otp'], input[id*='otp']",
                timeout=15000,
            )

            if not fill_otp_boxes(page, DEFAULT_BMC_LOGIN_OTP):
                otp_locators = [
                    "input[placeholder='----']",
                    "input[autocomplete='one-time-code']",
                    "input[name='otp']",
                    "input[id*='otp']",
                    "input[maxlength='4']",
                ]
                otp_input = None
                for selector in otp_locators:
                    loc = page.locator(selector)
                    try:
                        if loc.count() and loc.first.is_visible():
                            otp_input = loc.first
                            break
                    except Exception:
                        continue

                if otp_input is None:
                    raise PlaywrightTimeoutError("OTP input not found")

                otp_input.click()
                otp_input.fill(DEFAULT_BMC_LOGIN_OTP)

            page.wait_for_timeout(1500)
        except PlaywrightTimeoutError:
            print("OTP input not found.")
            browser.close()
            return 1

        try:
            print("Waiting for post-login confirmation...")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightError:
                page = get_active_page(context, page)

            page = get_active_page(context, page)
            wait_for_login_success(context, page, timeout_ms=20000)
            print("OTP verified and login successful.")
        except (PlaywrightTimeoutError, PlaywrightError):
            print("Login not confirmed. Session may not be saved.")
            try:
                page = get_active_page(context, page)
                page.screenshot(path="login_not_confirmed.png", full_page=True)
            except Exception:
                pass
            browser.close()
            return 1

        context.storage_state(path=SESSION_FILE_PATH)
        print(f"Login session saved to {SESSION_FILE_PATH}")
        browser.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(login_and_save_session())
