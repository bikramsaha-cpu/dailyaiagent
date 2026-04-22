const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "/api/proxy";

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
      `Backend API is unreachable. Start FastAPI on port 8000 or configure NEXT_PUBLIC_API_BASE_URL / API_SERVER_URL. ${message}`,
    );
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
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
    human_required?: string[];
    screenshot_path?: string;
    case_counts?: Record<string, number>;
    test_cases?: UrlAgentCase[];
  };
};

export const api = {
  getStatus: () => request<StatusPayload>("/status"),
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
    return request<{ records: SheetRecord[]; count: number }>(`/sheets/records?${params.toString()}`);
  },
  getDiagnosticsHealings: (limit = 100) =>
    request<DiagnosticsHealingItem[]>(`/diagnostics/healings?limit=${limit}`),
  getDiagnosticsSteps: (limit = 100) =>
    request<DiagnosticsStepItem[]>(`/diagnostics/steps?limit=${limit}`),
  runModule: (moduleId: string) =>
    request<RunItem>(`/modules/${moduleId}/run`, { method: "POST" }),
  generateTestlink: (payload: {
    module_id: string;
    suite_id: number;
    output_dir?: string;
    overwrite?: boolean;
    max_cases?: number;
  }) =>
    request<TestLinkGenerationResponse>("/testlink/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runUrlAgent: (payload: { url: string; headless?: boolean; slow_mo?: number }) =>
    request<UrlAgentRunResponse>("/url-agent/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export { API_BASE_URL };
