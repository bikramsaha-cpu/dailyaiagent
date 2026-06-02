from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.settings import ROOT_DIR
from core.workspace_settings import load_workspace_settings


@dataclass
class ManagedExecution:
    id: str
    kind: str
    title: str
    started_at: str
    status: str
    browser_mode: str
    command: list[str]
    cwd: str
    env_overrides: dict[str, str] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    pid: int | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["command"] = " ".join(self.command)
        return payload


class ExecutionTaskManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[str, ManagedExecution] = {}
        self._procs: dict[str, subprocess.Popen[str]] = {}
        self._env_overrides: dict[str, dict[str, str]] = {}

    def start_module(
        self,
        module_id: str,
        *,
        browser_mode: str = "headed",
        selected_tests: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        command = [sys.executable, str((ROOT_DIR / "run_module_task.py").resolve()), "--module-id", module_id]
        for test in selected_tests or []:
            command.extend(["--tests", test])
        if browser_mode == "headed":
            command.append("--headed")
        return self._start_task(
            kind="module",
            title=f"Module: {module_id}",
            command=command,
            payload={"module_id": module_id, "browser_mode": browser_mode, "selected_tests": selected_tests or []},
            browser_mode=browser_mode,
            env_overrides=env_overrides,
        )

    def start_url_agent(
        self,
        url: str,
        *,
        headless: bool = False,
        slow_mo: int = 100,
        visual_guard: bool = True,
    ) -> dict[str, Any]:
        command = [sys.executable, str((ROOT_DIR / "run_url_agent.py").resolve()), "--url", url, "--slow-mo", str(slow_mo)]
        if headless:
            command.append("--headless")
        if visual_guard:
            command.append("--visual-guard")
        return self._start_task(
            kind="url_agent",
            title=f"URL Agent: {url}",
            command=command,
            payload={"url": url, "headless": headless, "slow_mo": slow_mo, "visual_guard": visual_guard},
            browser_mode="headless" if headless else "headed",
        )

    def list_active(self) -> list[dict[str, Any]]:
        with self._lock:
            tasks = [task.as_payload() for task in self._tasks.values() if task.status == "running"]
        return sorted(tasks, key=lambda item: item["started_at"], reverse=True)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.as_payload() if task else None

    def stop_task(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            task = self._tasks.get(task_id)
            proc = self._procs.get(task_id)
        if task is None:
            raise KeyError(f"Unknown execution task: {task_id}")
        if proc is None or task.status != "running":
            return task.as_payload()
        self._terminate_process_tree(proc.pid)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._terminate_process_tree(proc.pid, force=True)
        with self._lock:
            task.status = "stopped"
            task.finished_at = datetime.now().isoformat(timespec="seconds")
            task.error = task.error or "Execution was stopped by the user."
            self._procs.pop(task_id, None)
            return task.as_payload()

    def restart_task(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Unknown execution task: {task_id}")
        if task.status == "running":
            self.stop_task(task_id)
        if task.kind == "module":
            env_overrides = self._env_overrides.get(task_id, {})
            return self.start_module(
                task.payload["module_id"],
                browser_mode=task.payload.get("browser_mode", "headed"),
                selected_tests=list(task.payload.get("selected_tests", [])),
                env_overrides=env_overrides,
            )
        if task.kind == "url_agent":
            return self.start_url_agent(
                task.payload["url"],
                headless=bool(task.payload.get("headless", False)),
                slow_mo=int(task.payload.get("slow_mo", 100)),
                visual_guard=bool(task.payload.get("visual_guard", True)),
            )
        raise KeyError(f"Unsupported task kind: {task.kind}")

    def _start_task(
        self,
        *,
        kind: str,
        title: str,
        command: list[str],
        payload: dict[str, Any],
        browser_mode: str,
        env_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        task_id = uuid.uuid4().hex
        env = {**os.environ, "PYTHONUTF8": "1"}
        workspace_settings = load_workspace_settings()
        for key, value in workspace_settings.items():
            if key.startswith("AUTOMATION_") and value and not env.get(key):
                env[key] = value
        env_overrides = {key: value for key, value in (env_overrides or {}).items() if value}
        env.update(env_overrides)
        proc = subprocess.Popen(
            command,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        task = ManagedExecution(
            id=task_id,
            kind=kind,
            title=title,
            started_at=datetime.now().isoformat(timespec="seconds"),
            status="running",
            browser_mode=browser_mode,
            command=command,
            cwd=str(ROOT_DIR),
            env_overrides=self._masked_env_overrides(env_overrides),
            payload=payload,
            pid=proc.pid,
        )
        with self._lock:
            self._tasks[task_id] = task
            self._procs[task_id] = proc
            if env_overrides:
                self._env_overrides[task_id] = dict(env_overrides)
        watcher = threading.Thread(target=self._watch_task, args=(task_id,), daemon=True)
        watcher.start()
        return task.as_payload()

    def _watch_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            proc = self._procs.get(task_id)
        if task is None or proc is None:
            return
        stdout, stderr = proc.communicate()
        payload = self._parse_payload(stdout, stderr, proc.returncode, task)
        with self._lock:
            task.result = payload
            task.finished_at = datetime.now().isoformat(timespec="seconds")
            task.status = "completed" if proc.returncode == 0 else ("stopped" if task.status == "stopped" else "failed")
            task.error = None if proc.returncode == 0 else self._extract_error(payload, stderr)
            self._procs.pop(task_id, None)

    def _parse_payload(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        task: ManagedExecution,
    ) -> dict[str, Any]:
        blob = (stdout or "").strip()
        json_start = blob.find("{")
        payload_text = blob[json_start:] if json_start >= 0 else blob
        payload: dict[str, Any]
        try:
            payload = json.loads(payload_text) if payload_text else {}
        except json.JSONDecodeError:
            payload = {}
        if stderr:
            payload["stderr"] = ((payload.get("stderr") or "") + ("\n" if payload.get("stderr") else "") + stderr).strip()
        if returncode != 0:
            payload.setdefault("status", "Fail")
            payload.setdefault("suite_name", task.kind)
            payload.setdefault("module_name", task.title)
            payload.setdefault("passed", 0)
            payload.setdefault("failed", 1)
            payload.setdefault("total", 1)
            payload.setdefault("extra", {})
        return payload

    @staticmethod
    def _extract_error(payload: dict[str, Any], stderr: str) -> str:
        for candidate in (
            payload.get("detail"),
            payload.get("stderr"),
            stderr.strip(),
            payload.get("stdout"),
        ):
            if candidate:
                return str(candidate)
        return "Execution failed."

    @staticmethod
    def _masked_env_overrides(env_overrides: dict[str, str]) -> dict[str, str]:
        masked: dict[str, str] = {}
        sensitive_tokens = ("KEY", "PASSWORD", "TOKEN", "SECRET", "OTP")
        for key, value in env_overrides.items():
            if any(token in key.upper() for token in sensitive_tokens):
                masked[key] = "***" if value else ""
            else:
                masked[key] = value
        return masked

    @staticmethod
    def _terminate_process_tree(pid: int | None, *, force: bool = False) -> None:
        if not pid:
            return
        args = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            args.append("/F")
        subprocess.run(args, capture_output=True, text=True, check=False)


task_manager = ExecutionTaskManager()
