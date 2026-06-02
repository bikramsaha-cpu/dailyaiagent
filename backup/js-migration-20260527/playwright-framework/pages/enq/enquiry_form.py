from __future__ import annotations

import time

from pages.base_page import BasePage


class EnquiryForm(BasePage):
    NEXT_BUTTON = "button.submit-button, button:has-text('Next')"
    SUBMIT_INPUT = "input#t0901_submit"
    ANY_CTA = (
        "button.submit-button, button:has-text('Next'), "
        "input#t0901_submit[value='Next'], input#t0901_submit[value='Submit'], input#t0901_submit"
    )

    def complete_search_city_flow(self) -> None:
        self.step("Navigate ISQs and submit", self._search_city_steps)

    def complete_search_all_india_flow(self) -> None:
        self.step("Complete enquiry form", self._search_all_india_steps)

    def complete_dir_flow(self) -> None:
        self.step("Navigate ISQs and submit", lambda: self._advance_until_done(max_clicks=6))

    def complete_pdp_flow(self) -> None:
        self.step("Click Next CTA 5 times", lambda: self._advance_until_done(max_clicks=6))

    def complete_company_page_flow(self) -> None:
        self.step("Click Next CTA 5 times", lambda: self._advance_until_done(max_clicks=6))

    def wait_for_thank_you(self, timeout_ms: int = 5000) -> None:
        self.step("Wait for Thank You Page", lambda: self.page.wait_for_timeout(timeout_ms))

    def _search_city_steps(self) -> None:
        self.page.wait_for_selector(self.NEXT_BUTTON, timeout=10000)
        self.page.click(self.NEXT_BUTTON)
        time.sleep(1)
        self.page.click(self.NEXT_BUTTON)
        time.sleep(1)
        self.page.wait_for_selector("input#t0901_submit[value='Next']", timeout=10000)
        self.page.click("input#t0901_submit[value='Next']")
        time.sleep(1)
        self.page.wait_for_selector("input#t0901_submit[value='Submit']", timeout=10000)
        self.page.click("input#t0901_submit[value='Submit']")

    def _search_all_india_steps(self) -> None:
        for _ in range(2):
            self.page.wait_for_selector("button.submit-button", timeout=10000)
            self.page.click("button.submit-button")
            time.sleep(1)
        self.page.wait_for_selector("input#t0901_submit[value='Next']", timeout=10000)
        self.page.click("input#t0901_submit[value='Next']")
        time.sleep(1)
        self.page.wait_for_selector("input#t0901_submit[value='Submit']", timeout=10000)
        self.page.click("input#t0901_submit[value='Submit']")
        time.sleep(2)

    def _pdp_steps(self) -> None:
        for index in range(5):
            if index < 3:
                self.page.wait_for_selector(self.NEXT_BUTTON, timeout=10000)
                self.page.click(self.NEXT_BUTTON)
            elif index == 3:
                self.page.wait_for_selector("input#t0901_submit[value='Next'], input#t0901_submit", timeout=10000)
                self.page.click("input#t0901_submit[value='Next'], input#t0901_submit")
            else:
                self.page.wait_for_selector("input#t0901_submit[value='Submit'], input#t0901_submit", timeout=10000)
                self.page.click("input#t0901_submit[value='Submit'], input#t0901_submit")
            time.sleep(1)

    def _click_submit_input(self, *, times: int) -> None:
        for _ in range(times):
            self.page.wait_for_selector(self.SUBMIT_INPUT, timeout=10000)
            self.page.click(self.SUBMIT_INPUT)
            time.sleep(1)

    def _advance_until_done(self, *, max_clicks: int) -> None:
        clicked = 0
        for _ in range(max_clicks):
            try:
                self.page.wait_for_selector(self.ANY_CTA, timeout=10000)
            except Exception:
                break
            locator = self.page.locator(self.ANY_CTA).first
            try:
                if not locator.is_visible():
                    break
            except Exception:
                break
            locator.click()
            clicked += 1
            time.sleep(1)
        if clicked == 0:
            raise TimeoutError("No enquiry form CTA was available to click")
