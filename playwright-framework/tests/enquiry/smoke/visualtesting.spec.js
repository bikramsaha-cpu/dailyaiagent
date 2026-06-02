import { test, expect } from '@playwright/test';

test('Visual Testing', async ({ page }) => {
  await page.goto('https://dir.indiamart.com/');
  await expect(await page.screenshot()).toMatchSnapshot('dirhome-page.png');
});