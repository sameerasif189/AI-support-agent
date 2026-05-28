"""
Single client-facing proposal PDF: strategy (LLM API + Private GPU) + full cost framework.

Includes a current-scope minimum scenario (five clients, five thousand aggregate conversations
per month, Postgres on client infrastructure, no WhatsApp, Slack, or separate storage line items).

Plain prose only (no HTML markup in Paragraph text). Cost columns highlighted in tables.

Output:
  Client_ERP_AI_Support_Unified_Proposal.pdf

Run: python generate_client_unified_proposal_pdf.py
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from generate_multi_tenant_cost_playbooks_pdf import gpu_monthly_from_hourly, llm_monthly_cost

BASE = r"c:\Users\PC\AI Support agent"
OUTPUT_PATH = BASE + r"\Client_ERP_AI_Support_Unified_Proposal.pdf"

NAVY = colors.HexColor("#1E293B")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#334155")
BG = colors.HexColor("#F8FAFC")
GRID = colors.HexColor("#CBD5E1")
HIGHLIGHT = colors.HexColor("#FEF3C7")
NOTE_BG = colors.HexColor("#E0F2FE")
FULL_WIDTH = 170 * mm

# Current-scope minimum scenario (Cost framework — detailed tables follow)
MIN_SCENARIO_CLIENTS = 5
MIN_SCENARIO_CONV_PER_MONTH = 5000
MIN_SCENARIO_TOKENS_IN = 2000
MIN_SCENARIO_TOKENS_OUT = 150
MIN_PLAT_VPS = 52
MIN_PLAT_OBSERVABILITY = 15
MIN_PLAT_DOMAIN_TLS = 8
MIN_PLAT_TOTAL = MIN_PLAT_VPS + MIN_PLAT_OBSERVABILITY + MIN_PLAT_DOMAIN_TLS
# Mid-tier hosted LLM illustrative rates ($/1M tokens) — quality/latency balance (reference tier)
MIN_LLM_PIN_PER_M = 0.40
MIN_LLM_POUT_PER_M = 1.60
# GPU hourly band used when sizing local inference for parity with that hosted tier (~24 GB VRAM class in playbook)
MIN_GPU_PARITY_HR_LOW = 0.45
MIN_GPU_PARITY_HR_HIGH = 0.95


def xe(text: str) -> str:
    return escape(text, entities={"\"": "&quot;", "'": "&apos;"})


def footer_canvas(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 8.5)
    w, _h = doc.pagesize
    canvas.drawString(20 * mm, 12 * mm, "Confidential — planning estimates only. Not a binding quote.")
    canvas.drawRightString(w - 20 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_styles():
    st = getSampleStyleSheet()
    doc_title = ParagraphStyle(
        "up_doc_title",
        parent=st["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.white,
    )
    doc_sub = ParagraphStyle(
        "up_doc_sub",
        parent=st["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.white,
    )
    doc_meta = ParagraphStyle(
        "up_doc_meta",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#E2E8F0"),
    )
    h1 = ParagraphStyle(
        "up_h1",
        parent=st["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=NAVY,
        spaceBefore=6,
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "up_h2",
        parent=st["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=8,
    )
    body = ParagraphStyle(
        "up_body",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=NAVY,
        spaceAfter=8,
    )
    lead = ParagraphStyle(
        "up_lead",
        parent=body,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "up_small",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=SLATE,
        spaceAfter=6,
    )
    tc = ParagraphStyle(
        "up_tc",
        parent=st["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11.5,
        textColor=NAVY,
    )
    th = ParagraphStyle("up_th", parent=tc, fontName="Helvetica-Bold", textColor=colors.white)
    tc_money = ParagraphStyle(
        "up_tc_money",
        parent=tc,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#92400E"),
    )
    note = ParagraphStyle(
        "up_note",
        parent=body,
        backColor=NOTE_BG,
        borderPadding=10,
        spaceBefore=6,
        spaceAfter=10,
    )
    return doc_title, doc_sub, doc_meta, h1, h2, body, lead, small, tc, th, tc_money, note


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


def wrap_cost_table(
    data_rows,
    col_widths,
    tbl_head,
    tbl_cell,
    tbl_cell_money,
    header_bg,
    money_cols: list[int],
    body_bg=colors.white,
    highlight_money: bool = True,
):
    """Same as wrap_table but highlights USD columns with amber tint on body rows."""
    wrapped = []
    for ri, row in enumerate(data_rows):
        line = []
        for ci, cell in enumerate(row):
            if ri == 0:
                sty = tbl_head
            else:
                is_money = ci in money_cols and highlight_money
                sty = tbl_cell_money if is_money else tbl_cell
            line.append(Paragraph(xe(str(cell)), sty))
        wrapped.append(line)
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for ri in range(1, len(data_rows)):
        ts.append(("BACKGROUND", (0, ri), (-1, ri), body_bg))
        for ci in money_cols:
            ts.append(("BACKGROUND", (ci, ri), (ci, ri), HIGHLIGHT))
    t.setStyle(TableStyle(ts))
    return t


def section_rule(elements, title: str, h2):
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(xe(title), h2))
    elements.append(HRFlowable(width="100%", thickness=0.9, color=BLUE, spaceBefore=2, spaceAfter=10))


def platform_misc_cost_rows():
    """Same line items as multi-tenant playbook; dollar column highlighted in unified doc."""
    return [
        ["Line item", "Typical USD / month (band)", "Notes"],
        [
            "Application / orchestration host (FastAPI VPS)",
            "$28 – $120",
            "Single VM vs small HA pair; rises with traffic and tenants",
        ],
        ["PostgreSQL (Neon or managed)", "$15 – $95", "Storage, connections, HA tier"],
        ["Domain + DNS", "$0 – $24", "Registrar; amortize annual to monthly"],
        ["TLS certificates", "$0 – $18", "Often zero (ACME); managed certs extra"],
        ["CDN / edge / WAF (optional)", "$0 – $65", "Public widget and bot protection"],
        ["Observability (logs, metrics, uptime)", "$12 – $85", "Vendor tier and retention"],
        ["Error tracking (optional)", "$0 – $39", "Often free tier then paid"],
        ["Backups + object storage", "$6 – $35", "Database backups and log archives"],
        [
            "WhatsApp / BSP (aggregate for five–six clients)",
            "$75 – $520",
            "Largest swing — Meta and BSP pricing differs",
        ],
        ["Slack app / workspace ops", "$6 – $42", "Usually smaller than WhatsApp"],
        ["Email / transactional alerts", "$0 – $28", "Operations notifications"],
        ["Secrets manager + CI (optional)", "$0 – $45", "CI minutes and vault"],
        [
            "Subtotal — platform and channels (planning range)",
            "~$142 – $1,076",
            "Sum of band lows and highs above",
        ],
        [
            "Illustrative midpoint bundle for scenario math below",
            "~$425 / mo",
            "Mid estimate excluding extremes; replace with your quotes",
        ],
    ]


def minimal_scope_platform_rows():
    """Fixed stack before inference — matches MIN_PLAT_* constants."""
    return [
        ["Component", "USD / month", "Notes"],
        ["Orchestration VPS (single VM)", f"${MIN_PLAT_VPS}", "FastAPI, TLS termination, modest headroom"],
        ["Observability (logs, uptime, metrics)", f"${MIN_PLAT_OBSERVABILITY}", "Small paid tier or free-tier equivalent"],
        ["Domain and TLS", f"${MIN_PLAT_DOMAIN_TLS}", "Registrar amortized; ACME certificates where applicable"],
        ["PostgreSQL", "$0", "Runs on your server — no separate managed-database fee in this slice"],
        ["WhatsApp and Slack", "$0", "Excluded from this estimate"],
        ["Object storage / off-site backup bucket", "$0", "Excluded — assumes existing server backup policy"],
        ["Subtotal — agent platform (fixed)", f"${MIN_PLAT_TOTAL}", "Same baseline for both inference paths below"],
    ]


def cover_block(elements, styles):
    doc_title, doc_sub, doc_meta, *_ = styles
    inner = Table(
        [
            [Paragraph(xe("ERP AI Support Agent"), doc_title)],
            [Paragraph(xe("Unified client proposal"), doc_sub)],
        ],
        colWidths=[FULL_WIDTH],
    )
    hdr = Table(
        [
            [inner],
            [
                Paragraph(
                    xe(
                        "Automated learning assistant · Hosted LLM API and Private GPU inference paths · "
                        "Cost planning framework included"
                    ),
                    doc_meta,
                )
            ],
            [Paragraph(xe("Planning document — implementation scope subject to your IT and procurement review."), doc_meta)],
        ],
        colWidths=[FULL_WIDTH],
    )
    hdr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    elements.append(hdr)
    elements.append(Spacer(1, 14))


def build_document():
    styles = build_styles()
    _dt, _ds, _dm, h1, h2, body, lead, small, tc, th, tc_money, note = styles

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="ERP AI Support Agent — Unified Proposal",
    )
    elements: list = []

    cover_block(elements, styles)

    section_rule(elements, "Executive summary", h1)
    elements.append(
        Paragraph(
            xe(
                "This document combines product definition and indicative economics for an ERP-aware support assistant "
                "with governed learning. The same Core Assistant and Learning Automation Module apply whether inference "
                "runs on a vendor-hosted large language model API or on a private rented GPU inside your network boundary."
            ),
            body,
        )
    )
    elements.append(
        Paragraph(
            xe(
                "Customer-facing behavior is contractually aligned across deployments: same prompts, retrieval depth, guardrails, "
                "and evaluation harness. Private GPU is provisioned so blind-reviewed answers match the hosted reference tier "
                "you approve — not a permanently weaker local model unless you explicitly choose a savings SKU."
            ),
            body,
        )
    )
    elements.append(
        Paragraph(
            xe(
                "Hosted LLM API: fastest rollout, elastic capacity, spend scales with tokens. Private GPU: predictable "
                "monthly rent for inference, stronger data-boundary story, operational responsibility for the inference stack."
            ),
            body,
        )
    )
    elements.append(
        Paragraph(
            xe(
                "Learning does not mean silent weight updates from raw chat. Approved resolutions flow through extraction, "
                "PII controls, ERP validation, contradiction checks, and publication into a searchable knowledge base feeding RAG."
            ),
            body,
        )
    )
    elements.append(
        Paragraph(
            xe(
                "Minimum monthly economics for a slim footprint — five clients on one stack, five thousand aggregate answered "
                "conversations per month, database on your infrastructure, no WhatsApp or Slack, no separate cloud storage line — "
                "are summarized early under Cost framework (hosted LLM API about eighty USD including platform; private GPU about "
                "five hundred eighty-six USD using a twenty-four gigabyte-class GPU rent midpoint sized for parity with that hosted tier)."
            ),
            body,
        )
    )

    section_rule(elements, "Commercial offering", h1)
    offering = [
        ["Layer", "Delivered capability", "Business outcome"],
        [
            "Core Assistant",
            "Orchestration on FastAPI: web chat plus optional WhatsApp and Slack routes; intents and guardrails; "
            "live ERP context from Postgres; knowledge retrieval via full-text RAG on kb_articles; caching; "
            "human handoff and ticketing hooks.",
            "Fewer tier-one tickets answered consistently from grounded policy and order context.",
        ],
        [
            "Learning Automation Module",
            "Capture resolved conversations; propose KB updates; scrub PII; ERP truth gate; contradiction detection; "
            "publish to tenant-scoped KB with audit trail and rollback.",
            "Knowledge stays current without manual FAQ duplication; changes are traceable.",
        ],
        [
            "Inference — choice A: Hosted LLM API",
            "Customer-facing completions via OpenAI-compatible vendor API; model tier selectable.",
            "Low operational lift on inference; variable usage bill.",
        ],
        [
            "Inference — choice B: Private GPU",
            "Completions on dedicated or rented GPU VM with OpenAI-compatible serving (for example Ollama or vLLM). "
            "VRAM and model quantization are chosen so outputs track the same acceptance targets as the hosted reference tier.",
            "Prompts and outputs remain inside agreed perimeter when architected accordingly.",
        ],
    ]
    elements.append(wrap_table(offering, [34 * mm, 68 * mm, 68 * mm], th, tc, NAVY, BG))

    section_rule(elements, "Comparison of inference choices", h1)
    cmp_rows = [
        ["Topic", "Hosted LLM API", "Private GPU"],
        ["Time to production", "Typically shortest — no GPU fleet.", "GPU sizing, firewall rules, and image bake add weeks."],
        ["Spend shape", "Mostly variable per token; tiers differ.", "Mostly fixed monthly GPU rent at 24/7; marginal chat near zero."],
        ["Burst traffic", "Vendor scales concurrency.", "Your cluster or queue limits; may need second GPU or rate limits."],
        ["Answer quality / parity", "Defined by the vendor model tier you select.", "Same golden-set evaluation as hosted path; GPU/model sized to meet identical acceptance thresholds."],
        ["Model changes", "Swap model id when vendor ships updates.", "You control upgrades; restarts and VRAM checks apply."],
        ["Procurement story", "DPAs and regional endpoints from vendor.", "Cap-ex style envelope; sovereignty narrative."],
    ]
    elements.append(wrap_table(cmp_rows, [38 * mm, 66 * mm, 66 * mm], th, tc, BLUE, colors.white))

    section_rule(elements, "Performance parity — hosted and local inference", h1)
    elements.append(
        Paragraph(
            xe(
                "The product is intentionally symmetric: orchestration, RAG retrieval parameters, tool calls into ERP, "
                "max token budgets, and refusal policies stay one codebase path. Only the chat-completions endpoint "
                "changes — vendor URL versus local OpenAI-compatible URL."
            ),
            body,
        )
    )
    for line in [
        "Acceptance tests: the same frozen golden prompts (ERP edge cases, refunds, delivery promises) score against "
        "fixed rubrics on both deployments before production traffic moves.",
        "Reference model: document which hosted model tier is the baseline; local weights are chosen (family, parameter count, "
        "quantization) to reproduce that baseline within agreed latency.",
        "Regression cadence: rerun the harness after KB publishes, model upgrades, or prompt edits — whichever inference path you use.",
        "Concurrency: parity is defined at agreed simultaneous-session targets; undersized GPU breaks latency before quality if overloaded.",
    ]:
        elements.append(Paragraph(xe(f"• {line}"), body))

    section_rule(elements, "Governed learning pipeline", h1)
    elements.append(
        Paragraph(
            xe(
                "Stages are identical for both inference paths. GPUs are not required for this pipeline unless you later "
                "add offline embedding jobs or optional fine-tuning."
            ),
            body,
        )
    )
    pipe = [
        ["Stage", "Description"],
        ["Capture", "Closed chats and resolved tickets become structured logs per tenant."],
        ["Extract", "Templates plus optional summarization produce candidate FAQ snippets."],
        ["PII scrub", "Reject or redact payloads that fail policy thresholds."],
        ["ERP truth gate", "Statements about orders, invoices, and customers must match live ERP or API snapshot."],
        ["Contradiction check", "Compare candidates against existing KB and canonical facts."],
        ["Publish", "Approved rows land in Postgres; search index updates for retrieval."],
        ["Serve", "Later chats retrieve fresher articles alongside ERP tool context."],
    ]
    elements.append(wrap_table(pipe, [28 * mm, 142 * mm], th, tc, BLUE, BG))

    section_rule(elements, "Enterprise controls", h1)
    gates = [
        ["Control", "Purpose"],
        ["ERP oracle", "Stops fabricated billing or order facts from entering KB."],
        ["Contradiction policy", "Avoids two incompatible policies both ranking high in search."],
        ["Tenant isolation", "Restaurant and SaaS tenants remain logically separated."],
        ["Audit trail", "Each publication records provenance and timestamps."],
    ]
    elements.append(wrap_table(gates, [38 * mm, 132 * mm], th, tc, NAVY, colors.white))
    elements.append(
        Paragraph(
            xe(
                "Explicit boundary: unsupervised fine-tuning straight from raw chats for factual ERP answers is out of scope "
                "for initial delivery. Optional future work could include scheduled adapter training under separate scope."
            ),
            note,
        )
    )

    elements.append(PageBreak())

    section_rule(elements, "Hosted LLM API path — positioning", h1)
    for line in [
        "Vendor absorbs burst load and hardware churn.",
        "Regional endpoints and enterprise agreements address residency questions.",
        "Caching, routing tiers, and token budgets manage variable spend.",
    ]:
        elements.append(Paragraph(xe(f"• {line}"), body))

    section_rule(elements, "Hosted LLM API — common objections", h2)
    obj = [
        ["Topic", "Response angle"],
        ["Data residency", "Negotiate region, retention, and training opt-outs per vendor DPA."],
        ["Spend volatility", "Caps, tiered models, aggressive caching; separate fixed fee for Learning Module possible."],
        ["Hallucination risk", "ERP gates, contradiction checks, and handoff unchanged from core design."],
    ]
    elements.append(wrap_table(obj, [34 * mm, 136 * mm], th, tc, NAVY, colors.white))

    elements.append(PageBreak())

    section_rule(elements, "Private GPU path — positioning", h1)
    for line in [
        "Inference payloads stay inside contracted networks when architecture follows least-privilege rules.",
        "Monthly GPU envelope is predictable once SKU is locked for parity with your hosted reference tier.",
        "Strong fit when procurement prohibits third-party inference or prefers dedicated capacity.",
        "Quality track: benchmark local serving against the hosted acceptance harness — not a separate product behavior.",
    ]:
        elements.append(Paragraph(xe(f"• {line}"), body))

    section_rule(elements, "Private GPU — operational considerations", h2)
    ops = [
        ["Topic", "Explanation"],
        ["Capacity", "Peak concurrent chats and context length drive VRAM more than monthly totals alone."],
        ["Evaluation gate", "Promote GPU builds only when golden-set metrics match the hosted baseline within SLA."],
        ["Always-on cost", "Idle time still rents GPU unless you accept cold-start scale-to-zero."],
    ]
    elements.append(wrap_table(ops, [34 * mm, 136 * mm], th, tc, NAVY, colors.white))

    section_rule(elements, "Choosing an inference path — decision guide", h1)
    elements.append(
        Paragraph(
            xe(
                "Both paths ship the same assistant behavior and the same governed learning module. The decision is procurement, "
                "risk appetite for variable cloud inference spend, and internal appetite for GPU operations."
            ),
            body,
        )
    )
    dec = [
        ["Priority", "Hosted LLM API is a strong default when…", "Private GPU deserves consideration when…"],
        ["Speed to launch", "You want production in weeks without provisioning GPUs.", "Lead time for GPU quota and networking is acceptable."],
        ["Spend profile", "Usage-based token billing aligns with finance.", "Finance prefers a stable monthly inference line item."],
        ["Operational load", "You want the vendor to absorb scaling and hardware churn.", "You have engineers to patch images and monitor VRAM."],
        ["Traffic spikes", "Elastic vendor concurrency is attractive.", "You will rate-limit, queue, or add GPUs for peaks."],
        ["Third-party inference", "Regional endpoints and contracts satisfy legal.", "Policy forbids sending prompts outside your perimeter."],
    ]
    elements.append(wrap_table(dec, [32 * mm, 69 * mm, 69 * mm], th, tc, BLUE, BG))
    elements.append(
        Paragraph(
            xe(
                "Hybrid patterns exist: hosted API for pilots, migration to private GPU after sizing; or API fallback behind GPU failure. "
                "Hybrid economics should be modeled separately."
            ),
            note,
        )
    )

    elements.append(PageBreak())

    section_rule(elements, "Cost framework — how to read this section", h1)
    elements.append(
        Paragraph(
            xe(
                "All dollar figures are planning bands for internal budgeting. Highlighted cells draw attention to monetary "
                "columns. Replace every band with your invoices before contractual commitments."
            ),
            body,
        )
    )
    elements.append(
        Paragraph(
            xe(
                "The tables below first isolate your present footprint: five tenants, five thousand aggregate conversations monthly, "
                "Postgres on your servers, no WhatsApp or Slack, no budget line for object storage or off-site backup buckets. "
                "Wider planning bands follow for when channels, managed database, and backups enter scope."
            ),
            small,
        )
    )

    llm_inf_floor = llm_monthly_cost(
        MIN_SCENARIO_CONV_PER_MONTH,
        MIN_SCENARIO_TOKENS_IN,
        MIN_SCENARIO_TOKENS_OUT,
        MIN_LLM_PIN_PER_M,
        MIN_LLM_POUT_PER_M,
    )
    gpu_lo_parity, gpu_hi_parity = gpu_monthly_from_hourly(MIN_GPU_PARITY_HR_LOW, MIN_GPU_PARITY_HR_HIGH)
    gpu_parity_mid_mo = (gpu_lo_parity + gpu_hi_parity) / 2
    llm_month_total = MIN_PLAT_TOTAL + llm_inf_floor
    gpu_month_total = MIN_PLAT_TOTAL + gpu_parity_mid_mo
    per_conv_llm = llm_month_total / MIN_SCENARIO_CONV_PER_MONTH
    per_conv_gpu = gpu_month_total / MIN_SCENARIO_CONV_PER_MONTH

    section_rule(elements, "Current-scope minimum — five clients · five thousand conversations / month", h1)
    elements.append(
        Paragraph(
            xe(
                "Assumptions: aggregate volume is five thousand answered conversations per calendar month across five customer "
                "organizations sharing one orchestration deployment. Average prompt shape matches the playbook token model "
                f"({MIN_SCENARIO_TOKENS_IN} input tokens and {MIN_SCENARIO_TOKENS_OUT} output tokens per conversation) until "
                "production logs refine it. Hosted LLM path uses mid-tier illustrative vendor rates; private GPU path uses "
                "twenty-four seven rent at the midpoint of the twenty-four gigabyte VRAM band in the reference table — "
                "the playbook tier typically associated with thirteen-billion-parameter-class instruction models at production "
                "precision — sized so evaluation scores track the same acceptance bar as the hosted reference. Peak concurrency "
                "can still force a larger SKU."
            ),
            body,
        )
    )
    elements.append(
        wrap_cost_table(
            minimal_scope_platform_rows(),
            [52 * mm, 28 * mm, 90 * mm],
            th,
            tc,
            tc_money,
            NAVY,
            money_cols=[1],
            body_bg=colors.white,
        )
    )
    elements.append(Spacer(1, 8))

    min_totals = [
        ["Inference path", "Fixed platform", "Inference (illustrative)", "Monthly total", "USD / answered conversation"],
        [
            "Hosted LLM API — mid-tier rates",
            f"${MIN_PLAT_TOTAL}",
            f"${llm_inf_floor:,.2f}",
            f"${llm_month_total:,.2f}",
            f"${per_conv_llm:.4f}",
        ],
        [
            "Private GPU — ~24 GB class (parity sizing), 24/7 midpoint",
            f"${MIN_PLAT_TOTAL}",
            f"${gpu_parity_mid_mo:,.2f}",
            f"${gpu_month_total:,.2f}",
            f"${per_conv_gpu:.4f}",
        ],
    ]
    elements.append(
        wrap_cost_table(
            min_totals,
            [44 * mm, 28 * mm, 38 * mm, 30 * mm, 30 * mm],
            th,
            tc,
            tc_money,
            BLUE,
            money_cols=[1, 2, 3, 4],
            body_bg=BG,
        )
    )
    econ_floor = llm_monthly_cost(
        MIN_SCENARIO_CONV_PER_MONTH,
        MIN_SCENARIO_TOKENS_IN,
        MIN_SCENARIO_TOKENS_OUT,
        0.10,
        0.40,
    )
    elements.append(
        Paragraph(
            xe(
                f"Illustrative economical vendor tier at the same volume would land near ${econ_floor:,.2f} for inference only "
                "(before platform), at the expense of model capability and latency — not recommended as the default \"decent performance\" "
                "baseline."
            ),
            small,
        )
    )

    section_rule(elements, "Expanded reference — platform and channels (when enabled)", h2)
    elements.append(
        Paragraph(
            xe(
                "Use these wider bands when WhatsApp, Slack, managed Postgres, object-storage backups, CDN, and similar "
                "services enter scope. Subtotal spans roughly one hundred forty-two to one thousand seventy-six USD "
                "depending chiefly on WhatsApp; midpoint bundle approximately four hundred twenty-five USD per month feeds "
                "the larger aggregate-volume scenarios later in this document."
            ),
            small,
        )
    )
    elements.append(
        wrap_cost_table(
            platform_misc_cost_rows(),
            [52 * mm, 42 * mm, 76 * mm],
            th,
            tc,
            tc_money,
            NAVY,
            money_cols=[1],
            body_bg=colors.white,
        )
    )
    elements.append(Spacer(1, 10))

    section_rule(elements, "GPU inference — rented VM bands", h2)
    gpu_rows = [
        ["VRAM band", "Example models", "Hourly rent (illustrative)", "Monthly at 730 hours"],
        ["~8 GB", "7B Q4 instruct", "$0.28 – $0.48", f"${gpu_monthly_from_hourly(0.28, 0.48)[0]:,.0f} – ${gpu_monthly_from_hourly(0.28, 0.48)[1]:,.0f}"],
        ["~16 GB", "13B Q4 / 7B FP16", "$0.38 – $0.72", f"${gpu_monthly_from_hourly(0.38, 0.72)[0]:,.0f} – ${gpu_monthly_from_hourly(0.38, 0.72)[1]:,.0f}"],
        ["~24 GB", "13B Q8 / FP16", "$0.45 – $0.95", f"${gpu_monthly_from_hourly(0.45, 0.95)[0]:,.0f} – ${gpu_monthly_from_hourly(0.45, 0.95)[1]:,.0f}"],
        ["~40–48 GB", "34B class", "$0.95 – $1.85", f"${gpu_monthly_from_hourly(0.95, 1.85)[0]:,.0f} – ${gpu_monthly_from_hourly(0.95, 1.85)[1]:,.0f}"],
        ["~80 GB", "70B+ class", "$1.85 – $3.50", f"${gpu_monthly_from_hourly(1.85, 3.5)[0]:,.0f} – ${gpu_monthly_from_hourly(1.85, 3.5)[1]:,.0f}"],
    ]
    elements.append(
        wrap_cost_table(
            gpu_rows,
            [22 * mm, 48 * mm, 38 * mm, 62 * mm],
            th,
            tc,
            tc_money,
            BLUE,
            money_cols=[2, 3],
            body_bg=BG,
        )
    )
    elements.append(
        Paragraph(
            xe("Formula: monthly GPU approximately hourly rate multiplied by seven hundred thirty for twenty-four seven operation."),
            small,
        )
    )

    gpu_mid = 420.0
    plat_mid = 425.0
    grand = gpu_mid + plat_mid
    scen_gpu = [
        ["Aggregate conversations per month", "GPU inference (mid)", "Platform (mid)", "Grand total (mid)", "Fully-loaded USD per conversation"],
        ["25,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 25000:.4f}"],
        ["30,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 30000:.4f}"],
        ["50,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 50000:.4f}"],
        ["60,000", f"${gpu_mid:,.0f}", f"${plat_mid:,.0f}", f"${grand:,.0f}", f"${grand / 60000:.4f}"],
    ]
    section_rule(elements, "GPU path — illustrative totals using midpoint assumptions", h2)
    elements.append(
        Paragraph(
            xe(
                "Inference uses one twenty-four seven GPU at roughly four hundred twenty USD monthly (example zero point five seven five USD per hour times seven hundred thirty). "
                "Platform uses four hundred twenty-five USD midpoint. GPU rent does not climb with conversation count until you add capacity."
            ),
            body,
        )
    )
    elements.append(
        wrap_cost_table(
            scen_gpu,
            [40 * mm, 32 * mm, 32 * mm, 34 * mm, 32 * mm],
            th,
            tc,
            tc_money,
            NAVY,
            money_cols=[1, 2, 3, 4],
            body_bg=colors.white,
        )
    )

    elements.append(PageBreak())

    section_rule(elements, "Hosted LLM API — token assumptions", h2)
    tin, tout = 2000, 150
    elements.append(
        Paragraph(
            xe(
                f"Illustrative averages for ERP plus restaurant prompts with retrieval: input tokens per conversation {tin}, "
                f"output tokens per conversation {tout}. Tune after production log sampling."
            ),
            body,
        )
    )

    tier_rows = [
        ["Tier label", "Input USD per 1M tokens", "Output USD per 1M tokens", "Notes"],
        ["Economical routing", "$0.10", "$0.40", "Verify current vendor list pricing."],
        ["Mid-tier hosted", "$0.40", "$1.60", "Balanced quality and latency."],
        ["Premium frontier-class", "$2.00", "$8.00", "Upper illustrative band."],
    ]
    elements.append(
        wrap_cost_table(
            tier_rows,
            [38 * mm, 38 * mm, 38 * mm, 56 * mm],
            th,
            tc,
            tc_money,
            BLUE,
            money_cols=[1, 2],
            body_bg=BG,
        )
    )

    tiers = [
        ("Economical", 0.10, 0.40),
        ("Mid-tier", 0.40, 1.60),
        ("Premium", 2.00, 8.00),
    ]
    convs = [25000, 30000, 50000, 60000]

    section_rule(elements, "LLM API inference cost by tier and volume", h2)
    for name, pin, pout in tiers:
        rows = [["Aggregate conversations per month", "Estimated LLM USD per month"]]
        for c in convs:
            m = llm_monthly_cost(c, tin, tout, pin, pout)
            rows.append([f"{c:,}", f"${m:,.2f}"])
        elements.append(Paragraph(xe(f"{name} tier"), lead))
        elements.append(
            wrap_cost_table(rows, [78 * mm, 92 * mm], th, tc, tc_money, NAVY, money_cols=[1], body_bg=colors.white)
        )
        elements.append(Spacer(1, 6))

    pin_m, pout_m = 0.40, 1.60
    combined_rows = [
        [
            "Aggregate conv per month",
            "LLM mid-tier estimate",
            "Platform mid",
            "Grand total mid",
            "Fully-loaded USD per conv",
            "LLM-only USD per conv",
        ],
    ]
    for c in convs:
        llm_c = llm_monthly_cost(c, tin, tout, pin_m, pout_m)
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

    section_rule(elements, "LLM API path — grand totals (mid tier plus platform midpoint)", h2)
    elements.append(
        wrap_cost_table(
            combined_rows,
            [28 * mm, 30 * mm, 26 * mm, 28 * mm, 30 * mm, 28 * mm],
            th,
            tc,
            tc_money,
            BLUE,
            money_cols=[1, 2, 3, 4, 5],
            body_bg=BG,
        )
    )

    section_rule(elements, "Knowledge retrieval incremental cost", h2)
    elements.append(
        Paragraph(
            xe(
                "This codebase uses Postgres full-text search on kb_articles. Incremental retrieval cost is bundled in database "
                "spend rather than a separate embedding bill. Optional future vector embeddings would add their own line item."
            ),
            body,
        )
    )

    section_rule(elements, "Single-tenant reference — monthly fixed stack (GPU illustration)", h2)
    fixed_rows = [
        ["Component", "Description", "USD per month (band)"],
        ["Rented GPU twenty-four seven", "Inference VM, roughly seven hundred thirty hours", "$180 – $1,825+"],
        ["Application VPS", "FastAPI and TLS proxy without GPU", "$18 – $85"],
        ["PostgreSQL managed", "ERP tables, KB, full-text index", "$0 – $70"],
        ["Channels", "WhatsApp BSP and Slack optional", "$0 – $90"],
        ["Embeddings API", "Zero when using Postgres FTS only", "$0"],
        ["External LLM API", "Zero when all completions stay on GPU", "$0"],
    ]
    elements.append(
        wrap_cost_table(fixed_rows, [34 * mm, 92 * mm, 44 * mm], th, tc, tc_money, NAVY, money_cols=[2], body_bg=colors.white)
    )

    section_rule(elements, "Single-tenant reference — fully-loaded USD per conversation", h2)
    elements.append(
        Paragraph(
            xe(
                "Example fixed stacks spread across monthly volumes (not additive to multi-tenant scenario tables above). "
                "Budget roughly two hundred ninety-five USD, Standard roughly six hundred thirty USD, Premium roughly one thousand two hundred ninety-five USD monthly stacks."
            ),
            small,
        )
    )
    ref_budget, ref_std, ref_prem = 295.0, 630.0, 1295.0
    vols = [500, 2500, 5000, 15000, 50000]
    per_conv = [["Monthly conversations", "Budget stack per conv", "Standard stack per conv", "Premium stack per conv"]]
    for n in vols:
        per_conv.append(
            [
                f"{n:,}",
                f"${ref_budget / n:.3f}",
                f"${ref_std / n:.3f}",
                f"${ref_prem / n:.3f}",
            ]
        )
    elements.append(
        wrap_cost_table(per_conv, [46 * mm, 41 * mm, 41 * mm, 42 * mm], th, tc, tc_money, BLUE, money_cols=[1, 2, 3], body_bg=BG)
    )

    elements.append(PageBreak())

    section_rule(elements, "Implementation roadmap — typical phases", h1)
    roadmap = [
        (
            "Discovery and integration planning",
            "Confirm ERP surfaces and APIs, channel choices (web, WhatsApp, Slack), retention policies, "
            "and pilot tenant scope. Agree inference path, hosted reference model tier, and parity acceptance metrics.",
        ),
        (
            "Pilot deployment",
            "Deploy orchestration, Postgres schema including kb_articles and search indexing, guardrails, "
            "and human handoff. Route a subset of traffic; capture transcripts for quality review.",
        ),
        (
            "Production scale-out",
            "Harden monitoring, rate limits, backups, and runbooks. Tune token budgets or GPU sizing using real concurrency traces.",
        ),
        (
            "Learning module activation",
            "Enable extraction and gates in shadow mode, then progressive auto-publish with rollback drills and dashboard review.",
        ),
    ]
    for title, desc in roadmap:
        elements.append(Paragraph(xe(title), lead))
        elements.append(Paragraph(xe(desc), body))

    section_rule(elements, "Appendix — terms used in this document", h1)
    gloss = [
        ["Term", "Meaning here"],
        ["RAG", "Retrieval-augmented generation: facts and policies from search are injected into the model prompt."],
        ["KB / knowledge base", "Structured articles stored in Postgres; retrieval feeds grounded answers."],
        ["ERP truth gate", "Automated check that factual statements align with live ERP or API data before publication."],
        ["Tenant", "A logically isolated customer organization within the shared platform stack."],
        ["OpenAI-compatible API", "HTTPS chat-completions shape usable with many vendors and local GPU servers."],
        ["BSP", "Business Solution Provider — WhatsApp messaging partner billing Meta conversation categories."],
        ["VRAM", "GPU memory; model size, precision, and concurrent chats influence required VRAM."],
        ["Fully-loaded per conversation", "Total monthly stack divided by answered conversations in that month."],
        [
            "Performance parity",
            "Hosted and local inference target the same prompts, tools, and scoring thresholds; GPU SKU follows from that baseline.",
        ],
        ["Golden set", "Frozen prompts and rubrics used to regression-test both backends before traffic moves."],
    ]
    elements.append(wrap_table(gloss, [38 * mm, 132 * mm], th, tc, NAVY, BG))

    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            xe(
                "Disclaimer: All figures are non-binding planning aids. Bind budgets to executed quotes from GPU hosts, database vendors, "
                "messaging providers, and LLM vendors."
            ),
            note,
        )
    )

    doc.build(elements, onFirstPage=footer_canvas, onLaterPages=footer_canvas)
    print(f"PDF generated: {OUTPUT_PATH}")


def main():
    build_document()


if __name__ == "__main__":
    main()
