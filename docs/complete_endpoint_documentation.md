# Complete SON Panel Endpoint Documentation (your-panel.example.com)

## Home and navigation

### GET /
Home page (dashboard). Server-rendered HTML.
- **Returns:** HTML with summary (occupancy, revenue, unpaid documents, recent invoices).

### GET /language/{lang}
Change interface language (pl/en).
- **Parameters:** `lang` = `pl` or `en`
- **Returns:** redirect to previous page.

### GET /logout
Logout. Clears session.
- **Returns:** redirect to login page.

### GET /lock?backUrl={url}
Lock screen. Requires re-login.
- **Parameters:** `backUrl` — URL to return to after unlock.

### GET /index/get-dictionary
Interface translation dictionary (JSON).
- **Returns:** JSON with translations.

---

## Tenants

### POST /tenants/index
Tenant list (DataTables server-side). **Tested: returns JSON.**
- **Request body:** DataTables params (draw, start, length, order, search, columns, tags)
- **Columns:** tenant_id, user_fullname, address, user_active, user_balance (+ additional: tenant_balance, tenant_agreement_status, tags, estate_id, room_name, last_accomodate_*, eah_owner_*, eas_owner_*, reservation_*)
- **Filter:** `columns[3][search][value]=1` for active tenants
- **Response JSON:**
```json
{
  "draw": "1",
  "recordsTotal": "2",
  "recordsFiltered": "2",
  "data": [{ "tenant_id": "1234", "user_fullname": "Tenant Name", "address": "City, Street 1 m. 1", "user_active": "1", "user_balance": "1234,56", "tags": "30dni", "estate_id": "999", "eah_owner_fullname": "Owner Name", "eah_owner_id": "5678", ... }]
}
```

### GET /tenants/view/{tenant_id}
Tenant card (server-rendered HTML). Contains personal data, accommodation, documents, insurances.

### GET /tenants/tenant-operations/{tenant_id}/
Tenant operations. **Tested: returns HTML** (fragment with table).
- **Parameter `?_={timestamp}`:** optional (jQuery cache-buster).
- **Response:** HTML with table (Type, Date, Income, Expense, Balance, Document, Status, Description).
- **Document column:** contains PDF links `/finances/download/{id}` or operation number.

### GET /tenants/tenant-liabilities/{tenant_id}/
Tenant liabilities (recurring charges). **Tested: returns HTML.**
- **Parameter `?_={timestamp}`:** optional.
- **Response:** HTML with table (Item name, Amount before discount, Amount after discount, Total discount, Discount details, Billing frequency, Period).

### POST /tenants/insurances/{tenant_id}
Tenant insurances. **Tested: returns JSON.**
- **Response JSON:**
```json
{
  "draw": null,
  "data": [{ "id": "537", "user_id": "1234", "company": "PZU", "number": "POL123456", "status": "4", "date_start": null, "date_end": "2027-01-12", "estate_id": null, "room_id": null, "created_at": "2026-01-12 14:40:47", ... }],
  "recordsTotal": "2",
  "recordsFiltered": "2"
}
```

### POST /tenants/share-file/
Share file with tenant (AJAX).
- **Parameters:** file_id, tenant_id

### POST /tenants/unshare-file/
Unshare file from tenant (AJAX).

---

## Estates

### POST /estates/index
Estate list (DataTables server-side). **Tested.**
- **Columns:** estate_id, address, estate_details, estate_access_code, estate_rental_type, free_rooms_count
- **Response JSON:** DataTables format with estate data.

### GET /estates/view-estate/{estate_id}
Estate card (server-rendered HTML). Contains details, rooms, tenants, documents, cost documents, insurances, meters, tickets, controls.

### GET /estates/estate-basic-info/{estate_id}/
Estate basic info (AJAX, HTML fragment).
- **Returns:** HTML with estate details (address, floor, area, rooms, access code, etc.)

### GET /estates/estate-insurances/{estate_id}/
Estate insurances (AJAX, HTML table).
- **Returns:** HTML table (insurance name, policy number, etc.)

### GET /estates/estate-accomodation/{estate_id}/reload/estate_accomodation
Estate accommodation (AJAX, HTML table).
- **Returns:** HTML table (room name, area, etc.)

### GET /estates/estate-meters/{estate_id}/
Estate meters (AJAX, HTML).
- **Returns:** HTML with meter readings (water, electricity, gas).

### GET /estates/estate-tickets/{estate_id}/
Estate tickets (AJAX, HTML table).
- **Returns:** HTML table (ticket type, number, description, status).

### GET /estates/estate-controls/{estate_id}/
Estate controls/inspections (AJAX, HTML table).
- **Returns:** HTML table (date, inspector, number of days, etc.)

### GET /estates/estate-cost-documents/{estate_id}/
Estate cost documents (AJAX, HTML table). **Tested.**
- **Returns:** HTML table (Date added, Sale date, Seller, Number, Amount, Payment deadline, Payment date, Download link).
- **Download link:** `/download-files-zip/?object=costDocument&object_id={cost_document_id}` → redirects to `/download-file/?object=costDocument&object_id={id}&file_id={file_id}` → PDF.
- **Cost documents include:** management fee invoices (the property management company), building administration (WM), utility bills (PGE), and **payouts to owner** (where seller = owner name, amount = payout).
- **Payout detection:** if seller name contains owner name → `is_payout = True`.

---

## Finances

### GET /finances/index
Financial documents list (server-rendered HTML with table). Contains PDF download links `/finances/download/{id}`.
- **Table columns:** Type, Date, Payment, Charge, Balance, Document, Status, Description
- **Content:** Management fee invoices (monthly), document settlements (payouts to owner), additional charges.
- **Pagination:** Server-side, 10 records per page. Use POST with `length=100` to get all records.

### GET /finances/download/{finance_id}
Download invoice/document PDF. **Tested: returns application/pdf.**
- **Response:** binary PDF.

### GET /finances/edit-liability/{liability_id}/reload/tenant_liabilities
Edit liability (modal AJAX). Returns edit form.

### POST /finances/send-document/
Send document (AJAX).

### POST /finances/mark-as-approved/
Approve document (AJAX).

### POST /finances/mark-as-disapproved/
Disapprove document (AJAX).

---

## Helpdesk

### POST /helpdesk/index
Ticket list (DataTables server-side). **Tested.**
- **Columns:** id, ticket_date_created, ticket_subject, ticket_description, ticket_state, id
- **Response JSON:** DataTables format.

### GET /helpdesk/view-ticket/{ticket_id}
Ticket details (server-rendered HTML).

---

## Files

### GET /files/index
Document list (server-rendered HTML).

### GET /download-file/?object={type}&object_id={id}&file_id={file_id}
Download file from tenant/estate/owner card. **Tested: returns application/pdf.**
- **Parameters:** object (user/estate/owner/costDocument), object_id, file_id
- **Returns:** file (PDF/image/document).

### GET /download-files-zip/?object=costDocument&object_id={id}
Download cost document (redirect). **Tested.**
- **Returns:** JSON redirect `{"type":"redirect","url":"\/download-file\/?object=costDocument&object_id={id}&file_id={file_id}"}`.

### POST /upload
File upload (multipart/form-data).

### GET /remove-temp-file
Remove temporary file (AJAX).

---

## Owners

### GET /owners/view/{owner_id}
Owner card (server-rendered HTML).

### POST /owners/share-file/
Share file with owner (AJAX).

### POST /owners/unshare-file/
Unshare file from owner (AJAX).

---

## Contractors

### GET /contractors/view/{contractor_id}
Contractor card (server-rendered HTML).

---

## Reports

### GET /reports/index
Reports page (server-rendered HTML). Contains report generation forms.

### Report endpoints (AJAX, data-url)
| Endpoint | Report |
|----------|--------|
| `/reports/sell-registry` | Sales register |
| `/reports/registry-debit-notes` | Accounting notes register |
| `/reports/invoices` | Invoice and charge list |
| `/reports/debit-notes` | Debit notes list |
| `/reports/incomes` | Inflow report |
| `/reports/new-incomes` | Inflow report (new) |
| `/reports/managment` | Sales by rent and other charges |
| `/reports/managment-lump-sum` | Lump-sum rental report [BETA] |
| `/reports/liabilities` | Future charges report |
| `/reports/meters` | Meters report |
| `/reports/mass-payments` | Mass payments |
| `/reports/receivables-report` | Receivables report |
| `/reports/receivables-report/xls` | Export to XLS |
| `/reports/receivables-report/pdf` | Export to PDF |
| `/reports/cost-document` | Cost documents (ZIP/PDF/XLS) |

### Report generation endpoints
| Endpoint | Format |
|----------|--------|
| `/reports_zip_cost-document/owner-report` | ZIP archive with cost documents |
| `/reports_pdf_invoices/owner-report` | PDF invoice report |
| `/reports_pdf_invoices/get-invoice-amount` | Get invoice amount |
| `/reports_converter_invoices/owner-report` | Converter (to InFakt) |
| `/reports_jpkfa3_invoices/owner-report` | JPK FA3 |
| `/reports_txt_invoices/owner-report` | TXT export |
| `/reports_fakturownia_invoices/generate` | Fakturownia generate |
| `/reports_fakturownia_invoices/get-invoice-amount` | Fakturownia amount |
| `/reports_jpk-vat2_invoices/owner-report` | JPK VAT2 |
| `/reports_pdf_incomes/owner-report` | PDF inflow report |

---

## Portlets

### POST /portlets/update
Update portlet order on dashboard (AJAX, drag & drop).

---

## Validators

### GET /validators/pesel
PESEL validation (AJAX, JSON).
- **Parameters:** value

### GET /validators/identity-number
Identity number validation (AJAX, JSON).
- **Parameters:** value

---

## Alerts

### GET /alerts
Get alerts (AJAX, JSON/HTML). Returns 404 without proper parameters.

---

## Tags

### GET /xget/tags/
Get tags list (AJAX, JSON). **Tested.**
- **Returns:** JSON array `[{value, text}]`

---

## Profile

### GET /profile/edit
Profile edit form (server-rendered HTML).

### POST /profile/edit
Save profile changes.

### GET /profile/index
Profile page.

---

## Authentication

### GET /login
Login page (server-rendered HTML). Form fields: `login` (email), `password`.

### POST /login?backUrl=/
Login submission.
- **Body:** `login={email}&password={password}`
- **Success:** redirect to dashboard (302 → 200)
- **Failure:** returns login page (contains "Zaloguj" login button and "login-form" class)
- **Session:** cookie `SON_SESSID`

### CSRF token
- **Location:** `<meta name="csrf-token" content="...">` in `<head>` of every authenticated page.
- **No hidden input field.** No JavaScript variable.
- **Header:** `X-CSRF-TOKEN: {token}` required for all AJAX requests.

---

## Summary — all endpoints (52)

| # | Method | Endpoint | Format | Tested |
|---|--------|----------|--------|--------|
| 1 | GET | / | HTML |  |
| 2 | GET | /language/{lang} | redirect |  |
| 3 | GET | /logout | redirect |  |
| 4 | GET | /lock?backUrl= | HTML |  |
| 5 | GET | /index/get-dictionary | JSON |  |
| 6 | POST | /tenants/index | JSON |  |
| 7 | GET | /tenants/view/{id} | HTML |  |
| 8 | GET | /tenants/tenant-operations/{id}/ | HTML |  |
| 9 | GET | /tenants/tenant-liabilities/{id}/ | HTML |  |
| 10 | POST | /tenants/insurances/{id} | JSON |  |
| 11 | POST | /tenants/share-file/ | JSON | — |
| 12 | POST | /tenants/unshare-file/ | JSON | — |
| 13 | POST | /estates/index | JSON |  |
| 14 | GET | /estates/view-estate/{id} | HTML |  |
| 15 | GET | /estates/estate-basic-info/{id}/ | HTML |  |
| 16 | GET | /estates/estate-insurances/{id}/ | HTML |  |
| 17 | GET | /estates/estate-accomodation/{id}/reload/estate_accomodation | HTML |  |
| 18 | GET | /estates/estate-meters/{id}/ | HTML |  |
| 19 | GET | /estates/estate-tickets/{id}/ | HTML |  |
| 20 | GET | /estates/estate-controls/{id}/ | HTML |  |
| 21 | GET | /estates/estate-cost-documents/{id}/ | HTML |  |
| 22 | GET | /xget/empty-rooms/ | JSON/HTML | — |
| 23 | GET | /xget/add-readings-table/ | HTML | — |
| 24 | GET | /xget/reading-validate/ | JSON | — |
| 25 | GET | /finances/index | HTML |  |
| 26 | GET | /finances/download/{id} | PDF |  |
| 27 | GET | /finances/edit-liability/{id}/reload/tenant_liabilities | HTML | — |
| 28 | POST | /finances/send-document/ | JSON | — |
| 29 | POST | /finances/mark-as-approved/ | JSON | — |
| 30 | POST | /finances/mark-as-disapproved/ | JSON | — |
| 31 | POST | /helpdesk/index | JSON |  |
| 32 | GET | /helpdesk/view-ticket/{id} | HTML |  |
| 33 | GET | /files/index | HTML |  |
| 34 | GET | /download-file/?object=...&object_id=...&file_id=... | file |  |
| 35 | GET | /download-files-zip/?object=costDocument&object_id={id} | redirect |  |
| 36 | POST | /upload | JSON | — |
| 37 | GET | /remove-temp-file | JSON | — |
| 38 | GET | /owners/view/{id} | HTML | — |
| 39 | POST | /owners/share-file/ | JSON | — |
| 40 | POST | /owners/unshare-file/ | JSON | — |
| 41 | GET | /contractors/view/{id} | HTML | — |
| 42 | GET | /reports/index | HTML |  |
| 43 | GET | /reports/{type} | HTML |  |
| 44 | POST | /reports_*/owner-report | various | — |
| 45 | POST | /portlets/update | JSON | — |
| 46 | GET | /validators/pesel | JSON | — |
| 47 | GET | /validators/identity-number | JSON | — |
| 48 | GET | /alerts | — | — |
| 49 | GET | /xget/tags/ | JSON |  |
| 50 | GET | /profile/edit | HTML |  |
| 51 | POST | /profile/edit | redirect |  |
| 52 | GET | /profile/index | HTML | — |
| 53 | GET/POST | /login | HTML/redirect |  |

**Tested:** 30 endpoints
**Untested (—):** 23 endpoints

### Tested endpoints (detailed)

| # | Endpoint | Result |
|---|----------|--------|
| 1 | `POST /tenants/index` | 200, JSON, 2 tenants |
| 2 | `GET /tenants/tenant-operations/{id}/` | 200, HTML, 53 operations, PDF links |
| 3 | `GET /tenants/tenant-liabilities/{id}/` | 200, HTML, 3 liabilities |
| 4 | `POST /tenants/insurances/{id}` | 200, JSON, 2 insurances |
| 5 | `GET /finances/download/{id}` | 200, application/pdf, 113,151 bytes |
| 6 | `GET /download-file/?object=user&object_id={id}&file_id={file_id}` | 200, application/pdf, 239,785 bytes |
| 7 | `POST /estates/index` | 200, JSON, DataTables |
| 8 | `POST /helpdesk/index` | 200, JSON, DataTables |
| 9 | `GET /xget/tags/` | 200, JSON, tag list |
| 10 | `GET /` (dashboard) | 200, HTML |
| 11 | `GET /tenants/index` (page) | 200, HTML, DataTables |
| 12 | `GET /estates/index` (page) | 200, HTML, DataTables |
| 13 | `GET /estates/view-estate/{id}` | 200, HTML, estate card |
| 14 | `GET /tenants/view/{id}` | 200, HTML, tenant card + download links |
| 15 | `GET /finances/index` | 200, HTML, 58 records, PDF links |
| 16 | `GET /helpdesk/view-ticket/{id}` | 200, HTML, ticket details |
| 17 | `GET /reports/index` | 200, HTML, report forms |
| 18 | `GET /files/index` | 200, HTML, document list |
| 19 | `GET /profile/edit` | 200, HTML, profile form |
| 20 | `GET /index/get-dictionary` | 200, JSON, translations |
| 21 | `GET /estates/estate-basic-info/{id}/` | 200, HTML, estate details |
| 22 | `GET /estates/estate-insurances/{id}/` | 200, HTML, insurance table |
| 23 | `GET /estates/estate-meters/{id}/` | 200, HTML, meter readings |
| 24 | `GET /estates/estate-tickets/{id}/` | 200, HTML, ticket table |
| 25 | `GET /estates/estate-controls/{id}/` | 200, HTML, controls table |
| 26 | `GET /estates/estate-cost-documents/{id}/` | 200, HTML, 96 cost documents |
| 27 | `GET /estates/estate-accomodation/{id}/reload/estate_accomodation` | 200, HTML, accommodation |
| 28 | `GET /download-files-zip/?object=costDocument&object_id={id}` | 200, JSON redirect |
| 29 | `GET /download-file/?object=costDocument&object_id={id}&file_id={file_id}` | 200, application/pdf, 619,181 bytes |
| 30 | `GET /finances/index` (POST, length=100) | 200, HTML, 58 records |

### Key facts

- **CSRF token**: `<meta name="csrf-token" content="...">` in `<head>` — no hidden input, no JS variable.
- **Timestamp `?_=`**: optional (jQuery cache-buster).
- **Accept header**: does not affect response format.
- **JSON vs HTML**: determined by endpoint, not by headers.
- **PDF download (finances)**: `/finances/download/{finance_id}` → `application/pdf`.
- **PDF download (cost documents)**: two-step: `/download-files-zip/?object=costDocument&object_id={id}` → JSON redirect → `/download-file/?object=costDocument&object_id={id}&file_id={file_id}` → `application/pdf`.
- **File download (tenant)**: `/download-file/?object=user&object_id={id}&file_id={file_id}` → file.
- **Session**: cookie `SON_SESSID`, expires after inactivity.
- **Rate limiting**: unofficial, use 1 req/s.
- **Payouts**: tracked in estate cost documents where seller = owner name. Not in finances table.