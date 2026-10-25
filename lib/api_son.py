"""Wrapper around SONInternalClient for the REST API.

Provides a process-wide singleton client guarded by a lock (SON panel is not
safe for concurrent sessions) and converts parsed data to API models.
"""

import os
import threading
from datetime import date

from lib.son_client import SONInternalClient, OUT_DIR, parse_pln
from lib.api_models import (
    TenantOut, OperationOut, LiabilityOut, InsuranceOut, FinanceOut, CostDocumentOut,
)


_lock = threading.Lock()
_client = None


def get_client():
    global _client
    with _lock:
        if _client is None:
            _client = SONInternalClient()
        return _client


def _iso(v):
    if isinstance(v, date):
        return v.isoformat()
    return v


def list_tenants():
    client = get_client()
    with _lock:
        rows = client.get_tenants()
    out = []
    for r in rows:
        tid = r.get("tenant_id")
        eid = r.get("estate_id")
        out.append(TenantOut(
            tenant_id=int(tid) if tid is not None and str(tid).isdigit() else tid,
            user_fullname=r.get("user_fullname") or "",
            address=r.get("address"),
            user_active=(r.get("user_active") == "1") if r.get("user_active") is not None else None,
            user_balance=parse_pln(r.get("user_balance")),
            estate_id=int(eid) if eid is not None and str(eid).isdigit() else None,
            eah_owner_fullname=r.get("eah_owner_fullname"),
            tags=r.get("tags"),
        ))
    return out


def list_estates():
    client = get_client()
    with _lock:
        rows = client.get_estates()
    for r in rows:
        if isinstance(r, dict):
            eid = r.get("estate_id")
            if eid is not None and str(eid).isdigit():
                r["estate_id"] = int(eid)
            ren = r.get("estate_is_under_renovation")
            if ren is not None and str(ren).isdigit():
                r["estate_is_under_renovation"] = (str(ren) == "1")
            for key in ("estate_manage_type", "estate_rental_type", "free_rooms_count"):
                v = r.get(key)
                if v is not None and str(v).isdigit():
                    r[key] = int(v)
    return rows


def _tenant_name(tenant_id):
    try:
        for t in list_tenants():
            if str(t.tenant_id) == str(tenant_id):
                return t.user_fullname
    except Exception:
        pass
    return None


def tenant_operations(tenant_id):
    client = get_client()
    name = _tenant_name(tenant_id)
    with _lock:
        html = client.get_tenant_operations(tenant_id)
        parsed = client.parse_operations(html, int(tenant_id) if str(tenant_id).isdigit() else tenant_id, name or "")
    out = []
    for e in parsed:
        out.append(OperationOut(
            tenant_id=e.get("tenant_id"),
            tenant_name=e.get("tenant_name"),
            type=e.get("type"),
            date=_iso(e.get("date")),
            date_raw=e.get("date_raw"),
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
    with _lock:
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
    with _lock:
        data = client.get_insurances(tenant_id)
        parsed = client.parse_insurances(data, int(tenant_id) if str(tenant_id).isdigit() else tenant_id, name or "")
    out = []
    for e in parsed:
        iid = e.get("id")
        st = e.get("status")
        eid = e.get("estate_id")
        rid = e.get("room_id")
        out.append(InsuranceOut(
            tenant_id=e.get("tenant_id"),
            tenant_name=e.get("tenant_name"),
            id=int(iid) if iid is not None and str(iid).isdigit() else None,
            company=e.get("company"),
            policy_number=e.get("policy_number"),
            status=int(st) if st is not None and str(st).isdigit() else None,
            start_date=_iso(e.get("start_date")),
            end_date=_iso(e.get("end_date")),
            estate_id=int(eid) if eid is not None and str(eid).isdigit() else None,
            room_id=int(rid) if rid is not None and str(rid).isdigit() else None,
            created_at=e.get("created_at"),
        ))
    return out


def finances():
    client = get_client()
    with _lock:
        html = client.get_finances()
        parsed = client.parse_finances(html)
    out = []
    for e in parsed:
        out.append(FinanceOut(
            type=e.get("type"),
            date=_iso(e.get("date")),
            date_raw=e.get("date_raw"),
            payment=e.get("payment"),
            charge=e.get("charge"),
            balance=e.get("balance"),
            document=e.get("document"),
            pdf_url=e.get("pdf_url"),
            status=e.get("status"),
            description=e.get("description"),
        ))
    return out


def estate_cost_documents(estate_id):
    client = get_client()
    with _lock:
        html = client.get_estate_cost_documents(estate_id)
        parsed = client.parse_estate_cost_documents(html, None)
    out = []
    for e in parsed:
        out.append(CostDocumentOut(
            date_added=_iso(e.get("date_added")),
            date_added_raw=e.get("date_added_raw"),
            sale_date=_iso(e.get("sale_date")),
            sale_date_raw=e.get("sale_date_raw"),
            seller=e.get("seller"),
            is_payout=e.get("is_payout"),
            number=e.get("number"),
            amount=e.get("amount"),
            payment_deadline=_iso(e.get("payment_deadline")),
            payment_deadline_raw=e.get("payment_deadline_raw"),
            payment_date=_iso(e.get("payment_date")),
            payment_date_raw=e.get("payment_date_raw"),
            download_zip_url=e.get("download_zip_url"),
            cost_document_id=int(e.get("cost_document_id")) if e.get("cost_document_id") is not None and str(e.get("cost_document_id")).isdigit() else None,
        ))
    return out


def out_dir():
    return OUT_DIR
