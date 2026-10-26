# SON Panel REST API - usage

## Configuration (.env)

- `SON_LOGIN` - SON panel login (email)
- `SON_PASSWORD` - SON panel password
- `SON_PANEL_URL` - panel URL (e.g. https://your-panel.example.com)
- `SON_OUT_DIR` - output directory (default ./invoices)
- `API_HOST` - bind host (default 127.0.0.1; use 0.0.0.0 in Docker)
- `API_PORT` - port (default 8000)

Payout detection is automatic (owner name from panel).

Notes:
- `.env` is not copied into the Docker image; it is bind-mounted as `/app/.env`.
- In Docker set `SON_OUT_DIR=/app/invoices` (named volume `son_data`).

## Endpoints

- `GET /health` - readiness (panel check, 503 if down)
- `GET /health/live` - liveness (no network)
- `GET /health/ready` - readiness (panel check)
- `GET /v1/tenants` - list tenants
- `GET /v1/estates` - list estates
- `GET /v1/tenants/{id}/operations` - tenant operations
- `GET /v1/tenants/{id}/liabilities` - tenant liabilities
- `GET /v1/tenants/{id}/insurances` - tenant insurances
- `GET /v1/finances` - owner finances
- `GET /v1/estates/{id}/cost-documents` - estate cost documents
- `GET /v1/estates/{id}/cost-documents/payouts` - payouts only
- `GET /v1/latest` - latest entries (income invoice, cost invoice, payout, payment) without downloading; optional `types` query param (repeatable) filters computed types
- `POST /v1/latest/download` - compute same entries, download PDFs, update `known_invoices.json`, return statuses/URLs
- `GET /v1/artifacts/{path}` - download file (PDF/CSV)

IDs are integers; booleans are true/false; dates are ISO (YYYY-MM-DD).

## Run locally

```
python api_server.py
```

Docs: http://127.0.0.1:8000/docs

## Examples (PowerShell)

List tenants:
```
Invoke-RestMethod http://127.0.0.1:8000/v1/tenants
```

Tenant operations:
```
Invoke-RestMethod http://127.0.0.1:8000/v1/tenants/2064/operations
```

Finances:
```
Invoke-RestMethod http://127.0.0.1:8000/v1/finances
```

Download artifact:
```
Invoke-WebRequest http://127.0.0.1:8000/v1/artifacts/operations.csv -OutFile operations.csv
```

Latest entries:
```
Invoke-RestMethod http://127.0.0.1:8000/v1/latest
Invoke-RestMethod -Method Post http://127.0.0.1:8000/v1/latest/download -ContentType "application/json" -Body "{}"
```

## Docker

```
docker compose up -d --build
```