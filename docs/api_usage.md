# SON Panel REST API - usage

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