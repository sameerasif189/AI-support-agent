#!/usr/bin/env python3
"""Populate Neon Postgres with deterministic synthetic ERP data (~270 rows).

Usage:
  set DATABASE_URL=postgresql://...
  python scripts/seed_db.py
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta

import psycopg


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set")

    random.seed(42)

    first_names = ["Alex", "Jordan", "Sam", "Taylor", "Casey", "Riley", "Morgan", "Quinn", "Avery", "Jamie"]
    last_names = ["Smith", "Jones", "Lee", "Brown", "Wong", "Patel", "Singh", "Khan", "Ali", "Chen"]
    tiers = ["starter", "professional", "enterprise"]
    product_cats = ["Hardware", "Software", "Services", "Consumables"]
    order_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    invoice_statuses = ["draft", "sent", "paid", "overdue"]
    ticket_statuses = ["open", "pending", "resolved"]
    ticket_categories = ["billing", "technical", "account", "shipping"]

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE order_items, invoices, orders, support_tickets, kb_articles, products, customers RESTART IDENTITY CASCADE")

            # 25 customers
            customers = []
            for i in range(1, 26):
                fn = first_names[i % len(first_names)]
                ln = last_names[i % len(last_names)]
                name = f"{fn} {ln}"
                email = f"user{i}@example.com"
                tier = tiers[i % len(tiers)]
                cur.execute(
                    "INSERT INTO customers (name, email, tier) VALUES (%s, %s, %s) RETURNING id",
                    (name, email, tier),
                )
                customers.append(cur.fetchone()[0])

            # 30 products
            products = []
            for i in range(1, 31):
                sku = f"SKU-{1000 + i}"
                cat = product_cats[i % len(product_cats)]
                price = round(10 + (i * 7.5) % 500 + random.random() * 5, 2)
                cur.execute(
                    "INSERT INTO products (sku, name, category, price) VALUES (%s, %s, %s, %s) RETURNING id",
                    (sku, f"Product Line {i}", cat, price),
                )
                products.append(cur.fetchone()[0])

            # 40 orders + ~80 order_items + 40 invoices
            orders_ids = []
            base_date = date.today() - timedelta(days=120)
            for o in range(1, 41):
                cid = customers[(o * 3) % len(customers)]
                order_number = f"ORD-{10400 + o}"
                status = order_statuses[o % len(order_statuses)]
                created = base_date + timedelta(days=o * 2 + (o % 5))
                cur.execute(
                    """
                    INSERT INTO orders (customer_id, order_number, status, total, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (cid, order_number, status, 0, created),
                )
                oid = cur.fetchone()[0]
                orders_ids.append((oid, cid, created))

                n_lines = 2 if o % 3 != 0 else 3
                line_total = 0.0
                for _ in range(n_lines):
                    pid = products[(o + _) % len(products)]
                    qty = 1 + (o % 4)
                    cur.execute("SELECT price FROM products WHERE id = %s", (pid,))
                    unit = float(cur.fetchone()[0])
                    line_total += unit * qty
                    cur.execute(
                        """
                        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (oid, pid, qty, unit),
                    )
                cur.execute("UPDATE orders SET total = %s WHERE id = %s", (round(line_total, 2), oid))

                inv_num = f"INV-{202600 + o}"
                inv_status = invoice_statuses[o % len(invoice_statuses)]
                due = created + timedelta(days=14 + (o % 10))
                cur.execute(
                    """
                    INSERT INTO invoices (order_id, invoice_number, status, amount, due_date)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (oid, inv_num, inv_status, round(line_total, 2), due),
                )

            # 30 support tickets
            subjects = [
                "Cannot download invoice PDF",
                "Order delayed — need ETA",
                "Wrong item shipped",
                "Upgrade tier request",
                "Payment failed on renewal",
                "API integration timeout",
                "Need VAT breakdown",
                "Refund status",
            ]
            for t in range(1, 31):
                cid = customers[t % len(customers)]
                subj = subjects[t % len(subjects)]
                st = ticket_statuses[t % len(ticket_statuses)]
                cat = ticket_categories[t % len(ticket_categories)]
                created = base_date + timedelta(days=t + 5)
                cur.execute(
                    """
                    INSERT INTO support_tickets (customer_id, subject, status, category, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cid, subj, st, cat, created),
                )

            # 25 KB articles (ERP documentation)
            articles = [
                ("How to download an invoice", "Open Billing > Invoices and click Download PDF next to the invoice row.", "faq"),
                ("Order status meanings", "Pending: not shipped. Processing: packing. Shipped: in transit. Delivered: completed.", "faq"),
                ("Payment methods", "We accept card, ACH, and wire for enterprise accounts.", "policy"),
                ("Refund policy", "Refunds are processed within 5–10 business days after approval.", "policy"),
                ("Account deletion", "Account deletion requires identity verification by a human agent.", "policy"),
                ("Support channels", "Reach us via web chat, WhatsApp, or Slack integrations.", "faq"),
                ("Tax and VAT", "VAT appears on invoice once billing country is verified.", "faq"),
                ("Multi-currency", "Invoices default to account currency; FX rates apply at billing time.", "faq"),
                ("API rate limits", "Standard tier: 60 req/min. Enterprise: negotiated limits.", "technical"),
                ("Webhook retries", "Failed webhooks retry with exponential backoff up to 24 hours.", "technical"),
                ("User roles", "Admin can invite users; Billing role can manage invoices only.", "faq"),
                ("Subscription renewal", "Renewals bill automatically unless canceled before renewal date.", "policy"),
                ("Credit notes", "Credit notes offset future invoices in the same billing profile.", "faq"),
                ("Shipping SLA", "Domestic 3–5 days; international 7–14 days unless expedited.", "faq"),
                ("Returns window", "Returns accepted within 30 days for unused items in original packaging.", "policy"),
                ("Data export", "Export CSV from Reports > Export with date filters.", "faq"),
                ("Inventory sync", "Inventory updates every 15 minutes from warehouse connectors.", "technical"),
                ("Purchase orders", "PO matching requires SKU and quantity alignment within tolerances.", "faq"),
                ("Vendor onboarding", "Submit W-9 and banking details in Vendor Portal.", "policy"),
                ("Audit trail", "Admin actions are logged under Settings > Audit Log.", "technical"),
                ("Integrations", "Connect Slack under Integrations > Notifications.", "faq"),
                ("Security", "Enable SSO under Enterprise settings.", "technical"),
                ("Billing disputes", "Open a billing ticket with invoice number attached.", "faq"),
                ("Late fees", "Overdue invoices may incur late fees per contract terms.", "policy"),
                ("Export compliance", "Certain SKUs require export documentation before shipment.", "policy"),
            ]
            for title, body, cat in articles[:25]:
                cur.execute(
                    "INSERT INTO kb_articles (title, body, category) VALUES (%s, %s, %s)",
                    (title, body, cat),
                )

        conn.commit()

    print("Seed complete: customers=25, products=30, orders=40, order_items≈80+, invoices=40, tickets=30, kb_articles=25")


if __name__ == "__main__":
    main()
