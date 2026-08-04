import csv
import io
from datetime import datetime

from flask import Response, jsonify, request

from reports import build_full_report


def _csv_response(rows, filename, columns=None):
    if not rows:
        rows = []
    output = io.StringIO()
    if columns:
        fieldnames = [c[0] for c in columns]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(src, "") for k, src in columns})
    else:
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def register_report_routes(app):
    @app.route("/api/reports/summary")
    def reports_summary():
        report = build_full_report()
        return jsonify({
            "sales_by_customer": report["sales"]["by_customer"],
            "purchases_by_supplier": report["purchasing"]["by_supplier"],
            "category_inventory": [
                {**c, "total_value": c["cost_value"]} for c in report["inventory"]["by_category"]
            ],
            "margin": report["inventory"]["margins"],
        })

    @app.route("/api/reports/full")
    def reports_full():
        date_from = request.args.get("from")
        date_to = request.args.get("to")
        return jsonify(build_full_report(date_from, date_to))

    @app.route("/api/reports/export")
    def reports_export():
        report_type = request.args.get("type", "financial")
        date_from = request.args.get("from")
        date_to = request.args.get("to")
        report = build_full_report(date_from, date_to)
        stamp = datetime.now().strftime("%Y%m%d")
        suffix = f"_{date_from}_{date_to}" if date_from or date_to else ""

        exports = {
            "ar_aging": (
                report["financial"]["ar_detail"],
                f"ar_aging{suffix}_{stamp}.csv",
                [
                    ("Invoice", "invoice_number"), ("Customer", "customer_name"),
                    ("Invoice Date", "invoice_date"), ("Due Date", "due_date"),
                    ("Total", "total"), ("Paid", "amount_paid"), ("Balance", "balance"),
                    ("Days Overdue", "days_overdue"), ("Status", "status"),
                ],
            ),
            "sales_by_customer": (
                report["sales"]["by_customer"],
                f"sales_by_customer{suffix}_{stamp}.csv",
                [
                    ("Customer", "name"), ("Type", "type"), ("Invoices", "invoice_count"),
                    ("Total Sales", "total_sales"), ("Collected", "collected"),
                    ("Outstanding", "outstanding"),
                ],
            ),
            "sales_by_category": (
                report["sales"]["by_category"],
                f"sales_by_category{suffix}_{stamp}.csv",
                [("Category", "category"), ("Units Sold", "units_sold"), ("Revenue", "revenue")],
            ),
            "top_products": (
                report["sales"]["top_products"],
                f"top_products{suffix}_{stamp}.csv",
                [
                    ("SKU", "sku"), ("Product", "name"), ("Category", "category"),
                    ("Qty Sold", "qty_sold"), ("Revenue", "revenue"),
                ],
            ),
            "sales_by_job": (
                report["sales"]["by_job"],
                f"sales_by_job{suffix}_{stamp}.csv",
                [
                    ("Job #", "job_number"), ("Job Name", "job_name"), ("Customer", "customer_name"),
                    ("Status", "status"), ("Estimated", "estimated_value"),
                    ("Invoiced", "invoiced"), ("Collected", "collected"),
                ],
            ),
            "purchases_by_supplier": (
                report["purchasing"]["by_supplier"],
                f"purchases_by_supplier{suffix}_{stamp}.csv",
                [
                    ("Supplier", "name"), ("Type", "type"), ("PO Count", "po_count"),
                    ("Total Purchases", "total_purchases"),
                ],
            ),
            "purchases_by_category": (
                report["purchasing"]["by_category"],
                f"purchases_by_category{suffix}_{stamp}.csv",
                [("Category", "category"), ("Units", "units"), ("Spend", "spend")],
            ),
            "inventory_valuation": (
                report["inventory"]["by_category"],
                f"inventory_valuation_{stamp}.csv",
                [
                    ("Category", "category"), ("Products", "product_count"),
                    ("Units", "total_units"), ("Cost Value", "cost_value"),
                    ("Retail Value", "retail_value"),
                ],
            ),
            "low_stock": (
                report["inventory"]["low_stock"],
                f"low_stock_{stamp}.csv",
                [
                    ("SKU", "sku"), ("Product", "name"), ("Category", "category"),
                    ("On Hand", "quantity_on_hand"), ("Reorder Level", "reorder_level"),
                    ("Qty Needed", "qty_needed"), ("Supplier", "supplier_name"), ("Unit Cost", "cost"),
                ],
            ),
            "product_margins": (
                report["inventory"]["margins"],
                f"product_margins_{stamp}.csv",
                [
                    ("SKU", "sku"), ("Product", "name"), ("Category", "category"),
                    ("Cost", "cost"), ("Price", "price"), ("Unit Margin", "unit_margin"),
                    ("Margin %", "margin_pct"), ("On Hand", "quantity_on_hand"),
                    ("Potential Profit", "potential_profit"),
                ],
            ),
            "order_fulfillment": (
                report["operations"]["fulfillment"],
                f"order_fulfillment{suffix}_{stamp}.csv",
                [
                    ("Order #", "order_number"), ("Customer", "customer_name"), ("Status", "status"),
                    ("Order Date", "order_date"), ("Required", "required_date"),
                    ("Total", "total"), ("Qty Ordered", "qty_ordered"), ("Qty Shipped", "qty_shipped"),
                ],
            ),
            "monthly_revenue": (
                report["financial"]["monthly_revenue"],
                f"monthly_revenue{suffix}_{stamp}.csv",
                [
                    ("Month", "month"), ("Invoices", "invoices"),
                    ("Revenue", "revenue"), ("Collected", "collected"),
                ],
            ),
            "ap_summary": (
                report["financial"]["ap_summary"],
                f"ap_summary_{stamp}.csv",
                [
                    ("Supplier", "supplier_name"), ("Type", "type"),
                    ("Open POs", "open_pos"), ("Open Value", "open_value"),
                ],
            ),
        }

        if report_type not in exports:
            return jsonify({"error": f"Unknown report type: {report_type}"}), 400

        rows, filename, columns = exports[report_type]
        return _csv_response(rows, filename, columns)
