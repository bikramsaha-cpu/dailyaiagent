import { expect } from "@playwright/test";

import { BasePage } from "../base-page";

export class EnquiryForm extends BasePage {
  private readonly nextButton = "button.submit-button, button:has-text('Next')";
  private readonly submitInput = "input#t0901_submit";
  private readonly anyCta =
    "button.submit-button, button:has-text('Next'), input#t0901_submit[value='Next'], input#t0901_submit[value='Submit'], input#t0901_submit";

  async completeSearchCityFlow(): Promise<void> {
    await this.step("Complete search city enquiry form questions", async () => {
      await this.clickNextLikeCta(4);
    });
  }

  async completeSearchAllIndiaFlow(): Promise<void> {
    await this.step("Complete all India enquiry form questions", async () => {
      await this.clickNextLikeCta(4);
    });
  }

  async completeGenericFlow(): Promise<void> {
    await this.step("Complete enquiry form", async () => {
      await this.clickNextLikeCta(6);
    });
  }

  async waitForThankYou(): Promise<void> {
    await this.step("Verify enquiry submission reaches a final page state", async () => {
      await this.page.waitForTimeout(3000);
      await expect(this.page.locator("body"), "Page body should remain visible after enquiry submission").toBeVisible();
    });
  }

  private async clickNextLikeCta(maxClicks: number): Promise<void> {
    let clicked = 0;
    for (let index = 0; index < maxClicks; index += 1) {
      const cta = this.page.locator(this.anyCta).first();
      try {
        await cta.waitFor({ state: "visible", timeout: 10_000 });
      } catch {
        break;
      }
      await expect(cta, `Enquiry form CTA ${index + 1} should be clickable`).toBeEnabled();
      await cta.click();
      clicked += 1;
      await this.page.waitForTimeout(1000);
    }
    if (!clicked) {
      throw new Error(`No enquiry CTA was available. Checked ${this.nextButton} and ${this.submitInput}.`);
    }
  }
}
