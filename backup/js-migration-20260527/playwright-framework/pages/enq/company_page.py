from __future__ import annotations

from test_data.config import ENQ_COMPANY_URL
from pages.base_page import BasePage


class CompanyPage(BasePage):
    def open(self) -> None:
        self.step("Open Company Page", lambda: self.goto(ENQ_COMPANY_URL))

    def click_contact_supplier(self) -> None:
        self.step(
            "Click Contact Supplier",
            lambda: self.page.click(
                "#head-suplr",
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )
