from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request

from database import db, generate_number, init_db, log_activity, row_to_dict, rows_to_list
from api_docs import register_api_docs
from reminder_routes import register_reminder_routes
from report_routes import register_report_routes
from seed import seed_if_empty

app = Flask(__name__)
register_report_routes(app)
register_api_docs(app)
register_reminder_routes(app)


@app.before_request
def _init_once():
    if not app.config.get("_INIT_DONE"):
        init_db()
        seed_if_empty()
        from reminders_service import seed_default_reminders
        from reminder_scheduler import start_reminder_scheduler

        seed_default_reminders()
        start_reminder_scheduler(app)
        app.config["_INIT_DONE"] = True


def not_found(entity, id_):
    return jsonify({"error": f"{entity} {id_} not found"}), 404


def calc_tax(subtotal, exempt=False):
    return 0 if exempt else round(subtotal * 0.08, 2)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    with db() as conn:
        inventory_value = conn.execute(
            """
            SELECT COALESCE(SUM(i.quantity_on_hand * p.cost), 0)
            FROM inventory i JOIN products p ON p.id = i.product_id
            """
        ).fetchone()[0]

        low_stock = conn.execute(
            """
            SELECT p.sku, p.name, i.quantity_on_hand, p.reorder_level
            FROM inventory i JOIN products p ON p.id = i.product_id
            WHERE i.quantity_on_hand <= p.reorder_level
            ORDER BY i.quantity_on_hand ASC LIMIT 8
            """
        ).fetchall()

        open_pos = conn.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE status IN ('sent', 'partial')"
        ).fetchone()[0]

        open_orders = conn.execute(
            "SELECT COUNT(*) FROM sales_orders WHERE status IN ('pending', 'confirmed', 'partial')"
        ).fetchone()[0]

        outstanding = conn.execute(
            """
            SELECT COALESCE(SUM(total - amount_paid), 0)
            FROM invoices WHERE status IN ('sent', 'partial', 'overdue')
            """
        ).fetchone()[0]

        revenue_mtd = conn.execute(
            """
            SELECT COALESCE(SUM(total), 0) FROM invoices
            WHERE invoice_date >= date('now', 'start of month')
            AND status != 'void'
            """
        ).fetchone()[0]

        active_jobs = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'active'"
        ).fetchone()[0]

        recent_activity = conn.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

        pending_quotes = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE status IN ('draft', 'sent')"
        ).fetchone()[0]

    return jsonify({
        "inventory_value": inventory_value,
        "low_stock": rows_to_list(low_stock),
        "open_pos": open_pos,
        "open_orders": open_orders,
        "outstanding_ar": outstanding,
        "revenue_mtd": revenue_mtd,
        "active_jobs": active_jobs,
        "pending_quotes": pending_quotes,
        "recent_activity": rows_to_list(recent_activity),
    })


# --- Suppliers ---

@app.route("/api/suppliers", methods=["GET", "POST"])
def suppliers():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
        return jsonify(rows_to_list(rows))

    data = request.json
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO suppliers (name, type, contact_name, email, phone, address, account_number, payment_terms, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["name"], data["type"], data.get("contact_name"), data.get("email"),
             data.get("phone"), data.get("address"), data.get("account_number"),
             data.get("payment_terms", "Net 30"), data.get("notes")),
        )
        sid = cur.lastrowid
        log_activity(conn, "supplier", sid, "created", f"Supplier {data['name']} added")
        row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/suppliers/<int:sid>", methods=["GET", "PUT", "DELETE"])
def supplier_detail(sid):
    if request.method == "GET":
        with db() as conn:
            row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
        return jsonify(row_to_dict(row)) if row else not_found("Supplier", sid)

    if request.method == "DELETE":
        with db() as conn:
            conn.execute("DELETE FROM suppliers WHERE id = ?", (sid,))
        return "", 204

    data = request.json
    with db() as conn:
        conn.execute(
            """UPDATE suppliers SET name=?, type=?, contact_name=?, email=?, phone=?,
               address=?, account_number=?, payment_terms=?, notes=? WHERE id=?""",
            (data["name"], data["type"], data.get("contact_name"), data.get("email"),
             data.get("phone"), data.get("address"), data.get("account_number"),
             data.get("payment_terms"), data.get("notes"), sid),
        )
        row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
    return jsonify(row_to_dict(row))


# --- Products & Inventory ---

@app.route("/api/products", methods=["GET", "POST"])
def products():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute(
                """
                SELECT p.*, s.name AS supplier_name,
                       COALESCE(i.quantity_on_hand, 0) AS quantity_on_hand,
                       COALESCE(i.quantity_reserved, 0) AS quantity_reserved,
                       i.location
                FROM products p
                LEFT JOIN suppliers s ON s.id = p.supplier_id
                LEFT JOIN inventory i ON i.product_id = p.id
                ORDER BY p.category, p.name
                """
            ).fetchall()
        return jsonify(rows_to_list(rows))

    data = request.json
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO products (sku, name, category, description, unit, cost, price, reorder_level, supplier_id, manufacturer_part)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["sku"], data["name"], data["category"], data.get("description"),
             data.get("unit", "each"), data.get("cost", 0), data.get("price", 0),
             data.get("reorder_level", 10), data.get("supplier_id"), data.get("manufacturer_part")),
        )
        pid = cur.lastrowid
        conn.execute(
            "INSERT INTO inventory (product_id, quantity_on_hand) VALUES (?, ?)",
            (pid, data.get("quantity_on_hand", 0)),
        )
        log_activity(conn, "product", pid, "created", f"Product {data['sku']} added")
        row = conn.execute(
            """SELECT p.*, s.name AS supplier_name,
                      COALESCE(i.quantity_on_hand, 0) AS quantity_on_hand
               FROM products p LEFT JOIN suppliers s ON s.id = p.supplier_id
               LEFT JOIN inventory i ON i.product_id = p.id WHERE p.id = ?""",
            (pid,),
        ).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/products/<int:pid>", methods=["GET", "PUT", "DELETE"])
def product_detail(pid):
    if request.method == "GET":
        with db() as conn:
            row = conn.execute(
                """SELECT p.*, s.name AS supplier_name,
                          COALESCE(i.quantity_on_hand, 0) AS quantity_on_hand,
                          COALESCE(i.quantity_reserved, 0) AS quantity_reserved, i.location
                   FROM products p LEFT JOIN suppliers s ON s.id = p.supplier_id
                   LEFT JOIN inventory i ON i.product_id = p.id WHERE p.id = ?""",
                (pid,),
            ).fetchone()
        return jsonify(row_to_dict(row)) if row else not_found("Product", pid)

    if request.method == "DELETE":
        with db() as conn:
            conn.execute("DELETE FROM inventory WHERE product_id = ?", (pid,))
            conn.execute("DELETE FROM products WHERE id = ?", (pid,))
        return "", 204

    data = request.json
    with db() as conn:
        conn.execute(
            """UPDATE products SET sku=?, name=?, category=?, description=?, unit=?,
               cost=?, price=?, reorder_level=?, supplier_id=?, manufacturer_part=? WHERE id=?""",
            (data["sku"], data["name"], data["category"], data.get("description"),
             data.get("unit"), data.get("cost"), data.get("price"),
             data.get("reorder_level"), data.get("supplier_id"), data.get("manufacturer_part"), pid),
        )
        if "quantity_on_hand" in data:
            conn.execute(
                "UPDATE inventory SET quantity_on_hand = ? WHERE product_id = ?",
                (data["quantity_on_hand"], pid),
            )
        row = conn.execute(
            """SELECT p.*, s.name AS supplier_name,
                      COALESCE(i.quantity_on_hand, 0) AS quantity_on_hand
               FROM products p LEFT JOIN suppliers s ON s.id = p.supplier_id
               LEFT JOIN inventory i ON i.product_id = p.id WHERE p.id = ?""",
            (pid,),
        ).fetchone()
    return jsonify(row_to_dict(row))


@app.route("/api/inventory")
def inventory_list():
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.sku, p.name, p.category, p.unit, p.cost, p.price, p.reorder_level,
                   i.quantity_on_hand, i.quantity_reserved, i.location,
                   s.name AS supplier_name,
                   (i.quantity_on_hand * p.cost) AS stock_value,
                   CASE WHEN i.quantity_on_hand <= p.reorder_level THEN 1 ELSE 0 END AS low_stock
            FROM products p
            JOIN inventory i ON i.product_id = p.id
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            ORDER BY low_stock DESC, p.name
            """
        ).fetchall()
    return jsonify(rows_to_list(rows))


# --- Purchase Orders ---

@app.route("/api/purchase-orders", methods=["GET", "POST"])
def purchase_orders():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute(
                """
                SELECT po.*, s.name AS supplier_name
                FROM purchase_orders po
                JOIN suppliers s ON s.id = po.supplier_id
                ORDER BY po.order_date DESC
                """
            ).fetchall()
            result = rows_to_list(rows)
            for po in result:
                lines = conn.execute(
                    """
                    SELECT pol.*, p.sku, p.name AS product_name
                    FROM purchase_order_lines pol
                    JOIN products p ON p.id = pol.product_id
                    WHERE pol.purchase_order_id = ?
                    """,
                    (po["id"],),
                ).fetchall()
                po["lines"] = rows_to_list(lines)
        return jsonify(result)

    data = request.json
    with db() as conn:
        po_number = generate_number("PO", conn, "purchase_orders", "po_number")
        subtotal = sum(l["quantity_ordered"] * l["unit_cost"] for l in data["lines"])
        tax = calc_tax(subtotal)
        total = subtotal + tax
        cur = conn.execute(
            """INSERT INTO purchase_orders (po_number, supplier_id, status, order_date, expected_date, subtotal, tax, total, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (po_number, data["supplier_id"], data.get("status", "draft"),
             data.get("order_date", datetime.now().strftime("%Y-%m-%d")),
             data.get("expected_date"), subtotal, tax, total, data.get("notes")),
        )
        po_id = cur.lastrowid
        for line in data["lines"]:
            lt = line["quantity_ordered"] * line["unit_cost"]
            conn.execute(
                """INSERT INTO purchase_order_lines (purchase_order_id, product_id, quantity_ordered, unit_cost, line_total)
                   VALUES (?, ?, ?, ?, ?)""",
                (po_id, line["product_id"], line["quantity_ordered"], line["unit_cost"], lt),
            )
        log_activity(conn, "purchase_order", po_id, "created", f"{po_number} created")
        row = conn.execute(
            "SELECT po.*, s.name AS supplier_name FROM purchase_orders po JOIN suppliers s ON s.id = po.supplier_id WHERE po.id = ?",
            (po_id,),
        ).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/purchase-orders/<int:po_id>", methods=["GET"])
def purchase_order_detail(po_id):
    with db() as conn:
        row = conn.execute(
            "SELECT po.*, s.name AS supplier_name FROM purchase_orders po JOIN suppliers s ON s.id = po.supplier_id WHERE po.id = ?",
            (po_id,),
        ).fetchone()
        if not row:
            return not_found("Purchase order", po_id)
        po = row_to_dict(row)
        lines = conn.execute(
            """
            SELECT pol.*, p.sku, p.name AS product_name
            FROM purchase_order_lines pol JOIN products p ON p.id = pol.product_id
            WHERE pol.purchase_order_id = ?
            """,
            (po_id,),
        ).fetchall()
        po["lines"] = rows_to_list(lines)
    return jsonify(po)


@app.route("/api/purchase-orders/<int:po_id>/status", methods=["PATCH"])
def po_status(po_id):
    data = request.json
    with db() as conn:
        conn.execute("UPDATE purchase_orders SET status = ? WHERE id = ?", (data["status"], po_id))
        po = conn.execute("SELECT po_number FROM purchase_orders WHERE id = ?", (po_id,)).fetchone()
        log_activity(conn, "purchase_order", po_id, data["status"], f"{po['po_number']} marked {data['status']}")
    return jsonify({"ok": True})


@app.route("/api/purchase-orders/<int:po_id>/receive", methods=["POST"])
def receive_po(po_id):
    data = request.json
    with db() as conn:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (po_id,)).fetchone()
        for receipt in data["lines"]:
            line = conn.execute(
                "SELECT * FROM purchase_order_lines WHERE id = ? AND purchase_order_id = ?",
                (receipt["line_id"], po_id),
            ).fetchone()
            qty = receipt["quantity"]
            new_received = line["quantity_received"] + qty
            conn.execute(
                "UPDATE purchase_order_lines SET quantity_received = ? WHERE id = ?",
                (new_received, receipt["line_id"]),
            )
            conn.execute(
                """UPDATE inventory SET quantity_on_hand = quantity_on_hand + ?,
                   last_received = date('now') WHERE product_id = ?""",
                (qty, line["product_id"]),
            )

        lines = conn.execute(
            "SELECT quantity_ordered, quantity_received FROM purchase_order_lines WHERE purchase_order_id = ?",
            (po_id,),
        ).fetchall()
        all_received = all(l["quantity_received"] >= l["quantity_ordered"] for l in lines)
        any_received = any(l["quantity_received"] > 0 for l in lines)
        status = "received" if all_received else ("partial" if any_received else po["status"])
        conn.execute("UPDATE purchase_orders SET status = ? WHERE id = ?", (status, po_id))
        log_activity(conn, "purchase_order", po_id, "received", f"{po['po_number']} inventory received")
    return jsonify({"ok": True, "status": status})


# --- Customers ---

@app.route("/api/customers", methods=["GET", "POST"])
def customers():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
        return jsonify(rows_to_list(rows))

    data = request.json
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO customers (name, type, contact_name, email, phone, address, tax_exempt, credit_limit, payment_terms, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["name"], data["type"], data.get("contact_name"), data.get("email"),
             data.get("phone"), data.get("address"), 1 if data.get("tax_exempt") else 0,
             data.get("credit_limit", 10000), data.get("payment_terms", "Net 30"), data.get("notes")),
        )
        cid = cur.lastrowid
        log_activity(conn, "customer", cid, "created", f"Customer {data['name']} added")
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/customers/<int:cid>", methods=["GET", "PUT", "DELETE"])
def customer_detail(cid):
    if request.method == "GET":
        with db() as conn:
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
        return jsonify(row_to_dict(row)) if row else not_found("Customer", cid)

    if request.method == "DELETE":
        with db() as conn:
            conn.execute("DELETE FROM customers WHERE id = ?", (cid,))
        return "", 204

    data = request.json
    with db() as conn:
        conn.execute(
            """UPDATE customers SET name=?, type=?, contact_name=?, email=?, phone=?,
               address=?, tax_exempt=?, credit_limit=?, payment_terms=?, notes=? WHERE id=?""",
            (data["name"], data["type"], data.get("contact_name"), data.get("email"),
             data.get("phone"), data.get("address"), 1 if data.get("tax_exempt") else 0,
             data.get("credit_limit"), data.get("payment_terms"), data.get("notes"), cid),
        )
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    return jsonify(row_to_dict(row))


# --- Jobs ---

@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute(
                """
                SELECT j.*, c.name AS customer_name
                FROM jobs j JOIN customers c ON c.id = j.customer_id
                ORDER BY j.created_at DESC
                """
            ).fetchall()
        return jsonify(rows_to_list(rows))

    data = request.json
    with db() as conn:
        job_number = generate_number("JOB", conn, "jobs", "job_number")
        cur = conn.execute(
            """INSERT INTO jobs (job_number, customer_id, name, site_address, status, start_date, end_date, estimated_value, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_number, data["customer_id"], data["name"], data.get("site_address"),
             data.get("status", "active"), data.get("start_date"), data.get("end_date"),
             data.get("estimated_value", 0), data.get("notes")),
        )
        jid = cur.lastrowid
        log_activity(conn, "job", jid, "created", f"{job_number} - {data['name']}")
        row = conn.execute(
            "SELECT j.*, c.name AS customer_name FROM jobs j JOIN customers c ON c.id = j.customer_id WHERE j.id = ?",
            (jid,),
        ).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/jobs/<int:jid>", methods=["GET", "PUT"])
def job_detail(jid):
    if request.method == "GET":
        with db() as conn:
            row = conn.execute(
                "SELECT j.*, c.name AS customer_name FROM jobs j JOIN customers c ON c.id = j.customer_id WHERE j.id = ?",
                (jid,),
            ).fetchone()
        return jsonify(row_to_dict(row)) if row else not_found("Job", jid)

    data = request.json
    with db() as conn:
        conn.execute(
            """UPDATE jobs SET customer_id=?, name=?, site_address=?, status=?,
               start_date=?, end_date=?, estimated_value=?, notes=? WHERE id=?""",
            (data["customer_id"], data["name"], data.get("site_address"), data.get("status"),
             data.get("start_date"), data.get("end_date"), data.get("estimated_value"),
             data.get("notes"), jid),
        )
        row = conn.execute(
            "SELECT j.*, c.name AS customer_name FROM jobs j JOIN customers c ON c.id = j.customer_id WHERE j.id = ?",
            (jid,),
        ).fetchone()
    return jsonify(row_to_dict(row))


# --- Quotes ---

@app.route("/api/quotes", methods=["GET", "POST"])
def quotes():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute(
                """
                SELECT q.*, c.name AS customer_name, j.name AS job_name
                FROM quotes q
                JOIN customers c ON c.id = q.customer_id
                LEFT JOIN jobs j ON j.id = q.job_id
                ORDER BY q.quote_date DESC
                """
            ).fetchall()
            result = rows_to_list(rows)
            for q in result:
                lines = conn.execute("SELECT * FROM quote_lines WHERE quote_id = ?", (q["id"],)).fetchall()
                q["lines"] = rows_to_list(lines)
        return jsonify(result)

    data = request.json
    with db() as conn:
        quote_number = generate_number("QT", conn, "quotes", "quote_number")
        customer = conn.execute("SELECT tax_exempt FROM customers WHERE id = ?", (data["customer_id"],)).fetchone()
        subtotal = sum(l["quantity"] * l["unit_price"] for l in data["lines"])
        tax = calc_tax(subtotal, bool(customer["tax_exempt"]))
        total = subtotal + tax
        valid = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cur = conn.execute(
            """INSERT INTO quotes (quote_number, customer_id, job_id, status, quote_date, valid_until, subtotal, tax, total, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (quote_number, data["customer_id"], data.get("job_id"), data.get("status", "draft"),
             data.get("quote_date", datetime.now().strftime("%Y-%m-%d")), valid,
             subtotal, tax, total, data.get("notes")),
        )
        qid = cur.lastrowid
        for line in data["lines"]:
            lt = line["quantity"] * line["unit_price"]
            conn.execute(
                """INSERT INTO quote_lines (quote_id, product_id, description, quantity, unit_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (qid, line.get("product_id"), line["description"], line["quantity"], line["unit_price"], lt),
            )
        log_activity(conn, "quote", qid, "created", f"{quote_number} created")
        row = conn.execute("SELECT * FROM quotes WHERE id = ?", (qid,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/quotes/<int:qid>", methods=["GET"])
def quote_detail(qid):
    with db() as conn:
        row = conn.execute(
            """
            SELECT q.*, c.name AS customer_name, j.name AS job_name
            FROM quotes q JOIN customers c ON c.id = q.customer_id
            LEFT JOIN jobs j ON j.id = q.job_id WHERE q.id = ?
            """,
            (qid,),
        ).fetchone()
        if not row:
            return not_found("Quote", qid)
        quote = row_to_dict(row)
        lines = conn.execute("SELECT * FROM quote_lines WHERE quote_id = ?", (qid,)).fetchall()
        quote["lines"] = rows_to_list(lines)
    return jsonify(quote)


@app.route("/api/quotes/<int:qid>/status", methods=["PATCH"])
def quote_status(qid):
    data = request.json
    with db() as conn:
        conn.execute("UPDATE quotes SET status = ? WHERE id = ?", (data["status"], qid))
        q = conn.execute("SELECT quote_number FROM quotes WHERE id = ?", (qid,)).fetchone()
        log_activity(conn, "quote", qid, data["status"], f"{q['quote_number']} marked {data['status']}")
    return jsonify({"ok": True})


# --- Sales Orders ---

@app.route("/api/sales-orders", methods=["GET", "POST"])
def sales_orders():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute(
                """
                SELECT so.*, c.name AS customer_name, j.name AS job_name
                FROM sales_orders so
                JOIN customers c ON c.id = so.customer_id
                LEFT JOIN jobs j ON j.id = so.job_id
                ORDER BY so.order_date DESC
                """
            ).fetchall()
            result = rows_to_list(rows)
            for so in result:
                lines = conn.execute(
                    """
                    SELECT sol.*, p.sku, p.name AS product_name
                    FROM sales_order_lines sol
                    JOIN products p ON p.id = sol.product_id
                    WHERE sol.sales_order_id = ?
                    """,
                    (so["id"],),
                ).fetchall()
                so["lines"] = rows_to_list(lines)
        return jsonify(result)

    data = request.json
    with db() as conn:
        order_number = generate_number("SO", conn, "sales_orders", "order_number")
        customer = conn.execute("SELECT tax_exempt FROM customers WHERE id = ?", (data["customer_id"],)).fetchone()
        subtotal = sum(l["quantity_ordered"] * l["unit_price"] for l in data["lines"])
        tax = calc_tax(subtotal, bool(customer["tax_exempt"]))
        total = subtotal + tax
        cur = conn.execute(
            """INSERT INTO sales_orders (order_number, customer_id, job_id, quote_id, status, order_date, required_date, subtotal, tax, total, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_number, data["customer_id"], data.get("job_id"), data.get("quote_id"),
             data.get("status", "pending"),
             data.get("order_date", datetime.now().strftime("%Y-%m-%d")),
             data.get("required_date"), subtotal, tax, total, data.get("notes")),
        )
        so_id = cur.lastrowid
        for line in data["lines"]:
            lt = line["quantity_ordered"] * line["unit_price"]
            conn.execute(
                """INSERT INTO sales_order_lines (sales_order_id, product_id, quantity_ordered, unit_price, line_total)
                   VALUES (?, ?, ?, ?, ?)""",
                (so_id, line["product_id"], line["quantity_ordered"], line["unit_price"], lt),
            )
        log_activity(conn, "sales_order", so_id, "created", f"{order_number} created")
        row = conn.execute("SELECT * FROM sales_orders WHERE id = ?", (so_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/sales-orders/<int:so_id>", methods=["GET"])
def sales_order_detail(so_id):
    with db() as conn:
        row = conn.execute(
            """
            SELECT so.*, c.name AS customer_name, j.name AS job_name
            FROM sales_orders so JOIN customers c ON c.id = so.customer_id
            LEFT JOIN jobs j ON j.id = so.job_id WHERE so.id = ?
            """,
            (so_id,),
        ).fetchone()
        if not row:
            return not_found("Sales order", so_id)
        order = row_to_dict(row)
        lines = conn.execute(
            """
            SELECT sol.*, p.sku, p.name AS product_name
            FROM sales_order_lines sol JOIN products p ON p.id = sol.product_id
            WHERE sol.sales_order_id = ?
            """,
            (so_id,),
        ).fetchall()
        order["lines"] = rows_to_list(lines)
    return jsonify(order)


@app.route("/api/sales-orders/<int:so_id>/ship", methods=["POST"])
def ship_order(so_id):
    data = request.json
    with db() as conn:
        so = conn.execute("SELECT order_number FROM sales_orders WHERE id = ?", (so_id,)).fetchone()
        for shipment in data["lines"]:
            line = conn.execute(
                "SELECT * FROM sales_order_lines WHERE id = ? AND sales_order_id = ?",
                (shipment["line_id"], so_id),
            ).fetchone()
            qty = shipment["quantity"]
            inv = conn.execute(
                "SELECT quantity_on_hand FROM inventory WHERE product_id = ?", (line["product_id"],)
            ).fetchone()
            if inv["quantity_on_hand"] < qty:
                return jsonify({"error": f"Insufficient stock for product {line['product_id']}"}), 400
            conn.execute(
                "UPDATE sales_order_lines SET quantity_shipped = quantity_shipped + ? WHERE id = ?",
                (qty, shipment["line_id"]),
            )
            conn.execute(
                "UPDATE inventory SET quantity_on_hand = quantity_on_hand - ? WHERE product_id = ?",
                (qty, line["product_id"]),
            )

        lines = conn.execute(
            "SELECT quantity_ordered, quantity_shipped FROM sales_order_lines WHERE sales_order_id = ?",
            (so_id,),
        ).fetchall()
        all_shipped = all(l["quantity_shipped"] >= l["quantity_ordered"] for l in lines)
        any_shipped = any(l["quantity_shipped"] > 0 for l in lines)
        status = "delivered" if all_shipped else ("partial" if any_shipped else "confirmed")
        conn.execute("UPDATE sales_orders SET status = ? WHERE id = ?", (status, so_id))
        log_activity(conn, "sales_order", so_id, "shipped", f"{so['order_number']} shipment processed")
    return jsonify({"ok": True, "status": status})


@app.route("/api/sales-orders/<int:so_id>/status", methods=["PATCH"])
def so_status(so_id):
    data = request.json
    with db() as conn:
        conn.execute("UPDATE sales_orders SET status = ? WHERE id = ?", (data["status"], so_id))
    return jsonify({"ok": True})


# --- Invoices ---

@app.route("/api/invoices", methods=["GET", "POST"])
def invoices():
    if request.method == "GET":
        with db() as conn:
            rows = conn.execute(
                """
                SELECT inv.*, c.name AS customer_name, j.name AS job_name
                FROM invoices inv
                JOIN customers c ON c.id = inv.customer_id
                LEFT JOIN jobs j ON j.id = inv.job_id
                ORDER BY inv.invoice_date DESC
                """
            ).fetchall()
            result = rows_to_list(rows)
            for inv in result:
                lines = conn.execute("SELECT * FROM invoice_lines WHERE invoice_id = ?", (inv["id"],)).fetchall()
                inv["lines"] = rows_to_list(lines)
        return jsonify(result)

    data = request.json
    with db() as conn:
        invoice_number = generate_number("INV", conn, "invoices", "invoice_number")
        customer = conn.execute("SELECT tax_exempt FROM customers WHERE id = ?", (data["customer_id"],)).fetchone()
        subtotal = sum(l["quantity"] * l["unit_price"] for l in data["lines"])
        tax = calc_tax(subtotal, bool(customer["tax_exempt"]))
        total = subtotal + tax
        due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cur = conn.execute(
            """INSERT INTO invoices (invoice_number, customer_id, sales_order_id, job_id, status, invoice_date, due_date, subtotal, tax, total, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (invoice_number, data["customer_id"], data.get("sales_order_id"), data.get("job_id"),
             data.get("status", "draft"),
             data.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
             due, subtotal, tax, total, data.get("notes")),
        )
        inv_id = cur.lastrowid
        for line in data["lines"]:
            lt = line["quantity"] * line["unit_price"]
            conn.execute(
                """INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (inv_id, line.get("product_id"), line["description"], line["quantity"], line["unit_price"], lt),
            )
        log_activity(conn, "invoice", inv_id, "created", f"{invoice_number} created")
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/invoices/<int:inv_id>", methods=["GET"])
def invoice_detail(inv_id):
    with db() as conn:
        row = conn.execute(
            """
            SELECT inv.*, c.name AS customer_name, j.name AS job_name
            FROM invoices inv JOIN customers c ON c.id = inv.customer_id
            LEFT JOIN jobs j ON j.id = inv.job_id WHERE inv.id = ?
            """,
            (inv_id,),
        ).fetchone()
        if not row:
            return not_found("Invoice", inv_id)
        invoice = row_to_dict(row)
        lines = conn.execute("SELECT * FROM invoice_lines WHERE invoice_id = ?", (inv_id,)).fetchall()
        invoice["lines"] = rows_to_list(lines)
    return jsonify(invoice)


@app.route("/api/invoices/<int:inv_id>/payment", methods=["POST"])
def invoice_payment(inv_id):
    data = request.json
    with db() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,)).fetchone()
        new_paid = inv["amount_paid"] + data["amount"]
        status = "paid" if new_paid >= inv["total"] else ("partial" if new_paid > 0 else inv["status"])
        conn.execute(
            "UPDATE invoices SET amount_paid = ?, status = ? WHERE id = ?",
            (new_paid, status, inv_id),
        )
        log_activity(conn, "invoice", inv_id, "payment", f"${data['amount']:.2f} payment on {inv['invoice_number']}")
    return jsonify({"ok": True, "status": status})


@app.route("/api/invoices/<int:inv_id>/status", methods=["PATCH"])
def invoice_status(inv_id):
    data = request.json
    with db() as conn:
        conn.execute("UPDATE invoices SET status = ? WHERE id = ?", (data["status"], inv_id))
        inv = conn.execute("SELECT invoice_number FROM invoices WHERE id = ?", (inv_id,)).fetchone()
        log_activity(conn, "invoice", inv_id, data["status"], f"{inv['invoice_number']} marked {data['status']}")
    return jsonify({"ok": True})


@app.route("/api/invoices/from-order/<int:so_id>", methods=["POST"])
def invoice_from_order(so_id):
    with db() as conn:
        so = conn.execute("SELECT * FROM sales_orders WHERE id = ?", (so_id,)).fetchone()
        lines = conn.execute(
            """
            SELECT sol.*, p.sku, p.name AS product_name
            FROM sales_order_lines sol JOIN products p ON p.id = sol.product_id
            WHERE sol.sales_order_id = ?
            """,
            (so_id,),
        ).fetchall()
        invoice_number = generate_number("INV", conn, "invoices", "invoice_number")
        due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cur = conn.execute(
            """INSERT INTO invoices (invoice_number, customer_id, sales_order_id, job_id, status, invoice_date, due_date, subtotal, tax, total, notes)
               VALUES (?, ?, ?, ?, 'draft', date('now'), ?, ?, ?, ?, ?)""",
            (invoice_number, so["customer_id"], so_id, so["job_id"], due,
             so["subtotal"], so["tax"], so["total"], f"Generated from {so['order_number']}"),
        )
        inv_id = cur.lastrowid
        for line in lines:
            conn.execute(
                """INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (inv_id, line["product_id"], line["product_name"], line["quantity_ordered"],
                 line["unit_price"], line["line_total"]),
            )
        log_activity(conn, "invoice", inv_id, "created", f"{invoice_number} from {so['order_number']}")
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


if __name__ == "__main__":
    from main import run_web
    run_web(debug=True, open_browser=True)
