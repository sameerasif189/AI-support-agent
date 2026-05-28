"""
Two client decks: Automated Learning Agent architecture — LLM API vs Private GPU inference paths.

Outputs:
  Client_Learning_Agent_Strategy_LLM_API.pdf
  Client_Learning_Agent_Strategy_Private_GPU.pdf

Run: python generate_client_learning_agent_decks_pdf.py
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE = r"c:\Users\PC\AI Support agent"
OUT_LLM = BASE + r"\Client_Learning_Agent_Strategy_LLM_API.pdf"
OUT_GPU = BASE + r"\Client_Learning_Agent_Strategy_Private_GPU.pdf"

NAVY = colors.HexColor("#1E293B")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#334155")
BG = colors.HexColor("#F8FAFC")
GRID = colors.HexColor("#CBD5E1")
TOTAL_BG = colors.HexColor("#DBEAFE")
FULL_WIDTH = 170 * mm


def xe(t: str) -> str:
    return escape(t, entities={"\"": "&quot;", "'": "&apos;"})


def build_styles():
    st = getSampleStyleSheet()
    title = ParagraphStyle(
        "la_title",
        parent=st["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.white,
    )
    deck_line = ParagraphStyle(
        "la_deck",
        parent=st["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.white,
    )
    hint = ParagraphStyle(
        "la_hint",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=colors.white,
    )
    h2 = ParagraphStyle(
        "la_h2",
        parent=st["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=8,
    )
    body = ParagraphStyle(
        "la_body",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=NAVY,
        spaceAfter=6,
    )
    small = ParagraphStyle(
        "la_small",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=SLATE,
        spaceAfter=6,
    )
    tc = ParagraphStyle(
        "la_tc",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11.5,
        textColor=NAVY,
    )
    th = ParagraphStyle("la_th", parent=tc, fontName="Helvetica-Bold", textColor=colors.white)
    box = ParagraphStyle(
        "la_box",
        parent=body,
        backColor=TOTAL_BG,
        borderPadding=10,
        spaceBefore=6,
        spaceAfter=10,
    )
    return title, deck_line, hint, h2, body, small, tc, th, box


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
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(xe(text), h2_style))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=BLUE, spaceBefore=2, spaceAfter=10))


def doc_header(elements, deck_title: str, inference_tagline: str, sty):
    title, deck_line, hint, *_ = sty
    inner = Table(
        [[Paragraph(xe("ERP AI Support Agent"), title)], [Paragraph(xe(deck_title), deck_line)]],
        colWidths=[FULL_WIDTH],
    )
    hdr = Table(
        [
            [inner],
            [Paragraph(xe(inference_tagline), hint)],
            [Paragraph(xe("Client strategy deck · Planning material · Final integration subject to client IT review."), hint)],
        ],
        colWidths=[FULL_WIDTH],
    )
    hdr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(hdr)
    elements.append(Spacer(1, 12))


def append_what_we_sell(elements, h2, body, small, tc, th, box, inference_mode: str):
    """Opening commercial clarity — what the client is purchasing."""
    section_heading(elements, "What we are selling (commercial offering)", h2)

    if inference_mode == "llm_api":
        inf_row = [
            "Inference — Hosted LLM API",
            "Customer replies generated via vendor chat-completions API (OpenAI-compatible); you choose model tier.",
            "Fastest deployment; elastic concurrency; pay per token (plus platform fees).",
        ]
        deck_note = (
            "This document describes the same product as the Private GPU deck — only the inference deployment changes."
        )
    else:
        inf_row = [
            "Inference — Private GPU",
            "Models run on dedicated/rented GPU VM (e.g. Ollama/vLLM); prompts stay inside agreed network boundary.",
            "Sovereignty story; predictable GPU monthly rent; ops ownership of inference stack.",
        ]
        deck_note = (
            "This document describes the same product as the LLM API deck — only the inference deployment changes."
        )

    offering = [
        ["SKU / layer", "What is included", "What the buyer gains"],
        [
            "Core Assistant",
            "Orchestration (FastAPI): web / WhatsApp / Slack hooks; intent + guardrails; live ERP context from Postgres; "
            "KB retrieval (RAG over kb_articles); answer cache; human handoff + ticketing.",
            "Production-grade ERP/restaurant support automation with grounded answers and escalation.",
        ],
        [
            "Learning Automation Module (add-on)",
            "Pipeline: capture resolved chats → extract KB candidates → PII scrub → ERP truth gate → contradiction check → "
            "auto-publish to searchable KB + audit trail + rollback hooks.",
            "KB stays fresh without manual FAQ copying; learning is governed — not raw-chat weight updates.",
        ],
        inf_row,
    ]
    elements.append(wrap_table(offering, [36 * mm, 62 * mm, 72 * mm], th, tc, NAVY, BG))
    elements.append(Paragraph(xe(deck_note), small))
    elements.append(
        Paragraph(
            xe(
                "<b>Not sold as:</b> unsupervised \"the model rewrote itself from chats\" for factual ERP answers. "
                "<b>Optional future SKU:</b> scheduled LoRA/fine-tune after KB+RAG plateaus — explicit scope + dataset governance."
            ),
            box,
        )
    )
    elements.append(Spacer(1, 8))


def append_shared_learning_sections(elements, h2, body, small, tc, th, box):
    section_heading(elements, "Product narrative — Automated Learning Support Agent", h2)
    elements.append(
        Paragraph(
            xe(
                "Clients receive a support assistant that improves continuously without manual copy-paste into PDFs. "
                "Learning means the underlying Knowledge Base (KB) ingested into Retrieval-Augmented Generation (RAG) "
                "updates automatically after validated signals — not silent neural-weight drift from raw chat."
            ),
            body,
        )
    )
    elements.append(
        Paragraph(
            xe(
                "<b>LLMs remain central:</b> one model (or tiered models) generates customer-facing replies; optionally a "
                "secondary model drafts KB candidates from transcripts. <b>Truth gates</b> decide what becomes searchable KB."
            ),
            body,
        )
    )

    section_heading(elements, "Automated learning pipeline (same for both inference paths)", h2)
    pipe = [
        ["Stage", "Description"],
        ["Capture", "Closed chats, resolved tickets, optional thumbs-down queues → structured logs per tenant."],
        ["Extract", "Candidate FAQs/snippets via templating + optional summarization model (runs inside client VPC)."],
        ["PII scrub", "Redact or reject payloads failing compliance regex / classifier thresholds."],
        ["ERP truth gate", "Statements about orders/invoices/customers must match live ERP/API snapshot or be rejected."],
        ["Contradiction check", "Compare candidates vs existing KB + canonical ERP-derived facts; block merges on conflict."],
        ["Publish", "Approved rows commit to Postgres KB (tenant-scoped); search index updates for RAG."],
        ["Serve", "Next conversations retrieve fresher KB alongside ERP tool context in the prompt."],
    ]
    elements.append(wrap_table(pipe, [28 * mm, 142 * mm], th, tc, BLUE, BG))

    section_heading(elements, "Hard gates — why this is safe to sell as enterprise support", h2)
    gates = [
        ["Gate", "Purpose"],
        ["ERP oracle", "Prevents learning fabricated order or billing facts from chat fiction."],
        ["Contradiction policy", "Prevents two conflicting policies ranking highly in RAG."],
        ["Tenant isolation", "Restaurant vs ERP SaaS clients never bleed KB rows unless linked by contract."],
        ["Audit trail", "Every auto-published article carries provenance (ticket id, rule version, timestamp)."],
    ]
    elements.append(wrap_table(gates, [32 * mm, 138 * mm], th, tc, NAVY, colors.white))

    elements.append(
        Paragraph(
            xe(
                "<b>Explicit non-goal:</b> unsupervised fine-tuning directly from raw chats for factual ERP answers — "
                "high hallucination risk. Optional quarterly LoRA may exist as a separate SKU after KB+RAG plateaus."
            ),
            box,
        )
    )

    section_heading(elements, "SKU alignment", h2)
    elements.append(
        Paragraph(
            xe(
                "Commercial SKUs match the opening table: Core Assistant + optional Learning Automation Module + inference tier "
                "chosen per procurement (this deck vs companion deck)."
            ),
            body,
        )
    )


def build_llm_pdf(pack):
    title, deck_line, hint, h2, body, small, tc, th, box = pack
    doc = SimpleDocTemplate(
        OUT_LLM,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Learning Agent Strategy LLM API",
    )
    elements = []

    doc_header(
        elements,
        "Automated Learning Agent — Hosted LLM Inference Path",
        "Inference: vendor-hosted chat completions · Learning: gated KB/RAG on your Postgres",
        pack,
    )

    append_what_we_sell(elements, h2, body, small, tc, th, box, "llm_api")

    append_shared_learning_sections(elements, h2, body, small, tc, th, box)

    section_heading(elements, "Where inference runs vs where learning runs", h2)
    elements.append(
        Paragraph(
            xe(
                "<b>Inside client VPC / your orchestration region:</b> FastAPI, ERP connectors, Postgres, transcript capture, "
                "learning workers (extract → gates → KB commit). <b>Vendor boundary:</b> chat completion requests carrying "
                "assembled prompts (subject to your DPA and data-minimization choices)."
            ),
            body,
        )
    )

    section_heading(elements, "Strengths to emphasize when selling", h2)
    for b in [
        "Fastest route to production — no GPU fleet to operate.",
        "Elastic concurrency — vendor absorbs burst traffic.",
        "Easy model upgrades — swap API model id when vendor ships improvements.",
        "Learning module ROI story — fewer KB maintenance hours; fresher answers without content team bottlenecks.",
        "Shared evaluation harness — golden prompts you approve become the baseline private GPU must match if you switch paths.",
    ]:
        elements.append(Paragraph(xe(f"• {b}"), body))

    section_heading(elements, "Buyer objections — prepare answers", h2)
    obj = [
        ["Topic", "Response angle"],
        ["Data residency", "Enterprise VPC / regional endpoints + retention configs per vendor DPA."],
        ["Variable spend", "Caps, caching, routing tiers; separate Learning SKU fixed fee optional."],
        ["Hallucination fear", "ERP gates + contradiction checks + human-handoff unchanged from core product."],
    ]
    elements.append(wrap_table(obj, [34 * mm, 136 * mm], th, tc, NAVY, colors.white))

    elements.append(PageBreak())
    section_heading(elements, "Recommended sales motion — LLM API path", h2)
    elements.append(
        Paragraph(
            xe(
                "<b>Lead SKU:</b> Core Assistant + Learning Automation Module on <b>hosted LLM API</b> for SMB through mid-market "
                "logos prioritizing speed and low ops. Position GPU sovereign tier only when procurement demands no third-party inference."
            ),
            box,
        )
    )

    doc.build(elements)


def build_gpu_pdf(pack):
    title, deck_line, hint, h2, body, small, tc, th, box = pack
    doc = SimpleDocTemplate(
        OUT_GPU,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Learning Agent Strategy Private GPU",
    )
    elements = []

    doc_header(
        elements,
        "Automated Learning Agent — Private GPU Inference Path",
        "Inference: rented or dedicated GPU with OpenAI-compatible serving · Learning: identical gated KB/RAG pipeline",
        pack,
    )

    append_what_we_sell(elements, h2, body, small, tc, th, box, "gpu")

    append_shared_learning_sections(elements, h2, body, small, tc, th, box)

    section_heading(elements, "Where inference runs vs where learning runs", h2)
    elements.append(
        Paragraph(
            xe(
                "<b>Inside controlled perimeter:</b> GPU hosts weight inference (Ollama/vLLM-class); orchestration + Postgres "
                "remain on CPU tier. <b>Learning pipeline stays CPU + DB:</b> same extract → gate → KB publish loop — GPU only "
                "needed again if you add offline embedding or LoRA training jobs."
            ),
            body,
        )
    )

    section_heading(elements, "Strengths to emphasize when selling", h2)
    for b in [
        "Data sovereignty narrative — chat payloads stay inside contracted networks when architected correctly.",
        "Predictable monthly inference envelope once SKU sized — aligns with CFO capex/opex preferences.",
        "Premium positioning — ideal for regulated verticals, franchise HQ IT, government-adjacent ERP.",
        "Same Learning SKU attach — differentiation is governance + infra story, not different automation logic.",
        "Benchmark parity — GPU model and VRAM chosen so golden-set scores track the hosted reference tier you approve.",
    ]:
        elements.append(Paragraph(xe(f"• {b}"), body))

    section_heading(elements, "Operational truths buyers must accept", h2)
    ops = [
        ["Consideration", "Plain explanation"],
        ["Capacity planning", "Peak concurrent chats determine VRAM — not monthly conv count alone."],
        ["Model standardization", "Multi-tenant GPU economics favor one primary instruct model per cluster."],
        ["Always-on cost", "Even idle periods incur GPU rent unless aggressive scale-to-zero (adds cold-start risk)."],
    ]
    elements.append(wrap_table(ops, [38 * mm, 132 * mm], th, tc, NAVY, colors.white))

    elements.append(PageBreak())
    section_heading(elements, "Recommended sales motion — Private GPU path", h2)
    elements.append(
        Paragraph(
            xe(
                "<b>Upsell / niche hero SKU:</b> Market private GPU stack when procurement demands zero vendor inference or "
                "when aggregate token economics justify dedicated capacity. Bundle Learning Automation Module as compliance-grade "
                "continuous KB improvement — proof points: ERP oracle gates + audit trail."
            ),
            box,
        )
    )

    doc.build(elements)


def main():
    pack = build_styles()
    build_llm_pdf(pack)
    build_gpu_pdf(pack)
    print(f"PDF generated: {OUT_LLM}")
    print(f"PDF generated: {OUT_GPU}")


if __name__ == "__main__":
    main()
