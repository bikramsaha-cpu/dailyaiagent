import { expect, test } from "@playwright/test";

export async function loginBuyerAndSaveSession(page, options) {
  await test.step(`Open buyer login page for ${options.moduleLabel}`, async () => {
    await page.goto("https://buyer.indiamart.com/login");
    await expect(page.locator("#mobilemy"), "Mobile input should be visible on buyer login page").toBeVisible();
  });

  await test.step("Enter buyer mobile number", async () => {
    await page.locator("#mobilemy").fill(options.phone);
    await page.locator(".nrp-submit-btn").click();
  });

  await test.step("Enter buyer OTP", async () => {
    const otpInputs = page.locator(".nrp-otp-boxes .nrp-otp-input");
    await expect(otpInputs.first(), "OTP inputs should be visible").toBeVisible();
    for (const [index, digit] of options.otp.split("").entries()) {
      await otpInputs.nth(index).fill(digit);
    }
  });

  await test.step("Verify buyer dashboard is visible", async () => {
    await expect(page.locator('span:has-text("Dashboard")'), "Dashboard should be visible after buyer login").toContainText(
      "Dashboard",
      { timeout: 20_000 },
    );
  });

  await test.step(`Save buyer session for ${options.moduleLabel}`, async () => {
    await page.context().storageState({ path: options.authFile });
  });
}
