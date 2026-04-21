from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = Path(os.getenv("AUTOMATION_ARTIFACTS_DIR", ROOT_DIR / "artifacts"))
REPORTS_DIR = ARTIFACTS_DIR / "reports"
RUNS_DIR = ARTIFACTS_DIR / "runs"
SESSION_DIR = ARTIFACTS_DIR / "sessions"
DB_PATH = ARTIFACTS_DIR / "execution.db"
MODULE_REGISTRY_PATH = ROOT_DIR / "automation_modules.json"

DEFAULT_SHEET_NAME = os.getenv("AUTOMATION_SHEET_NAME", "Buyer Automation")
DEFAULT_SHEET_URL = os.getenv("AUTOMATION_SHEET_URL", "")

LLM_API_KEY = os.getenv("AUTOMATION_LLM_API_KEY", "") or os.getenv("LITELLM_API_KEY", "")
LLM_BASE_URL = os.getenv("AUTOMATION_LLM_BASE_URL", "") or os.getenv(
    "LITELLM_API_BASE",
    "https://imllm.intermesh.net/v1",
)
LLM_MODEL = os.getenv("AUTOMATION_LLM_MODEL", "") or os.getenv("LITELLM_MODEL", "anthropic/claude-sonnet-4-6")
DEVTOOLS_ENABLED = os.getenv("AUTOMATION_DEVTOOLS_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
DIAGNOSTICS_HTML_LIMIT = int(os.getenv("AUTOMATION_DIAGNOSTICS_HTML_LIMIT", "4000"))
DEFAULT_LOGIN_PHONE = os.getenv("AUTOMATION_DEFAULT_LOGIN_PHONE", "9643193481")
DEFAULT_LOGIN_OTP = os.getenv("AUTOMATION_DEFAULT_LOGIN_OTP", "1956")
URL_AGENT_MAX_LINKS = int(os.getenv("AUTOMATION_URL_AGENT_MAX_LINKS", "3"))
URL_AGENT_MAX_FORMS = int(os.getenv("AUTOMATION_URL_AGENT_MAX_FORMS", "3"))
URL_AGENT_MAX_CTAS = int(os.getenv("AUTOMATION_URL_AGENT_MAX_CTAS", "3"))

TESTLINK_API_KEY = os.getenv("AUTOMATION_TESTLINK_API_KEY", "") or os.getenv("TESTLINK_API_KEY", "")
TESTLINK_URL = os.getenv("AUTOMATION_TESTLINK_URL", "") or os.getenv(
    "TESTLINK_URL",
    "https://testlink.intermesh.net/lib/api/xmlrpc/v1/xmlrpc.php",
)
TESTLINK_CA_BUNDLE = (
    os.getenv("AUTOMATION_TESTLINK_CA_BUNDLE", "")
    or os.getenv("TESTLINK_CA_BUNDLE", "")
    or os.getenv("SSL_CERT_FILE", "")
)
TESTLINK_INSECURE_SKIP_VERIFY = (
    os.getenv("AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY", "")
    or os.getenv("TESTLINK_INSECURE_SKIP_VERIFY", "1")
).strip().lower() not in {
    "0",
    "false",
    "no",
}

SMTP_HOST = os.getenv("AUTOMATION_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("AUTOMATION_SMTP_PORT", "587"))
SMTP_USER = os.getenv("AUTOMATION_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("AUTOMATION_SMTP_PASSWORD", "")
SMTP_RECIPIENTS = [
    email.strip()
    for email in os.getenv(
        "AUTOMATION_SMTP_RECIPIENTS",
        "bikram.saha@indiamart.com"
    ).split(",")
    if email.strip()
]

for path in (ARTIFACTS_DIR, REPORTS_DIR, RUNS_DIR, SESSION_DIR):
    path.mkdir(parents=True, exist_ok=True)
