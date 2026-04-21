from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any

from core.module_registry import get_module, load_modules
from core.reporting import write_html_report
from core.store import ExecutionStore, RunSummary


class ModuleRunner:
    def __init__(self, store: ExecutionStore | None = None):
        self.store = store or ExecutionStore()

    def run_module(self, module_id: str) -> dict[str, Any]:
        module = get_module(module_id)
        started_at = datetime.now().isoformat(timespec="seconds")
        command = [sys.executable, str(module.runner_path)]
        env = {**os.environ, "PYTHONUTF8": "1"}
        root_dir = str(module.runner_path.parents[1])
        env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=str(module.runner_path.parent),
        )
        finished_at = datetime.now().isoformat(timespec="seconds")
        status = "Pass" if result.returncode == 0 else "Fail"
        summary = RunSummary(
            suite_name=module.suite,
            module_name=module.label,
            started_at=started_at,
            finished_at=finished_at,
            passed=1 if status == "Pass" else 0,
            failed=0 if status == "Pass" else 1,
            total=1,
            status=status,
            command=" ".join(command),
            stdout=result.stdout,
            stderr=result.stderr,
            extra={"runner_path": str(module.runner_path), "return_code": result.returncode},
        )
        summary_dict = asdict(summary)
        summary.report_path = str(write_html_report(summary_dict))
        run_id = self.store.record_run(summary)
        payload = asdict(summary)
        payload["id"] = run_id
        return payload

    def run_all(self, module_ids: list[str] | None = None) -> list[dict[str, Any]]:
        module_ids = module_ids or [module.id for module in load_modules()]
        return [self.run_module(module_id) for module_id in module_ids]
