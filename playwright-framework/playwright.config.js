import fs from "node:fs";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const authFiles = {
  enquiry: "test-results/auth/enquiry-buyer.json",
  pbr: "test-results/auth/pbr-buyer.json",
  bmc: "test-results/auth/bmc-buyer.json",
};

function hasStoredSession(authFile) {
  if (process.env.FORCE_LOGIN === "true") {
    return false;
  }
  const resolvedPath = path.resolve(authFile);
  return fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).size > 2;
}

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["json", { outputFile: "test-results/results.json" }],
    ["./utils/sheet-reporter.js"],
  ],
  use: {
    baseURL: process.env.ENQUIRY_BASE_URL || "https://dir.indiamart.com",
    headless: process.env.HEADLESS !== "false",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "enquiry-login",
      testMatch: /enquiry\/setup\/buyer-login\.setup\.js/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
    {
      name: "pbr-login",
      testMatch: /pbr\/setup\/buyer-login\.setup\.js/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
    {
      name: "bmc-login",
      testMatch: /bmc\/setup\/buyer-login\.setup\.js/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
    {
      name: "enquiry-chromium",
      testMatch: "**/enquiry/smoke/*.spec.js",
      dependencies: hasStoredSession(authFiles.enquiry) ? [] : ["enquiry-login"],
      use: {
        ...devices["Desktop Chrome"],
        storageState: authFiles.enquiry,
      },
    },
    {
      name: "pbr-chromium",
      testMatch: /pbr\/smoke\/.*\.spec\.js/,
      dependencies: hasStoredSession(authFiles.pbr) ? [] : ["pbr-login"],
      use: {
        ...devices["Desktop Chrome"],
        storageState: authFiles.pbr,
      },
    },
    {
      name: "bmc-chromium",
      testMatch: /bmc\/smoke\/.*\.spec\.js/,
      dependencies: hasStoredSession(authFiles.bmc) ? [] : ["bmc-login"],
      use: {
        ...devices["Desktop Chrome"],
        storageState: authFiles.bmc,
      },
    },
  ],
  outputDir: "test-results/artifacts",
});
