"""Wrapper around SONInternalClient for the REST API.

Provides a process-wide singleton client guarded by a lock (SON panel is not
safe for concurrent sessions) and converts parsed data to API models.
"""

import os
import re
import json
import time
import tempfile
import logging
import threading
from dataclasses import dataclass
from datetime import date
from typing import Optional

from lib.son_client import SONInternalClient, OUT_DIR, parse_pln
from lib.api_models import (
    TenantOut, OperationOut, LiabilityOut, InsuranceOut, FinanceOut, CostDocumentOut,
    EstateOut, LatestOut, LatestDownloadOut, LatestDownloadResult,
    ArtifactLink,
)


_panel_lock = threading.Lock()
logger = logging.getLogger("son_api")
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
            estate_id=_to_int(estate_id),
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


# ---------------------------------------------------------------------------
# LATEST mode helpers (4 entries: income_invoice, cost_invoice, payout, payment)
# ---------------------------------------------------------------------------

_state_lock = threading.Lock()


def _state_path():
    return os.path.join(out_dir(), "known_invoices.json")


def _load_state():
    path = _state_path()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save_state(state):
    path = _state_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".",
        dir=os.path.dirname(path) or ".",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


@dataclass
class _LatestComputed:
    payout_raw: Optional[dict]
    income_model: Optional[OperationOut]
    cost_model: Optional[FinanceOut]
    payout_model: Optional[CostDocumentOut]
    payment_model: Optional[OperationOut]
    warnings: list
    last_document_date: Optional[str]


_ALLOWED_TYPES = {"income_invoice", "cost_invoice", "payout", "payment"}


def _compute_latest(types=None):
    if types is None:
        types = list(_ALLOWED_TYPES)
    types_set = set(types)
    unknown = types_set - _ALLOWED_TYPES
    if unknown:
        raise ValueError(f"unknown types: {sorted(unknown)}")

    warnings = []
    income_raw = None
    income_date = None
    payment_raw = None
    payment_date = None
    cost_raw = None
    cost_date = None
    payout_raw = None
    payout_date = None
    payout_eid = None

    client = get_client()

    tenants_ok = True
    tenant_ops_ok = True
    finances_ok = True
    estates_ok = True
    cost_docs_ok = True

    need_tenants = ("income_invoice" in types_set or "payment" in types_set or "payout" in types_set)

    # tenants
    raw_tenants = []
    active_tenants = []
    if need_tenants:
        tenants_ok = False
        tenant_ops_ok = False
        try:
            raw_tenants = _get_raw_tenants()
            tenants_ok = True
        except Exception as e:
            logger.exception("tenants fetch failed")
            warnings.append("tenants: upstream error")
            raw_tenants = []
        active_tenants = [t for t in raw_tenants if _to_bool(t.get("user_active"))]

    owner_names = {t.get("eah_owner_fullname") for t in raw_tenants if t.get("eah_owner_fullname")}
    if "payout" in types_set and not owner_names and tenants_ok:
        warnings.append("no owner names found in tenants")

    # income_invoice + payment (wpłata) from tenant operations
    if "income_invoice" in types_set or "payment" in types_set:
        if active_tenants:
            for t in active_tenants:
                tid = t.get("tenant_id")
                name = t.get("user_fullname") or ""
                try:
                    with _panel_lock:
                        html = client.get_tenant_operations(tid)
                        ops = client.parse_operations(html, _to_int(tid) if _to_int(tid) is not None else tid, name)
                    tenant_ops_ok = True
                except Exception as e:
                    logger.exception("tenant %s operations failed", tid)
                    warnings.append(f"tenant {tid} operations: upstream error")
                    continue
                for op in ops:
                    d = op.get("date")
                    if d is None:
                        continue
                    typ = op.get("type")
                    if "income_invoice" in types_set and typ in ("FV", "KR"):
                        if income_date is None or d > income_date:
                            income_date = d
                            income_raw = op
                    if "payment" in types_set and op.get("income") is not None and typ not in ("FV", "KR"):
                        if payment_date is None or d > payment_date:
                            payment_date = d
                            payment_raw = op
        else:
            tenant_ops_ok = True

    # cost_invoice from owner finances
    if "cost_invoice" in types_set:
        try:
            with _panel_lock:
                html = client.get_finances(page_size=100)
                fins = client.parse_finances(html)
            finances_ok = True
            for fin in fins:
                if fin.get("type") in ("FV", "KR") and fin.get("pdf_url"):
                    d = fin.get("date")
                    if d is None:
                        continue
                    if cost_date is None or d > cost_date:
                        cost_date = d
                        cost_raw = fin
        except Exception as e:
            logger.exception("finances fetch failed")
            warnings.append("finances: upstream error")
            finances_ok = False

    estates_list = []
    # payout across all estates
    if "payout" in types_set:
        estates_ok = False
        cost_docs_ok = False
        try:
            with _panel_lock:
                estates = client.get_estates()
            estates_list = estates
            estates_ok = True
            if not estates_list:
                cost_docs_ok = True
            for est in estates:
                eid = est.get("estate_id")
                if not eid:
                    continue
                try:
                    with _panel_lock:
                        html = client.get_estate_cost_documents(eid)
                        cds = client.parse_estate_cost_documents(html, owner_name=None)
                    cost_docs_ok = True
                except Exception as e:
                    logger.exception("estate %s cost documents failed", eid)
                    warnings.append(f"estate {eid} cost documents: upstream error")
                    continue
                for cd in cds:
                    seller = cd.get("seller") or ""
                    is_payout = any(on and on.lower() in seller.lower() for on in owner_names)
                    if not is_payout:
                        continue
                    if cd.get("amount", 0) == 0:
                        continue
                    d = cd.get("date_added")
                    if d is None:
                        continue
                    if payout_date is None or d > payout_date:
                        payout_date = d
                        payout_raw = cd
                        payout_eid = eid
            if payout_raw is not None:
                cd_id = payout_raw.get("cost_document_id")
                if cd_id:
                    try:
                        with _panel_lock:
                            pdf_url = client.get_cost_document_download_url(cd_id)
                        payout_raw["pdf_url"] = pdf_url
                    except Exception as e:
                        logger.exception("payout pdf url failed")
                        warnings.append("payout pdf url: upstream error")
                        payout_raw["pdf_url"] = None
                payout_raw["estate_id"] = payout_eid
                payout_raw["is_payout"] = True
        except Exception as e:
            logger.exception("estates fetch failed")
            warnings.append("estates: upstream error")

    # Total failure check: raise only if ALL requested sources failed.
    requested_sources = []
    source_ok = []
    if "income_invoice" in types_set or "payment" in types_set:
        requested_sources.append("tenant")
        tenant_source_ok = tenants_ok and (not active_tenants or tenant_ops_ok)
        source_ok.append(tenant_source_ok)
    if "cost_invoice" in types_set:
        requested_sources.append("cost")
        source_ok.append(finances_ok)
    if "payout" in types_set:
        requested_sources.append("payout")
        payout_source_ok = estates_ok and (not estates_list or cost_docs_ok)
        source_ok.append(payout_source_ok)

    if requested_sources and not any(source_ok):
        raise RuntimeError("all upstream sources failed")

    # convert to models
    income_model = None
    if income_raw is not None:
        income_model = OperationOut(
            tenant_id=income_raw.get("tenant_id"),
            tenant_name=income_raw.get("tenant_name"),
            type=income_raw.get("type"),
            date=_iso(income_raw.get("date")),
            income=income_raw.get("income"),
            expense=income_raw.get("expense"),
            balance=income_raw.get("balance"),
            document=income_raw.get("document"),
            pdf_url=income_raw.get("pdf_url"),
            status=income_raw.get("status"),
            description=income_raw.get("description"),
        )

    payment_model = None
    if payment_raw is not None:
        payment_model = OperationOut(
            tenant_id=payment_raw.get("tenant_id"),
            tenant_name=payment_raw.get("tenant_name"),
            type=payment_raw.get("type"),
            date=_iso(payment_raw.get("date")),
            income=payment_raw.get("income"),
            expense=payment_raw.get("expense"),
            balance=payment_raw.get("balance"),
            document=payment_raw.get("document"),
            pdf_url=payment_raw.get("pdf_url"),
            status=payment_raw.get("status"),
            description=payment_raw.get("description"),
        )

    cost_model = None
    if cost_raw is not None:
        cost_model = FinanceOut(
            type=cost_raw.get("type"),
            date=_iso(cost_raw.get("date")),
            payment=cost_raw.get("payment"),
            charge=cost_raw.get("charge"),
            balance=cost_raw.get("balance"),
            document=cost_raw.get("document"),
            pdf_url=cost_raw.get("pdf_url"),
            status=cost_raw.get("status"),
            description=cost_raw.get("description"),
        )

    payout_model = None
    if payout_raw is not None:
        eid = payout_raw.get("estate_id")
        payout_model = CostDocumentOut(
            estate_id=_to_int(eid),
            date_added=_iso(payout_raw.get("date_added")),
            sale_date=_iso(payout_raw.get("sale_date")),
            seller=payout_raw.get("seller"),
            is_payout=True,
            number=payout_raw.get("number"),
            amount=payout_raw.get("amount"),
            payment_deadline=_iso(payout_raw.get("payment_deadline")),
            payment_date=_iso(payout_raw.get("payment_date")),
            download_zip_url=payout_raw.get("download_zip_url"),
            cost_document_id=_to_int(payout_raw.get("cost_document_id")),
            pdf_url=payout_raw.get("pdf_url"),
        )

    dates = []
    if income_model and income_model.date:
        dates.append(income_model.date)
    if payment_model and payment_model.date:
        dates.append(payment_model.date)
    if cost_model and cost_model.date:
        dates.append(cost_model.date)
    if payout_model and payout_model.date_added:
        dates.append(payout_model.date_added)
    last_document_date = max(dates) if dates else None

    return _LatestComputed(
        payout_raw=payout_raw,
        income_model=income_model,
        cost_model=cost_model,
        payout_model=payout_model,
        payment_model=payment_model,
        warnings=warnings,
        last_document_date=last_document_date,
    )


def latest_invoices(types=None):
    c = _compute_latest(types)
    return LatestOut(
        income_invoice=c.income_model,
        cost_invoice=c.cost_model,
        payout=c.payout_model,
        payment=c.payment_model,
        warnings=c.warnings,
        last_document_date=c.last_document_date,
    )


def download_latest(types=None, force=False):
    c = _compute_latest(types)
    types_set = set(types) if types is not None else set(_ALLOWED_TYPES)
    unknown = types_set - _ALLOWED_TYPES
    if unknown:
        raise ValueError(f"unknown types: {sorted(unknown)}")

    client = get_client()
    downloads = {}

    # Serialize state load/mutate/save (and the resulting downloads) so concurrent
    # /v1/latest/download calls cannot lose updates or clobber the state file.
    with _state_lock:
        state = _load_state()
        tenant_key = "all"
        try:
            raw_tenants = _get_raw_tenants()
            active_tenants = [t for t in raw_tenants if _to_bool(t.get("user_active"))]
            if active_tenants:
                tid = active_tenants[0].get("tenant_id")
                if tid is not None:
                    tenant_key = str(tid)
        except Exception:
            tenant_key = "all"

        known = state.setdefault(tenant_key, [])
        if not isinstance(known, list):
            known = []
            state[tenant_key] = known
        # Snapshot after normalization so a no-op call does not report an update.
        state_before = json.dumps(state, sort_keys=True, default=str)

        entries = [
            ("income_invoice", c.income_model, None, "income_invoice"),
            ("cost_invoice", c.cost_model, None, "cost_invoice"),
            ("payout", c.payout_model, c.payout_raw, "payout"),
            ("payment", c.payment_model, None, "payment"),
        ]

        for kind, model, raw, _ in entries:
            if kind not in types_set:
                downloads[kind] = LatestDownloadResult(kind=kind, status="skipped")
                continue
            if model is None:
                downloads[kind] = LatestDownloadResult(kind=kind, status="no_entry")
                continue
            pdf_url = getattr(model, "pdf_url", None)
            if not pdf_url:
                downloads[kind] = LatestDownloadResult(kind=kind, status="no_pdf")
                continue

            tracked = True
            if kind == "income_invoice" or kind == "payment":
                doc = getattr(model, "document", None)
                if not doc:
                    d = getattr(model, "date", None)
                    doc = f"{kind}_{d}" if d else None
            elif kind == "cost_invoice":
                doc = getattr(model, "document", None)
                if not doc:
                    d = getattr(model, "date", None)
                    doc = f"{kind}_{d}" if d else None
            else:
                raw_date = None
                if isinstance(raw, dict):
                    raw_date = raw.get("date_added_raw")
                if raw_date:
                    doc = f"payout_{str(raw_date).replace('/', '-')}"
                else:
                    d = getattr(model, "date_added", None)
                    if d:
                        parts = str(d).split("-")
                        if len(parts) == 3:
                            doc = f"payout_{parts[2]}-{parts[1]}-{parts[0]}"
                        else:
                            doc = f"payout_{d}"
                    else:
                        doc = None

            if not doc:
                doc = kind
                tracked = False

            safe_name = re.sub(r"[^\w\-]", "_", str(doc))
            dest = os.path.join(out_dir(), f"{safe_name}.pdf")

            error = None
            if tracked and not force and doc in known and os.path.exists(dest):
                status = "already_have"
            else:
                try:
                    with _panel_lock:
                        ok = client.download_file(pdf_url, dest)
                except Exception as e:
                    c.warnings.append(f"{kind} download: {e}")
                    ok = False
                    error = str(e)
                if not ok:
                    if error is None:
                        error = "download failed"
                status = "saved" if ok else "failed"
                if ok and tracked and doc not in known:
                    known.append(doc)

            # Only expose path/url when the file is actually present after a
            # successful (or already-cached) download.
            if status == "failed" or not os.path.exists(dest):
                _path = None
            else:
                _path = os.path.basename(dest)
            _rel = f"/v1/artifacts/{_path}" if _path else None
            downloads[kind] = LatestDownloadResult(
                kind=kind,
                status=status,
                path=_path,
                url=ArtifactLink(relative=_rel, absolute=_rel) if _rel else None,
                error=error if status == "failed" else None,
            )

        # Only treat the state as updated when its contents actually changed.
        # Rewriting an identical known_invoices.json is not an update.
        state_changed = json.dumps(state, sort_keys=True, default=str) != state_before
        state_updated = False
        if state_changed:
            try:
                _save_state(state)
                state_updated = True
            except Exception as e:
                c.warnings.append(f"state save: {e}")

    return LatestDownloadOut(
        income_invoice=c.income_model,
        cost_invoice=c.cost_model,
        payout=c.payout_model,
        payment=c.payment_model,
        warnings=c.warnings,
        last_document_date=c.last_document_date,
        downloads=downloads,
        state_updated=state_updated,
    )
