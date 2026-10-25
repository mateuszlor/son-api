# SON Panel Automation

Automated data extraction and monitoring for the SON (System Obsługi Najmu) rental management panel.

## What is SON?

SON (System Obsługi Najmu) is a commercial SaaS property management platform by System Obsługi Najmu sp. z o.o. (Kraków, Poland). This project automates data extraction from a ed SON instance used by the property management company to manage rental properties.

## Scripts

### `fetch_latest_invoice.py` — Quick check (LATEST mode)
Fetches the latest invoice from 3 sources (tenant operations, owner finances, estate cost documents). Reports 3 entries (Cost, Income, Payout) and downloads PDF for each that has a link.

```powershell
python fetch_latest_invoice.py
```

**Output:**
```
=== LATEST ===
Cost: 1/FV/01/10/2026/0001 (01/10/2026, -275.0)
Income: 123456 (02/10/2026, 1234,56)
Payout: payout_01-09-2026 (01/09/2026, 2475.0)

Downloading: 1/FV/01/10/2026/0001
   Saved: ./invoices\81_01_10_2026.pdf
```

Second run: "Already have" — no duplicate downloads.

### `fetch_all_data.py` — Full report (ALL mode)
Fetches everything: tenants, operations, liabilities, insurances, finances, cost documents. Saves CSV files and downloads all PDFs. Generates alerts and amount totals.

```powershell
python fetch_all_data.py
```

## Setup

1. Install dependencies:
   ```
   pip install requests beautifulsoup4 python-dotenv
   ```

2. Create `.env` file (do NOT commit):
   ```
   SON_LOGIN=your@email.com
   SON_PASSWORD=your_password
   SON_PANEL_URL=https://your-panel.example.com
   SON_OUT_DIR=./invoices
   ```

3. Run:
   ```
   python fetch_latest_invoice.py
   ```

## Output files

| File | Content |
|------|---------|
| `invoices/operations.csv` | Tenant operations (payments, invoices) |
| `invoices/liabilities.csv` | Recurring charges (rent, utilities, parking) |
| `invoices/insurances.csv` | Insurance policies |
| `invoices/finances.csv` | Owner finances (cost invoices, payouts) |
| `invoices/cost_documents.csv` | Cost documents (costs + payouts) |
| `invoices/*.pdf` | Downloaded invoice PDFs |
| `invoices/known_invoices.json` | State file (tracks downloaded invoices) |

## Structure

```
your-project/
├── fetch_all_data.py          # Full data fetch (ALL mode)
├── fetch_latest_invoice.py    # Quick check (LATEST mode)
├── .env                       # Credentials (never commit, never read by LLM)
├── .gitignore
├── AGENTS.md                  # Agent rules
├── lib/
│   ├── __init__.py
│   └── son_client.py          # Shared library (endpoints + parsers)
└── docs/
    ├── system_analysis_and_automation_plan.md
    ├── automation_flow.md
    ├── son_integration_models.md
    └── complete_endpoint_documentation.md
```

## Security

- `.env` is in `.gitignore` — never committed
- Agent (LLM) is permanently blocked from reading/editing/copying `.env`
- Credentials stored only in `.env` or environment variables
- No placeholders in code — all configuration via `.env`

## Documentation

See `docs/` for detailed documentation:
- `complete_endpoint_documentation.md` — all 52 panel endpoints
- `son_integration_models.md` — data models (Python + TypeScript)
- `automation_flow.md` — flow diagrams (Mermaid, validated)
- `system_analysis_and_automation_plan.md` — system analysis + automation plan