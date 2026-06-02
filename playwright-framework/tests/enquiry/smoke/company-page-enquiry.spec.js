import { expect, test } from "@playwright/test";

import { clickContactSupplier, enquiryUrls, submitEnquiryQuestions, verifyFinalPageState } from "../enquiry-helpers.js";

test.describe("Enquiry Submission Test from the MDC Company Page", () => {

  // test case 1: Verify user is able to post an enquiry from MDC Page Header Contact Supplier CTA
  test("Verify user is able to post and enquiry from MDC Page Header Contact Supplier CTA", async ({ page }) => {
    await test.step("Open company page as logged-in buyer", async () => {
      await page.goto(enquiryUrls.company);
      await expect(page.locator("body"), "Company page should load").toBeVisible();
    });

    await test.step("Open enquiry form from header Contact supplier CTA", async () => {
      await expect(
        page.locator(".btn-contact-supplier").first(),
        "Contact Supplier CTA should be visible"
      ).toBeVisible();

      await page.locator(".btn-contact-supplier").first().click();
      await page.locator("label[for='product-1']").click();
      await expect(page.locator(".product-submit-btn")).toBeVisible();
      await page.locator(".product-submit-btn").click();
      });

   await test.step("Complete enquiry form by clicking Next through all ISQ screens", async () => {
   const enquiryCta = page.locator(
    "button.submit-button, input[value='Next'], input#t0901_submit"
  );

  for (let step = 1; step <= 5; step++) {
    const nextButton = enquiryCta.first();

      await expect(
        nextButton,
        `Next button should be visible on question ${step}`
      ).toBeVisible({ timeout: 10_000 });

      await expect(
        nextButton,
        `Next button should be enabled on question ${step}`
      ).toBeEnabled();

      await nextButton.click();
    }
  });
    await verifyFinalPageState(page);
  });

// test case 2: Verify user is able to post an enquiry from MDC Page Header Call NOW CTA
  test("Verify user is able to post an enquiry from MDC Page Header Call NOW CTA", async ({ page }) => {
  let companyName;

  await test.step("Open company page as logged-in buyer", async () => {
    await page.goto(enquiryUrls.company);
    await expect(page.locator("body"), "Company page should load").toBeVisible();

    companyName = (await page.locator(".header-content h1").innerText()).trim();
  });

  await test.step("Open enquiry form from header CALL NOW CTA", async () => {
    await expect(
      page.locator(".btn-view-mobile").first(),
      "Call NOW CTA should be visible"
    ).toBeVisible();

    await page.locator(".btn-view-mobile").first().click();
    await page.locator("label[for='product-1']").click();
    await expect(page.locator(".product-submit-btn")).toBeVisible();
    await page.locator(".product-submit-btn").click();
  });

  await test.step("Complete enquiry form by clicking Next through all ISQ screens", async () => {
    const enquiryCta = page.locator(
      "button.submit-button, input[value='Next'], input#t0901_submit"
    );

    for (let step = 1; step <= 5; step++) {
      const nextButton = enquiryCta.first();

      await expect(nextButton, `Next button should be visible on question ${step}`)
        .toBeVisible({ timeout: 10_000 });

      await expect(nextButton, `Next button should be enabled on question ${step}`)
        .toBeEnabled();

      await nextButton.click();
    }
  });

  await expect(page.locator(".thSentTo a")).toHaveText(companyName);
  console.log("Company name in Thank You page matches the company Name:", companyName);
  await verifyFinalPageState(page);
});


















});
