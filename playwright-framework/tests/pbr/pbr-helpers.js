import { expect } from "@playwright/test";

export const pbrSelectors = {
  formCta:
    "button.submit-button, button:has-text('Next'), input#t0901_submit, input#t0101_submit, input#t0102_submit, input.form-btn[type='submit']",
  productInput: "input[name='q_desc'], input[name='product_name'], input[placeholder*='product'], textarea",
};

export async function openPbrCase(page, testCase) {
  await page.goto(testCase.url, { waitUntil: "domcontentloaded" });
  await expect(page.locator("body"), `${testCase.title} page should load`).toBeVisible();
}

export async function openPbrForm(page, testCase) {
  const trigger = page.locator(testCase.openSelector).first();
  await expect(trigger, `${testCase.title} submit requirement CTA should be visible`).toBeVisible({ timeout: 15_000 });
  await trigger.scrollIntoViewIfNeeded();
  await trigger.click();
  await expect(page.locator(pbrSelectors.formCta).first(), `${testCase.title} PBR form CTA should be visible`).toBeVisible({
    timeout: 15_000,
  });
}

export async function fillProductNameIfNeeded(page, testCase) {
  if (!testCase.productName) {
    return;
  }
  const input = page.locator(pbrSelectors.productInput).first();
  if (await input.isVisible({ timeout: 3000 }).catch(() => false)) {
    await input.fill(testCase.productName);
  }
}

export async function submitPbrForm(page, testCase) {
  for (let index = 0; index < testCase.ctaClicks; index += 1) {
    const cta = page.locator(pbrSelectors.formCta).first();
    await expect(cta, `${testCase.title} form CTA ${index + 1} should be visible`).toBeVisible({ timeout: 10_000 });
    await expect(cta, `${testCase.title} form CTA ${index + 1} should be enabled`).toBeEnabled();
    await cta.click();
    await page.waitForTimeout(800);
  }
  await expect(page.locator("body"), `${testCase.title} should finish on a valid page`).toBeVisible();
}

export async function runPbrCase(page, testCase) {
  await openPbrCase(page, testCase);
  await openPbrForm(page, testCase);
  await fillProductNameIfNeeded(page, testCase);
  await submitPbrForm(page, testCase);
}
