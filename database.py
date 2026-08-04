import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "electrical.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('wholesaler', 'manufacturer')),
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                account_number TEXT,
                payment_terms TEXT DEFAULT 'Net 30',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                unit TEXT DEFAULT 'each',
                cost REAL DEFAULT 0,
                price REAL DEFAULT 0,
                reorder_level INTEGER DEFAULT 10,
                supplier_id INTEGER,
                manufacturer_part TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL UNIQUE,
                quantity_on_hand INTEGER DEFAULT 0,
                quantity_reserved INTEGER DEFAULT 0,
                location TEXT DEFAULT 'Main Warehouse',
                last_received TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT UNIQUE NOT NULL,
                supplier_id INTEGER NOT NULL,
                status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'sent', 'partial', 'received', 'cancelled')),
                order_date TEXT NOT NULL,
                expected_date TEXT,
                subtotal REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );

            CREATE TABLE IF NOT EXISTS purchase_order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_ordered INTEGER NOT NULL,
                quantity_received INTEGER DEFAULT 0,
                unit_cost REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('contractor', 'builder', 'commercial', 'residential')),
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                tax_exempt INTEGER DEFAULT 0,
                credit_limit REAL DEFAULT 10000,
                payment_terms TEXT DEFAULT 'Net 30',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                site_address TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'on_hold', 'cancelled')),
                start_date TEXT,
                end_date TEXT,
                estimated_value REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                job_id INTEGER,
                status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'sent', 'accepted', 'declined', 'expired')),
                quote_date TEXT NOT NULL,
                valid_until TEXT,
                subtotal REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS quote_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL,
                product_id INTEGER,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS sales_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                job_id INTEGER,
                quote_id INTEGER,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'partial', 'shipped', 'delivered', 'cancelled')),
                order_date TEXT NOT NULL,
                required_date TEXT,
                subtotal REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (quote_id) REFERENCES quotes(id)
            );

            CREATE TABLE IF NOT EXISTS sales_order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_ordered INTEGER NOT NULL,
                quantity_shipped INTEGER DEFAULT 0,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (sales_order_id) REFERENCES sales_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                sales_order_id INTEGER,
                job_id INTEGER,
                status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'sent', 'partial', 'paid', 'overdue', 'void')),
                invoice_date TEXT NOT NULL,
                due_date TEXT,
                subtotal REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                amount_paid REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (sales_order_id) REFERENCES sales_orders(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS invoice_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                action TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER DEFAULT 0,
                smtp_host TEXT DEFAULT '',
                smtp_port INTEGER DEFAULT 587,
                smtp_user TEXT DEFAULT '',
                smtp_password TEXT DEFAULT '',
                from_email TEXT DEFAULT '',
                to_emails TEXT DEFAULT '',
                use_tls INTEGER DEFAULT 1,
                check_interval_minutes INTEGER DEFAULT 15,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL CHECK(category IN (
                    'reorder', 'sales_call', 'backup_local', 'backup_cloud',
                    'accounts_receivable', 'quote_followup', 'po_followup', 'inventory', 'general'
                )),
                description TEXT,
                task_type TEXT DEFAULT 'manual' CHECK(task_type IN ('manual', 'auto')),
                recurrence TEXT DEFAULT 'weekly' CHECK(recurrence IN ('none', 'daily', 'weekly', 'monthly')),
                due_time TEXT DEFAULT '08:00',
                next_due_date TEXT NOT NULL,
                email_to TEXT,
                enabled INTEGER DEFAULT 1,
                last_sent_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reminder_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER,
                subject TEXT NOT NULL,
                recipients TEXT NOT NULL,
                body_preview TEXT,
                status TEXT NOT NULL CHECK(status IN ('sent', 'failed', 'skipped')),
                error_message TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE SET NULL
            );

            INSERT OR IGNORE INTO email_settings (id) VALUES (1);
            """
        )


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]


def log_activity(conn, entity_type, entity_id, action, description):
    conn.execute(
        "INSERT INTO activity_log (entity_type, entity_id, action, description) VALUES (?, ?, ?, ?)",
        (entity_type, entity_id, action, description),
    )


def generate_number(prefix, conn, table, column):
    year = datetime.now().strftime("%Y")
    pattern = f"{prefix}-{year}-%"
    row = conn.execute(
        f"SELECT {column} FROM {table} WHERE {column} LIKE ? ORDER BY id DESC LIMIT 1",
        (pattern,),
    ).fetchone()
    if row:
        last_num = int(row[column].split("-")[-1])
        return f"{prefix}-{year}-{last_num + 1:04d}"
    return f"{prefix}-{year}-0001"
