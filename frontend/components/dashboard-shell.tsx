"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  Activity,
  Bot,
  ChevronDown,
  ChevronRight,
  CirclePlay,
  Download,
  Filter,
  FlaskConical,
  History,
  LoaderCircle,
  PanelLeftClose,
  PanelLeftOpen,
  RotateCcw,
  Settings2,
  Sparkles,
  Square,
  Stethoscope,
  TableProperties,
  X,
} from "lucide-react";

import {
  api,
  DiagnosticsHealingItem,
  DiagnosticsStepItem,
  ExecutionTask,
  ModuleItem,
  ModuleTestItem,
  RunItem,
  SheetRecord,
  StatusPayload,
  TestLinkGenerationResponse,
  UrlAgentRunResponse,
} from "@/lib/api";

type LoadState = {
  status?: StatusPayload;
  modules: ModuleItem[];
  runs: RunItem[];
};

type WorkspaceSettings = {
  llmApiKey: string;
  llmBaseUrl: string;
  llmModel: string;
  defaultPhone: string;
  defaultOtp: string;
  testlinkApiKey: string;
  testlinkUrl: string;
  testlinkCaBundle: string;
  testlinkInsecureSkipVerify: boolean;
  smtpRecipients: string;
};

type ExecutionStepRow = {
  title: string;
  status: string;
  remarks: string;
};

type ExecutionCaseRow = {
  key: string;
  testTitle: string;
  status: string;
  browser: string;
  phone: string;
  date: string;
  time: string;
  remarks: string;
  steps: ExecutionStepRow[];
};

const DASHBOARD_TABS = [
  "Executions",
  "Downloads",
  "Test Generator",
  "Launcher History",
  "Diagnostics",
  "E2E Agent",
] as const;

const SETTINGS_STORAGE_KEY = "daily-qa-workspace-settings";

const DEFAULT_SETTINGS: WorkspaceSettings = {
  llmApiKey: "",
  llmBaseUrl: "https://imllm.intermesh.net/v1",
  llmModel: "anthropic/claude-sonnet-4-6",
  defaultPhone: "9643193481",
  defaultOtp: "1956",
  testlinkApiKey: "",
  testlinkUrl: "https://testlink.intermesh.net/lib/api/xmlrpc/v1/xmlrpc.php",
  testlinkCaBundle: "",
  testlinkInsecureSkipVerify: true,
  smtpRecipients: "",
};

function StatCard({
  label,
  value,
  accent,
  loading = false,
}: {
  label: string;
  value: string | number;
  accent: string;
  loading?: boolean;
}) {
  return (
    <div className={`rounded-[20px] border border-white/60 bg-white/80 p-5 shadow-soft backdrop-blur transition-all duration-300 ${loading ? "scale-[0.99]" : "scale-100"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{label}</p>
      {loading ? (
        <div className="mt-4 h-12 w-24 animate-pulse rounded-2xl bg-slate-100" />
      ) : (
        <p className={`mt-3 text-4xl font-semibold transition-all duration-300 ${accent}`}>{value}</p>
      )}
    </div>
  );
}

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700">
      <span className="font-medium">{label}:</span> {value}
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-2 text-sm transition ${
        active
          ? "border-cobalt bg-[linear-gradient(135deg,rgba(42,86,255,0.12),rgba(28,167,216,0.16))] text-slate-900"
          : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
      }`}
    >
      {label}
    </button>
  );
}

function SectionTitle({ icon, title, description }: { icon: React.ReactNode; title: string; description?: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1 text-cobalt">{icon}</div>
      <div>
        <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
    </div>
  );
}

function parseSheetDate(value?: string) {
  if (!value) {
    return null;
  }
  const raw = value.trim();
  if (!raw) {
    return null;
  }
  const parts = raw.includes("/") ? raw.split("/") : raw.split("-");
  if (parts.length !== 3) {
    return null;
  }
  if (parts[0].length === 4) {
    return raw.slice(0, 10);
  }
  const [day, month, year] = parts;
  if (!day || !month || !year) {
    return null;
  }
  return `${year.padStart(4, "0")}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function downloadFile(filename: string, content: BlobPart, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function buildCsv(records: SheetRecord[]) {
  if (!records.length) {
    return "";
  }
  const headers = Object.keys(records[0]);
  const escapeCell = (value: string) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows = [
    headers.map(escapeCell).join(","),
    ...records.map((record) => headers.map((header) => escapeCell(record[header] ?? "")).join(",")),
  ];
  return rows.join("\n");
}

function buildHtmlReport(records: SheetRecord[], filters: Record<string, string>) {
  const headers = records.length ? Object.keys(records[0]) : [];
  const filterRows = Object.entries(filters)
    .map(([key, value]) => `<tr><td><strong>${key}</strong></td><td>${value || "-"}</td></tr>`)
    .join("");
  const tableHead = headers.map((header) => `<th>${header}</th>`).join("");
  const tableBody = records
    .map(
      (record) =>
        `<tr>${headers
          .map((header) => `<td>${String(record[header] ?? "-").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</td>`)
          .join("")}</tr>`,
    )
    .join("");

  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Filtered Execution Report</title>
  <style>
    body { font-family: Segoe UI, Arial, sans-serif; padding: 32px; color: #0f172a; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #dbe4f0; padding: 10px; text-align: left; vertical-align: top; }
    th { background: #eff6ff; }
    .filters { max-width: 720px; }
    .filters td:first-child { width: 220px; }
  </style>
</head>
<body>
  <h1>Filtered Execution Report</h1>
  <table class="filters">${filterRows}</table>
  <table>
    <thead><tr>${tableHead}</tr></thead>
    <tbody>${tableBody || '<tr><td colspan="99">No rows matched the selected filters.</td></tr>'}</tbody>
  </table>
</body>
</html>`;
}

function stripBrowserPrefix(value: string) {
  return value.replace(/^\[[^\]]+\]\s*/, "").trim();
}

function normalizeCaseTitle(value: string) {
  const title = stripBrowserPrefix(value || "")
    .replace(/^test[_\s-]+/i, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return title || "Untitled Test";
}

function formatStatus(status: string) {
  const normalized = (status || "").trim().toLowerCase();
  if (normalized === "pass") {
    return "Pass";
  }
  if (normalized === "fail") {
    return "Fail";
  }
  if (normalized === "pass-healed") {
    return "Pass-Healed";
  }
  return status || "-";
}

function statusClass(status: string) {
  const normalized = status.trim().toLowerCase();
  if (normalized === "pass" || normalized === "pass-healed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (normalized === "fail") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function buildExecutionCaseRows(records: SheetRecord[]) {
  const grouped = new Map<string, ExecutionCaseRow>();

  records.forEach((record, index) => {
    const rawTitle = record["Test Title"] || record.test_title || record.Title || "Untitled Test";
    const hasStepColumn = Boolean(record["Test Step"] || record.test_step);
    const testTitle = hasStepColumn ? rawTitle : normalizeCaseTitle(record["Test Case"] || record.test_case || rawTitle);
    const stepTitle = stripBrowserPrefix(record["Test Step"] || record.test_step || rawTitle || `Step ${index + 1}`) || `Step ${index + 1}`;
    const browser = record.Browser || record.browser || "-";
    const phone = record.Phone || record.phone || "-";
    const date = record.Date || record.date || "-";
    const time = record.Time || record.time || "-";
    const key = `${testTitle}|${browser}|${phone}|${date}|${time}`;
    const current = grouped.get(key);
    const step = {
      title: stepTitle,
      status: formatStatus(record.Status || record.status || "-"),
      remarks: record.Remarks || record.remarks || "",
    };

    if (!current) {
      grouped.set(key, {
        key,
        testTitle,
        status: step.status,
        browser,
        phone,
        date,
        time,
        remarks: step.remarks,
        steps: [step],
      });
      return;
    }

    current.steps.push(step);
    if (step.status.toLowerCase() === "fail") {
      current.status = "Fail";
    }
    if (!current.remarks && step.remarks) {
      current.remarks = step.remarks;
    }
  });

  return Array.from(grouped.values());
}

function executionCasesToSheetRecords(rows: ExecutionCaseRow[], includeRemarks: boolean): SheetRecord[] {
  return rows.map((row) => ({
    "Test Title": row.testTitle,
    Status: row.status,
    "Test Steps": row.steps.map((step) => `${step.status}: ${step.title}`).join(" | "),
    ...(includeRemarks ? { Remarks: row.remarks || "-" } : {}),
    Browser: row.browser,
    Phone: row.phone,
    Date: row.date,
    Time: row.time,
  }));
}

export function DashboardShell() {
  const [mounted, setMounted] = useState(false);
  const [data, setData] = useState<LoadState>({ modules: [], runs: [] });
  const [selectedModule, setSelectedModule] = useState("");
  const [activeTab, setActiveTab] = useState<(typeof DASHBOARD_TABS)[number]>("Executions");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sheetTabs, setSheetTabs] = useState<string[]>([]);
  const [selectedSheetTab, setSelectedSheetTab] = useState("");
  const [rawSheetRecords, setRawSheetRecords] = useState<SheetRecord[]>([]);
  const [availableStatuses, setAvailableStatuses] = useState<string[]>([]);
  const [availableBrowsers, setAvailableBrowsers] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [browserFilter, setBrowserFilter] = useState<string[]>([]);
  const [searchText, setSearchText] = useState("");
  const [showRemarks, setShowRemarks] = useState(false);
  const [expandedCaseRows, setExpandedCaseRows] = useState<string[]>([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [diagnosticView, setDiagnosticView] = useState<"Healing History" | "Step Failures">("Healing History");
  const [healings, setHealings] = useState<DiagnosticsHealingItem[]>([]);
  const [stepEvents, setStepEvents] = useState<DiagnosticsStepItem[]>([]);
  const [workspaceSettings, setWorkspaceSettings] = useState<WorkspaceSettings>(DEFAULT_SETTINGS);
  const [generatorSuiteId, setGeneratorSuiteId] = useState("");
  const [generatorOutputDir, setGeneratorOutputDir] = useState("");
  const [generatorMaxCases, setGeneratorMaxCases] = useState("0");
  const [generatorOverwrite, setGeneratorOverwrite] = useState(false);
  const [generationResult, setGenerationResult] = useState<TestLinkGenerationResponse | null>(null);
  const [urlAgentInput, setUrlAgentInput] = useState("https://example.com");
  const [urlAgentHeadless, setUrlAgentHeadless] = useState(false);
  const [urlAgentVisualGuard, setUrlAgentVisualGuard] = useState(true);
  const [moduleBrowserMode, setModuleBrowserMode] = useState<"headed" | "headless">("headed");
  const [moduleTests, setModuleTests] = useState<ModuleTestItem[]>([]);
  const [selectedModuleTests, setSelectedModuleTests] = useState<string[]>([]);
  const [isTestPickerOpen, setIsTestPickerOpen] = useState(false);
  const [isLoadingModuleTests, setIsLoadingModuleTests] = useState(false);
  const [urlAgentResult, setUrlAgentResult] = useState<UrlAgentRunResponse | null>(null);
  const [error, setError] = useState("");
  const [settingsSavedMessage, setSettingsSavedMessage] = useState("");
  const [executionNotice, setExecutionNotice] = useState("");
  const [isSendingReportEmail, setIsSendingReportEmail] = useState(false);
  const [isSheetLoading, setIsSheetLoading] = useState(false);
  const [isRunningModule, setIsRunningModule] = useState(false);
  const [isGeneratingTests, setIsGeneratingTests] = useState(false);
  const [isRunningUrlAgent, setIsRunningUrlAgent] = useState(false);
  const [isStoppingExecution, setIsStoppingExecution] = useState(false);
  const [activeTask, setActiveTask] = useState<ExecutionTask | null>(null);
  const [isPending, startTransition] = useTransition();
  const loadedSheetTabsRef = useRef<Record<string, string[]>>({});
  const loadedSheetRecordsRef = useRef<Record<string, SheetRecord[]>>({});

  const derivedAiEnabled = Boolean(
    workspaceSettings.llmApiKey.trim() &&
      workspaceSettings.llmBaseUrl.trim() &&
      workspaceSettings.llmModel.trim(),
  );
  const derivedTestlinkEnabled = Boolean(
    workspaceSettings.testlinkApiKey.trim() && workspaceSettings.testlinkUrl.trim(),
  );
  const smtpRecipientsList = useMemo(
    () =>
      workspaceSettings.smtpRecipients
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    [workspaceSettings.smtpRecipients],
  );
  const selectedModuleTestNames = useMemo(
    () =>
      moduleTests
        .filter((item) => selectedModuleTests.includes(item.path))
        .map((item) => item.label),
    [moduleTests, selectedModuleTests],
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        setWorkspaceSettings({ ...DEFAULT_SETTINGS, ...(JSON.parse(stored) as Partial<WorkspaceSettings>) });
      }
    } catch {
      setWorkspaceSettings(DEFAULT_SETTINGS);
    }
  }, []);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [status, modules, runs, healingData, stepData, activeExecutions] = await Promise.all([
          api.getStatus(),
          api.getModules(),
          api.getRuns(20),
          api.getDiagnosticsHealings(150),
          api.getDiagnosticsSteps(150),
          api.getActiveExecutions(),
        ]);
        setData({ status, modules, runs });
        setHealings(healingData);
        setStepEvents(stepData);
        setSelectedModule((current) => current || modules[0]?.id || "");
        setActiveTask(activeExecutions[0] || null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load dashboard.");
      }
    };

    startTransition(() => {
      void loadDashboard();
    });
  }, []);

  const selectedDefinition = useMemo(
    () => data.modules.find((module) => module.id === selectedModule) || data.modules[0],
    [data.modules, selectedModule],
  );

  const refreshSheetRecords = useCallback(
    async (forceRefresh = false) => {
      if (!selectedDefinition || !selectedSheetTab) {
        return;
      }
      if (sheetTabs.length && !sheetTabs.includes(selectedSheetTab)) {
        return;
      }
      setIsSheetLoading(true);
      setError("");
      const cacheKey = `${selectedDefinition.sheet_name}::${selectedSheetTab}`;
      const cachedRecords = loadedSheetRecordsRef.current[cacheKey];
      if (cachedRecords && !forceRefresh) {
        const statuses = Array.from(new Set(cachedRecords.map((row) => row.Status).filter(Boolean))).sort();
        const browsers = Array.from(new Set(cachedRecords.map((row) => row.Browser).filter(Boolean))).sort();
        const dates = cachedRecords
          .map((row) => parseSheetDate(row.Date))
          .filter((value): value is string => Boolean(value))
          .sort();
        setAvailableStatuses(statuses);
        setAvailableBrowsers(browsers);
        setStatusFilter(statuses);
        setBrowserFilter(browsers);
        setStartDate(dates[0] || "");
        setEndDate(dates[dates.length - 1] || "");
        setRawSheetRecords(cachedRecords);
        setIsSheetLoading(false);
        return;
      }
      if (forceRefresh) {
        delete loadedSheetRecordsRef.current[cacheKey];
      }
      setRawSheetRecords([]);
      try {
        const payload = await api.getSheetRecords(selectedDefinition.sheet_name, selectedSheetTab, {
          force_refresh: forceRefresh,
        });
        const records = payload.records;
        loadedSheetRecordsRef.current[cacheKey] = records;
        const statuses = Array.from(new Set(records.map((row) => row.Status).filter(Boolean))).sort();
        const browsers = Array.from(new Set(records.map((row) => row.Browser).filter(Boolean))).sort();
        const dates = records.map((row) => parseSheetDate(row.Date)).filter((value): value is string => Boolean(value));
        dates.sort();
        setAvailableStatuses(statuses);
        setAvailableBrowsers(browsers);
        setStatusFilter(statuses);
        setBrowserFilter(browsers);
        setStartDate(dates[0] || "");
        setEndDate(dates[dates.length - 1] || "");
        setRawSheetRecords(records);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load sheet records.");
      } finally {
        setIsSheetLoading(false);
      }
    },
    [selectedDefinition, selectedSheetTab, sheetTabs],
  );

  useEffect(() => {
    if (!activeTask?.id) {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const task = await api.getExecution(activeTask.id);
        setActiveTask(task);
        const running = task.status === "running";
        setIsRunningModule(running && task.kind === "module");
        setIsRunningUrlAgent(running && task.kind === "url_agent");
        if (!running) {
          if (task.kind === "module" && task.result) {
            const run = task.result as RunItem;
            setData((current) => ({ ...current, runs: [run, ...current.runs].slice(0, 20) }));
            setActiveTab("Executions");
            void refreshSheetRecords(true);
          }
          if (task.kind === "url_agent" && task.result) {
            setUrlAgentResult(task.result as UrlAgentRunResponse);
          }
          if (task.error) {
            setError(task.error);
          }
          window.clearInterval(timer);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not refresh execution state.");
        window.clearInterval(timer);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [activeTask?.id, refreshSheetRecords]);

  useEffect(() => {
    setSelectedSheetTab("");
    setRawSheetRecords([]);
    setModuleTests([]);
    setSelectedModuleTests([]);
    if (!selectedDefinition) {
      return;
    }
    const loadTabs = async () => {
      const cacheKey = `${selectedDefinition.sheet_name}::${selectedDefinition.default_tab}`;
      const cachedTabs = loadedSheetTabsRef.current[cacheKey];
      if (cachedTabs) {
        setSheetTabs(cachedTabs);
        setSelectedSheetTab((current) =>
          current && cachedTabs.includes(current) ? current : selectedDefinition.default_tab || cachedTabs[0] || "",
        );
        return;
      }
      try {
        const payload = await api.getSheetTabs(selectedDefinition.sheet_name, selectedDefinition.default_tab);
        const nextTabs = payload.tabs.length ? payload.tabs : [selectedDefinition.default_tab];
        loadedSheetTabsRef.current[cacheKey] = nextTabs;
        setSheetTabs(nextTabs);
        setSelectedSheetTab((current) =>
          current && nextTabs.includes(current) ? current : selectedDefinition.default_tab || nextTabs[0] || "",
        );
      } catch {
        setSheetTabs([selectedDefinition.default_tab]);
        setSelectedSheetTab(selectedDefinition.default_tab);
      }
    };
    void loadTabs();
  }, [selectedDefinition]);

  useEffect(() => {
    if (!selectedDefinition) {
      return;
    }
    const loadModuleTests = async () => {
      setIsLoadingModuleTests(true);
      try {
        const payload = await api.getModuleTests(selectedDefinition.id);
        setModuleTests(payload.tests);
      } catch (err) {
        setModuleTests([]);
        setError(err instanceof Error ? err.message : "Could not load module test cases.");
      } finally {
        setIsLoadingModuleTests(false);
      }
    };
    void loadModuleTests();
  }, [selectedDefinition]);

  useEffect(() => {
    void refreshSheetRecords(false);
  }, [refreshSheetRecords]);

  const sheetRecords = useMemo(() => {
    const normalizedSearch = searchText.trim().toLowerCase();
    return rawSheetRecords.filter((record) => {
      const recordStatus = (record.Status || "").trim();
      const recordBrowser = (record.Browser || "").trim();
      const recordDate = parseSheetDate(record.Date);
      const haystack = Object.values(record).join(" ").toLowerCase();

      if (statusFilter.length && !statusFilter.includes(recordStatus)) {
        return false;
      }
      if (browserFilter.length && !browserFilter.includes(recordBrowser)) {
        return false;
      }
      if (startDate && (!recordDate || recordDate < startDate)) {
        return false;
      }
      if (endDate && (!recordDate || recordDate > endDate)) {
        return false;
      }
      if (normalizedSearch && !haystack.includes(normalizedSearch)) {
        return false;
      }
      return true;
    });
  }, [browserFilter, endDate, rawSheetRecords, searchText, startDate, statusFilter]);

  const executionTotals = useMemo(() => {
    const rows = buildExecutionCaseRows(sheetRecords);
    const total = rows.length;
    const passed = rows.filter((row) => row.status.trim().toLowerCase() === "pass").length;
    const failed = rows.filter((row) => row.status.trim().toLowerCase() === "fail").length;
    const passRate = total ? `${((passed / total) * 100).toFixed(1)}%` : "0.0%";
    return { total, passed, failed, passRate };
  }, [sheetRecords]);

  const executionCaseRows = useMemo(() => buildExecutionCaseRows(sheetRecords), [sheetRecords]);

  const executionExportRows = useMemo(
    () => executionCasesToSheetRecords(executionCaseRows, showRemarks),
    [executionCaseRows, showRemarks],
  );

  const suiteRuns = useMemo(() => {
    if (!selectedDefinition) {
      return data.runs;
    }
    return data.runs.filter((run) => run.suite_name === selectedDefinition.suite);
  }, [data.runs, selectedDefinition]);

  const filteredHealings = useMemo(() => {
    if (!selectedDefinition) {
      return healings;
    }
    return healings.filter((row) => row.suite_name === selectedDefinition.suite);
  }, [healings, selectedDefinition]);

  const filteredFailedSteps = useMemo(() => {
    const scoped = selectedDefinition ? stepEvents.filter((row) => row.suite_name === selectedDefinition.suite) : stepEvents;
    return scoped.filter((row) => (row.status || "").toLowerCase().startsWith("fail"));
  }, [selectedDefinition, stepEvents]);

  const activeExecutionLabel = useMemo(() => {
    if (isRunningUrlAgent) {
      return `Running URL agent in ${urlAgentHeadless ? "headless" : "headed"} mode${urlAgentVisualGuard ? " with visual guard" : ""} and collecting page evidence...`;
    }
    if (isGeneratingTests) {
      return "Generating tests from TestLink...";
    }
    if (isRunningModule) {
      return `Running selected module in ${moduleBrowserMode} mode...`;
    }
    if (isSheetLoading) {
      return "Refreshing dashboard data...";
    }
    return "";
  }, [isGeneratingTests, isRunningModule, isRunningUrlAgent, isSheetLoading, urlAgentHeadless, urlAgentVisualGuard]);

  function toggleFilterValue(values: string[], value: string) {
    return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
  }

  function resetFilters() {
    setStatusFilter(availableStatuses);
    setBrowserFilter(availableBrowsers);
    setSearchText("");
    const dates = rawSheetRecords
      .map((row) => parseSheetDate(row.Date))
      .filter((value): value is string => Boolean(value))
      .sort();
    setStartDate(dates[0] || "");
    setEndDate(dates[dates.length - 1] || "");
  }

  function toggleModuleTest(path: string) {
    setSelectedModuleTests((current) =>
      current.includes(path) ? current.filter((item) => item !== path) : [...current, path],
    );
  }

  async function handleRunModule() {
    if (!selectedDefinition) {
      return;
    }
    setError("");
    setIsRunningModule(true);
    try {
      const task = await api.startModuleExecution({
        module_id: selectedDefinition.id,
        browser_mode: moduleBrowserMode,
        selected_tests: selectedModuleTests,
        llm_api_key: workspaceSettings.llmApiKey.trim() || undefined,
        llm_base_url: workspaceSettings.llmBaseUrl.trim() || undefined,
        llm_model: workspaceSettings.llmModel.trim() || undefined,
        default_login_phone: workspaceSettings.defaultPhone.trim() || undefined,
        default_login_otp: workspaceSettings.defaultOtp.trim() || undefined,
        smtp_recipients: workspaceSettings.smtpRecipients.trim() || undefined,
      });
      setActiveTask(task);
      setIsTestPickerOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Module run failed.");
      setIsRunningModule(false);
    }
  }

  async function handleGenerateTests() {
    if (!selectedDefinition) {
      return;
    }
    if (!generatorSuiteId.trim() || Number.isNaN(Number(generatorSuiteId))) {
      setError("Please enter a valid numeric Suite ID.");
      return;
    }
    setError("");
    setIsGeneratingTests(true);
    try {
      const result = await api.generateTestlink({
        module_id: selectedDefinition.id,
        suite_id: Number(generatorSuiteId),
        output_dir: generatorOutputDir.trim() || undefined,
        overwrite: generatorOverwrite,
        max_cases: Number(generatorMaxCases) > 0 ? Number(generatorMaxCases) : undefined,
        testlink_api_key: workspaceSettings.testlinkApiKey.trim() || undefined,
        testlink_url: workspaceSettings.testlinkUrl.trim() || undefined,
        testlink_ca_bundle: workspaceSettings.testlinkCaBundle.trim() || undefined,
        testlink_insecure_skip_verify: workspaceSettings.testlinkInsecureSkipVerify,
        llm_api_key: workspaceSettings.llmApiKey.trim() || undefined,
        llm_base_url: workspaceSettings.llmBaseUrl.trim() || undefined,
        llm_model: workspaceSettings.llmModel.trim() || undefined,
      });
      setGenerationResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate tests.");
    } finally {
      setIsGeneratingTests(false);
    }
  }

  async function handleRunUrlAgent() {
    if (!urlAgentInput.trim()) {
      setError("Please enter a URL.");
      return;
    }
    setError("");
    setIsRunningUrlAgent(true);
    try {
      const task = await api.startUrlAgentExecution({
        url: urlAgentInput.trim(),
        headless: urlAgentHeadless,
        slow_mo: 100,
        visual_guard: urlAgentVisualGuard,
      });
      setActiveTask(task);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run URL agent.");
    }
  }

  async function handleStopExecution() {
    if (!activeTask?.id) {
      return;
    }
    const taskSnapshot = activeTask;
    setIsStoppingExecution(true);
    setIsRunningModule(false);
    setIsRunningUrlAgent(false);
    setActiveTask((current) =>
      current
        ? {
            ...current,
            status: "stopped",
            finished_at: new Date().toISOString(),
            error: "Execution was stopped by the user.",
          }
        : null,
    );
    showExecutionNotice(`${taskSnapshot.kind === "module" ? "Module" : "URL agent"} execution stopped.`);
    try {
      const task = await api.stopExecution(taskSnapshot.id);
      setActiveTask(task);
    } catch (err) {
      setActiveTask(taskSnapshot);
      setIsRunningModule(taskSnapshot.kind === "module");
      setIsRunningUrlAgent(taskSnapshot.kind === "url_agent");
      setExecutionNotice("");
      setError(err instanceof Error ? err.message : "Could not stop execution.");
    } finally {
      setIsStoppingExecution(false);
    }
  }

  async function handleRestartExecution() {
    if (!activeTask) {
      return;
    }
    setError("");
    try {
      if (activeTask.status === "running") {
        await api.stopExecution(activeTask.id);
      }
      if (activeTask.kind === "module") {
        await handleRunModule();
        return;
      }
      await handleRunUrlAgent();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restart execution.");
    }
  }

  async function handleSendReportEmail() {
    if (!selectedDefinition || !selectedSheetTab) {
      setError("Select a module and sheet tab before sending the report.");
      return;
    }
    if (!smtpRecipientsList.length) {
      setError("Add at least one SMTP recipient in Workspace Settings before sending mail.");
      setSettingsOpen(true);
      return;
    }
    setError("");
    setIsSendingReportEmail(true);
    try {
      const response = await api.sendSheetReportEmail({
        module_id: selectedDefinition.id,
        sheet_name: selectedDefinition.sheet_name,
        tab_name: selectedSheetTab,
        status: statusFilter,
        browser: browserFilter,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: searchText.trim() || undefined,
        recipients: smtpRecipientsList,
      });
      showExecutionNotice(
        `Report emailed to ${response.recipients.join(", ")} for ${response.total} filtered rows.`,
      );
      setActiveTab("Downloads");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send report email.");
    } finally {
      setIsSendingReportEmail(false);
    }
  }

  async function handleSaveSettings() {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(workspaceSettings));
    setError("");
    let backendSynced = false;
    try {
      await api.saveWorkspaceSettings({
        llm_api_key: workspaceSettings.llmApiKey.trim(),
        llm_base_url: workspaceSettings.llmBaseUrl.trim(),
        llm_model: workspaceSettings.llmModel.trim(),
        default_login_phone: workspaceSettings.defaultPhone.trim(),
        default_login_otp: workspaceSettings.defaultOtp.trim(),
        testlink_api_key: workspaceSettings.testlinkApiKey.trim(),
        testlink_url: workspaceSettings.testlinkUrl.trim(),
        testlink_ca_bundle: workspaceSettings.testlinkCaBundle.trim(),
        testlink_insecure_skip_verify: workspaceSettings.testlinkInsecureSkipVerify,
        smtp_recipients: workspaceSettings.smtpRecipients.trim(),
      });
      backendSynced = true;
    } catch (err) {
      console.warn("Workspace settings backend sync skipped.", err);
    }
    setSettingsSavedMessage(
      backendSynced
        ? "Workspace settings saved successfully."
        : "Settings saved in this browser. Module runs still use these values.",
    );
    window.setTimeout(() => {
      setSettingsSavedMessage("");
    }, 3500);
  }

  function showExecutionNotice(message: string) {
    setExecutionNotice(message);
    window.setTimeout(() => {
      setExecutionNotice("");
    }, 3000);
  }

  function renderExecutionsTable() {
    const tableColSpan = showRemarks ? 8 : 7;
    return (
      <div className="rounded-[24px] border border-slate-200/70 bg-white/85 p-5 shadow-soft">
        <SectionTitle
          icon={<Filter className="h-5 w-5" />}
          title="Filtered Execution Data"
          description={isSheetLoading ? "Refreshing records for the selected module..." : "One row per test case with expandable execution steps."}
        />
        <div className="mt-4 space-y-3 overflow-hidden rounded-[20px] border border-slate-100 bg-slate-50/70 p-3">
          <div className="grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-[minmax(140px,180px)_minmax(180px,1fr)_minmax(130px,150px)_minmax(130px,150px)_88px_120px]">
            <select
              className="min-h-[42px] min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-cobalt focus:ring-4 focus:ring-blue-100"
              value={selectedSheetTab}
              onChange={(event) => setSelectedSheetTab(event.target.value)}
            >
              {sheetTabs.map((tab) => (
                <option key={tab} value={tab}>
                  {tab}
                </option>
              ))}
            </select>
            <input
              type="search"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Filter by test case, step, browser, status..."
              className="min-h-[42px] min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-cobalt focus:ring-4 focus:ring-blue-100"
            />
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="min-h-[42px] min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-cobalt focus:ring-4 focus:ring-blue-100"
            />
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="min-h-[42px] min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-cobalt focus:ring-4 focus:ring-blue-100"
            />
            <button
              type="button"
              onClick={resetFilters}
              className="inline-flex min-h-[42px] min-w-0 items-center justify-center rounded-2xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-600 transition hover:border-cobalt hover:text-cobalt"
            >
              Reset
            </button>
            <button
              type="button"
              onClick={() => refreshSheetRecords(true)}
              disabled={isSheetLoading}
              className="inline-flex min-h-[42px] min-w-0 items-center justify-center gap-2 rounded-2xl border border-cobalt bg-white px-3 text-sm font-semibold text-cobalt transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSheetLoading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
              Sync Sheet
            </button>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {availableStatuses.map((status) => (
              <FilterChip
                key={status}
                label={status}
                active={statusFilter.includes(status)}
                onClick={() => setStatusFilter((current) => toggleFilterValue(current, status))}
              />
            ))}
            {availableBrowsers.map((browser) => (
              <FilterChip
                key={browser}
                label={browser}
                active={browserFilter.includes(browser)}
                onClick={() => setBrowserFilter((current) => toggleFilterValue(current, browser))}
              />
            ))}
            <button
              type="button"
              onClick={() => setShowRemarks((current) => !current)}
              className={`rounded-full border px-3 py-2 text-sm font-medium transition ${
                showRemarks
                  ? "border-cobalt bg-blue-50 text-cobalt"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
              }`}
            >
              {showRemarks ? "Hide Remarks" : "Show Remarks"}
            </button>
          </div>
        </div>
        <div className="mt-4 overflow-hidden rounded-[20px] border border-slate-100">
          <div className="max-h-[560px] overflow-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead className="sticky top-0 bg-slate-50">
                <tr className="text-left text-slate-500">
                  <th className="w-10 px-4 py-3 font-medium"></th>
                  <th className="min-w-[220px] px-4 py-3 font-medium">Test Title</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="min-w-[260px] px-4 py-3 font-medium">Test Steps</th>
                  {showRemarks ? <th className="min-w-[260px] px-4 py-3 font-medium">Remarks</th> : null}
                  <th className="px-4 py-3 font-medium">Browser</th>
                  <th className="px-4 py-3 font-medium">Phone</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {isSheetLoading ? (
                  <tr>
                    <td className="px-4 py-8 text-slate-500" colSpan={tableColSpan + 1}>
                      <span className="inline-flex items-center gap-2">
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        Loading module data...
                      </span>
                    </td>
                  </tr>
                ) : null}
                {executionCaseRows.map((row) => {
                  const isExpanded = expandedCaseRows.includes(row.key);
                  const failedSteps = row.steps.filter((step) => step.status.toLowerCase() === "fail").length;
                  return (
                    <Fragment key={row.key}>
                      <tr key={row.key} className="align-top">
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedCaseRows((current) =>
                                current.includes(row.key) ? current.filter((key) => key !== row.key) : [...current, row.key],
                              )
                            }
                            className="rounded-full border border-slate-200 p-1 text-slate-500 transition hover:border-cobalt hover:text-cobalt"
                            aria-label={isExpanded ? "Hide test steps" : "Show test steps"}
                          >
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </button>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-900">{row.testTitle}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${statusClass(row.status)}`}>
                            {row.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {row.steps.length} step{row.steps.length === 1 ? "" : "s"}
                          {failedSteps ? <span className="ml-2 text-rose-600">{failedSteps} failed</span> : null}
                        </td>
                        {showRemarks ? <td className="max-w-[360px] px-4 py-3 text-slate-700">{row.remarks || "-"}</td> : null}
                        <td className="px-4 py-3 text-slate-700">{row.browser}</td>
                        <td className="px-4 py-3 text-slate-700">{row.phone}</td>
                        <td className="px-4 py-3 text-slate-700">{row.date}</td>
                        <td className="px-4 py-3 text-slate-700">{row.time}</td>
                      </tr>
                      {isExpanded ? (
                        <tr key={`${row.key}-steps`}>
                          <td className="bg-slate-50 px-4 py-3" colSpan={tableColSpan + 1}>
                            <div className="rounded-2xl border border-slate-200 bg-white">
                              {row.steps.map((step, stepIndex) => (
                                <div
                                  key={`${row.key}-${step.title}-${stepIndex}`}
                                  className="grid gap-3 border-b border-slate-100 px-4 py-3 last:border-b-0 md:grid-cols-[minmax(200px,1fr)_120px_minmax(240px,1.2fr)]"
                                >
                                  <p className="font-medium text-slate-800">{step.title}</p>
                                  <span className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${statusClass(step.status)}`}>
                                    {step.status}
                                  </span>
                                  {showRemarks ? <p className="text-slate-600">{step.remarks || "-"}</p> : <span />}
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
                {!isSheetLoading && executionCaseRows.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-slate-500" colSpan={tableColSpan + 1}>
                      No rows matched the selected filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  function renderDownloads() {
    const filterSummary = {
      Module: selectedDefinition?.label || "",
      Tab: selectedSheetTab,
      Status: statusFilter.join(", "),
      Browser: browserFilter.join(", "),
      Search: searchText,
      "Start Date": startDate,
      "End Date": endDate,
    };

    return (
      <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
        <SectionTitle
          icon={<Download className="h-5 w-5" />}
          title="Download Center"
          description="Export or email the current filtered execution view."
        />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <button
            type="button"
            onClick={() => downloadFile(`${selectedSheetTab || "executions"}_filtered.csv`, buildCsv(executionExportRows), "text/csv")}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-left text-slate-900 transition hover:border-cobalt hover:bg-blue-50"
          >
            <p className="font-semibold">Download CSV</p>
            <p className="mt-1 text-sm text-slate-500">Raw rows from the current filtered table.</p>
          </button>
          <button
            type="button"
            onClick={() =>
              downloadFile(
                `${selectedSheetTab || "executions"}_report.html`,
                buildHtmlReport(executionExportRows, filterSummary),
                "text/html",
              )
            }
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-left text-slate-900 transition hover:border-cobalt hover:bg-blue-50"
          >
            <p className="font-semibold">Download HTML Report</p>
            <p className="mt-1 text-sm text-slate-500">Shareable report with filter context and table data.</p>
          </button>
          <button
            type="button"
            onClick={handleSendReportEmail}
            disabled={isSendingReportEmail || !selectedDefinition || !selectedSheetTab}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-left text-slate-900 transition hover:border-cobalt hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <p className="inline-flex items-center gap-2 font-semibold">
              {isSendingReportEmail ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {isSendingReportEmail ? "Sending Mail Report..." : "Send Report on Mail"}
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Sends the current filtered table for the selected date range to saved recipients.
            </p>
          </button>
        </div>
        <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <p className="font-medium text-slate-900">Mail Recipients</p>
          <p className="mt-1">
            {smtpRecipientsList.length
              ? smtpRecipientsList.join(", ")
              : "No recipients saved yet. Add them in Workspace Settings to enable report mail."}
          </p>
        </div>
      </div>
    );
  }

  function renderTestGenerator() {
    return (
      <div className="space-y-6">
        <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
          <SectionTitle
            icon={<FlaskConical className="h-5 w-5" />}
            title="TestLink Test Generator"
            description="Fetch manual cases from TestLink and generate Playwright tests into the selected module."
          />
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-600">
              Target Module
              <select
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                value={selectedModule}
                onChange={(event) => setSelectedModule(event.target.value)}
              >
                {data.modules.map((module) => (
                  <option key={module.id} value={module.id}>
                    {module.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-600">
              Suite ID
              <input
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                value={generatorSuiteId}
                onChange={(event) => setGeneratorSuiteId(event.target.value)}
                placeholder="Enter TestLink suite id"
              />
            </label>
            <label className="block text-sm font-medium text-slate-600">
              Output Folder
              <input
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                value={generatorOutputDir}
                onChange={(event) => setGeneratorOutputDir(event.target.value)}
                placeholder="Leave blank to use the module default folder"
              />
            </label>
            <label className="block text-sm font-medium text-slate-600">
              Max Cases
              <input
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                value={generatorMaxCases}
                onChange={(event) => setGeneratorMaxCases(event.target.value)}
                placeholder="0 for all"
              />
            </label>
          </div>
          <label className="mt-4 flex items-center gap-3 text-sm text-slate-600">
            <input type="checkbox" checked={generatorOverwrite} onChange={(event) => setGeneratorOverwrite(event.target.checked)} />
            Overwrite existing files
          </label>
          <button
            type="button"
            onClick={handleGenerateTests}
            disabled={isGeneratingTests}
            className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-4 font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isGeneratingTests ? <LoaderCircle className="h-5 w-5 animate-spin" /> : null}
            {isGeneratingTests ? "Generating..." : "Generate Tests"}
          </button>
        </div>

        {generationResult ? (
          <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
            <div className="grid gap-4 md:grid-cols-5">
              <StatCard label="Module" value={generationResult.module.label} accent="text-slate-900" />
              <StatCard label="Suite ID" value={generationResult.suite_id} accent="text-slate-900" />
              <StatCard label="Generated" value={generationResult.generated} accent="text-emerald-600" />
              <StatCard label="Skipped" value={generationResult.skipped} accent="text-amber-600" />
              <StatCard label="Failed" value={generationResult.failed} accent="text-rose-600" />
            </div>
            <p className="mt-4 text-sm text-slate-500">Output folder: {generationResult.output_dir}</p>
            {!generationResult.results.length ? (
              <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                No generated files were returned. Check the Suite ID, TestLink API key, and LLM settings, then try again.
              </div>
            ) : null}
            <div className="mt-5 overflow-hidden rounded-3xl border border-slate-100">
              <div className="max-h-[420px] overflow-auto">
                <table className="min-w-full divide-y divide-slate-100 text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-slate-500">
                      <th className="px-4 py-3 font-medium">Title</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Detail</th>
                      <th className="px-4 py-3 font-medium">Output Path</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {generationResult.results.map((row, index) => (
                      <tr key={`${row.title}-${index}`}>
                        <td className="px-4 py-3 text-slate-900">{row.title}</td>
                        <td className="px-4 py-3 text-slate-700">{row.status}</td>
                        <td className="px-4 py-3 text-slate-700">{row.detail}</td>
                        <td className="px-4 py-3 text-slate-700">{row.output_path || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function renderLauncherHistory() {
    return (
      <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
        <SectionTitle
          icon={<History className="h-5 w-5" />}
          title="Launcher History"
          description="Recent launcher executions for the selected module suite."
        />
        <div className="mt-5 overflow-hidden rounded-3xl border border-slate-100">
          <div className="max-h-[520px] overflow-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-500">
                  <th className="px-4 py-3 font-medium">Suite</th>
                  <th className="px-4 py-3 font-medium">Module</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Passed</th>
                  <th className="px-4 py-3 font-medium">Failed</th>
                  <th className="px-4 py-3 font-medium">Total</th>
                  <th className="px-4 py-3 font-medium">Started</th>
                  <th className="px-4 py-3 font-medium">Finished</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {suiteRuns.map((run) => (
                  <tr key={run.id}>
                    <td className="px-4 py-3">{run.suite_name}</td>
                    <td className="px-4 py-3">{run.module_name}</td>
                    <td className="px-4 py-3">{run.status}</td>
                    <td className="px-4 py-3">{run.passed}</td>
                    <td className="px-4 py-3">{run.failed}</td>
                    <td className="px-4 py-3">{run.total}</td>
                    <td className="px-4 py-3">{run.started_at}</td>
                    <td className="px-4 py-3">{run.finished_at}</td>
                  </tr>
                ))}
                {suiteRuns.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-slate-500" colSpan={8}>
                      No launcher history yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  function renderDiagnostics() {
    return (
      <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
        <SectionTitle
          icon={<Stethoscope className="h-5 w-5" />}
          title="Diagnostics"
          description="Healing history and failed steps are available again for the selected suite."
        />
        <div className="mt-6 flex flex-wrap gap-3">
          {(["Healing History", "Step Failures"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setDiagnosticView(tab)}
              className={`rounded-full border px-4 py-2 text-sm transition ${
                diagnosticView === tab
                  ? "border-cobalt bg-blue-50 text-slate-900"
                  : "border-slate-200 bg-white text-slate-600"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {diagnosticView === "Healing History" ? (
          <div className="mt-5 overflow-hidden rounded-3xl border border-slate-100">
            <div className="max-h-[520px] overflow-auto">
              <table className="min-w-full divide-y divide-slate-100 text-sm">
                <thead className="bg-slate-50">
                  <tr className="text-left text-slate-500">
                    <th className="px-4 py-3 font-medium">Updated</th>
                    <th className="px-4 py-3 font-medium">Locator</th>
                    <th className="px-4 py-3 font-medium">Strategy</th>
                    <th className="px-4 py-3 font-medium">Previous</th>
                    <th className="px-4 py-3 font-medium">Chosen</th>
                    <th className="px-4 py-3 font-medium">Module</th>
                    <th className="px-4 py-3 font-medium">Test</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {filteredHealings.map((row) => (
                    <tr key={row.id}>
                      <td className="px-4 py-3">{row.created_at || "-"}</td>
                      <td className="px-4 py-3">{row.locator_name || "-"}</td>
                      <td className="px-4 py-3">{row.strategy || "-"}</td>
                      <td className="px-4 py-3">{row.previous_selector || "-"}</td>
                      <td className="px-4 py-3">{row.chosen_selector || "-"}</td>
                      <td className="px-4 py-3">{row.module_name || "-"}</td>
                      <td className="px-4 py-3">{row.test_name || "-"}</td>
                    </tr>
                  ))}
                  {filteredHealings.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-slate-500" colSpan={7}>
                        No locator healing history yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="mt-5 overflow-hidden rounded-3xl border border-slate-100">
            <div className="max-h-[520px] overflow-auto">
              <table className="min-w-full divide-y divide-slate-100 text-sm">
                <thead className="bg-slate-50">
                  <tr className="text-left text-slate-500">
                    <th className="px-4 py-3 font-medium">Created</th>
                    <th className="px-4 py-3 font-medium">Step</th>
                    <th className="px-4 py-3 font-medium">Browser</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Remarks</th>
                    <th className="px-4 py-3 font-medium">Screenshot</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {filteredFailedSteps.map((row) => (
                    <tr key={row.id}>
                      <td className="px-4 py-3">{row.created_at || "-"}</td>
                      <td className="px-4 py-3">{row.step_name || "-"}</td>
                      <td className="px-4 py-3">{row.browser_name || "-"}</td>
                      <td className="px-4 py-3">{row.status || "-"}</td>
                      <td className="px-4 py-3">{row.remarks || "-"}</td>
                      <td className="px-4 py-3">{row.screenshot_path || "-"}</td>
                    </tr>
                  ))}
                  {filteredFailedSteps.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-slate-500" colSpan={6}>
                        No failed step screenshots available for this module.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  }

  function renderE2EAgent() {
    const caseCounts = urlAgentResult?.extra?.case_counts;
    const visualSummary = urlAgentResult?.extra?.visual_summary;
    const testCases = urlAgentResult?.extra?.test_cases || [];
    const findings = urlAgentResult?.extra?.findings || [];
    const visualFindings = urlAgentResult?.extra?.visual_findings || [];
    const humanRequired = urlAgentResult?.extra?.human_required || [];
    const visualCases = testCases.filter((item) => (item.title || "").startsWith("Visual Guard:"));
    const actionCases = testCases.filter((item) => !(item.title || "").startsWith("Visual Guard:"));

    return (
      <div className="space-y-6">
        <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
          <SectionTitle
            icon={<Bot className="h-5 w-5" />}
            title="AI URL Agent"
            description="Paste one URL and let the agent assess page behavior with the existing backend runner."
          />
          <div className="mt-6 grid gap-4 md:grid-cols-[1.5fr_0.7fr]">
            <label className="block text-sm font-medium text-slate-600">
              Target URL
              <input
                className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                value={urlAgentInput}
                onChange={(event) => setUrlAgentInput(event.target.value)}
                placeholder="https://www.example.com/page"
              />
            </label>
            <div className="flex flex-col justify-end gap-4">
              <label className="flex items-center gap-3 text-sm text-slate-600">
                <input type="checkbox" checked={urlAgentHeadless} onChange={(event) => setUrlAgentHeadless(event.target.checked)} />
                Headless
              </label>
              <label className="flex items-center gap-3 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={urlAgentVisualGuard}
                  onChange={(event) => setUrlAgentVisualGuard(event.target.checked)}
                />
                Visual Guard AI
              </label>
              <button
                type="button"
                onClick={handleRunUrlAgent}
                disabled={isRunningUrlAgent}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-4 font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRunningUrlAgent ? <LoaderCircle className="h-5 w-5 animate-spin" /> : null}
                {isRunningUrlAgent ? "Running URL Agent..." : "Run URL Agent"}
              </button>
              {activeTask?.kind === "url_agent" ? (
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={handleStopExecution}
                    disabled={!isRunningUrlAgent || isStoppingExecution}
                    className="inline-flex items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Square className="h-4 w-4" />
                    {isStoppingExecution ? "Stopping..." : "Stop"}
                  </button>
                  <button
                    type="button"
                    onClick={handleRestartExecution}
                    className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 transition hover:border-cobalt hover:text-cobalt"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Restart
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {urlAgentResult ? (
          <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
            <div className="grid gap-4 md:grid-cols-5">
              <StatCard label="Status" value={urlAgentResult.status || "-"} accent="text-slate-900" />
              <StatCard label="Executed" value={testCases.length} accent="text-slate-900" />
              <StatCard label="Passed" value={caseCounts?.Pass || 0} accent="text-emerald-600" />
              <StatCard label="Failed" value={caseCounts?.Fail || 0} accent="text-rose-600" />
              <StatCard label="Needs Review" value={caseCounts?.["Needs Review"] || 0} accent="text-amber-600" />
            </div>
            {urlAgentResult.extra?.visual_guard_enabled ? (
              <div className="mt-4 grid gap-4 md:grid-cols-4">
                <StatCard label="Visual Checks" value={visualSummary?.executed || 0} accent="text-slate-900" />
                <StatCard label="Visual Pass" value={visualSummary?.passed || 0} accent="text-emerald-600" />
                <StatCard label="Visual Fail" value={visualSummary?.failed || 0} accent="text-rose-600" />
                <StatCard label="Visual Review" value={visualSummary?.needs_review || 0} accent="text-amber-600" />
              </div>
            ) : null}
            <div className="mt-6 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl border border-slate-100 bg-slate-50 p-5">
                <h3 className="text-lg font-semibold text-slate-900">Overall Page Assessment</h3>
                <p className="mt-2 break-all text-sm text-slate-500">{urlAgentResult.extra?.url || "-"}</p>
                <div className="mt-4 space-y-2 text-sm text-slate-700">
                  {findings.length ? findings.map((item, index) => <p key={`${item}-${index}`}>- {item}</p>) : <p>No findings captured.</p>}
                </div>
                {urlAgentResult.extra?.visual_guard_enabled ? (
                  <div className="mt-6">
                    <h4 className="font-semibold text-slate-900">Visual Guard Findings</h4>
                    <div className="mt-2 space-y-2 text-sm text-slate-700">
                      {visualFindings.length ? visualFindings.map((item, index) => <p key={`${item}-${index}`}>- {item}</p>) : <p>No visual issues detected.</p>}
                    </div>
                  </div>
                ) : null}
                <div className="mt-6">
                  <h4 className="font-semibold text-slate-900">Human Intervention</h4>
                  <div className="mt-2 space-y-2 text-sm text-slate-700">
                    {humanRequired.length ? humanRequired.map((item, index) => <p key={`${item}-${index}`}>- {item}</p>) : <p>No immediate human intervention detected.</p>}
                  </div>
                </div>
              </div>
              <div className="space-y-5">
                {visualCases.length ? (
                  <div className="overflow-hidden rounded-3xl border border-slate-100">
                    <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
                      <h4 className="font-semibold text-slate-900">Visual Guard Checks</h4>
                    </div>
                    <div className="max-h-[220px] overflow-auto">
                      <table className="min-w-full divide-y divide-slate-100 text-sm">
                        <thead className="bg-slate-50">
                          <tr className="text-left text-slate-500">
                            <th className="px-4 py-3 font-medium">Check</th>
                            <th className="px-4 py-3 font-medium">Status</th>
                            <th className="px-4 py-3 font-medium">Details</th>
                            <th className="px-4 py-3 font-medium">Evidence</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                          {visualCases.map((item, index) => (
                            <tr key={`${item.title || "visual"}-${index}`}>
                              <td className="px-4 py-3">{item.title || "-"}</td>
                              <td className="px-4 py-3">{item.status || "-"}</td>
                              <td className="px-4 py-3">{item.details || "-"}</td>
                              <td className="px-4 py-3">{item.evidence || "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}
                <div className="overflow-hidden rounded-3xl border border-slate-100">
                  <table className="min-w-full divide-y divide-slate-100 text-sm">
                    <thead className="bg-slate-50">
                      <tr className="text-left text-slate-500">
                        <th className="px-4 py-3 font-medium">Test Case</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                        <th className="px-4 py-3 font-medium">Details</th>
                        <th className="px-4 py-3 font-medium">Evidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {actionCases.map((item, index) => (
                        <tr key={`${item.title || "case"}-${index}`}>
                          <td className="px-4 py-3">{item.title || "-"}</td>
                          <td className="px-4 py-3">{item.status || "-"}</td>
                          <td className="px-4 py-3">{item.details || "-"}</td>
                          <td className="px-4 py-3">{item.evidence || "-"}</td>
                        </tr>
                      ))}
                      {actionCases.length === 0 ? (
                        <tr>
                          <td className="px-4 py-6 text-slate-500" colSpan={4}>
                            No non-visual exploratory cases were executed.
                          </td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function renderActiveTab() {
    switch (activeTab) {
      case "Executions":
        return renderExecutionsTable();
      case "Downloads":
        return renderDownloads();
      case "Test Generator":
        return renderTestGenerator();
      case "Launcher History":
        return renderLauncherHistory();
      case "Diagnostics":
        return renderDiagnostics();
      case "E2E Agent":
        return renderE2EAgent();
      default:
        return null;
    }
  }

  if (!mounted) {
    return null;
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top_left,_rgba(41,84,255,0.12),_transparent_36%),linear-gradient(180deg,_#f7fbff_0%,_#eef5ff_100%)] px-4 py-5 text-ink md:px-6 xl:px-8">
      <div className="mx-auto max-w-[1720px] space-y-5">
        {activeExecutionLabel ? (
          <section className="overflow-hidden rounded-[24px] border border-blue-100 bg-white/90 shadow-soft backdrop-blur">
            <div className="h-1.5 w-full overflow-hidden bg-blue-50">
              <div className="h-full w-1/3 animate-[pulse_1.2s_ease-in-out_infinite] rounded-full bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)]" />
            </div>
            <div className="flex items-center gap-3 px-4 py-3 text-sm text-slate-700">
              <LoaderCircle className="h-4 w-4 animate-spin text-cobalt" />
              <span>{activeExecutionLabel}</span>
            </div>
          </section>
        ) : null}

        {executionNotice ? (
          <section className="rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-soft">
            {executionNotice}
          </section>
        ) : null}

        <section className="flex flex-wrap items-center justify-between gap-4 rounded-[22px] border border-white/70 bg-white/80 px-5 py-4 shadow-soft backdrop-blur">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarCollapsed((current) => !current)}
              className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-cobalt hover:text-cobalt"
            >
              {sidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            </button>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Daily QA Dashboard</p>
              <h1 className="text-2xl font-semibold text-slate-900">Clean control panel for runs, filters, and diagnostics</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill label="AI" value={derivedAiEnabled ? "Enabled" : data.status?.ai.label || "Disabled"} />
            <StatusPill
              label="TestLink"
              value={derivedTestlinkEnabled ? "Configured" : data.status?.testlink.label || "Missing Config"}
            />
            <StatusPill label="Sheet" value={selectedSheetTab || "Loading"} />
            <button
              type="button"
              onClick={() => setSettingsOpen((current) => !current)}
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-cobalt hover:text-cobalt"
            >
              {settingsOpen ? <X className="h-4 w-4" /> : <Settings2 className="h-4 w-4" />}
              {settingsOpen ? "Close Settings" : "Settings"}
            </button>
          </div>
        </section>

        <section className={`grid min-w-0 gap-5 ${sidebarCollapsed ? "lg:grid-cols-[80px_minmax(0,1fr)]" : "lg:grid-cols-[300px_minmax(0,1fr)]"}`}>
          <aside className="rounded-[24px] border border-slate-200/70 bg-white/80 p-4 shadow-soft backdrop-blur">
            {sidebarCollapsed ? (
              <div className="flex h-full flex-col items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSidebarCollapsed(false)}
                  className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-cobalt hover:text-cobalt"
                >
                  <PanelLeftOpen className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  onClick={() => setSettingsOpen(true)}
                  className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700"
                >
                  <Settings2 className="h-5 w-5" />
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">Side Panel</p>
                    <p className="mt-1 text-sm text-slate-500">Module launcher and workspace controls.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSidebarCollapsed(true)}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-cobalt hover:text-cobalt"
                  >
                    <PanelLeftClose className="h-5 w-5" />
                  </button>
                </div>

                <div className="rounded-[20px] border border-slate-200 bg-white p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Module Launcher</p>
                  <div className="mt-4 space-y-4">
                    <label className="block text-sm font-medium text-slate-600">
                      Target module
                      <select
                        className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-base text-slate-900 outline-none transition focus:border-cobalt"
                        value={selectedModule}
                        onChange={(event) => setSelectedModule(event.target.value)}
                      >
                        {data.modules.map((module) => (
                          <option key={module.id} value={module.id}>
                            {module.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div>
                      <p className="text-sm font-medium text-slate-600">Browser Mode</p>
                      <div className="mt-2 flex gap-2">
                        {(["headed", "headless"] as const).map((mode) => (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => setModuleBrowserMode(mode)}
                            className={`rounded-full border px-4 py-2 text-sm transition ${
                              moduleBrowserMode === mode
                                ? "border-cobalt bg-blue-50 text-slate-900"
                                : "border-slate-200 bg-white text-slate-600"
                            }`}
                          >
                            {mode}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid gap-3">
                      <button
                        type="button"
                        onClick={() => setIsTestPickerOpen(true)}
                        disabled={!selectedDefinition || isLoadingModuleTests || !moduleTests.length}
                        className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-sm font-semibold text-slate-800 transition hover:border-cobalt hover:text-cobalt disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isLoadingModuleTests ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <TableProperties className="h-5 w-5" />}
                        {selectedModuleTests.length
                          ? `Selected ${selectedModuleTests.length} Test Case${selectedModuleTests.length > 1 ? "s" : ""}`
                          : moduleTests.length
                            ? "Choose Test Cases"
                            : "No Test Cases Found"}
                      </button>
                      <button
                        type="button"
                        onClick={handleRunModule}
                        disabled={isRunningModule || !selectedDefinition}
                        className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-4 text-base font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isRunningModule ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <CirclePlay className="h-5 w-5" />}
                        {isRunningModule ? "Running module..." : "Run Selected Module"}
                      </button>
                      {activeTask?.kind === "module" ? (
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={handleStopExecution}
                            disabled={!isRunningModule || isStoppingExecution}
                            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <Square className="h-4 w-4" />
                            {isStoppingExecution ? "Stopping..." : "Stop"}
                          </button>
                          <button
                            type="button"
                            onClick={handleRestartExecution}
                            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 transition hover:border-cobalt hover:text-cobalt"
                          >
                            <RotateCcw className="h-4 w-4" />
                            Restart
                          </button>
                        </div>
                      ) : null}
                    </div>

                    {selectedModuleTests.length ? (
                      <div className="rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-slate-700">
                        <p>Execution mode: only the selected test cases will run without forcing login again if a saved session already exists.</p>
                        <p className="mt-2 text-xs text-slate-500">{selectedModuleTestNames.join(", ")}</p>
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                        Execution mode: the full module will run.
                      </div>
                    )}

                    {selectedDefinition ? (
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-slate-900">{selectedDefinition.label}</p>
                            <p className="mt-1">{selectedDefinition.description || "Core runner is reused as-is."}</p>
                          </div>
                          {isSheetLoading ? <LoaderCircle className="mt-1 h-4 w-4 animate-spin text-cobalt" /> : null}
                        </div>
                        <p className="mt-3 text-xs uppercase tracking-[0.2em] text-slate-400">
                          {selectedDefinition.sheet_name} / {selectedDefinition.default_tab}
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            )}
          </aside>

          <div className="min-w-0 space-y-5">
            {settingsOpen ? (
              <section className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
                <div className="flex items-center justify-between gap-4">
                  <SectionTitle
                    icon={<Settings2 className="h-5 w-5" />}
                    title="Workspace Settings"
                    description="Restored core fields from the Streamlit panel and moved them to a cleaner top section."
                  />
                  <button
                    type="button"
                    onClick={() => setSettingsOpen(false)}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <label className="block text-sm font-medium text-slate-600">
                    LLM API Key
                    <input
                      type="password"
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.llmApiKey}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, llmApiKey: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    LLM Base URL
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.llmBaseUrl}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, llmBaseUrl: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    LLM Model
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.llmModel}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, llmModel: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    Default Login Phone
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.defaultPhone}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, defaultPhone: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    Default Login OTP
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.defaultOtp}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, defaultOtp: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    TestLink API Key
                    <input
                      type="password"
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.testlinkApiKey}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, testlinkApiKey: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    TestLink URL
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.testlinkUrl}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, testlinkUrl: event.target.value }))}
                    />
                  </label>
                  <label className="block text-sm font-medium text-slate-600">
                    CA Bundle Path
                    <input
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.testlinkCaBundle}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, testlinkCaBundle: event.target.value }))}
                      placeholder="Optional PEM file path"
                    />
                  </label>
                  <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={workspaceSettings.testlinkInsecureSkipVerify}
                      onChange={(event) =>
                        setWorkspaceSettings((current) => ({ ...current, testlinkInsecureSkipVerify: event.target.checked }))
                      }
                    />
                    Skip SSL verification temporarily
                  </label>
                  <label className="block text-sm font-medium text-slate-600 md:col-span-2 xl:col-span-3">
                    SMTP Recipients
                    <textarea
                      className="mt-2 min-h-[96px] w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                      value={workspaceSettings.smtpRecipients}
                      onChange={(event) => setWorkspaceSettings((current) => ({ ...current, smtpRecipients: event.target.value }))}
                      placeholder="email1@example.com, email2@example.com"
                    />
                  </label>
                </div>
                {settingsSavedMessage ? (
                  <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {settingsSavedMessage}
                  </div>
                ) : null}
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handleSaveSettings}
                    className="rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-3 font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px]"
                  >
                    Save Workspace Settings
                  </button>
                  <p className="text-sm text-slate-400">These settings stay in your browser for the React panel.</p>
                </div>
              </section>
            ) : null}

            <section className="grid gap-4 md:grid-cols-4">
              <StatCard label="Total" value={executionTotals.total} accent="text-slate-900" loading={isSheetLoading} />
              <StatCard label="Passed" value={executionTotals.passed} accent="text-emerald-600" loading={isSheetLoading} />
              <StatCard label="Failed" value={executionTotals.failed} accent="text-rose-600" loading={isSheetLoading} />
              <StatCard label="Pass Rate" value={executionTotals.passRate} accent="text-cobalt" loading={isSheetLoading} />
            </section>

            {error ? (
              <div className="rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">{error}</div>
            ) : null}

            <section className="rounded-[24px] border border-slate-200/70 bg-white/80 p-5 shadow-soft">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Workspace Tabs</p>
                  <p className="mt-1 text-sm text-slate-500">Switch sections without losing the active module context.</p>
                </div>
                {isSheetLoading ? (
                  <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-2 text-sm text-cobalt">
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Updating counts...
                  </span>
                ) : null}
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                {DASHBOARD_TABS.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-full border px-5 py-2.5 text-sm transition ${
                      activeTab === tab
                        ? "border-cobalt bg-[linear-gradient(135deg,rgba(42,86,255,0.12),rgba(28,167,216,0.12))] text-slate-900"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </section>

            {renderActiveTab()}
          </div>
        </section>
      </div>
      {isTestPickerOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4 py-8 backdrop-blur-sm">
          <div className="flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-[32px] border border-slate-200/80 bg-white shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Module Test Picker</p>
                <h3 className="mt-1 text-xl font-semibold text-slate-900">
                  {selectedDefinition?.label || "Selected module"} test cases
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  Select all cases or just one or two from the module runner. Keep selection empty if you want to run the whole module.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsTestPickerOpen(false)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-cobalt hover:text-cobalt"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-6 py-4">
              <button
                type="button"
                onClick={() => setSelectedModuleTests(moduleTests.map((item) => item.path))}
                disabled={!moduleTests.length}
                className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-cobalt hover:text-cobalt disabled:cursor-not-allowed disabled:opacity-60"
              >
                Select All
              </button>
              <button
                type="button"
                onClick={() => setSelectedModuleTests([])}
                className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-cobalt hover:text-cobalt"
              >
                Clear Selection
              </button>
              <div className="rounded-full bg-blue-50 px-4 py-2 text-sm text-slate-700">
                {selectedModuleTests.length
                  ? `${selectedModuleTests.length} selected`
                  : "Full module run remains active"}
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto px-6 py-4">
              {isLoadingModuleTests ? (
                <div className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                  <LoaderCircle className="h-4 w-4 animate-spin text-cobalt" />
                  Loading available test cases...
                </div>
              ) : moduleTests.length ? (
                <div className="overflow-hidden rounded-3xl border border-slate-100">
                  <div className="grid grid-cols-[56px_minmax(0,1fr)] border-b border-slate-100 bg-slate-50 px-4 py-3 text-left text-sm font-medium text-slate-500">
                    <div>Pick</div>
                    <div>Test Case</div>
                  </div>
                  <div className="divide-y divide-slate-100 bg-white">
                    {moduleTests.map((item) => {
                      const selected = selectedModuleTests.includes(item.path);
                      return (
                        <label
                          key={item.id}
                          className={`grid cursor-pointer grid-cols-[56px_minmax(0,1fr)] items-start gap-3 px-4 py-4 transition ${
                            selected ? "bg-blue-50/40" : "hover:bg-slate-50/80"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() => toggleModuleTest(item.path)}
                            className="mt-1 h-5 w-5 rounded border-slate-300 text-cobalt"
                          />
                          <div className="min-w-0">
                            <p className="break-words text-base font-semibold text-slate-900">{item.label}</p>
                            <p className="mt-1 break-all font-mono text-xs text-slate-500">{item.path}</p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                  No runnable test files were found for this module yet.
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-6 py-5">
              <p className="text-sm text-slate-500">
                Existing saved login session will be reused. Login bootstrap only runs if the session file is missing.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsTestPickerOpen(false)}
                  className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-cobalt hover:text-cobalt"
                >
                  Done
                </button>
                <button
                  type="button"
                  onClick={handleRunModule}
                  disabled={isRunningModule || !selectedDefinition}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isRunningModule ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CirclePlay className="h-4 w-4" />}
                  {selectedModuleTests.length ? "Run Selected Test Cases" : "Run Full Module"}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
