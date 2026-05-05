from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


OUTPUT_PATH = r"c:\Users\PC\AI Support agent\ERP_AI_Support_Agent_Lean_Plan_50_to_100.pdf"


def build_pdf() -> None:
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title="ERP AI Support Agent Lean Plan",
        author="AI Support Agent",
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#1E293B")
    blue = colors.HexColor("#2563EB")
    slate = colors.HexColor("#334155")
    bg = colors.HexColor("#F8FAFC")

    title = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.white,
        spaceAfter=4,
    )
    sub = ParagraphStyle(
        "sub",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.white,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=blue,
        spaceBefore=8,
        spaceAfter=5,
    )
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.2,
        leading=14.5,
        textColor=navy,
    )
    small = ParagraphStyle(
        "small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=slate,
    )

    elements = []

    header = Table(
        [[
            Paragraph("ERP AI Support Agent<br/>Lean Deployment Plan (Client Ready)", title),
            Paragraph(
                "Budget target: $50-$100/month | Channels included: Web + WhatsApp + Slack | "
                "Region: Pakistan",
                sub,
            ),
        ]],
        colWidths=[170 * mm],
        rowHeights=[33 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), navy),
                ("BOX", (0, 0), (-1, -1), 0, navy),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(header)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("1) Positioning for Clients", h2))
    elements.append(
        Paragraph(
            "<b>Project Title:</b> AI Customer Support Agent for ERP-enabled SaaS "
            "(Automates 60-75% repetitive support queries).",
            body,
        )
    )
    elements.append(
        Paragraph(
            "<b>Problem:</b> ERP support teams lose time on repetitive questions (order status, invoices, account updates). "
            "This increases response time and support cost.",
            body,
        )
    )
    elements.append(
        Paragraph(
            "<b>Solution:</b> A business-ready AI support system using low-cost LLM inference, retrieval from your knowledge base, "
            "and secure ERP API integration with human handoff.",
            body,
        )
    )

    elements.append(Paragraph("2) Cheapest Practical Architecture", h2))
    arch_rows = [
        ["Layer", "Lean Choice"],
        ["UI", "Website chat + WhatsApp + Slack (all available)"],
        ["Backend", ".NET API on your existing i7 server"],
        ["Retrieval", "PostgreSQL + pgvector on same server"],
        ["LLM", "Single low-cost external API model"],
        ["Memory", "Session table in Postgres (no Redis initially)"],
        ["Handoff", "Create ticket + notify human agent"],
    ]
    arch_tbl = Table(arch_rows, colWidths=[45 * mm, 125 * mm])
    arch_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 1), (-1, -1), bg),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(arch_tbl)
    elements.append(Spacer(1, 6))
    elements.append(
        Paragraph(
            "This setup avoids cloud GPU costs while keeping response quality acceptable for ERP support.",
            small,
        )
    )

    elements.append(Paragraph("3) Exact Lean Cost Plan (5,000 Conversations/Month)", h2))
    cost_rows = [
        ["Category", "Line Item", "Monthly Cost (USD)"],
        ["LLM", "Low-cost model usage (tight token limits)", "$38"],
        ["Database", "Postgres + pgvector (self-hosted)", "$0"],
        ["Storage/Backups", "Nightly backup + object storage", "$8"],
        ["Monitoring", "Basic uptime + error logging", "$4"],
        ["Channels", "WhatsApp provider + low-volume messaging", "$28"],
        ["Channels", "Slack bot/webhook operations", "$5"],
        ["Infra Overhead", "Networking/misc ops reserve", "$9"],
        ["TOTAL", "Exact monthly total (all 3 channels active)", "$92"],
    ]
    cost_tbl = Table(cost_rows, colWidths=[36 * mm, 95 * mm, 39 * mm])
    cost_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("BACKGROUND", (0, 1), (-1, -2), colors.white),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(cost_tbl)
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<b>Cost per conversation:</b> $92 / 5,000 = $0.018", body))
    elements.append(
        Paragraph(
            "Assumption: average ~1,500 input tokens and ~250 output tokens with strict prompt control, top-3 retrieval, and response cap.",
            small,
        )
    )

    elements.append(PageBreak())
    elements.append(Paragraph("4) Cost Control Rules (Required to Stay Below $100 with 3 Channels)", h2))
    controls = [
        "Limit max output tokens per answer (e.g., 120-180).",
        "Use retrieval top-k = 3 (avoid long context packing).",
        "Use one low-cost model only in Phase 1.",
        "Add answer cache for repetitive FAQs.",
        "If confidence is low, handoff to ticket instead of multi-turn loops.",
        "Set monthly hard cap with alert at 70% usage.",
        "Enforce WhatsApp template minimization and short response policy.",
    ]
    for c in controls:
        elements.append(Paragraph(f"• {c}", body))

    elements.append(Paragraph("5) Implementation Plan (4 Weeks)", h2))
    plan_rows = [
        ["Week", "Deliverables", "Success Check"],
        ["Week 1", "Intent mapping + ERP API wrappers + KB cleanup", "Top 20 intents mapped"],
        ["Week 2", "RAG ingestion + prompt template + web chat widget", "Accurate answers on test set"],
        ["Week 3", "Handoff flow + WhatsApp + Slack integration + logging", "All channels pass UAT"],
        ["Week 4", "UAT, tuning, go-live", "Cost/day within target range"],
    ]
    plan_tbl = Table(plan_rows, colWidths=[22 * mm, 92 * mm, 56 * mm])
    plan_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9.2),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(plan_tbl)

    elements.append(Paragraph("6) Upgrade Path (After Traction)", h2))
    elements.append(
        Paragraph(
            "Phase 2: Add premium fallback model only for complex cases once ROI is validated.<br/>"
            "Phase 3: Add richer channel automation (broadcasts, advanced workflows) as budget grows.",
            body,
        )
    )
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            "<b>Final Recommendation:</b> Run all three channels from day one with strict token and messaging limits. "
            "This keeps estimated monthly spend near $92 while maintaining decent support performance.",
            body,
        )
    )

    doc.build(elements)


if __name__ == "__main__":
    build_pdf()
    print(f"PDF generated: {OUTPUT_PATH}")
