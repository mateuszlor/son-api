"""REST API for SON panel data (FastAPI).

Run:
  python api_server.py
  # or: uvicorn api_server:app --host 127.0.0.1 --port 8000

Docs:
  http://127.0.0.1:8000/docs
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from lib.api_son import (
    list_tenants, list_estates, tenant_operations, tenant_liabilities,
    tenant_insurances, finances, estate_cost_documents, estate_payouts, out_dir,
)
from lib.path_safety import safe_resolve
from lib.api_models import (
    TenantOut, OperationOut, LiabilityOut, InsuranceOut, FinanceOut,
    CostDocumentOut, HealthOut, EstateOut,
)

app = FastAPI(title="SON Panel API", version="1.0.0")


def _raise_panel_error(exc):
    status = 502
    resp = getattr(exc, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        if code == 404:
            status = 404
        elif isinstance(code, int) and code >= 500:
            status = 502
    elif "404" in str(exc):
        status = 404
    raise HTTPException(status_code=status, detail="SON panel error") from exc


@app.get("/health", response_model=HealthOut)
@app.get("/health/ready", response_model=HealthOut)
def health_ready():
    try:
        from lib.api_son import panel_ping
        panel_ping()
        return HealthOut(status="ok", son_connected=True)
    except Exception:
        raise HTTPException(status_code=503, detail="SON panel unavailable")


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/v1/tenants", response_model=list[TenantOut])
def get_tenants():
    try:
        return list_tenants()
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/estates", response_model=list[EstateOut])
def get_estates():
    try:
        return list_estates()
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/tenants/{tenant_id}/operations", response_model=list[OperationOut])
def get_tenant_operations(tenant_id: int):
    try:
        return tenant_operations(tenant_id)
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/tenants/{tenant_id}/liabilities", response_model=list[LiabilityOut])
def get_tenant_liabilities(tenant_id: int):
    try:
        return tenant_liabilities(tenant_id)
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/tenants/{tenant_id}/insurances", response_model=list[InsuranceOut])
def get_tenant_insurances(tenant_id: int):
    try:
        return tenant_insurances(tenant_id)
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/finances", response_model=list[FinanceOut])
def get_finances():
    try:
        return finances()
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/estates/{estate_id}/cost-documents", response_model=list[CostDocumentOut])
def get_estate_cost_documents(estate_id: int):
    try:
        return estate_cost_documents(estate_id)
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/estates/{estate_id}/payouts", response_model=list[CostDocumentOut])
def get_estate_payouts(estate_id: int):
    try:
        return estate_payouts(estate_id)
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/artifacts/{path:path}")
def get_artifact(path: str):
    full = safe_resolve(out_dir(), path)
    if not full or not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full)


def main():
    import uvicorn
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
