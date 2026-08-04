# PowerFlow — Electrical Business Manager

End-to-end business management for electrical supply companies: purchasing from wholesalers and manufacturers through sales to contractors and builders.

## Features

### Purchasing
- **Suppliers** — Manage wholesalers and manufacturers with contact info, account numbers, and payment terms
- **Products** — Full electrical product catalog (wire, breakers, panels, conduit, devices, lighting)
- **Purchase Orders** — Create POs, send to suppliers, receive inventory
- **Inventory** — Real-time stock levels, low-stock alerts, warehouse tracking

### Sales
- **Customers** — Contractors, builders, commercial, and residential accounts
- **Jobs** — Project tracking with site addresses and estimated values
- **Quotes** — Create estimates and track acceptance
- **Sales Orders** — Process orders, ship from inventory, generate invoices
- **Invoices** — Billing, payment tracking, accounts receivable

### Reports
- **Financial** — P&L summary, gross margin, A/R aging, A/P summary, monthly revenue trend
- **Sales** — By customer, category, job, top products, quote pipeline & conversion rate
- **Purchasing** — By supplier & category, PO status breakdown
- **Inventory** — Valuation, low stock/reorder, margin analysis
- **Operations** — Job summary, open order fulfillment

All reports support date-range filtering, CSV export, and print.

### Email Reminders
- **Automated tasks** — reorder alerts, sales calls, local/cloud backups, A/R, quotes, PO follow-up
- **SMTP configuration** — Gmail, Office 365, or any SMTP server
- **Scheduling** — daily, weekly, or monthly with background checker
- **Manual reminders** — custom tasks with your own message
- **Send log** — history of all notification attempts

Configure under the **Reminders** tab → **Email Settings**.

## Quick Start

```powershell
cd C:\Users\rober\Documents\GitHub\ElecticalBiz
pip install -r requirements.txt
```

### Standalone desktop app (default)

Double-click **`PowerFlow.bat`**, or run:

```powershell
python main.py
```

Opens PowerFlow in its own window — no browser tab needed. Uses Edge WebView2 on Windows.

### Web application

Double-click **`PowerFlow-Web.bat`**, or run:

```powershell
python main.py --web --browser
```

Then open **http://127.0.0.1:5000** (browser opens automatically with `--browser`).

For development with Flask debug mode:

```powershell
python app.py
```

| Mode | Command | Use case |
|------|---------|----------|
| Standalone | `python main.py` | Desktop app for daily use |
| Web server | `python main.py --web` | LAN access, multiple users, API clients |
| Dev | `python app.py` | Local development with auto-reload |

**API documentation:** [http://127.0.0.1:5000/api/docs](http://127.0.0.1:5000/api/docs)
The app ships with sample data so you can explore the full workflow immediately.

## API

REST JSON API at `/api/*`. Key entry points:

| URL | Description |
|-----|-------------|
| `/api` | API index and endpoint map |
| `/api/docs` | Interactive HTML documentation |
| `/api/openapi.json` | OpenAPI 3.0 specification |
| `/api/health` | Health check |
| `/api/docs/markdown` | Markdown reference (`docs/API.md`) |

See [docs/API.md](docs/API.md) for the complete endpoint reference.

## Workflow Example

1. **Purchase** — Create a PO to Graybar for wire and conduit → Send → Receive into inventory
2. **Quote** — Build a quote for Summit Electric Contractors on the Riverside job
3. **Sell** — Convert to a sales order → Ship products (deducts inventory) → Generate invoice
4. **Collect** — Record payment against the invoice

## Tech Stack

- Python 3 + Flask
- SQLite database
- Single-page frontend (vanilla JS, no build step required)
- **Standalone:** pywebview (native desktop window)
- **Web:** any modern browser or REST API client