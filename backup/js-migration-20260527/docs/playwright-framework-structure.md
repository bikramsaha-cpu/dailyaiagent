# Modern Playwright Framework Structure

This project now has one active automation framework folder: `playwright-framework/`.

The implementation is Python Playwright with pytest because the current Daily QA Agent backend and frontend runner are Python-based. The layout mirrors a modern Playwright framework and avoids duplicate root-level `framework/` and `tests/` folders.

## Locator Healing Layer

Locator healing is provided by the shared `core/` package and is attached automatically by the pytest `page` fixture.

```text
playwright-framework/tests/conftest.py
  page fixture
    -> context.new_page()
    -> core.healing.attach_healing(...)
    -> returns HealingPage to tests and page objects

core/
  healing.py               LocatorHealer, HealingPage, HealingLocator
  locator_registry.py      Stores successful healed selectors
  browser_diagnostics.py   Captures page URL/title/text/HTML, overlays, and candidate elements
  llm_client.py            Optional LLM selector suggestions
  store.py                 Records healing attempts in SQLite

artifacts/
  locator_registry.json    Reused healed selectors
```

When a page object calls `page.locator(...).click()`, `page.click(...)`, `page.fill(...)`, `page.select_option(...)`, or `page.wait_for_selector(...)`, the wrapper first tries the normal selector. If that fails, the healer tries the registry, selector variants, role/text candidates, intent candidates, optional LLM suggestions, and DOM-scored candidates. Successful heals are saved in `artifacts/locator_registry.json` and recorded through `ExecutionStore.record_locator_healing()`.

This is why tests such as:

```python
enquiry_form = EnquiryForm(page, **page_context)
```

already receive healing support. The `page` fixture supplies a `HealingPage`; page objects do not need to instantiate the healer manually.

## Active Layout

```text
playwright-framework/
  tests/
    enq/
      smoke/
      regress/
    pbr/
      smoke/
      regress/
    bmc/
      smoke/
      regress/
  pages/
    base_page.py
    login_page.py
    enq/
    pbr/
    bmc/
  fixtures/
  utils/
    google.py
    helper.py
    random_data.py
    api_utils.py
  test_data/
    config.py
    users.json
    config.json
  locators/
    enq_locators.py
  hooks/
    before_each.py
    after_each.py
  api/
    auth_api.py
  reports/
    html-report/
    allure-results/
  screenshots/
  videos/
  traces/
  .env.example
  package.json
  README.md
```

## Operational Modules

Only these modules are exposed in `automation_modules.json` and therefore in the frontend:

- ENQ
- PBR
- BMC

Current status:

- ENQ runs from `playwright-framework/tests/enq` using modern POM.
- PBR remains operational through `PBR/run_all.py` until migrated into `playwright-framework/tests/pbr`.
- BMC remains operational through `bmc/run_all.py` until migrated into `playwright-framework/tests/bmc`.

## Auth Standard

All framework auth uses the working BMC buyer login flow:

- URL: `https://buyer.indiamart.com/login`
- Storage state: `artifacts/sessions/bmc/bmclogin.json`
- Config envs: `AUTOMATION_BMC_LOGIN_PHONE`, `AUTOMATION_BMC_LOGIN_OTP`, `AUTOMATION_AUTH_SESSION_FILE`

ENQ logged-in tests also consume this shared BMC auth storage state.

## Frontend Flow

The frontend starts modules through the backend:

```text
frontend -> backend -> run_module_task.py -> automation_modules.json -> module run_all.py
```

For ENQ, `enq/run_all.py` is now a thin wrapper that runs pytest against `playwright-framework/tests/enq`.

## Backup Policy

Inactive modules and old script-style code live under:

```text
backup/
  original_configs/automation_modules.full.json
  legacy_modules/
```

Do not add new active tests under backup or old module folders.

## Google Sheet Performance

`core/google_logger.py` now caches the gspread client, spreadsheet, worksheet objects, and sheet records in-process. This avoids repeated Google auth/open/read calls during module runs and makes dashboard refreshes faster.

Execution tabs should use this header order:

```text
Test Title | Test Step | Status | Remarks | Browser | Phone | Date | Time
```

`Test Title` is the test file name, for example `test_pdp_enquiry.py`, so one file is treated as one test case in the portal. `Test Step` stores each Playwright step under that case. If an old tab still has `Test Title | Status | Remarks | Browser | Phone | Date | Time`, the logger upgrades it by inserting `Test Step` after `Test Title` during the next write.

The frontend keeps all execution filters above the table. Use `Sync Sheet` to force a fresh Google Sheet read; module runs also trigger this refresh automatically when execution completes.

## Commands

```bash
python -m pytest playwright-framework/tests/enq/smoke --browser chromium --collect-only
python enq/run_all.py --skip-login --browser chromium
python run_module_task.py --module-id enq --headed
```

## Healing Troubleshooting

- If healing is not triggered, confirm the test uses the pytest `page` fixture from `playwright-framework/tests/conftest.py`.
- If a raw Playwright page is created manually, wrap it with `attach_healing(page, suite_name=..., module_name=..., test_name=...)`.
- If LLM suggestions are expected, configure `AUTOMATION_LLM_API_KEY`, `AUTOMATION_LLM_BASE_URL`, and `AUTOMATION_LLM_MODEL`.
- If a locator heals repeatedly, update the page object with the new stable selector instead of relying on healing forever.

## Migration Rule

When migrating PBR or BMC, create tests and page objects inside `playwright-framework/` first, then reduce the module folder to a thin `run_all.py` wrapper, like ENQ.
