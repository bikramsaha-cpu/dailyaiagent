from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from core.settings import SESSION_DIR


ROOT_DIR = Path(__file__).resolve().parents[3]
BMC_LOGIN_RUNNER = ROOT_DIR / "backup" / "legacy_modules" / "bmc_legacy" / "buyer_login.py"
BMC_SESSION_DIR = SESSION_DIR / "bmc"
BMC_SESSION_FILE = BMC_SESSION_DIR / "bmclogin.json"
PBR_SESSION_FILE = SESSION_DIR / "pbrlogin.json"
LEGACY_PBR_SESSION_FILE = Path("/var/log/web_tester_logs/pbrlogin.json")


def login_and_save_session() -> int:
    if not BMC_LOGIN_RUNNER.exists():
        print(f"BMC login runner not found: {BMC_LOGIN_RUNNER}")
        return 1

    env = {**os.environ, "PYTHONUTF8": "1", "AUTOMATION_SESSION_DIR": str(BMC_SESSION_DIR)}
    env["PYTHONPATH"] = str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(BMC_LOGIN_RUNNER)],
        cwd=str(BMC_LOGIN_RUNNER.parent),
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        return result.returncode
    if not BMC_SESSION_FILE.exists():
        print(f"BMC session was not created: {BMC_SESSION_FILE}")
        return 1

    PBR_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BMC_SESSION_FILE, PBR_SESSION_FILE)
    try:
        LEGACY_PBR_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BMC_SESSION_FILE, LEGACY_PBR_SESSION_FILE)
    except OSError as exc:
        print(f"Could not copy legacy PBR session file: {exc}")
    print(f"PBR now uses BMC auth session: {BMC_SESSION_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(login_and_save_session())
