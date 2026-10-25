"""Shared client library for SON panel.

Contains SONInternalClient class with all endpoints and parsers.
Used by fetch_all_data.py and fetch_latest_invoice.py.

Requirements:
  pip install requests beautifulsoup4 python-dotenv
"""

import os
import re
import time
import json
import csv
from datetime import datetime, date
from bs4 import BeautifulSoup
import requests

# Load variables from .env file (if exists)
_env_loaded = False
try:
    from dotenv import load_dotenv
    load_dotenv()
    _env_loaded = True
except ImportError:
    pass

if not _env_loaded:
    # Manual .env parser (no external dependencies)
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(_env_path):
        _env_path = ".env"
    if os.path.exists(_env_path):
        with open(_env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#"):
                    continue
                if "=" in _line:
                    _key, _val = _line.split("=", 1)
                    _key = _key.strip()
                    _val = _val.strip().strip('"').strip("'")
                    if _key and _key not in os.environ:
                        os.environ[_key] = _val

BASE = os.getenv("SON_PANEL_URL")
if not BASE:
    raise SystemExit("Ustaw SON_PANEL_URL w pliku .env (np. https://your-panel.example.com)")
BASE = BASE.rstrip("/")
LOGIN = os.getenv("SON_LOGIN")
PASSWORD = os.getenv("SON_PASSWORD")
OUT_DIR = os.getenv("SON_OUT_DIR", "./invoices")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_pln(s):
    if s is None:
        return None
    s = str(s).strip().replace("\xa0", " ").replace(" ", "").replace("zł", "").replace("PLN", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def extract_tables_with_links(html):
    """Extract HTML tables. Returns list of dicts: headers, rows, links."""
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for table in soup.find_all("table"):
        rows = []
        links = []
        for tr_idx, tr in enumerate(table.find_all("tr")):
            cells = []
            for td_idx, cell in enumerate(tr.find_all(["td", "th"])):
                cells.append(cell.get_text(strip=True))
                a = cell.find("a", href=True)
                if a:
                    links.append((tr_idx, td_idx, a["href"], a.get_text(strip=True)))
            if cells:
                rows.append(cells)
        if rows:
            result.append({"headers": rows[0] if rows else [], "rows": rows, "links": links})
    return result


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SONInternalClient:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
        })
        self.csrf = None
        self._login()

    def _login(self):
        self.s.get(f"{BASE}/", timeout=30)
        import urllib.parse
        form_data = urllib.parse.urlencode(
            {"login": (LOGIN or "").strip(), "password": (PASSWORD or "").strip()},
            encoding="utf-8",
        )
        r = self.s.post(
            f"{BASE}/login?backUrl=/",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            allow_redirects=True,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Login failed: HTTP {r.status_code}")
        if "Zaloguj" in r.text and "login-form" in r.text:
            raise RuntimeError("Login failed: invalid email or password. Check .env\nServer response (first 200 chars): " + r.text[:200].replace("\n", " "))
        self._refresh_csrf(r.text)
        if not self.csrf:
            for path in ["/", "/tenants/index", "/finances/index"]:
                try:
                    r2 = self.s.get(f"{BASE}{path}", timeout=30)
                    self._refresh_csrf(r2.text)
                    if self.csrf:
                        break
                except Exception:
                    continue
        if not self.csrf:
            raise RuntimeError("Logged in but CSRF token not found. Check page structure.")

    def _refresh_csrf(self, html):
        """CSRF token is in meta tag: <meta name="csrf-token" content="..."> in <head>."""
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", {"name": "csrf-token"})
        if meta and meta.get("content"):
            self.csrf = meta["content"]
            return
        for m in soup.find_all("meta"):
            name = (m.get("name") or "").lower()
            if "token" in name and m.get("content"):
                self.csrf = m["content"]
                return

    def _ensure_csrf(self):
        if not self.csrf:
            r = self.s.get(f"{BASE}/", timeout=30)
            self._refresh_csrf(r.text)
            if not self.csrf:
                raise RuntimeError("No CSRF token")

    def _ajax_headers(self):
        h = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        if self.csrf:
            h["X-CSRF-TOKEN"] = self.csrf
        return h

    def _post(self, path, data=None, retries=3):
        self._ensure_csrf()
        for attempt in range(retries):
            r = self.s.post(f"{BASE}{path}", data=data, headers=self._ajax_headers(), timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 5)))
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r
        raise RuntimeError(f"Max retries exceeded: POST {path}")

    def _get(self, path, retries=3):
        self._ensure_csrf()
        for attempt in range(retries):
            r = self.s.get(f"{BASE}{path}", headers=self._ajax_headers(), timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 5)))
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r
        raise RuntimeError(f"Max retries exceeded: GET {path}")

    def get_tenants(self, page_size=100):
        all_tenants = []
        start = 0
        while True:
            data = {
                "draw": "1", "start": str(start), "length": str(page_size),
                "order[0][column]": "1", "order[0][dir]": "asc",
                "search[value]": "", "search[regex]": "false",
            }
            cols = ["tenant_id", "user_fullname", "address", "user_active", "user_balance"]
            for i, c in enumerate(cols):
                data[f"columns[{i}][data]"] = c
                data[f"columns[{i}][searchable]"] = "true"
                data[f"columns[{i}][orderable]"] = "true"
                data[f"columns[{i}][search][value]"] = ""
                data[f"columns[{i}][search][regex]"] = "false"
            r = self._post("/tenants/index", data=data)
            j = r.json()
            rows = j.get("data", [])
            if not rows:
                break
            all_tenants.extend(rows)
            total = int(j.get("recordsTotal") or j.get("recordsFiltered") or 0)
            start += len(rows)
            if start >= total:
                break
            time.sleep(0.5)
        return all_tenants

    def get_estates(self, page_size=100):
        all_estates = []
        start = 0
        while True:
            data = {
                "draw": "1", "start": str(start), "length": str(page_size),
                "order[0][column]": "1", "order[0][dir]": "asc",
                "search[value]": "", "search[regex]": "false",
            }
            cols = ["estate_id", "address", "estate_details", "estate_access_code", "estate_rental_type", "free_rooms_count"]
            for i, c in enumerate(cols):
                data[f"columns[{i}][data]"] = c
                data[f"columns[{i}][searchable]"] = "true"
                data[f"columns[{i}][orderable]"] = "true"
                data[f"columns[{i}][search][value]"] = ""
                data[f"columns[{i}][search][regex]"] = "false"
            r = self._post("/estates/index", data=data)
            j = r.json()
            rows = j.get("data", [])
            if not rows:
                break
            all_estates.extend(rows)
            total = int(j.get("recordsTotal") or j.get("recordsFiltered") or 0)
            start += len(rows)
            if start >= total:
                break
            time.sleep(0.5)
        return all_estates

    def get_tenant_operations(self, tenant_id):
        r = self._get(f"/tenants/tenant-operations/{tenant_id}/")
        return r.text

    def get_insurances(self, tenant_id):
        r = self._post(f"/tenants/insurances/{tenant_id}")
        try:
            return r.json()
        except Exception:
            return r.text

    def get_tenant_liabilities(self, tenant_id):
        r = self._get(f"/tenants/tenant-liabilities/{tenant_id}/")
        return r.text

    def get_finances(self, page_size=100):
        """Fetch owner finances (cost invoices + payouts) from /finances/index.
        Server-side DataTables via POST. Returns HTML with all records."""
        data = {
            "draw": "1",
            "start": "0",
            "length": str(page_size),
            "order[0][column]": "1",
            "order[0][dir]": "desc",
            "search[value]": "",
            "search[regex]": "false",
        }
        r = self._post("/finances/index", data=data)
        return r.text

    def parse_finances(self, html):
        """Parse finances HTML table (Type, Date, Payment, Charge, Balance, Document, Status, Description)."""
        tables = extract_tables_with_links(html)
        result = []
        for t in tables:
            rows = t["rows"]
            links = t["links"]
            link_map = {}
            for (ri, ci, href, text) in links:
                link_map[(ri, ci)] = (href, text)
            headers = [h.lower() for h in rows[0]] if rows else []
            for ri, row in enumerate(rows[1:], start=1):
                entry = {}
                for ci, cell in enumerate(row):
                    hdr = headers[ci] if ci < len(headers) else f"col_{ci}"
                    val = cell.strip()
                    if "typ" in hdr:
                        entry["type"] = val if val else None
                    elif "data" in hdr:
                        m = re.search(r"(\d{2}/\d{2}/\d{4})", val)
                        entry["date"] = parse_date(m.group(1)) if m else None
                        entry["date_raw"] = m.group(1) if m else val
                    elif "wpł" in hdr or "wplat" in hdr or "payment" in hdr:
                        entry["payment"] = parse_pln(val)
                    elif "należ" in hdr or "nalezn" in hdr or "charge" in hdr:
                        entry["charge"] = parse_pln(val)
                    elif "saldo" in hdr or "balance" in hdr:
                        entry["balance"] = parse_pln(val)
                    elif "dokument" in hdr or "document" in hdr:
                        entry["document"] = val
                        if (ri, ci) in link_map:
                            href, text = link_map[(ri, ci)]
                            entry["pdf_url"] = href
                            entry["document"] = text
                    elif "status" in hdr:
                        entry["status"] = val if val else None
                    elif "opis" in hdr or "description" in hdr:
                        entry["description"] = val if val else None
                if entry.get("date") or entry.get("document") or entry.get("description"):
                    result.append(entry)
        return result

    def parse_operations(self, html, tenant_id, tenant_name):
        tables = extract_tables_with_links(html)
        result = []
        for t in tables:
            rows = t["rows"]
            links = t["links"]
            link_map = {}
            for (ri, ci, href, text) in links:
                link_map[(ri, ci)] = (href, text)
            headers = [h.lower() for h in rows[0]] if rows else []
            for ri, row in enumerate(rows[1:], start=1):
                entry = {"tenant_id": tenant_id, "tenant_name": tenant_name}
                for ci, cell in enumerate(row):
                    hdr = headers[ci] if ci < len(headers) else f"col_{ci}"
                    val = cell.strip()
                    if "typ" in hdr:
                        entry["type"] = val if val else None
                    elif "data" in hdr:
                        m = re.search(r"(\d{2}/\d{2}/\d{4})", val)
                        entry["date"] = parse_date(m.group(1)) if m else None
                        entry["date_raw"] = m.group(1) if m else val
                    elif "przych" in hdr:
                        entry["income"] = parse_pln(val)
                    elif "rozch" in hdr:
                        entry["expense"] = parse_pln(val)
                    elif "saldo" in hdr:
                        entry["balance"] = parse_pln(val)
                    elif "dokument" in hdr:
                        entry["document"] = val
                        if (ri, ci) in link_map:
                            href, text = link_map[(ri, ci)]
                            entry["pdf_url"] = href
                            entry["document"] = text
                    elif "status" in hdr:
                        entry["status"] = val if val else None
                    elif "opis" in hdr:
                        entry["description"] = val if val else None
                if entry.get("date") or entry.get("document") or entry.get("description"):
                    result.append(entry)
        return result

    def parse_liabilities(self, html, tenant_id, tenant_name):
        tables = extract_tables_with_links(html)
        result = []
        for t in tables:
            rows = t["rows"]
            headers = [h.lower() for h in rows[0]] if rows else []
            for row in rows[1:]:
                entry = {"tenant_id": tenant_id, "tenant_name": tenant_name}
                for ci, cell in enumerate(row):
                    hdr = headers[ci] if ci < len(headers) else f"col_{ci}"
                    val = cell.strip()
                    if "nazwa" in hdr or "pozyc" in hdr:
                        entry["item_name"] = val
                    elif "przed rabat" in hdr or "kwota przed" in hdr:
                        entry["amount_before_discount"] = parse_pln(val)
                    elif "netto po" in hdr or "po rabat" in hdr:
                        entry["amount_after_discount"] = parse_pln(val)
                    elif "suma rabat" in hdr:
                        entry["total_discount"] = parse_pln(val)
                    elif "szczeg" in hdr:
                        entry["discount_details"] = val if val else None
                    elif "nalicz" in hdr:
                        entry["billing_frequency"] = val
                    elif "okres" in hdr:
                        entry["period"] = val
                if entry.get("item_name"):
                    result.append(entry)
        return result

    def parse_insurances(self, data, tenant_id, tenant_name):
        result = []
        items = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
        for item in items:
            entry = {
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                "id": item.get("id"),
                "company": item.get("company"),
                "policy_number": item.get("number"),
                "status": item.get("status"),
                "start_date": parse_date(item.get("date_start")) if item.get("date_start") else None,
                "end_date": parse_date(item.get("date_end")) if item.get("date_end") else None,
                "estate_id": item.get("estate_id"),
                "room_id": item.get("room_id"),
                "created_at": item.get("created_at"),
            }
            result.append(entry)
        return result

    def detect_new_invoices(self, tenant_id, tenant_name, known_invoice_numbers):
        html = self.get_tenant_operations(tenant_id)
        ops = self.parse_operations(html, tenant_id, tenant_name)
        new_invoices = []
        for op in ops:
            if op.get("type") in ("FV", "KR") and op.get("document"):
                inv_num = op["document"]
                if inv_num not in known_invoice_numbers:
                    new_invoices.append(op)
                    known_invoice_numbers.add(inv_num)
        return new_invoices, known_invoice_numbers, ops

    def get_estate_cost_documents(self, estate_id):
        """Fetch cost documents for an estate. Returns HTML."""
        r = self._get(f"/estates/estate-cost-documents/{estate_id}/")
        return r.text

    def parse_estate_cost_documents(self, html, owner_name=None):
        """Parse estate cost documents table.
        Columns: Date added, Sale date, Seller, Number, Amount, Payment deadline, Payment date, (download link)."""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": "estate-cost-documents-table"})
        if not table:
            table = soup.find("table")
        result = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells or len(cells) < 7:
                continue
            # Skip header row
            if cells[0].name == "th":
                continue
            entry = {}
            # Column 0: Date added
            entry["date_added"] = parse_date(cells[0].get_text(strip=True))
            entry["date_added_raw"] = cells[0].get_text(strip=True)
            # Column 1: Sale date
            entry["sale_date"] = parse_date(cells[1].get_text(strip=True))
            entry["sale_date_raw"] = cells[1].get_text(strip=True)
            # Column 2: Seller
            entry["seller"] = cells[2].get_text(strip=True)
            # Payout: if seller is the owner (money going to owner)
            if owner_name and entry["seller"] and owner_name.lower() in entry["seller"].lower():
                entry["is_payout"] = True
            else:
                entry["is_payout"] = False
            # Column 3: Number
            entry["number"] = cells[3].get_text(strip=True)
            # Column 4: Amount
            entry["amount"] = parse_pln(cells[4].get_text(strip=True))
            # Column 5: Payment deadline
            entry["payment_deadline"] = parse_date(cells[5].get_text(strip=True))
            entry["payment_deadline_raw"] = cells[5].get_text(strip=True)
            # Column 6: Payment date
            pd_text = cells[6].get_text(strip=True)
            entry["payment_date"] = parse_date(pd_text) if pd_text and pd_text.lower() not in ("nie opłacono", "nie oplacono", "nieopłacono") else None
            entry["payment_date_raw"] = pd_text
            # Column 7: Download link
            a = tr.find("a", href=True)
            if a:
                entry["download_zip_url"] = a["href"]
                m = re.search(r"object_id=(\d+)", a["href"])
                if m:
                    entry["cost_document_id"] = m.group(1)
            if entry.get("date_added") or entry.get("seller") or entry.get("number") or entry.get("amount") is not None:
                result.append(entry)
        return result

    def get_cost_document_download_url(self, cost_document_id):
        """Get the actual download URL for a cost document.
        Step 1: GET /download-files-zip/?object=costDocument&object_id={id} -> JSON redirect
        Step 2: GET /download-file/?object=costDocument&object_id={id}&file_id={file_id} -> PDF"""
        r = self._get(f"/download-files-zip/?object=costDocument&object_id={cost_document_id}")
        try:
            data = r.json()
            if data.get("type") == "redirect" and data.get("url"):
                return data["url"]
        except Exception:
            pass
        return None

    def download_cost_document(self, cost_document_id, dest_path):
        """Download a cost document PDF (two-step: redirect then download)."""
        url = self.get_cost_document_download_url(cost_document_id)
        if not url:
            print(f"    No download URL for cost document {cost_document_id}")
            return False
        return self.download_file(url, dest_path)

    def normalize_url(self, url):
        url = url.strip()
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return BASE + url
        return BASE + "/" + url

    def download_file(self, url, dest_path):
        full_url = self.normalize_url(url)
        try:
            r = self.s.get(full_url, headers=self._ajax_headers(), timeout=60, stream=True)
            if r.status_code == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                print(f"    HTTP {r.status_code}: {full_url}")
                return False
        except Exception as e:
            print(f"    Download error {full_url}: {e}")
            return False

    def fetch_invoice_pdfs(self, operations, tenant_id, out_dir):
        downloaded = []
        tenant_dir = os.path.join(out_dir, f"pdfs_{tenant_id}")
        os.makedirs(tenant_dir, exist_ok=True)
        seen = set()
        pdf_links = []
        for op in operations:
            url = op.get("pdf_url")
            if url and url not in seen:
                seen.add(url)
                pdf_links.append((url, op.get("document", "invoice")))
        print(f"  Found {len(pdf_links)} PDF links")
        for url, doc_num in pdf_links:
            safe_name = re.sub(r"[^\w\-]", "_", str(doc_num)) if doc_num else "invoice"
            fname = f"{safe_name}.pdf"
            dest = os.path.join(tenant_dir, fname)
            # Skip if already downloaded (don't create duplicates)
            if os.path.exists(dest):
                print(f"    Already exists: {os.path.basename(dest)}")
                downloaded.append(dest)
                continue
            if self.download_file(url, dest):
                downloaded.append(dest)
                print(f"    Downloaded: {os.path.basename(dest)}")
        return downloaded
