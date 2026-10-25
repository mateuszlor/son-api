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
    tenant_insurances, finances, estate_cost_documents, out_dir,
)
from lib.path_safety import safe_resolve
from lib.api_models import (
    TenantOut, OperationOut, LiabilityOut, InsuranceOut, FinanceOut,
    CostDocumentOut, HealthOut, EstateOut,
)

app = FastAPI(title="SON Panel API", version="1.0.0")


@app.get("/health", response_model=HealthOut)
def health():
    try:
        from lib.api_son import get_client
        get_client()
        return HealthOut(status="ok", son_connected=True)
    except Exception:
        raise HTTPException(status_code=503, detail="SON panel unavailable")


@app.get("/v1/tenants", response_model=list[TenantOut])
def get_tenants():
    try:
        return list_tenants()
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


@app.get("/v1/estates", response_model=list[EstateOut])
def get_estates():
    try:
        return list_estates()
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


@app.get("/v1/tenants/{tenant_id}/operations", response_model=list[OperationOut])
def get_tenant_operations(tenant_id: int):
    try:
        return tenant_operations(tenant_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


@app.get("/v1/tenants/{tenant_id}/liabilities", response_model=list[LiabilityOut])
def get_tenant_liabilities(tenant_id: int):
    try:
        return tenant_liabilities(tenant_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


@app.get("/v1/tenants/{tenant_id}/insurances", response_model=list[InsuranceOut])
def get_tenant_insurances(tenant_id: int):
    try:
        return tenant_insurances(tenant_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


@app.get("/v1/finances", response_model=list[FinanceOut])
def get_finances():
    try:
        return finances()
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


@app.get("/v1/estates/{estate_id}/cost-documents", response_model=list[CostDocumentOut])
def get_estate_cost_documents(estate_id: int):
    try:
        return estate_cost_documents(estate_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail="SON panel error")


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
    uvicorn.run("api_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
