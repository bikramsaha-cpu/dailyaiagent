from __future__ import annotations

import json
import logging
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from testlink import TestlinkAPIClient

from core.module_registry import get_module
from core import settings as core_settings


log = logging.getLogger(__name__)


@dataclass(slots=True)
class GenerationResult:
    title: str
    output_path: Path | None
    status: str
    detail: str = ""


@dataclass(slots=True)
class TestLinkGeneratorConfig:
    suite_id: int
    module_id: str
    output_dir: Path
    testlink_url: str = getattr(
        core_settings,
        "TESTLINK_URL",
        "https://testlink.intermesh.net/lib/api/xmlrpc/v1/xmlrpc.php",
    )
    testlink_api_key: str = getattr(core_settings, "TESTLINK_API_KEY", "")
    llm_api_key: str = getattr(core_settings, "LLM_API_KEY", "")
    llm_base_url: str = getattr(core_settings, "LLM_BASE_URL", "https://imllm.intermesh.net/v1")
    llm_model: str = getattr(core_settings, "LLM_MODEL", "anthropic/claude-sonnet-4-6")
    ca_bundle: str = getattr(core_settings, "TESTLINK_CA_BUNDLE", "")
    insecure_skip_verify: bool = getattr(core_settings, "TESTLINK_INSECURE_SKIP_VERIFY", True)
    overwrite: bool = False
    max_cases: int | None = None


class TestLinkCaseGenerator:
    def __init__(self, config: TestLinkGeneratorConfig):
        self.config = config

    def run(self) -> list[GenerationResult]:
        self._validate()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        client = self._create_testlink_client()
        testcases = client.getTestCasesForTestSuite(self.config.suite_id, True, "full")
        results: list[GenerationResult] = []

        if not testcases:
            log.warning("No test cases found in Suite ID %s", self.config.suite_id)
            return results

        for index, testcase in enumerate(testcases, start=1):
            if self.config.max_cases is not None and index > self.config.max_cases:
                break
            results.append(self._generate_test_file(testcase))
        return results

    def _validate(self) -> None:
        if not self.config.testlink_api_key:
            raise ValueError("AUTOMATION_TESTLINK_API_KEY is required.")
        if not self.config.llm_api_key:
            raise ValueError("AUTOMATION_LLM_API_KEY is required.")
        if not self.config.llm_base_url:
            raise ValueError("AUTOMATION_LLM_BASE_URL is required.")
        if not self.config.llm_model:
            raise ValueError("AUTOMATION_LLM_MODEL is required.")

    def _create_testlink_client(self) -> TestlinkAPIClient:
        ssl_context = self._build_ssl_context()
        return TestlinkAPIClient(
            self.config.testlink_url,
            self.config.testlink_api_key,
            context=ssl_context,
        )

    def _build_ssl_context(self) -> ssl.SSLContext:
        if self.config.ca_bundle:
            ca_path = Path(self.config.ca_bundle)
            if not ca_path.exists():
                raise FileNotFoundError(f"Configured CA bundle was not found: {ca_path}")
            log.info("Using TestLink CA bundle: %s", ca_path)
            return ssl.create_default_context(cafile=str(ca_path))

        if self.config.insecure_skip_verify:
            log.warning(
                "SSL verification for TestLink is disabled. "
                "Set AUTOMATION_TESTLINK_CA_BUNDLE to enable verification."
            )
            return ssl._create_unverified_context()

        return ssl.create_default_context()

    def _generate_test_file(self, testcase: dict[str, Any]) -> GenerationResult:
        title = testcase.get("name", "Unnamed_Test_Case").strip()
        steps_list = testcase.get("steps", [])
        if not isinstance(steps_list, list):
            return GenerationResult(title=title, output_path=None, status="skipped", detail="Invalid step format")

        steps_combined = self._build_steps_text(steps_list)
        if not steps_combined.strip():
            return GenerationResult(title=title, output_path=None, status="skipped", detail="No valid steps found")

        safe_title = self._safe_name(title)
        output_path = self.config.output_dir / f"test_{safe_title}.py"
        if output_path.exists() and not self.config.overwrite:
            return GenerationResult(title=title, output_path=output_path, status="skipped", detail="File already exists")

        log.info("Generating script for: %s", title)
        script = self._generate_script(title, steps_combined)
        try:
            compile(script, str(output_path), "exec")
        except SyntaxError as exc:
            return GenerationResult(title=title, output_path=None, status="failed", detail=f"Syntax error: {exc}")

        output_path.write_text(self._render_file_header(title) + script, encoding="utf-8")
        return GenerationResult(title=title, output_path=output_path, status="generated")

    def _generate_script(self, title: str, steps_combined: str) -> str:
        prompt = self._build_prompt(title, steps_combined)
        payload = {
            "model": self.config.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate robust Playwright Python tests from manual test cases. "
                        "Return only valid Python code."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.config.llm_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(f"LLM request failed for '{title}': {exc}") from exc

        raw_script = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        script = self._clean_generated_script(raw_script)
        if not script:
            raise RuntimeError(f"LLM returned an empty script for '{title}'.")
        return script

    def _build_prompt(self, title: str, steps_combined: str) -> str:
        module = get_module(self.config.module_id)
        module_dir = core_settings.ROOT_DIR / module.id
        auth_candidates = [
            module_dir / "testscript" / "auth.json",
            module_dir / "auth.json",
        ]
        auth_hint = next((candidate for candidate in auth_candidates if candidate.exists()), auth_candidates[0])
        relative_auth_hint = auth_hint.relative_to(core_settings.ROOT_DIR).as_posix()

        return (
            f"Convert the following manual test case into a Playwright Python test script for the '{module.label}' module.\n"
            f"Test case title: {title}\n\n"
            "Requirements:\n"
            "- Return only valid Python code with no explanation and no markdown fences.\n"
            "- Use `from playwright.sync_api import sync_playwright, expect` when needed.\n"
            "- Generate one pytest-style function named from the test case title.\n"
            f"- Reuse the saved Playwright session from `{relative_auth_hint}` if login is needed.\n"
            "- Prefer resilient locators based on role, label, placeholder, or stable text.\n"
            "- Add short waits only when necessary.\n"
            "- Keep the script runnable as a standalone pytest test.\n\n"
            f"Manual steps:\n{steps_combined}"
        )

    @staticmethod
    def _build_steps_text(steps_list: list[dict[str, Any]]) -> str:
        chunks: list[str] = []
        for step in steps_list:
            actions_text = BeautifulSoup(step.get("actions", ""), "html.parser").get_text(separator="\n").strip()
            expected_text = BeautifulSoup(step.get("expected_results", ""), "html.parser").get_text(separator="\n").strip()
            if not actions_text and not expected_text:
                continue
            chunks.append(
                f"Step {step.get('step_number', '?')}:\n"
                f"Action: {actions_text or '-'}\n"
                f"Expected: {expected_text or '-'}"
            )
        return "\n\n".join(chunks)

    @staticmethod
    def _clean_generated_script(script: str) -> str:
        code_match = re.search(r"```(?:python)?(.*?)```", script, re.DOTALL)
        if code_match:
            script = code_match.group(1).strip()

        lines = script.splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ", "def ", "class ", "@")):
                return "\n".join(lines[index:]).strip()
        return script.strip()

    @staticmethod
    def _safe_name(title: str) -> str:
        cleaned = re.sub(r"[^0-9A-Za-z_-]+", "_", title).strip("_")
        return cleaned or "generated_test"

    @staticmethod
    def _render_file_header(title: str) -> str:
        return f"# Test Case: {title}\n# Auto-generated from TestLink using the daily-qa-agent generator.\n\n"


def default_output_dir_for_module(module_id: str) -> Path:
    module = get_module(module_id)
    module_dir = core_settings.ROOT_DIR / module.id
    testscript_dir = module_dir / "testscript"
    base_dir = testscript_dir if testscript_dir.exists() else module_dir
    return base_dir / "generated_from_testlink"
