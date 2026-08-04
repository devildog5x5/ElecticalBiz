"""Report query builders for PowerFlow."""

from database import db, rows_to_list


def _date_clause(column, date_from, date_to):
    clauses = []
    params = []
    if date_from:
        clauses.append(f"{column} >= ?")
        params.append(date_from)
    if date_to:
        clauses.append(f"{column} <= ?")
        params.append(date_to)
    where = f" AND {' AND '.join(clauses)}" if clauses else ""
    return where, params


def build_full_report(date_from=None, date_to=None):
    inv_where, inv_params = _date_clause("inv.invoice_date", date_from, date_to)
    po_where, po_params = _date_clause("po.order_date", date_from, date_to)
    so_where, so_params = _date_clause("so.order_date", date_from, date_to)
    qt_where, qt_params = _date_clause("q.quote_date", date_from, date_to)

    with db() as conn:
        # --- Financial KPIs ---
        revenue = conn.execute(
            f"""
            SELECT COALESCE(SUM(total), 0) AS total,
                   COALESCE(SUM(amount_paid), 0) AS collected,
                   COALESCE(SUM(total - amount_paid), 0) AS outstanding,
                   COUNT(*) AS invoice_count
            FROM invoices inv
            WHERE inv.status NOT IN ('void', 'draft') {inv_where}
            """,
            inv_params,
        ).fetchone()

        cogs = conn.execute(
            f"""
            SELECT COALESCE(SUM(pol.line_total), 0) AS total
            FROM purchase_order_lines pol
            JOIN purchase_orders po ON po.id = pol.purchase_order_id
            WHERE po.status IN ('received', 'partial') {po_where}
            """,
            po_params,
        ).fetchone()

        inventory_cost = conn.execute(
            """
            SELECT COALESCE(SUM(i.quantity_on_hand * p.cost), 0) AS total,
                   COALESCE(SUM(i.quantity_on_hand * p.price), 0) AS retail
            FROM inventory i JOIN products p ON p.id = i.product_id
            """
        ).fetchone()

        gross_profit = revenue["total"] - cogs["total"]
        gross_margin = round(gross_profit / revenue["total"] * 100, 1) if revenue["total"] else 0

        # --- AR Aging ---
        ar_aging = conn.execute(
            """
            SELECT
                CASE
                    WHEN julianday('now') - julianday(due_date) <= 0 THEN 'current'
                    WHEN julianday('now') - julianday(due_date) <= 30 THEN '1-30'
                    WHEN julianday('now') - julianday(due_date) <= 60 THEN '31-60'
                    WHEN julianday('now') - julianday(due_date) <= 90 THEN '61-90'
                    ELSE '90+'
                END AS bucket,
                COUNT(*) AS invoice_count,
                COALESCE(SUM(total - amount_paid), 0) AS balance
            FROM invoices
            WHERE status IN ('sent', 'partial', 'overdue')
              AND (total - amount_paid) > 0
            GROUP BY bucket
            ORDER BY CASE bucket
                WHEN 'current' THEN 1 WHEN '1-30' THEN 2 WHEN '31-60' THEN 3
                WHEN '61-90' THEN 4 ELSE 5 END
            """
        ).fetchall()

        ar_detail = conn.execute(
            """
            SELECT invoice_number, c.name AS customer_name, invoice_date, due_date,
                   total, amount_paid, (total - amount_paid) AS balance, status,
                   CAST(julianday('now') - julianday(due_date) AS INTEGER) AS days_overdue
            FROM invoices inv
            JOIN customers c ON c.id = inv.customer_id
            WHERE inv.status IN ('sent', 'partial', 'overdue')
              AND (inv.total - inv.amount_paid) > 0
            ORDER BY due_date ASC
            """
        ).fetchall()

        # --- AP / Outstanding POs ---
        ap_summary = conn.execute(
            """
            SELECT s.name AS supplier_name, s.type,
                   COUNT(po.id) AS open_pos,
                   COALESCE(SUM(po.total), 0) AS open_value
            FROM purchase_orders po
            JOIN suppliers s ON s.id = po.supplier_id
            WHERE po.status IN ('sent', 'partial')
            GROUP BY s.id ORDER BY open_value DESC
            """
        ).fetchall()

        # --- Monthly revenue trend ---
        monthly_revenue = conn.execute(
            f"""
            SELECT strftime('%Y-%m', invoice_date) AS month,
                   COUNT(*) AS invoices,
                   COALESCE(SUM(total), 0) AS revenue,
                   COALESCE(SUM(amount_paid), 0) AS collected
            FROM invoices
            WHERE status NOT IN ('void', 'draft') {inv_where.replace('inv.', '')}
            GROUP BY month ORDER BY month DESC LIMIT 12
            """,
            inv_params,
        ).fetchall()

        # --- Sales by customer ---
        sales_by_customer = conn.execute(
            f"""
            SELECT c.name, c.type,
                   COUNT(inv.id) AS invoice_count,
                   COALESCE(SUM(inv.total), 0) AS total_sales,
                   COALESCE(SUM(inv.amount_paid), 0) AS collected,
                   COALESCE(SUM(inv.total - inv.amount_paid), 0) AS outstanding
            FROM customers c
            LEFT JOIN invoices inv ON inv.customer_id = c.id
                AND inv.status NOT IN ('void', 'draft') {inv_where}
            GROUP BY c.id ORDER BY total_sales DESC
            """,
            inv_params,
        ).fetchall()

        # --- Sales by category ---
        sales_by_category = conn.execute(
            f"""
            SELECT COALESCE(p.category, 'Other') AS category,
                   COALESCE(SUM(il.line_total), 0) AS revenue,
                   COALESCE(SUM(il.quantity), 0) AS units_sold
            FROM invoice_lines il
            JOIN invoices inv ON inv.id = il.invoice_id
            LEFT JOIN products p ON p.id = il.product_id
            WHERE inv.status NOT IN ('void', 'draft') {inv_where}
            GROUP BY category ORDER BY revenue DESC
            """,
            inv_params,
        ).fetchall()

        # --- Top products ---
        top_products = conn.execute(
            f"""
            SELECT COALESCE(p.sku, '—') AS sku,
                   il.description AS name,
                   COALESCE(p.category, 'Other') AS category,
                   COALESCE(SUM(il.quantity), 0) AS qty_sold,
                   COALESCE(SUM(il.line_total), 0) AS revenue
            FROM invoice_lines il
            JOIN invoices inv ON inv.id = il.invoice_id
            LEFT JOIN products p ON p.id = il.product_id
            WHERE inv.status NOT IN ('void', 'draft') {inv_where}
            GROUP BY il.product_id, il.description
            ORDER BY revenue DESC LIMIT 15
            """,
            inv_params,
        ).fetchall()

        # --- Quote pipeline ---
        quote_pipeline = conn.execute(
            f"""
            SELECT status, COUNT(*) AS count, COALESCE(SUM(total), 0) AS value
            FROM quotes q WHERE 1=1 {qt_where.replace('q.', '')}
            GROUP BY status
            """,
            qt_params,
        ).fetchall()

        quote_conversion = conn.execute(
            f"""
            SELECT
                (SELECT COUNT(*) FROM quotes WHERE status = 'accepted' {qt_where.replace('q.', '')}) AS accepted,
                (SELECT COUNT(*) FROM quotes WHERE status IN ('sent','accepted','declined') {qt_where.replace('q.', '')}) AS decided,
                (SELECT COUNT(*) FROM quotes WHERE 1=1 {qt_where.replace('q.', '')}) AS total
            """,
            qt_params * 3,
        ).fetchone()

        # --- Sales by job ---
        sales_by_job = conn.execute(
            f"""
            SELECT j.job_number, j.name AS job_name, c.name AS customer_name, j.status,
                   j.estimated_value,
                   COALESCE(SUM(inv.total), 0) AS invoiced,
                   COALESCE(SUM(inv.amount_paid), 0) AS collected
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            LEFT JOIN invoices inv ON inv.job_id = j.id
                AND inv.status NOT IN ('void', 'draft') {inv_where}
            GROUP BY j.id ORDER BY invoiced DESC
            """,
            inv_params,
        ).fetchall()

        # --- Purchases by supplier ---
        purchases_by_supplier = conn.execute(
            f"""
            SELECT s.name, s.type,
                   COUNT(po.id) AS po_count,
                   COALESCE(SUM(po.total), 0) AS total_purchases
            FROM suppliers s
            LEFT JOIN purchase_orders po ON po.supplier_id = s.id
                AND po.status != 'cancelled' {po_where}
            GROUP BY s.id ORDER BY total_purchases DESC
            """,
            po_params,
        ).fetchall()

        # --- PO status ---
        po_status = conn.execute(
            f"""
            SELECT status, COUNT(*) AS count, COALESCE(SUM(total), 0) AS value
            FROM purchase_orders po WHERE 1=1 {po_where.replace('po.', '')}
            GROUP BY status
            """,
            po_params,
        ).fetchall()

        # --- Purchases by category ---
        purchases_by_category = conn.execute(
            f"""
            SELECT p.category,
                   COALESCE(SUM(pol.quantity_ordered), 0) AS units,
                   COALESCE(SUM(pol.line_total), 0) AS spend
            FROM purchase_order_lines pol
            JOIN purchase_orders po ON po.id = pol.purchase_order_id
            JOIN products p ON p.id = pol.product_id
            WHERE po.status != 'cancelled' {po_where}
            GROUP BY p.category ORDER BY spend DESC
            """,
            po_params,
        ).fetchall()

        # --- Inventory ---
        category_inventory = conn.execute(
            """
            SELECT p.category, COUNT(*) AS product_count,
                   SUM(i.quantity_on_hand) AS total_units,
                   SUM(i.quantity_on_hand * p.cost) AS cost_value,
                   SUM(i.quantity_on_hand * p.price) AS retail_value
            FROM products p JOIN inventory i ON i.product_id = p.id
            GROUP BY p.category ORDER BY cost_value DESC
            """
        ).fetchall()

        low_stock = conn.execute(
            """
            SELECT p.sku, p.name, p.category, i.quantity_on_hand, p.reorder_level,
                   s.name AS supplier_name, p.cost,
                   (p.reorder_level - i.quantity_on_hand) AS qty_needed
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            WHERE i.quantity_on_hand <= p.reorder_level
            ORDER BY qty_needed DESC
            """
        ).fetchall()

        margin = conn.execute(
            """
            SELECT p.sku, p.name, p.category, p.cost, p.price,
                   (p.price - p.cost) AS unit_margin,
                   ROUND((p.price - p.cost) / NULLIF(p.price, 0) * 100, 1) AS margin_pct,
                   i.quantity_on_hand,
                   ROUND(i.quantity_on_hand * (p.price - p.cost), 2) AS potential_profit
            FROM products p
            JOIN inventory i ON i.product_id = p.id
            ORDER BY margin_pct DESC
            """
        ).fetchall()

        # --- Order fulfillment ---
        fulfillment = conn.execute(
            f"""
            SELECT so.order_number, c.name AS customer_name, so.status,
                   so.order_date, so.required_date, so.total,
                   COALESCE(SUM(sol.quantity_ordered), 0) AS qty_ordered,
                   COALESCE(SUM(sol.quantity_shipped), 0) AS qty_shipped
            FROM sales_orders so
            JOIN customers c ON c.id = so.customer_id
            LEFT JOIN sales_order_lines sol ON sol.sales_order_id = so.id
            WHERE so.status NOT IN ('delivered', 'cancelled') {so_where}
            GROUP BY so.id ORDER BY so.required_date ASC
            """,
            so_params,
        ).fetchall()

        # --- Job summary ---
        job_summary = conn.execute(
            """
            SELECT status, COUNT(*) AS count,
                   COALESCE(SUM(estimated_value), 0) AS pipeline_value
            FROM jobs GROUP BY status
            """
        ).fetchall()

    conv_rate = 0
    if quote_conversion["decided"]:
        conv_rate = round(quote_conversion["accepted"] / quote_conversion["decided"] * 100, 1)

    return {
        "filters": {"date_from": date_from, "date_to": date_to},
        "financial": {
            "revenue": revenue["total"],
            "collected": revenue["collected"],
            "outstanding_ar": revenue["outstanding"],
            "invoice_count": revenue["invoice_count"],
            "cogs": cogs["total"],
            "gross_profit": gross_profit,
            "gross_margin_pct": gross_margin,
            "inventory_cost": inventory_cost["total"],
            "inventory_retail": inventory_cost["retail"],
            "open_ap": sum(r["open_value"] for r in ap_summary),
            "ar_aging": rows_to_list(ar_aging),
            "ar_detail": rows_to_list(ar_detail),
            "ap_summary": rows_to_list(ap_summary),
            "monthly_revenue": rows_to_list(monthly_revenue),
        },
        "sales": {
            "by_customer": rows_to_list(sales_by_customer),
            "by_category": rows_to_list(sales_by_category),
            "top_products": rows_to_list(top_products),
            "by_job": rows_to_list(sales_by_job),
            "quote_pipeline": rows_to_list(quote_pipeline),
            "quote_conversion_rate": conv_rate,
            "quote_total": quote_conversion["total"],
        },
        "purchasing": {
            "by_supplier": rows_to_list(purchases_by_supplier),
            "po_status": rows_to_list(po_status),
            "by_category": rows_to_list(purchases_by_category),
        },
        "inventory": {
            "by_category": rows_to_list(category_inventory),
            "low_stock": rows_to_list(low_stock),
            "margins": rows_to_list(margin),
        },
        "operations": {
            "fulfillment": rows_to_list(fulfillment),
            "job_summary": rows_to_list(job_summary),
        },
    }
