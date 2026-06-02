import { test } from "@playwright/test";

import { loginBuyerAndSaveSession } from "../../shared/buyer-login.js";

const buyerAuthFile = "test-results/auth/bmc-buyer.json";
const buyerPhone = process.env.BMC_LOGIN_PHONE || process.env.AUTOMATION_DEFAULT_LOGIN_PHONE || "9643193481";
const buyerOtp = process.env.BMC_LOGIN_OTP || process.env.AUTOMATION_DEFAULT_LOGIN_OTP || "1956";

test("bmc buyer login saves authenticated session", async ({ page }) => {
  await loginBuyerAndSaveSession(page, {
    authFile: buyerAuthFile,
    phone: buyerPhone,
    otp: buyerOtp,
    moduleLabel: "BMC",
  });
});
