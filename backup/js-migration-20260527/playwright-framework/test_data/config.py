from __future__ import annotations

import os
from pathlib import Path

from core.settings import DEFAULT_LOGIN_OTP, DEFAULT_LOGIN_PHONE, SESSION_DIR


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


HEADLESS = env_bool("AUTOMATION_HEADLESS", True)
SLOW_MO = env_int("AUTOMATION_SLOW_MO", 0)
DEFAULT_BROWSERS = env_list("AUTOMATION_BROWSERS", ["chromium", "firefox"])

ENQ_SHEET_NAME = os.getenv("AUTOMATION_ENQ_SHEET_NAME", "Buyer Automation")
ENQ_SHEET_TAB = os.getenv("AUTOMATION_ENQ_SHEET_TAB", "ENQ")
ENQ_SHEET_URL = os.getenv(
    "AUTOMATION_ENQ_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1t_kEjtyZQ_xcOqJ3v5_apcyCEmi8V6wi5w1KjXNEyqg/edit?gid=0#gid=0",
)
ENQ_MOBILE_NUMBER = os.getenv("AUTOMATION_ENQ_MOBILE_NUMBER", DEFAULT_LOGIN_PHONE)
ENQ_LOGIN_OTP = os.getenv("AUTOMATION_ENQ_LOGIN_OTP", DEFAULT_LOGIN_OTP)
BMC_LOGIN_PHONE = os.getenv("AUTOMATION_BMC_LOGIN_PHONE", DEFAULT_LOGIN_PHONE)
BMC_LOGIN_OTP = os.getenv("AUTOMATION_BMC_LOGIN_OTP", DEFAULT_LOGIN_OTP)
BMC_SESSION_FILE = Path(
    os.getenv("AUTOMATION_BMC_SESSION_FILE", str(SESSION_DIR / "bmc" / "bmclogin.json"))
)
AUTH_SESSION_FILE = Path(
    os.getenv("AUTOMATION_AUTH_SESSION_FILE", str(BMC_SESSION_FILE))
)
ENQ_SESSION_FILE = AUTH_SESSION_FILE

DIR_BASE_URL = os.getenv("AUTOMATION_DIR_BASE_URL", "https://dir.indiamart.com")
ENQ_SEARCH_TERM = os.getenv("AUTOMATION_ENQ_SEARCH_TERM", "hat")
ENQ_ALL_INDIA_SEARCH_TERM = os.getenv("AUTOMATION_ENQ_ALL_INDIA_SEARCH_TERM", "headphones")
ENQ_IMPCAT_URL = os.getenv(
    "AUTOMATION_ENQ_IMPCAT_URL",
    "https://dir.indiamart.com/impcat/denim-clothing.html",
)
ENQ_PDP_URL = os.getenv(
    "AUTOMATION_ENQ_PDP_URL",
    "https://www.indiamart.com/proddetail/oppo-mobile-phones-2851972054933.html?pos=1&kwd=oppo%20mobile%20phone&tags=rk:C|plc:1|dt:0|db:01|prc:1|dtp:p||sv:VGP|rsf:gd|ri:VGP_C_0_P-|-res:RC3|ktp:N0|stype:attr=1-br|mtp:Brn|wc:3|lcf:3|cq:hyderabad|qr_nm:gl-gd|cs:17525|com-cf:nl|ptrs:na|mc:184317|cat:750|qry_typ:P|lang:en|rtn:5-0-1-2-1-1-0|tyr:1|qrd:250819|mrd:250812|prdt:250820|pfen:1|gli:G0I0|v=4|crs=city-landing",
)
ENQ_COMPANY_URL = os.getenv(
    "AUTOMATION_ENQ_COMPANY_URL",
    "https://www.indiamart.com/raghavendraagency-hyderabad/?pid=2851972054933&c_id=750&mid=184317&pn=Oppo%20Mobile%20Phones",
)
