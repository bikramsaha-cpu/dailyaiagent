import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import { NextRequest, NextResponse } from "next/server";

type ManagedTask = {
  id: string;
  kind: "module" | "url_agent";
  title: string;
  started_at: string;
  status: "running" | "completed" | "failed" | "stopped";
  browser_mode: "headed" | "headless";
  command: string;
  cwd: string;
  payload: Record<string, unknown>;
  pid?: number;
  finished_at?: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  proc?: ChildProcessWithoutNullStreams;
};

type RunRecord = {
  id: number;
  module_name: string;
  suite_name: string;
  started_at: string;
  finished_at: string;
  status: string;
  passed: number;
  failed: number;
  total: number;
  command?: string;
  stdout?: string;
  stderr?: string;
  report_path?: string;
  extra?: Record<string, unknown>;
};

const cwd = process.cwd();
const repoRoot = path.basename(cwd).toLowerCase() === "frontend" ? path.resolve(cwd, "..") : cwd;
const frameworkDir = path.join(repoRoot, "playwright-framework");
const testResultsDir = path.join(frameworkDir, "test-results");
const resultsJsonPath = path.join(testResultsDir, "results.json");
const runsJsonPath = path.join(testResultsDir, "daily-qa-runs.json");
const nodeCommand = process.execPath;
const playwrightCli = path.join(frameworkDir, "node_modules", "@playwright", "test", "cli.js");
const sheetCache = new Map<string, { createdAt: number; value: unknown }>();
const sheetCacheMs = Number(process.env.AUTOMATION_SHEET_CACHE_SECONDS || 45) * 1000;

const modules = [
  {
    id: "enquiry",
    label: "Enquiry Desktop",
    suite: "Enquiry",
    description: "Runs the clean JavaScript Playwright enquiry suite",
    sheet_name: "Buyer Automation",
    default_tab: "ENQ",
    runner: "playwright-framework",
  },
  {
    id: "pbr",
    label: "PBR Desktop",
    suite: "PBR",
    description: "Runs the clean JavaScript Playwright PBR suite",
    sheet_name: "Buyer Automation",
    default_tab: "PBR",
    runner: "playwright-framework",
  },
  {
    id: "bmc",
    label: "BMC Desktop",
    suite: "BMC",
    description: "Runs the clean JavaScript Playwright BMC suite",
    sheet_name: "Buyer Automation",
    default_tab: "BMC",
    runner: "playwright-framework",
  },
];

const globalForTasks = globalThis as typeof globalThis & {
  dailyQaTasks?: Map<string, ManagedTask>;
};
const tasks = globalForTasks.dailyQaTasks ?? new Map<string, ManagedTask>();
globalForTasks.dailyQaTasks = tasks;

function json(payload: unknown, status = 200) {
  return NextResponse.json(payload, { status });
}

function now() {
  return new Date().toISOString().slice(0, 19);
}

function readRuns(): RunRecord[] {
  try {
    return JSON.parse(fs.readFileSync(runsJsonPath, "utf8")) as RunRecord[];
  } catch {
    return [];
  }
}

function base64Url(input: string | Buffer) {
  return Buffer.from(input).toString("base64url");
}

function loadGoogleCredentials() {
  const envJson = process.env.AUTOMATION_GOOGLE_CREDENTIALS_JSON?.trim();
  if (envJson) {
    return JSON.parse(envJson) as { client_email: string; private_key: string; token_uri?: string };
  }

  const candidates = [
    process.env.AUTOMATION_GOOGLE_CREDENTIALS,
    process.env.GOOGLE_APPLICATION_CREDENTIALS,
    path.join(repoRoot, "credentials.json"),
    path.join(repoRoot, "backup", "js-migration-20260527", "enquiry", "credentials.json"),
  ].filter(Boolean) as string[];
  const credsPath = candidates.find((candidate) => fs.existsSync(candidate));
  if (!credsPath) {
    throw new Error("Google credentials not found. Set AUTOMATION_GOOGLE_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS.");
  }
  return JSON.parse(fs.readFileSync(credsPath, "utf8")) as {
    client_email: string;
    private_key: string;
    token_uri?: string;
  };
}

async function googleAccessToken() {
  const cacheKey = "google-token";
  const cached = sheetCache.get(cacheKey);
  if (cached && Date.now() - cached.createdAt < 50 * 60 * 1000) {
    return cached.value as string;
  }

  const creds = loadGoogleCredentials();
  const nowSeconds = Math.floor(Date.now() / 1000);
  const scope = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
  ].join(" ");
  const header = base64Url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = base64Url(
    JSON.stringify({
      iss: creds.client_email,
      scope,
      aud: creds.token_uri || "https://oauth2.googleapis.com/token",
      iat: nowSeconds,
      exp: nowSeconds + 3600,
    }),
  );
  const unsignedJwt = `${header}.${claim}`;
  const signature = crypto.createSign("RSA-SHA256").update(unsignedJwt).sign(creds.private_key);
  const assertion = `${unsignedJwt}.${base64Url(signature)}`;

  const response = await fetch(creds.token_uri || "https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion,
    }),
    cache: "no-store",
  });
  const payload = (await response.json()) as { access_token?: string; error_description?: string; error?: string };
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description || payload.error || "Google auth failed.");
  }
  sheetCache.set(cacheKey, { createdAt: Date.now(), value: payload.access_token });
  return payload.access_token;
}

async function googleJson<T>(url: string): Promise<T> {
  const token = await googleAccessToken();
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok) {
    const error = payload as { error?: { message?: string } };
    throw new Error(error.error?.message || `Google API request failed with ${response.status}`);
  }
  return payload as T;
}

async function spreadsheetIdForTitle(sheetName: string) {
  const cacheKey = `sheet-id:${sheetName}`;
  const cached = sheetCache.get(cacheKey);
  if (cached && Date.now() - cached.createdAt < sheetCacheMs) {
    return cached.value as string;
  }

  const escapedName = sheetName.replaceAll("\\", "\\\\").replaceAll("'", "\\'");
  const query = encodeURIComponent(
    `name='${escapedName}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false`,
  );
  const payload = await googleJson<{ files?: Array<{ id: string; name: string }> }>(
    `https://www.googleapis.com/drive/v3/files?q=${query}&fields=files(id,name)&supportsAllDrives=true&includeItemsFromAllDrives=true`,
  );
  const file = payload.files?.[0];
  if (!file?.id) {
    throw new Error(`Google Sheet not found: ${sheetName}`);
  }
  sheetCache.set(cacheKey, { createdAt: Date.now(), value: file.id });
  return file.id;
}

async function googleSheetTabs(sheetName: string, fallbackTab: string) {
  const cacheKey = `tabs:${sheetName}`;
  const cached = sheetCache.get(cacheKey);
  if (cached && Date.now() - cached.createdAt < sheetCacheMs) {
    return cached.value as string[];
  }
  const spreadsheetId = await spreadsheetIdForTitle(sheetName);
  const payload = await googleJson<{ sheets?: Array<{ properties?: { title?: string } }> }>(
    `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}?fields=sheets.properties.title`,
  );
  const tabs = payload.sheets?.map((sheet) => sheet.properties?.title).filter((title): title is string => Boolean(title)) || [
    fallbackTab,
  ];
  sheetCache.set(cacheKey, { createdAt: Date.now(), value: tabs });
  return tabs;
}

async function googleSheetRecords(sheetName: string, tabName: string, forceRefresh: boolean) {
  const cacheKey = `records:${sheetName}:${tabName}`;
  const cached = sheetCache.get(cacheKey);
  if (!forceRefresh && cached && Date.now() - cached.createdAt < sheetCacheMs) {
    return cached.value as Record<string, string>[];
  }

  const spreadsheetId = await spreadsheetIdForTitle(sheetName);
  const range = encodeURIComponent(`'${tabName.replaceAll("'", "''")}'`);
  const payload = await googleJson<{ values?: string[][] }>(
    `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${range}`,
  );
  const [headers = [], ...rows] = payload.values || [];
  const records = rows.map((row) => {
    const record: Record<string, string> = {};
    headers.forEach((header, index) => {
      record[header] = row[index] || "";
    });
    return record;
  });
  sheetCache.set(cacheKey, { createdAt: Date.now(), value: records });
  return records;
}

function writeRuns(runs: RunRecord[]) {
  fs.mkdirSync(testResultsDir, { recursive: true });
  fs.writeFileSync(runsJsonPath, JSON.stringify(runs.slice(0, 100), null, 2));
}

function taskPayload(task: ManagedTask) {
  const { proc, ...payload } = task;
  return payload;
}

function titleToId(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function regexEscape(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function dataDrivenModuleTests(moduleId: string) {
  const config =
    moduleId === "pbr"
      ? {
          dataFile: path.join(frameworkDir, "tests", "pbr", "pbr-cases.js"),
          specPath: "tests/pbr/smoke/pbr-legacy-cases.spec.js",
          group: "smoke",
        }
      : moduleId === "bmc"
        ? {
            dataFile: path.join(frameworkDir, "tests", "bmc", "bmc-cases.js"),
            specPath: "tests/bmc/smoke/bmc-legacy-cases.spec.js",
            group: "smoke",
          }
        : null;
  if (!config || !fs.existsSync(config.dataFile)) {
    return null;
  }
  const source = fs.readFileSync(config.dataFile, "utf8");
  const titles = Array.from(
    new Set([
      ...Array.from(source.matchAll(/title:\s*"([^"]+)"/g)).map((match) => match[1]),
      ...Array.from(source.matchAll(/pbrCase\(\s*"([^"]+)"/g)).map((match) => match[1]),
    ]),
  );
  return titles.map((title) => ({
    id: `${config.specPath}::${titleToId(title)}`,
    label: title,
    path: `${config.specPath}::${title}`,
    group: config.group,
  }));
}

function loginSetupTest(moduleId: string) {
  const setupPath = `tests/${moduleId}/setup/buyer-login.setup.js`;
  const fullPath = path.join(frameworkDir, setupPath);
  if (!fs.existsSync(fullPath)) {
    return null;
  }
  return {
    id: setupPath,
    label: "Buyer login setup",
    path: setupPath,
    group: "setup",
  };
}

function moduleTests(moduleId: string) {
  const dataDriven = dataDrivenModuleTests(moduleId);
  const setupTest = loginSetupTest(moduleId);
  if (dataDriven) {
    return setupTest ? [setupTest, ...dataDriven] : dataDriven;
  }
  const testRoot = path.join(frameworkDir, "tests", moduleId);
  const files: string[] = [];
  function walk(dir: string) {
    if (!fs.existsSync(dir)) {
      return;
    }
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.name.endsWith(".spec.js")) {
        files.push(fullPath);
      }
    }
  }
  walk(testRoot);
  const discoveredTests = files.sort().map((file) => {
    const relativePath = path.relative(frameworkDir, file).replaceAll(path.sep, "/");
    const label = path
      .basename(file, ".spec.js")
      .replaceAll("-", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
    return {
      id: relativePath,
      label,
      path: relativePath,
      group: path.relative(testRoot, path.dirname(file)).replaceAll(path.sep, "/") || "enquiry",
    };
  });
  return setupTest ? [setupTest, ...discoveredTests] : discoveredTests;
}

function summarizePlaywrightJson(
  startedAt: string,
  finishedAt: string,
  command: string,
  stdout: string,
  stderr: string,
  moduleDefinition = modules[0],
): RunRecord {
  let passed = 0;
  let failed = 0;
  let skipped = 0;
  try {
    const report = JSON.parse(fs.readFileSync(resultsJsonPath, "utf8")) as {
      stats?: { expected?: number; unexpected?: number; skipped?: number; flaky?: number };
    };
    passed = Number(report.stats?.expected || 0) + Number(report.stats?.flaky || 0);
    failed = Number(report.stats?.unexpected || 0);
    skipped = Number(report.stats?.skipped || 0);
  } catch {
    failed = stderr ? 1 : 0;
  }
  const total = passed + failed + skipped;
  const status = failed === 0 ? "Pass" : "Fail";
  return {
    id: Date.now(),
    module_name: moduleDefinition.label,
    suite_name: moduleDefinition.suite,
    started_at: startedAt,
    finished_at: finishedAt,
    status,
    passed,
    failed,
    total: total || (status === "Pass" ? 1 : 0),
    command,
    stdout,
    stderr,
    report_path: path.join(frameworkDir, "playwright-report", "index.html"),
    extra: {
      framework: "JavaScript Playwright",
      results_json: resultsJsonPath,
    },
  };
}

function startModuleTask(payload: { module_id?: string; browser_mode?: "headed" | "headless"; selected_tests?: string[] }) {
  fs.mkdirSync(testResultsDir, { recursive: true });
  try {
    fs.rmSync(resultsJsonPath, { force: true });
  } catch {
    // Best effort cleanup; Playwright will overwrite this on a normal run.
  }

  const browserMode = payload.browser_mode || "headed";
  const selectedTests = payload.selected_tests || [];
  const moduleId = payload.module_id || "enquiry";
  const moduleDefinition = modules.find((module) => module.id === moduleId) || modules[0];
  const args = [playwrightCli, "test"];
  if (selectedTests.length) {
    const pathSelections = selectedTests.map((item) => item.split("::")[0]);
    args.push(...Array.from(new Set(pathSelections)));
    const titleSelections = selectedTests
      .filter((item) => item.includes("::"))
      .map((item) => item.slice(item.indexOf("::") + 2))
      .filter(Boolean);
    if (titleSelections.length) {
      args.push("-g", [`${moduleId} buyer login saves authenticated session`, ...titleSelections.map(regexEscape)].join("|"));
    }
  } else {
    args.push(`tests/${moduleId}`);
  }
  if (browserMode === "headed") {
    args.push("--headed");
  }

  const command = `${nodeCommand} ${args.join(" ")}`;
  const startedAt = now();
  const task: ManagedTask = {
    id: crypto.randomUUID(),
    kind: "module",
    title: `Module: ${moduleId}`,
    started_at: startedAt,
    status: "running",
    browser_mode: browserMode,
    command,
    cwd: frameworkDir,
    payload: { module_id: moduleId, browser_mode: browserMode, selected_tests: selectedTests },
    finished_at: null,
    result: null,
    error: null,
  };
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (typeof value === "string") {
      env[key] = value;
    }
  }
  const proc = spawn(nodeCommand, args, {
    cwd: frameworkDir,
    env: {
      ...env,
      HEADLESS: browserMode === "headless" ? "true" : "false",
      DAILY_QA_MODULE_ID: moduleId,
      DAILY_QA_MODULE_LABEL: moduleDefinition.label,
      DAILY_QA_SUITE_NAME: moduleDefinition.suite,
    } as unknown as NodeJS.ProcessEnv,
    windowsHide: true,
  });
  task.proc = proc;
  task.pid = proc.pid;
  tasks.set(task.id, task);

  let stdout = "";
  let stderr = "";
  proc.stdout.on("data", (chunk) => {
    stdout += chunk.toString();
  });
  proc.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  proc.on("close", (code) => {
    if (task.status === "stopped") {
      return;
    }
    const finishedAt = now();
    const run = summarizePlaywrightJson(startedAt, finishedAt, command, stdout, stderr, moduleDefinition);
    if (code !== 0 && run.failed === 0) {
      run.failed = 1;
      run.total = Math.max(run.total, 1);
      run.status = "Fail";
    }
    task.finished_at = finishedAt;
    task.status = code === 0 ? "completed" : "failed";
    task.result = run;
    task.error = code === 0 ? null : stderr || stdout || "Playwright execution failed.";
    writeRuns([run, ...readRuns()]);
  });

  return taskPayload(task);
}

async function postBody(request: NextRequest) {
  try {
    return await request.json();
  } catch {
    return {};
  }
}

function backendModuleId(moduleId: string) {
  return moduleId === "enquiry" ? "enq" : moduleId;
}

async function generateTestsFromBackend(body: Record<string, unknown>) {
  const backendBaseUrl = (process.env.DAILY_QA_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const payload = {
    ...body,
    module_id: backendModuleId(String(body.module_id || "enquiry")),
  };

  let response: Response;
  try {
    response = await fetch(`${backendBaseUrl}/api/testlink/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Python backend is not reachable at ${backendBaseUrl}. Start it before using TestLink generation. ${
        error instanceof Error ? error.message : ""
      }`.trim(),
    );
  }

  const text = await response.text();
  let result: Record<string, unknown>;
  try {
    result = text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    throw new Error(text || `Backend returned ${response.status}`);
  }

  if (!response.ok) {
    throw new Error(String(result.detail || text || `Backend returned ${response.status}`));
  }

  return result;
}

function sheetRecords() {
  return readRuns().map((run) => ({
    "Test Title": run.module_name,
    Status: run.status,
    Browser: "chromium",
    Phone: "-",
    Date: run.started_at.slice(0, 10),
    Time: run.started_at.slice(11, 19),
    Remarks: run.stderr || run.stdout || "-",
  }));
}

async function handleGet(request: NextRequest, pathParts: string[]) {
  const route = pathParts.join("/");
  const search = request.nextUrl.searchParams;

  if (route === "health") return json({ status: "ok" });
  if (route === "status") {
    return json({
      ai: { enabled: false, label: "Not configured", base_url: "", model: "" },
      testlink: { enabled: false, label: "Enquiry Playwright mode", url: "" },
    });
  }
  if (route === "modules") return json(modules);
  if (route === "runs") return json(readRuns().slice(0, Number(search.get("limit") || 20)));
  if (route === "diagnostics/healings") return json([]);
  if (route === "diagnostics/steps") return json([]);
  if (route === "executions/active") {
    return json(Array.from(tasks.values()).filter((task) => task.status === "running").map(taskPayload));
  }
  if (pathParts[0] === "modules" && pathParts[2] === "tests") {
    const moduleId = pathParts[1];
    if (!modules.some((module) => module.id === moduleId)) {
      return json({ detail: `Unknown module: ${moduleId}` }, 404);
    }
    return json({ tests: moduleTests(moduleId) });
  }
  if (route === "sheets/tabs") {
    try {
      const tabs = await googleSheetTabs(search.get("sheet_name") || "Buyer Automation", search.get("fallback_tab") || "ENQ");
      return json({ tabs });
    } catch (error) {
      return json({ detail: error instanceof Error ? error.message : "Could not load Google Sheet tabs." }, 500);
    }
  }
  if (route === "sheets/records") {
    try {
      const records = await googleSheetRecords(
        search.get("sheet_name") || "Buyer Automation",
        search.get("tab_name") || "ENQ",
        search.get("force_refresh") === "true",
      );
      return json({ records, count: records.length });
    } catch (error) {
      return json({ detail: error instanceof Error ? error.message : "Could not load Google Sheet records." }, 500);
    }
  }
  if (pathParts[0] === "executions" && pathParts[1]) {
    const task = tasks.get(pathParts[1]);
    return task ? json(taskPayload(task)) : json({ detail: `Unknown execution task: ${pathParts[1]}` }, 404);
  }
  return json({ detail: `Unknown API route: /api/${route}` }, 404);
}

async function handlePost(request: NextRequest, pathParts: string[]) {
  const route = pathParts.join("/");
  const body = await postBody(request);

  if (route === "settings/workspace") return json({ saved: true, keys: Object.keys(body) });
  if (route === "executions/module/start") {
    if (body.module_id && !modules.some((module) => module.id === body.module_id)) {
      return json({ detail: `Unknown module: ${body.module_id}` }, 400);
    }
    return json(startModuleTask(body));
  }
  if (pathParts[0] === "executions" && pathParts[2] === "stop") {
    const task = tasks.get(pathParts[1]);
    if (!task) return json({ detail: `Unknown execution task: ${pathParts[1]}` }, 404);
    task.proc?.kill();
    task.status = "stopped";
    task.finished_at = now();
    task.error = task.error || "Execution was stopped by the user.";
    return json(taskPayload(task));
  }
  if (pathParts[0] === "executions" && pathParts[2] === "restart") {
    const task = tasks.get(pathParts[1]);
    if (!task) return json({ detail: `Unknown execution task: ${pathParts[1]}` }, 404);
    return json(startModuleTask(task.payload as { module_id?: string; browser_mode?: "headed" | "headless"; selected_tests?: string[] }));
  }
  if (route === "testlink/generate") {
    try {
      return json(await generateTestsFromBackend(body));
    } catch (error) {
      return json({ detail: error instanceof Error ? error.message : "Could not generate tests from TestLink." }, 500);
    }
  }
  if (route === "reports/email") {
    return json({ sent: false, recipients: body.recipients || [], total: sheetRecords().length, passed: 0, failed: 0, pass_rate: 0 });
  }
  if (route === "executions/url-agent/start" || route === "url-agent/run") {
    return json({ detail: "URL Agent was moved to backup. This clean setup runs Playwright modules only." }, 400);
  }
  return json({ detail: `Unknown API route: /api/${route}` }, 404);
}

export async function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const params = await context.params;
  return handleGet(request, params.path || []);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const params = await context.params;
  return handlePost(request, params.path || []);
}
