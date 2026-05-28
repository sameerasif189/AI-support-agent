"""
Generate a client-facing Word document for Nexus Support (ERP AI Support Agent).

Run: python generate_client_product_guide_docx.py
Output: Client_Nexus_Support_Product_Guide.docx
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BASE = Path(r"c:\Users\PC\AI Support agent")
ASSETS = Path(
    r"C:\Users\PC\.cursor\projects\c-Users-PC-AI-Support-agent\assets"
)
OUTPUT = BASE / "Client_Nexus_Support_Product_Guide.docx"

# Brand colours
NAVY = RGBColor(0x1E, 0x29, 0x3B)
BLUE = RGBColor(0x25, 0x63, 0xEB)
PURPLE = RGBColor(0x7C, 0x3A, 0xED)
SLATE = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x64, 0x74, 0x8B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0D, 0x94, 0x88)

FILL_NAVY = "1E293B"
FILL_BLUE = "EEF2FF"
FILL_USER = "ECFDF5"
FILL_ADMIN = "FEF3C7"
FILL_NOTE = "E0F2FE"
FILL_FRAME = "F8FAFC"
FILL_WHITE = "FFFFFF"

BORDER_NAVY = "1E293B"
BORDER_PURPLE = "7C3AED"
BORDER_BLUE = "2563EB"
BORDER_TEAL = "0D9488"
BORDER_AMBER = "D97706"

IMG = {
    "login": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-0fea6d21-e5f9-41d9-afbd-3a07de2c6396.png",
    "chat_loading": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-a8dbfcbe-c2e8-4db3-9bdc-6c2a450391f5.png",
    "chat_answer": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-88b6a13a-d1a8-4074-a49e-f4cc376b130d.png",
    "indexed_docs": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-61719d97-618f-41e3-980d-6375c65fd2aa.png",
    "kb_text": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-389c74ad-27b9-4002-9098-6e24f0f38ddc.png",
    "kb_file": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-87bc7aa4-2ee0-4e16-83ed-af12b9da7623.png",
    "kb_feed": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-0a6c9b4e-6393-4de9-aa72-59ccd816faf0.png",
    "rag_diagram": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-0bd69724-1a6d-49bc-bf50-9cf6a96515b8.png",
    "admin_chat": ASSETS
    / "c__Users_PC_AppData_Roaming_Cursor_User_workspaceStorage_2ab4aa2809b52d35b548406eb9b621e8_images_image-46a0adb0-81f1-4429-92ed-d1922a63ce2f.png",
}


# ── OOXML helpers ──────────────────────────────────────────────────────────


def _set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill_hex)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)


def _set_cell_borders(
    cell,
    *,
    color: str = BORDER_PURPLE,
    size: int = 6,
    left_size: int | None = None,
) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(left_size if edge == "left" and left_size else size))
        el.set(qn("w:color"), color)
        el.set(qn("w:space"), "0")
        borders.append(el)
    tc_pr.append(borders)


def _set_cell_margins(cell, *, top=60, bottom=60, left=100, right=100) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tc_pr.append(mar)


def _set_table_width_full(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    if tbl.tblPr is None:
        tbl.insert(0, tbl_pr)
    w = OxmlElement("w:tblW")
    w.set(qn("w:type"), "pct")
    w.set(qn("w:w"), "5000")
    tbl_pr.append(w)


def _remove_table_spacing(table) -> None:
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        return
    for tag in ("w:tblCellSpacing", "w:tblCellMar"):
        for el in tbl_pr.findall(qn(tag)):
            tbl_pr.remove(el)


def _tight_para(p, *, before=0, after=0, align=None) -> None:
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.1
    if align is not None:
        p.alignment = align


def _no_proof(run) -> None:
    r_pr = run._element.get_or_add_rPr()
    if r_pr.find(qn("w:noProof")) is None:
        r_pr.append(OxmlElement("w:noProof"))
    lang = r_pr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        lang.set(qn("w:val"), "en-US")
        r_pr.append(lang)


def _no_proof_paragraph(p) -> None:
    p_pr = p._element.get_or_add_pPr()
    if p_pr.find(qn("w:noProof")) is None:
        p_pr.append(OxmlElement("w:noProof"))
    for run in p.runs:
        _no_proof(run)


def _add_run(paragraph, text: str, *, bold=False, italic=False, color=None, size=11):
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    _no_proof(run)
    return run


def _disable_proofing(doc: Document) -> None:
    settings = doc.settings.element
    for tag in ("w:hideSpellingErrors", "w:hideGrammaticalErrors"):
        el = settings.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            settings.append(el)
        el.set(qn("w:val"), "1")
    proof = settings.find(qn("w:proofState"))
    if proof is None:
        proof = OxmlElement("w:proofState")
        settings.append(proof)
    proof.set(qn("w:spelling"), "clean")
    proof.set(qn("w:grammar"), "clean")


def _no_proof_style(style) -> None:
    try:
        r_pr = style.element.get_or_add_rPr()
    except AttributeError:
        return
    if r_pr.find(qn("w:noProof")) is None:
        r_pr.append(OxmlElement("w:noProof"))


def _finalize_document(doc: Document) -> None:
    """Strip spell/grammar flags from every paragraph and run."""
    for style in doc.styles:
        _no_proof_style(style)
    for p in doc.paragraphs:
        _no_proof_paragraph(p)
        _tight_para(p, before=0, after=0)
    for table in doc.tables:
        _set_table_compact(table)
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _no_proof_paragraph(p)


def _set_table_compact(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)
    spacing = tbl_pr.find(qn("w:tblCellSpacing"))
    if spacing is None:
        spacing = OxmlElement("w:tblCellSpacing")
        tbl_pr.append(spacing)
    spacing.set(qn("w:w"), "0")
    spacing.set(qn("w:type"), "dxa")


_last_para = None


def _collapse_before_next_block() -> None:
    global _last_para
    if _last_para is not None:
        _last_para.paragraph_format.space_after = Pt(0)
        _last_para.paragraph_format.space_before = Pt(0)


def _setup_page(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)


def setup_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = SLATE
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.line_spacing = 1.1
    _no_proof_style(normal)

    for level, size, color in [(1, 20, NAVY), (2, 14, NAVY), (3, 12, BLUE)]:
        h = doc.styles[f"Heading {level}"]
        h.font.name = "Calibri"
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = color
        h.paragraph_format.space_before = Pt(8 if level > 1 else 4)
        h.paragraph_format.space_after = Pt(0)
        h.paragraph_format.keep_with_next = True
        _no_proof_style(h)

    for name in ("List Bullet", "List Number"):
        if name in doc.styles:
            lb = doc.styles[name]
            lb.paragraph_format.space_after = Pt(0)
            lb.paragraph_format.space_before = Pt(0)
            _no_proof_style(lb)


# ── Layout blocks ──────────────────────────────────────────────────────────


def add_spacer(doc: Document, pt: int = 6) -> None:
    global _last_para
    p = doc.add_paragraph()
    _tight_para(p, before=0, after=0)
    p.paragraph_format.space_before = Pt(pt)
    _last_para = p


def add_heading_tight(doc: Document, text: str, level: int = 2):
    global _last_para
    h = doc.add_heading(text, level=level)
    h.paragraph_format.space_before = Pt(8 if level > 1 else 4)
    h.paragraph_format.space_after = Pt(0)
    _no_proof_paragraph(h)
    _last_para = h
    return h


def add_cover(doc: Document) -> None:
    banner = doc.add_table(rows=1, cols=1)
    _set_table_width_full(banner)
    cell = banner.rows[0].cells[0]
    _set_cell_shading(cell, FILL_NAVY)
    _set_cell_margins(cell, top=280, bottom=280, left=200, right=200)
    _set_cell_borders(cell, color=BORDER_PURPLE, size=8, left_size=32)

    p = cell.paragraphs[0]
    _tight_para(p, before=0, after=6, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_run(p, "NEXUS SUPPORT", bold=True, color=BLUE, size=13)

    p2 = cell.add_paragraph()
    _tight_para(p2, before=0, after=6, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_run(p2, "Enterprise AI Support Platform", bold=True, color=WHITE, size=26)

    p3 = cell.add_paragraph()
    _tight_para(p3, before=0, after=0, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_run(p3, "Product Guide and Live Demonstration", color=RGBColor(0xCB, 0xD5, 0xE1), size=14)

    add_spacer(doc, 16)

    chips = doc.add_table(rows=1, cols=3)
    _set_table_width_full(chips)
    for i, (label, fill, border) in enumerate(
        [
            ("RAG Knowledge", FILL_BLUE, BORDER_BLUE),
            ("ERP Context", FILL_USER, BORDER_TEAL),
            ("Native GPU + API", "F3E8FF", BORDER_PURPLE),
        ]
    ):
        c = chips.rows[0].cells[i]
        _set_cell_shading(c, fill)
        _set_cell_borders(c, color=border, size=6)
        _set_cell_margins(c, top=80, bottom=80, left=60, right=60)
        cp = c.paragraphs[0]
        _tight_para(cp, align=WD_ALIGN_PARAGRAPH.CENTER)
        _add_run(cp, label, bold=True, color=NAVY, size=10)

    add_spacer(doc, 20)
    p = doc.add_paragraph()
    _tight_para(p, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_run(
        p,
        f"Prepared for client review  |  {date.today():%B %d, %Y}",
        color=MUTED,
        size=10,
    )
    doc.add_page_break()


def add_part_banner(doc: Document, title: str, subtitle: str, fill: str, border: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    _set_table_width_full(table)
    cell = table.rows[0].cells[0]
    _set_cell_shading(cell, fill)
    _set_cell_borders(cell, color=border, size=6, left_size=28)
    _set_cell_margins(cell, top=100, bottom=100, left=140, right=120)
    p = cell.paragraphs[0]
    _tight_para(p, before=0, after=4)
    _add_run(p, title + "\n", bold=True, color=NAVY, size=13)
    _add_run(p, subtitle, color=SLATE, size=10)
    add_spacer(doc, 4)


def add_callout(doc: Document, title: str, body: str, fill: str, border: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    _set_table_width_full(table)
    cell = table.rows[0].cells[0]
    _set_cell_shading(cell, fill)
    _set_cell_borders(cell, color=border, size=6, left_size=24)
    _set_cell_margins(cell, top=90, bottom=90, left=130, right=110)
    p = cell.paragraphs[0]
    _tight_para(p, before=0, after=4)
    _add_run(p, title + "\n", bold=True, color=NAVY, size=11)
    _add_run(p, body, color=SLATE, size=10)
    _set_table_compact(table)
    add_spacer(doc, 4)


def add_body(doc: Document, text: str, *, gap_after: int = 4) -> None:
    global _last_para
    p = doc.add_paragraph()
    _tight_para(p, before=0, after=gap_after)
    _add_run(p, text)
    _last_para = p


def add_bullets(doc: Document, items: list[str], *, gap_after: int = 4) -> None:
    global _last_para
    for i, item in enumerate(items):
        p = doc.add_paragraph(style="List Bullet")
        _tight_para(p, before=0, after=0 if i == len(items) - 1 else 1)
        if p.runs:
            p.clear()
        _add_run(p, item, size=10.5)
        _last_para = p
    if gap_after:
        add_spacer(doc, gap_after)


def add_image(doc: Document, path: Path, caption: str, width_in: float = 5.85) -> None:
    global _last_para
    _collapse_before_next_block()

    frame = doc.add_table(rows=1, cols=1)
    _set_table_width_full(frame)
    _remove_table_spacing(frame)
    _set_table_compact(frame)
    cell = frame.rows[0].cells[0]
    _set_cell_shading(cell, FILL_FRAME)
    _set_cell_borders(cell, color=BORDER_PURPLE, size=8)
    _set_cell_margins(cell, top=36, bottom=36, left=72, right=72)

    if not path.exists():
        p = cell.paragraphs[0]
        _tight_para(p, align=WD_ALIGN_PARAGRAPH.CENTER)
        _add_run(p, f"[Image missing: {path.name}]", color=MUTED, size=10)
    else:
        p = cell.paragraphs[0]
        _tight_para(p, before=0, after=0, align=WD_ALIGN_PARAGRAPH.CENTER)
        run = p.add_run()
        _no_proof(run)
        run.add_picture(str(path), width=Inches(width_in))

    cap = cell.add_paragraph()
    _tight_para(cap, before=0, after=0, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_run(cap, caption, italic=True, color=MUTED, size=9)
    _last_para = None
    add_spacer(doc, 6)


def add_styled_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    _set_table_width_full(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        _set_cell_shading(cell, FILL_NAVY)
        _set_cell_borders(cell, color=BORDER_NAVY, size=4)
        _set_cell_margins(cell, top=70, bottom=70, left=80, right=80)
        _add_run(cell.paragraphs[0], h, bold=True, color=WHITE, size=10)
    for r, row in enumerate(rows, start=1):
        alt = r % 2 == 0
        for c, val in enumerate(row):
            cell = table.rows[r].cells[c]
            _set_cell_shading(cell, FILL_BLUE if (c == 0 or alt) else FILL_WHITE)
            _set_cell_borders(cell, color="CBD5E1", size=4)
            _set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            _add_run(cell.paragraphs[0], val, color=SLATE, size=10)
    _set_table_compact(table)
    add_spacer(doc, 6)


def add_comparison_table(doc: Document) -> None:
    add_styled_table(
        doc,
        ["Feature", "Local GPU (no cloud LLM needed)", "Cloud API only (no GPU)"],
        [
            [
                "Where answers are generated",
                "On your machine via llama.cpp (Qwen2.5-7B GGUF)",
                "Groq or OpenAI-compatible hosted API",
            ],
            [
                "Data privacy for chat",
                "Questions and ERP context stay on-premises",
                "Question and context sent to cloud provider",
            ],
            [
                "Hardware required",
                "NVIDIA GPU (8 GB+ VRAM recommended)",
                "None — any server or laptop",
            ],
            [
                "Typical latency",
                "2 to 15 seconds first reply (model load), then faster",
                "Usually under 2 seconds per reply",
            ],
            [
                "Embeddings (RAG search)",
                "OpenAI-compatible API (separate from chat LLM)",
                "Same — embeddings always use embedding API",
            ],
            [
                "User selector in UI",
                "Auto / Local GPU / Cloud API",
                "Auto picks Cloud API when GPU unavailable",
            ],
            [
                "Cost model",
                "GPU hardware or rental; no per-token chat fee",
                "Pay-per-token on hosted LLM; free tier available (Groq)",
            ],
        ],
    )


def build() -> None:
    global _last_para
    _last_para = None
    doc = Document()
    _disable_proofing(doc)
    _setup_page(doc)
    setup_styles(doc)

    add_cover(doc)

    doc.add_heading("Executive Summary", level=1)
    add_body(
        doc,
        "Nexus Support is an enterprise AI assistant that connects to your ERP database "
        "and a searchable knowledge base. Customers ask natural-language questions about "
        "orders, invoices, and policies. The system retrieves the right documents, loads "
        "their account context, and produces a grounded answer with source citations and "
        "confidence scores visible in the chat.",
    )
    add_callout(
        doc,
        "What makes this different from a generic chatbot?",
        "Every answer is augmented with real ERP data (orders, invoices, tickets) and "
        "indexed documentation (RAG). The assistant does not invent facts. It combines "
        "retrieved knowledge with live database context before the language model writes "
        "the reply.",
        FILL_NOTE,
        BORDER_BLUE,
    )

    doc.add_heading("Key capabilities (live and verified)", level=2)
    add_bullets(
        doc,
        [
            "Sign-in workspace with role-based access (customer, agent, admin).",
            "Hybrid RAG: vector embeddings (pgvector) plus full-text search on Neon Postgres.",
            "ERP context: customers, orders, invoices, support tickets linked at chat time.",
            "Dual LLM routing: local GPU (llama.cpp + Qwen2.5-7B) or cloud API (Groq).",
            "Knowledge ingestion: paste text, upload files, one-shot URLs, live API feeds.",
            "Learning from chat: successful Q&A pairs become indexed help articles automatically.",
            "Customer memory: remembers prior conversations within a session.",
            "Channels: web UI, WhatsApp, and Slack webhooks.",
        ],
    )
    doc.add_page_break()

    add_part_banner(
        doc,
        "Part 1 — End-User Experience (Customer)",
        "Customers sign in, ask questions, and receive grounded answers scoped to their own account.",
        FILL_USER,
        BORDER_TEAL,
    )
    add_callout(
        doc,
        "Who is this for?",
        "Customers (cust1 through cust8), agents, and anyone who needs answers — not "
        "administrators managing the knowledge base. Customers only see their own ERP data.",
        FILL_USER,
        BORDER_TEAL,
    )

    add_heading_tight(doc, "1.1  Sign in to your workspace", level=2)
    add_body(
        doc,
        "Users open the Nexus Support portal and sign in with a username and password. "
        "For demo accounts, the password is the user's first name (for example: cust1 "
        "uses Alex, admin uses Admin). The login screen highlights RAG knowledge, ERP "
        "context, and Native GPU plus API.",
        gap_after=2,
    )
    add_image(doc, IMG["login"], "Figure 1 — Login screen (customer cust1 signing in)")

    add_heading_tight(doc, "1.2  Ask questions in plain English", level=2)
    add_body(
        doc,
        "After sign-in, the chat panel opens. The header shows the signed-in name, role "
        "(CUSTOMER), and which engines are active: RAG, Native GPU (llama.cpp), and Groq API. "
        "Customers type questions such as \"Are there any current pending orders?\" without "
        "SQL or menu navigation.",
        gap_after=2,
    )
    add_image(
        doc,
        IMG["chat_loading"],
        "Figure 2 — Customer chat: question submitted, assistant processing",
    )

    add_heading_tight(doc, "1.3  Grounded answers with transparency", level=2)
    add_body(
        doc,
        "The assistant returns factual answers drawn from ERP records and the knowledge base. "
        "Each reply shows metadata tags so users and auditors can see how the answer was built:",
        gap_after=2,
    )
    add_bullets(
        doc,
        [
            "LLM LOCAL — answer generated on the local GPU (no cloud LLM call for this reply).",
            "2 SOURCES — two knowledge chunks were retrieved and cited.",
            "76 to 84% CONFIDENCE — retrieval and intent confidence score.",
            "REMEMBERED YOU — customer memory from prior turns in this session.",
            "ADDED TO KB — the exchange was distilled into a reusable help article.",
        ],
        gap_after=2,
    )
    add_image(
        doc,
        IMG["chat_answer"],
        "Figure 3 — Customer receives order details (ORD-10475, $1,671.45) with source tags",
    )

    add_heading_tight(doc, "1.4  LLM mode selector (user control)", level=2)
    add_body(
        doc,
        "The dropdown next to the message box lets users choose how the reply is generated:",
    )
    add_bullets(
        doc,
        [
            "Auto — tries local GPU first, falls back to cloud API if GPU is unavailable.",
            "Local GPU — forces on-premises llama.cpp inference (private, no token cost).",
            "Cloud API — forces Groq or hosted LLM (fast, no GPU required).",
        ],
    )
    add_callout(
        doc,
        "In plain terms",
        "Think of Auto as a smart switch: use your own computer's graphics card when it is "
        "ready, otherwise use the internet-based AI service. Embeddings (the search index) "
        "always run through a separate API. That part is the same in both modes.",
        FILL_NOTE,
        BORDER_BLUE,
    )
    doc.add_page_break()

    add_part_banner(
        doc,
        "Part 2 — Administrator Experience",
        "Admins and agents curate knowledge, register live feeds, and query ERP data globally.",
        FILL_ADMIN,
        BORDER_AMBER,
    )
    add_callout(
        doc,
        "Who is this for?",
        "Administrators (admin / Admin) and support agents (agent / Morgan) who curate "
        "knowledge, register live feeds, and review indexed documents. Admins see all "
        "customers' ERP data; agents see support scope.",
        FILL_ADMIN,
        BORDER_AMBER,
    )

    add_heading_tight(doc, "2.1  Admin workspace: global ERP and knowledge panel", level=2)
    add_body(
        doc,
        "Administrators sign in as admin / Admin and see the full workspace: chat on the "
        "left and the Knowledge panel on the right. Unlike customers, admins can query "
        "across all accounts — for example \"list the highest bill customers\" or "
        "\"list top 5 orders.\" Answers still show LLM LOCAL, source count, and confidence "
        "tags for auditability.",
        gap_after=2,
    )
    add_bullets(
        doc,
        [
            "Admin badge (yellow) vs Customer badge (purple) — role is visible in the header.",
            "Global ERP queries return cross-customer data (for example Drew Wong, $3,490.00 top bill).",
            "Knowledge panel on Live feed tab — register and sync API sources in the same view.",
            "Status bar: Groq on, Native GPU, Qwen2.5-7B-Instruct — local inference active.",
        ],
        gap_after=2,
    )
    add_image(
        doc,
        IMG["admin_chat"],
        "Figure 4 — Admin: global ERP queries (highest bills, top 5 orders) with Knowledge panel",
        width_in=6.35,
    )

    add_heading_tight(doc, "2.2  Knowledge panel (admin-only)", level=2)
    add_body(
        doc,
        "When an admin or agent signs in, an additional Knowledge panel appears beside the "
        "chat. Four ingestion methods are available:",
    )
    add_bullets(
        doc,
        [
            "Text — paste documentation directly; indexed immediately.",
            "File — upload .txt, .md, .csv, .json, or .log files.",
            "Once — fetch a single URL and index its content one time.",
            "Live feed — register an API URL that is polled every N minutes into the KB.",
        ],
    )
    add_body(
        doc,
        "Learned rows (from chat Q&A) are separate from live feeds. They appear in the "
        "Indexed Documents list automatically when confidence thresholds are met.",
    )

    add_heading_tight(doc, "2.3  Add text to the knowledge base", level=2)
    add_image(doc, IMG["kb_text"], "Figure 5 — Admin: paste title and content, click Add to knowledge")

    add_heading_tight(doc, "2.4  Upload a file", level=2)
    add_image(doc, IMG["kb_file"], "Figure 6 — Admin: upload UTF-8 text files for indexing")

    add_heading_tight(doc, "2.5  Register a live API feed", level=2)
    add_body(
        doc,
        "Live feeds poll an external (or internal demo) API on a schedule — for example "
        "every 60 minutes — and refresh the knowledge base without manual uploads. The demo "
        "feed at localhost:8000 maps to the built-in ERP help JSON endpoint.",
        gap_after=2,
    )
    add_image(doc, IMG["kb_feed"], "Figure 7 — Admin: register live feed with refresh interval")

    add_heading_tight(doc, "2.6  Indexed documents (including learned articles)", level=2)
    add_body(
        doc,
        "All indexed content — manual uploads, feed syncs, and chat-learned articles — "
        "appears in the Indexed Documents sidebar. Items tagged \"learned from chat\" were "
        "created automatically from successful customer conversations.",
        gap_after=2,
    )
    add_image(
        doc,
        IMG["indexed_docs"],
        "Figure 8 — Indexed documents: manual and auto-learned help articles",
    )
    doc.add_page_break()

    add_part_banner(
        doc,
        "Part 3 — How RAG Works (Plain English)",
        "Retrieval-Augmented Generation: search first, then answer.",
        FILL_NOTE,
        BORDER_BLUE,
    )
    add_body(
        doc,
        "RAG stands for Retrieval-Augmented Generation. Instead of asking the AI to "
        "memorize everything, we give it a searchable library and let it look things up "
        "before answering — like an open-book exam.",
        gap_after=2,
    )
    add_image(
        doc,
        IMG["rag_diagram"],
        "Figure 9 — RAG architecture: data preparation (left) and live Q&A loop (right)",
        width_in=6.15,
    )

    doc.add_heading("3.1  Data preparation (happens when content is added)", level=2)
    add_bullets(
        doc,
        [
            "A. Raw data — admin uploads text or files, or the system learns from chat.",
            "B. Extraction — text is pulled from files, URLs, or API feeds.",
            "C. Chunking — long documents are split into about 400-token pieces with overlap.",
            "D. Embedding — each chunk is converted to a numeric vector (1,536 dimensions) "
            "via OpenAI text-embedding-3-small and stored in Neon Postgres (pgvector).",
        ],
    )

    doc.add_heading("3.2  Live question answering (happens at chat time)", level=2)
    add_bullets(
        doc,
        [
            "1. Query — customer asks a question.",
            "2. Embed query — the same embedding model vectorizes the question.",
            "3. Vector search — pgvector finds the most similar stored chunks (hybrid plus FTS).",
            "4. ERP context — SQL loads that customer's orders, invoices, and tickets.",
            "5. LLM — local GPU or cloud API receives system rules, retrieved chunks, "
            "ERP JSON, and chat history, then writes the final answer.",
        ],
    )

    doc.add_heading("3.3  What embeddings are (for non-technical readers)", level=2)
    add_callout(
        doc,
        "Simple analogy",
        "An embedding turns a sentence into a list of numbers that capture its meaning. "
        "Similar sentences get similar numbers. When you ask about pending orders, the system "
        "finds document chunks whose numbers are closest — even if the exact words differ.",
        FILL_NOTE,
        BORDER_BLUE,
    )
    add_body(
        doc,
        "Important: Groq (used for chat) does not provide embeddings. Embeddings use a "
        "separate OpenAI-compatible API key. Chat can run locally on GPU while search "
        "indexing uses a lightweight cloud embedding service.",
    )
    doc.add_page_break()

    add_part_banner(
        doc,
        "Part 4 — Local GPU vs Cloud API (No GPU)",
        "Same RAG pipeline and UI — only the final writing step changes.",
        "F3E8FF",
        BORDER_PURPLE,
    )
    add_body(
        doc,
        "Nexus Support supports both deployment models. The same RAG pipeline, ERP "
        "integration, and UI work in either mode.",
    )
    add_comparison_table(doc)

    doc.add_heading("4.1  Local GPU path (what you see in the screenshots)", level=2)
    add_bullets(
        doc,
        [
            "Model: Qwen2.5-7B-Instruct (GGUF Q4_K_M) via llama.cpp in-process.",
            "No Ollama required — model loads directly from the models folder.",
            "Status bar shows: Groq on, Native GPU, Qwen2.5-7B-Instruct.",
            "Reply tag LLM LOCAL confirms the answer came from on-premises inference.",
            "Setup: scripts/setup_local_llm.ps1 and scripts/download_gguf.py",
        ],
    )

    doc.add_heading("4.2  Cloud API only path (no GPU)", level=2)
    add_bullets(
        doc,
        [
            "Set LLM_ORDER=api (or leave GPU model unconfigured).",
            "Chat uses Groq llama-3.1-8b-instant (free tier available).",
            "RAG, ERP, knowledge ingestion, and learning — unchanged.",
            "Ideal for Vercel serverless, laptops without NVIDIA GPU, and quick demos.",
            "Reply tag shows LLM API instead of LLM LOCAL.",
        ],
    )

    doc.add_heading("4.3  Recommended production pattern", level=2)
    add_body(
        doc,
        "Many clients use Auto mode: local GPU for sensitive or high-volume chat, cloud "
        "API as fallback during maintenance or burst traffic. Embeddings and KB learning "
        "expansion can stay on the hosted API while customer-facing answers stay on GPU.",
    )
    doc.add_page_break()

    doc.add_heading("Part 5 — User Roles at a Glance", level=1)
    add_styled_table(
        doc,
        ["Role", "Login example", "ERP data scope", "Knowledge panel"],
        [
            ["Customer", "cust1 / Alex", "Own account only", "Hidden"],
            ["Agent", "agent / Morgan", "Support tickets scope", "Visible"],
            ["Admin", "admin / Admin", "All customers", "Visible"],
        ],
    )

    doc.add_heading("Part 6 — Technology Stack Summary", level=1)
    add_bullets(
        doc,
        [
            "Backend: FastAPI (Python) — /chat, /auth, /knowledge, /erp routes.",
            "Database: Neon Postgres — ERP tables plus pgvector knowledge_chunks.",
            "Embeddings: OpenAI text-embedding-3-small (1536-dim vectors).",
            "Local LLM: llama.cpp plus Qwen2.5-7B-Instruct GGUF on NVIDIA GPU.",
            "Cloud LLM: Groq OpenAI-compatible API (llama-3.1-8b-instant).",
            "Frontend: Single-page web UI (static/index.html) — dark enterprise theme.",
            "Deploy: Local uvicorn, or Vercel serverless via api/index.py.",
        ],
    )

    doc.add_heading("Appendix — Demo Accounts", level=1)
    add_bullets(
        doc,
        [
            "admin / Admin — full ERP and knowledge admin.",
            "agent / Morgan — support agent with knowledge panel.",
            "cust1 / Alex — customer id 1.",
            "cust2 through cust8 / first name — additional customer personas.",
        ],
    )
    add_body(
        doc,
        "Start locally: powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1 "
        "then open http://localhost:8000/",
    )

    footer = doc.add_table(rows=1, cols=1)
    _set_table_width_full(footer)
    fc = footer.rows[0].cells[0]
    _set_cell_shading(fc, FILL_NAVY)
    _set_cell_borders(fc, color=BORDER_PURPLE, size=6)
    _set_cell_margins(fc, top=80, bottom=80, left=120, right=120)
    fp = fc.paragraphs[0]
    _tight_para(fp, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_run(
        fp,
        f"End of document  |  Confidential  |  Live system screenshots  |  {date.today():%B %Y}",
        color=RGBColor(0xCB, 0xD5, 0xE1),
        size=9,
    )

    _finalize_document(doc)
    doc.save(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
