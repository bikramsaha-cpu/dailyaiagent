from __future__ import annotations

import os
from pathlib import Path

from core.workspace_settings import load_workspace_settings


ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = Path(os.getenv("AUTOMATION_ARTIFACTS_DIR", ROOT_DIR / "artifacts"))
REPORTS_DIR = ARTIFACTS_DIR / "reports"
RUNS_DIR = ARTIFACTS_DIR / "runs"
SESSION_DIR = ARTIFACTS_DIR / "sessions"
DB_PATH = ARTIFACTS_DIR / "execution.db"
MODULE_REGISTRY_PATH = ROOT_DIR / "automation_modules.json"

DEFAULT_SHEET_NAME = os.getenv("AUTOMATION_SHEET_NAME", "Buyer Automation")
DEFAULT_SHEET_URL = os.getenv("AUTOMATION_SHEET_URL", "")

_WORKSPACE_SETTINGS = load_workspace_settings()


def _setting(primary_key: str, *fallback_keys: str, default: str = "") -> str:
    for key in (primary_key, *fallback_keys):
        value = os.getenv(key, "").strip()
        if value:
            return value
    for key in (primary_key, *fallback_keys):
        value = str(_WORKSPACE_SETTINGS.get(key, "")).strip()
        if value:
            return value
    return default


LLM_API_KEY = _setting("AUTOMATION_LLM_API_KEY", "LITELLM_API_KEY")
LLM_BASE_URL = _setting(
    "AUTOMATION_LLM_BASE_URL",
    "LITELLM_API_BASE",
    default="https://imllm.intermesh.net/v1",
)
LLM_MODEL = _setting(
    "AUTOMATION_LLM_MODEL",
    "LITELLM_MODEL",
    default="anthropic/claude-sonnet-4-6",
)
DEVTOOLS_ENABLED = os.getenv("AUTOMATION_DEVTOOLS_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
DIAGNOSTICS_HTML_LIMIT = int(os.getenv("AUTOMATION_DIAGNOSTICS_HTML_LIMIT", "4000"))
DEFAULT_LOGIN_PHONE = _setting("AUTOMATION_DEFAULT_LOGIN_PHONE", default="9643193481")
DEFAULT_LOGIN_OTP = _setting("AUTOMATION_DEFAULT_LOGIN_OTP", default="1956")
URL_AGENT_MAX_LINKS = int(os.getenv("AUTOMATION_URL_AGENT_MAX_LINKS", "3"))
URL_AGENT_MAX_FORMS = int(os.getenv("AUTOMATION_URL_AGENT_MAX_FORMS", "3"))
URL_AGENT_MAX_CTAS = int(os.getenv("AUTOMATION_URL_AGENT_MAX_CTAS", "3"))

TESTLINK_API_KEY = _setting("AUTOMATION_TESTLINK_API_KEY", "TESTLINK_API_KEY")
TESTLINK_URL = _setting(
    "AUTOMATION_TESTLINK_URL",
    "TESTLINK_URL",
    default="https://testlink.intermesh.net/lib/api/xmlrpc/v1/xmlrpc.php",
)
TESTLINK_CA_BUNDLE = _setting(
    "AUTOMATION_TESTLINK_CA_BUNDLE",
    "TESTLINK_CA_BUNDLE",
    "SSL_CERT_FILE",
)
TESTLINK_INSECURE_SKIP_VERIFY = _setting(
    "AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY",
    "TESTLINK_INSECURE_SKIP_VERIFY",
    default="1",
).strip().lower() not in {
    "0",
    "false",
    "no",
}

SMTP_HOST = _setting("AUTOMATION_SMTP_HOST", default="smtp.gmail.com")
SMTP_PORT = int(_setting("AUTOMATION_SMTP_PORT", default="587"))
SMTP_USER = _setting("AUTOMATION_SMTP_USER", default="techalerts@indiamart.com")
SMTP_PASSWORD = _setting("AUTOMATION_SMTP_PASSWORD", default="utoqdasmgzvoklgf")
SMTP_RECIPIENTS = [
    email.strip()
    for email in _setting(
        "AUTOMATION_SMTP_RECIPIENTS",
        default="bikram.saha@indiamart.com"
    ).split(",")
    if email.strip()
]

for path in (ARTIFACTS_DIR, REPORTS_DIR, RUNS_DIR, SESSION_DIR):
    path.mkdir(parents=True, exist_ok=True)
