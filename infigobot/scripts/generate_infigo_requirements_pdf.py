"""Generate Infigo team implementation requirements PDF for client handoff."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Infigo_Team_Implementation_Requirements.pdf"


class HandoffPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def _width(self) -> float:
        return self.epw

    def section_title(self, title: str) -> None:
        self.set_x(self.l_margin)
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 64, 120)
        self.multi_cell(self._width(), 8, title)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def sub_title(self, title: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(self._width(), 7, title)
        self.ln(1)

    def body(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(self._width(), 5.5, text)
        self.ln(2)

    def bullet(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(self._width(), 5.5, f"  -  {text}")

    def code_block(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_fill_color(245, 245, 245)
        self.set_font("Courier", "", 9)
        w = self._width()
        for line in text.strip().splitlines():
            self.multi_cell(w, 5, "  " + line, fill=True)
        self.ln(3)
        self.set_font("Helvetica", "", 10)


def build() -> Path:
    pdf = HandoffPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    w = pdf.epw
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(w, 10, "AI Chat Widget")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 64, 120)
    pdf.multi_cell(w, 8, "Implementation Requirements - Infigo Solutions")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        w,
        5.5,
        "This document describes what the Infigo development team must implement on the "
        "public React website. The chat API is hosted separately on Vercel; no database, "
        "SSH, or Groq/OpenAI keys are required on Infigo's side.",
    )
    pdf.ln(2)

    pdf.section_title("What you will receive from us (separately)")
    pdf.bullet("API base URL - your deployed infigobot Vercel URL")
    pdf.bullet("Public chat key - browser-safe key (PUBLIC_CHAT_API_KEY); not the LLM key")
    pdf.bullet(
        "Reference repository: https://github.com/sameerasif189/infigobot "
        "(read-only; copy files listed below)"
    )
    pdf.ln(2)

    pdf.section_title("Step 1 - Add content.json (bot knowledge)")
    pdf.body(
        "Create public/content.json in the Infigo React project. Copy the template from our repo, "
        "then replace placeholder text with approved marketing copy (services, FAQs, contact, process)."
    )
    pdf.sub_title("Template source")
    pdf.bullet("File: docs/examples/public-content.json")
    pdf.bullet(
        "GitHub: https://github.com/sameerasif189/infigobot/blob/main/docs/examples/public-content.json"
    )
    pdf.sub_title("Rules")
    pdf.bullet("Do not put API secrets in content.json - only public marketing text.")
    pdf.bullet("Commit and deploy the website as usual.")
    pdf.sub_title("Acceptance test")
    pdf.body("After deploy, open in a browser:")
    pdf.code_block("https://infigosolutions.com/content.json")
    pdf.body("Must return JSON (not 404, not the HTML homepage).")

    pdf.section_title("Step 2 - Add the chat widget file")
    pdf.body("Copy the React widget component into your project:")
    pdf.code_block(
        "From:  docs/examples/InfigoChatWidget.tsx\n"
        "To:    src/components/InfigoChatWidget.tsx"
    )
    pdf.body(
        "Path may vary (e.g. src/components/chat/). Adjust the import path in Step 4. "
        "No extra npm packages required - React and fetch only."
    )

    pdf.section_title("Step 3 - Frontend environment variables")
    pdf.body(
        "Add to .env or .env.production (do not commit secrets if the repo is public). "
        "Use the API URL and public chat key we send you."
    )
    pdf.sub_title("Vite projects")
    pdf.code_block(
        "VITE_INFIGO_CHAT_API_URL=https://YOUR-API-URL.vercel.app\n"
        "VITE_INFIGO_CHAT_API_KEY=VALUE_WE_SEND_YOU"
    )
    pdf.sub_title("Create React App projects")
    pdf.code_block(
        "REACT_APP_INFIGO_CHAT_API_URL=https://YOUR-API-URL.vercel.app\n"
        "REACT_APP_INFIGO_CHAT_API_KEY=VALUE_WE_SEND_YOU"
    )
    pdf.body(
        "The frontend key must match PUBLIC_CHAT_API_KEY on the API exactly. "
        "Use only one prefix (VITE_ or REACT_APP_), depending on your build tool."
    )

    pdf.add_page()
    pdf.section_title("Step 4 - Show widget on main page (all routes)")
    pdf.body("Mount the widget once in the root layout (e.g. src/App.tsx):")
    pdf.code_block(
        'import { InfigoChatWidget } from "./components/InfigoChatWidget";\n\n'
        "export default function App() {\n"
        "  return (\n"
        "    <>\n"
        "      {/* existing routes / homepage */}\n"
        "      <InfigoChatWidget />\n"
        "    </>\n"
        "  );\n"
        "}"
    )
    pdf.body("Build and deploy. A chat button should appear bottom-right on the homepage and inner pages.")

    pdf.section_title("Step 5 - Staging (optional)")
    pdf.body(
        "If you test on a staging domain (e.g. https://staging.infigosolutions.com), send us the "
        "exact URL. We will add it to CORS on the API and redeploy:"
    )
    pdf.code_block(
        "CORS_ALLOWED_ORIGINS=https://infigosolutions.com,https://www.infigosolutions.com,"
        "https://staging.infigosolutions.com"
    )
    pdf.body("Staging must also serve content.json, e.g. https://staging.infigosolutions.com/content.json")

    pdf.section_title("Alternative - Script embed (no new React file)")
    pdf.body("Add to public/index.html before </body> if you prefer not to add a component:")
    pdf.code_block(
        '<script src="https://YOUR-API-URL.vercel.app/static/infigo-embed.js"\n'
        '  data-api-url="https://YOUR-API-URL.vercel.app"\n'
        '  data-api-key="VALUE_WE_SEND_YOU"\n'
        '  data-title="Infigo Assistant"\n'
        '  data-color="#6366f1"\n'
        "  defer></script>"
    )

    pdf.section_title("Acceptance checklist")
    checks = [
        "https://infigosolutions.com/content.json returns valid JSON",
        "Chat button visible on homepage and inner pages",
        "Sending a message returns a reply (no CORS or 401 errors)",
        'Question "How long does an MVP take?" answered from your JSON',
        "Production env vars set; secrets not in public git",
    ]
    for item in checks:
        pdf.bullet(f"[ ] {item}")
    pdf.ln(4)

    pdf.section_title("Troubleshooting")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(55, 6, "Symptom", border=1)
    pdf.cell(60, 6, "Likely cause", border=1)
    pdf.cell(75, 6, "Fix", border=1, ln=1)
    pdf.set_font("Helvetica", "", 8)
    rows = [
        ("Could not reach server", "Wrong API URL / CORS", "Check env URL; tell us staging domain"),
        ("HTTP 401", "Key mismatch", "Frontend key must match PUBLIC_CHAT_API_KEY"),
        ("Generic answers", "content.json missing", "Deploy public/content.json"),
        ("No chat button", "Widget not mounted", "Add <InfigoChatWidget /> to App.tsx"),
    ]
    for a, b, c in rows:
        pdf.cell(55, 6, a, border=1)
        pdf.cell(60, 6, b, border=1)
        pdf.cell(75, 6, c, border=1, ln=1)

    pdf.ln(6)
    pdf.section_title("What Infigo does not need")
    pdf.bullet("Neon / Postgres / database on your side")
    pdf.bullet("Groq or OpenAI API keys")
    pdf.bullet("Changes to existing contact forms or backend APIs")
    pdf.bullet("Meta / WhatsApp integration")

    pdf.ln(4)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        pdf.epw,
        5,
        "Questions about API URL, keys, or CORS: contact the team that deployed the infigobot API. "
        "Content accuracy in content.json: Infigo marketing / product owner.",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
