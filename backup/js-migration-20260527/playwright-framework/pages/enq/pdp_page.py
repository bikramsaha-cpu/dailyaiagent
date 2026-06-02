from __future__ import annotations

from test_data.config import ENQ_PDP_URL
from pages.base_page import BasePage


class PdpPage(BasePage):
    def open(self) -> None:
        self.step("Open PDP Page", lambda: self.goto(ENQ_PDP_URL))

    def click_contact_supplier(self) -> None:
        self.step(
            "Click Contact Supplier",
            lambda: self.page.click(
                "button:has-text('Contact Supplier'), a:has-text('Contact Supplier'), span:has-text('Contact Supplier')",
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )
