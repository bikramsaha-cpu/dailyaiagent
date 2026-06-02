import { expect, test } from "@playwright/test";

import { clickContactSupplier, enquiryUrls, submitEnquiryQuestions, verifyFinalPageState } from "../enquiry-helpers.js";

test.describe("Enquiry regression tests", () => {
  test("buyer can submit an enquiry from DIR impact category page", async ({ page }) => {
    await test.step("Open DIR impact category page as logged-in buyer", async () => {
      await page.goto(enquiryUrls.impcat);
      await expect(page.locator("body"), "Impact category page should load").toBeVisible();
    });

    await test.step("Open enquiry form from Contact Supplier CTA", async () => {
      await clickContactSupplier(page, "button[data-click='^CTAContactSupplier'], button:has-text('Contact Supplier')");
    });

    await test.step("Submit DIR enquiry form questions", async () => {
      await submitEnquiryQuestions(page, 5);
    });

    await verifyFinalPageState(page);
  });
});
