from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


OUTPUT_PATH = r"c:\Users\PC\AI Support agent\ERP_AI_Support_Agent_Client_Ready_Proposal_5k_BRANDED.pdf"


def money(v: float) -> str:
    return f"${v:,.0f}"


def build_pdf() -> None:
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="ERP AI Support Agent Proposal",
        author="AI Support Agent",
    )

    styles = getSampleStyleSheet()
    brand_blue = colors.HexColor("#1E3A8A")
    brand_cyan = colors.HexColor("#0EA5E9")
    dark_text = colors.HexColor("#0F172A")
    muted_text = colors.HexColor("#334155")
    light_bg = colors.HexColor("#F8FAFC")

    title_style = ParagraphStyle(
        "TitleBrand",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.white,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleBrand",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.white,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=brand_blue,
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=dark_text,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=muted_text,
    )

    elements = []

    # Cover header card
    header_data = [[
        Paragraph("ERP AI Support Agent<br/>Client-Ready Proposal", title_style),
        Paragraph(
            "Scope: 5,000 conversations/month | Region: Pakistan delivery context | "
            "Pricing Basis: Azure OpenAI + Full Stack",
            subtitle_style,
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[170 * mm], rowHeights=[36 * mm])
    header_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), brand_blue),
                ("INNERGRID", (0, 0), (-1, -1), 0, brand_blue),
                ("BOX", (0, 0), (-1, -1), 0, brand_blue),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(header_tbl)
    elements.append(Spacer(1, 10))

    kpi_data = [
        ["Auto-Resolution Target", "60-80%"],
        ["Median Response Target", "< 3 seconds"],
        ["Exact Monthly Cost (5k)", "$265"],
        ["Cost Per Conversation", "$0.053"],
    ]
    kpi_tbl = Table(kpi_data, colWidths=[85 * mm, 85 * mm])
    kpi_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("TEXTCOLOR", (0, 0), (-1, -1), dark_text),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(kpi_tbl)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Business Positioning", h2))
    elements.append(
        Paragraph(
            "<b>Project Title:</b> AI Customer Support Agent for ERP-enabled SaaS "
            "(Automates 60-80% repetitive queries).",
            body,
        )
    )
    elements.append(
        Paragraph(
            "<b>Problem:</b> Repetitive ERP support tickets increase response times, "
            "agent workload, and operational cost.",
            body,
        )
    )
    elements.append(
        Paragraph(
            "<b>Solution:</b> A production-ready AI support system combining LLM "
            "inference, retrieval-augmented generation, ERP tool-calling, and human handoff.",
            body,
        )
    )
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Hardware-Aware Deployment Plan", h2))
    elements.append(
        Paragraph(
            "<b>Production (i7 12th Gen, 32GB RAM):</b> host .NET API, orchestration, "
            "auth, ERP connectors, logs, and RAG services.",
            body,
        )
    )
    elements.append(
        Paragraph(
            "<b>Development (5600X, 32GB RAM, RTX 5060 Ti 16GB):</b> local model tests, "
            "prompt tuning, evaluation, and fallback experiments.",
            body,
        )
    )
    elements.append(
        Paragraph(
            "<b>Inference policy:</b> 85% low-cost model and 15% premium fallback for "
            "complex queries to balance quality and cost.",
            body,
        )
    )
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Exact Cost Breakdown (5,000 Conversations/Month)", h2))

    infra = [35, 25, 20, 15, 10]
    llm = [42, 78]
    channels = [0, 32, 8]
    infra_total = sum(infra)
    llm_total = sum(llm)
    channels_total = sum(channels)
    grand_total = infra_total + llm_total + channels_total
    per_convo = grand_total / 5000

    cost_rows = [
        ["Category", "Line Item", "Monthly Cost (USD)"],
        ["Infrastructure", "App hosting (API + workers)", money(infra[0])],
        ["Infrastructure", "Managed Postgres", money(infra[1])],
        ["Infrastructure", "Vector retrieval storage/index", money(infra[2])],
        ["Infrastructure", "Monitoring/logging/alerts", money(infra[3])],
        ["Infrastructure", "Backup/object storage", money(infra[4])],
        ["LLM", "Low-cost model traffic (85%)", money(llm[0])],
        ["LLM", "Premium fallback traffic (15%)", money(llm[1])],
        ["Channels", "Website chat", money(channels[0])],
        ["Channels", "WhatsApp messaging + provider", money(channels[1])],
        ["Channels", "Slack app operations", money(channels[2])],
        ["TOTAL", "Exact monthly total", money(grand_total)],
    ]
    cost_tbl = Table(cost_rows, colWidths=[35 * mm, 95 * mm, 40 * mm])
    cost_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -2), 9.5),
                ("BACKGROUND", (0, 1), (-1, -2), colors.white),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E0F2FE")),
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
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            f"<b>Cost per conversation:</b> {money(grand_total)} / 5,000 = ${per_convo:.3f}",
            body,
        )
    )
    elements.append(
        Paragraph(
            "Assumption: ~2,000 input + 600 output tokens per conversation with RAG and tool routing.",
            small,
        )
    )

    elements.append(PageBreak())
    elements.append(Paragraph("Implementation Roadmap (4 Weeks)", h2))
    roadmap_rows = [
        ["Week", "Deliverables"],
        ["Week 1", "Intent mapping, ERP API wrappers, knowledge ingestion"],
        ["Week 2", "RAG pipeline, routing policy, web chat integration"],
        ["Week 3", "WhatsApp + Slack channels, handoff workflow, observability"],
        ["Week 4", "UAT, security hardening, go-live checklist, demo handoff"],
    ]
    roadmap_tbl = Table(roadmap_rows, colWidths=[28 * mm, 142 * mm])
    roadmap_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), brand_cyan),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BAE6FD")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(roadmap_tbl)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Risk Controls and Governance", h2))
    bullets = [
        "Role-based access and audit logs for all ERP actions.",
        "Confidence thresholds before transactional actions.",
        "Prompt-injection filtering and retrieval source controls.",
        "Human escalation path for low-confidence or sensitive requests.",
        "Cost monitor with monthly threshold alerts and fallback policy.",
    ]
    for bullet in bullets:
        elements.append(Paragraph(f"• {bullet}", body))

    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            "<b>Final Recommendation:</b> For your current scale, external LLM inference with "
            "RAG on your CPU production server is the most practical and cost-efficient path.",
            body,
        )
    )

    doc.build(elements)


if __name__ == "__main__":
    build_pdf()
    print(f"PDF generated: {OUTPUT_PATH}")
