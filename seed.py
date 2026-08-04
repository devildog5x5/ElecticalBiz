from database import db, log_activity


def seed_if_empty():
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        if count > 0:
            return

        suppliers = [
            ("Graybar Electric", "wholesaler", "Mike Stevens", "mike.stevens@graybar.com", "555-0101",
             "1200 Industrial Blvd, Denver, CO", "GRY-88421", "Net 30", "Primary wire & conduit supplier"),
            ("Rexel USA", "wholesaler", "Sarah Chen", "sarah.chen@rexel.com", "555-0102",
             "450 Commerce Way, Phoenix, AZ", "RXL-55210", "Net 45", "Panels, breakers, switchgear"),
            ("Southwire Company", "manufacturer", "James Wilson", "james.wilson@southwire.com", "555-0201",
             "1 Southwire Dr, Carrollton, GA", "SW-100045", "Net 30", "Direct wire manufacturer"),
            ("Eaton Corporation", "manufacturer", "Lisa Park", "lisa.park@eaton.com", "555-0202",
             "1000 Eaton Blvd, Cleveland, OH", "ETN-77832", "Net 30", "Breakers, panels, lighting controls"),
            ("Platt Electric Supply", "wholesaler", "Tom Rivera", "tom.rivera@platt.com", "555-0103",
             "890 Supply Chain Rd, Portland, OR", "PLT-33109", "Net 30", "Job site delivery available"),
        ]
        for s in suppliers:
            conn.execute(
                "INSERT INTO suppliers (name, type, contact_name, email, phone, address, account_number, payment_terms, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                s,
            )

        products = [
            ("WIRE-12-2-RMW", "12/2 Romex Wire 250ft", "Wire & Cable", "12 AWG NM-B copper wire, 250ft roll", "roll", 89.50, 124.99, 20, 1, "28827426"),
            ("WIRE-10-3-RMW", "10/3 Romex Wire 250ft", "Wire & Cable", "10 AWG NM-B copper wire, 250ft roll", "roll", 145.00, 198.99, 15, 1, "28828226"),
            ("BRKR-20A-SQD", "Square D QO 20A Breaker", "Breakers", "Single pole 20A circuit breaker", "each", 8.25, 14.99, 50, 2, "QO120"),
            ("BRKR-15A-SQD", "Square D QO 15A Breaker", "Breakers", "Single pole 15A circuit breaker", "each", 7.50, 13.99, 50, 2, "QO115"),
            ("PNL-200A-QO", "200A Main Breaker Panel", "Panels", "30-space 200A main breaker load center", "each", 185.00, 289.99, 8, 2, "QO130M200"),
            ("PNL-100A-QO", "100A Main Breaker Panel", "Panels", "20-space 100A main breaker load center", "each", 95.00, 159.99, 10, 2, "QO120M100"),
            ("COND-1-EMT10", "1\" EMT Conduit 10ft", "Conduit", "Electrical metallic tubing, 10ft stick", "stick", 6.80, 11.49, 100, 1, "EMT-100"),
            ("COND-3/4-EMT10", "3/4\" EMT Conduit 10ft", "Conduit", "Electrical metallic tubing, 10ft stick", "stick", 4.20, 7.99, 150, 1, "EMT-075"),
            ("BOX-4S-DP", "4\" Square Deep Box", "Boxes & Fittings", "4-inch square deep device box", "each", 2.10, 4.49, 200, 5, "DS4D"),
            ("GFCI-20A-WR", "20A Weather Resistant GFCI", "Devices", "Tamper-resistant weather-resistant GFCI receptacle", "each", 14.50, 24.99, 40, 4, "TRWRGF20"),
            ("LED-6-3000K", "6\" LED Recessed Can 3000K", "Lighting", "6-inch LED recessed downlight, 3000K warm white", "each", 18.00, 32.99, 60, 4, "RL6-30K"),
            ("MC-12-2-250", "12/2 MC Cable 250ft", "Wire & Cable", "Metal-clad armored cable 12/2, 250ft", "roll", 210.00, 298.99, 12, 3, "MC-12-2-250"),
        ]
        for p in products:
            conn.execute(
                "INSERT INTO products (sku, name, category, description, unit, cost, price, reorder_level, supplier_id, manufacturer_part) VALUES (?,?,?,?,?,?,?,?,?,?)",
                p,
            )

        for i, qty in enumerate([45, 28, 120, 95, 12, 18, 240, 380, 520, 65, 88, 22], start=1):
            conn.execute(
                "INSERT INTO inventory (product_id, quantity_on_hand, quantity_reserved, location, last_received) VALUES (?,?,0,'Main Warehouse',date('now'))",
                (i, qty),
            )

        customers = [
            ("Summit Electric Contractors", "contractor", "Dave Morrison", "dave@summitelectric.com", "555-1001",
             "2200 Builder Lane, Austin, TX", 0, 50000, "Net 30", "Commercial & industrial work"),
            ("Horizon Builders LLC", "builder", "Karen Walsh", "karen@horizonbuilders.com", "555-1002",
             "1500 Development Dr, Dallas, TX", 0, 75000, "Net 45", "Residential subdivisions"),
            ("Metro Commercial Electric", "contractor", "Ray Patel", "ray@metrocommercialelectric.com", "555-1003",
             "800 Tower St, Houston, TX", 0, 100000, "Net 30", "Large commercial projects"),
            ("Oakwood Custom Homes", "builder", "Emily Foster", "emily@oakwoodhomes.com", "555-1004",
             "340 Craftsman Way, San Antonio, TX", 0, 35000, "Net 30", "High-end custom homes"),
            ("Precision Wiring Inc", "contractor", "Chris Nguyen", "chris@precisionwiring.com", "555-1005",
             "675 Industrial Park, Fort Worth, TX", 0, 40000, "Net 15", "Service & remodel work"),
        ]
        for c in customers:
            conn.execute(
                "INSERT INTO customers (name, type, contact_name, email, phone, address, tax_exempt, credit_limit, payment_terms, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                c,
            )

        jobs = [
            ("JOB-2026-0001", 1, "Riverside Office Park Phase 2", "1200 Riverside Dr, Austin, TX", "active", "2026-01-15", "2026-06-30", 125000, "Electrical rough-in and trim"),
            ("JOB-2026-0002", 2, "Willow Creek Subdivision Lot 14-28", "Willow Creek Rd, Dallas, TX", "active", "2026-02-01", "2026-08-15", 89000, "New construction residential"),
            ("JOB-2026-0003", 3, "Downtown Tower Retrofit", "500 Main St, Houston, TX", "active", "2026-03-01", "2026-12-31", 450000, "Panel upgrades and LED retrofit"),
            ("JOB-2026-0004", 4, "Oakwood Estate Model Home", "12 Estate Blvd, San Antonio, TX", "completed", "2025-11-01", "2026-02-28", 42000, "Model home electrical package"),
        ]
        for j in jobs:
            conn.execute(
                "INSERT INTO jobs (job_number, customer_id, name, site_address, status, start_date, end_date, estimated_value, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                j,
            )

        conn.execute(
            """INSERT INTO purchase_orders (po_number, supplier_id, status, order_date, expected_date, subtotal, tax, total, notes)
               VALUES ('PO-2026-0001', 1, 'received', '2026-01-10', '2026-01-17', 4250.00, 340.00, 4590.00, 'Wire and conduit restock')"""
        )
        po_lines = [
            (1, 1, 30, 30, 89.50, 2685.00),
            (1, 7, 100, 100, 6.80, 680.00),
            (1, 8, 150, 150, 4.20, 630.00),
            (1, 9, 50, 50, 2.10, 105.00),
        ]
        for line in po_lines:
            conn.execute(
                "INSERT INTO purchase_order_lines (purchase_order_id, product_id, quantity_ordered, quantity_received, unit_cost, line_total) VALUES (?,?,?,?,?,?)",
                line,
            )

        conn.execute(
            """INSERT INTO purchase_orders (po_number, supplier_id, status, order_date, expected_date, subtotal, tax, total, notes)
               VALUES ('PO-2026-0002', 2, 'sent', '2026-07-28', '2026-08-05', 2890.00, 231.20, 3121.20, 'Breaker and panel order')"""
        )
        po_lines2 = [
            (2, 3, 50, 0, 8.25, 412.50),
            (2, 4, 50, 0, 7.50, 375.00),
            (2, 5, 5, 0, 185.00, 925.00),
            (2, 6, 8, 0, 95.00, 760.00),
        ]
        for line in po_lines2:
            conn.execute(
                "INSERT INTO purchase_order_lines (purchase_order_id, product_id, quantity_ordered, quantity_received, unit_cost, line_total) VALUES (?,?,?,?,?,?)",
                line,
            )

        conn.execute(
            """INSERT INTO quotes (quote_number, customer_id, job_id, status, quote_date, valid_until, subtotal, tax, total, notes)
               VALUES ('QT-2026-0001', 1, 1, 'accepted', '2026-01-05', '2026-02-05', 18500.00, 1480.00, 19980.00, 'Phase 2 rough-in materials')"""
        )
        quote_lines = [
            (1, 1, "12/2 Romex Wire 250ft", 40, 124.99, 4999.60),
            (1, 3, "Square D QO 20A Breaker", 60, 14.99, 899.40),
            (1, 5, "200A Main Breaker Panel", 4, 289.99, 1159.96),
            (1, 7, "1\" EMT Conduit 10ft", 200, 11.49, 2298.00),
            (1, None, "Labor allowance - material staging", 1, 9143.04, 9143.04),
        ]
        for line in quote_lines:
            conn.execute(
                "INSERT INTO quote_lines (quote_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)",
                line,
            )

        conn.execute(
            """INSERT INTO sales_orders (order_number, customer_id, job_id, quote_id, status, order_date, required_date, subtotal, tax, total, notes)
               VALUES ('SO-2026-0001', 1, 1, 1, 'confirmed', '2026-01-20', '2026-02-01', 18500.00, 1480.00, 19980.00, 'Riverside Phase 2 delivery')"""
        )
        so_lines = [
            (1, 1, 40, 0, 124.99, 4999.60),
            (1, 3, 60, 0, 14.99, 899.40),
            (1, 5, 4, 0, 289.99, 1159.96),
            (1, 7, 200, 0, 11.49, 2298.00),
        ]
        for line in so_lines:
            conn.execute(
                "INSERT INTO sales_order_lines (sales_order_id, product_id, quantity_ordered, quantity_shipped, unit_price, line_total) VALUES (?,?,?,?,?,?)",
                line,
            )

        conn.execute(
            """INSERT INTO invoices (invoice_number, customer_id, sales_order_id, job_id, status, invoice_date, due_date, subtotal, tax, total, amount_paid, notes)
               VALUES ('INV-2026-0001', 1, 1, 1, 'sent', '2026-01-22', '2026-02-21', 18500.00, 1480.00, 19980.00, 0, 'Riverside Phase 2 - initial shipment')"""
        )
        inv_lines = [
            (1, 1, "12/2 Romex Wire 250ft", 40, 124.99, 4999.60),
            (1, 3, "Square D QO 20A Breaker", 60, 14.99, 899.40),
            (1, 5, "200A Main Breaker Panel", 4, 289.99, 1159.96),
            (1, 7, "1\" EMT Conduit 10ft", 200, 11.49, 2298.00),
            (1, None, "Labor allowance - material staging", 1, 9143.04, 9143.04),
        ]
        for line in inv_lines:
            conn.execute(
                "INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)",
                line,
            )

        activities = [
            ("purchase_order", 1, "received", "PO-2026-0001 received from Graybar Electric"),
            ("sales_order", 1, "created", "SO-2026-0001 confirmed for Summit Electric"),
            ("invoice", 1, "sent", "INV-2026-0001 sent to Summit Electric Contractors"),
            ("purchase_order", 2, "sent", "PO-2026-0002 sent to Rexel USA"),
            ("quote", 1, "accepted", "QT-2026-0001 accepted by Summit Electric"),
        ]
        for a in activities:
            log_activity(conn, *a)
