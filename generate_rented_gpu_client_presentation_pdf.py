"""
Client presentation PDF — lean-plan palette, ReportLab with wrapping cells (no overlap).

Run: python generate_rented_gpu_client_presentation_pdf.py
"""

from __future__ import annotations

from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT_PATH = r"c:\Users\PC\AI Support agent\ERP_AI_Support_Agent_Rented_GPU_Client_Presentation.pdf"

NAVY = colors.HexColor("#1E293B")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#334155")
BG = colors.HexColor("#F8FAFC")
GRID = colors.HexColor("#CBD5E1")
TOTAL_BG = colors.HexColor("#DBEAFE")
CODE_BG = colors.HexColor("#F1F5F9")

FULL_WIDTH = 170 * mm


def xe(text: str) -> str:
    return escape(text, entities={"\"": "&quot;", "'": "&apos;"})


def build_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "rg_title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=colors.white,
        spaceAfter=4,
    )
    header_sub = ParagraphStyle(
        "rg_header_sub",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.white,
    )
    h2 = ParagraphStyle(
        "rg_h2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=16,
        spaceAfter=10,
    )
    h3 = ParagraphStyle(
        "rg_h3",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=BLUE,
        spaceBefore=12,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "rg_body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=NAVY,
        spaceAfter=6,
    )
    small = ParagraphStyle(
        "rg_small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=SLATE,
        spaceAfter=6,
    )
    tbl_cell = ParagraphStyle(
        "rg_tbl_cell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=NAVY,
    )
    tbl_head = ParagraphStyle(
        "rg_tbl_head",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
    )
    code_cell = ParagraphStyle(
        "rg_code_cell",
        parent=styles["BodyText"],
        fontName="Courier",
        fontSize=7.8,
        leading=10,
        textColor=NAVY,
        leftIndent=4,
        rightIndent=4,
        spaceBefore=2,
        spaceAfter=2,
    )
    note_box = ParagraphStyle(
        "rg_note_box",
        parent=body,
        backColor=TOTAL_BG,
        borderPadding=10,
        spaceBefore=8,
        spaceAfter=8,
    )
    header_line2 = ParagraphStyle(
        "rg_header_l2",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.white,
        spaceAfter=0,
    )
    return title, header_sub, header_line2, h2, h3, body, small, tbl_cell, tbl_head, code_cell, note_box


def _table_wrap(data_rows, col_widths, head_style, cell_style, header_bg, body_bg=colors.white):
    """Build Table with Paragraph cells so text wraps (fixes overlap)."""
    wrapped = []
    for ri, row in enumerate(data_rows):
        line = []
        for ci, cell in enumerate(row):
            sty = head_style if ri == 0 else cell_style
            line.append(Paragraph(xe(str(cell)), sty))
        wrapped.append(line)
    tbl = Table(wrapped, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                ("BACKGROUND", (0, 1), (-1, -1), body_bg),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return tbl


def section_heading(elements, text: str, h2_style):
    """Clear visual section start: heading + rule."""
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(xe(text), h2_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=2, spaceAfter=12))


def code_block_paragraphs(elements, lines: list[str], code_style):
    """Monospace prompt sample as wrapped Paragraphs inside a shaded table row."""
    paras = [[Paragraph(xe(line), code_style)] for line in lines]
    t = Table(paras, colWidths=[FULL_WIDTH - 14])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 10))


def cost_per_conv_table(fixed_budget: float, fixed_std: float, fixed_prem: float, volumes: list[int]):
    rows = [["Monthly conversations", "All-in $/conv (Budget)", "All-in $/conv (Standard)", "All-in $/conv (Premium)"]]
    for n in volumes:
        rows.append(
            [
                f"{n:,}",
                f"${(fixed_budget / n):.3f}",
                f"${(fixed_std / n):.3f}",
                f"${(fixed_prem / n):.3f}",
            ]
        )
    return rows


def build_pdf() -> None:
    title, header_sub, header_line2, h2, h3, body, small, tbl_cell, tbl_head, code_cell, note_box = build_styles()

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="ERP AI Support Agent — Rented GPU Client Presentation",
        author="AI Support Agent",
    )

    elements: list = []

    # Header: auto row height (no fixed rowHeights) — avoids title/sub overlap
    hdr_inner = Table(
        [
            [Paragraph("ERP AI Support Agent", title)],
            [Paragraph("Rented GPU · Client Presentation", header_line2)],
        ],
        colWidths=[FULL_WIDTH],
    )
    hdr_inner.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    hdr = Table(
        [
            [hdr_inner],
            [
                Paragraph(
                    xe(
                        "Private inference on a hired GPU VM · ERP & restaurant sites · "
                        "Postgres full-text RAG · USD planning bands (not a binding vendor quote)"
                    ),
                    header_sub,
                )
            ],
        ],
        colWidths=[FULL_WIDTH],
    )
    hdr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOX", (0, 0), (-1, -1), 0, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(hdr)
    elements.append(Spacer(1, 14))

    section_heading(elements, "1) Positioning", h2)
    elements.extend(
        [
            Paragraph(
                xe(
                    "Deploy a support chatbot on the client's website (and optionally WhatsApp / Slack). "
                    "Orchestration runs on a small VPS (FastAPI). Replies are generated on a rented GPU VM "
                    "with an OpenAI-compatible server (Ollama / vLLM)."
                ),
                body,
            ),
            Paragraph(
                xe(
                    "Knowledge-grounded answers use RAG: retrieve top matching KB articles from Postgres, "
                    "inject them into the prompt together with live ERP/POS context."
                ),
                body,
            ),
            Paragraph(
                xe(
                    "Operational learning: approved transcripts become new KB rows — immediate effect via RAG "
                    "without retraining weights on every message."
                ),
                body,
            ),
        ]
    )

    section_heading(elements, "2) Architecture & request flow", h2)
    arch_data = [
        ["Step", "What happens"],
        ["1", "User sends message from embedded chat widget → HTTPS POST to FastAPI /chat."],
        ["2", "Intent + guardrails run; ERP/POS context loaded from Postgres."],
        ["3", "RAG: full-text search ranks KB articles; top-k chunks appended to prompt."],
        ["4", "FastAPI POST to rented GPU /v1/chat/completions with assembled prompt."],
        ["5", "Reply sanitized, optionally cached; JSON returned to client UI."],
        ["6", "Low confidence / sensitive intents → support ticket + human handoff."],
    ]
    elements.append(_table_wrap(arch_data, [22 * mm, 148 * mm], tbl_head, tbl_cell, BLUE, BG))
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            xe("Browsers never call the GPU directly; firewall GPU to API IPs only. Same stack for web / Slack / WhatsApp routes."),
            small,
        )
    )

    section_heading(elements, "3) RAG implementation (this codebase)", h2)
    elements.extend(
        [
            Paragraph(
                xe(
                    "KB table kb_articles stores title + body. A generated tsvector column search_vector indexes "
                    "English full text; retrieval uses websearch_to_tsquery + ts_rank_cd."
                ),
                body,
            ),
            Paragraph(xe("New installs: column included in scripts/init_schema.sql."), body),
            Paragraph(
                xe("Existing databases: run scripts/migrate_kb_rag_fts.sql once on Neon / Postgres."),
                body,
            ),
            Paragraph(xe("If the column is missing, retrieval falls back to token overlap — migrate for production quality."), small),
        ]
    )

    section_heading(elements, "4) Environment variables", h2)
    env_rows = [
        ["Variable", "Purpose"],
        ["DATABASE_URL", "Postgres (ERP tables + kb_articles + RAG index)"],
        ["LLM_API_BASE", "Rented GPU OpenAI-compatible base URL (…/v1)"],
        ["LLM_MODEL", "Model id on the GPU server"],
        ["LLM_API_KEY", "Non-empty required by app to enable LLM path (placeholder OK for local GPU)"],
    ]
    elements.append(_table_wrap(env_rows, [42 * mm, 128 * mm], tbl_head, tbl_cell, NAVY, colors.white))

    section_heading(elements, "5) Monthly fixed costs (planning bands)", h2)
    fixed_rows = [
        ["Component", "Description", "USD / mo (band)"],
        ["Rented GPU (24/7)", "Always-on inference VM · ~730 hr · Ollama/vLLM", "$180 – $1,825+"],
        ["App VPS", "FastAPI + TLS proxy (no GPU)", "$18 – $85"],
        ["PostgreSQL", "Neon / managed · ERP + KB + FTS RAG index", "$0 – $70"],
        ["Channels", "WhatsApp BSP / Slack (optional)", "$0 – $90"],
        ["Embeddings API", "$0 if using Postgres FTS RAG (no separate embedding vendor)", "$0"],
        ["External LLM API", "$0 when all completions stay on rented GPU", "$0"],
    ]
    elements.append(_table_wrap(fixed_rows, [38 * mm, 92 * mm, 40 * mm], tbl_head, tbl_cell, NAVY, colors.white))
    elements.append(
        Paragraph(
            xe("GPU rent formula: Monthly_GPU ≈ hourly_rate × 730 (example: $0.55/hr → ~$401.50/mo)."),
            body,
        )
    )

    # Reference stacks for conversation math
    fixed_budget = Decimal("295")
    fixed_std = Decimal("630")
    fixed_prem = Decimal("1295")

    elements.append(
        Paragraph(
            xe(
                f"Reference stacks for usage math — Budget ~${fixed_budget}/mo, Standard ~${fixed_std}/mo, "
                f"Premium ~${fixed_prem}/mo (illustrative; GPU quote wins)."
            ),
            small,
        )
    )

    section_heading(elements, "6) Total cost vs conversation volume", h2)
    elements.append(
        Paragraph(
            xe(
                "With a 24/7 GPU, marginal cost per extra chat is ~$0. Below spreads the full monthly stack evenly "
                "over answered conversations (fully-loaded $/conversation)."
            ),
            body,
        )
    )
    conv_rows = cost_per_conv_table(float(fixed_budget), float(fixed_std), float(fixed_prem), [500, 2500, 5000, 15000, 50000])
    elements.append(_table_wrap(conv_rows, [52 * mm, 39 * mm, 39 * mm, 40 * mm], tbl_head, tbl_cell, BLUE, BG))

    elements.append(
        KeepTogether(
            [
                Paragraph(xe("Notes"), h3),
                Paragraph(
                    xe(
                        "• Handoffs and errors still consume API/GPU time — budget using sustained peaks, not averages only."
                    ),
                    small,
                ),
                Paragraph(
                    xe(
                        "• Add ~5–15% headroom if many concurrent chats increase KV cache and latency retries."
                    ),
                    small,
                ),
                Paragraph(
                    xe(
                        "• /metrics/budget tracks heuristic USD — tune after you pick real infra invoices."
                    ),
                    small,
                ),
            ]
        )
    )

    elements.append(PageBreak())

    section_heading(elements, "7) VRAM & model sizing", h2)
    vram_data = [
        ["VRAM (approx)", "Typical models", "Notes"],
        ["~8 GB", "7B instruct Q4", "Pilot; trim RAG k and prompt"],
        ["~16 GB", "13B Q4 or 7B Q8 / FP16", "SMB production entry"],
        ["~24 GB", "13B Q8 / FP16", "Recommended default for ERP + restaurant support"],
        ["~40–48 GB", "34B Q8-class", "Premium nuance"],
        ["~80 GB", "70B+", "Highest monthly GPU rent"],
    ]
    elements.append(_table_wrap(vram_data, [28 * mm, 52 * mm, 90 * mm], tbl_head, tbl_cell, BLUE, BG))

    section_heading(elements, "8) Sample prompts by GPU tier", h2)
    elements.append(
        Paragraph(
            xe("Shorter tiers pack less instruction text; ~24 GB matches production-style grounding."),
            small,
        )
    )

    elements.append(Paragraph(xe("Tier ~8 GB"), h3))
    code_block_paragraphs(
        elements,
        [
            "Role: ACME Bistro POS support. Two sentences max.",
            "ERP: order ORD-442 status=kitchen | KB: refunds within 7 days in-store.",
            "User: Refund on yesterday takeout?",
            "Answer + one next step.",
        ],
        code_cell,
    )

    elements.append(Paragraph(xe("Tier ~16 GB"), h3))
    code_block_paragraphs(
        elements,
        [
            "You support ACME ERP (restaurant wholesale). Plain language.",
            "ERP: customer_id=1204 | SO-901 shipped | open_tickets: 1",
            "KB [hours]: Billing disputes Mon–Fri 9–6 ET via portal.",
            "User: Why is my invoice late?",
            "Lead with ERP/KB facts; ≤2 sentences; handoff if policy unknown.",
        ],
        code_cell,
    )

    elements.append(Paragraph(xe("Tier ~24 GB (production-style)"), h3))
    code_block_paragraphs(
        elements,
        [
            "Professional ERP/restaurant support. Polite, confident. No process narration.",
            "Ground: cite order_number/status when present in ERP.",
            "ERP: {customer_name: Nile Cafe, recent_orders: [{num:ORD-77,status:out_for_delivery}]}",
            "Knowledge: [delivery_policy] +15m ETA Fri–Sun peaks.",
            "User: Where is my Friday dinner order?",
            "If missing from ERP+KB: state limit + one concrete next action.",
        ],
        code_cell,
    )

    elements.append(Paragraph(xe("Tier ~40+ GB (policy-heavy KB)"), h3))
    code_block_paragraphs(
        elements,
        [
            "Senior franchised ERP + F&B support.",
            "Rank sources: signed franchise policy > KB SOP > general reasoning.",
            "ERP: full JSON (invoices, tickets, loyalty) — redact in logs.",
            "KB: allergen matrix | refund matrix | incident escalation.",
            "User: Nut allergy report at Branch 12 — first steps?",
            "Safety steps, ticket fields, escalation guardrails.",
        ],
        code_cell,
    )

    section_heading(elements, "9) Client onboarding & improvement loop", h2)
    onboard = [
        ["Phase", "Work", "Outcome"],
        ["Discover", "Menus / SKUs / policies → kb_articles ingest", "RAG corpus live"],
        ["Wire-up", "customer_id / SSO → ERP context queries", "Personalized answers"],
        ["Pilot", "~24 GB tier for 2 weeks; latency + handoff KPIs", "Go / no-go"],
        ["Operate", "Weekly KB updates from reviewed transcripts", "Rising coverage"],
        ["Optional", "Quarterly LoRA fine-tune if KB plateaus", "Extra tone fit"],
    ]
    elements.append(_table_wrap(onboard, [28 * mm, 78 * mm, 64 * mm], tbl_head, tbl_cell, BLUE, BG))

    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            xe(
                "Recommendation: standardize on ~24 GB rented GPU + 13B instruct (Q8 or FP16), "
                "Postgres FTS RAG, and KB-led iteration — private inference with predictable infra spend."
            ),
            note_box,
        )
    )
    elements.append(
        Paragraph(
            xe("Appendix: attach GPU hourly × 730, VPS invoice, and Postgres invoice to finalize the budget row."),
            small,
        )
    )

    doc.build(elements)


if __name__ == "__main__":
    build_pdf()
    print(f"PDF generated: {OUTPUT_PATH}")
