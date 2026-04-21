from __future__ import annotations

import csv
import html
import io
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UI_SETTINGS_PATH = ROOT_DIR / "artifacts" / "ui_settings.json"
AGENT_FLOWS_DIR = ROOT_DIR / "artifacts" / "agent_flows"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from core.google_logger import GoogleSheetLogger
from core.mailer import send_run_report_email
from core.module_registry import load_modules
from core.runner import ModuleRunner
from core.testlink_generator import TestLinkCaseGenerator, TestLinkGeneratorConfig, default_output_dir_for_module
from core.store import ExecutionStore
from core.settings import DEFAULT_SHEET_NAME


st.set_page_config(page_title="Daily QA Automation", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
        :root {
            --surface: rgba(255,255,255,0.88);
            --surface-strong: rgba(255,255,255,0.96);
            --surface-tint: rgba(248, 250, 252, 0.92);
            --panel-border: rgba(148, 163, 184, 0.18);
            --panel-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
            --navy: #10213c;
            --blue: #2563eb;
            --cyan: #0ea5e9;
            --teal: #0f766e;
            --rose: #fb7185;
            --amber: #f59e0b;
            --text-main: #0f172a;
            --text-soft: #64748b;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.16), transparent 25%),
                radial-gradient(circle at 82% 12%, rgba(14, 165, 233, 0.14), transparent 22%),
                radial-gradient(circle at 70% 80%, rgba(251, 113, 133, 0.08), transparent 20%),
                linear-gradient(180deg, #f2f7ff 0%, #f8fbff 24%, #ffffff 52%, #f8fafc 100%);
            color: var(--text-main);
        }
        .block-container {
            padding-top: 1.3rem;
            padding-bottom: 2.4rem;
            max-width: 1380px;
        }
        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.22);
        }
        section[data-testid="stSidebar"] * {
            color: #1e293b;
        }
        section[data-testid="stSidebar"] .stTextInput label,
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stMultiSelect label,
        section[data-testid="stSidebar"] .stDateInput label,
        section[data-testid="stSidebar"] .stCheckbox label,
        section[data-testid="stSidebar"] .stTextArea label {
            color: #475569 !important;
        }
        .sidebar-brand {
            padding: 1rem 1rem 0.95rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #dbeafe, #ecfeff);
            border: 1px solid rgba(59, 130, 246, 0.18);
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.08);
            margin-bottom: 1rem;
        }
        .sidebar-brand h3 {
            margin: 0 0 0.25rem 0;
            font-size: 1.15rem;
            color: #0f172a;
        }
        .sidebar-brand p {
            margin: 0;
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.45;
        }
        .sidebar-section-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #2563eb;
            margin: 0.15rem 0 0.6rem;
        }
        .hero {
            padding: 1.55rem 1.65rem;
            border-radius: 32px;
            background:
                radial-gradient(circle at top right, rgba(186, 230, 253, 0.35), transparent 30%),
                radial-gradient(circle at 20% 120%, rgba(251, 191, 36, 0.18), transparent 22%),
                linear-gradient(135deg, #10213c 0%, #1d4ed8 50%, #0891b2 100%);
            color: white;
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.14);
            margin-bottom: 1.1rem;
        }
        .hero h1 {
            font-size: 2.55rem;
            margin-bottom: 0.2rem;
            line-height: 1;
        }
        .hero p {
            margin: 0;
            opacity: 0.92;
            font-size: 1.02rem;
            max-width: 780px;
            line-height: 1.6;
        }
        .hero-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 1rem;
        }
        .hero-badge {
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.18);
            font-size: 0.86rem;
            color: #eff6ff;
            backdrop-filter: blur(10px);
        }
        .context-strip {
            background: var(--surface);
            border: 1px solid var(--panel-border);
            border-radius: 20px;
            padding: 1rem 1.1rem;
            box-shadow: var(--panel-shadow);
            margin-bottom: 1rem;
            color: #475569;
            font-size: 0.95rem;
        }
        .section-card {
            background: var(--surface);
            border: 1px solid var(--panel-border);
            border-radius: 24px;
            padding: 1rem 1.1rem;
            box-shadow: var(--panel-shadow);
        }
        .section-header {
            margin: 0 0 0.85rem 0;
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--text-main);
        }
        .section-subtle {
            color: var(--text-soft);
            margin: -0.2rem 0 1rem 0;
            font-size: 0.96rem;
        }
        .metric-card {
            background: var(--surface-strong);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 22px;
            padding: 1rem 1rem 0.85rem;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
            min-height: 136px;
        }
        .metric-card:hover,
        .section-card:hover {
            transform: translateY(-1px);
            transition: transform 160ms ease, box-shadow 160ms ease;
            box-shadow: 0 22px 46px rgba(15, 23, 42, 0.08);
        }
        .metric-value {
            font-size: 1.1rem;
            font-weight: 800;
            line-height: 1.45;
            word-break: break-word;
            overflow-wrap: anywhere;
            display: -webkit-box;
            -webkit-line-clamp: 4;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .agent-shell {
            background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(248,250,252,0.98));
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 26px;
            padding: 1.1rem 1.1rem 1rem;
            box-shadow: 0 18px 48px rgba(15, 23, 42, 0.06);
            margin-bottom: 1rem;
        }
        .agent-hero {
            background: linear-gradient(135deg, #111827 0%, #0f766e 52%, #14b8a6 100%);
            color: white;
            border-radius: 20px;
            padding: 1.15rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.12);
        }
        .agent-hero h3 {
            margin: 0 0 0.25rem 0;
            font-size: 1.5rem;
        }
        .agent-hero p {
            margin: 0;
            opacity: 0.92;
        }
        .small-label {
            color: #64748b;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.25rem;
        }
        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin: 0.2rem 0 0.1rem 0;
        }
        .pill {
            padding: 0.45rem 0.75rem;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.08);
            border: 1px solid rgba(37, 99, 235, 0.12);
            color: #1e3a8a;
            font-size: 0.88rem;
            font-weight: 600;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.14);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        }
        .stDataFrame thead tr th {
            background: #f8fafc !important;
        }
        .stButton > button,
        div[data-testid="stButton"] > button,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            border-radius: 14px;
            padding: 0.68rem 1rem;
            font-weight: 700;
            border: 0;
            box-shadow: 0 10px 22px rgba(37, 99, 235, 0.14);
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stButton > button:hover,
        div[data-testid="stButton"] > button:hover,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
            filter: brightness(1.03);
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stButton > button *,
        div[data-testid="stButton"] > button *,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stDownloadButton > button {
            border-radius: 14px;
            border: 1px solid rgba(37, 99, 235, 0.16);
            background: white;
            color: var(--navy);
            font-weight: 700;
        }
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stSelectbox [data-baseweb="select"],
        .stMultiSelect [data-baseweb="select"] {
            border-radius: 16px !important;
            border: 1px solid rgba(148, 163, 184, 0.2) !important;
            background: rgba(255,255,255,0.95) !important;
            box-shadow: inset 0 1px 1px rgba(15, 23, 42, 0.02);
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus {
            border-color: rgba(37, 99, 235, 0.36) !important;
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08) !important;
        }
        .settings-note {
            color: #64748b;
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            border-bottom: 0;
            margin-bottom: 0.8rem;
            padding: 0.2rem;
            background: rgba(255,255,255,0.58);
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 999px;
            width: fit-content;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            background: rgba(255,255,255,0.7);
            border: 1px solid rgba(148, 163, 184, 0.18);
            padding: 0.45rem 0.95rem;
            height: auto;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #dbeafe, #ecfeff);
            color: #0f172a;
            border-color: rgba(37, 99, 235, 0.22);
        }
        .stExpander {
            border: 1px solid rgba(148, 163, 184, 0.16) !important;
            border-radius: 18px !important;
            background: rgba(255,255,255,0.62);
        }
        .stAlert {
            border-radius: 18px;
            border: 0;
        }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"],
        section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"],
        section[data-testid="stSidebar"] .stTextInput input,
        section[data-testid="stSidebar"] .stTextArea textarea,
        section[data-testid="stSidebar"] .stDateInput input {
            background: rgba(255,255,255,0.96) !important;
            color: #0f172a !important;
        }
        section[data-testid="stSidebar"] .stExpander details {
            background: rgba(255,255,255,0.68);
            border-radius: 18px;
        }
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] p {
            color: #64748b !important;
        }
        .latest-run-shell {
            background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,252,0.98));
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 26px;
            padding: 1rem 1.1rem;
            box-shadow: var(--panel-shadow);
            margin: 0.2rem 0 1.2rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_modules():
    return load_modules()


@st.cache_resource
def get_store():
    return ExecutionStore()


@st.cache_resource
def get_runner():
    return ModuleRunner(store=get_store())


@st.cache_resource
def get_sheet_logger(sheet_name: str, tab_name: str):
    return GoogleSheetLogger(sheet_name, tab_name)


@st.cache_data(ttl=30)
def get_tab_names(sheet_name: str, fallback_tab: str) -> list[str]:
    try:
        logger = get_sheet_logger(sheet_name, fallback_tab)
        return logger.list_tab_names()
    except Exception:
        return []


@st.cache_data(ttl=20)
def read_sheet_records(sheet_name: str, tab_name: str) -> list[dict[str, str]]:
    logger = get_sheet_logger(sheet_name, tab_name)
    return logger.read_records(tab_name)


@st.cache_data(ttl=20)
def read_healing_records(limit: int = 100) -> list[dict[str, str]]:
    return get_store().list_locator_healings(limit=limit)


@st.cache_data(ttl=20)
def read_step_events(limit: int = 100) -> list[dict[str, str]]:
    try:
        from core.store import ExecutionStore as _ExecutionStore
        return _ExecutionStore().list_step_events(limit=limit)
    except Exception:
        return []


def get_ai_status() -> dict[str, str]:
    api_key = os.getenv("AUTOMATION_LLM_API_KEY", "").strip()
    base_url = os.getenv("AUTOMATION_LLM_BASE_URL", "").strip()
    model = os.getenv("AUTOMATION_LLM_MODEL", "").strip()
    enabled = bool(api_key and base_url and model)
    return {
        "enabled": "Enabled" if enabled else "Disabled",
        "base_url": base_url or "-",
        "model": model or "-",
    }


def get_testlink_status(saved_settings: dict[str, str]) -> dict[str, str]:
    api_key = (
        os.getenv("AUTOMATION_TESTLINK_API_KEY", "").strip()
        or os.getenv("TESTLINK_API_KEY", "").strip()
        or saved_settings.get("AUTOMATION_TESTLINK_API_KEY", "").strip()
    )
    url = (
        os.getenv("AUTOMATION_TESTLINK_URL", "").strip()
        or os.getenv("TESTLINK_URL", "").strip()
        or saved_settings.get("AUTOMATION_TESTLINK_URL", "").strip()
    )
    return {
        "enabled": "Configured" if api_key and url else "Missing Config",
        "url": url or "-",
    }


def get_runtime_setting(saved_settings: dict[str, str], primary_key: str, *fallback_keys: str, default: str = "") -> str:
    for key in (primary_key, *fallback_keys):
        value = os.getenv(key, "").strip()
        if value:
            return value
    for key in (primary_key, *fallback_keys):
        value = str(saved_settings.get(key, "")).strip()
        if value:
            return value
    return default


def load_ui_settings() -> dict[str, str]:
    if UI_SETTINGS_PATH.exists():
        try:
            return json.loads(UI_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_ui_settings(values: dict[str, str]) -> None:
    UI_SETTINGS_PATH.write_text(json.dumps(values, indent=2), encoding="utf-8")
    for key, value in values.items():
        if value:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


def parse_recipients(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def render_settings_panel(saved_settings: dict[str, str]) -> None:
    st.markdown("<div class='sidebar-section-title'>Workspace Settings</div>", unsafe_allow_html=True)
    with st.expander("Open Settings", expanded=False):
        st.markdown("#### AI")
        existing_recipients = parse_recipients(
            os.getenv(
                "AUTOMATION_SMTP_RECIPIENTS",
                saved_settings.get("AUTOMATION_SMTP_RECIPIENTS", ""),
            )
        )
        settings_values = {
            "AUTOMATION_LLM_API_KEY": st.text_input(
                "API Key",
                value=os.getenv("AUTOMATION_LLM_API_KEY", saved_settings.get("AUTOMATION_LLM_API_KEY", "")),
                type="password",
            ),
            "AUTOMATION_LLM_BASE_URL": st.text_input(
                "Base URL",
                value=os.getenv("AUTOMATION_LLM_BASE_URL", saved_settings.get("AUTOMATION_LLM_BASE_URL", "https://imllm.intermesh.net/v1")),
            ),
            "AUTOMATION_LLM_MODEL": st.text_input(
                "Model",
                value=os.getenv("AUTOMATION_LLM_MODEL", saved_settings.get("AUTOMATION_LLM_MODEL", "anthropic/claude-sonnet-4-6")),
            ),
            "AUTOMATION_DEFAULT_LOGIN_PHONE": st.text_input(
                "Default Login Phone",
                value=os.getenv("AUTOMATION_DEFAULT_LOGIN_PHONE", saved_settings.get("AUTOMATION_DEFAULT_LOGIN_PHONE", "9643193481")),
            ),
            "AUTOMATION_DEFAULT_LOGIN_OTP": st.text_input(
                "Default Login OTP",
                value=os.getenv("AUTOMATION_DEFAULT_LOGIN_OTP", saved_settings.get("AUTOMATION_DEFAULT_LOGIN_OTP", "1956")),
            ),
        }

        st.markdown("#### TestLink")
        settings_values.update(
            {
                "AUTOMATION_TESTLINK_API_KEY": st.text_input(
                    "TestLink API Key",
                    value=os.getenv(
                        "AUTOMATION_TESTLINK_API_KEY",
                        os.getenv("TESTLINK_API_KEY", saved_settings.get("AUTOMATION_TESTLINK_API_KEY", "")),
                    ),
                    type="password",
                ),
                "AUTOMATION_TESTLINK_URL": st.text_input(
                    "TestLink URL",
                    value=os.getenv(
                        "AUTOMATION_TESTLINK_URL",
                        os.getenv(
                            "TESTLINK_URL",
                            saved_settings.get(
                                "AUTOMATION_TESTLINK_URL",
                                "https://testlink.intermesh.net/lib/api/xmlrpc/v1/xmlrpc.php",
                            ),
                        ),
                    ),
                ),
                "AUTOMATION_TESTLINK_CA_BUNDLE": st.text_input(
                    "CA Bundle Path",
                    value=os.getenv(
                        "AUTOMATION_TESTLINK_CA_BUNDLE",
                        os.getenv("TESTLINK_CA_BUNDLE", saved_settings.get("AUTOMATION_TESTLINK_CA_BUNDLE", "")),
                    ),
                    placeholder="Optional PEM file path",
                ),
                "AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY": "1"
                if st.checkbox(
                    "Skip SSL verification temporarily",
                    value=(
                        os.getenv(
                            "AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY",
                            os.getenv("TESTLINK_INSECURE_SKIP_VERIFY", saved_settings.get("AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY", "1")),
                        )
                        .strip()
                        .lower()
                        not in {"0", "false", "no"}
                    ),
                )
                else "0",
            }
        )

        st.markdown("#### Notifications")
        selected_existing_recipients = st.multiselect(
            "Existing Recipients",
            options=existing_recipients,
            default=existing_recipients,
            help="Keep selected recipients and add new ones below.",
        )
        new_recipients = st.text_area(
            "Add More Recipients",
            value="",
            height=90,
            placeholder="Enter email addresses separated by commas",
        )
        combined_recipients = []
        for recipient in selected_existing_recipients + parse_recipients(new_recipients):
            if recipient not in combined_recipients:
                combined_recipients.append(recipient)
        settings_values["AUTOMATION_SMTP_RECIPIENTS"] = ",".join(combined_recipients)

        if combined_recipients:
            st.caption("Saved recipients: " + ", ".join(combined_recipients))
        else:
            st.caption("No recipients configured yet.")

        if st.button("Save Workspace Settings", use_container_width=True):
            save_ui_settings(settings_values)
            st.success("Settings saved.")
        st.markdown("<div class='settings-note'>Settings are stored locally for this workspace.</div>", unsafe_allow_html=True)


def healing_outcome_label(row: dict[str, str]) -> str:
    strategy = (row.get("strategy") or "").strip().lower()
    details = row.get("details_json") or {}
    if not isinstance(details, dict):
        details = {}
    failure_notes = details.get("failure_notes") or []
    note_blob = " ".join(str(item) for item in failure_notes).lower()
    tried_blob = " ".join(str(item) for item in (details.get("tried") or [])).lower()

    if strategy == "unresolved":
        return "healing attempted but unresolved"
    if "popup" in strategy or "overlay" in strategy or "popup" in note_blob or "overlay" in note_blob or "close-btn" in tried_blob:
        return "healed after popup bypass"
    return "healed successfully"


def diagnostics_provider_label(payload: dict[str, str] | None) -> str:
    if not isinstance(payload, dict):
        return "playwright"
    details = payload.get("details_json") or payload.get("extra_json") or {}
    if not isinstance(details, dict):
        return "playwright"
    diagnostics = details.get("diagnostics") or {}
    if not isinstance(diagnostics, dict):
        return "playwright"
    return diagnostics.get("provider") or "playwright"


def build_csv_bytes(records: list[dict[str, str]]) -> bytes:
    if not records:
        return b""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8")


def build_html_report(tab_name: str, records: list[dict[str, str]], filters: dict[str, str]) -> bytes:
    rows = ""
    for record in records:
        rows += "<tr>" + "".join(f"<td>{record.get(col, '')}</td>" for col in record.keys()) + "</tr>"

    headers = "".join(f"<th>{col}</th>" for col in records[0].keys()) if records else "<th>No data</th>"
    filters_html = "".join(
        f"<li><b>{key}:</b> {value or 'All'}</li>" for key, value in filters.items()
    )

    html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Inter, Arial, sans-serif; color: #0f172a; padding: 24px; }}
          h1 {{ margin-bottom: 0.2rem; }}
          .meta {{ color: #475569; margin-bottom: 16px; }}
          .filters {{ background: #f8fafc; padding: 14px 16px; border-radius: 14px; margin-bottom: 18px; }}
          table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
          th, td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; vertical-align: top; }}
          th {{ background: #0f172a; color: white; position: sticky; top: 0; }}
          tr:nth-child(even) {{ background: #f8fafc; }}
        </style>
      </head>
      <body>
        <h1>{tab_name} Execution Report</h1>
        <div class="meta">Generated from Google Sheets data</div>
        <div class="filters">
          <strong>Filters</strong>
          <ul>{filters_html}</ul>
        </div>
        <table>
          <tr>{headers}</tr>
          {rows or '<tr><td>No records found</td></tr>'}
        </table>
      </body>
    </html>
    """
    return html.encode("utf-8")


def short_text(value: str | None, limit: int = 90) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return html.escape(text or "-")
    return html.escape(text[: limit - 1].rstrip() + "...")


DEFAULT_AGENT_STEPS = json.dumps(
    [
        {
            "name": "Wait for page heading",
            "action": "wait_for",
            "selector": "h1",
        },
        {
            "name": "Capture page",
            "action": "screenshot",
            "screenshot_name": "journey_home.png",
        },
    ],
    indent=2,
)


def parse_browser_selection(browser_labels: list[str]) -> list[str]:
    mapping = {
        "Chromium": "chromium",
        "Firefox": "firefox",
    }
    browsers = [mapping[label] for label in browser_labels if label in mapping]
    return browsers or ["chromium"]


def save_agent_flow(flow_payload: dict[str, object], module_name: str) -> Path:
    AGENT_FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in module_name).strip("_") or "agent_flow"
    target = AGENT_FLOWS_DIR / f"{safe_name}_{stamp}.json"
    target.write_text(json.dumps(flow_payload, indent=2), encoding="utf-8")
    return target


def build_agent_flow_payload(
    *,
    suite_name: str,
    module_name: str,
    start_url: str,
    browsers: list[str],
    headless: bool,
    slow_mo: int,
    steps_text: str,
) -> tuple[dict[str, object] | None, str | None]:
    try:
        steps = json.loads(steps_text)
    except json.JSONDecodeError as exc:
        return None, f"Journey JSON is invalid: {exc}"
    if not isinstance(steps, list):
        return None, "Journey JSON must be an array of step objects."
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            return None, f"Step {index} must be a JSON object."
        if not step.get("name") or not step.get("action"):
            return None, f"Step {index} must include both 'name' and 'action'."
    payload = {
        "suite_name": suite_name.strip() or "Agentic E2E",
        "module_name": module_name.strip() or "custom_journey",
        "base_url": start_url.strip(),
        "start_url": start_url.strip(),
        "browsers": browsers,
        "headless": headless,
        "slow_mo": int(slow_mo),
        "steps": steps,
    }
    return payload, None


def run_agent_flow_subprocess(flow_path: Path) -> dict[str, object]:
    command = [sys.executable, str((ROOT_DIR / "run_e2e_agent.py").resolve()), "--flow", str(flow_path.resolve())]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT_DIR),
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    payload_text = stdout
    json_start = stdout.find("{")
    if json_start >= 0:
        payload_text = stdout[json_start:]
    try:
        payload = json.loads(payload_text) if payload_text else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Agent runner returned non-JSON output.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        ) from exc
    if stderr:
        payload["stderr"] = ((payload.get("stderr") or "") + ("\n" if payload.get("stderr") else "") + stderr).strip()
    payload.setdefault("command", " ".join(command))
    return payload


def run_url_agent_subprocess(url: str, *, headless: bool = False, slow_mo: int = 100) -> dict[str, object]:
    command = [sys.executable, str((ROOT_DIR / "run_url_agent.py").resolve()), "--url", url, "--slow-mo", str(slow_mo)]
    if headless:
        command.append("--headless")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT_DIR),
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    payload_text = stdout
    json_start = stdout.find("{")
    if json_start >= 0:
        payload_text = stdout[json_start:]
    try:
        payload = json.loads(payload_text) if payload_text else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"URL agent returned non-JSON output.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        ) from exc
    if stderr:
        payload["stderr"] = ((payload.get("stderr") or "") + ("\n" if payload.get("stderr") else "") + stderr).strip()
    if result.returncode != 0:
        payload.setdefault("status", "Fail")
        payload.setdefault("suite_name", "URL Agent")
        payload.setdefault("module_name", url)
        payload.setdefault("passed", 0)
        payload.setdefault("failed", 1)
        payload.setdefault("total", 1)
        payload.setdefault("extra", {})
        payload["extra"].setdefault("human_required", ["URL agent failed before producing a complete report."])
        payload["extra"].setdefault("findings", [])
        payload["extra"].setdefault("test_cases", [])
        payload["extra"].setdefault("case_counts", {"Pass": 0, "Fail": 1, "Needs Review": 0})
        payload["extra"].setdefault("url", url)
    else:
        payload.setdefault("status", "Pass")
    payload.setdefault("command", " ".join(command))
    return payload


def get_step_template(action: str) -> dict[str, object]:
    templates = {
        "wait_for": {"name": "Wait for element", "action": "wait_for", "selector": "h1"},
        "click": {"name": "Click element", "action": "click", "selector": "button"},
        "fill": {"name": "Fill input", "action": "fill", "selector": "input", "value": ""},
        "press": {"name": "Press key", "action": "press", "selector": "input", "key": "Enter"},
        "assert_text": {"name": "Assert text", "action": "assert_text", "selector": "body", "expects_text": ""},
        "assert_url": {"name": "Assert URL", "action": "assert_url", "expects_url": "**"},
        "screenshot": {"name": "Capture page", "action": "screenshot", "screenshot_name": "step.png"},
        "goto": {"name": "Open page", "action": "goto", "url": "/"},
    }
    return dict(templates.get(action, {"name": "New step", "action": action}))


def default_step_list() -> list[dict[str, object]]:
    return [
        {"name": "Wait for page heading", "action": "wait_for", "selector": "h1"},
        {"name": "Capture page", "action": "screenshot", "screenshot_name": "journey_home.png"},
    ]


modules = get_modules()
module_options = {module.id: module for module in modules}
selected_module = module_options.get("enq")
saved_settings = load_ui_settings()
for env_key, env_value in saved_settings.items():
    if env_value and not os.getenv(env_key):
        os.environ[env_key] = env_value
ai_status = get_ai_status()

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
          <h3>Daily QA Control</h3>
          <p>Run modules, filter execution history, and manage workspace settings from one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='sidebar-section-title'>Module Launcher</div>", unsafe_allow_html=True)
    with st.container():
        selected_module_id = st.selectbox(
            "Module",
            list(module_options.keys()) or ["pbr", "enq"],
            format_func=lambda key: module_options.get(key).label if key in module_options else key.upper(),
        )
        selected_module = module_options.get(selected_module_id, selected_module)
        module_sheet_name = selected_module.sheet_name if selected_module else DEFAULT_SHEET_NAME
        module_default_tab = selected_module.default_tab if selected_module else "PBR"
        tab_names = get_tab_names(module_sheet_name, module_default_tab) if modules else []
        run_clicked = st.button("Run Selected Module", type="primary", use_container_width=True)
        st.caption(f"Active sheet: {module_sheet_name}")

    st.divider()
    st.markdown("<div class='sidebar-section-title'>Filters</div>", unsafe_allow_html=True)
    default_tab_index = 0
    if tab_names and selected_module and selected_module.default_tab in tab_names:
        default_tab_index = tab_names.index(selected_module.default_tab)
    selected_tab = st.selectbox(
        "Google Sheet Tab",
        tab_names or [module_default_tab],
        index=default_tab_index if tab_names else 0,
        key=f"sheet_tab_{selected_module_id}",
    )

    records_for_tab = read_sheet_records(module_sheet_name, selected_tab) if selected_tab in tab_names else []
    statuses = sorted({row.get("Status", "") for row in records_for_tab if row.get("Status")})
    browsers = sorted({row.get("Browser", "") for row in records_for_tab if row.get("Browser")})

    with st.expander("Quick Filters", expanded=True):
        status_filter = st.multiselect("Status", statuses, default=statuses)
        browser_filter = st.multiselect("Browser", browsers, default=browsers)
        search_text = st.text_input("Search text", placeholder="Test title, remarks, browser, phone...")

    date_values = [row.get("Date", "") for row in records_for_tab if row.get("Date")]
    parsed_dates = []
    for value in date_values:
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                parsed_dates.append(datetime.strptime(value, fmt).date())
                break
            except ValueError:
                continue
    min_date = min(date_values) if date_values else None
    max_date = max(date_values) if date_values else None

    with st.expander("Date Range", expanded=False):
        st.caption(f"Available: {min_date or '-'} to {max_date or '-'}")
        start_default = min(parsed_dates) if parsed_dates else date.today()
        end_default = max(parsed_dates) if parsed_dates else date.today()
        start_date = st.date_input("Start date", value=start_default)
        end_date = st.date_input("End date", value=end_default)

    st.divider()
    render_settings_panel(saved_settings)

last_run = st.session_state.get("last_run_result")
if last_run:
    st.markdown(
        """
        <div class="latest-run-shell">
          <div class="section-header">Latest Module Run</div>
          <div class="section-subtle">Quick visibility into the most recent launcher result.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    summary_cols = st.columns(4)
    for col, label, value in [
        (summary_cols[0], "Status", last_run["status"]),
        (summary_cols[1], "Suite", last_run["suite_name"]),
        (summary_cols[2], "Module", last_run["module_name"]),
        (summary_cols[3], "Return Code", last_run["extra"].get("return_code")),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                  <div class="small-label">{label}</div>
                  <div style="font-size: 1.1rem; font-weight: 800;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with st.expander("Stdout", expanded=True):
        st.code(last_run.get("stdout") or "", language="text")
    if last_run.get("stderr"):
        with st.expander("Stderr", expanded=True):
            st.code(last_run.get("stderr") or "", language="text")

if run_clicked and selected_module_id in module_options:
    runner = get_runner()
    module = module_options[selected_module_id]
    with st.spinner(f"Running {module.label}..."):
        result = runner.run_module(module.id)
    st.cache_data.clear()
    st.session_state["last_run_result"] = result
    if result["status"] == "Pass":
        st.success(f"{module.label} finished with Pass")
    else:
        st.error(f"{module.label} finished with Fail")

testlink_status = get_testlink_status(saved_settings)

st.markdown(
    f"""
    <div class="hero">
      <h1>Daily QA Automation</h1>
      <p>Run modules, inspect execution data, generate tests from TestLink, and manage AI-assisted workflows from one clean workspace.</p>
      <div class="hero-badges">
        <span class="hero-badge">Active module: {selected_module.label if selected_module else '-'}</span>
        <span class="hero-badge">AI: {ai_status['enabled']}</span>
        <span class="hero-badge">TestLink: {testlink_status['enabled']}</span>
        <span class="hero-badge">Sheet: {module_sheet_name}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="context-strip">
      <strong>Module:</strong> {selected_module.label if selected_module else '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
      <strong>Sheet:</strong> {module_sheet_name} &nbsp;&nbsp;|&nbsp;&nbsp;
      <strong>Tab:</strong> {selected_tab} &nbsp;&nbsp;|&nbsp;&nbsp;
      <strong>AI:</strong> {ai_status['enabled']} &nbsp;&nbsp;|&nbsp;&nbsp;
      <strong>TestLink:</strong> {testlink_status['enabled']} &nbsp;&nbsp;|&nbsp;&nbsp;
      <strong>Diagnostics:</strong> {'Playwright + DevTools' if os.getenv('AUTOMATION_DEVTOOLS_ENABLED', '1').strip().lower() not in {'0', 'false', 'no'} else 'Playwright only'}
      <div class="pill-row" style="margin-top:0.8rem;">
        <span class="pill">Google Sheet: {selected_tab}</span>
        <span class="pill">Search: {search_text or 'All records'}</span>
        <span class="pill">Date window: {start_date.isoformat()} to {end_date.isoformat()}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if selected_tab in tab_names:
    raw_records = read_sheet_records(module_sheet_name, selected_tab)
    logger = get_sheet_logger(module_sheet_name, selected_tab)
    filtered_records = logger.filter_records(
        tab_name=selected_tab,
        status=",".join(status_filter) if status_filter else None,
        browser=",".join(browser_filter) if browser_filter else None,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        search=search_text,
    )
else:
    raw_records = []
    filtered_records = []

total = len(filtered_records)
passed = sum(1 for row in filtered_records if row.get("Status", "").strip().lower() == "pass")
failed = sum(1 for row in filtered_records if row.get("Status", "").strip().lower() == "fail")
pass_rate = round((passed / total) * 100, 1) if total else 0.0
healing_records = [
    row
    for row in read_healing_records(150)
    if not selected_module or row.get("suite_name") == selected_module.suite
]
step_events = [
    row
    for row in read_step_events(150)
    if not selected_module or row.get("suite_name") == selected_module.suite
]

metric_cols = st.columns(4)
for col, label, value, accent in [
    (metric_cols[0], "Total", total, "#0f172a"),
    (metric_cols[1], "Passed", passed, "#16a34a"),
    (metric_cols[2], "Failed", failed, "#dc2626"),
    (metric_cols[3], "Pass Rate", f"{pass_rate}%", "#1d4ed8"),
]:
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="small-label">{label}</div>
              <div style="font-size: 2rem; font-weight: 800; color: {accent}; line-height: 1.1;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Executions", "Downloads", "Test Generator", "Launcher History", "Diagnostics", "E2E Agent"]
)

with tab1:
    st.markdown("### Filtered Execution Data")
    if filtered_records:
        st.dataframe(filtered_records, use_container_width=True, hide_index=True)
    else:
        st.info("No rows matched the selected filters.")

    if filtered_records:
        st.markdown("### Browser Breakdown")
        browser_counts = {}
        for row in filtered_records:
            browser = row.get("Browser", "Unknown") or "Unknown"
            browser_counts.setdefault(browser, {"Pass": 0, "Fail": 0})
            status = row.get("Status", "").strip().lower()
            if status == "pass":
                browser_counts[browser]["Pass"] += 1
            elif status == "fail":
                browser_counts[browser]["Fail"] += 1
        st.bar_chart(
            {
                browser: counts["Pass"] + counts["Fail"]
                for browser, counts in browser_counts.items()
            }
        )

with tab2:
    st.markdown("### Download Center")
    filters = {
        "Tab": selected_tab,
        "Status": ", ".join(status_filter),
        "Browser": ", ".join(browser_filter),
        "Search": search_text,
        "Start Date": start_date.isoformat() if start_date else "",
        "End Date": end_date.isoformat() if end_date else "",
    }
    csv_bytes = build_csv_bytes(filtered_records)
    html_bytes = build_html_report(selected_tab, filtered_records, filters)

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"{selected_tab.lower()}_filtered.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "Download HTML Report",
            data=html_bytes,
            file_name=f"{selected_tab.lower()}_report.html",
            mime="text/html",
            use_container_width=True,
        )

    st.caption("The HTML report is generated from the current filtered sheet view.")

with tab3:
    st.markdown("### TestLink Test Generator")
    st.caption("Fetch manual cases from TestLink and generate Playwright tests directly into the selected module folder.")
    last_generation = st.session_state.get("last_testlink_generation")

    with st.form("testlink_generator_form"):
        gen_col1, gen_col2 = st.columns([1.15, 0.85])
        with gen_col1:
            generator_module_keys = list(module_options.keys()) or ["bmc"]
            generator_module = st.selectbox(
                "Target Module",
                generator_module_keys,
                index=(generator_module_keys.index(selected_module.id) if selected_module else 0),
                format_func=lambda key: module_options.get(key).label if key in module_options else key.upper(),
                key="generator_module",
            )
            generator_default_output = str(default_output_dir_for_module(generator_module))
            generator_output_state_key = f"generator_output_dir_{generator_module}"
            generator_suite_state_key = f"generator_suite_id_{generator_module}"
            generator_suite_id = st.text_input(
                "Suite ID",
                value=st.session_state.get(generator_suite_state_key, ""),
                placeholder="Enter TestLink suite id",
            )
            generator_output_dir = st.text_input(
                "Output Folder",
                value=st.session_state.get(generator_output_state_key, generator_default_output),
                help="Generated tests will be saved here.",
            )
        with gen_col2:
            generator_max_cases = st.number_input(
                "Max Cases",
                min_value=0,
                value=0,
                help="Leave as 0 to generate every test case in the suite.",
            )
            generator_overwrite = st.checkbox("Overwrite Existing Files", value=False)
            generator_submit = st.form_submit_button("Generate Tests", type="primary", use_container_width=True)

    st.session_state[generator_output_state_key] = generator_output_dir
    st.session_state[generator_suite_state_key] = generator_suite_id

    if generator_submit:
        if not generator_suite_id.strip().isdigit():
            st.error("Please enter a valid numeric Suite ID.")
        else:
            try:
                config = TestLinkGeneratorConfig(
                    suite_id=int(generator_suite_id.strip()),
                    module_id=generator_module,
                    output_dir=Path(generator_output_dir).resolve(),
                    testlink_api_key=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_TESTLINK_API_KEY",
                        "TESTLINK_API_KEY",
                    ),
                    testlink_url=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_TESTLINK_URL",
                        "TESTLINK_URL",
                        default="https://testlink.intermesh.net/lib/api/xmlrpc/v1/xmlrpc.php",
                    ),
                    llm_api_key=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_LLM_API_KEY",
                        "LITELLM_API_KEY",
                    ),
                    llm_base_url=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_LLM_BASE_URL",
                        "LITELLM_API_BASE",
                        default="https://imllm.intermesh.net/v1",
                    ),
                    llm_model=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_LLM_MODEL",
                        "LITELLM_MODEL",
                        default="anthropic/claude-sonnet-4-6",
                    ),
                    ca_bundle=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_TESTLINK_CA_BUNDLE",
                        "TESTLINK_CA_BUNDLE",
                        "SSL_CERT_FILE",
                    ),
                    insecure_skip_verify=get_runtime_setting(
                        saved_settings,
                        "AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY",
                        "TESTLINK_INSECURE_SKIP_VERIFY",
                        default="1",
                    ).lower() not in {"0", "false", "no"},
                    overwrite=generator_overwrite,
                    max_cases=int(generator_max_cases) or None,
                )
                with st.spinner("Generating tests from TestLink..."):
                    results = TestLinkCaseGenerator(config).run()
            except Exception as exc:
                st.error(f"Could not generate tests: {exc}")
            else:
                summary = {
                    "module": generator_module,
                    "suite_id": int(generator_suite_id.strip()),
                    "output_dir": str(Path(generator_output_dir).resolve()),
                    "generated": sum(1 for item in results if item.status == "generated"),
                    "skipped": sum(1 for item in results if item.status == "skipped"),
                    "failed": sum(1 for item in results if item.status == "failed"),
                    "results": [
                        {
                            "title": item.title,
                            "status": item.status,
                            "detail": item.detail,
                            "output_path": str(item.output_path) if item.output_path else "",
                        }
                        for item in results
                    ],
                }
                st.session_state["last_testlink_generation"] = summary
                last_generation = summary
                if summary["failed"] == 0:
                    st.success(
                        f"Generated {summary['generated']} test file(s) for suite {summary['suite_id']}."
                    )
                else:
                    st.warning(
                        f"Generated {summary['generated']} file(s) with {summary['failed']} failure(s). Review the results below."
                    )

    if last_generation:
        summary_cols = st.columns(5)
        for col, label, value in [
            (summary_cols[0], "Module", last_generation.get("module")),
            (summary_cols[1], "Suite ID", last_generation.get("suite_id")),
            (summary_cols[2], "Generated", last_generation.get("generated")),
            (summary_cols[3], "Skipped", last_generation.get("skipped")),
            (summary_cols[4], "Failed", last_generation.get("failed")),
        ]:
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="small-label">{label}</div>
                      <div style="font-size: 1.1rem; font-weight: 800;">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.caption(f"Output folder: {last_generation.get('output_dir')}")
        result_rows = last_generation.get("results") or []
        if result_rows:
            st.dataframe(result_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No cases were returned for the selected suite.")

with tab4:
    st.markdown("### Launcher Runs")
    runs = get_store().list_runs(limit=20)
    if runs:
        st.dataframe(
            [
                {
                    "suite": row["suite_name"],
                    "module": row["module_name"],
                    "status": row["status"],
                    "passed": row["passed"],
                    "failed": row["failed"],
                    "total": row["total"],
                    "started": row["started_at"],
                    "finished": row["finished_at"],
                    "report": row["report_path"],
                }
                for row in runs
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No launcher history yet.")

with tab5:
    diag1, diag2 = st.tabs(["Healing History", "Step Failures"])

    with diag1:
        st.markdown("### Locator Healing History")
        st.caption(f"Filtered to suite: {selected_module.suite if selected_module else '-'}")
        if healing_records:
            healing_view = [
                {
                    "outcome": healing_outcome_label(row),
                    "provider": diagnostics_provider_label(row),
                    "locator": row.get("locator_name"),
                    "previous": row.get("previous_selector"),
                    "chosen": row.get("chosen_selector"),
                    "strategy": row.get("strategy"),
                    "module": row.get("module_name"),
                    "test": row.get("test_name"),
                    "updated": row.get("created_at"),
                }
                for row in healing_records
            ]
            st.dataframe(healing_view, use_container_width=True, hide_index=True)
            latest = healing_records[0]
            with st.expander("Latest Healing Detail", expanded=False):
                st.caption(f"Diagnostics provider: {diagnostics_provider_label(latest)}")
                st.json(latest)
                st.code(latest.get("html_snapshot") or "", language="html")
        else:
            st.info("No locator healing history yet.")

    with diag2:
        st.markdown("### Step Failure Screenshots")
        failed_steps = [row for row in step_events if (row.get("status") or "").lower().startswith("fail")]
        if failed_steps:
            latest_failed = failed_steps[0]
            screenshot_path = latest_failed.get("screenshot_path")
            if screenshot_path and Path(screenshot_path).exists():
                st.image(str(Path(screenshot_path).resolve()), caption=f"Screenshot: {Path(screenshot_path).name}", use_container_width=True)
            else:
                st.info("No screenshot file found for the latest failed step.")

            st.dataframe(
                [
                    {
                        "step": row.get("step_name"),
                        "browser": row.get("browser_name"),
                        "status": row.get("status"),
                        "provider": diagnostics_provider_label(row),
                        "remarks": row.get("remarks"),
                        "screenshot": row.get("screenshot_path"),
                        "created": row.get("created_at"),
                    }
                    for row in failed_steps
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No failed step screenshots available for this module.")

with tab6:
    st.markdown(
        """
        <div class="agent-shell">
          <div class="agent-hero">
            <h3>AI URL Agent</h3>
            <p>Paste one URL. The agent opens the page, attempts login with the configured phone and OTP when needed, explores CTA clicks, search, and form submissions, then records pass or fail status for each case.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    last_url_agent_run = st.session_state.get("last_url_agent_run_result")
    last_agent_run = st.session_state.get("last_agent_run_result")
    if "agent_step_list" not in st.session_state:
        st.session_state["agent_step_list"] = default_step_list()

    simple_col1, simple_col2 = st.columns([1.35, 0.85])
    with simple_col1:
        url_agent_input = st.text_input(
            "Target URL",
            value="https://example.com",
            key="url_agent_target_url",
            placeholder="https://www.example.com/page",
        )
    with simple_col2:
        url_agent_headless = st.toggle("Headless", value=False, key="url_agent_headless")
        url_agent_run = st.button("Run URL Agent", type="primary", use_container_width=True)
        recipients_preview = parse_recipients(
            os.getenv(
                "AUTOMATION_SMTP_RECIPIENTS",
                saved_settings.get("AUTOMATION_SMTP_RECIPIENTS", ""),
            )
        )
        if recipients_preview:
            st.caption("Report recipients: " + ", ".join(recipients_preview))
        else:
            st.caption("No email recipients configured yet. Save them from Settings to enable report sending.")

    if url_agent_run:
        if not url_agent_input.strip():
            st.error("Please enter a URL.")
        else:
            try:
                with st.spinner("Assessing page and generating report..."):
                    result = run_url_agent_subprocess(url_agent_input.strip(), headless=url_agent_headless, slow_mo=100)
            except Exception as exc:
                st.error(f"Could not run URL agent: {exc}")
            else:
                st.cache_data.clear()
                st.session_state["last_url_agent_run_result"] = result
                last_url_agent_run = result
                result_status = str(result.get("status", "Fail"))
                if result_status == "Pass":
                    st.success("Page assessment completed.")
                else:
                    st.warning("Page assessment completed with human review recommendations.")

    if last_url_agent_run:
        summary_cols = st.columns(5)
        extra = last_url_agent_run.get("extra") or {}
        case_counts = extra.get("case_counts") or {}
        for col, label, value in [
            (summary_cols[0], "Status", last_url_agent_run.get("status")),
            (summary_cols[1], "Executed", len(extra.get("test_cases") or [])),
            (summary_cols[2], "Passed", case_counts.get("Pass", 0)),
            (summary_cols[3], "Failed", case_counts.get("Fail", 0)),
            (summary_cols[4], "Needs Review", case_counts.get("Needs Review", 0)),
        ]:
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="small-label">{label}</div>
                      <div class="metric-value">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown(
            f"""
            <div class="section-card" style="margin-bottom: 1rem;">
              <div class="small-label">Page</div>
              <div class="metric-value">{short_text((extra.get("page_summary") or {}).get("title") or last_url_agent_run.get("module_name"), 180)}</div>
              <div style="margin-top: 0.6rem; color: #64748b;">{short_text(extra.get("url") or '', 180)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        detail_col1, detail_col2 = st.columns([1.05, 1.15])
        with detail_col1:
            st.markdown("#### Overall Page Assessment")
            findings = extra.get("findings") or []
            if findings:
                for item in findings:
                    st.write(f"- {item}")
            else:
                st.info("No findings captured.")
            screenshot_path = extra.get("screenshot_path")
            if screenshot_path and Path(screenshot_path).exists():
                st.image(str(Path(screenshot_path).resolve()), caption=Path(screenshot_path).name, use_container_width=True)
        with detail_col2:
            st.markdown("#### Executed Test Cases")
            test_cases = extra.get("test_cases") or []
            if test_cases:
                st.dataframe(
                    [
                        {
                            "test_case": case.get("title"),
                            "status": case.get("status"),
                            "details": case.get("details"),
                            "evidence": case.get("evidence"),
                        }
                        for case in test_cases
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No test cases executed.")

        st.markdown("#### Human Intervention")
        human_required = extra.get("human_required") or []
        if human_required:
            for item in human_required:
                st.write(f"- {item}")
        else:
            st.success("No immediate human intervention detected.")

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if last_url_agent_run.get("report_path"):
                st.markdown(f"HTML report: [report.html]({Path(last_url_agent_run.get('report_path')).resolve()})")
        with action_col2:
            if st.button("Send Latest URL Report", use_container_width=True, key="send_latest_url_agent_report"):
                try:
                    send_run_report_email(last_url_agent_run, recipients=recipients_preview)
                except Exception as exc:
                    st.error(f"Could not send report email: {exc}")
                else:
                    st.success("URL report email sent.")

        with st.expander("Execution JSON", expanded=False):
            st.json(extra.get("test_cases") or [])

    with st.expander("Advanced Journey Builder", expanded=False):
        st.caption("Use this only when you want a custom scripted journey instead of the URL-only assessment.")
        agent_col1, agent_col2 = st.columns([1.35, 0.85])
        with agent_col1:
            suite_name_input = st.text_input("Suite Name", value="Agentic E2E", key="agent_suite_name")
            module_name_input = st.text_input("Journey Name", value="custom_journey", key="agent_module_name")
            start_url_input = st.text_input("Journey Target URL", value="https://example.com", key="agent_start_url")
            build_mode = st.radio(
                "Journey Editor",
                ["Guided Builder", "Raw JSON"],
                horizontal=True,
                key="agent_editor_mode",
            )

            if build_mode == "Guided Builder":
                builder_cols = st.columns([1.2, 1, 1])
                with builder_cols[0]:
                    new_step_action = st.selectbox(
                        "Add Step Type",
                        ["wait_for", "click", "fill", "press", "assert_text", "assert_url", "screenshot", "goto"],
                        key="new_step_action",
                    )
                with builder_cols[1]:
                    if st.button("Add Step", use_container_width=True, key="add_agent_step"):
                        st.session_state["agent_step_list"] = st.session_state["agent_step_list"] + [get_step_template(new_step_action)]
                with builder_cols[2]:
                    if st.button("Reset Steps", use_container_width=True, key="reset_agent_steps"):
                        st.session_state["agent_step_list"] = default_step_list()

                rendered_steps: list[dict[str, object]] = []
                for index, step in enumerate(st.session_state["agent_step_list"], start=1):
                    with st.expander(f"Step {index}: {step.get('name', 'Unnamed Step')}", expanded=index <= 2):
                        step_name = st.text_input("Step Name", value=str(step.get("name", "")), key=f"step_name_{index}")
                        action = st.selectbox(
                            "Action",
                            ["goto", "wait_for", "click", "fill", "press", "assert_text", "assert_url", "screenshot"],
                            index=["goto", "wait_for", "click", "fill", "press", "assert_text", "assert_url", "screenshot"].index(str(step.get("action", "wait_for"))),
                            key=f"step_action_{index}",
                        )
                        selector = st.text_input("Selector", value=str(step.get("selector", "")), key=f"step_selector_{index}")
                        step_payload: dict[str, object] = {"name": step_name, "action": action}
                        if selector:
                            step_payload["selector"] = selector
                        if action == "goto":
                            step_payload["url"] = st.text_input("URL", value=str(step.get("url", "/")), key=f"step_url_{index}")
                        if action == "fill":
                            step_payload["value"] = st.text_input("Value", value=str(step.get("value", "")), key=f"step_value_{index}")
                        if action == "press":
                            step_payload["key"] = st.text_input("Key", value=str(step.get("key", "Enter")), key=f"step_key_{index}")
                        if action == "assert_text":
                            step_payload["expects_text"] = st.text_input("Expected Text", value=str(step.get("expects_text", "")), key=f"step_expect_text_{index}")
                        if action == "assert_url":
                            step_payload["expects_url"] = st.text_input("Expected URL Pattern", value=str(step.get("expects_url", "**")), key=f"step_expect_url_{index}")
                        if action == "screenshot":
                            step_payload["screenshot_name"] = st.text_input("Screenshot Name", value=str(step.get("screenshot_name", f"step_{index}.png")), key=f"step_screenshot_{index}")
                        timeout_value = st.number_input("Timeout (ms)", min_value=0, max_value=60000, value=int(step.get("timeout_ms", 10000) or 10000), step=500, key=f"step_timeout_{index}")
                        if timeout_value:
                            step_payload["timeout_ms"] = int(timeout_value)
                        rendered_steps.append(step_payload)
                        if st.button("Remove Step", key=f"remove_step_{index}"):
                            st.session_state["agent_step_list"] = [
                                item for item_idx, item in enumerate(st.session_state["agent_step_list"], start=1) if item_idx != index
                            ]
                            st.rerun()
                st.session_state["agent_step_list"] = rendered_steps
                steps_text_input = json.dumps(rendered_steps, indent=2)
                st.text_area("Generated Journey JSON", value=steps_text_input, height=220, disabled=True, key="agent_steps_preview")
            else:
                steps_text_input = st.text_area(
                    "Journey Steps JSON",
                    value=st.session_state.get("agent_steps_text", DEFAULT_AGENT_STEPS),
                    height=420,
                    key="agent_steps_text",
                )
                try:
                    parsed_raw_steps = json.loads(steps_text_input)
                    if isinstance(parsed_raw_steps, list):
                        st.session_state["agent_step_list"] = parsed_raw_steps
                except Exception:
                    pass

        with agent_col2:
            browser_labels = st.multiselect(
                "Browsers",
                ["Chromium", "Firefox"],
                default=["Chromium"],
                key="agent_browsers",
            )
            headless_input = st.toggle("Headless", value=False, key="agent_headless")
            slow_mo_input = st.slider("Slow Motion (ms)", min_value=0, max_value=1000, value=120, step=20, key="agent_slow_mo")
            run_agent_clicked = st.button("Run Advanced E2E Agent", type="primary", use_container_width=True)

        if run_agent_clicked:
            flow_payload, flow_error = build_agent_flow_payload(
                suite_name=suite_name_input,
                module_name=module_name_input,
                start_url=start_url_input,
                browsers=parse_browser_selection(browser_labels),
                headless=headless_input,
                slow_mo=slow_mo_input,
                steps_text=steps_text_input,
            )
            if flow_error:
                st.error(flow_error)
            else:
                flow_path = save_agent_flow(flow_payload, module_name_input)
                try:
                    with st.spinner(f"Running journey '{module_name_input}'..."):
                        result = run_agent_flow_subprocess(flow_path)
                except Exception as exc:
                    st.error(f"Could not run E2E agent: {exc}")
                else:
                    st.cache_data.clear()
                    st.session_state["last_agent_run_result"] = result
                    last_agent_run = result
                    if result["status"] == "Pass":
                        st.success(f"Journey '{module_name_input}' finished with Pass")
                    else:
                        st.error(f"Journey '{module_name_input}' finished with Fail")

    if last_agent_run:
        summary_cols = st.columns(4)
        for col, label, value in [
            (summary_cols[0], "Status", last_agent_run.get("status")),
            (summary_cols[1], "Suite", last_agent_run.get("suite_name")),
            (summary_cols[2], "Journey", last_agent_run.get("module_name")),
            (summary_cols[3], "Report", Path(last_agent_run.get("report_path", "")).name if last_agent_run.get("report_path") else "-"),
        ]:
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="small-label">{label}</div>
                      <div style="font-size: 1.1rem; font-weight: 800;">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        report_path = last_agent_run.get("report_path")
        flow_source_path = (last_agent_run.get("extra") or {}).get("source_path")
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.markdown("#### Run Artifacts")
            if flow_source_path:
                st.markdown(f"Flow file: [flow.json]({Path(flow_source_path).resolve()})")
            if report_path:
                st.markdown(f"HTML report: [report.html]({Path(report_path).resolve()})")
            st.json(
                {
                    "started_at": last_agent_run.get("started_at"),
                    "finished_at": last_agent_run.get("finished_at"),
                    "passed": last_agent_run.get("passed"),
                    "failed": last_agent_run.get("failed"),
                    "total": last_agent_run.get("total"),
                    "browser_breakdown": last_agent_run.get("browser_breakdown"),
                }
            )
        with detail_col2:
            st.markdown("#### Actions")
            if st.button("Send Latest Agent Report", use_container_width=True, key="send_latest_agent_report"):
                try:
                    send_run_report_email(last_agent_run, recipients=recipients_preview)
                except Exception as exc:
                    st.error(f"Could not send report email: {exc}")
                else:
                    st.success("Agent report email sent.")

        if last_agent_run.get("stdout"):
            with st.expander("Agent Stdout", expanded=False):
                st.code(last_agent_run.get("stdout") or "", language="text")
        if last_agent_run.get("stderr"):
            with st.expander("Agent Stderr", expanded=False):
                st.code(last_agent_run.get("stderr") or "", language="text")
