import { BasePage } from "../base-page";
import { expect } from "@playwright/test";

import { enquiryData } from "../../data/enquiry";

export class SearchPage extends BasePage {
  async open(): Promise<void> {
    await this.step("Open enquiry search page", async () => {
      await this.goto(enquiryData.baseUrl);
      await expect(this.page.locator("input#search_string"), "Search input should be visible").toBeVisible();
      await expect(this.page.locator("input#btnSearch"), "Search button should be visible").toBeVisible();
    });
  }

  async searchFor(term = enquiryData.searchTerm): Promise<void> {
    await this.step(`Search for product: ${term}`, async () => {
      await this.page.locator("input#search_string").fill(term);
      await this.page.locator("input#btnSearch").click();
      await expect(
        this.page.locator("button.contactsupplier, button:has-text('Contact Supplier')").first(),
        "Search result should show a Contact Supplier button",
      ).toBeVisible({ timeout: 15_000 });
    });
  }

  async selectAllIndia(): Promise<void> {
    await this.step("Select All India city chip", async () => {
      const allIndiaChip = this.page.locator("ul#city-scrollbar1 li.newcitychip").first();
      await expect(allIndiaChip, "All India filter should be visible").toBeVisible();
      await allIndiaChip.click();
    });
  }

  async clickFirstContactSupplier(): Promise<void> {
    await this.step("Click first Contact Supplier CTA", async () => {
      await this.page
        .getByRole("button", { name: /contact supplier/i })
        .or(this.page.locator("button.contactsupplier"))
        .first()
        .click({ timeout: 15_000 });
      await expect(
        this.page.locator("button.submit-button, button:has-text('Next'), input#t0901_submit").first(),
        "Enquiry form should open after clicking Contact Supplier",
      ).toBeVisible({ timeout: 15_000 });
    });
  }
}
