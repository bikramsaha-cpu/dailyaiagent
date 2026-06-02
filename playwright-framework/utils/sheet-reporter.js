import { appendSheetRows } from "./google-sheets.js";

function timestampParts() {
  const now = new Date();
  const date = [
    String(now.getDate()).padStart(2, "0"),
    String(now.getMonth() + 1).padStart(2, "0"),
    now.getFullYear(),
  ].join("-");
  const time = [
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0"),
  ].join(":");
  return { date, time };
}

function statusFromError(error) {
  return error ? "Fail" : "Pass";
}

function cleanTitle(title) {
  return title.replace(/\s+/g, " ").trim();
}

function flattenSteps(steps, depth = 0) {
  const rows = [];
  for (const step of steps) {
    if (["test.step", "expect"].includes(step.category)) {
      rows.push(step);
    }
    if (step.steps.length && depth < 3) {
      rows.push(...flattenSteps(step.steps, depth + 1));
    }
  }
  return rows;
}

function browserName(test) {
  return test.parent.project()?.name || "chromium";
}

function moduleFromTest(test) {
  const file = test.location.file.replaceAll("\\", "/");
  if (file.includes("/tests/pbr/")) {
    return { sheetName: process.env.PBR_SHEET_NAME || "Buyer Automation", tabName: process.env.PBR_SHEET_TAB || "PBR" };
  }
  if (file.includes("/tests/bmc/")) {
    return { sheetName: process.env.BMC_SHEET_NAME || "Buyer Automation", tabName: process.env.BMC_SHEET_TAB || "BMC" };
  }
  return { sheetName: process.env.ENQUIRY_SHEET_NAME || "Buyer Automation", tabName: process.env.ENQUIRY_SHEET_TAB || "ENQ" };
}

function remarksForStep(step) {
  if (step.error?.message) {
    return step.error.message.split("\n")[0];
  }
  return step.duration ? `${step.duration} ms` : "";
}

function rowsForTest(test, result) {
  const { date, time } = timestampParts();
  const testTitle = cleanTitle(test.title);
  const browser = browserName(test);
  const phone = process.env.ENQUIRY_LOGIN_PHONE || process.env.AUTOMATION_DEFAULT_LOGIN_PHONE || "";
  const steps = flattenSteps(result.steps);

  if (!steps.length) {
    return [[testTitle, "Test execution", statusFromError(result.error), result.error?.message || "", browser, phone, date, time]];
  }

  const rows = steps.map((step) => [
    testTitle,
    cleanTitle(step.title),
    statusFromError(step.error),
    remarksForStep(step),
    browser,
    phone,
    date,
    time,
  ]);
  if (result.error && !steps.some((step) => step.error)) {
    rows.push([testTitle, "Test result", "Fail", result.error.message || "Test failed", browser, phone, date, time]);
  }
  return rows;
}

export default class GoogleSheetReporter {
  async onTestEnd(test, result) {
    if ((process.env.ENQUIRY_LOG_TO_SHEET || "true").toLowerCase() === "false") {
      return;
    }

    const { sheetName, tabName } = moduleFromTest(test);
    try {
      await appendSheetRows(sheetName, tabName, rowsForTest(test, result));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`[sheet-reporter] Could not log ${test.title}: ${message}`);
    }
  }
}
