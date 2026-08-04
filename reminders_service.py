"""Email reminders and scheduled task notifications."""

import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import db, log_activity, row_to_dict, rows_to_list

CATEGORY_LABELS = {
    "reorder": "Inventory Reorder",
    "sales_call": "Sales Calls",
    "backup_local": "Local Backup",
    "backup_cloud": "Cloud Backup Verification",
    "accounts_receivable": "Accounts Receivable",
    "quote_followup": "Quote Follow-up",
    "po_followup": "Purchase Order Follow-up",
    "inventory": "Inventory Review",
    "general": "General Task",
}


def get_email_settings():
    with db() as conn:
        row = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()
    return row_to_dict(row)


def save_email_settings(data):
    with db() as conn:
        existing = conn.execute("SELECT smtp_password FROM email_settings WHERE id = 1").fetchone()
        password = data.get("smtp_password")
        if not password and existing:
            password = existing["smtp_password"]
        conn.execute(
            """UPDATE email_settings SET enabled=?, smtp_host=?, smtp_port=?, smtp_user=?,
               smtp_password=?, from_email=?, to_emails=?, use_tls=?, check_interval_minutes=?,
               updated_at=datetime('now') WHERE id=1""",
            (
                1 if data.get("enabled") else 0,
                data.get("smtp_host", ""),
                int(data.get("smtp_port", 587)),
                data.get("smtp_user", ""),
                password or "",
                data.get("from_email", ""),
                data.get("to_emails", ""),
                1 if data.get("use_tls", True) else 0,
                int(data.get("check_interval_minutes", 15)),
            ),
        )
        row = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()
    safe = row_to_dict(row)
    safe["smtp_password"] = "********" if safe.get("smtp_password") else ""
    return safe


def parse_recipients(settings, override=None):
    raw = override or settings.get("to_emails") or ""
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_email(subject, body_html, body_text, recipients, settings=None):
    settings = settings or get_email_settings()
    if not settings.get("enabled"):
        return {"ok": False, "error": "Email is not enabled. Configure SMTP in Reminders settings."}
    if not recipients:
        return {"ok": False, "error": "No recipients configured."}
    if not settings.get("smtp_host") or not settings.get("from_email"):
        return {"ok": False, "error": "SMTP host and from email are required."}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings["from_email"]
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        if settings.get("use_tls"):
            server = smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=30)
        if settings.get("smtp_user"):
            server.login(settings["smtp_user"], settings.get("smtp_password") or "")
        server.sendmail(settings["from_email"], recipients, msg.as_string())
        server.quit()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def log_reminder_send(reminder_id, subject, recipients, body_preview, status, error=None):
    with db() as conn:
        conn.execute(
            """INSERT INTO reminder_log (reminder_id, subject, recipients, body_preview, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (reminder_id, subject, ", ".join(recipients), body_preview[:500], status, error),
        )


def advance_due_date(current_date_str, recurrence):
    current = datetime.strptime(current_date_str, "%Y-%m-%d").date()
    if recurrence == "daily":
        return (current + timedelta(days=1)).isoformat()
    if recurrence == "weekly":
        return (current + timedelta(days=7)).isoformat()
    if recurrence == "monthly":
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        day = min(current.day, 28)
        return datetime(year, month, day).date().isoformat()
    return current_date_str


def build_auto_content(category):
    with db() as conn:
        if category == "reorder":
            rows = conn.execute(
                """
                SELECT p.sku, p.name, i.quantity_on_hand, p.reorder_level, s.name AS supplier_name
                FROM inventory i JOIN products p ON p.id = i.product_id
                LEFT JOIN suppliers s ON s.id = p.supplier_id
                WHERE i.quantity_on_hand <= p.reorder_level
                ORDER BY i.quantity_on_hand ASC
                """
            ).fetchall()
            if not rows:
                return None, "All inventory levels are above reorder points. No action needed."
            lines = ["SKU | Product | On Hand | Reorder | Supplier"]
            for r in rows:
                lines.append(f"{r['sku']} | {r['name']} | {r['quantity_on_hand']} | {r['reorder_level']} | {r['supplier_name'] or '—'}")
            body = "Low stock items requiring reorder:\n\n" + "\n".join(lines)
            body += "\n\nAction: Create purchase orders for items below reorder level."
            return f"PowerFlow: {len(rows)} items need reorder", body

        if category == "sales_call":
            rows = conn.execute(
                """
                SELECT c.name, c.contact_name, c.phone, c.type,
                       COALESCE(SUM(inv.total - inv.amount_paid), 0) AS outstanding
                FROM customers c
                LEFT JOIN invoices inv ON inv.customer_id = c.id
                    AND inv.status IN ('sent', 'partial', 'overdue')
                WHERE c.type IN ('contractor', 'builder')
                GROUP BY c.id ORDER BY outstanding DESC, c.name
                """
            ).fetchall()
            pending_quotes = conn.execute(
                "SELECT COUNT(*) FROM quotes WHERE status IN ('draft', 'sent')"
            ).fetchone()[0]
            lines = [f"{r['name']} ({r['type']}) — {r['contact_name'] or '—'} — {r['phone'] or '—'}" for r in rows]
            body = f"Sales call checklist — {len(rows)} contractor/builder accounts\n"
            body += f"Pending quotes to follow up: {pending_quotes}\n\n"
            body += "\n".join(lines) if lines else "No customers on file."
            body += "\n\nAction: Call top accounts, follow up on open quotes, and identify new job opportunities."
            return "PowerFlow: Weekly sales call reminders", body

        if category == "backup_local":
            body = (
                "Local database backup reminder\n\n"
                "Back up the PowerFlow SQLite database:\n"
                "  data/electrical.db\n\n"
                "Recommended steps:\n"
                "1. Close PowerFlow or ensure no writes in progress\n"
                "2. Copy data/electrical.db to your backup drive\n"
                "3. Optionally copy the entire data/ folder\n"
                "4. Verify the backup file opens and has a recent timestamp\n"
            )
            return "PowerFlow: Local backup reminder", body

        if category == "backup_cloud":
            body = (
                "Cloud backup verification reminder\n\n"
                "Verify your off-site / cloud backups:\n"
                "1. Confirm last sync completed successfully (OneDrive, Dropbox, etc.)\n"
                "2. Open the cloud portal and verify data/electrical.db is present\n"
                "3. Check file date matches today's local backup\n"
                "4. Test restore on a non-production copy if due for quarterly drill\n"
                "5. Document verification in your runbook\n"
            )
            return "PowerFlow: Cloud backup verification", body

        if category == "accounts_receivable":
            rows = conn.execute(
                """
                SELECT inv.invoice_number, c.name, inv.due_date,
                       inv.total, inv.amount_paid, (inv.total - inv.amount_paid) AS balance,
                       CAST(julianday('now') - julianday(inv.due_date) AS INTEGER) AS days_overdue
                FROM invoices inv JOIN customers c ON c.id = inv.customer_id
                WHERE inv.status IN ('sent', 'partial', 'overdue')
                  AND (inv.total - inv.amount_paid) > 0
                ORDER BY inv.due_date ASC
                """
            ).fetchall()
            if not rows:
                return None, "No outstanding invoices. A/R is clear."
            total = sum(r["balance"] for r in rows)
            lines = [f"{r['invoice_number']} | {r['name']} | Due {r['due_date']} | {r['balance']:.2f} | {r['days_overdue']}d overdue" for r in rows]
            body = f"Outstanding A/R: ${total:,.2f} across {len(rows)} invoice(s)\n\n" + "\n".join(lines)
            body += "\n\nAction: Contact customers with overdue balances and record payments in PowerFlow."
            return f"PowerFlow: A/R follow-up — ${total:,.2f} outstanding", body

        if category == "quote_followup":
            rows = conn.execute(
                """
                SELECT q.quote_number, c.name, q.quote_date, q.valid_until, q.total, q.status
                FROM quotes q JOIN customers c ON c.id = q.customer_id
                WHERE q.status IN ('draft', 'sent')
                ORDER BY q.valid_until ASC
                """
            ).fetchall()
            if not rows:
                return None, "No pending quotes requiring follow-up."
            lines = [f"{r['quote_number']} | {r['name']} | ${r['total']:,.2f} | Valid until {r['valid_until']} | {r['status']}" for r in rows]
            body = "Quotes needing follow-up:\n\n" + "\n".join(lines)
            body += "\n\nAction: Call customers on sent quotes before they expire."
            return f"PowerFlow: {len(rows)} quotes need follow-up", body

        if category == "po_followup":
            rows = conn.execute(
                """
                SELECT po.po_number, s.name, po.order_date, po.expected_date, po.status, po.total
                FROM purchase_orders po JOIN suppliers s ON s.id = po.supplier_id
                WHERE po.status IN ('sent', 'partial')
                ORDER BY po.expected_date ASC
                """
            ).fetchall()
            if not rows:
                return None, "No open purchase orders awaiting delivery."
            lines = [f"{r['po_number']} | {r['name']} | Expected {r['expected_date'] or '—'} | ${r['total']:,.2f} | {r['status']}" for r in rows]
            body = "Open purchase orders:\n\n" + "\n".join(lines)
            body += "\n\nAction: Confirm delivery dates with suppliers and receive inventory when shipments arrive."
            return f"PowerFlow: {len(rows)} POs awaiting delivery", body

        if category == "inventory":
            value = conn.execute(
                "SELECT COALESCE(SUM(i.quantity_on_hand * p.cost), 0) FROM inventory i JOIN products p ON p.id = i.product_id"
            ).fetchone()[0]
            low = conn.execute(
                "SELECT COUNT(*) FROM inventory i JOIN products p ON p.id = i.product_id WHERE i.quantity_on_hand <= p.reorder_level"
            ).fetchone()[0]
            body = f"Weekly inventory review\n\nInventory value at cost: ${value:,.2f}\nLow stock SKUs: {low}\n\nAction: Review counts, cycle-count high-value items, and adjust reorder levels."
            return "PowerFlow: Weekly inventory review", body

    return "PowerFlow reminder", "Task reminder from PowerFlow."


def wrap_html(title, body_text):
    body_html = body_text.replace("\n", "<br>")
    return f"""<!DOCTYPE html><html><body style="font-family:Segoe UI,sans-serif;color:#222;">
    <h2 style="color:#f0a500;">{title}</h2>
    <div style="background:#f5f5f5;padding:16px;border-radius:8px;">{body_html}</div>
    <p style="color:#888;font-size:12px;margin-top:24px;">Sent by PowerFlow Electrical Business Manager</p>
    </body></html>"""


def process_reminder(reminder, settings, force=False):
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    if not force:
        if not reminder.get("enabled"):
            return {"skipped": True, "reason": "disabled"}
        if reminder["next_due_date"] > today:
            return {"skipped": True, "reason": "not due yet"}
        if reminder["next_due_date"] == today and reminder.get("due_time", "08:00") > now_time:
            return {"skipped": True, "reason": "not due yet"}

    recipients = parse_recipients(settings, reminder.get("email_to"))
    if reminder.get("task_type") == "auto":
        subject, body = build_auto_content(reminder["category"])
        if subject is None:
            log_reminder_send(reminder["id"], reminder["title"], recipients, body, "skipped")
            if not force and reminder.get("recurrence") != "none":
                with db() as conn:
                    conn.execute(
                        "UPDATE reminders SET next_due_date=?, last_sent_at=datetime('now') WHERE id=?",
                        (advance_due_date(reminder["next_due_date"], reminder["recurrence"]), reminder["id"]),
                    )
            return {"skipped": True, "reason": "nothing to report", "message": body}
    else:
        subject = f"PowerFlow: {reminder['title']}"
        body = reminder.get("description") or reminder["title"]
        if reminder.get("description"):
            body = f"{reminder['title']}\n\n{reminder['description']}"

    html = wrap_html(reminder["title"], body)
    result = send_email(subject, html, body, recipients, settings)

    if result["ok"]:
        with db() as conn:
            next_date = reminder["next_due_date"]
            if reminder.get("recurrence") != "none":
                next_date = advance_due_date(reminder["next_due_date"], reminder["recurrence"])
            conn.execute(
                "UPDATE reminders SET last_sent_at=datetime('now'), next_due_date=? WHERE id=?",
                (next_date, reminder["id"]),
            )
            log_activity(conn, "reminder", reminder["id"], "sent", f"Email sent: {reminder['title']}")
        log_reminder_send(reminder["id"], subject, recipients, body, "sent")
        return {"ok": True, "subject": subject}
    log_reminder_send(reminder["id"], subject, recipients, body, "failed", result.get("error"))
    return {"ok": False, "error": result.get("error")}


def process_due_reminders(force_all=False):
    settings = get_email_settings()
    if not settings.get("enabled") and not force_all:
        return {"processed": 0, "results": [], "message": "Email disabled"}

    with db() as conn:
        if force_all:
            rows = conn.execute("SELECT * FROM reminders WHERE enabled=1 ORDER BY next_due_date").fetchall()
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            rows = conn.execute(
                "SELECT * FROM reminders WHERE enabled=1 AND next_due_date <= ? ORDER BY next_due_date",
                (today,),
            ).fetchall()

    results = []
    for row in rows:
        r = row_to_dict(row)
        results.append({"id": r["id"], "title": r["title"], **process_reminder(r, settings, force=force_all)})
    sent = sum(1 for x in results if x.get("ok"))
    return {"processed": len(results), "sent": sent, "results": results}


def seed_default_reminders():
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
        if count > 0:
            return
        today = datetime.now().date()
        defaults = [
            ("Low stock reorder check", "reorder", "Email when items fall at or below reorder level", "auto", "daily", "07:30", today.isoformat()),
            ("Weekly sales call list", "sales_call", "Contractor/builder accounts to contact", "auto", "weekly", "08:00", today.isoformat()),
            ("Local database backup", "backup_local", "Copy data/electrical.db to backup drive", "auto", "weekly", "17:00", today.isoformat()),
            ("Cloud backup verification", "backup_cloud", "Verify off-site backup sync and file integrity", "auto", "weekly", "17:30", today.isoformat()),
            ("Outstanding A/R follow-up", "accounts_receivable", "Email list of unpaid/overdue invoices", "auto", "daily", "09:00", today.isoformat()),
            ("Quote follow-up", "quote_followup", "Pending quotes approaching expiration", "auto", "daily", "10:00", today.isoformat()),
            ("Open PO delivery check", "po_followup", "Purchase orders awaiting receipt", "auto", "weekly", "11:00", today.isoformat()),
            ("Weekly inventory review", "inventory", "Review stock counts and valuation", "auto", "weekly", "08:30", (today + timedelta(days=(4 - today.weekday()) % 7)).isoformat()),
        ]
        for d in defaults:
            conn.execute(
                """INSERT INTO reminders (title, category, description, task_type, recurrence, due_time, next_due_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                d,
            )


def list_reminders():
    with db() as conn:
        rows = conn.execute("SELECT * FROM reminders ORDER BY next_due_date, due_time").fetchall()
    return rows_to_list(rows)


def get_reminder(rid):
    with db() as conn:
        row = conn.execute("SELECT * FROM reminders WHERE id = ?", (rid,)).fetchone()
    return row_to_dict(row)


def create_reminder(data):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO reminders (title, category, description, task_type, recurrence, due_time, next_due_date, email_to, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["title"], data["category"], data.get("description", ""),
                data.get("task_type", "manual"), data.get("recurrence", "weekly"),
                data.get("due_time", "08:00"), data["next_due_date"],
                data.get("email_to"), 1 if data.get("enabled", True) else 0,
            ),
        )
        rid = cur.lastrowid
        log_activity(conn, "reminder", rid, "created", data["title"])
        row = conn.execute("SELECT * FROM reminders WHERE id = ?", (rid,)).fetchone()
    return row_to_dict(row)


def update_reminder(rid, data):
    with db() as conn:
        conn.execute(
            """UPDATE reminders SET title=?, category=?, description=?, task_type=?, recurrence=?,
               due_time=?, next_due_date=?, email_to=?, enabled=? WHERE id=?""",
            (
                data["title"], data["category"], data.get("description", ""),
                data.get("task_type", "manual"), data.get("recurrence", "weekly"),
                data.get("due_time", "08:00"), data["next_due_date"],
                data.get("email_to"), 1 if data.get("enabled", True) else 0, rid,
            ),
        )
        row = conn.execute("SELECT * FROM reminders WHERE id = ?", (rid,)).fetchone()
    return row_to_dict(row)


def delete_reminder(rid):
    with db() as conn:
        conn.execute("DELETE FROM reminders WHERE id = ?", (rid,))


def get_reminder_log(limit=50):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT l.*, r.title AS reminder_title
            FROM reminder_log l LEFT JOIN reminders r ON r.id = l.reminder_id
            ORDER BY l.sent_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows_to_list(rows)
