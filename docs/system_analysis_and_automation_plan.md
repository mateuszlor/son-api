# System Obsługi Najmu (SON) — System Analysis and Automation Plan

## 1. System identification

- **Name:** "System Obsługi Najmu" (SON), version 3 (SON3).
- **Type:** **Commercial SaaS**, not owned by the property management company. Vendor: **System Obsługi Najmu sp. z o.o.** (Kraków, KRS 0000604035, NIP 9452191405), website: systemobsluginajmu.pl / info.systemobsluginajmu.pl.
- **Your instance:** `https://your-panel.example.com/` is a ed instance. the property management company is a SON client/administrator managing your apartment; you have access to the **Owner Panel** (or tenant panel depending on role).
- **Documentation:** przewodnik.systemobsluginajmu.pl (categories: Receivables and invoices, Finance and costs, Owners and management reports, Communication, Integrations).
- **Roles:** Administrator (the property management company), Owner (you), Tenant, Contractor, Accountant.

### Key modules (owner panel)
Home (occupancy, revenue, unpaid documents, recent invoices), Tenants, Estates, **Finance** (Tenant settlements / Manager settlements), Meters, Messages, Tickets, Documents, Reports (account transaction summary, sales register, accounting document list with InFakt export, cost documents).

## 2. What the provided requests reveal

Endpoints are **administrative panel** (the property management company), not public API:

| Request | Meaning |
|---|---|
| `POST /tenants/index` | DataTables server-side; tenant list with filters (active), columns: `tenant_id`, `user_fullname`, `address`, `user_active`, `user_balance`; pagination/sorting. |
| `GET /tenants/tenant-operations/{id}` | HTML fragment with operation history (payments, deposits, charges) and balance. |
| `POST /tenants/insurances/{id}` | JSON with insurances (e.g., PZU, policy number, expiry date). |
| `GET /tenants/tenant-liabilities/{id}` | HTML fragment with liabilities/invoices (invoice number, items: rent, utilities, parking, amounts, early payment discounts). |

**Authentication:** session (cookie `SON_SESSID`) + CSRF token (`X-CSRF-TOKEN`) + header `X-Requested-With: XMLHttpRequest`. This is a web application (PHP/Apache). CSRF token without active session is useless — **do not share tokens/sessions**.

**Note:** `/tenants/*` is administrator level. Owner panel has read-only access to approved documents.

## 3. Automation possibilities

### A. Built into SON (configured by the property management company administrator)
- **Future receivables** — automatic, recurring invoice/charge generation for rent.
- **Automatic messages** (email/SMS): welcome email, new financial document notification, payment reminder.
- **Automatic payment booking** (if enabled).
- **KSeF** (costs), **report export to InFakt**.
- **Action:** ask the property management company to enable these features and **approve invoices** (owner sees only approved ones).

### B. Official SON API (requires admin access — not available to owners)
The public SON API (`s3api.systemobsluginajmu.pl/v2`) requires an `X-SON-TOKEN` which is only available to account administrators. As an owner, you cannot generate this token. The internal AJAX endpoints documented in `complete_endpoint_documentation.md` are the practical alternative.

### C. When no API token/permissions (owner panel)
- **Web scraping / browser automation** (Playwright/Puppeteer/Selenium): login, download invoice PDFs, read balances/statuses, save to CSV/Excel/accounting.
- **Email automation:** rules on SON notifications (new document, payment reminder) → parse → entry to spreadsheet/accounting/Slack/Telegram.
- **Report export** (monthly "Accounting document list" → InFakt) + consolidation script.

### D. Rental monitoring — metrics and alerts
- Tenant balance, unpaid/partially paid/overdue documents, payment deadlines.
- Insurances: alert before policy expiry.
- Tickets: open/pending.
- Meters and utilities: readings.
- Deposit: balance.
- Monthly reports: transaction summary, sales register, accounting documents, costs.

### E. Accounting automation
- Download invoices from panel → InFakt/wFirma/Fakturownia (SON supports export to InFakt).
- KSeF for costs.
- Reconciliation of payments with bank statement (automatic payment booking in SON).

## 4. What I still need

1. **Role and access:** owner panel or admin? Do you have access to generate API tokens in SON account settings?
2. **the property management company consent** for integration/API (owner often lacks permissions).
3. **List of processes** to automate (invoices, balances, insurances, meters, tickets, reports).
4. **Target tools:** InFakt/wFirma/Excel/Google Sheets/Notion; notification channel (email/Telegram/Slack).
5. **Script data:** login/password or token, sample data, consent for personal data processing (GDPR) and compliance with SON terms.
6. **Should I prepare a script** (Python) for API or scraping? If so — provide secure way to pass secrets (environment variables).

## 5. Proposed implementation plan

1. Obtain access (owner panel + possibly API token). Check modules and invoice approval.
2. Enable built-in automations (future receivables, notifications) — through the property management company.
3. Configure report export and InFakt integration.
4. Build script/Make scenario: polling API/scraping → spreadsheet/accounting → alerts.
5. Testing and error monitoring (rate limits, concurrency).

## 6. Security
- Do not share CSRF tokens/sessions; store secrets in environment variables; use HTTPS.
- Rate limiting: 120 req/window, concurrency limit per token — implement retry with `Retry-After`.
- GDPR: tenant data is personal data; automation requires legal basis and administrator consent (the property management company).