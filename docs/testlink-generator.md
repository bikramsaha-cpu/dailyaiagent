## TestLink Generator

Use `run_testlink_generator.py` to fetch manual test cases from TestLink and generate Playwright Python tests into a module-specific folder inside this repo.

### Required environment variables

- `AUTOMATION_TESTLINK_API_KEY`
- `AUTOMATION_LLM_API_KEY`

Optional:

- `AUTOMATION_TESTLINK_URL`
- `AUTOMATION_TESTLINK_CA_BUNDLE`
- `AUTOMATION_TESTLINK_INSECURE_SKIP_VERIFY`
- `AUTOMATION_LLM_BASE_URL`
- `AUTOMATION_LLM_MODEL`

### Example

```powershell
python run_testlink_generator.py --module bmc --suite-id 344132
```

Default output folders:

- If `<module>/testscript` exists: `<module>/testscript/generated_from_testlink`
- Otherwise: `<module>/generated_from_testlink`

Useful flags:

- `--overwrite`
- `--max-cases 5`
- `--output-dir <custom-path>`
