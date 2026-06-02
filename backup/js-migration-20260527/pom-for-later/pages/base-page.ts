import { Page, test } from "@playwright/test";

export class BasePage {
  constructor(protected readonly page: Page) {}

  protected async step<T>(title: string, action: () => Promise<T>): Promise<T> {
    return test.step(title, action);
  }

  async goto(pathOrUrl: string): Promise<void> {
    await this.page.goto(pathOrUrl, { waitUntil: "domcontentloaded" });
  }
}
