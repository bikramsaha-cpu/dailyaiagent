import { test } from "@playwright/test";

import { pbrCases } from "../pbr-cases.js";
import { runPbrCase } from "../pbr-helpers.js";

test.describe("PBR legacy cases", () => {
  for (const testCase of pbrCases) {
    test(testCase.title, async ({ page }) => {
      await runPbrCase(page, testCase);
    });
  }
});
