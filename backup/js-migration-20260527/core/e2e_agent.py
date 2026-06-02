from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from core.browser_diagnostics import collect_page_diagnostics
from core.healing import LocatorHealer, LocatorSpec
from core.reporting import write_html_report
from core.settings import RUNS_DIR
from core.store import ExecutionStore, RunSummary


VARIABLE_PATTERN = re.compile(r"\$\{([^}]+)\}")


@dataclass
class AgentStep:
    name: str
    action: str
    selector: str | None = None
    selectors: list[str] = field(default_factory=list)
    role: str | None = None
    role_name: str | None = None
    text: str | None = None
    exact: bool = False
    url: str | None = None
    value: str | None = None
    key: str | None = None
    timeout_ms: int | None = None
    wait_until: str | None = None
    expects_text: str | None = None
    expects_url: str | None = None
    screenshot_name: str | None = None
    option: str | None = None
    script: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentFlow:
    suite_name: str
    module_name: str
    start_url: str | None = None
    base_url: str | None = None
    browsers: list[str] = field(default_factory=lambda: ["chromium"])
    headless: bool = False
    slow_mo: int = 100
    storage_state: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    context_options: dict[str, Any] = field(default_factory=dict)
    steps: list[AgentStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentFlow":
        steps = [AgentStep(**step) for step in payload.get("steps", [])]
        return cls(
            suite_name=payload["suite_name"],
            module_name=payload["module_name"],
            start_url=payload.get("start_url"),
            base_url=payload.get("base_url"),
            browsers=payload.get("browsers") or ["chromium"],
            headless=bool(payload.get("headless", False)),
            slow_mo=int(payload.get("slow_mo", 100)),
            storage_state=payload.get("storage_state"),
            variables=payload.get("variables") or {},
            context_options=payload.get("context_options") or {},
            steps=steps,
        )


class E2EAgentRunner:
    def __init__(self, store: ExecutionStore | None = None):
        self.store = store or ExecutionStore()
        self.healer = LocatorHealer(store=self.store)

    def load_flow(self, flow_path: str | Path) -> AgentFlow:
        path = Path(flow_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        flow = AgentFlow.from_dict(payload)
        return self._resolve_flow(flow, path)

    def run_flow_file(self, flow_path: str | Path) -> dict[str, Any]:
        flow = self.load_flow(flow_path)
        return self.run_flow(flow, source_path=Path(flow_path))

    def run_flow(self, flow: AgentFlow, *, source_path: Path | None = None) -> dict[str, Any]:
        started_at = datetime.now().isoformat(timespec="seconds")
        browser_breakdown: dict[str, dict[str, int]] = {}
        extra_runs: list[dict[str, Any]] = []
        overall_status = "Pass"
        overall_stdout: list[str] = []
        overall_stderr: list[str] = []

        with sync_playwright() as playwright:
            for browser_name in flow.browsers:
                browser_run = self._run_browser(playwright, flow, browser_name)
                browser_breakdown[browser_name] = {
                    "Pass": browser_run["passed"],
                    "Fail": browser_run["failed"],
                }
                extra_runs.append(browser_run)
                overall_stdout.extend(browser_run["stdout"])
                overall_stderr.extend(browser_run["stderr"])
                if browser_run["status"] != "Pass":
                    overall_status = "Fail"

        finished_at = datetime.now().isoformat(timespec="seconds")
        passed = sum(item["passed"] for item in extra_runs)
        failed = sum(item["failed"] for item in extra_runs)
        total = passed + failed
        summary = RunSummary(
            suite_name=flow.suite_name,
            module_name=flow.module_name,
            started_at=started_at,
            finished_at=finished_at,
            passed=passed,
            failed=failed,
            total=total,
            status=overall_status,
            command=f"python run_e2e_agent.py --flow {source_path}" if source_path else "python run_e2e_agent.py",
            stdout="\n".join(overall_stdout),
            stderr="\n".join(overall_stderr),
            browser_breakdown=browser_breakdown,
            extra={
                "source_path": str(source_path) if source_path else None,
                "browsers": extra_runs,
                "variables": flow.variables,
            },
        )
        summary_dict = asdict(summary)
        summary.report_path = str(write_html_report(summary_dict))
        run_id = self.store.record_run(summary)
        payload = asdict(summary)
        payload["id"] = run_id
        return payload

    def _run_browser(self, playwright: Playwright, flow: AgentFlow, browser_name: str) -> dict[str, Any]:
        browser_type = getattr(playwright, browser_name)
        browser = browser_type.launch(headless=flow.headless, slow_mo=flow.slow_mo)
        stdout: list[str] = []
        stderr: list[str] = []
        passed = 0
        failed = 0
        artifacts_dir = self._browser_artifact_dir(flow, browser_name)
        context = None

        try:
            context = self._create_context(browser, flow)
            page = context.new_page()
            page._context = {
                "suite_name": flow.suite_name,
                "module_name": flow.module_name,
                "test_name": flow.module_name,
            }
            if flow.start_url:
                page.goto(flow.start_url, wait_until="domcontentloaded")
                stdout.append(f"[{browser_name}] open:{flow.start_url}")

            for step in flow.steps:
                try:
                    self._execute_step(page, flow, step, browser_name, artifacts_dir)
                    passed += 1
                    stdout.append(f"[{browser_name}] pass:{step.name}")
                    self.store.record_step_event(
                        suite_name=flow.suite_name,
                        module_name=flow.module_name,
                        test_name=flow.module_name,
                        browser_name=browser_name,
                        step_name=step.name,
                        status="Pass",
                    )
                except Exception as exc:
                    failed += 1
                    screenshot_path = artifacts_dir / self._safe_name(f"{step.name}.png")
                    try:
                        page.screenshot(path=str(screenshot_path), full_page=True)
                    except Exception:
                        screenshot_path = None
                    diagnostics = collect_page_diagnostics(
                        page,
                        action=step.action,
                        locator_name=step.name,
                        intent=step.metadata.get("intent") if isinstance(step.metadata, dict) else None,
                    )
                    stderr.append(f"[{browser_name}] fail:{step.name}:{type(exc).__name__}: {exc}")
                    self.store.record_step_event(
                        suite_name=flow.suite_name,
                        module_name=flow.module_name,
                        test_name=flow.module_name,
                        browser_name=browser_name,
                        step_name=step.name,
                        status="Fail",
                        remarks=f"{type(exc).__name__}: {exc}",
                        screenshot_path=str(screenshot_path) if screenshot_path else None,
                        extra={"diagnostics": diagnostics, "step": asdict(step)},
                    )
                    raise
        finally:
            if context is not None:
                context.close()
            browser.close()

        return {
            "browser": browser_name,
            "status": "Pass" if failed == 0 else "Fail",
            "passed": passed,
            "failed": failed,
            "stdout": stdout,
            "stderr": stderr,
            "artifacts_dir": str(artifacts_dir),
        }

    def _create_context(self, browser: Browser, flow: AgentFlow) -> BrowserContext:
        context_options = dict(flow.context_options)
        if flow.storage_state:
            context_options["storage_state"] = flow.storage_state
        return browser.new_context(**context_options)

    def _execute_step(
        self,
        page: Page,
        flow: AgentFlow,
        step: AgentStep,
        browser_name: str,
        artifacts_dir: Path,
    ) -> None:
        action = step.action.strip().lower()
        timeout_ms = step.timeout_ms or 10000

        if action == "goto":
            if not step.url:
                raise ValueError(f"Step '{step.name}' is missing url")
            page.goto(
                self._normalize_url(step.url, flow.base_url),
                wait_until=step.wait_until or "domcontentloaded",
                timeout=timeout_ms,
            )
            return

        if action == "fill":
            if step.value is None:
                raise ValueError(f"Step '{step.name}' is missing value")
            locator = self._resolve_locator(page, step, flow)
            locator.fill(step.value, timeout=timeout_ms)
            return

        if action == "click":
            locator = self._resolve_locator(page, step, flow)
            locator.click(timeout=timeout_ms)
            return

        if action == "press":
            locator = self._resolve_locator(page, step, flow)
            locator.press(step.key or "Enter", timeout=timeout_ms)
            return

        if action == "wait_for":
            locator = self._resolve_locator(page, step, flow)
            locator.wait_for(timeout=timeout_ms)
            return

        if action == "select":
            if step.option is None:
                raise ValueError(f"Step '{step.name}' is missing option")
            locator = self._resolve_locator(page, step, flow)
            locator.select_option(step.option, timeout=timeout_ms)
            return

        if action == "assert_text":
            expected_text = step.expects_text or step.value
            if not expected_text:
                raise ValueError(f"Step '{step.name}' is missing expects_text")
            locator = self._resolve_locator(page, step, flow)
            actual_text = locator.inner_text(timeout=timeout_ms)
            if expected_text not in actual_text:
                raise AssertionError(
                    f"Expected '{expected_text}' in locator text for step '{step.name}', got '{actual_text[:240]}'"
                )
            return

        if action == "assert_url":
            expected_url = step.expects_url or step.value
            if not expected_url:
                raise ValueError(f"Step '{step.name}' is missing expects_url")
            page.wait_for_url(expected_url, timeout=timeout_ms)
            return

        if action == "screenshot":
            screenshot_name = step.screenshot_name or f"{browser_name}_{self._safe_name(step.name)}.png"
            page.screenshot(path=str(artifacts_dir / screenshot_name), full_page=True)
            return

        if action == "evaluate":
            if not step.script:
                raise ValueError(f"Step '{step.name}' is missing script")
            page.evaluate(step.script)
            return

        raise ValueError(f"Unsupported action '{step.action}' in step '{step.name}'")

    def _resolve_locator(self, page: Page, step: AgentStep, flow: AgentFlow):
        selectors = list(step.selectors)
        if step.selector:
            selectors.insert(0, step.selector)
        if not selectors and not step.role and not step.text:
            raise ValueError(f"Step '{step.name}' is missing locator details")
        for selector in selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    return locator.first
            except Exception:
                continue
        spec = LocatorSpec(
            name=step.name,
            selectors=selectors,
            role=step.role,
            role_name=step.role_name,
            text=step.text,
            exact=step.exact,
            intent=step.metadata.get("intent") if isinstance(step.metadata, dict) else None,
            metadata=step.metadata if isinstance(step.metadata, dict) else {},
        )
        return self.healer.resolve(
            page,
            spec,
            suite_name=flow.suite_name,
            module_name=flow.module_name,
            test_name=flow.module_name,
            action=step.action,
        )

    def _resolve_flow(self, flow: AgentFlow, source_path: Path) -> AgentFlow:
        variables = self._build_variables(flow, source_path)
        steps = [self._resolve_step(step, variables) for step in flow.steps]
        return AgentFlow(
            suite_name=self._render_string(flow.suite_name, variables),
            module_name=self._render_string(flow.module_name, variables),
            start_url=self._render_string(flow.start_url, variables),
            base_url=self._render_string(flow.base_url, variables),
            browsers=list(flow.browsers),
            headless=flow.headless,
            slow_mo=flow.slow_mo,
            storage_state=self._resolve_optional_path(self._render_string(flow.storage_state, variables), source_path),
            variables=variables,
            context_options=self._render_mapping(flow.context_options, variables, source_path),
            steps=steps,
        )

    def _resolve_step(self, step: AgentStep, variables: dict[str, Any]) -> AgentStep:
        payload = asdict(step)
        payload["name"] = self._render_string(step.name, variables)
        payload["selector"] = self._render_string(step.selector, variables)
        payload["selectors"] = [self._render_string(item, variables) for item in step.selectors]
        payload["role"] = self._render_string(step.role, variables)
        payload["role_name"] = self._render_string(step.role_name, variables)
        payload["text"] = self._render_string(step.text, variables)
        payload["url"] = self._render_string(step.url, variables)
        payload["value"] = self._render_string(step.value, variables)
        payload["key"] = self._render_string(step.key, variables)
        payload["wait_until"] = self._render_string(step.wait_until, variables)
        payload["expects_text"] = self._render_string(step.expects_text, variables)
        payload["expects_url"] = self._render_string(step.expects_url, variables)
        payload["screenshot_name"] = self._render_string(step.screenshot_name, variables)
        payload["option"] = self._render_string(step.option, variables)
        payload["script"] = self._render_string(step.script, variables)
        payload["metadata"] = self._render_mapping(step.metadata, variables, None)
        return AgentStep(**payload)

    def _build_variables(self, flow: AgentFlow, source_path: Path) -> dict[str, Any]:
        variables = dict(flow.variables)
        variables.setdefault("flow_dir", str(source_path.parent.resolve()))
        if flow.base_url:
            variables.setdefault("base_url", flow.base_url)
        return variables

    def _render_mapping(
        self,
        payload: dict[str, Any],
        variables: dict[str, Any],
        source_path: Path | None,
    ) -> dict[str, Any]:
        rendered: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, str):
                rendered[key] = self._render_string(value, variables)
                if key == "storage_state" and source_path is not None:
                    rendered[key] = self._resolve_optional_path(rendered[key], source_path)
            else:
                rendered[key] = value
        return rendered

    def _render_string(self, value: str | None, variables: dict[str, Any]) -> str | None:
        if value is None or not isinstance(value, str):
            return value

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        return VARIABLE_PATTERN.sub(replace, value)

    def _resolve_optional_path(self, value: str | None, source_path: Path | None) -> str | None:
        if not value:
            return None
        path = Path(value)
        if path.is_absolute() or source_path is None:
            return str(path)
        return str((source_path.parent / path).resolve())

    def _browser_artifact_dir(self, flow: AgentFlow, browser_name: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = RUNS_DIR / f"{flow.module_name}_{browser_name}_{stamp}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _normalize_url(url: str, base_url: str | None) -> str:
        if base_url and url.startswith("/"):
            return base_url.rstrip("/") + url
        return url

    @staticmethod
    def _safe_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "step"
