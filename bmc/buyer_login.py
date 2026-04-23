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
        page.locator("input#signInSubmitButton, button:has-text('Send OTP'), input[value='Send OTP']").first.click()

        try:
            print("Entering configured OTP...")
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
                digit_boxes = page.locator("input[maxlength='1']")
                if digit_boxes.count() >= len(DEFAULT_BMC_LOGIN_OTP):
                    for index, digit in enumerate(DEFAULT_BMC_LOGIN_OTP):
                        digit_boxes.nth(index).fill(digit)
                else:
                    raise PlaywrightTimeoutError("OTP input not found")
            else:
                otp_input.fill(DEFAULT_BMC_LOGIN_OTP)
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
