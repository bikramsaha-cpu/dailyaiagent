import { test as base } from "@playwright/test";

import { EnquiryForm } from "../pages/enquiry/enquiry-form";
import { SearchPage } from "../pages/enquiry/search-page";

type EnquiryFixtures = {
  searchPage: SearchPage;
  enquiryForm: EnquiryForm;
};

export const test = base.extend<EnquiryFixtures>({
  searchPage: async ({ page }, use) => {
    await use(new SearchPage(page));
  },
  enquiryForm: async ({ page }, use) => {
    await use(new EnquiryForm(page));
  },
});

export { expect } from "@playwright/test";
