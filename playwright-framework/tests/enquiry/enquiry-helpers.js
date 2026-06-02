import { expect } from "@playwright/test";

export const enquiryUrls = {
  home: process.env.ENQUIRY_BASE_URL || "https://dir.indiamart.com",
  impcat: process.env.ENQUIRY_IMPCAT_URL || "https://dir.indiamart.com/impcat/sugarcane-juice-machine.html",
  pdp:
    process.env.ENQUIRY_PDP_URL ||
    "https://www.indiamart.com/proddetail/sugarcane-juice-machine-2855214905512.html",
  company:
    process.env.ENQUIRY_COMPANY_URL ||
    "https://www.indiamart.com/web-solution-malda/",
};

export const searchTerms = {
  city: process.env.ENQUIRY_SEARCH_TERM || "hat",
  allIndia: process.env.ENQUIRY_ALL_INDIA_SEARCH_TERM || "headphones",
};

export const selectors = {
  searchInput: "input#search_string",
  searchButton: "input#btnSearch",
  allIndiaChip: "ul#city-scrollbar1 li.newcitychip",
  contactSupplier: "button.contactsupplier, button:has-text('Contact Supplier'), a:has-text('Contact Supplier')",
  enquiryCta:
    "button.submit-button, input[value='Next'], button.submit-button, input#t0901_submit",
};

export async function openSearchPage(page) {
  await page.goto(enquiryUrls.home);
  await expect(page.locator(selectors.searchInput), "Search input should be visible").toBeVisible();
}

export async function searchForProduct(page, term) {
  await page.locator(selectors.searchInput).fill(term);
  await page.locator(selectors.searchButton).click();
  await expect(page.locator(selectors.contactSupplier).first(), "Search result should show Contact Supplier").toBeVisible({
    timeout: 15_000,
  });
}

export async function selectAllIndia(page) {
  await expect(page.locator(selectors.allIndiaChip).first(), "All India chip should be visible").toBeVisible();
  await page.locator(selectors.allIndiaChip).first().click();
}

export async function clickContactSupplier(page, selector = selectors.contactSupplier) {
  await expect(page.locator(selector).first(), "Contact Supplier CTA should be visible").toBeVisible({ timeout: 15_000 });
  await page.locator(selector).first().click();
  await expect(page.locator(selectors.enquiryCta).first(), "Enquiry form CTA should be visible").toBeVisible({
    timeout: 15_000,
  });
}

export async function submitEnquiryQuestions(page, ctaClicks) {
  const formCta = page.locator(selectors.enquiryCta);
  for (let index = 0; index < ctaClicks; index += 1) {
    const firstCta = formCta.first();
    await expect(firstCta, `Enquiry CTA ${index + 1} should be visible`).toBeVisible({ timeout: 10_000 });
    await expect(firstCta, `Enquiry CTA ${index + 1} should be enabled`).toBeEnabled();
    await firstCta.click();
    await page.waitForTimeout(1000);
  }
}

export async function verifyFinalPageState(page) {
await page.waitForTimeout(3000);
await expect(await page.locator('#t0901msglink').textContent()).toBe(' Chat With Seller');
console.log("Verify The Chat With Seller Button Visiblity on Thank You Screen");

}
