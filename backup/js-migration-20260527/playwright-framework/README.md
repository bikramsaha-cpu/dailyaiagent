# Daily QA Agent Playwright Framework

This is the single active automation framework area for the portal.

The project currently runs Python Playwright through pytest because the Daily QA Agent backend and frontend module runner are Python-based. The folder layout mirrors a modern Playwright framework so ENQ, PBR, and BMC can be migrated module by module without spreading test assets across the repository.

## Structure

```text
playwright-framework/
  tests/        Module specs split into smoke and regress
  pages/        Page object models
  fixtures/     Shared fixture helpers
  utils/        Utility helpers
  test_data/    Environment-backed data/config
  locators/     Shared selectors
  hooks/        Reusable lifecycle hooks
  api/          API clients/helpers
  reports/      Framework reports
  screenshots/  Failure screenshots
  videos/       Optional videos
  traces/       Playwright traces
```

## Active Modules

- ENQ: modern POM tests under `tests/enq/smoke` and `tests/enq/regress`
- PBR: active legacy runner under `../PBR/run_all.py`
- BMC: active legacy runner under `../bmc/run_all.py`

Only ENQ, PBR, and BMC are listed in the frontend module registry.

## Commands

```bash
python -m pytest playwright-framework/tests/enq/smoke --browser chromium --collect-only
python enq/run_all.py --skip-login --browser chromium
python run_module_task.py --module-id enq --headed
```
