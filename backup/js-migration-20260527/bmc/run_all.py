from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LEGACY_RUNNER = ROOT_DIR / "backup" / "legacy_modules" / "bmc_legacy" / "run_all.py"


def main() -> int:
    if not LEGACY_RUNNER.exists():
        print(f"Legacy BMC runner not found: {LEGACY_RUNNER}")
        return 1

    env = {**os.environ, "PYTHONUTF8": "1"}
    env["PYTHONPATH"] = str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(LEGACY_RUNNER), *sys.argv[1:]],
        cwd=str(LEGACY_RUNNER.parent),
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
