# SON Panel REST API - usage

## Configuration (.env)

Required (existing):
- `SON_LOGIN` - SON panel login (email)
- `SON_PASSWORD` - SON panel password
- `SON_PANEL_URL` - panel URL (e.g. https://your-panel.example.com)
- `SON_OUT_DIR` - output directory (default ./invoices)

Optional (API/Docker):
- `API_HOST` - bind host (default 127.0.0.1; use 0.0.0.0 in Docker)
- `API_PORT` - port (default 8000)

Notes:
- `.env` is not copied into the Docker image; use `env_file` in compose.
- In Docker set `OUT_DIR=/app/invoices` (named volume `son_data`).

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

## Docker

```
docker compose up -d --build
```