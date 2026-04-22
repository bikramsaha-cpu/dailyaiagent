"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
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
  Settings2,
  Sparkles,
  Stethoscope,
  TableProperties,
  X,
} from "lucide-react";

import {
  api,
  DiagnosticsHealingItem,
  DiagnosticsStepItem,
  ModuleItem,
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
    <div className={`rounded-[28px] border border-white/60 bg-white/80 p-6 shadow-soft backdrop-blur transition-all duration-300 ${loading ? "scale-[0.99]" : "scale-100"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{label}</p>
      {loading ? (
        <div className="mt-4 h-12 w-24 animate-pulse rounded-2xl bg-slate-100" />
      ) : (
        <p className={`mt-4 text-4xl font-semibold transition-all duration-300 ${accent}`}>{value}</p>
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
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [quickFiltersOpen, setQuickFiltersOpen] = useState(true);
  const [dateRangeOpen, setDateRangeOpen] = useState(false);
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
  const [urlAgentResult, setUrlAgentResult] = useState<UrlAgentRunResponse | null>(null);
  const [error, setError] = useState("");
  const [isSheetLoading, setIsSheetLoading] = useState(false);
  const [isRunningModule, setIsRunningModule] = useState(false);
  const [isPending, startTransition] = useTransition();
  const loadedSheetTabsRef = useRef<Record<string, string[]>>({});
  const loadedSheetRecordsRef = useRef<Record<string, SheetRecord[]>>({});

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
        const [status, modules, runs, healingData, stepData] = await Promise.all([
          api.getStatus(),
          api.getModules(),
          api.getRuns(20),
          api.getDiagnosticsHealings(150),
          api.getDiagnosticsSteps(150),
        ]);
        setData({ status, modules, runs });
        setHealings(healingData);
        setStepEvents(stepData);
        setSelectedModule((current) => current || modules[0]?.id || "");
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

  useEffect(() => {
    setSelectedSheetTab("");
    setRawSheetRecords([]);
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
    if (!selectedDefinition || !selectedSheetTab) {
      return;
    }
    if (sheetTabs.length && !sheetTabs.includes(selectedSheetTab)) {
      return;
    }
    const loadTabData = async () => {
      setIsSheetLoading(true);
      setError("");
      const cacheKey = `${selectedDefinition.sheet_name}::${selectedSheetTab}`;
      const cachedRecords = loadedSheetRecordsRef.current[cacheKey];
      if (cachedRecords) {
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
      setRawSheetRecords([]);
      try {
        const payload = await api.getSheetRecords(selectedDefinition.sheet_name, selectedSheetTab);
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
    };
    void loadTabData();
  }, [selectedDefinition, selectedSheetTab]);

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
    const total = sheetRecords.length;
    const passed = sheetRecords.filter((row) => (row.Status || "").trim().toLowerCase() === "pass").length;
    const failed = sheetRecords.filter((row) => (row.Status || "").trim().toLowerCase() === "fail").length;
    const passRate = total ? `${((passed / total) * 100).toFixed(1)}%` : "0.0%";
    return { total, passed, failed, passRate };
  }, [sheetRecords]);

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

  const tableHeaders = useMemo(() => {
    if (!sheetRecords.length) {
      return [];
    }
    return Object.keys(sheetRecords[0]);
  }, [sheetRecords]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (searchText.trim()) {
      count += 1;
    }
    if (startDate || endDate) {
      count += 1;
    }
    if (statusFilter.length && statusFilter.length !== availableStatuses.length) {
      count += 1;
    }
    if (browserFilter.length && browserFilter.length !== availableBrowsers.length) {
      count += 1;
    }
    return count;
  }, [availableBrowsers.length, availableStatuses.length, browserFilter.length, endDate, searchText, startDate, statusFilter.length]);

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

  async function handleRunModule() {
    if (!selectedDefinition) {
      return;
    }
    setError("");
    setIsRunningModule(true);
    try {
      const run = await api.runModule(selectedDefinition.id);
      setData((current) => ({ ...current, runs: [run, ...current.runs].slice(0, 20) }));
      setActiveTab("Launcher History");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Module run failed.");
    } finally {
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
    try {
      const result = await api.generateTestlink({
        module_id: selectedDefinition.id,
        suite_id: Number(generatorSuiteId),
        output_dir: generatorOutputDir.trim() || undefined,
        overwrite: generatorOverwrite,
        max_cases: Number(generatorMaxCases) > 0 ? Number(generatorMaxCases) : undefined,
      });
      setGenerationResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate tests.");
    }
  }

  async function handleRunUrlAgent() {
    if (!urlAgentInput.trim()) {
      setError("Please enter a URL.");
      return;
    }
    setError("");
    try {
      const result = await api.runUrlAgent({
        url: urlAgentInput.trim(),
        headless: urlAgentHeadless,
        slow_mo: 100,
      });
      setUrlAgentResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run URL agent.");
    }
  }

  function handleSaveSettings() {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(workspaceSettings));
  }

  function renderExecutionsTable() {
    return (
      <div className="rounded-[32px] border border-slate-200/70 bg-white/85 p-6 shadow-soft">
        <SectionTitle
          icon={<Filter className="h-5 w-5" />}
          title="Filtered Execution Data"
          description={isSheetLoading ? "Refreshing records for the selected module..." : "Table filters update instantly in the current view."}
        />
        <div className="mt-5 overflow-hidden rounded-3xl border border-slate-100">
          <div className="max-h-[560px] overflow-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead className="sticky top-0 bg-slate-50">
                <tr className="text-left text-slate-500">
                  {tableHeaders.map((header) => (
                    <th key={header} className="whitespace-nowrap px-4 py-3 font-medium">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {isSheetLoading ? (
                  <tr>
                    <td className="px-4 py-8 text-slate-500" colSpan={Math.max(tableHeaders.length, 1)}>
                      <span className="inline-flex items-center gap-2">
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        Loading module data...
                      </span>
                    </td>
                  </tr>
                ) : null}
                {sheetRecords.map((row, index) => (
                  <tr key={`${row["Test Title"] || row.test_title || "row"}-${index}`}>
                    {tableHeaders.map((header) => (
                      <td key={header} className="px-4 py-3 align-top text-slate-700">
                        {row[header] || "-"}
                      </td>
                    ))}
                  </tr>
                ))}
                {!isSheetLoading && sheetRecords.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-slate-500" colSpan={Math.max(tableHeaders.length, 1)}>
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
          description="Export the current filtered execution view as CSV or HTML."
        />
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <button
            type="button"
            onClick={() => downloadFile(`${selectedSheetTab || "executions"}_filtered.csv`, buildCsv(sheetRecords), "text/csv")}
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
                buildHtmlReport(sheetRecords, filterSummary),
                "text/html",
              )
            }
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-left text-slate-900 transition hover:border-cobalt hover:bg-blue-50"
          >
            <p className="font-semibold">Download HTML Report</p>
            <p className="mt-1 text-sm text-slate-500">Shareable report with filter context and table data.</p>
          </button>
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
            className="mt-6 inline-flex rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-4 font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px]"
          >
            Generate Tests
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
    const testCases = urlAgentResult?.extra?.test_cases || [];
    const findings = urlAgentResult?.extra?.findings || [];
    const humanRequired = urlAgentResult?.extra?.human_required || [];

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
              <button
                type="button"
                onClick={handleRunUrlAgent}
                className="inline-flex rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-4 font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px]"
              >
                Run URL Agent
              </button>
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
            <div className="mt-6 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl border border-slate-100 bg-slate-50 p-5">
                <h3 className="text-lg font-semibold text-slate-900">Overall Page Assessment</h3>
                <p className="mt-2 break-all text-sm text-slate-500">{urlAgentResult.extra?.url || "-"}</p>
                <div className="mt-4 space-y-2 text-sm text-slate-700">
                  {findings.length ? findings.map((item, index) => <p key={`${item}-${index}`}>- {item}</p>) : <p>No findings captured.</p>}
                </div>
                <div className="mt-6">
                  <h4 className="font-semibold text-slate-900">Human Intervention</h4>
                  <div className="mt-2 space-y-2 text-sm text-slate-700">
                    {humanRequired.length ? humanRequired.map((item, index) => <p key={`${item}-${index}`}>- {item}</p>) : <p>No immediate human intervention detected.</p>}
                  </div>
                </div>
              </div>
              <div className="overflow-hidden rounded-3xl border border-slate-100">
                <div className="max-h-[420px] overflow-auto">
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
                      {testCases.map((item, index) => (
                        <tr key={`${item.title || "case"}-${index}`}>
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
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(41,84,255,0.12),_transparent_36%),linear-gradient(180deg,_#f7fbff_0%,_#eef5ff_100%)] px-6 py-8 text-ink md:px-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-[28px] border border-white/70 bg-white/80 px-5 py-4 shadow-soft backdrop-blur">
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
            <StatusPill label="AI" value={data.status?.ai.label || "Loading"} />
            <StatusPill label="TestLink" value={data.status?.testlink.label || "Loading"} />
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

        <section className={`grid gap-6 ${sidebarCollapsed ? "lg:grid-cols-[88px_minmax(0,1fr)]" : "lg:grid-cols-[330px_minmax(0,1fr)]"}`}>
          <aside className="rounded-[32px] border border-slate-200/70 bg-white/80 p-4 shadow-soft backdrop-blur">
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
                  onClick={() => setQuickFiltersOpen(true)}
                  className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700"
                >
                  <Filter className="h-5 w-5" />
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
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">Side Panel</p>
                    <p className="mt-1 text-sm text-slate-500">Module, sheet tab, and quick filters in one place.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSidebarCollapsed(true)}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-cobalt hover:text-cobalt"
                  >
                    <PanelLeftClose className="h-5 w-5" />
                  </button>
                </div>

                <div className="rounded-[28px] border border-slate-200 bg-white p-4">
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

                    <button
                      type="button"
                      onClick={handleRunModule}
                      disabled={isRunningModule || !selectedDefinition}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#2a56ff,_#1ca7d8)] px-5 py-4 text-base font-semibold text-white shadow-lg shadow-cyanflash/20 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isRunningModule ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <CirclePlay className="h-5 w-5" />}
                      {isRunningModule ? "Running module..." : "Run Selected Module"}
                    </button>

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

                <div className="rounded-[28px] border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Filters</p>
                      <p className="mt-1 text-sm text-slate-500">{activeFilterCount ? `${activeFilterCount} active` : "Ready to filter"}</p>
                    </div>
                    <button
                      type="button"
                      onClick={resetFilters}
                      className="rounded-full border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 transition hover:border-cobalt hover:text-cobalt"
                    >
                      Reset
                    </button>
                  </div>

                  <div className="mt-4 space-y-4">
                    <label className="block text-sm font-medium text-slate-600">
                      Google Sheet Tab
                      <select
                        className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-base text-slate-900 outline-none transition focus:border-cobalt"
                        value={selectedSheetTab}
                        onChange={(event) => setSelectedSheetTab(event.target.value)}
                      >
                        {sheetTabs.map((tab) => (
                          <option key={tab} value={tab}>
                            {tab}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block text-sm font-medium text-slate-600">
                      Search
                      <input
                        className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                        value={searchText}
                        onChange={(event) => setSearchText(event.target.value)}
                        placeholder="Search title, remarks, browser, phone..."
                      />
                    </label>

                    <div className="grid gap-3 md:grid-cols-2">
                      <label className="block text-sm font-medium text-slate-600">
                        Start date
                        <input
                          type="date"
                          className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                          value={startDate}
                          onChange={(event) => setStartDate(event.target.value)}
                        />
                      </label>
                      <label className="block text-sm font-medium text-slate-600">
                        End date
                        <input
                          type="date"
                          className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-cobalt"
                          value={endDate}
                          onChange={(event) => setEndDate(event.target.value)}
                        />
                      </label>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <p className="text-sm font-medium text-slate-600">Status</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {availableStatuses.map((status) => (
                            <FilterChip
                              key={status}
                              label={status}
                              active={statusFilter.includes(status)}
                              onClick={() => setStatusFilter((current) => toggleFilterValue(current, status))}
                            />
                          ))}
                        </div>
                      </div>

                      <div>
                        <p className="text-sm font-medium text-slate-600">Browser</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {availableBrowsers.map((browser) => (
                            <FilterChip
                              key={browser}
                              label={browser}
                              active={browserFilter.includes(browser)}
                              onClick={() => setBrowserFilter((current) => toggleFilterValue(current, browser))}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </aside>

          <div className="space-y-6">
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

            <section className="rounded-[32px] border border-slate-200/70 bg-white/80 p-5 shadow-soft">
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
                    className={`rounded-full border px-5 py-3 text-base transition ${
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
    </main>
  );
}
