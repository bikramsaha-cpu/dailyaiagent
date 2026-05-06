from __future__ import annotations

import os
import subprocess
import sys
import ast
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from core.module_registry import get_module, load_modules
from core.reporting import write_html_report
from core.store import ExecutionStore, RunSummary
from core.workspace_settings import load_workspace_settings


class ModuleRunner:
    def __init__(self, store: ExecutionStore | None = None):
        self.store = store or ExecutionStore()

    def run_module(self, module_id: str, selected_tests: list[str] | None = None) -> dict[str, Any]:
        module = get_module(module_id)
        started_at = datetime.now().isoformat(timespec="seconds")
        env = {**os.environ, "PYTHONUTF8": "1"}
        for key, value in load_workspace_settings().items():
            if key.startswith("AUTOMATION_") and value and not env.get(key):
                env[key] = value
        root_dir = str(module.runner_path.parents[1])
        env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
        if selected_tests:
            result = self._run_selected_tests(module, selected_tests, env=env)
            command = result.pop("command")
        else:
            command = [sys.executable, str(module.runner_path)]
            subprocess_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                cwd=str(module.runner_path.parent),
            )
            result = {
                "returncode": subprocess_result.returncode,
                "stdout": subprocess_result.stdout,
                "stderr": subprocess_result.stderr,
                "passed": 1 if subprocess_result.returncode == 0 else 0,
                "failed": 0 if subprocess_result.returncode == 0 else 1,
                "total": 1,
            }
        finished_at = datetime.now().isoformat(timespec="seconds")
        status = "Pass" if result["returncode"] == 0 else "Fail"
        summary = RunSummary(
            suite_name=module.suite,
            module_name=module.label,
            started_at=started_at,
            finished_at=finished_at,
            passed=int(result["passed"]),
            failed=int(result["failed"]),
            total=int(result["total"]),
            status=status,
            command=" ".join(command),
            stdout=result["stdout"],
            stderr=result["stderr"],
            extra={
                "runner_path": str(module.runner_path),
                "return_code": result["returncode"],
                "selected_tests": selected_tests or [],
            },
        )
        summary_dict = asdict(summary)
        summary.report_path = str(write_html_report(summary_dict))
        run_id = self.store.record_run(summary)
        payload = asdict(summary)
        payload["id"] = run_id
        return payload

    def list_module_tests(self, module_id: str) -> list[dict[str, str]]:
        module = get_module(module_id)
        module_dir = module.module_dir
        tests: list[dict[str, str]] = []
        paths = self._declared_runner_scripts(module.runner_path, module_dir)
        if not paths:
            paths = self._discover_test_scripts(module_dir)

        for path in paths:
            relative_path = path.relative_to(module_dir).as_posix()
            tests.append(
                {
                    "id": relative_path,
                    "label": self._test_label(path),
                    "path": relative_path,
                    "group": path.relative_to(module_dir).parts[0] if len(path.relative_to(module_dir).parts) > 1 else "root",
                }
            )
        return tests

    @staticmethod
    def _declared_runner_scripts(runner_path: Path, module_dir: Path) -> list[Path]:
        try:
            tree = ast.parse(runner_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            return []

        paths: list[Path] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if not target_names.intersection({"scripts_to_run", "SCRIPTS_TO_RUN"}):
                continue
            for item in ModuleRunner._iter_script_declarations(node.value):
                candidate = (module_dir / item).resolve()
                if (
                    candidate.exists()
                    and candidate.suffix == ".py"
                    and candidate.name not in ModuleRunner._bootstrap_script_names()
                ):
                    paths.append(candidate)

        return ModuleRunner._unique_paths(paths)

    @staticmethod
    def _iter_script_declarations(node: ast.AST) -> list[Path]:
        if not isinstance(node, (ast.List, ast.Tuple)):
            return []

        paths: list[Path] = []
        for item in node.elts:
            path_node = item
            tab_node: ast.AST | None = None
            if isinstance(item, ast.Tuple) and item.elts:
                path_node = item.elts[0]
                tab_node = item.elts[1] if len(item.elts) > 1 else None
            if isinstance(tab_node, ast.Constant) and tab_node.value is None:
                continue
            path = ModuleRunner._literal_path(path_node)
            if path:
                paths.append(path)
        return paths

    @staticmethod
    def _literal_path(node: ast.AST) -> Path | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return Path(node.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            parts = []
            for arg in node.args:
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    return None
                parts.append(arg.value)
            return Path(*parts) if parts else None
        return None

    @staticmethod
    def _discover_test_scripts(module_dir: Path) -> list[Path]:
        preferred_roots = [
            "testscript",
            "lms_test_scripts",
            "generated_from_testlink",
            "FullyLoggedin",
            "Identified",
            "fullyloggedin",
        ]
        roots = [module_dir / name for name in preferred_roots if (module_dir / name).exists()]
        roots = roots or [module_dir]

        paths: list[Path] = []
        for root in roots:
            test_paths = sorted(root.rglob("test_*.py"))
            paths.extend(test_paths)
            if not test_paths:
                paths.extend(
                    path
                    for path in sorted(root.rglob("*.py"))
                    if ModuleRunner._looks_like_runnable_test(path)
                )
        return ModuleRunner._unique_paths(paths)

    @staticmethod
    def _looks_like_runnable_test(path: Path) -> bool:
        ignored_names = {
            "__init__.py",
            "conftest.py",
            "google_logger.py",
            "logger_instance.py",
            "mailer.py",
            "run_all.py",
            *ModuleRunner._bootstrap_script_names(),
        }
        return path.name not in ignored_names and "__pycache__" not in path.parts

    @staticmethod
    def _bootstrap_script_names() -> set[str]:
        return {"buyer_login.py", "seller_login.py", "login.py", "sellerlogin.py"}

    @staticmethod
    def _unique_paths(paths: list[Path]) -> list[Path]:
        unique: dict[str, Path] = {}
        for path in paths:
            unique[str(path)] = path
        return sorted(unique.values(), key=lambda path: str(path).lower())

    @staticmethod
    def _test_label(path: Path) -> str:
        label = path.stem
        if label.startswith("test_"):
            label = label[5:]
        label = label.replace("_", " ").replace("-", " ").strip()
        return label[:1].upper() + label[1:] if label else path.name

    def _run_selected_tests(self, module, selected_tests: list[str], *, env: dict[str, str]) -> dict[str, Any]:
        module_dir = module.module_dir
        selected_paths = [module_dir / Path(item) for item in selected_tests]
        missing = [path for path in selected_paths if not path.exists()]
        if missing:
            missing_list = ", ".join(path.name for path in missing)
            return {
                "command": [sys.executable, str(module.runner_path), "--selected-tests"],
                "returncode": 1,
                "stdout": "",
                "stderr": f"Selected test file(s) not found: {missing_list}",
                "passed": 0,
                "failed": len(selected_tests),
                "total": len(selected_tests),
            }

        bootstrap = self._bootstrap_script(module_dir, selected_paths)
        commands: list[list[str]] = []
        if bootstrap is not None:
            commands.append([sys.executable, str(bootstrap)])
        commands.extend([[sys.executable, str(path)] for path in selected_paths])

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        passed = 0
        failed = 0
        for command in commands:
            subprocess_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                cwd=str(module_dir),
            )
            header = f"\n=== Running {Path(command[-1]).name} ===\n"
            if subprocess_result.stdout:
                stdout_parts.append(header + subprocess_result.stdout)
            if subprocess_result.stderr:
                stderr_parts.append(header + subprocess_result.stderr)
            if subprocess_result.returncode == 0:
                if bootstrap is None or command[-1] != str(bootstrap):
                    passed += 1
            else:
                if bootstrap is not None and command[-1] == str(bootstrap):
                    stderr_parts.append("Bootstrap/login step failed. Remaining selected tests were not executed.\n")
                    failed = len(selected_paths)
                    return {
                        "command": [sys.executable, str(module.runner_path), "--selected-tests", *selected_tests],
                        "returncode": subprocess_result.returncode,
                        "stdout": "".join(stdout_parts),
                        "stderr": "".join(stderr_parts),
                        "passed": 0,
                        "failed": failed,
                        "total": len(selected_paths),
                    }
                failed += 1

        return {
            "command": [sys.executable, str(module.runner_path), "--selected-tests", *selected_tests],
            "returncode": 0 if failed == 0 else 1,
            "stdout": "".join(stdout_parts),
            "stderr": "".join(stderr_parts),
            "passed": passed,
            "failed": failed,
            "total": len(selected_paths),
        }

    @staticmethod
    def _bootstrap_script(module_dir: Path, selected_paths: list[Path]) -> Path | None:
        names = {path.name for path in selected_paths}
        for bootstrap_name in ("buyer_login.py", "seller_login.py", "login.py", "sellerlogin.py"):
            candidate = module_dir / bootstrap_name
            if candidate.exists() and bootstrap_name not in names and ModuleRunner._session_bootstrap_required(module_dir):
                return candidate
        return None

    @staticmethod
    def _session_bootstrap_required(module_dir: Path) -> bool:
        root_dir = module_dir.parent
        if module_dir.name == "recommendation":
            candidate_files = [
                root_dir / "artifacts" / "sessions" / "enqlogin.json",
                Path("/var/log/web_tester_logs/enqlogin.json"),
            ]
            return not any(
                candidate.exists() and candidate.stat().st_size > 2
                for candidate in candidate_files
            )

        session_dir = root_dir / "artifacts" / "sessions" / module_dir.name
        candidate_files = [
            module_dir / "auth.json",
            module_dir / f"{module_dir.name}login.json",
        ]
        if session_dir.exists():
            candidate_files.extend(sorted(session_dir.glob("*.json")))

        for candidate in candidate_files:
            try:
                if candidate.exists() and candidate.stat().st_size > 2:
                    return False
            except OSError:
                continue
        return True

    def run_all(self, module_ids: list[str] | None = None) -> list[dict[str, Any]]:
        module_ids = module_ids or [module.id for module in load_modules()]
        return [self.run_module(module_id) for module_id in module_ids]
