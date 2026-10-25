"""Main automation script for SON panel.

Fetches all tenants with data, parses HTML to CSV, generates alerts.
Uses shared library lib/son_client.py.

Requirements:
  pip install requests beautifulsoup4 python-dotenv

Usage:
  python fetch_all_data.py
"""

import os
import sys
import re
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import json
import csv
import time
from datetime import date

# Load variables from .env file (if exists)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from lib.son_client import SONInternalClient, parse_pln, OUT_DIR


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        client = SONInternalClient()
        print("Logged in.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Check .env (SON_LOGIN, SON_PASSWORD).")
        return

    print("\n=== Fetching tenant list ===")
    tenants = client.get_tenants()
    print(f"Found {len(tenants)} tenants.")

    with open(os.path.join(OUT_DIR, "tenants.json"), "w", encoding="utf-8") as f:
        json.dump(tenants, f, ensure_ascii=False, indent=2, default=str)

    all_operations = []
    all_liabilities = []
    all_insurances = []
    all_pdfs = []
    all_cost_docs = []

    for i, t in enumerate(tenants, 1):
        tid = int(t.get("tenant_id") or t.get("id"))
        name = t.get("user_fullname") or t.get("fullname") or "?"
        balance = t.get("user_balance", "?")
        active = t.get("user_active", "?")
        print(f"\n[{i}/{len(tenants)}] Tenant {tid} — {name} (balance: {balance}, active: {active})")

        try:
            ops_html = client.get_tenant_operations(tid)
            ops = client.parse_operations(ops_html, tid, name)
            all_operations.extend(ops)
            print(f"  operations: {len(ops)}")
            with open(os.path.join(OUT_DIR, f"ops_{tid}.html"), "w", encoding="utf-8") as f:
                f.write(ops_html)
        except Exception as e:
            print(f"  ERROR operations: {e}")
            ops = []

        try:
            liab_html = client.get_tenant_liabilities(tid)
            liabs = client.parse_liabilities(liab_html, tid, name)
            all_liabilities.extend(liabs)
            print(f"  liabilities: {len(liabs)}")
            with open(os.path.join(OUT_DIR, f"liab_{tid}.html"), "w", encoding="utf-8") as f:
                f.write(liab_html)
        except Exception as e:
            print(f"  ERROR liabilities: {e}")

        try:
            ins_data = client.get_insurances(tid)
            ins = client.parse_insurances(ins_data, tid, name)
            all_insurances.extend(ins)
            print(f"  insurances: {len(ins)}")
            with open(os.path.join(OUT_DIR, f"ins_{tid}.json"), "w", encoding="utf-8") as f:
                json.dump(ins_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"  ERROR insurances: {e}")

        try:
            pdfs = client.fetch_invoice_pdfs(ops, tid, OUT_DIR)
            all_pdfs.extend(pdfs)
            print(f"  PDFs downloaded: {len(pdfs)}")
        except Exception as e:
            print(f"  ERROR PDFs: {e}")

        time.sleep(1)

    # Fetch owner finances (cost invoices + payouts)
    print("\n=== Fetching owner finances ===")
    all_finances = []
    try:
        fin_html = client.get_finances(page_size=100)
        fins = client.parse_finances(fin_html)
        all_finances.extend(fins)
        print(f"  Finances: {len(fins)}")
        with open(os.path.join(OUT_DIR, "finances.html"), "w", encoding="utf-8") as f:
            f.write(fin_html)
        seen = set()
        for fin in fins:
            url = fin.get("pdf_url")
            if url and url not in seen:
                seen.add(url)
                safe = re.sub(r"[^\w\-]", "_", str(fin.get("document", "finance")))
                dest = os.path.join(OUT_DIR, f"finances_pdfs/{safe}.pdf")
                if os.path.exists(dest):
                    print(f"    Already exists: {safe}.pdf")
                else:
                    if client.download_file(url, dest):
                        print(f"    Downloaded: {safe}.pdf")
                    else:
                        print(f"    FAILED: {safe}.pdf")
    except Exception as e:
        print(f"  ERROR finances: {e}")

    def save_csv(rows, filename):
        if not rows:
            return
        keys = list({k for r in rows for k in r.keys()})
        with open(os.path.join(OUT_DIR, filename), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    save_csv(all_operations, "operations.csv")
    save_csv(all_liabilities, "liabilities.csv")
    save_csv(all_insurances, "insurances.csv")
    save_csv(all_finances, "finances.csv")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tenants: {len(tenants)}")
    print(f"Operations: {len(all_operations)}")
    print(f"Liabilities: {len(all_liabilities)}")
    print(f"Insurances: {len(all_insurances)}")
    print(f"Finances: {len(all_finances)}")
    print(f"PDFs: {len(all_pdfs)}")

    print("\n--- Tenants with negative balance ---")
    for t in tenants:
        bal = parse_pln(t.get("user_balance"))
        if bal is not None and bal < 0:
            print(f"  {t.get('user_fullname')} (id={t.get('tenant_id')}): {bal:.2f}")

    print("\n--- Insurances expiring within 60 days ---")
    today = date.today()
    for ins in all_insurances:
        dk = ins.get("end_date")
        if dk and isinstance(dk, date):
            days = (dk - today).days
            if 0 <= days <= 60:
                print(f"  {ins.get('tenant_name')} (id={ins.get('tenant_id')}): {ins.get('company')} {ins.get('policy_number')} — expires {dk} (in {days} days)")

    print("\n--- Unpaid invoices ---")
    unpaid = [op for op in all_operations if op.get("type") == "FV" and op.get("status") != "Opłacona"]
    if unpaid:
        for op in unpaid:
            print(f"  {op.get('tenant_name')} (id={op.get('tenant_id')}): {op.get('document')} — {op.get('expense')} — date: {op.get('date_raw')}")
    else:
        print("  No unpaid invoices.")

    # Fetch estate cost documents
    print("\n=== Fetching estate cost documents ===")
    try:
        estates = client.get_estates()
        for est in estates:
            eid = est.get("estate_id")
            if not eid:
                continue
            print(f"  Estate {eid}: {est.get('address', '')}")
            cd_html = client.get_estate_cost_documents(eid)
            owner_name = None
            for t in tenants:
                if str(t.get("estate_id")) == str(eid):
                    owner_name = t.get("eah_owner_fullname")
                    break
            if not owner_name and tenants:
                owner_name = tenants[0].get("eah_owner_fullname")
            cds = client.parse_estate_cost_documents(cd_html, owner_name=owner_name)
            for cd in cds:
                cd["estate_id"] = eid
            all_cost_docs.extend(cds)
            payouts = [cd for cd in cds if cd.get("is_payout")]
            costs = [cd for cd in cds if not cd.get("is_payout")]
            print(f"    Cost documents: {len(cds)} ({len(costs)} costs, {len(payouts)} payouts)")
            # Download PDFs
            seen = set()
            for cd in cds:
                cd_id = cd.get("cost_document_id")
                if not cd_id or cd_id in seen:
                    continue
                seen.add(cd_id)
                url = client.get_cost_document_download_url(cd_id)
                if url:
                    safe = re.sub(r"[^\w\-]", "_", str(cd.get("number", cd_id)))
                    dest = os.path.join(OUT_DIR, f"cost_docs_pdfs/{safe}.pdf")
                    if not os.path.exists(dest):
                        if client.download_file(url, dest):
                            print(f"    Downloaded: {safe}.pdf")
            with open(os.path.join(OUT_DIR, f"cost_docs_{eid}.html"), "w", encoding="utf-8") as f:
                f.write(cd_html)
    except Exception as e:
        print(f"  ERROR cost documents: {e}")

    save_csv(all_cost_docs, "cost_documents.csv")

    print("\n--- Summary: Cost documents ---")
    print(f"Cost documents: {len(all_cost_docs)}")
    payouts_all = [cd for cd in all_cost_docs if cd.get("is_payout")]
    print(f"  Payouts to owner: {len(payouts_all)}")
    print(f"  Cost documents: {len(all_cost_docs) - len(payouts_all)}")

    # === SUMOWANIE KWOT ===
    print("\n" + "=" * 60)
    print("SUMY KWOT")
    print("=" * 60)

    # Operacje najemców
    total_income = sum(op.get("income") or 0 for op in all_operations if op.get("income"))
    total_expense = sum(op.get("expense") or 0 for op in all_operations if op.get("expense"))
    print(f"Operacje najemców:")
    print(f"  Przychody (wpłaty):     {total_income:>12.2f} zł")
    print(f"  Rozchody (faktury):     {total_expense:>12.2f} zł")
    print(f"  Saldo:                  {total_income + total_expense:>12.2f} zł")

    # Finanse właściciela
    total_charges = sum(f.get("charge") or 0 for f in all_finances if f.get("charge"))
    total_payments = sum(f.get("payment") or 0 for f in all_finances if f.get("payment"))
    print(f"\nFinanse właściciela:")
    print(f"  Należności (koszty):    {total_charges:>12.2f} zł")
    print(f"  Wpłaty (rozliczenia):   {total_payments:>12.2f} zł")
    print(f"  Saldo:                  {total_charges + total_payments:>12.2f} zł")

    # Dokumenty kosztowe
    total_costs = sum(cd.get("amount") or 0 for cd in all_cost_docs if not cd.get("is_payout") and cd.get("amount"))
    total_payouts = sum(cd.get("amount") or 0 for cd in all_cost_docs if cd.get("is_payout") and cd.get("amount"))
    print(f"\nDokumenty kosztowe:")
    print(f"  Koszty:                 {total_costs:>12.2f} zł")
    print(f"  Wypłaty do właściciela: {total_payouts:>12.2f} zł")
    print(f"  Saldo:                  {total_costs + total_payouts:>12.2f} zł")

    # Podsumowanie ogólne
    print(f"\n" + "=" * 60)
    print("PODSUMOWANIE OGÓLNE")
    print("=" * 60)
    print(f"  Łączne przychody:       {total_income + total_payments + total_payouts:>12.2f} zł")
    print(f"  Łączne koszty:          {abs(total_expense) + abs(total_charges) + abs(total_costs):>12.2f} zł")
    print(f"  Saldo końcowe:          {total_income + total_expense + total_charges + total_payments + total_costs + total_payouts:>12.2f} zł")

    print(f"\nData saved to: {os.path.abspath(OUT_DIR)}")


if __name__ == "__main__":
    main()
