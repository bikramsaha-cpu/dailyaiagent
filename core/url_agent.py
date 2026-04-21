from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from core.browser_diagnostics import collect_page_diagnostics
from core.settings import DEFAULT_LOGIN_OTP, DEFAULT_LOGIN_PHONE, REPORTS_DIR, RUNS_DIR, URL_AGENT_MAX_CTAS, URL_AGENT_MAX_FORMS, URL_AGENT_MAX_LINKS
from core.store import ExecutionStore, RunSummary


class URLAuditAgent:
    def __init__(self, store: ExecutionStore | None = None):
        self.store = store or ExecutionStore()

    def run(self, url: str, *, headless: bool = False, slow_mo: int = 100) -> dict[str, Any]:
        started_at = datetime.now().isoformat(timespec="seconds")
        artifact_dir = self._artifact_dir(url)
        screenshot_path = artifact_dir / "page.png"
        state_path = artifact_dir / "auth_state.json"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            login_case = self._attempt_login(page, context)
            if login_case["status"] == "Pass":
                try:
                    context.storage_state(path=str(state_path))
                except Exception:
                    state_path = None
            else:
                state_path = None
            page.wait_for_timeout(1000)
            page.screenshot(path=str(screenshot_path), full_page=True)
            diagnostics = collect_page_diagnostics(page, action="url_audit", locator_name="page", intent="page audit")
            summary = self._extract_page_summary(page)
            planned = self._plan_cases(summary, diagnostics, url)
            executed = [login_case] + self._execute_cases(browser, url, planned, artifact_dir, state_path)
            context.close()
            browser.close()

        findings = self._findings(summary, diagnostics, executed)
        human_required = self._human_required(summary, diagnostics, executed)
        counts = self._case_counts(executed)
        finished_at = datetime.now().isoformat(timespec="seconds")
        status = "Fail" if counts["Fail"] else ("Needs Review" if counts["Needs Review"] or human_required else "Pass")
        run = RunSummary(
            suite_name="AI URL Agent",
            module_name=self._module_name(url),
            started_at=started_at,
            finished_at=finished_at,
            passed=counts["Pass"],
            failed=counts["Fail"],
            total=len(executed),
            status=status,
            command=f"python run_url_agent.py --url {url}",
            stdout=json.dumps({"findings": findings, "executed_cases": executed, "human_required": human_required}, indent=2),
            browser_breakdown={"chromium": {"Pass": counts["Pass"], "Fail": counts["Fail"]}},
            extra={
                "url": url,
                "login_phone": DEFAULT_LOGIN_PHONE,
                "screenshot_path": str(screenshot_path),
                "page_summary": summary,
                "diagnostics": diagnostics,
                "findings": findings,
                "test_cases": executed,
                "human_required": human_required,
                "case_counts": counts,
            },
        )
        payload = asdict(run)
        run.report_path = str(self._write_report(payload))
        run_id = self.store.record_run(run)
        payload = asdict(run)
        payload["id"] = run_id
        return payload

    def _attempt_login(self, page, context) -> dict[str, Any]:
        result = {
            "id": "login_flow",
            "title": "Attempt login if required",
            "objective": f"Use phone {DEFAULT_LOGIN_PHONE} and OTP {DEFAULT_LOGIN_OTP} when the page asks for login.",
            "status": "Skipped",
            "details": "No login gate was detected.",
            "evidence": "",
        }
        try:
            body = (page.locator("body").inner_text(timeout=2000) or "").lower()
            if not any(term in body for term in ["login", "sign in", "send otp", "verify otp", "mobile number", "enter otp"]):
                return result
            self._click_first(page, ["a:has-text('Sign in')", "button:has-text('Sign in')", "a:has-text('Login')", "button:has-text('Login')", "[href*='login']", "[data-click*='login']"])
            page.wait_for_timeout(1000)
            mobile = self._first_visible(page, ["input#mobilemy", "input[type='tel']", "input[name='mobile']", "input[name='phone']", "input[id*='mobile']", "input[id*='phone']"])
            if mobile is None:
                result["status"] = "Needs Review"
                result["details"] = "Login was indicated but no mobile input was found."
                return result
            mobile.fill(DEFAULT_LOGIN_PHONE)
            self._click_first(page, ["input#signInSubmitButton", "button:has-text('Send OTP')", "input[value='Send OTP']", "button:has-text('Continue')", "button:has-text('Next')"])
            page.wait_for_timeout(1000)
            if not self._fill_otp(page):
                result["status"] = "Needs Review"
                result["details"] = "Phone was entered but OTP input could not be found."
                result["evidence"] = DEFAULT_LOGIN_PHONE
                return result
            self._click_first(page, ["input[value='Verify OTP']", "button:has-text('Verify OTP')", "button:has-text('Verify')", "button:has-text('Submit')"])
            page.wait_for_timeout(1800)
            if self._login_success(context):
                result["status"] = "Pass"
                result["details"] = "Configured phone and OTP were accepted and login success indicators appeared."
                result["evidence"] = DEFAULT_LOGIN_PHONE
                return result
            result["status"] = "Needs Review"
            result["details"] = "Login was attempted but success could not be confirmed."
            result["evidence"] = DEFAULT_LOGIN_PHONE
            return result
        except Exception as exc:
            result["status"] = "Fail"
            result["details"] = f"{type(exc).__name__}: {exc}"
            result["evidence"] = DEFAULT_LOGIN_PHONE
            return result

    def _extract_page_summary(self, page) -> dict[str, Any]:
        return page.evaluate(
            """
            () => {
              const n = (v) => (v || '').replace(/\\s+/g, ' ').trim();
              const arr = (s, fn) => Array.from(document.querySelectorAll(s)).slice(0, 30).map(fn);
              return {
                title: document.title || '',
                url: location.href,
                headings: arr('h1, h2, h3', el => n(el.innerText || '')),
                links: arr('a[href]', el => ({ text: n(el.innerText || el.title || ''), href: el.href || '' })),
                buttons: arr('button, input[type="button"], input[type="submit"], [role="button"], a[href]', el => ({ text: n(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || ''), href: el.href || '' })),
                searchInputs: arr('input[type="search"], input[name*="search"], input[id*="search"], input[placeholder*="Search"], input[placeholder*="search"]', el => ({ id: el.id || '', name: el.name || '', placeholder: el.getAttribute('placeholder') || '' })),
                forms: Array.from(document.forms).slice(0, 6).map((form, index) => ({
                  index,
                  id: form.id || '',
                  fields: Array.from(form.querySelectorAll('input, textarea, select')).slice(0, 20).map((field) => ({
                    tag: field.tagName.toLowerCase(),
                    type: field.getAttribute('type') || '',
                    name: field.getAttribute('name') || '',
                    id: field.id || '',
                    placeholder: field.getAttribute('placeholder') || ''
                  }))
                })),
                pageText: n(document.body ? document.body.innerText : '').slice(0, 5000)
              };
            }
            """
        )

    def _plan_cases(self, summary: dict[str, Any], diagnostics: dict[str, Any], url: str) -> list[dict[str, Any]]:
        cases = [{"id": "page_load", "title": "Page load and visual smoke check", "objective": "Verify the page opens and body content is visible.", "kind": "page_load"}]
        for heading in (summary.get("headings") or [])[:3]:
            if heading:
                cases.append({"id": f"heading_{len(cases)}", "title": f"Verify heading: {heading[:60]}", "objective": "Confirm heading visibility.", "kind": "heading", "heading": heading})
        if summary.get("searchInputs"):
            cases.append({"id": "search_flow", "title": "Execute search flow", "objective": "Use the page search input and verify a reaction.", "kind": "search"})
        for idx, form in enumerate((summary.get("forms") or [])[: URL_AGENT_MAX_FORMS], start=1):
            fields = [f.get("name") or f.get("placeholder") or f.get("id") or f.get("type") or f.get("tag") for f in form.get("fields", [])[:5]]
            cases.append({"id": f"form_{idx}", "title": f"Fill and submit form {idx}", "objective": f"Fill safe fields and attempt submit for: {', '.join(str(x) for x in fields if x)}", "kind": "form_submit", "form_index": idx - 1})
        if diagnostics.get("interceptors"):
            cases.append({"id": "popup_handling", "title": "Validate popup handling", "objective": "Dismiss visible popup blockers.", "kind": "popup"})
        for idx, cta in enumerate(self._safe_ctas(summary.get("buttons") or [])[: URL_AGENT_MAX_CTAS], start=1):
            cases.append({"id": f"cta_{idx}", "title": f"Click CTA: {(cta.get('text') or 'CTA')[:60]}", "objective": "Click a visible CTA and verify page reaction.", "kind": "cta_click", "text": cta.get("text"), "href": cta.get("href")})
        for idx, link in enumerate(self._safe_links(summary.get("links") or [], url)[: URL_AGENT_MAX_LINKS], start=1):
            cases.append({"id": f"link_{idx}", "title": f"Click internal link: {(link.get('text') or link.get('href') or '')[:60]}", "objective": "Click a safe internal link and verify navigation.", "kind": "link_click", "text": link.get("text"), "href": link.get("href")})
        return cases

    def _execute_cases(self, browser, url: str, cases: list[dict[str, Any]], artifact_dir: Path, state_path: Path | None) -> list[dict[str, Any]]:
        executed = []
        for case in cases:
            opts = {"storage_state": str(state_path)} if state_path and state_path.exists() else {}
            context = browser.new_context(**opts)
            page = context.new_page()
            result = {"id": case["id"], "title": case["title"], "objective": case["objective"], "status": "Skipped", "details": "", "evidence": ""}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1200)
                kind = case["kind"]
                if kind == "page_load":
                    page.locator("body").wait_for(timeout=5000)
                    result.update(status="Pass", details=f"Loaded {page.url} and body content was visible.", evidence=page.title())
                elif kind == "heading":
                    loc = page.get_by_text(case.get("heading") or "", exact=False).first
                    loc.wait_for(timeout=5000)
                    result.update(status="Pass", details="Heading was found on the page.", evidence=case.get("heading", ""))
                elif kind == "search":
                    result.update(self._run_search(page))
                elif kind == "form_submit":
                    result.update(self._run_form_submit(page, int(case.get("form_index", 0))))
                elif kind == "popup":
                    result.update(self._run_popup(page))
                elif kind == "cta_click":
                    result.update(self._run_click(page, case, cta_mode=True))
                elif kind == "link_click":
                    result.update(self._run_click(page, case, cta_mode=False))
            except PlaywrightTimeoutError as exc:
                result.update(status="Fail", details=f"Timeout while executing case: {exc}")
            except Exception as exc:
                result.update(status="Fail", details=f"{type(exc).__name__}: {exc}")
            finally:
                shot = artifact_dir / f"{case['id']}.png"
                try:
                    page.screenshot(path=str(shot), full_page=True)
                    result["screenshot"] = str(shot)
                except Exception:
                    pass
                context.close()
            executed.append(result)
        return executed

    def _run_search(self, page) -> dict[str, Any]:
        loc = self._first_visible(page, ["input[type='search']", "input[name*='search']", "input[id*='search']", "input[placeholder*='Search']", "input[placeholder*='search']"])
        if loc is None:
            return {"status": "Skipped", "details": "No search field was detected.", "evidence": ""}
        before = page.url
        query = "pharmaceutical tablets"
        loc.fill(query)
        try:
            loc.press("Enter")
        except Exception:
            self._click_first(page, ["button[type='submit']", "button:has-text('Search')", "input[type='submit']"])
        page.wait_for_timeout(1800)
        body = (page.locator("body").inner_text(timeout=3000) or "").lower()
        if page.url != before or query.lower() in body:
            return {"status": "Pass", "details": "Search interaction executed and the page reacted.", "evidence": query}
        return {"status": "Needs Review", "details": "Search was attempted but the response could not be confidently verified.", "evidence": query}

    def _run_form_submit(self, page, form_index: int) -> dict[str, Any]:
        form = page.locator("form").nth(form_index)
        if form.count() == 0:
            return {"status": "Fail", "details": "Form was not found on the page.", "evidence": ""}
        fields = form.locator("input, textarea, select")
        filled, skipped = [], []
        for idx in range(min(fields.count(), 10)):
            field = fields.nth(idx)
            tag = (field.evaluate("el => el.tagName.toLowerCase()") or "").lower()
            input_type = (field.get_attribute("type") or "").lower()
            blob = " ".join(str(field.get_attribute(a) or "") for a in ("name", "id", "placeholder")).lower()
            if input_type in {"hidden", "button", "submit"}:
                continue
            if input_type in {"password", "file"} or any(x in blob for x in ("captcha", "otp", "verification")):
                skipped.append(blob or input_type)
                continue
            try:
                if tag == "select":
                    if field.locator("option").count() > 1:
                        field.select_option(index=1)
                        filled.append(blob or f"select_{idx}")
                elif tag == "textarea":
                    field.fill("Automated QA journey check")
                    filled.append(blob or f"textarea_{idx}")
                else:
                    field.fill(self._sample_value(blob, input_type))
                    filled.append(blob or f"input_{idx}")
            except Exception:
                continue
        submit = self._first_visible_within(form, ["button[type='submit']", "input[type='submit']", "button:has-text('Submit')", "button:has-text('Send')", "button:has-text('Get Best Price')", "button:has-text('Contact Supplier')", "button:has-text('Get Quotes')"])
        before_url = page.url
        before_text = (page.locator("body").inner_text(timeout=3000) or "")[:3000]
        if submit is not None and filled:
            try:
                submit.click(timeout=5000)
                page.wait_for_timeout(2000)
            except Exception:
                pass
        after_text = (page.locator("body").inner_text(timeout=3000) or "")[:3000].lower()
        if any(term in after_text for term in ("thank you", "thankyou", "submitted", "success", "verified", "enquiry")):
            return {"status": "Pass", "details": f"Filled {len(filled)} safe field(s) and observed a submission-style confirmation.", "evidence": ", ".join(filled[:5])}
        if filled and (page.url != before_url or after_text != before_text.lower()):
            return {"status": "Needs Review" if skipped else "Pass", "details": f"Filled {len(filled)} field(s) and triggered a visible page change after submit.", "evidence": ", ".join(filled[:5])}
        if filled:
            return {"status": "Needs Review" if skipped else "Pass", "details": f"Filled {len(filled)} safe field(s). Submit confirmation was not clearly detected.", "evidence": ", ".join(filled[:5])}
        if skipped:
            return {"status": "Needs Review", "details": "Form contains only sensitive or protected inputs requiring human help.", "evidence": ", ".join(skipped[:3])}
        return {"status": "Skipped", "details": "No safe editable fields were detected in this form.", "evidence": ""}

    def _run_popup(self, page) -> dict[str, Any]:
        before = len((collect_page_diagnostics(page, action="popup_check", locator_name="popup", intent="dismiss popup").get("interceptors") or []))
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        self._click_first(page, ["button[aria-label='close']", "button[title='close']", ".close-btn", ".close", "[data-testid='close']", ".modal button", ".popup button"])
        page.wait_for_timeout(800)
        after = len((collect_page_diagnostics(page, action="popup_after", locator_name="popup", intent="dismiss popup").get("interceptors") or []))
        if after < before:
            return {"status": "Pass", "details": f"Popup handling executed. Interceptors: {before} -> {after}", "evidence": "overlay reduced"}
        if before == 0:
            return {"status": "Skipped", "details": "No visible popup or overlay blocker was detected.", "evidence": ""}
        return {"status": "Needs Review", "details": "Popup-like elements remained after automated dismissal attempts.", "evidence": ""}

    def _run_click(self, page, case: dict[str, Any], *, cta_mode: bool) -> dict[str, Any]:
        text = (case.get("text") or "").strip()
        href = (case.get("href") or "").strip()
        loc = None
        if text:
            selectors = [f"button:has-text('{text}')", f"a:has-text('{text}')", f"text={text}"] if cta_mode else [f"a:has-text('{text}')", f"text={text}"]
            loc = self._first_visible(page, selectors)
        if loc is None and href:
            try:
                loc = page.locator(f'a[href="{href}"]').first
            except Exception:
                loc = None
        if loc is None:
            return {"status": "Fail", "details": "Target element could not be located for clicking.", "evidence": text or href}
        before_url = page.url
        before_text = (page.locator("body").inner_text(timeout=3000) or "")[:2500]
        try:
            loc.evaluate("el => el.removeAttribute && el.removeAttribute('target')")
        except Exception:
            pass
        try:
            loc.click(timeout=5000)
        except Exception:
            try:
                loc.evaluate("el => el.click()")
            except Exception as exc:
                return {"status": "Fail", "details": f"Click failed: {exc}", "evidence": text or href}
        page.wait_for_timeout(1500)
        after_text = (page.locator("body").inner_text(timeout=3000) or "")[:2500]
        if page.url != before_url or after_text != before_text:
            return {"status": "Pass", "details": "Click executed and the page reacted with navigation or content change.", "evidence": text or href}
        return {"status": "Needs Review", "details": "Click executed but no clear page change was detected.", "evidence": text or href}

    def _fill_otp(self, page) -> bool:
        otp = self._first_visible(page, ["input[placeholder='----']", "input[autocomplete='one-time-code']", "input[name='otp']", "input[id*='otp']", "input[maxlength='4']"])
        if otp is not None:
            try:
                otp.fill(DEFAULT_LOGIN_OTP)
                return True
            except Exception:
                pass
        boxes = page.locator("input[maxlength='1']")
        try:
            if boxes.count() >= 4:
                for i, digit in enumerate(DEFAULT_LOGIN_OTP[:4]):
                    boxes.nth(i).fill(digit)
                return True
        except Exception:
            pass
        return False

    def _login_success(self, context) -> bool:
        success = ["text=Dashboard", "text=My Orders", "text=Messages", "text=My Profile", "text=Post RFQ", "text=Hi ", "text=Logout"]
        for page in reversed(context.pages):
            try:
                if page.is_closed():
                    continue
                url = page.url or ""
                if "login" not in url and ("buyer." in url or "my.indiamart" in url):
                    return True
                for selector in success:
                    loc = page.locator(selector)
                    if loc.count() and loc.first.is_visible():
                        return True
            except Exception:
                continue
        return False

    def _first_visible(self, page, selectors: list[str]):
        for selector in selectors:
            try:
                loc = page.locator(selector)
                if loc.count() and loc.first.is_visible():
                    return loc.first
            except Exception:
                continue
        return None

    def _first_visible_within(self, root, selectors: list[str]):
        for selector in selectors:
            try:
                loc = root.locator(selector)
                if loc.count() and loc.first.is_visible():
                    return loc.first
            except Exception:
                continue
        return None

    def _click_first(self, page, selectors: list[str]) -> bool:
        loc = self._first_visible(page, selectors)
        if loc is None:
            return False
        try:
            loc.click(timeout=5000)
            return True
        except Exception:
            return False

    def _findings(self, summary: dict[str, Any], diagnostics: dict[str, Any], executed: list[dict[str, Any]]) -> list[str]:
        counts = self._case_counts(executed)
        findings = [
            f"Loaded page title: {summary.get('title') or '-'}",
            f"Detected {len(summary.get('headings') or [])} headings, {len(summary.get('forms') or [])} forms, and {len(summary.get('buttons') or [])} CTA or clickable candidates.",
            f"Executed {len(executed)} exploratory case(s): {counts['Pass']} passed, {counts['Fail']} failed, {counts['Needs Review']} need review, {counts['Skipped']} skipped.",
        ]
        if summary.get("headings"):
            findings.append(f"Primary heading snapshot: {', '.join((summary.get('headings') or [])[:3])}")
        if diagnostics.get("interceptors"):
            findings.append("Popup or overlay-like elements are present and may affect automated flows.")
        return findings

    def _human_required(self, summary: dict[str, Any], diagnostics: dict[str, Any], executed: list[dict[str, Any]]) -> list[str]:
        blob = " ".join([summary.get("title") or "", summary.get("pageText") or ""]).lower()
        interventions = []
        for term, message in [("captcha", "Human intervention is likely needed for CAPTCHA or bot checks."), ("payment", "Human review is recommended before automating payment or checkout."), ("upload", "Human input may be needed to confirm file uploads."), ("password", "Human input may be needed for password-based login.")]:
            if term in blob:
                interventions.append(message)
        for case in executed:
            if case.get("status") == "Needs Review":
                interventions.append(f"{case.get('title')}: {case.get('details')}")
        if diagnostics.get("interceptors"):
            interventions.append("Popup or overlay behavior should be reviewed by a person if it blocks the intended journey.")
        deduped = []
        for item in interventions:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _write_report(self, summary: dict[str, Any]) -> Path:
        extra = summary.get("extra", {}) or {}
        cases = extra.get("test_cases", [])
        counts = extra.get("case_counts", {})
        rows = "".join(
            f"<tr><td>{self._escape(c.get('title', ''))}</td><td>{self._escape(c.get('objective', ''))}</td><td>{self._escape(c.get('status', ''))}</td><td>{self._escape(c.get('details', ''))}</td><td><code>{self._escape(c.get('screenshot', ''))}</code></td></tr>"
            for c in cases
        )
        findings = "".join(f"<li>{self._escape(x)}</li>" for x in extra.get("findings", []))
        human = "".join(f"<li>{self._escape(x)}</li>" for x in extra.get("human_required", []))
        report = REPORTS_DIR / f"url_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report.write_text(
            f"""
            <html><head><style>
            body {{ font-family: Arial, sans-serif; margin: 24px; color: #0f172a; background: #f8fafc; }}
            .card {{ background: white; border: 1px solid #dbe3ee; border-radius: 14px; padding: 16px; margin-bottom: 16px; }}
            .grid {{ display:grid; grid-template-columns: repeat(5,1fr); gap:12px; margin-bottom:16px; }}
            .metric {{ background:#f8fafc; border:1px solid #dbe3ee; border-radius:12px; padding:12px; }}
            .label {{ color:#64748b; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
            .value {{ font-size:24px; font-weight:800; margin-top:6px; }}
            table {{ border-collapse: collapse; width:100%; }} th,td {{ border:1px solid #dbe3ee; padding:8px 10px; text-align:left; vertical-align:top; }}
            th {{ background:#0f172a; color:white; }} code {{ background:#e2e8f0; padding:2px 4px; border-radius:4px; }}
            </style></head><body>
            <h1>AI URL Agent Report</h1>
            <div class="card">
              <p><b>URL:</b> <code>{self._escape(extra.get('url', ''))}</code></p>
              <p><b>Status:</b> {self._escape(summary.get('status', ''))}</p>
              <p><b>Page Title:</b> {self._escape((extra.get('page_summary') or {}).get('title', ''))}</p>
              <p><b>Login Phone Used:</b> <code>{self._escape(extra.get('login_phone', ''))}</code></p>
              <p><b>Screenshot:</b> <code>{self._escape(extra.get('screenshot_path', ''))}</code></p>
            </div>
            <div class="grid">
              <div class="metric"><div class="label">Executed</div><div class="value">{len(cases)}</div></div>
              <div class="metric"><div class="label">Passed</div><div class="value">{counts.get('Pass', 0)}</div></div>
              <div class="metric"><div class="label">Failed</div><div class="value">{counts.get('Fail', 0)}</div></div>
              <div class="metric"><div class="label">Needs Review</div><div class="value">{counts.get('Needs Review', 0)}</div></div>
              <div class="metric"><div class="label">Skipped</div><div class="value">{counts.get('Skipped', 0)}</div></div>
            </div>
            <div class="card"><h2>Overall Page Assessment</h2><ul>{findings or '<li>No findings captured.</li>'}</ul></div>
            <div class="card"><h2>Executed Exploratory Cases</h2><table><tr><th>Test Case</th><th>Objective</th><th>Status</th><th>Execution Details</th><th>Screenshot</th></tr>{rows or '<tr><td colspan="5">No test cases executed.</td></tr>'}</table></div>
            <div class="card"><h2>Human Intervention</h2><ul>{human or '<li>No immediate human intervention detected.</li>'}</ul></div>
            <div class="card"><h2>Diagnostics Snapshot</h2><pre>{self._escape(json.dumps(extra.get('diagnostics', {}), indent=2))}</pre></div>
            </body></html>
            """,
            encoding="utf-8",
        )
        return report

    def _case_counts(self, executed: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"Pass": 0, "Fail": 0, "Needs Review": 0, "Skipped": 0}
        for case in executed:
            status = case.get("status") or "Skipped"
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _safe_links(self, links: list[dict[str, Any]], url: str) -> list[dict[str, Any]]:
        host = urlparse(url).netloc
        risky = {"login", "sign in", "logout", "delete", "remove", "payment", "checkout", "buy", "order"}
        result = []
        for link in links:
            href = (link.get("href") or "").strip()
            text = (link.get("text") or "").strip().lower()
            if not href:
                continue
            target_host = urlparse(href).netloc
            if target_host and target_host != host:
                continue
            if any(word in text for word in risky):
                continue
            result.append(link)
        return result

    def _safe_ctas(self, buttons: list[dict[str, Any]]) -> list[dict[str, Any]]:
        risky = {"logout", "delete", "remove", "payment", "checkout", "buy now", "cancel"}
        good = {"contact", "quote", "details", "view", "explore", "search", "send", "submit", "get", "next"}
        result = []
        for button in buttons:
            text = (button.get("text") or "").strip().lower()
            if not text or any(word in text for word in risky):
                continue
            if any(word in text for word in good) or button.get("href"):
                result.append(button)
        return result

    def _sample_value(self, blob: str, input_type: str) -> str:
        if input_type == "email" or "email" in blob:
            return "qa.agent@example.com"
        if input_type == "tel" or "mobile" in blob or "phone" in blob:
            return DEFAULT_LOGIN_PHONE
        if "otp" in blob:
            return DEFAULT_LOGIN_OTP
        if "qty" in blob or "quantity" in blob:
            return "10"
        if "city" in blob:
            return "Noida"
        if "name" in blob:
            return "QA Agent"
        return "Automated Input"

    @staticmethod
    def _module_name(url: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", re.sub(r"^https?://", "", url).strip("/"))[:80] or "page_audit"

    @staticmethod
    def _artifact_dir(url: str) -> Path:
        target = RUNS_DIR / f"url_agent_{URLAuditAgent._module_name(url)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _escape(value: Any) -> str:
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
