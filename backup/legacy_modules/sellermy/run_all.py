from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_TO_RUN = [
    "sellerlogin.py",
    "dashboard.py",
    "profile.py",
    "newproducts.py",
    "photo-doc.py",
    "settings.py",
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    overall_exit_code = 0
    first_start_time: datetime | None = None
    last_end_time: datetime | None = None

    for script_name in SCRIPTS_TO_RUN:
        script_path = os.path.join(BASE_DIR, script_name)
        start_now = datetime.now()
        if first_start_time is None:
            first_start_time = start_now

        print(f"\n=== Running {script_path} at {start_now.strftime('%H:%M:%S')} ===")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            cwd=BASE_DIR,
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"Error in {script_name}:\n{result.stderr}")

        if result.returncode != 0:
            overall_exit_code = 1

        last_end_time = datetime.now()

    if first_start_time and last_end_time:
        print(f"\nRun window: {first_start_time.isoformat(timespec='seconds')} -> {last_end_time.isoformat(timespec='seconds')}")

    return overall_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
