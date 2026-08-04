"""OpenAPI 3.0 specification for the PowerFlow REST API."""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "PowerFlow Electrical Business Manager API",
        "description": (
            "REST API for end-to-end electrical supply chain management: "
            "purchasing, inventory, sales, invoicing, and reporting."
        ),
        "version": "1.0.0",
        "contact": {"name": "Robert Foster"},
    },
    "servers": [{"url": "http://127.0.0.1:5000", "description": "Local development"}],
    "tags": [
        {"name": "System", "description": "Health and API metadata"},
        {"name": "Dashboard", "description": "Business KPIs and activity"},
        {"name": "Suppliers", "description": "Wholesalers and manufacturers"},
        {"name": "Products", "description": "Product catalog"},
        {"name": "Inventory", "description": "Stock levels"},
        {"name": "Purchase Orders", "description": "Procurement workflow"},
        {"name": "Customers", "description": "Contractors and builders"},
        {"name": "Jobs", "description": "Project tracking"},
        {"name": "Quotes", "description": "Estimates and proposals"},
        {"name": "Sales Orders", "description": "Customer orders and fulfillment"},
        {"name": "Invoices", "description": "Billing and payments"},
        {"name": "Reports", "description": "Analytics and CSV export"},
    ],
    "paths": {
        "/api": {
            "get": {
                "tags": ["System"],
                "summary": "API index",
                "description": "Returns API name, version, and links to documentation.",
                "responses": {"200": {"description": "API metadata"}},
            }
        },
        "/api/health": {
            "get": {
                "tags": ["System"],
                "summary": "Health check",
                "responses": {"200": {"description": "Service is healthy"}},
            }
        },
        "/api/dashboard": {
            "get": {
                "tags": ["Dashboard"],
                "summary": "Dashboard KPIs",
                "description": "Revenue, inventory value, open orders, low stock, and recent activity.",
                "responses": {"200": {"description": "Dashboard metrics"}},
            }
        },
        "/api/activity": {
            "get": {
                "tags": ["Dashboard"],
                "summary": "Activity log",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                    {"name": "entity_type", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "Activity entries"}},
            }
        },
        "/api/suppliers": {
            "get": {"tags": ["Suppliers"], "summary": "List suppliers", "responses": {"200": {"description": "Supplier list"}}},
            "post": {
                "tags": ["Suppliers"],
                "summary": "Create supplier",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SupplierInput"}}}},
                "responses": {"201": {"description": "Supplier created"}},
            },
        },
        "/api/suppliers/{id}": {
            "get": {"tags": ["Suppliers"], "summary": "Get supplier", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Supplier"}, "404": {"description": "Not found"}}},
            "put": {"tags": ["Suppliers"], "summary": "Update supplier", "parameters": [{"$ref": "#/components/parameters/Id"}], "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SupplierInput"}}}}, "responses": {"200": {"description": "Updated"}}},
            "delete": {"tags": ["Suppliers"], "summary": "Delete supplier", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"204": {"description": "Deleted"}}},
        },
        "/api/products": {
            "get": {"tags": ["Products"], "summary": "List products with inventory", "responses": {"200": {"description": "Product list"}}},
            "post": {
                "tags": ["Products"],
                "summary": "Create product",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProductInput"}}}},
                "responses": {"201": {"description": "Product created"}},
            },
        },
        "/api/products/{id}": {
            "get": {"tags": ["Products"], "summary": "Get product", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Product"}, "404": {"description": "Not found"}}},
            "put": {"tags": ["Products"], "summary": "Update product", "parameters": [{"$ref": "#/components/parameters/Id"}], "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProductInput"}}}}, "responses": {"200": {"description": "Updated"}}},
            "delete": {"tags": ["Products"], "summary": "Delete product", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"204": {"description": "Deleted"}}},
        },
        "/api/inventory": {
            "get": {"tags": ["Inventory"], "summary": "Inventory snapshot with valuation", "responses": {"200": {"description": "Inventory rows"}}},
        },
        "/api/purchase-orders": {
            "get": {"tags": ["Purchase Orders"], "summary": "List purchase orders with line items", "responses": {"200": {"description": "PO list"}}},
            "post": {
                "tags": ["Purchase Orders"],
                "summary": "Create purchase order",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PurchaseOrderInput"}}}},
                "responses": {"201": {"description": "PO created"}},
            },
        },
        "/api/purchase-orders/{id}": {
            "get": {"tags": ["Purchase Orders"], "summary": "Get purchase order", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "PO with lines"}, "404": {"description": "Not found"}}},
        },
        "/api/purchase-orders/{id}/status": {
            "patch": {
                "tags": ["Purchase Orders"],
                "summary": "Update PO status",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string", "enum": ["draft", "sent", "partial", "received", "cancelled"]}}, "required": ["status"]}}}},
                "responses": {"200": {"description": "Status updated"}},
            },
        },
        "/api/purchase-orders/{id}/receive": {
            "post": {
                "tags": ["Purchase Orders"],
                "summary": "Receive PO line items into inventory",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "object", "properties": {"line_id": {"type": "integer"}, "quantity": {"type": "integer"}}, "required": ["line_id", "quantity"]}}}, "required": ["lines"]}}}},
                "responses": {"200": {"description": "Inventory updated"}},
            },
        },
        "/api/customers": {
            "get": {"tags": ["Customers"], "summary": "List customers", "responses": {"200": {"description": "Customer list"}}},
            "post": {
                "tags": ["Customers"],
                "summary": "Create customer",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CustomerInput"}}}},
                "responses": {"201": {"description": "Customer created"}},
            },
        },
        "/api/customers/{id}": {
            "get": {"tags": ["Customers"], "summary": "Get customer", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Customer"}, "404": {"description": "Not found"}}},
            "put": {"tags": ["Customers"], "summary": "Update customer", "parameters": [{"$ref": "#/components/parameters/Id"}], "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CustomerInput"}}}}, "responses": {"200": {"description": "Updated"}}},
            "delete": {"tags": ["Customers"], "summary": "Delete customer", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"204": {"description": "Deleted"}}},
        },
        "/api/jobs": {
            "get": {"tags": ["Jobs"], "summary": "List jobs", "responses": {"200": {"description": "Job list"}}},
            "post": {
                "tags": ["Jobs"],
                "summary": "Create job",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/JobInput"}}}},
                "responses": {"201": {"description": "Job created"}},
            },
        },
        "/api/jobs/{id}": {
            "get": {"tags": ["Jobs"], "summary": "Get job", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Job"}, "404": {"description": "Not found"}}},
            "put": {"tags": ["Jobs"], "summary": "Update job", "parameters": [{"$ref": "#/components/parameters/Id"}], "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/JobInput"}}}}, "responses": {"200": {"description": "Updated"}}},
        },
        "/api/quotes": {
            "get": {"tags": ["Quotes"], "summary": "List quotes with line items", "responses": {"200": {"description": "Quote list"}}},
            "post": {
                "tags": ["Quotes"],
                "summary": "Create quote",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/QuoteInput"}}}},
                "responses": {"201": {"description": "Quote created"}},
            },
        },
        "/api/quotes/{id}": {
            "get": {"tags": ["Quotes"], "summary": "Get quote", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Quote with lines"}, "404": {"description": "Not found"}}},
        },
        "/api/quotes/{id}/status": {
            "patch": {
                "tags": ["Quotes"],
                "summary": "Update quote status",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string", "enum": ["draft", "sent", "accepted", "declined", "expired"]}}, "required": ["status"]}}}},
                "responses": {"200": {"description": "Status updated"}},
            },
        },
        "/api/sales-orders": {
            "get": {"tags": ["Sales Orders"], "summary": "List sales orders with line items", "responses": {"200": {"description": "Order list"}}},
            "post": {
                "tags": ["Sales Orders"],
                "summary": "Create sales order",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SalesOrderInput"}}}},
                "responses": {"201": {"description": "Order created"}},
            },
        },
        "/api/sales-orders/{id}": {
            "get": {"tags": ["Sales Orders"], "summary": "Get sales order", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Order with lines"}, "404": {"description": "Not found"}}},
        },
        "/api/sales-orders/{id}/ship": {
            "post": {
                "tags": ["Sales Orders"],
                "summary": "Ship order lines (deducts inventory)",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "object", "properties": {"line_id": {"type": "integer"}, "quantity": {"type": "integer"}}, "required": ["line_id", "quantity"]}}}, "required": ["lines"]}}}},
                "responses": {"200": {"description": "Shipment processed"}, "400": {"description": "Insufficient stock"}},
            },
        },
        "/api/sales-orders/{id}/status": {
            "patch": {
                "tags": ["Sales Orders"],
                "summary": "Update sales order status",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}}}},
                "responses": {"200": {"description": "Status updated"}},
            },
        },
        "/api/invoices": {
            "get": {"tags": ["Invoices"], "summary": "List invoices with line items", "responses": {"200": {"description": "Invoice list"}}},
            "post": {
                "tags": ["Invoices"],
                "summary": "Create invoice",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/InvoiceInput"}}}},
                "responses": {"201": {"description": "Invoice created"}},
            },
        },
        "/api/invoices/{id}": {
            "get": {"tags": ["Invoices"], "summary": "Get invoice", "parameters": [{"$ref": "#/components/parameters/Id"}], "responses": {"200": {"description": "Invoice with lines"}, "404": {"description": "Not found"}}},
        },
        "/api/invoices/{id}/payment": {
            "post": {
                "tags": ["Invoices"],
                "summary": "Record payment",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"amount": {"type": "number"}}, "required": ["amount"]}}}},
                "responses": {"200": {"description": "Payment recorded"}},
            },
        },
        "/api/invoices/{id}/status": {
            "patch": {
                "tags": ["Invoices"],
                "summary": "Update invoice status",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string", "enum": ["draft", "sent", "partial", "paid", "overdue", "void"]}}, "required": ["status"]}}}},
                "responses": {"200": {"description": "Status updated"}},
            },
        },
        "/api/invoices/from-order/{id}": {
            "post": {
                "tags": ["Invoices"],
                "summary": "Generate invoice from sales order",
                "parameters": [{"$ref": "#/components/parameters/Id"}],
                "responses": {"201": {"description": "Invoice created from order"}},
            },
        },
        "/api/reports/summary": {
            "get": {"tags": ["Reports"], "summary": "Legacy summary report", "responses": {"200": {"description": "Summary metrics"}}},
        },
        "/api/reports/full": {
            "get": {
                "tags": ["Reports"],
                "summary": "Full reporting package",
                "parameters": [
                    {"name": "from", "in": "query", "schema": {"type": "string", "format": "date"}, "description": "Start date (YYYY-MM-DD)"},
                    {"name": "to", "in": "query", "schema": {"type": "string", "format": "date"}, "description": "End date (YYYY-MM-DD)"},
                ],
                "responses": {"200": {"description": "Financial, sales, purchasing, inventory, and operations reports"}},
            },
        },
        "/api/reports/export": {
            "get": {
                "tags": ["Reports"],
                "summary": "Export report as CSV",
                "parameters": [
                    {"name": "type", "in": "query", "required": True, "schema": {"type": "string", "enum": [
                        "ar_aging", "sales_by_customer", "sales_by_category", "top_products", "sales_by_job",
                        "purchases_by_supplier", "purchases_by_category", "inventory_valuation", "low_stock",
                        "product_margins", "order_fulfillment", "monthly_revenue", "ap_summary",
                    ]}},
                    {"name": "from", "in": "query", "schema": {"type": "string", "format": "date"}},
                    {"name": "to", "in": "query", "schema": {"type": "string", "format": "date"}},
                ],
                "responses": {"200": {"description": "CSV file", "content": {"text/csv": {}}}, "400": {"description": "Unknown report type"}},
            },
        },
    },
    "components": {
        "parameters": {
            "Id": {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
        },
        "schemas": {
            "Error": {"type": "object", "properties": {"error": {"type": "string"}}},
            "SupplierInput": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name": {"type": "string"}, "type": {"type": "string", "enum": ["wholesaler", "manufacturer"]},
                    "contact_name": {"type": "string"}, "email": {"type": "string"}, "phone": {"type": "string"},
                    "address": {"type": "string"}, "account_number": {"type": "string"},
                    "payment_terms": {"type": "string", "default": "Net 30"}, "notes": {"type": "string"},
                },
            },
            "ProductInput": {
                "type": "object",
                "required": ["sku", "name", "category"],
                "properties": {
                    "sku": {"type": "string"}, "name": {"type": "string"}, "category": {"type": "string"},
                    "description": {"type": "string"}, "unit": {"type": "string", "default": "each"},
                    "cost": {"type": "number"}, "price": {"type": "number"}, "reorder_level": {"type": "integer"},
                    "supplier_id": {"type": "integer", "nullable": True}, "manufacturer_part": {"type": "string"},
                    "quantity_on_hand": {"type": "integer"},
                },
            },
            "PurchaseOrderInput": {
                "type": "object",
                "required": ["supplier_id", "lines"],
                "properties": {
                    "supplier_id": {"type": "integer"}, "status": {"type": "string"},
                    "order_date": {"type": "string", "format": "date"}, "expected_date": {"type": "string", "format": "date"},
                    "notes": {"type": "string"},
                    "lines": {"type": "array", "items": {"$ref": "#/components/schemas/POLineInput"}},
                },
            },
            "POLineInput": {
                "type": "object",
                "required": ["product_id", "quantity_ordered", "unit_cost"],
                "properties": {"product_id": {"type": "integer"}, "quantity_ordered": {"type": "integer"}, "unit_cost": {"type": "number"}},
            },
            "CustomerInput": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name": {"type": "string"}, "type": {"type": "string", "enum": ["contractor", "builder", "commercial", "residential"]},
                    "contact_name": {"type": "string"}, "email": {"type": "string"}, "phone": {"type": "string"},
                    "address": {"type": "string"}, "tax_exempt": {"type": "boolean"}, "credit_limit": {"type": "number"},
                    "payment_terms": {"type": "string"}, "notes": {"type": "string"},
                },
            },
            "JobInput": {
                "type": "object",
                "required": ["customer_id", "name"],
                "properties": {
                    "customer_id": {"type": "integer"}, "name": {"type": "string"}, "site_address": {"type": "string"},
                    "status": {"type": "string"}, "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}, "estimated_value": {"type": "number"}, "notes": {"type": "string"},
                },
            },
            "QuoteInput": {
                "type": "object",
                "required": ["customer_id", "lines"],
                "properties": {
                    "customer_id": {"type": "integer"}, "job_id": {"type": "integer", "nullable": True},
                    "status": {"type": "string"}, "quote_date": {"type": "string", "format": "date"}, "notes": {"type": "string"},
                    "lines": {"type": "array", "items": {"$ref": "#/components/schemas/DocumentLineInput"}},
                },
            },
            "SalesOrderInput": {
                "type": "object",
                "required": ["customer_id", "lines"],
                "properties": {
                    "customer_id": {"type": "integer"}, "job_id": {"type": "integer", "nullable": True},
                    "quote_id": {"type": "integer", "nullable": True}, "status": {"type": "string"},
                    "order_date": {"type": "string", "format": "date"}, "required_date": {"type": "string", "format": "date"},
                    "notes": {"type": "string"},
                    "lines": {"type": "array", "items": {"$ref": "#/components/schemas/SOLineInput"}},
                },
            },
            "SOLineInput": {
                "type": "object",
                "required": ["product_id", "quantity_ordered", "unit_price"],
                "properties": {"product_id": {"type": "integer"}, "quantity_ordered": {"type": "integer"}, "unit_price": {"type": "number"}},
            },
            "InvoiceInput": {
                "type": "object",
                "required": ["customer_id", "lines"],
                "properties": {
                    "customer_id": {"type": "integer"}, "sales_order_id": {"type": "integer", "nullable": True},
                    "job_id": {"type": "integer", "nullable": True}, "status": {"type": "string"},
                    "invoice_date": {"type": "string", "format": "date"}, "notes": {"type": "string"},
                    "lines": {"type": "array", "items": {"$ref": "#/components/schemas/DocumentLineInput"}},
                },
            },
            "DocumentLineInput": {
                "type": "object",
                "required": ["description", "quantity", "unit_price"],
                "properties": {
                    "product_id": {"type": "integer", "nullable": True}, "description": {"type": "string"},
                    "quantity": {"type": "number"}, "unit_price": {"type": "number"},
                },
            },
        },
    },
}

API_INDEX = {
    "name": "PowerFlow Electrical Business Manager API",
    "version": "1.0.0",
    "documentation": {
        "html": "/api/docs",
        "openapi": "/api/openapi.json",
        "markdown": "/api/docs/markdown",
    },
    "endpoints": {
        "system": ["/api", "/api/health"],
        "dashboard": ["/api/dashboard", "/api/activity"],
        "suppliers": ["/api/suppliers", "/api/suppliers/{id}"],
        "products": ["/api/products", "/api/products/{id}"],
        "inventory": ["/api/inventory"],
        "purchase_orders": ["/api/purchase-orders", "/api/purchase-orders/{id}", "/api/purchase-orders/{id}/status", "/api/purchase-orders/{id}/receive"],
        "customers": ["/api/customers", "/api/customers/{id}"],
        "jobs": ["/api/jobs", "/api/jobs/{id}"],
        "quotes": ["/api/quotes", "/api/quotes/{id}", "/api/quotes/{id}/status"],
        "sales_orders": ["/api/sales-orders", "/api/sales-orders/{id}", "/api/sales-orders/{id}/ship", "/api/sales-orders/{id}/status"],
        "invoices": ["/api/invoices", "/api/invoices/{id}", "/api/invoices/{id}/payment", "/api/invoices/{id}/status", "/api/invoices/from-order/{id}"],
        "reports": ["/api/reports/summary", "/api/reports/full", "/api/reports/export"],
    },
}
