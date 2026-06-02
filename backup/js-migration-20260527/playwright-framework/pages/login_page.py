from __future__ import annotations

import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from test_data.config import AUTH_SESSION_FILE, BMC_LOGIN_OTP, BMC_LOGIN_PHONE
from pages.base_page import BasePage


class LoginPage(BasePage):
    URL = "https://buyer.indiamart.com/login"

    def login_and_save_session(self) -> None:
        self.step("Open buyer login page", lambda: self.goto(self.URL))
        self.step("Enter mobile number", self._enter_mobile_number)
        self.step("Request OTP", self._request_otp)
        self.step("Enter OTP", self._enter_otp)
        self.step("Confirm login", self._confirm_login)
        AUTH_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.page.context.storage_state(path=str(AUTH_SESSION_FILE))

    def _enter_mobile_number(self) -> None:
        self.page.wait_for_selector("input#mobilemy, input[type='tel'], input[name='mobile']", timeout=15000)
        self.page.locator("input#mobilemy, input[type='tel'], input[name='mobile']").first.fill(BMC_LOGIN_PHONE)

    def _request_otp(self) -> None:
        self.page.locator(
            "#signInSubmitButton, button#signInSubmitButton, button:has-text('Send OTP'), input[value='Send OTP']"
        ).first.click()

    def _enter_otp(self) -> None:
        self.page.wait_for_selector(
            "div.nrp-otp-boxes, input.nrp-otp-input, input[maxlength='1'], "
            "input[autocomplete='one-time-code'], input[name='otp'], input[id*='otp']",
            timeout=15000,
        )
        if self._fill_otp_boxes(BMC_LOGIN_OTP):
            self.page.wait_for_timeout(1500)
            return

        for selector in (
            "input[placeholder='----']",
            "input[autocomplete='one-time-code']",
            "input[name='otp']",
            "input[id*='otp']",
            "input[maxlength='4']",
        ):
            loc = self.page.locator(selector)
            try:
                if loc.count() and loc.first.is_visible():
                    loc.first.click()
                    loc.first.fill(BMC_LOGIN_OTP)
                    self.page.wait_for_timeout(1500)
                    return
            except Exception:
                continue
        raise PlaywrightTimeoutError("OTP input not found")

    def _fill_otp_boxes(self, otp: str) -> bool:
        otp_digits = otp.strip()
        if not otp_digits:
            return False
        for selector in (
            "div.nrp-otp-boxes input.nrp-otp-input",
            ".nrp-otp-boxes input[maxlength='1']",
            "input.nrp-otp-input",
            "input[maxlength='1']",
        ):
            boxes = self.page.locator(selector)
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

    def _confirm_login(self) -> None:
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except PlaywrightError:
            pass
        self._wait_for_login_success(timeout_ms=20000)

    def _wait_for_login_success(self, timeout_ms: int = 20000) -> None:
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
            page = self._active_page()
            for selector in success_selectors:
                try:
                    loc = page.locator(selector)
                    if loc.count() and loc.first.is_visible():
                        self.page = page
                        return
                except Exception:
                    continue
            try:
                if "buyer.indiamart.com" in (page.url or "") and "login" not in page.url:
                    self.page = page
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise PlaywrightTimeoutError("Login success indicators not found")

    def _active_page(self):
        for candidate in reversed(self.page.context.pages):
            try:
                if not candidate.is_closed():
                    return candidate
            except Exception:
                continue
        return self.page
