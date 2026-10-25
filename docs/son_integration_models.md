# SON Panel Integration — Data Models and Description

## 1. Authentication

### Login
```
POST /login?backUrl=/
Content-Type: application/x-www-form-urlencoded

Body: login={email}&password={password}
```
- Response: redirect (302) to home page or re-display of login form (error).
- Session: cookie `SON_SESSID` (expires after inactivity).
- After login, every page contains a CSRF token in a meta tag in `<head>`.

### CSRF token
```
Header: X-CSRF-TOKEN: {token}
```
- Required for all AJAX requests (`X-Requested-With: XMLHttpRequest`).
- Token is bound to session — changes on new login.
- Without valid token: HTTP 403 or redirect to login.

### Required headers for AJAX
```
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
X-CSRF-TOKEN: {token}
Content-Type: application/x-www-form-urlencoded; charset=UTF-8  (for POST)
```

---

## 2. Endpoints

### 2.1 Tenant list
```
POST /tenants/index
```
**Request body (DataTables):**
| Parameter | Type | Description |
|-----------|------|-------------|
| draw | int | DataTables request number |
| start | int | Offset (pagination) |
| length | int | Page size (max 50-100) |
| order[0][column] | int | Sort column index (1 = user_fullname) |
| order[0][dir] | string | Direction: asc/desc |
| search[value] | string | Global search |
| columns[i][data] | string | Column name |
| columns[i][searchable] | bool | Whether column is searchable |
| columns[i][orderable] | bool | Whether column is sortable |
| columns[i][search][value] | string | Column filter (e.g., "1" for active) |
| columns[i][search][regex] | bool | Regex in filter |

**Columns:**
| Index | Data | Description |
|-------|------|-------------|
| 0 | tenant_id | Tenant ID |
| 1 | user_fullname | Full name |
| 2 | address | Accommodation address |
| 3 | user_active | Active (1/0) |
| 4 | user_balance | Balance |

**Response (JSON):**
```json
{
  "draw": "1",
  "recordsTotal": "2",
  "recordsFiltered": "2",
  "data": [
    {
      "tenant_id": "1234",
      "user_fullname": "Tenant Name",
      "address": "City, Street 1 m. 1",
      "user_active": "1",
      "user_balance": "1234,56",
      "tenant_balance": "1234",
      "tenant_agreement_status": "8",
      "tags": "30dni",
      "estate_id": "999",
      "eah_owner_fullname": "Owner Name",
      "eah_owner_id": "5678"
    }
  ]
}
```

### 2.2 Tenant operations
```
GET /tenants/tenant-operations/1234/
```
**Note:** `?_={timestamp}` parameter (jQuery cache-buster) is **optional** — endpoint works identically without it. Accept header does not affect response format (always HTML).

**Response:** HTML fragment with operations table.

**Table columns:**
| Column | Type | Description |
|--------|------|-------------|
| Type | string | Operation type (payment, deposit, charge, etc.) |
| Date | date | Operation date (DD/MM/YYYY) |
| Income | decimal | Income amount (PLN) |
| Expense | decimal | Expense amount (PLN) |
| Balance | decimal | Balance after operation (PLN) |
| Document | string | Document number / PDF link (`/finances/download/{id}`) |
| Status | string | "Opłacona" (Paid) or empty |
| Description | string | Operation description |

### 2.3 Tenant liabilities (invoices)
```
GET /tenants/tenant-liabilities/1234/
```
**Note:** `?_={timestamp}` parameter is **optional**.

**Response:** HTML fragment with two tables:

**Table 1 — Liabilities:**
| Column | Type | Description |
|--------|------|-------------|
| Item name | string | Liability name (rent, utilities, parking) |
| Amount before discount | decimal | Gross amount before discounts |
| Amount after discount | decimal | Net amount after discounts |
| Total discount | decimal | Total discount value |
| Discount details | string | Discount description (e.g., "Early payment discount: 1234,56") |
| Billing frequency | string | Monthly |
| Period | string | Validity period (e.g., "28/10/2024 - 27/10/2026") |

### 2.4 Tenant insurances
```
POST /tenants/insurances/1234
```
**Response (JSON):**
```json
{
  "draw": null,
  "data": [
    {
      "id": "537",
      "user_id": "1234",
      "estate_id": null,
      "room_id": null,
      "reference_id": null,
      "status": "4",
      "date_start": null,
      "date_end": "2027-01-12",
      "company": "PZU",
      "number": "POL123456",
      "amount": null,
      "rent": null,
      "is_simpl_rent": "0",
      "policy_id": null,
      "invitation_url": null,
      "created_at": "2026-01-12 14:40:47",
      "updated_at": "2026-01-12 14:40:47",
      "add_info_from_simpl_at": null,
      "estate_address": null,
      "user_fullname": "Tenant Name"
    }
  ],
  "recordsTotal": "2",
  "recordsFiltered": "2"
}
```

### 2.5 Estate cost documents
```
GET /estates/estate-cost-documents/{estate_id}/
```
**Response:** HTML fragment with cost documents table.

**Table columns:**
| Column | Type | Description |
|--------|------|-------------|
| Date added | date | Date document was added (DD/MM/YYYY) |
| Sale date | date | Date of sale/service (DD/MM/YYYY) |
| Seller | string | Who issued the document (the property management company, WM, PGE, or owner) |
| Number | string | Document number (e.g., cost invoice number) |
| Amount | decimal | Amount (PLN) |
| Payment deadline | date | Payment deadline (DD/MM/YYYY) |
| Payment date | date/string | Payment date or "Not paid" |
| (actions) | HTML | Download link (if available) |

**Payout detection:** If seller name contains owner name → `is_payout = True`. Payouts are entries where the owner is the seller (money to owner).

### 2.6 Download cost document (two-step)
```
GET /download-files-zip/?object=costDocument&object_id={cost_document_id}
```
**Response:** JSON redirect `{"type":"redirect","url":"\/download-file\/?object=costDocument&object_id={id}&file_id={file_id}"}`

```
GET /download-file/?object=costDocument&object_id={id}&file_id={file_id}
```
**Response:** binary PDF.

### 2.7 Estate insurances
```
GET /estates/estate-insurances/{estate_id}/
```
**Response:** HTML fragment with insurance table.

### 2.8 Estate meters
```
GET /estates/estate-meters/{estate_id}/
```
**Response:** HTML fragment with meter readings (water, electricity, gas).

### 2.9 Estate tickets
```
GET /estates/estate-tickets/{estate_id}/
```
**Response:** HTML fragment with ticket table.

### 2.10 Estate controls
```
GET /estates/estate-controls/{estate_id}/
```
**Response:** HTML fragment with control/inspection table.

### 2.11 Estate basic info
```
GET /estates/estate-basic-info/{estate_id}/
```
**Response:** HTML fragment with estate details (address, floor, area, rooms, access code, etc.)

### 2.12 Estate accommodation
```
GET /estates/estate-accomodation/{estate_id}/reload/estate_accomodation
```
**Response:** HTML fragment with accommodation table.

### 2.5 Download invoice PDF
Links are embedded in HTML response from `/tenants/tenant-operations/{id}/` as:
```html
<a href="/finances/download/12345">1/FV/01/01/2025/0001</a>
```
Pattern: `/finances/download/12345` where `finance_id` is the internal document ID.

**Download:**
```
GET /finances/download/12345
Headers: X-Requested-With: XMLHttpRequest, X-CSRF-TOKEN: {token}
Response: application/pdf (binary)
```
**Tested:** returns `application/pdf`, 113,151 bytes.

### 2.6 Download tenant file
```
GET /download-file/?object=user&object_id=1234&file_id=12345
```
- **Parameters:** object (user/estate/owner), object_id, file_id
- **Returns:** file (PDF/image/document). **Tested: returns application/pdf, 239,785 bytes.**

---

## 3. Data models (Python dataclasses)

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List

@dataclass
class Tenant:
    tenant_id: int
    user_fullname: str
    address: str
    user_active: bool
    user_balance: float

@dataclass
class Operation:
    tenant_id: int
    tenant_name: str
    type: Optional[str] = None          # FV, KR, or None (payment)
    date: Optional[date] = None
    date_raw: Optional[str] = None
    income: Optional[float] = None
    expense: Optional[float] = None
    balance: Optional[float] = None
    document: Optional[str] = None     # invoice number or operation ID
    pdf_url: Optional[str] = None      # /finances/download/{id}
    status: Optional[str] = None       # "Opłacona" or None
    description: Optional[str] = None

@dataclass
class Liability:
    tenant_id: int
    tenant_name: str
    item_name: Optional[str] = None
    amount_before_discount: Optional[float] = None
    amount_after_discount: Optional[float] = None
    total_discount: Optional[float] = None
    discount_details: Optional[str] = None
    billing_frequency: Optional[str] = None
    period: Optional[str] = None

@dataclass
class Insurance:
    tenant_id: int
    tenant_name: str
    id: Optional[str] = None
    company: Optional[str] = None
    policy_number: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    estate_id: Optional[str] = None
    room_id: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class TenantFull:
    tenant: Tenant
    operations: List[Operation] = field(default_factory=list)
    liabilities: List[Liability] = field(default_factory=list)
    insurances: List[Insurance] = field(default_factory=list)
    pdf_paths: List[str] = field(default_factory=list)
```

## 4. TypeScript interfaces

```typescript
interface Tenant {
  tenant_id: number;
  user_fullname: string;
  address: string;
  user_active: boolean;
  user_balance: number;
}

interface Operation {
  tenant_id: number;
  tenant_name: string;
  type: string | null;
  date: string | null;
  date_raw: string | null;
  income: number | null;
  expense: number | null;
  balance: number | null;
  document: string | null;
  pdf_url: string | null;
  status: string | null;
  description: string | null;
}

interface Liability {
  tenant_id: number;
  tenant_name: string;
  item_name?: string;
  amount_before_discount?: number | null;
  amount_after_discount?: number | null;
  total_discount?: number | null;
  discount_details?: string | null;
  billing_frequency?: string;
  period?: string;
}

interface Insurance {
  tenant_id: number;
  tenant_name: string;
  id?: string;
  company?: string;
  policy_number?: string;
  status?: string;
  start_date?: string | null;
  end_date?: string | null;
  estate_id?: string | null;
  room_id?: string | null;
  created_at?: string;
}

interface DataTablesResponse<T> {
  draw: string;
  recordsTotal: string;
  recordsFiltered: string;
  data: T[];
}
```

## 5. Integration flow

```
1. POST /login → session (SON_SESSID cookie)
2. Extract CSRF token from <meta name="csrf-token" content="..."> in <head>
3. POST /tenants/index (pagination) → tenant list
4. For each tenant:
   a. GET /tenants/tenant-operations/{id}/ → operations (HTML → parse)
   b. GET /tenants/tenant-liabilities/{id}/ → liabilities (HTML → parse)
   c. POST /tenants/insurances/{id} → insurances (JSON → parse)
   d. Download PDFs from /finances/download/{id} links
5. Aggregate, save CSV/JSON, generate alerts
6. Scheduled execution (cron) + re-login on session expiry
```

## 6. Alert rules

| Alert | Condition | Source |
|-------|-----------|--------|
| New invoice | Row with Type=FV or KR with unknown document number | tenant-operations |
| Unpaid invoice | Type=FV, Status != "Opłacona" | tenant-operations |
| Overdue invoice | Type=FV, Status != "Opłacona" and date + 14 days < today | tenant-operations |
| Negative balance | user_balance < 0 | /tenants/index |
| No payment this month | No "Przelew" operation with current month name | tenant-operations |
| Insurance expiring | end_date - today <= 30 days | /tenants/insurances |
| Insurance expired | end_date < today | /tenants/insurances |
| No insurance | Insurance list empty for tenant | /tenants/insurances |
| New ticket | Ticket with status "new" or "open" | /helpdesk/index |
| Ticket pending > 7 days | ticket_date_created + 7 days < today and status != "resolved" | /helpdesk/index |
| Tenant agreement ending | tenant_agreement_status indicates end of tenancy | /tenants/index |
| Tenant inactive | user_active = 0 | /tenants/index |
| No accommodation | address is null or "Brak zakwaterowania" | /tenants/index |
| Tag "30dni" | Tag contains "30dni" (tenancy ends in 30 days) | /tenants/index |
| Tag "koniec najmu" | Tag contains "koniec najmu" | /tenants/index |
| Empty rooms | free_rooms_count > 0 | /estates/index |
| New document | New file_id in tenant card | /tenants/view/{id} |
| Unapproved document | Invoice status "unsent" or "pending" | tenant-operations |
| Correction issued | Row with Type=KR | tenant-operations |
| Liability expiring | period end date < today + 30 days | tenant-liabilities |
| Amount changed | amount_after_discount differs from previous run | tenant-liabilities |

## 7. Limitations and notes

- **Internal endpoints** — may change without notice.
- **Session expires** — script must re-login automatically.
- **CSRF token** changes — extracted dynamically from each page.
- **Rate limiting** — unofficial, but panel may block excessive traffic; use 1 req/s.
- **GDPR** — automated tenant data processing requires legal basis.
- **PDF download URL** — pattern `/finances/download/{id}`, confirmed working.
- **Timestamp parameter** `?_={timestamp}` is optional (jQuery cache-buster).
- **Accept header** does not affect response format.
