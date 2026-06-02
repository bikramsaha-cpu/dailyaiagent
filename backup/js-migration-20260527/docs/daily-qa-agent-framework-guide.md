# Daily QA Agent Framework Guide

This document explains the current Daily QA Agent automation structure, how the framework is organized, and how to execute tests from command line or through the module runner.

## 1. Project Overview

`daily-qa-agent` is an automation workspace for running buyer-side QA modules such as ENQ, PBR, and BMC. The active modern automation framework is kept inside:

```text
playwright-framework/
```

The framework uses:

- Python
- pytest
- Playwright sync API
- Page Object Model
- environment-based test data
- module wrappers for dashboard/backend execution
- Google Sheet logging for execution results

The current active module status is:

| Module | Status | Runner |
| --- | --- | --- |
| ENQ | Modern Playwright pytest framework | `enq/run_all.py` |
| PBR | Existing legacy module runner | `PBR/run_all.py` |
| BMC | Existing legacy module runner | `bmc/run_all.py` |

## 2. Root Folder Structure

```text
daily-qa-agent/
  automation_modules.json        Module registry used by backend/frontend
  pytest.ini                     pytest discovery and marker config
  requirements.txt               Python dependencies
  run_module_task.py             Common module execution entry point
  run_e2e_agent.py               E2E agent entry point
  run_testlink_generator.py      TestLink generation entry point
  run_url_agent.py               URL diagnostics/agent entry point

  backend/                       FastAPI backend
  frontend/                      Next.js dashboard UI
  core/                          Shared runner, reporting, settings, store, mailer
    healing.py                   Locator healing engine
    locator_registry.py          Stores healed selectors for reuse
    browser_diagnostics.py       Captures DOM/page diagnostics for healing
    llm_client.py                Optional LLM selector suggestion client
    store.py                     SQLite execution and healing history
  docs/                          Project documentation
  artifacts/                     Runtime output, sessions, reports, summaries

  playwright-framework/          Main modern Playwright pytest framework
  enq/                           ENQ module wrapper
  PBR/                           PBR module wrapper
  bmc/                           BMC module wrapper
  backup/                        Old/legacy inactive code backup
```

## 3. Playwright Framework Structure

```text
playwright-framework/
  api/
    auth_api.py                  API helper/client area

  fixtures/
    __init__.py                  Shared fixture package placeholder

  hooks/
    before_each.py               Reusable pre-test hook area
    after_each.py                Reusable post-test hook area

  locators/
    enq_locators.py              Shared ENQ selectors

  pages/
    base_page.py                 Common page object behavior
    login_page.py                Login page object
    enq/
      search_page.py             ENQ search page object
      pdp_page.py                ENQ PDP page object
      dir_page.py                ENQ DIR page object
      company_page.py            ENQ company page object
      enquiry_form.py            Shared enquiry form object
    pbr/                         Future PBR page objects
    bmc/                         Future BMC page objects

  test_data/
    config.py                    Environment-backed config values
    config.json                  Static config data
    users.json                   User/test data

  tests/
    conftest.py                  pytest options, browser/page fixtures, reporting hooks
    enq/
      smoke/                     Critical ENQ smoke tests
      regress/                   Broader ENQ regression tests

  utils/
    api_utils.py                 API utility helpers
    google.py                    Google Sheet logger builder
    helper.py                    Common helper functions
    random_data.py               Random test data helpers

  reports/                       Framework reports
  screenshots/                   Failure screenshots
  traces/                        Playwright traces
  videos/                        Optional videos
  .env.example                   Framework-level env reference
  package.json                   Optional npm script shortcuts
  README.md                      Short framework summary
```

## 4. Execution Flow

### 4.1 Dashboard/backend module flow

The dashboard starts module execution through this chain:

```text
frontend -> backend -> run_module_task.py -> automation_modules.json -> module run_all.py
```

For ENQ:

```text
run_module_task.py --module-id enq
  -> automation_modules.json
  -> enq/run_all.py
  -> pytest playwright-framework/tests/enq
```

### 4.2 Direct pytest flow

Direct pytest execution uses:

```text
pytest.ini
  -> playwright-framework/tests/conftest.py
  -> page fixture wraps Playwright page with core.healing.attach_healing
  -> selected test files
  -> page objects
  -> page.locator/click/fill/select_option can self-heal when selector fails
  -> Google logger/report summary
```

## 5. Locator Healing Structure

Locator healing is part of the shared `core/` layer, not inside individual ENQ page objects.

```text
core/
  healing.py               Main healing engine
  locator_registry.py      JSON registry of selectors that were healed successfully
  browser_diagnostics.py   Page snapshot, visible text, HTML, overlay, and candidate element collection
  llm_client.py            Optional OpenAI-compatible LLM client for selector suggestions
  store.py                 Saves healing attempts in the SQLite execution DB

artifacts/
  locator_registry.json    Reusable healed selector cache
  daily_qa_agent.sqlite    Execution runs, step events, and locator healing history
```

### 5.1 How healing is attached

The pytest `page` fixture in `playwright-framework/tests/conftest.py` creates a normal Playwright page and wraps it with:

```python
healing_page = attach_healing(
    context.new_page(),
    suite_name="ENQ",
    module_name=module_name,
    test_name=request.node.name,
)
```

That means tests and page objects receive a `HealingPage`, not the raw Playwright page.

Example from a test:

```python
def test_dir_enquiry(page, page_context):
    enquiry_form = EnquiryForm(page, **page_context)
```

Here `page` already includes healing. The page object does not need to create the healer manually.

### 5.2 What actions can heal

Healing is applied when code uses these page methods:

```python
page.locator(selector).click()
page.locator(selector).fill(value)
page.locator(selector).select_option(value)
page.click(selector)
page.fill(selector, value)
page.select_option(selector, value)
page.wait_for_selector(selector)
```

If the original selector works, the action runs normally. If it fails, the healing engine tries alternate selector strategies before failing the test.

### 5.3 Healing resolution order

When a selector breaks, `LocatorHealer.resolve()` tries:

1. Previously healed selector from `artifacts/locator_registry.json`.
2. Original selector and expanded selector variants.
3. Role-based candidates, such as button/link names.
4. Text-based candidates.
5. Intent-specific candidates, especially contact-supplier/enquiry CTAs.
6. Optional LLM-generated selectors when `AUTOMATION_LLM_API_KEY`, `AUTOMATION_LLM_BASE_URL`, and `AUTOMATION_LLM_MODEL` are configured.
7. DOM-scored candidates from the current page snapshot.

If a good selector is found, it is saved for the next run.

### 5.4 What healing records

Successful and unresolved healing attempts are written through `ExecutionStore.record_locator_healing()`.

The stored data includes:

- suite name
- module name
- test name
- locator name
- previous selector
- chosen selector
- healing strategy
- page URL/title
- HTML snapshot
- diagnostics and evidence

The backend can list recent healing records through `core/api_services.py` using `list_locator_healings()`.

### 5.5 How to write selectors for better healing

Healing works best when page objects provide meaningful selectors and intent metadata.

Basic usage:

```python
self.page.locator("button:has-text('Contact Supplier')").click()
```

Better usage when the selector is fragile:

```python
self.page.click(
    "[data-click='CTAContactSupplier']",
    intent="click contact supplier CTA",
    text="Contact Supplier",
    keywords=["contact", "supplier", "enquiry"],
)
```

Keep this rule in mind:

- Page objects should still contain the best known selector.
- Healing is a recovery layer, not a replacement for clean locators.
- When a selector heals repeatedly, update the page object with the better stable selector.

## 6. Environment Setup

Run all commands from the project root:

```powershell
cd C:\Users\Imart\daily-qa-agent
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Install Playwright browser binaries:

```powershell
python -m playwright install
```

Create a local environment file from the example:

```powershell
Copy-Item .env.example .env
```

Fill required values in `.env`, especially login, browser, Google logging, SMTP, and LLM values if those integrations are needed.

## 7. Important Environment Variables

| Variable | Purpose |
| --- | --- |
| `AUTOMATION_HEADLESS` | `1` for headless browser, `0` for visible browser |
| `AUTOMATION_SLOW_MO` | Slow down browser actions in milliseconds |
| `AUTOMATION_BROWSERS` | Comma-separated browser list, for example `chromium,firefox` |
| `AUTOMATION_DEFAULT_LOGIN_PHONE` | Default buyer login phone |
| `AUTOMATION_DEFAULT_LOGIN_OTP` | Default login OTP |
| `AUTOMATION_BMC_LOGIN_PHONE` | BMC login phone used for shared auth |
| `AUTOMATION_BMC_LOGIN_OTP` | BMC login OTP |
| `AUTOMATION_BMC_SESSION_FILE` | BMC storage state path |
| `AUTOMATION_AUTH_SESSION_FILE` | Shared auth storage state path |
| `AUTOMATION_ENQ_SEARCH_TERM` | ENQ search page product keyword |
| `AUTOMATION_ENQ_ALL_INDIA_SEARCH_TERM` | ENQ all-India search keyword |
| `AUTOMATION_ENQ_IMPCAT_URL` | ENQ DIR/MCAT page URL |
| `AUTOMATION_ENQ_PDP_URL` | ENQ PDP URL |
| `AUTOMATION_ENQ_COMPANY_URL` | ENQ company page URL |
| `AUTOMATION_GOOGLE_LOGGING_ENABLED` | Enable/disable Google Sheet logging |
| `AUTOMATION_GOOGLE_CREDENTIALS` | Path to Google credentials file |
| `AUTOMATION_GOOGLE_CREDENTIALS_JSON` | Google credentials JSON content |
| `AUTOMATION_SMTP_*` | Email summary configuration |
| `AUTOMATION_LLM_API_KEY` | Enables optional LLM selector healing suggestions |
| `AUTOMATION_LLM_BASE_URL` | OpenAI-compatible LLM base URL |
| `AUTOMATION_LLM_MODEL` | LLM model used for selector suggestions |

## 8. Authentication Flow

Logged-in ENQ tests use the shared BMC auth storage state by default.

Default session path:

```text
artifacts/sessions/bmc/bmclogin.json
```

Generate or refresh the auth session:

```powershell
python -m pytest playwright-framework/tests/enq/smoke/test_auth.py --browser chromium --headed
```

After the session file exists, logged-in tests can reuse it.

## 9. Execution Commands

### 9.1 Collect tests without running

```powershell
python -m pytest playwright-framework/tests/enq/smoke --browser chromium --collect-only
```

### 9.2 Run all ENQ tests through pytest

```powershell
python -m pytest playwright-framework/tests/enq --browser chromium
```

### 9.3 Run ENQ smoke tests

```powershell
python -m pytest playwright-framework/tests/enq/smoke --browser chromium
```

### 9.4 Run ENQ regression tests

```powershell
python -m pytest playwright-framework/tests/enq/regress --browser chromium
```

### 9.5 Run one ENQ test file

```powershell
python -m pytest playwright-framework/tests/enq/smoke/test_dir_enquiry.py --browser chromium
```

### 9.6 Run tests in headed mode

```powershell
python -m pytest playwright-framework/tests/enq/smoke/test_dir_enquiry.py --browser chromium --headed
```

### 9.7 Run with slow motion

```powershell
python -m pytest playwright-framework/tests/enq/smoke/test_dir_enquiry.py --browser chromium --headed --slow-mo 500
```

### 9.8 Run on multiple browsers

```powershell
python -m pytest playwright-framework/tests/enq --browser chromium --browser firefox
```

### 9.9 Run ENQ through module wrapper

```powershell
python enq/run_all.py --skip-login --browser chromium
```

Run with login step:

```powershell
python enq/run_all.py --browser chromium --headed
```

Run a selected test through the ENQ wrapper:

```powershell
python enq/run_all.py --skip-login --browser chromium playwright-framework/tests/enq/smoke/test_dir_enquiry.py
```

### 9.10 Run ENQ through common module runner

```powershell
python run_module_task.py --module-id enq
```

Run headed:

```powershell
python run_module_task.py --module-id enq --headed
```

Run selected tests:

```powershell
python run_module_task.py --module-id enq --tests playwright-framework/tests/enq/smoke/test_dir_enquiry.py
```

### 9.11 Run PBR and BMC modules

```powershell
python run_module_task.py --module-id pbr
python run_module_task.py --module-id bmc
```

Direct runners:

```powershell
python PBR/run_all.py
python bmc/run_all.py
```

## 10. pytest Markers

Markers are configured in `pytest.ini`.

| Marker | Meaning |
| --- | --- |
| `enq` | ENQ module test |
| `auth` | Login/session setup test |
| `loggedin` | Test requires saved authenticated storage state |
| `module(name)` | Module area inside the suite |
| `smoke` | Critical smoke coverage |
| `regression` | Broader regression coverage |

Example:

```python
@pytest.mark.enq
@pytest.mark.smoke
@pytest.mark.loggedin
@pytest.mark.module("DIR")
def test_dir_enquiry(page, page_context):
    ...
```

Run by marker:

```powershell
python -m pytest playwright-framework/tests/enq -m "enq and smoke" --browser chromium
```

## 11. Page Object Pattern

Tests should stay clean and readable. Business flow and selectors should live in page objects.

Recommended test style:

```python
def test_dir_enquiry(page, page_context):
    dir_page = DirPage(page, **page_context)
    enquiry_form = EnquiryForm(page, **page_context)

    dir_page.open()
    dir_page.click_supplier_cta()
    enquiry_form.submit_enquiry()
```

Recommended placement:

| Item | Location |
| --- | --- |
| Test scenario | `playwright-framework/tests/<module>/<suite>/test_*.py` |
| Page actions | `playwright-framework/pages/<module>/*.py` |
| Shared form actions | `playwright-framework/pages/<module>/enquiry_form.py` |
| Shared selectors | `playwright-framework/locators/*.py` |
| Config/test data | `playwright-framework/test_data/config.py` |
| Reusable helpers | `playwright-framework/utils/*.py` |

## 12. Adding a New ENQ Test

1. Add the test file under the correct suite:

```text
playwright-framework/tests/enq/smoke/test_new_flow.py
```

or:

```text
playwright-framework/tests/enq/regress/test_new_flow.py
```

2. Add or reuse page object methods under:

```text
playwright-framework/pages/enq/
```

3. Add selectors to:

```text
playwright-framework/locators/enq_locators.py
```

4. Add configurable data in:

```text
playwright-framework/test_data/config.py
```

5. Mark the test properly:

```python
@pytest.mark.enq
@pytest.mark.smoke
@pytest.mark.loggedin
@pytest.mark.module("Search")
```

6. Run the test directly:

```powershell
python -m pytest playwright-framework/tests/enq/smoke/test_new_flow.py --browser chromium --headed
```

## 13. Reports and Runtime Output

Runtime files are written under:

```text
artifacts/
```

Important output locations:

| Output | Location |
| --- | --- |
| ENQ pytest summary JSON | `artifacts/runs/enq_pytest_summary.json` |
| Auth/session state | `artifacts/sessions/` |
| Healed selector cache | `artifacts/locator_registry.json` |
| Healing history | SQLite DB through `core.store.ExecutionStore` |
| HTML run report | generated by `core.reporting.write_html_report` |
| Screenshots/traces/videos | `playwright-framework/screenshots`, `traces`, `videos` |
| Dashboard run history | recorded through `core.store.ExecutionStore` |

ENQ wrapper execution also records a portal summary and sends email when SMTP is configured.

## 14. Google Sheet Logging

ENQ tests build the logger from:

```text
playwright-framework/utils/google.py
```

Config values come from:

```text
playwright-framework/test_data/config.py
```

Expected sheet columns:

```text
Test Title | Test Step | Status | Remarks | Browser | Phone | Date | Time
```

`Test Title` is usually the test file name. `Test Step` stores each logged step under that test case.

## 15. Frontend and Backend

Backend:

```powershell
uvicorn backend.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses the backend to trigger module runs. Module definitions come from:

```text
automation_modules.json
```

## 16. Best Practices

- Keep test files short and scenario-focused.
- Put browser actions inside page objects.
- Do not duplicate selectors inside tests.
- Put configurable URLs, phones, OTPs, and search terms in environment/config files.
- Use `--headed` and `--slow-mo` only for debugging.
- Run `test_auth.py` first when the shared auth session is missing.
- Add new migrated modules inside `playwright-framework/` before replacing old module wrappers.
- Keep old or inactive code inside `backup/`; do not add new active tests there.
- Use markers consistently so smoke/regression runs stay predictable.
- Treat healing records as feedback; update page object selectors when the same locator heals repeatedly.

## 17. Common Troubleshooting

### Session file not found

Run:

```powershell
python -m pytest playwright-framework/tests/enq/smoke/test_auth.py --browser chromium --headed
```

### Browser binaries missing

Run:

```powershell
python -m playwright install
```

### Tests are running on unexpected browsers

Check:

```text
AUTOMATION_BROWSERS
```

or pass browsers explicitly:

```powershell
python -m pytest playwright-framework/tests/enq --browser chromium
```

### Google logging fails

Check these values:

```text
AUTOMATION_GOOGLE_LOGGING_ENABLED
AUTOMATION_GOOGLE_CREDENTIALS
AUTOMATION_GOOGLE_CREDENTIALS_JSON
AUTOMATION_ENQ_SHEET_NAME
AUTOMATION_ENQ_SHEET_TAB
```

### Login values are not picked up

Check:

```text
AUTOMATION_DEFAULT_LOGIN_PHONE
AUTOMATION_DEFAULT_LOGIN_OTP
AUTOMATION_BMC_LOGIN_PHONE
AUTOMATION_BMC_LOGIN_OTP
AUTOMATION_AUTH_SESSION_FILE
```

### Healing is not happening

Check that the test uses the pytest-provided `page` fixture. Healing is attached in `playwright-framework/tests/conftest.py`; manually created raw Playwright pages will not be wrapped unless `attach_healing()` is called.

Also check that the page object calls healing-aware methods such as `page.locator(...).click()`, `page.click(...)`, `page.fill(...)`, or `page.wait_for_selector(...)`.

### LLM healing is not suggesting selectors

LLM healing is optional. It runs only when these values are configured:

```text
AUTOMATION_LLM_API_KEY
AUTOMATION_LLM_BASE_URL
AUTOMATION_LLM_MODEL
```

Without these values, deterministic healing still runs through registry, selector variants, role/text, intent, and DOM candidates.

## 18. Migration Rule for PBR and BMC

When PBR or BMC is migrated to the modern framework:

1. Create tests under `playwright-framework/tests/<module>/`.
2. Create page objects under `playwright-framework/pages/<module>/`.
3. Add shared locators under `playwright-framework/locators/`.
4. Keep the module-level `run_all.py` as a thin wrapper.
5. Keep `automation_modules.json` pointing to the wrapper.

This keeps dashboard execution stable while the implementation moves into the modern framework.
