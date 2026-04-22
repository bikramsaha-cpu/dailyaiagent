# Modern UI Architecture

This project now supports a modern split architecture without changing the existing automation core:

- `backend/`
  FastAPI layer that wraps the current Python services.
- `frontend/`
  Next.js dashboard shell for operators.
- `ui/`
  Existing Streamlit app, kept intact for gradual migration.

## Why this approach

- Existing runners in `PBR/`, `enq/`, `bmc/`, and other modules stay unchanged.
- Existing shared services in `core/` remain the system of record.
- The new API and frontend only orchestrate and display the same data.

## Backend

Start the API locally:

```bash
uvicorn backend.main:app --reload --port 8000
```

Available endpoints:

- `GET /api/health`
- `GET /api/status`
- `GET /api/modules`
- `GET /api/modules/{module_id}`
- `POST /api/modules/{module_id}/run`
- `GET /api/runs`
- `GET /api/sheets/tabs`
- `GET /api/sheets/records`
- `GET /api/diagnostics/healings`
- `GET /api/diagnostics/steps`
- `POST /api/url-agent/run`
- `POST /api/testlink/generate`

## Frontend

Install and run:

```bash
cd frontend
npm install
npm run dev
```

Set the backend URL when needed:

```bash
API_SERVER_URL=http://127.0.0.1:8000
```

The frontend now proxies API calls through Next.js, so browser requests go to `/api/proxy/*` and the proxy forwards them to the FastAPI server.

## Migration path

1. Keep Streamlit available for day-to-day use.
2. Expand the new React UI feature by feature.
3. Move advanced screens like URL Agent, TestLink Generator, and diagnostics into the Next.js app.
4. Retire Streamlit only after parity is good enough for the team.
