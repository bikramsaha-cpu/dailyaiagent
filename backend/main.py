from __future__ import annotations

from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.execution_tasks import task_manager
from core.api_services import (
    generate_testlink_tests,
    get_module_payload,
    get_status_payload,
    latest_run_for_module,
    list_locator_healings,
    list_module_tests,
    list_modules_payload,
    list_runs,
    list_sheet_tabs,
    list_step_events,
    read_sheet_records,
    run_module,
    send_sheet_report_email,
    run_url_audit,
)
from core.workspace_settings import save_workspace_settings


class URLAgentRequest(BaseModel):
    url: str
    headless: bool = False
    slow_mo: int = Field(default=100, ge=0, le=5000)
    visual_guard: bool = True


class TestLinkRequest(BaseModel):
    module_id: str
    suite_id: int
    output_dir: Optional[str] = None
    overwrite: bool = False
    max_cases: Optional[int] = Field(default=None, ge=1)
    testlink_api_key: Optional[str] = None
    testlink_url: Optional[str] = None
    testlink_ca_bundle: Optional[str] = None
    testlink_insecure_skip_verify: Optional[bool] = None
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None


class ModuleExecutionRequest(BaseModel):
    module_id: str
    browser_mode: str = Field(default="headed", pattern="^(headed|headless)$")
    selected_tests: List[str] = Field(default_factory=list)
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    default_login_phone: Optional[str] = None
    default_login_otp: Optional[str] = None
    smtp_recipients: Optional[str] = None


class SheetReportEmailRequest(BaseModel):
    module_id: str
    sheet_name: str
    tab_name: str
    status: List[str] = Field(default_factory=list)
    browser: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    search: Optional[str] = None
    recipients: List[str] = Field(default_factory=list)


class WorkspaceSettingsRequest(BaseModel):
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    default_login_phone: Optional[str] = None
    default_login_otp: Optional[str] = None
    testlink_api_key: Optional[str] = None
    testlink_url: Optional[str] = None
    testlink_ca_bundle: Optional[str] = None
    testlink_insecure_skip_verify: Optional[bool] = None
    smtp_recipients: Optional[str] = None


app = FastAPI(
    title="Daily QA Agent API",
    version="1.0.0",
    description="A modern API facade over the existing daily-qa-agent automation core.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def module_env_overrides(request: ModuleExecutionRequest) -> dict[str, str]:
    candidates = {
        "AUTOMATION_LLM_API_KEY": request.llm_api_key,
        "AUTOMATION_LLM_BASE_URL": request.llm_base_url,
        "AUTOMATION_LLM_MODEL": request.llm_model,
        "AUTOMATION_DEFAULT_LOGIN_PHONE": request.default_login_phone,
        "AUTOMATION_DEFAULT_LOGIN_OTP": request.default_login_otp,
        "AUTOMATION_SMTP_RECIPIENTS": request.smtp_recipients,
    }
    return {
        key: value.strip()
        for key, value in candidates.items()
        if isinstance(value, str) and value.strip()
    }


def workspace_settings_env(request: WorkspaceSettingsRequest) -> dict[str, str]:
    candidates = {
        "AUTOMATION_LLM_API_KEY": request.llm_api_key,
        "AUTOMATION_LLM_BASE_URL": request.llm_base_url,
        "AUTOMATION_LLM_MODEL": request.llm_model,
        "AUTOMATION_DEFAULT_LOGIN_PHONE": request.default_login_phone,
        "AUTOMATION_DEFAULT_LOGIN_OTP": request.default_login_otp,
        "AUTOMATION_TESTLINK_API_KEY": request.testlink_api_key,
        "AUTOMATION_TESTLINK_URL": request.testlink_url,
        "AUTOMATION_TESTLINK_CA_BUNDLE": request.testlink_ca_bundle,
        "AUTOMATION_SMTP_RECIPIENTS": request.smtp_recipients,
    }
    values = {
        key: value.strip()
        for key, value in candidates.items()
        if isinstance(value, str)
    }
    if request.testlink_insecure_skip_verify is not None:
        values["AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY"] = "1" if request.testlink_insecure_skip_verify else "0"
    return values


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/settings/workspace")
def save_workspace_settings_endpoint(request: WorkspaceSettingsRequest) -> dict[str, Any]:
    import os

    values = save_workspace_settings(workspace_settings_env(request))
    for key, value in values.items():
        if value:
            os.environ[key] = value
    return {"saved": True, "keys": sorted(values.keys())}


@app.get("/api/status")
def status() -> dict[str, Any]:
    return get_status_payload()


@app.get("/api/modules")
def modules() -> list[dict[str, Any]]:
    return list_modules_payload()


@app.get("/api/modules/{module_id}")
def module_detail(module_id: str) -> dict[str, Any]:
    try:
        payload = get_module_payload(module_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload["latest_run"] = latest_run_for_module(module_id)
    return payload


@app.get("/api/modules/{module_id}/tests")
def module_tests(module_id: str) -> dict[str, Any]:
    try:
        return {"tests": list_module_tests(module_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load module tests: {exc}") from exc


@app.post("/api/modules/{module_id}/run")
def run_selected_module(module_id: str) -> dict[str, Any]:
    try:
        return run_module(module_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Module run failed: {exc}") from exc


@app.post("/api/executions/module/start")
def start_module_execution(request: ModuleExecutionRequest) -> dict[str, Any]:
    try:
        return task_manager.start_module(
            request.module_id,
            browser_mode=request.browser_mode,
            selected_tests=request.selected_tests,
            env_overrides=module_env_overrides(request),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not start module execution: {exc}") from exc


@app.post("/api/executions/url-agent/start")
def start_url_agent_execution(request: URLAgentRequest) -> dict[str, Any]:
    try:
        return task_manager.start_url_agent(
            request.url,
            headless=request.headless,
            slow_mo=request.slow_mo,
            visual_guard=request.visual_guard,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not start URL agent execution: {exc}") from exc


@app.get("/api/executions/active")
def active_executions() -> list[dict[str, Any]]:
    return task_manager.list_active()


@app.get("/api/executions/{task_id}")
def execution_detail(task_id: str) -> dict[str, Any]:
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown execution task: {task_id}")
    return task


@app.post("/api/executions/{task_id}/stop")
def stop_execution(task_id: str) -> dict[str, Any]:
    try:
        return task_manager.stop_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not stop execution: {exc}") from exc


@app.post("/api/executions/{task_id}/restart")
def restart_execution(task_id: str) -> dict[str, Any]:
    try:
        return task_manager.restart_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not restart execution: {exc}") from exc


@app.get("/api/runs")
def runs(
    limit: int = Query(default=50, ge=1, le=500),
    suite_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    return list_runs(limit=limit, suite_name=suite_name)


@app.get("/api/sheets/tabs")
def sheet_tabs(sheet_name: str, fallback_tab: str) -> dict[str, Any]:
    try:
        return {"tabs": list_sheet_tabs(sheet_name, fallback_tab)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load sheet tabs: {exc}") from exc


@app.get("/api/sheets/records")
def sheet_records(
    sheet_name: str,
    tab_name: str,
    status: Optional[List[str]] = Query(default=None),
    browser: Optional[List[str]] = Query(default=None),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    try:
        records = read_sheet_records(
            sheet_name=sheet_name,
            tab_name=tab_name,
            status=status,
            browser=browser,
            start_date=start_date,
            end_date=end_date,
            search=search,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read sheet records: {exc}") from exc
    return {"records": records, "count": len(records)}


@app.get("/api/diagnostics/healings")
def diagnostics_healings(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    return list_locator_healings(limit=limit)


@app.get("/api/diagnostics/steps")
def diagnostics_steps(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    return list_step_events(limit=limit)


@app.post("/api/url-agent/run")
def run_url_agent(request: URLAgentRequest) -> dict[str, Any]:
    try:
        return run_url_audit(
            request.url,
            headless=request.headless,
            slow_mo=request.slow_mo,
            visual_guard=request.visual_guard,
        )
    except Exception as exc:
        detail = str(exc).strip() or repr(exc) or exc.__class__.__name__
        raise HTTPException(
            status_code=500,
            detail=f"URL agent failed ({exc.__class__.__name__}): {detail}",
        ) from exc


@app.post("/api/testlink/generate")
def generate_from_testlink(request: TestLinkRequest) -> dict[str, Any]:
    try:
        return generate_testlink_tests(
            module_id=request.module_id,
            suite_id=request.suite_id,
            output_dir=request.output_dir,
            overwrite=request.overwrite,
            max_cases=request.max_cases,
            testlink_api_key=request.testlink_api_key,
            testlink_url=request.testlink_url,
            testlink_ca_bundle=request.testlink_ca_bundle,
            testlink_insecure_skip_verify=request.testlink_insecure_skip_verify,
            llm_api_key=request.llm_api_key,
            llm_base_url=request.llm_base_url,
            llm_model=request.llm_model,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Test generation failed: {exc}") from exc


@app.post("/api/reports/email")
def email_filtered_report(request: SheetReportEmailRequest) -> dict[str, Any]:
    try:
        return send_sheet_report_email(
            module_id=request.module_id,
            sheet_name=request.sheet_name,
            tab_name=request.tab_name,
            status=request.status,
            browser=request.browser,
            start_date=request.start_date,
            end_date=request.end_date,
            search=request.search,
            recipients=request.recipients,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not send report email: {exc}") from exc
