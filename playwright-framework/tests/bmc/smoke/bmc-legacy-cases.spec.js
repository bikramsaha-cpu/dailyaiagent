import { expect, test } from "@playwright/test";

import { bmcCases } from "../bmc-cases.js";
import { bmcSelectors, bmcUrls, openFirstConversation, openMessageCentre, sendMessage } from "../bmc-helpers.js";

test.describe("BMC legacy cases", () => {
  for (const testCase of bmcCases) {
    test(testCase.title, async ({ page }) => {
      if (testCase.kind === "buyer-page") {
        await page.goto(bmcUrls.buyerHome, { waitUntil: "domcontentloaded" });
        await expect(page.locator("body"), "Buyer page should load for logged-in user").toBeVisible();
        return;
      }

      if (testCase.kind === "open-message-centre") {
        await openMessageCentre(page);
        return;
      }

      if (testCase.kind === "open-conversation") {
        await openFirstConversation(page);
        return;
      }

      if (testCase.kind === "send-message") {
        await openFirstConversation(page);
        await sendMessage(page, `Automation check ${Date.now()}`);
        return;
      }

      if (testCase.kind === "search-city") {
        await openMessageCentre(page);
        const search = page.locator(bmcSelectors.search).first();
        await expect(search, "Message centre search input should be visible").toBeVisible();
        await search.fill(process.env.BMC_SEARCH_CITY || "Delhi");
        await expect(page.locator(bmcSelectors.contactCard).first(), "Search should keep contact results visible").toBeVisible();
        return;
      }

      await page.goto(bmcUrls.buyerHome, { waitUntil: "domcontentloaded" });
      const messageLink = page.locator("a[href*='message'], [class*='message'], #messageWid").first();
      await expect(messageLink, "Message navigation should be available from buyer header").toBeVisible({ timeout: 15_000 });
      await messageLink.click();
      await expect(page).toHaveURL(/message|chat|bmc|enquiry/i, { timeout: 15_000 });
    });
  }
});
