import { test } from "@playwright/test";

import {
  clickContactSupplier,
  openSearchPage,
  searchForProduct,
  searchTerms,
  selectAllIndia,
  submitEnquiryQuestions,
  verifyFinalPageState,
} from "../enquiry-helpers.js";

test.describe("Enquiry smoke tests", () => {
  test("buyer can submit an enquiry from all India search results", async ({ page }) => {
    await test.step("Open enquiry search page as logged-in buyer", async () => {
      await openSearchPage(page);
    });

    await test.step(`Search for product: ${searchTerms.allIndia}`, async () => {
      await searchForProduct(page, searchTerms.allIndia);
    });

    await test.step("Select All India filter", async () => {
      await selectAllIndia(page);
    });

    await test.step("Open first enquiry form", async () => {
      await clickContactSupplier(page);
    });

    await test.step("Submit enquiry form questions", async () => {
      await submitEnquiryQuestions(page, 4);
    });

    await verifyFinalPageState(page);
  });
});
