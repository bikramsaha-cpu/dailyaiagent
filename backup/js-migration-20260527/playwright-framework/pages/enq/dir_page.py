from __future__ import annotations

from test_data.config import ENQ_IMPCAT_URL
from pages.base_page import BasePage


class DirPage(BasePage):
    def open_impcat(self) -> None:
        self.step("Open Impact Page", lambda: self.goto(ENQ_IMPCAT_URL))

    def click_contact_supplier(self) -> None:
        self.step(
            "Click Contact Supplier CTA",
            lambda: self.page.click(
                "[data-click^='CTAContactSupplier'], [data-click*='ContactSupplier'], button.contactsupplier, button:has-text('Contact Supplier')",
                intent="click contact supplier cta",
                text="Contact Supplier",
                role="button",
                role_name="Contact Supplier",
                keywords=["Contact Supplier", "CTA", "Supplier", "Contact"],
            ),
        )
