# PowerFlow REST API Reference

**Version:** 1.0.0  
**Base URL:** `http://127.0.0.1:5000`  
**Format:** JSON (`Content-Type: application/json` for POST/PUT/PATCH)

Interactive docs: [http://127.0.0.1:5000/api/docs](http://127.0.0.1:5000/api/docs)  
OpenAPI spec: [http://127.0.0.1:5000/api/openapi.json](http://127.0.0.1:5000/api/openapi.json)

---

## System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api` | API index with endpoint groups and doc links |
| GET | `/api/health` | Health check (database connectivity) |
| GET | `/api/docs` | HTML API documentation |
| GET | `/api/openapi.json` | OpenAPI 3.0 specification |
| GET | `/api/docs/markdown` | This reference as Markdown |

---

## Dashboard

### GET `/api/dashboard`

Returns business KPIs: revenue MTD, outstanding A/R, inventory value, open POs/orders, active jobs, low stock alerts, recent activity.

### GET `/api/activity`

Activity log entries.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `limit` | integer | Max rows (default 50, max 200) |
| `entity_type` | string | Filter by entity: `supplier`, `product`, `purchase_order`, `customer`, `job`, `quote`, `sales_order`, `invoice` |

---

## Suppliers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/suppliers` | List all suppliers |
| POST | `/api/suppliers` | Create supplier |
| GET | `/api/suppliers/{id}` | Get supplier by ID |
| PUT | `/api/suppliers/{id}` | Update supplier |
| DELETE | `/api/suppliers/{id}` | Delete supplier |

**POST/PUT body:**

```json
{
  "name": "Graybar Electric",
  "type": "wholesaler",
  "contact_name": "Mike Stevens",
  "email": "mike@graybar.com",
  "phone": "555-0101",
  "address": "1200 Industrial Blvd",
  "account_number": "GRY-88421",
  "payment_terms": "Net 30",
  "notes": ""
}
```

`type` must be `wholesaler` or `manufacturer`.

---

## Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | List products with inventory and supplier |
| POST | `/api/products` | Create product (initializes inventory) |
| GET | `/api/products/{id}` | Get product by ID |
| PUT | `/api/products/{id}` | Update product and optional stock level |
| DELETE | `/api/products/{id}` | Delete product and inventory row |

**POST/PUT body:**

```json
{
  "sku": "WIRE-12-2-RMW",
  "name": "12/2 Romex Wire 250ft",
  "category": "Wire & Cable",
  "description": "12 AWG NM-B copper wire",
  "unit": "roll",
  "cost": 89.50,
  "price": 124.99,
  "reorder_level": 20,
  "supplier_id": 1,
  "manufacturer_part": "28827426",
  "quantity_on_hand": 45
}
```

---

## Inventory

### GET `/api/inventory`

Full inventory snapshot with cost value, reorder levels, and low-stock flag.

---

## Purchase Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/purchase-orders` | List POs with line items |
| POST | `/api/purchase-orders` | Create PO |
| GET | `/api/purchase-orders/{id}` | Get PO with lines |
| PATCH | `/api/purchase-orders/{id}/status` | Update status |
| POST | `/api/purchase-orders/{id}/receive` | Receive goods into inventory |

**POST body:**

```json
{
  "supplier_id": 1,
  "expected_date": "2026-08-15",
  "notes": "Wire restock",
  "lines": [
    { "product_id": 1, "quantity_ordered": 30, "unit_cost": 89.50 }
  ]
}
```

**PATCH status body:** `{ "status": "sent" }`  
Statuses: `draft`, `sent`, `partial`, `received`, `cancelled`

**POST receive body:**

```json
{
  "lines": [
    { "line_id": 1, "quantity": 30 }
  ]
}
```

---

## Customers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/customers` | List customers |
| POST | `/api/customers` | Create customer |
| GET | `/api/customers/{id}` | Get customer |
| PUT | `/api/customers/{id}` | Update customer |
| DELETE | `/api/customers/{id}` | Delete customer |

**POST/PUT body:**

```json
{
  "name": "Summit Electric Contractors",
  "type": "contractor",
  "contact_name": "Dave Morrison",
  "email": "dave@summit.com",
  "phone": "555-1001",
  "address": "2200 Builder Lane",
  "tax_exempt": false,
  "credit_limit": 50000,
  "payment_terms": "Net 30",
  "notes": ""
}
```

`type`: `contractor`, `builder`, `commercial`, `residential`

---

## Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List jobs with customer name |
| POST | `/api/jobs` | Create job |
| GET | `/api/jobs/{id}` | Get job |
| PUT | `/api/jobs/{id}` | Update job |

**POST/PUT body:**

```json
{
  "customer_id": 1,
  "name": "Riverside Office Park Phase 2",
  "site_address": "1200 Riverside Dr",
  "status": "active",
  "start_date": "2026-01-15",
  "end_date": "2026-06-30",
  "estimated_value": 125000,
  "notes": ""
}
```

---

## Quotes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/quotes` | List quotes with lines |
| POST | `/api/quotes` | Create quote |
| GET | `/api/quotes/{id}` | Get quote |
| PATCH | `/api/quotes/{id}/status` | Update status |

**POST body:**

```json
{
  "customer_id": 1,
  "job_id": 1,
  "lines": [
    { "product_id": 1, "description": "12/2 Romex Wire", "quantity": 40, "unit_price": 124.99 }
  ]
}
```

**PATCH status:** `{ "status": "accepted" }`  
Statuses: `draft`, `sent`, `accepted`, `declined`, `expired`

---

## Sales Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sales-orders` | List orders with lines |
| POST | `/api/sales-orders` | Create order |
| GET | `/api/sales-orders/{id}` | Get order |
| POST | `/api/sales-orders/{id}/ship` | Ship lines (deducts inventory) |
| PATCH | `/api/sales-orders/{id}/status` | Update status |

**POST body:**

```json
{
  "customer_id": 1,
  "job_id": 1,
  "quote_id": 1,
  "required_date": "2026-02-01",
  "status": "confirmed",
  "lines": [
    { "product_id": 1, "quantity_ordered": 40, "unit_price": 124.99 }
  ]
}
```

**POST ship body:** `{ "lines": [{ "line_id": 1, "quantity": 40 }] }`

Returns `400` if insufficient stock.

---

## Invoices

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/invoices` | List invoices with lines |
| POST | `/api/invoices` | Create invoice |
| GET | `/api/invoices/{id}` | Get invoice |
| POST | `/api/invoices/{id}/payment` | Record payment |
| PATCH | `/api/invoices/{id}/status` | Update status |
| POST | `/api/invoices/from-order/{id}` | Generate invoice from sales order |

**POST body:**

```json
{
  "customer_id": 1,
  "job_id": 1,
  "lines": [
    { "product_id": 1, "description": "12/2 Romex Wire", "quantity": 40, "unit_price": 124.99 }
  ]
}
```

**POST payment body:** `{ "amount": 5000.00 }`

**PATCH status:** `{ "status": "sent" }`  
Statuses: `draft`, `sent`, `partial`, `paid`, `overdue`, `void`

---

## Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/summary` | Legacy summary (4 tables) |
| GET | `/api/reports/full` | Full reporting package |
| GET | `/api/reports/export` | CSV export |

### GET `/api/reports/full`

**Query parameters:** `from`, `to` (YYYY-MM-DD, optional)

Returns sections: `financial`, `sales`, `purchasing`, `inventory`, `operations`.

### GET `/api/reports/export`

**Query parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `type` | yes | Report type (see below) |
| `from` | no | Start date |
| `to` | no | End date |

**Export types:** `ar_aging`, `sales_by_customer`, `sales_by_category`, `top_products`, `sales_by_job`, `purchases_by_supplier`, `purchases_by_category`, `inventory_valuation`, `low_stock`, `product_margins`, `order_fulfillment`, `monthly_revenue`, `ap_summary`

---

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation error, insufficient stock) |
| 404 | Resource not found |
| 204 | Success with no body (DELETE) |

Error body format:

```json
{ "error": "Description of the problem" }
```

---

## Tax Calculation

Sales tax is applied at **8%** unless the customer is marked `tax_exempt`. Tax is calculated automatically on quotes, sales orders, and invoices.

---

## Number Formats

Auto-generated document numbers follow the pattern `{PREFIX}-{YEAR}-{SEQUENCE}`:

| Entity | Prefix | Example |
|--------|--------|---------|
| Purchase Order | PO | PO-2026-0001 |
| Job | JOB | JOB-2026-0001 |
| Quote | QT | QT-2026-0001 |
| Sales Order | SO | SO-2026-0001 |
| Invoice | INV | INV-2026-0001 |
