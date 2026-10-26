"""REST API for SON panel data (FastAPI).

Run:
  python api_server.py
  # or: uvicorn api_server:app --host 127.0.0.1 --port 8000

Docs:
  http://127.0.0.1:8000/docs
"""

import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse

logger = logging.getLogger("son_api")

from lib.api_son import (
    list_tenants, list_estates, tenant_operations, tenant_liabilities,
    tenant_insurances, finances, estate_cost_documents, estate_payouts, out_dir,
    latest_invoices, download_latest,
)
from lib.path_safety import safe_resolve
from lib.api_models import (
    TenantOut, OperationOut, LiabilityOut, InsuranceOut, FinanceOut,
    CostDocumentOut, HealthOut, EstateOut, LiveOut,
    LatestOut, LatestDownloadOut, LatestDownloadRequest,
)



def _is_noisy_path(path: str) -> bool:
    """Paths that are polled frequently by external monitors/probes."""
    return path.startswith("/health")

app = FastAPI(title="SON Panel API", version="1.0.0")


@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        duration = (time.monotonic() - start) * 1000
        if _is_noisy_path(request.url.path):
            logger.debug("%s %s -> 500 (%.0f ms)", request.method, request.url.path, duration)
        else:
            logger.exception("%s %s -> 500 (%.0f ms)", request.method, request.url.path, duration)
        raise
    duration = (time.monotonic() - start) * 1000
    if _is_noisy_path(request.url.path):
        logger.debug("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, duration)
    else:
        logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, duration)
    return response


def _raise_panel_error(exc):
    if isinstance(exc, HTTPException):
        raise exc
    import requests
    resp = getattr(exc, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        status = 404 if code == 404 else 502
    elif isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        status = 502
    elif isinstance(exc, RuntimeError):
        status = 502
    else:
        status = 500
    logger.exception("SON panel error")
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


@app.get("/health/live", response_model=LiveOut)
def health_live():
    return LiveOut(status="ok")


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


@app.get("/v1/estates/{estate_id}/cost-documents/payouts", response_model=list[CostDocumentOut])
def get_estate_payouts(estate_id: int):
    try:
        return estate_payouts(estate_id)
    except Exception as e:
        _raise_panel_error(e)


@app.get("/v1/latest", response_model=LatestOut)
def get_latest(types: Optional[list[str]] = Query(default=None)):
    try:
        return latest_invoices(types=types)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_panel_error(e)


@app.post("/v1/latest/download", response_model=LatestDownloadOut)
def post_latest_download(req: Optional[LatestDownloadRequest] = None, request: Request = None):
    if req is None:
        req = LatestDownloadRequest()
    try:
        result = download_latest(types=req.types, force=req.force)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _raise_panel_error(e)
    # Build absolute URLs (respect reverse proxy headers).
    proto = "http"
    host = None
    if request is not None:
        # A forwarded header may contain a comma-separated list when the request
        # traverses multiple proxies. The leftmost entry is the original value
        # seen by the client-facing proxy, so split and take the first one.
        proto_header = request.headers.get("x-forwarded-proto", request.url.scheme)
        proto = proto_header.split(",")[0].strip() if proto_header is not None else request.url.scheme
        if not proto:
            proto = request.url.scheme

        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host is None:
            host = request.headers.get("host")
        else:
            host = forwarded_host.split(",")[0].strip()
        if not host:
            host = request.url.netloc
    if host:
        base = f"{proto}://{host}/"
        for d in result.downloads.values():
            if d.path and d.url is not None:
                d.url.absolute = base + "v1/artifacts/" + d.path
    return result


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
    uvicorn.run(app, host=host, port=port, reload=False, access_log=False)


if __name__ == "__main__":
    main()
