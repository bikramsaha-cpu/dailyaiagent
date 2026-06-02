import { expect, test } from "@playwright/test";

import {
  clickContactSupplier,
  openSearchPage,
  searchForProduct,
  searchTerms,
  submitEnquiryQuestions,
  verifyFinalPageState,
} from "../enquiry-helpers.js";

test.describe("Enquiry smoke tests", () => {
  test("buyer can submit an enquiry from search city results", async ({ page }) => {
    await test.step("Open enquiry search page as logged-in buyer", async () => {
      await openSearchPage(page);
    });

    await test.step(`Search for product: ${searchTerms.city}`, async () => {
      await searchForProduct(page, searchTerms.city);
    });

    await test.step("Open first enquiry form", async () => {
      await clickContactSupplier(page);
    });

    await test.step("Submit enquiry form questions", async () => {
      await submitEnquiryQuestions(page, 4);
    });

    await verifyFinalPageState(page);
    await expect(page.locator("body"), "Browser should remain on a valid page after the enquiry flow").toBeVisible();
  });
});
