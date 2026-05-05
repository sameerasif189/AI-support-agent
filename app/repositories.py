"""Parameterized DB access for ERP demo data and KB search."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .models import RetrievalChunk


def parse_customer_id(user_id: str) -> int:
    try:
        return int(str(user_id).strip())
    except (TypeError, ValueError):
        return 1


async def get_customer_row(pool: Any, customer_id: int) -> Optional[Dict[str, Any]]:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name, email, tier, created_at FROM customers WHERE id = %s",
                (customer_id,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "tier": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            }


async def get_customer_context(pool: Any, user_id: str, query_text: str) -> Dict[str, Any]:
    cid = parse_customer_id(user_id)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name, email, tier FROM customers WHERE id = %s",
                (cid,),
            )
            crow = await cur.fetchone()
            if not crow:
                return {
                    "user_id": user_id,
                    "resolved_customer_id": cid,
                    "error": "customer_not_found",
                    "query": query_text,
                }

            await cur.execute(
                """
                SELECT order_number, status, total, created_at
                FROM orders
                WHERE customer_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (cid,),
            )
            recent_orders = []
            for r in await cur.fetchall():
                recent_orders.append(
                    {
                        "order_number": r[0],
                        "status": r[1],
                        "total": float(r[2]) if r[2] is not None else 0,
                        "created_at": r[3].isoformat() if r[3] else None,
                    }
                )

            await cur.execute(
                "SELECT COUNT(*) FROM support_tickets WHERE customer_id = %s AND status IN ('open', 'pending')",
                (cid,),
            )
            open_tickets = int((await cur.fetchone())[0])

            await cur.execute(
                """
                SELECT i.invoice_number, i.status, i.amount, i.due_date, o.order_number
                FROM invoices i
                JOIN orders o ON o.id = i.order_id
                WHERE o.customer_id = %s
                ORDER BY i.id DESC
                LIMIT 1
                """,
                (cid,),
            )
            inv_row = await cur.fetchone()
            last_invoice = None
            if inv_row:
                last_invoice = {
                    "invoice_number": inv_row[0],
                    "status": inv_row[1],
                    "amount": float(inv_row[2]) if inv_row[2] is not None else 0,
                    "due_date": inv_row[3].isoformat() if inv_row[3] else None,
                    "order_number": inv_row[4],
                }

            last_order_id = recent_orders[0]["order_number"] if recent_orders else None

            return {
                "user_id": user_id,
                "resolved_customer_id": cid,
                "customer_name": crow[1],
                "account_tier": crow[3],
                "email": crow[2],
                "last_order_id": last_order_id,
                "recent_orders": recent_orders,
                "open_tickets": open_tickets,
                "last_invoice": last_invoice,
                "query": query_text,
            }


async def create_support_ticket(pool: Any, user_id: str, summary: str) -> str:
    cid = parse_customer_id(user_id)
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO support_tickets (customer_id, subject, status, category)
                    VALUES (%s, %s, 'open', 'general')
                    RETURNING id
                    """,
                    (cid, summary[:300]),
                )
                tid = (await cur.fetchone())[0]
        return f"TKT-{tid}"


async def search_kb(pool: Any, query: str, k: int) -> List[RetrievalChunk]:
    tokens = set(query.lower().split())
    if not tokens:
        return []
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, category, title, body FROM kb_articles")
            rows = await cur.fetchall()

    scored: List[Tuple[float, RetrievalChunk]] = []
    for row in rows:
        doc_id, category, title, body = row
        text = f"{title} {body}"
        score = len(tokens.intersection(set(text.lower().split()))) / (len(tokens) + 1)
        scored.append(
            (
                score,
                RetrievalChunk(
                    id=f"kb-{doc_id}",
                    source=category,
                    text=f"{title}. {body}",
                    score=float(round(score, 3)),
                ),
            )
        )
    scored.sort(reverse=True, key=lambda x: x[0])
    return [c for _, c in scored[:k]]


async def get_order_detail(pool: Any, order_id: int) -> Optional[Dict[str, Any]]:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT o.id, o.order_number, o.status, o.total, o.created_at,
                       o.customer_id, c.name, c.email
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE o.id = %s
                """,
                (order_id,),
            )
            orow = await cur.fetchone()
            if not orow:
                return None
            oid = orow[0]
            await cur.execute(
                """
                SELECT p.sku, p.name, oi.quantity, oi.unit_price
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = %s
                """,
                (oid,),
            )
            items = []
            for r in await cur.fetchall():
                items.append(
                    {
                        "sku": r[0],
                        "product_name": r[1],
                        "quantity": r[2],
                        "unit_price": float(r[3]) if r[3] is not None else 0,
                    }
                )
            return {
                "id": orow[0],
                "order_number": orow[1],
                "status": orow[2],
                "total": float(orow[3]) if orow[3] is not None else 0,
                "created_at": orow[4].isoformat() if orow[4] else None,
                "customer_id": orow[5],
                "customer_name": orow[6],
                "customer_email": orow[7],
                "items": items,
            }


async def list_orders_for_customer(pool: Any, customer_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, order_number, status, total, created_at
                FROM orders
                WHERE customer_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (customer_id, limit),
            )
            rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "order_number": r[1],
            "status": r[2],
            "total": float(r[3]) if r[3] is not None else 0,
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


async def list_unpaid_invoices(pool: Any, user_id: str) -> List[Dict[str, Any]]:
    cid = parse_customer_id(user_id)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT i.invoice_number, i.status, i.amount, i.due_date, o.order_number
                FROM invoices i
                JOIN orders o ON o.id = i.order_id
                WHERE o.customer_id = %s AND i.status NOT IN ('paid')
                ORDER BY i.due_date ASC
                """,
                (cid,),
            )
            rows = await cur.fetchall()
    return [
        {
            "invoice_number": r[0],
            "status": r[1],
            "amount": float(r[2]) if r[2] is not None else 0,
            "due_date": r[3].isoformat() if r[3] else None,
            "order_number": r[4],
        }
        for r in rows
    ]
