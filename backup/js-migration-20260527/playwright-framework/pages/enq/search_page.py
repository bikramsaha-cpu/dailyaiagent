from __future__ import annotations

from test_data.config import DIR_BASE_URL
from pages.base_page import BasePage


class SearchPage(BasePage):
    def open(self) -> None:
        self.step("Open Search Page", lambda: self.goto(DIR_BASE_URL))

    def search_for(self, term: str) -> None:
        self.step("Enter search term", lambda: self.page.fill("input#search_string", term))
        self.step("Click Search button", lambda: self.page.click("input#btnSearch"))

    def select_all_india(self) -> None:
        self.step("Click All India Chip", lambda: self.page.click("ul#city-scrollbar1 li.newcitychip"))

    def click_first_contact_supplier(self) -> None:
        self.step(
            "Click first Contact Supplier CTA",
            lambda: self.page.click(
                "button.contactsupplier",
                timeout=10000,
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )
