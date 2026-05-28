"""
Multi-tenant cost playbooks — GPU path vs LLM API path (ReportLab, lean styling).

Outputs:
  ERP_AI_Support_Agent_GPU_MultiTenant_Cost_Playbook.pdf
  ERP_AI_Support_Agent_LLM_API_MultiTenant_Cost_Playbook.pdf

Run: python generate_multi_tenant_cost_playbooks_pdf.py
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE = r"c:\Users\PC\AI Support agent"
OUT_GPU = BASE + r"\ERP_AI_Support_Agent_GPU_MultiTenant_Cost_Playbook.pdf"
OUT_LLM = BASE + r"\ERP_AI_Support_Agent_LLM_API_MultiTenant_Cost_Playbook.pdf"

NAVY = colors.HexColor("#1E293B")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#334155")
BG = colors.HexColor("#F8FAFC")
GRID = colors.HexColor("#CBD5E1")
TOTAL_BG = colors.HexColor("#DBEAFE")

FULL_WIDTH = 170 * mm


def xe(text: str) -> str:
    return escape(text, entities={"\"": "&quot;", "'": "&apos;"})


def build_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "mt_title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.white,
    )
    header_sub = ParagraphStyle(
        "mt_header_sub",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.white,
    )
    header_l2 = ParagraphStyle(
        "mt_header_l2",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.white,
    )
    h2 = ParagraphStyle(
        "mt_h2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=10,
    )
    body = ParagraphStyle(
        "mt_body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=NAVY,
        spaceAfter=6,
    )
    small = ParagraphStyle(
        "mt_small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=SLATE,
        spaceAfter=6,
    )
    tbl_cell = ParagraphStyle(
        "mt_tbl_cell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11.5,
        textColor=NAVY,
    )
    tbl_head = ParagraphStyle(
        "mt_tbl_head",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    note_box = ParagraphStyle(
        "mt_note",
        parent=body,
        backColor=TOTAL_BG,
        borderPadding=10,
        spaceBefore=8,
        spaceAfter=8,
    )
    return title, header_sub, header_l2, h2, body, small, tbl_cell, tbl_head, note_box


def wrap_table(data_rows, col_widths, tbl_head, tbl_cell, header_bg, body_bg=colors.white):
    wrapped = []
    for ri, row in enumerate(data_rows):
        sty = tbl_head if ri == 0 else tbl_cell
        wrapped.append([Paragraph(xe(str(c)), sty) for c in row])
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                ("BACKGROUND", (0, 1), (-1, -1), body_bg),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def section_heading(elements, text: str, h2_style):
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(xe(text), h2_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=2, spaceAfter=12))


def navy_header(elements, title_txt: str, subtitle_doc: str, styles_pack):
    title, header_sub, header_l2, *_ = styles_pack
    inner = Table(
        [[Paragraph(xe(title_txt), title)], [Paragraph(xe(subtitle_doc), header_l2)]],
        colWidths=[FULL_WIDTH],
    )
    hdr = Table(
        [[inner], [Paragraph(xe("Planning bands — not vendor quotes. Attach invoices / pricing PDFs."), header_sub)]],
        colWidths=[FULL_WIDTH],
    )
    hdr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(hdr)
    elements.append(Spacer(1, 12))


def platform_misc_table(tbl_head, tbl_cell):
    """Itemized shared costs — identical in both playbooks."""
    rows = [
        ["Line item", "Typical USD / month (band)", "Notes"],
        [
            "Application / orchestration host (FastAPI VPS)",
            "$28 – $120",
            "Single VM vs small HA pair; rises with traffic & tenants",
        ],
        ["PostgreSQL (Neon or managed)", "$15 – $95", "Storage, connections, HA tier"],
        ["Domain + DNS", "$0 – $24", "Registrar; amortize annual to monthly"],
        ["TLS certificates", "$0 – $18", "Often $0 (ACME); managed certs extra"],
        ["CDN / edge / WAF (optional)", "$0 – $65", "Public widget + bot protection"],
        ["Observability (logs, metrics, uptime)", "$12 – $85", "Vendor tier & retention"],
        ["Error tracking (optional, e.g. Sentry-class)", "$0 – $39", "Often free tier → paid"],
        ["Backups + object storage", "$6 – $35", "DB backups + log archives"],
        [
            "WhatsApp / BSP (aggregate for 5–6 clients)",
            "$75 – $520",
            "Dominant variable — Meta/BSP conversation pricing differs",
        ],
        ["Slack app / workspace ops", "$6 – $42", "Usually small vs WhatsApp"],
        ["Email / transactional alerts", "$0 – $28", "SES-class ops notifications"],
        ["Secrets manager + CI (optional)", "$0 – $45", "GitHub Actions minutes, vault"],
        [
            "Subtotal — platform & channels (planning range)",
            "~$142 – $1,076",
            "Sum of band lows / highs above (wide mostly due to WhatsApp)",
        ],
        [
            "Illustrative midpoint bundle for scenario math below",
            "~$425 / mo",
            "Mid estimate excluding extremes; replace with your quotes",
        ],
    ]
    return wrap_table(rows, [52 * mm, 42 * mm, 76 * mm], tbl_head, tbl_cell, NAVY, colors.white)


def gpu_monthly_from_hourly(low_h: float, high_h: float) -> tuple[float, float]:
    return low_h * 730, high_h * 730


def llm_monthly_cost(conv: int, tin: int, tout: int, pin_per_m: float, pout_per_m: float) -> float:
    return conv * (tin * pin_per_m / 1_000_000 + tout * pout_per_m / 1_000_000)


def build_gpu_pdf(styles_pack) -> None:
    _, _, _, h2, body, small, tbl_cell, tbl_head, note_box = styles_pack
    doc = SimpleDocTemplate(
        OUT_GPU,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="GPU multi-tenant cost playbook",
    )
    elements: list = []

    navy_header(
        elements,
        "ERP AI Support Agent",
        "GPU inference — multi-tenant cost playbook (5–6 clients · 5k–10k conv/client · mo)",
        styles_pack,
    )

    section_heading(elements, "Assumptions", h2)
    elements.append(
        Paragraph(
            xe(
                "Five to six production tenants (mix restaurant + ERP SaaS). Each tenant target "
                "5,000–10,000 conversations per month. Aggregate scenarios: 25k / 30k / 50k / 60k conv/month. "
                "One shared FastAPI stack; Postgres holds ERP + kb_articles; RAG retrieval is CPU + Postgres FTS."
            ),
            body,
        )
    )

    section_heading(elements, "GPU options (rented VM)", h2)
    gpu_rows = [
        ["VRAM band", "Example models", "Hourly rent (illustr.)", "~Monthly @ 730 h"],
        ["~8 GB", "7B Q4 instruct", "$0.28 – $0.48", f"${gpu_monthly_from_hourly(0.28, 0.48)[0]:,.0f} – ${gpu_monthly_from_hourly(0.28, 0.48)[1]:,.0f}"],
        ["~16 GB", "13B Q4 / 7B FP16", "$0.38 – $0.72", f"${gpu_monthly_from_hourly(0.38, 0.72)[0]:,.0f} – ${gpu_monthly_from_hourly(0.38, 0.72)[1]:,.0f}"],
        ["~24 GB", "13B Q8 / FP16 (recommended)", "$0.45 – $0.95", f"${gpu_monthly_from_hourly(0.45, 0.95)[0]:,.0f} – ${gpu_monthly_from_hourly(0.45, 0.95)[1]:,.0f}"],
        ["~40–48 GB", "34B class", "$0.95 – $1.85", f"${gpu_monthly_from_hourly(0.95, 1.85)[0]:,.0f} – ${gpu_monthly_from_hourly(0.95, 1.85)[1]:,.0f}"],
        ["~80 GB", "70B+ class", "$1.85 – $3.50", f"${gpu_monthly_from_hourly(1.85, 3.5)[0]:,.0f} – ${gpu_monthly_from_hourly(1.85, 3.5)[1]:,.0f}"],
    ]
    elements.append(wrap_table(gpu_rows, [22 * mm, 48 * mm, 38 * mm, 62 * mm], tbl_head, tbl_cell, BLUE, BG))
    elements.append(
        Paragraph(
            xe("Formula: monthly_GPU_usd ≈ hourly_rate × 730 for 24/7. Spot/interruptible cheaper but risky for SLA."),
            small,
        )
    )

    section_heading(elements, "Multi-tenant sizing note", h2)
    elements.append(
        Paragraph(
            xe(
                "Monthly conversation counts do not fix GPU size — peak concurrent chats, context length (ERP+RAG), "
                "and KV cache drive VRAM. Add rate limits per tenant, horizontal second GPU, or queue if p95 latency breaches SLO."
            ),
            body,
        )
    )

    section_heading(elements, "Platform & miscellaneous costs (itemized)", h2)
    elements.append(
        Paragraph(
            xe(
                "Listed separately — same structure as LLM API playbook. WhatsApp row varies most by BSP/Meta pricing."
            ),
            small,
        )
    )
    elements.append(platform_misc_table(tbl_head, tbl_cell))
    elements.append(Spacer(1, 10))

    section_heading(elements, "Grand totals — GPU path (illustrative mids)", h2)
    elements.append(
        Paragraph(
            xe(
                "Inference: one 24/7 GPU VM midpoint ~$420/mo ($0.575/hr × 730). Platform midpoint ~$425/mo from table above. "
                "GPU rent does not scale with aggregate conv count until you add capacity."
            ),
            body,
        )
    )
    gpu_mid = 420.0
    plat_mid = 425.0
    grand = gpu_mid + plat_mid
    scen_rows = [
        ["Aggregate conv / month", "GPU inference (mid)", "Platform (mid)", "Grand total (mid)", "Fully-loaded $/conv"],
        ["25,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 25000:.4f}"],
        ["30,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 30000:.4f}"],
        ["50,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 50000:.4f}"],
        ["60,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 60000:.4f}"],
    ]
    elements.append(wrap_table(scen_rows, [34 * mm, 32 * mm, 32 * mm, 34 * mm, 38 * mm], tbl_head, tbl_cell, NAVY, colors.white))
    elements.append(
        Paragraph(
            xe(
                "Band sensitivity: add second GPU region or HA → multiply inference row. Replace mids with your quotes."
            ),
            small,
        )
    )

    elements.append(PageBreak())
    section_heading(elements, "Optional add-ons", h2)
    for line in [
        "Staging GPU for load tests (fraction of prod hourly × hours used).",
        "Cross-region inference for data residency (second monthly GPU bill).",
        "Premium support contract from GPU host or MSP retainer (not itemized).",
    ]:
        elements.append(Paragraph(xe(f"• {line}"), body))

    elements.append(
        Paragraph(
            xe(
                "Disclaimer: figures are planning aids only. Bind budgets to GPU quotes, Neon tier, and BSP invoices."
            ),
            note_box,
        )
    )

    doc.build(elements)


def build_llm_pdf(styles_pack) -> None:
    _, _, _, h2, body, small, tbl_cell, tbl_head, note_box = styles_pack
    doc = SimpleDocTemplate(
        OUT_LLM,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="LLM API multi-tenant cost playbook",
    )
    elements: list = []

    navy_header(
        elements,
        "ERP AI Support Agent",
        "LLM API — multi-tenant cost playbook (5–6 clients · 5k–10k conv/client · mo)",
        styles_pack,
    )

    section_heading(elements, "Assumptions", h2)
    elements.append(
        Paragraph(
            xe(
                "Same tenant and volume scenarios as GPU playbook. Inference billed per token to vendor. "
                "Average prompt tokens (user + system + RAG + ERP JSON) and output tokens drive monthly LLM line."
            ),
            body,
        )
    )

    section_heading(elements, "Token model", h2)
    tin, tout = 2000, 150
    elements.append(
        Paragraph(
            xe(
                f"Illustrative averages for ERP + restaurant + RAG: T_in = {tin} tokens/conv, T_out = {tout} tokens/conv. "
                "Your guardrails cap max_output_tokens in app — tune after log sampling."
            ),
            body,
        )
    )

    section_heading(elements, "LLM API pricing tiers (illustrative $/1M tokens)", h2)
    tier_rows = [
        ["Tier", "Input $/1M", "Output $/1M", "Notes"],
        ["Economical routing", "$0.10", "$0.40", "Cheap chat-class stack — verify vendor list price"],
        ["Mid-tier hosted", "$0.40", "$1.60", "Quality/latency balance"],
        ["Premium frontier-class", "$2.00", "$8.00", "Illustrative upper band — replace with quote"],
    ]
    elements.append(wrap_table(tier_rows, [38 * mm, 30 * mm, 30 * mm, 72 * mm], tbl_head, tbl_cell, BLUE, BG))

    tiers = [
        ("Economical", 0.10, 0.40),
        ("Mid-tier", 0.40, 1.60),
        ("Premium", 2.00, 8.00),
    ]

    section_heading(elements, "LLM inference cost by aggregate volume", h2)
    convs = [25000, 30000, 50000, 60000]
    for name, pin, pout in tiers:
        rows = [["Aggregate conv/mo", "Est. LLM USD/mo"]]
        for c in convs:
            m = llm_monthly_cost(c, tin, tout, pin, pout)
            rows.append([f"{c:,}", f"${m:,.2f}"])
        elements.append(Paragraph(xe(f"{name} (T_in={tin}, T_out={tout})"), body))
        elements.append(wrap_table(rows, [78 * mm, 92 * mm], tbl_head, tbl_cell, NAVY, colors.white))
        elements.append(Spacer(1, 8))

    section_heading(elements, "Platform & miscellaneous costs (itemized)", h2)
    elements.append(platform_misc_table(tbl_head, tbl_cell))
    elements.append(Spacer(1, 10))

    section_heading(elements, "Grand totals — LLM API path (mid tier + platform mid)", h2)
    plat_mid = 425.0
    pin, pout = 0.40, 1.60

    llm_mid_25k = llm_monthly_cost(25000, tin, tout, pin, pout)

    combined_rows = [
        ["Aggregate conv/mo", "LLM (mid tier est.)", "Platform (mid)", "Grand total (mid)", "Fully-loaded $/conv", "LLM-only $/conv"],
    ]
    for c in convs:
        llm_c = llm_monthly_cost(c, tin, tout, pin, pout)
        tot = llm_c + plat_mid
        combined_rows.append(
            [
                f"{c:,}",
                f"${llm_c:,.2f}",
                f"${plat_mid:,.0f}",
                f"${tot:,.2f}",
                f"${tot / c:.4f}",
                f"${llm_c / c:.4f}",
            ]
        )
    elements.append(wrap_table(combined_rows, [30 * mm, 34 * mm, 28 * mm, 30 * mm, 26 * mm, 26 * mm], tbl_head, tbl_cell, BLUE, BG))
    elements.append(
        Paragraph(
            xe(
                f"Example mid-tier LLM @ 25k conv: ~${llm_mid_25k:,.2f}/mo inference + ~${plat_mid:,.0f} platform. "
                "Swap tier rows using tables above."
            ),
            small,
        )
    )

    section_heading(elements, "Embeddings / vector RAG", h2)
    elements.append(
        Paragraph(
            xe(
                "Current codebase: Postgres FTS on kb_articles — $0 incremental vs generic DB cost. "
                "Optional future: embedding API + pgvector → add per-token embedding line item."
            ),
            body,
        )
    )

    elements.append(
        Paragraph(
            xe("Disclaimer: Replace illustrative rates with your provider price sheet before signing."),
            note_box,
        )
    )

    doc.build(elements)


def main() -> None:
    styles_pack = build_styles()
    build_gpu_pdf(styles_pack)
    build_llm_pdf(styles_pack)
    print(f"PDF generated: {OUT_GPU}")
    print(f"PDF generated: {OUT_LLM}")


if __name__ == "__main__":
    main()
