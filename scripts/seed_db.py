#!/usr/bin/env python3
"""Populate Neon Postgres with ~500 linked ERP rows + demo login users.

Usage:
  set DATABASE_URL=postgresql://...
  python scripts/seed_db.py

Login: password = user's first name (case-insensitive).
  admin / Admin
  agent / Morgan
  cust1 / Alex  (customer id 1)
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta
from pathlib import Path

import psycopg

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# Target ~500 rows across core tables (excluding sessions / runtime RAG uploads)
N_CUSTOMERS = 50
N_PRODUCTS = 40
N_ORDERS = 80
N_TICKETS = 50
N_KB = 30
# order_items ≈ 2 per order → 160; invoices = 80 → total 50+40+80+160+80+50+30+10 users = 500


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set")

    random.seed(42)

    first_names = [
        "Alex", "Jordan", "Sam", "Taylor", "Casey", "Riley", "Morgan", "Quinn",
        "Avery", "Jamie", "Drew", "Blake", "Cameron", "Dakota", "Emery", "Finley",
    ]
    last_names = [
        "Smith", "Jones", "Lee", "Brown", "Wong", "Patel", "Singh", "Khan",
        "Ali", "Chen", "Garcia", "Miller", "Davis", "Wilson", "Moore", "Taylor",
    ]
    tiers = ["starter", "professional", "enterprise"]
    product_cats = ["Hardware", "Software", "Services", "Consumables"]
    order_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    invoice_statuses = ["draft", "sent", "paid", "overdue"]
    ticket_statuses = ["open", "pending", "resolved"]
    ticket_categories = ["billing", "technical", "account", "shipping"]

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE app_sessions, rag_documents, app_users, order_items, invoices, "
                "orders, support_tickets, kb_articles, products, customers RESTART IDENTITY CASCADE"
            )

            customers: list[tuple[int, str]] = []
            for i in range(1, N_CUSTOMERS + 1):
                fn = first_names[i % len(first_names)]
                ln = last_names[(i * 2) % len(last_names)]
                name = f"{fn} {ln}"
                email = f"user{i}@example.com"
                tier = tiers[i % len(tiers)]
                cur.execute(
                    "INSERT INTO customers (name, email, tier) VALUES (%s, %s, %s) RETURNING id",
                    (name, email, tier),
                )
                cid = cur.fetchone()[0]
                customers.append((cid, fn))

            products = []
            for i in range(1, N_PRODUCTS + 1):
                sku = f"SKU-{1000 + i}"
                cat = product_cats[i % len(product_cats)]
                price = round(10 + (i * 7.5) % 500 + random.random() * 5, 2)
                cur.execute(
                    "INSERT INTO products (sku, name, category, price) VALUES (%s, %s, %s, %s) RETURNING id",
                    (sku, f"Product Line {i}", cat, price),
                )
                products.append(cur.fetchone()[0])

            base_date = date.today() - timedelta(days=365)
            for o in range(1, N_ORDERS + 1):
                cid = customers[(o * 3) % len(customers)][0]
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

                n_lines = 2 if o % 3 != 0 else 3
                line_total = 0.0
                for li in range(n_lines):
                    pid = products[(o + li) % len(products)]
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
            for t in range(1, N_TICKETS + 1):
                cid = customers[t % len(customers)][0]
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

            for i in range(1, N_KB + 1):
                cur.execute(
                    """
                    INSERT INTO kb_articles (title, body, category)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        f"ERP help topic {i}",
                        f"This article explains ERP feature area {i}. "
                        f"Use the Orders and Billing modules for self-service.",
                        "faq" if i % 2 else "policy",
                    ),
                )

            cur.execute(
                """
                INSERT INTO app_users (username, first_name, role, customer_id)
                VALUES ('admin', 'Admin', 'admin', NULL)
                """
            )
            cur.execute(
                """
                INSERT INTO app_users (username, first_name, role, customer_id)
                VALUES ('agent', 'Morgan', 'agent', NULL)
                """
            )
            for idx in range(1, 9):
                cid, fn = customers[idx - 1]
                cur.execute(
                    """
                    INSERT INTO app_users (username, first_name, role, customer_id)
                    VALUES (%s, %s, 'customer', %s)
                    """,
                    (f"cust{idx}", fn, cid),
                )

        conn.commit()

    total = N_CUSTOMERS + N_PRODUCTS + N_ORDERS + (N_ORDERS * 2) + N_ORDERS + N_TICKETS + N_KB + 10
    print(
        f"Seed complete (~{total} rows): customers={N_CUSTOMERS}, products={N_PRODUCTS}, "
        f"orders={N_ORDERS}, order_items~{N_ORDERS * 2}, invoices={N_ORDERS}, "
        f"tickets={N_TICKETS}, kb={N_KB}, users=10"
    )
    print("Log in: admin/Admin, agent/Morgan, cust1..cust8/<first name>")


if __name__ == "__main__":
    main()
