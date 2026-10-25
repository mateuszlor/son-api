"""Fetch the latest invoice (PDF) from SON panel.

Returns 3 entries (LATEST mode):
  1. Income invoice (faktura przychodowa) — latest rent invoice
  2. Cost invoice (faktura kosztowa) — latest management fee invoice
  3. Payout (wypłata) — latest payout to owner

Downloads PDF for each that has a PDF link.
If already downloaded — prints "Already have".

Requirements:
  pip install requests beautifulsoup4 python-dotenv

Usage:
  python fetch_latest_invoice.py
"""

import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import re
import json
from datetime import datetime

# Load variables from .env file (if exists)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from lib.son_client import SONInternalClient, OUT_DIR

FACTURES_DIR = os.getenv("SON_OUT_DIR", "./invoices")


def main():
    os.makedirs(FACTURES_DIR, exist_ok=True)
    state_file = os.path.join(FACTURES_DIR, "known_invoices.json")

    known = {}
    if os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as f:
            known = json.load(f)

    try:
        client = SONInternalClient()
        print("Logged in.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Check .env (SON_LOGIN, SON_PASSWORD).")
        return

    tenants = client.get_tenants()
    tenant = next((t for t in tenants if t.get("user_active") == "1"), tenants[0] if tenants else None)

    if not tenant:
        print("No tenants found.")
        return

    tid = int(tenant["tenant_id"])
    name = tenant["user_fullname"]
    print(f"Tenant: {name} (id: {tid})")

    # Three lists for three entry types (LATEST mode)
    income_invoices = [] # Faktura przychodowa (rent invoice)
    cost_invoices = []   # Faktura kosztowa (management fee)
    payouts = []         # Wypłata (payout to owner)

    # Source 1: tenant operations (rent invoices)
    try:
        html = client.get_tenant_operations(tid)
        ops = client.parse_operations(html, tid, name)
        for op in ops:
            if op.get("type") in ("FV", "KR"):
                income_invoices.append({
                    "type": "INCOME_INVOICE",
                    "date": op.get("date_raw", ""),
                    "date_obj": op.get("date"),
                    "amount": op.get("expense"),
                    "document": op.get("document", ""),
                    "pdf_url": op.get("pdf_url"),
                    "status": op.get("status"),
                    "description": op.get("description"),
                })
    except Exception as e:
        print(f"  Tenant operations: {e}")

    # Source 2: owner finances (cost invoices — FV/KR with PDF)
    try:
        html = client.get_finances(page_size=100)
        fins = client.parse_finances(html)
        for fin in fins:
            if fin.get("type") in ("FV", "KR") and fin.get("pdf_url"):
                cost_invoices.append({
                    "type": "COST_INVOICE",
                    "date": fin.get("date_raw", ""),
                    "date_obj": fin.get("date"),
                    "amount": fin.get("charge"),
                    "document": fin.get("document", ""),
                    "pdf_url": fin.get("pdf_url"),
                    "status": fin.get("status"),
                })
    except Exception as e:
        print(f"  Finances: {e}")

    # Source 3: estate cost documents (payouts where seller is owner)
    try:
        estates = client.get_estates()
        for est in estates:
            eid = est.get("estate_id")
            if not eid:
                continue
            owner_name = None
            for t in tenants:
                if str(t.get("estate_id")) == str(eid):
                    owner_name = t.get("eah_owner_fullname")
                    break
            if not owner_name and tenants:
                owner_name = tenants[0].get("eah_owner_fullname")
            cd_html = client.get_estate_cost_documents(eid)
            cds = client.parse_estate_cost_documents(cd_html, owner_name=owner_name)
            for cd in cds:
                if cd.get("is_payout") and cd.get("amount", 0) != 0:
                    cd_id = cd.get("cost_document_id")
                    pdf_url = None
                    if cd_id:
                        pdf_url = client.get_cost_document_download_url(cd_id)
                    payouts.append({
                        "type": "PAYOUT",
                        "date": cd.get("date_added_raw", ""),
                        "date_obj": cd.get("date_added"),
                        "amount": cd.get("amount"),
                        "document": f"payout_{cd.get('date_added_raw', '').replace('/', '-')}",
                        "pdf_url": pdf_url,
                        "status": None,
                    })
    except Exception as e:
        print(f"  Estate cost documents: {e}")

    # --- LATEST mode: latest entry of each type ---

    def latest_of(entries):
        if not entries:
            return None
        entries.sort(key=lambda x: x["date_obj"] or datetime.min.date(), reverse=True)
        return entries[0]

    latest_income = latest_of(income_invoices)
    latest_cost = latest_of(cost_invoices)
    latest_payout = latest_of(payouts)

    # Report
    print("\n=== LATEST ===")
    if latest_income:
        print(f"\nIncome invoice: {latest_income['document']} ({latest_income['date']}, {latest_income['amount']})")
    else:
        print("\nIncome invoice: none")
    if latest_cost:
        print(f"Cost invoice: {latest_cost['document']} ({latest_cost['date']}, {latest_cost['amount']})")
    else:
        print("Cost invoice: none")
    if latest_payout:
        print(f"Payout: {latest_payout['document']} ({latest_payout['date']}, {latest_payout['amount']})")
    else:
        print("Payout: none")

    # Download PDF for each entry that has a PDF
    all_entries = [x for x in [latest_income, latest_cost, latest_payout] if x]
    for entry in all_entries:
        if entry.get("pdf_url"):
            safe_name = re.sub(r"[^\w\-]", "_", entry["document"])
            dest = os.path.join(FACTURES_DIR, f"{safe_name}.pdf")
            known_tid = known.get(str(tid), [])
            if entry["document"] in known_tid and os.path.exists(dest):
                print(f"\nAlready have: {entry['document']} ({dest})")
            else:
                print(f"\nDownloading: {entry['document']}")
                if client.download_file(entry["pdf_url"], dest):
                    print(f"   Saved: {dest}")
                else:
                    print(f"   Download failed")
    if not any(e.get("pdf_url") for e in all_entries):
        print("\nNo PDFs to download.")

    # Update state
    if str(tid) not in known:
        known[str(tid)] = []
    for entry in all_entries:
        if entry["document"] not in known[str(tid)]:
            known[str(tid)].append(entry["document"])
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(known, f, ensure_ascii=False, indent=2)
    print(f"\nState saved to: {state_file}")


if __name__ == "__main__":
    main()
