# E2E Agent Workflow

This repo now includes a reusable E2E agent runner for browser automation.

## What it gives you

- Declarative flow files in JSON
- Playwright-driven browser execution
- Locator healing through the existing healing engine
- Automatic screenshots and diagnostics on failure
- CDP-backed debug metadata when `AUTOMATION_DEVTOOLS_ENABLED=1`
- Run summaries stored in `artifacts/execution.db`
- HTML reports written to `artifacts/reports`

## Run it

```powershell
python run_e2e_agent.py --flow flows/sample_e2e_flow.json
```

`flows/sample_e2e_flow.json` is a stable smoke sample for `example.com`.

If you want to start from a real site and first capture evidence before adding assertions, use:

```powershell
python run_e2e_agent.py --flow flows/indiamart_home_debug.json
```

## Flow format

Top-level fields:

- `suite_name`: report grouping name
- `module_name`: logical flow name
- `base_url`: optional base URL variable
- `start_url`: page opened before steps run
- `browsers`: `chromium`, `firefox`, or both
- `headless`: browser mode
- `slow_mo`: slow motion delay in milliseconds
- `storage_state`: optional Playwright auth state file
- `variables`: string variables for `${...}` interpolation
- `context_options`: passed to `browser.new_context(...)`
- `steps`: ordered actions

Supported step actions:

- `goto`
- `click`
- `fill`
- `press`
- `wait_for`
- `select`
- `assert_text`
- `assert_url`
- `screenshot`
- `evaluate`

Locator-capable steps can use:

- `selector`
- `selectors`
- `role`
- `role_name`
- `text`
- `exact`
- `metadata.intent`

## Example

```json
{
  "suite_name": "Buyer Journey",
  "module_name": "login_and_search",
  "base_url": "https://www.indiamart.com",
  "start_url": "${base_url}",
  "browsers": ["chromium"],
  "storage_state": "../enq/auth.json",
  "steps": [
    {
      "name": "Open login CTA",
      "action": "click",
      "selector": "a.login-btn",
      "selectors": ["text=Sign In", "[data-click='login']"],
      "metadata": {
        "intent": "open login"
      }
    },
    {
      "name": "Search input",
      "action": "fill",
      "selector": "input[type='search']",
      "value": "steel pipes"
    },
    {
      "name": "Submit search",
      "action": "press",
      "selector": "input[type='search']",
      "key": "Enter"
    },
    {
      "name": "Wait for results",
      "action": "assert_url",
      "expects_url": "**/search*.html*"
    }
  ]
}
```

## MCP alignment

The runner is built so the workflow layer is separate from browser-specific debugging:

- Playwright executes the user flow.
- `core/browser_diagnostics.py` captures browser state and uses CDP when Chromium is available.
- The same flow contract can later be wired to a Playwright MCP server and Chrome DevTools MCP server without changing the JSON flow shape.

This workspace does not currently include MCP server configuration, so the implementation here uses local Playwright plus CDP-backed diagnostics as the execution engine.

If you want to move fully to MCP next, the clean next step is adding a transport adapter layer that maps these same actions to MCP tool calls instead of local Playwright calls.
