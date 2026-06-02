const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "/qa-ai-agent/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "The frontend could not reach the API server.";
    throw new Error(
      `Backend API is unreachable. Start the Next.js app or configure NEXT_PUBLIC_API_BASE_URL. ${message}`,
    );
  }
  if (!response.ok) {
    const text = await response.text();
    if (text) {
      try {
        const parsed = JSON.parse(text) as { detail?: string };
        throw new Error(parsed.detail || text);
      } catch {
        throw new Error(text);
      }
    }
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type ModuleItem = {
  id: string;
  label: string;
  suite: string;
  description: string;
  sheet_name: string;
  default_tab: string;
  runner: string;
};

export type ModuleTestItem = {
  id: string;
  label: string;
  path: string;
  group: string;
};

export type RunItem = {
  id: number;
  module_name: string;
  suite_name: string;
  started_at: string;
  finished_at: string;
  status: string;
  passed: number;
  failed: number;
  total: number;
  stdout?: string;
  stderr?: string;
};

export type StatusPayload = {
  ai: { enabled: boolean; label: string; base_url: string; model: string };
  testlink: { enabled: boolean; label: string; url: string };
};

export type SheetRecord = Record<string, string>;

export type DiagnosticsHealingItem = {
  id: number;
  created_at?: string;
  suite_name?: string;
  module_name?: string;
  test_name?: string;
  locator_name?: string;
  previous_selector?: string;
  strategy?: string;
  chosen_selector?: string;
  page_url?: string;
  page_title?: string;
  html_snapshot?: string;
  details_json?: Record<string, unknown>;
};

export type DiagnosticsStepItem = {
  id: number;
  created_at?: string;
  suite_name?: string;
  module_name?: string;
  test_name?: string;
  browser_name?: string;
  step_name?: string;
  status?: string;
  remarks?: string;
  screenshot_path?: string;
  run_time?: string;
  extra_json?: Record<string, unknown>;
};

export type TestLinkGenerationResult = {
  title: string;
  status: string;
  detail: string;
  output_path?: string | null;
};

export type TestLinkGenerationResponse = {
  module: ModuleItem;
  suite_id: number;
  output_dir: string;
  generated: number;
  skipped: number;
  failed: number;
  results: TestLinkGenerationResult[];
};

export type UrlAgentCase = {
  title?: string;
  status?: string;
  details?: string;
  evidence?: string;
};

export type UrlAgentRunResponse = {
  id?: number;
  suite_name?: string;
  module_name?: string;
  status?: string;
  report_path?: string;
  extra?: {
    url?: string;
    findings?: string[];
    visual_findings?: string[];
    human_required?: string[];
    screenshot_path?: string;
    case_counts?: Record<string, number>;
    visual_summary?: Record<string, number>;
    visual_guard_enabled?: boolean;
    test_cases?: UrlAgentCase[];
  };
};

export type ExecutionTask = {
  id: string;
  kind: "module" | "url_agent";
  title: string;
  started_at: string;
  status: "running" | "completed" | "failed" | "stopped";
  browser_mode: "headed" | "headless";
  command: string;
  cwd: string;
  payload: Record<string, unknown>;
  pid?: number | null;
  finished_at?: string | null;
  result?: RunItem | UrlAgentRunResponse | null;
  error?: string | null;
};

export type EmailReportResponse = {
  sent: boolean;
  recipients: string[];
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
};

export const api = {
  getStatus: () => request<StatusPayload>("/status"),
  saveWorkspaceSettings: (payload: {
    llm_api_key?: string;
    llm_base_url?: string;
    llm_model?: string;
    default_login_phone?: string;
    default_login_otp?: string;
    testlink_api_key?: string;
    testlink_url?: string;
    testlink_ca_bundle?: string;
    testlink_insecure_skip_verify?: boolean;
    smtp_recipients?: string;
  }) =>
    request<{ saved: boolean; keys: string[] }>("/settings/workspace", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getModules: () => request<ModuleItem[]>("/modules"),
  getRuns: (limit = 20, suiteName?: string) =>
    request<RunItem[]>(
      `/runs?limit=${limit}${suiteName ? `&suite_name=${encodeURIComponent(suiteName)}` : ""}`,
    ),
  getSheetTabs: (sheetName: string, fallbackTab: string) =>
    request<{ tabs: string[] }>(
      `/sheets/tabs?sheet_name=${encodeURIComponent(sheetName)}&fallback_tab=${encodeURIComponent(fallbackTab)}`,
    ),
  getSheetRecords: (
    sheetName: string,
    tabName: string,
    filters?: {
      status?: string[];
      browser?: string[];
      start_date?: string;
      end_date?: string;
      search?: string;
      force_refresh?: boolean;
    },
  ) => {
    const params = new URLSearchParams({
      sheet_name: sheetName,
      tab_name: tabName,
    });
    for (const value of filters?.status || []) {
      params.append("status", value);
    }
    for (const value of filters?.browser || []) {
      params.append("browser", value);
    }
    if (filters?.start_date) {
      params.set("start_date", filters.start_date);
    }
    if (filters?.end_date) {
      params.set("end_date", filters.end_date);
    }
    if (filters?.search) {
      params.set("search", filters.search);
    }
    if (filters?.force_refresh) {
      params.set("force_refresh", "true");
    }
    return request<{ records: SheetRecord[]; count: number }>(`/sheets/records?${params.toString()}`);
  },
  getDiagnosticsHealings: (limit = 100) =>
    request<DiagnosticsHealingItem[]>(`/diagnostics/healings?limit=${limit}`),
  getDiagnosticsSteps: (limit = 100) =>
    request<DiagnosticsStepItem[]>(`/diagnostics/steps?limit=${limit}`),
  getModuleTests: (moduleId: string) => request<{ tests: ModuleTestItem[] }>(`/modules/${moduleId}/tests`),
  startModuleExecution: (payload: {
    module_id: string;
    browser_mode: "headed" | "headless";
    selected_tests?: string[];
    llm_api_key?: string;
    llm_base_url?: string;
    llm_model?: string;
    default_login_phone?: string;
    default_login_otp?: string;
    smtp_recipients?: string;
  }) =>
    request<ExecutionTask>("/executions/module/start", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  startUrlAgentExecution: (payload: { url: string; headless?: boolean; slow_mo?: number; visual_guard?: boolean }) =>
    request<ExecutionTask>("/executions/url-agent/start", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getActiveExecutions: () => request<ExecutionTask[]>("/executions/active"),
  getExecution: (taskId: string) => request<ExecutionTask>(`/executions/${taskId}`),
  stopExecution: (taskId: string) =>
    request<ExecutionTask>(`/executions/${taskId}/stop`, {
      method: "POST",
    }),
  restartExecution: (taskId: string) =>
    request<ExecutionTask>(`/executions/${taskId}/restart`, {
      method: "POST",
    }),
  runModule: (moduleId: string) =>
    request<RunItem>(`/modules/${moduleId}/run`, { method: "POST" }),
  generateTestlink: (payload: {
    module_id: string;
    suite_id: number;
    output_dir?: string;
    overwrite?: boolean;
    max_cases?: number;
    testlink_api_key?: string;
    testlink_url?: string;
    testlink_ca_bundle?: string;
    testlink_insecure_skip_verify?: boolean;
    llm_api_key?: string;
    llm_base_url?: string;
    llm_model?: string;
  }) =>
    request<TestLinkGenerationResponse>("/testlink/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runUrlAgent: (payload: { url: string; headless?: boolean; slow_mo?: number; visual_guard?: boolean }) =>
    request<UrlAgentRunResponse>("/url-agent/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  sendSheetReportEmail: (payload: {
    module_id: string;
    sheet_name: string;
    tab_name: string;
    status?: string[];
    browser?: string[];
    start_date?: string;
    end_date?: string;
    search?: string;
    recipients?: string[];
  }) =>
    request<EmailReportResponse>("/reports/email", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export { API_BASE_URL };
