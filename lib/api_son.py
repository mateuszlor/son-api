"""Wrapper around SONInternalClient for the REST API.

Provides a process-wide singleton client guarded by a lock (SON panel is not
safe for concurrent sessions) and converts parsed data to API models.
"""

import os
import time
import threading
from datetime import date

from lib.son_client import SONInternalClient, OUT_DIR, parse_pln
from lib.api_models import (
    TenantOut, OperationOut, LiabilityOut, InsuranceOut, FinanceOut, CostDocumentOut,
    EstateOut,
)


_panel_lock = threading.Lock()
_client_lock = threading.Lock()
_client = None
_tenants_raw_cache = None
_tenants_raw_cache_time = 0.0
_TENANT_CACHE_TTL = 300.0


def get_client():
    global _client
    with _client_lock:
        if _client is None:
            _client = SONInternalClient()
        return _client


def panel_ping():
    client = get_client()
    with _panel_lock:
        client._get("/")


def _iso(v):
    if isinstance(v, date):
        return v.isoformat()
    return v


def _to_int(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_bool(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v == 1
    return str(v).strip().lower() in ("1", "true", "yes", "y")


def _get_raw_tenants():
    global _tenants_raw_cache, _tenants_raw_cache_time
    now = time.monotonic()
    if _tenants_raw_cache is not None and (now - _tenants_raw_cache_time) < _TENANT_CACHE_TTL:
        return _tenants_raw_cache
    client = get_client()
    with _panel_lock:
        rows = client.get_tenants()
    _tenants_raw_cache = rows
    _tenants_raw_cache_time = now
    return rows


def list_tenants():
    rows = _get_raw_tenants()
    out = []
    for r in rows:
        tid = r.get("tenant_id")
        eid = r.get("estate_id")
        out.append(TenantOut(
            tenant_id=_to_int(tid) if _to_int(tid) is not None else tid,
            user_fullname=r.get("user_fullname") or "",
            address=r.get("address"),
            user_active=_to_bool(r.get("user_active")),
            user_balance=parse_pln(r.get("user_balance")),
            estate_id=_to_int(eid),
            eah_owner_fullname=r.get("eah_owner_fullname"),
            tags=r.get("tags"),
        ))
    return out


def list_estates():
    client = get_client()
    with _panel_lock:
        rows = client.get_estates()
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        eid = r.get("estate_id")
        ren = r.get("estate_is_under_renovation")
        fc = r.get("free_rooms_count")
        mt = r.get("estate_manage_type")
        rt = r.get("estate_rental_type")
        out.append(EstateOut(
            address=r.get("address"),
            estate_is_under_renovation=_to_bool(ren),
            estate_manage_type=_to_int(mt),
            estate_id=_to_int(eid),
            tags=r.get("tags"),
            estate_details=r.get("estate_details"),
            estate_rental_type=_to_int(rt),
            rooms_accommodation=r.get("rooms_accommodation"),
            free_rooms_count=_to_int(fc),
        ))
    return out


def _load_tenant_names():
    try:
        rows = _get_raw_tenants()
    except Exception:
        return {}
    cache = {}
    for r in rows:
        tid = r.get("tenant_id")
        if tid is not None:
            cache[str(tid)] = r.get("user_fullname")
    return cache


def _tenant_name(tenant_id):
    try:
        cache = _load_tenant_names()
        return cache.get(str(tenant_id))
    except Exception:
        pass
    return None


def tenant_operations(tenant_id):
    client = get_client()
    name = _tenant_name(tenant_id)
    with _panel_lock:
        html = client.get_tenant_operations(tenant_id)
        parsed = client.parse_operations(html, int(tenant_id) if str(tenant_id).isdigit() else tenant_id, name or "")
    out = []
    for e in parsed:
        out.append(OperationOut(
            tenant_id=e.get("tenant_id"),
            tenant_name=e.get("tenant_name"),
            type=e.get("type"),
            date=_iso(e.get("date")),
            income=e.get("income"),
            expense=e.get("expense"),
            balance=e.get("balance"),
            document=e.get("document"),
            pdf_url=e.get("pdf_url"),
            status=e.get("status"),
            description=e.get("description"),
        ))
    return out


def tenant_liabilities(tenant_id):
    client = get_client()
    name = _tenant_name(tenant_id)
    with _panel_lock:
        html = client.get_tenant_liabilities(tenant_id)
        parsed = client.parse_liabilities(html, int(tenant_id) if str(tenant_id).isdigit() else tenant_id, name or "")
    out = []
    for e in parsed:
        out.append(LiabilityOut(
            tenant_id=e.get("tenant_id"),
            tenant_name=e.get("tenant_name"),
            item_name=e.get("item_name"),
            amount_before_discount=e.get("amount_before_discount"),
            amount_after_discount=e.get("amount_after_discount"),
            total_discount=e.get("total_discount"),
            discount_details=e.get("discount_details"),
            billing_frequency=e.get("billing_frequency"),
            period=e.get("period"),
        ))
    return out


def tenant_insurances(tenant_id):
    client = get_client()
    name = _tenant_name(tenant_id)
    with _panel_lock:
        data = client.get_insurances(tenant_id)
        parsed = client.parse_insurances(data, int(tenant_id) if str(tenant_id).isdigit() else tenant_id, name or "")
    out = []
    for e in parsed:
        out.append(InsuranceOut(
            tenant_id=_to_int(e.get("tenant_id")),
            tenant_name=e.get("tenant_name"),
            id=_to_int(e.get("id")),
            company=e.get("company"),
            policy_number=e.get("policy_number"),
            status=_to_int(e.get("status")),
            start_date=_iso(e.get("start_date")),
            end_date=_iso(e.get("end_date")),
            estate_id=_to_int(e.get("estate_id")),
            room_id=_to_int(e.get("room_id")),
            created_at=e.get("created_at"),
        ))
    return out


def finances():
    client = get_client()
    with _panel_lock:
        html = client.get_finances()
        parsed = client.parse_finances(html)
    out = []
    for e in parsed:
        out.append(FinanceOut(
            type=e.get("type"),
            date=_iso(e.get("date")),
            payment=e.get("payment"),
            charge=e.get("charge"),
            balance=e.get("balance"),
            document=e.get("document"),
            pdf_url=e.get("pdf_url"),
            status=e.get("status"),
            description=e.get("description"),
        ))
    return out


def estate_payouts(estate_id):
    return [d for d in estate_cost_documents(estate_id) if d.is_payout]


def estate_cost_documents(estate_id):
    client = get_client()
    owner_name = None
    try:
        tenants = list_tenants()
        for t in tenants:
            if getattr(t, "eah_owner_fullname", None):
                owner_name = t.eah_owner_fullname
                break
    except Exception:
        owner_name = None
    with _panel_lock:
        html = client.get_estate_cost_documents(estate_id)
        parsed = client.parse_estate_cost_documents(html, owner_name)
    out = []
    for e in parsed:
        out.append(CostDocumentOut(
            estate_id=int(estate_id) if estate_id is not None and str(estate_id).isdigit() else None,
            date_added=_iso(e.get("date_added")),
            sale_date=_iso(e.get("sale_date")),
            seller=e.get("seller"),
            is_payout=e.get("is_payout"),
            number=e.get("number"),
            amount=e.get("amount"),
            payment_deadline=_iso(e.get("payment_deadline")),
            payment_date=_iso(e.get("payment_date")),
            download_zip_url=e.get("download_zip_url"),
            cost_document_id=_to_int(e.get("cost_document_id")),
        ))
    return out


def out_dir():
    return OUT_DIR
