import { expect, test } from "@playwright/test";

import { clickContactSupplier, enquiryUrls, submitEnquiryQuestions, verifyFinalPageState } from "../enquiry-helpers.js";

test.describe("Enquiry regression tests", () => {
  test("buyer can submit an enquiry from product detail page", async ({ page }) => {
    await test.step("Open product detail page as logged-in buyer", async () => {
      await page.goto(enquiryUrls.pdp);
      await expect(page.locator("body"), "Product detail page should load").toBeVisible();
    });

    await test.step("Open enquiry form from Contact Supplier CTA", async () => {
      await clickContactSupplier(
        page,
        "button:has-text('Contact Supplier'), a:has-text('Contact Supplier'), span:has-text('Contact Supplier')",
      );
    });

    await test.step("Submit PDP enquiry form questions", async () => {
      await submitEnquiryQuestions(page, 5);
    });

    await verifyFinalPageState(page);
  });
});
