"""
generate_mcp_report.py — Generates ClaimCopilot MCP Audit Report as PDF.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import PageBreak
import datetime

OUTPUT_PATH = r"c:\Users\T.Lok Avinashh\Desktop\ClaimCopilot_MCP_Audit_Report.pdf"

# ── Colour palette ─────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#1A237E")
TEAL      = colors.HexColor("#00796B")
RED       = colors.HexColor("#C62828")
AMBER     = colors.HexColor("#F57F17")
GREEN     = colors.HexColor("#2E7D32")
LIGHT_BG  = colors.HexColor("#F5F5F5")
LIGHT_TEAL= colors.HexColor("#E0F2F1")
LIGHT_RED = colors.HexColor("#FFEBEE")
LIGHT_AMB = colors.HexColor("#FFFDE7")
WHITE     = colors.white
DARK_TEXT = colors.HexColor("#212121")
MID_TEXT  = colors.HexColor("#424242")

# ── Styles ─────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE_STYLE = S("Title",
    fontName="Helvetica-Bold", fontSize=26, textColor=WHITE,
    spaceAfter=4, leading=32, alignment=TA_CENTER)

SUBTITLE_STYLE = S("Subtitle",
    fontName="Helvetica", fontSize=13, textColor=colors.HexColor("#B2EBF2"),
    spaceAfter=2, alignment=TA_CENTER)

VERDICT_STYLE = S("Verdict",
    fontName="Helvetica-Bold", fontSize=14, textColor=AMBER,
    spaceAfter=4, alignment=TA_CENTER)

H1 = S("H1",
    fontName="Helvetica-Bold", fontSize=15, textColor=NAVY,
    spaceBefore=14, spaceAfter=6, leading=20,
    borderPad=4)

H2 = S("H2",
    fontName="Helvetica-Bold", fontSize=12, textColor=TEAL,
    spaceBefore=10, spaceAfter=4)

BODY = S("Body",
    fontName="Helvetica", fontSize=9.5, textColor=DARK_TEXT,
    spaceAfter=4, leading=14)

CODE = S("Code",
    fontName="Courier", fontSize=8, textColor=colors.HexColor("#37474F"),
    spaceAfter=3, leading=12, backColor=colors.HexColor("#ECEFF1"),
    leftIndent=10, borderPad=4)

CAPTION = S("Caption",
    fontName="Helvetica-Oblique", fontSize=8, textColor=MID_TEXT,
    spaceAfter=2)

# ── Helpers ────────────────────────────────────────────────────────────────────

def hr(color=NAVY, thickness=1.5, width="100%"):
    return HRFlowable(width=width, thickness=thickness, color=color, spaceAfter=8, spaceBefore=4)

def section_header(text):
    return [
        Spacer(1, 0.3*cm),
        Paragraph(text, H1),
        hr(TEAL, 1),
    ]

def sub_header(text):
    return Paragraph(text, H2)

def body(text):
    return Paragraph(text, BODY)

def code_block(text):
    return Paragraph(text.replace("\n", "<br/>").replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;"), CODE)

def table_with_style(data, col_widths, header_bg=NAVY, header_fg=WHITE, stripe=LIGHT_BG, alternate=WHITE):
    style = [
        ("BACKGROUND",  (0,0), (-1,0), header_bg),
        ("TEXTCOLOR",   (0,0), (-1,0), header_fg),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 9),
        ("ALIGN",       (0,0), (-1,0), "LEFT"),
        ("BOTTOMPADDING",(0,0),(-1,0), 7),
        ("TOPPADDING",  (0,0), (-1,0), 7),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 8.5),
        ("TOPPADDING",  (0,1), (-1,-1), 5),
        ("BOTTOMPADDING",(0,1),(-1,-1), 5),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#CFD8DC")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[stripe, alternate]),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("WORDWRAP",    (0,0), (-1,-1), True),
    ]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

def score_table(rows):
    """Scorecard table with coloured Score column."""
    header = [Paragraph("<b>MCP Feature</b>", BODY), Paragraph("<b>Status</b>", BODY), Paragraph("<b>Score</b>", BODY)]
    data = [header]
    for feat, status, score in rows:
        val = int(score.split("/")[0])
        color = GREEN if val >= 8 else (AMBER if val >= 5 else RED)
        score_p = Paragraph(f'<font color="#{color.hexval()[2:]}"><b>{score}</b></font>', BODY)
        data.append([Paragraph(feat, BODY), Paragraph(status, BODY), score_p])
    # totals row
    data.append([
        Paragraph("<b>Overall Total</b>", BODY),
        Paragraph("", BODY),
        Paragraph('<b>51 / 100</b>', BODY)
    ])
    t = Table(data, colWidths=[4.5*cm, 9.5*cm, 2.5*cm], repeatRows=1)
    style = [
        ("BACKGROUND",  (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#CFD8DC")),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[LIGHT_BG, WHITE]),
        ("BACKGROUND",  (0,-1), (-1,-1), colors.HexColor("#E3F2FD")),
        ("FONTNAME",    (0,-1), (-1,-1), "Helvetica-Bold"),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
    ]
    t.setStyle(TableStyle(style))
    return t

# ── Page template with header/footer ──────────────────────────────────────────

def on_first_page(canvas, doc):
    w, h = A4
    # Navy header banner
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 5.5*cm, w, 5.5*cm, fill=1, stroke=0)
    # Teal accent bar
    canvas.setFillColor(TEAL)
    canvas.rect(0, h - 5.7*cm, w, 0.22*cm, fill=1, stroke=0)
    # Date
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#80CBC4"))
    canvas.drawRightString(w - 1.5*cm, h - 0.5*cm,
                           datetime.datetime.now().strftime("Generated: %d %B %Y"))

def on_later_pages(canvas, doc):
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 1*cm, w, 1*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(WHITE)
    canvas.drawString(1.5*cm, h - 0.65*cm, "ClaimCopilot  •  MCP Audit Report")
    canvas.drawRightString(w - 1.5*cm, h - 0.65*cm, f"Page {doc.page}")
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0.7*cm, w, 0.15*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_TEXT)
    canvas.drawCentredString(w/2, 0.3*cm, "Confidential — Internal Audit Document")


# ── Build document ─────────────────────────────────────────────────────────────

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=6.5*cm, bottomMargin=2*cm,
        title="ClaimCopilot MCP Audit Report",
        author="Antigravity AI",
    )

    story = []

    # ─── Cover content (sits inside the banner space via first-page template) ──
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("ClaimCopilot", TITLE_STYLE))
    story.append(Paragraph("Model Context Protocol (MCP) — Full Audit Report", SUBTITLE_STYLE))
    story.append(Paragraph("Verdict: Solid Prototype — Not Yet Perfect  •  Score: 51 / 100", VERDICT_STYLE))
    story.append(Spacer(1, 0.6*cm))

    # ─── Section 1: What You've Done Right ────────────────────────────────────
    story += section_header("1.  What You've Done Right ✅")
    story.append(body(
        "The project demonstrates a strong architectural understanding of MCP conventions. "
        "The following areas are implemented correctly and reflect production-level thinking:"
    ))
    story.append(Spacer(1, 0.2*cm))

    good_data = [
        ["Area", "Assessment"],
        ["MCP Server", "Uses FastMCP from the official mcp[cli] package — correct foundation"],
        ["Tool Registration", "2 tools registered with clear names and descriptions"],
        ["Lazy Imports", "Sentence-transformers loaded lazily — prevents 60-sec init timeout"],
        ["Stdio Transport", "server.run() uses stdio — correct for Claude Desktop"],
        ["5-Tool Pipeline", "Clean: File Read → Extract → RAG+Structured (parallel) → Validate"],
        ["Pydantic v2 Schemas", "All 8 data models strongly typed with validators"],
        ["Error Propagation", "Typed exceptions bubble correctly through the full pipeline"],
        ["Parallel Execution", "Tools 3 & 4 run concurrently via ThreadPoolExecutor — efficient"],
        ["Archival System", "Claims and JSON results auto-saved to Past records/ directory"],
        ["Unit Tests", "One test file per tool — good structural coverage"],
        ["Logging", "stderr logging with timestamps — correct channel for MCP"],
    ]
    story.append(table_with_style(
        [[Paragraph(c, BODY) for c in row] for row in good_data],
        [5*cm, 11.5*cm], header_bg=TEAL
    ))
    story.append(Spacer(1, 0.4*cm))

    # ─── Section 2: Critical MCP Gaps ─────────────────────────────────────────
    story += section_header("2.  MCP Protocol Gaps ❌")

    story.append(sub_header("🔴 Critical — Must Fix (Protocol Violations)"))
    story.append(Spacer(1, 0.2*cm))

    crit_data = [
        ["#", "Issue", "Why It Matters"],
        ["1", "No @server.resource() definitions",
         "A perfect MCP exposes data as resources (past_records://list, policy://POL-001). Without this, Claude cannot browse your records passively — only actively invoke tools."],
        ["2", "No @server.prompt() templates",
         "MCP has a prompt registry. Without it, Claude Desktop cannot offer slash-command shortcuts for evaluate_claim, query_policy, etc."],
        ["3", "process_medical_claim takes a file path string",
         "Claude Desktop cannot provide local file paths. This tool must accept file_base64 (base64-encoded content) or work via MCP resources."],
        ["4", "server.run() with no transport argument",
         "Should be server.run(transport='stdio'). The silent default may break on newer MCP SDK versions."],
        ["5", "No MCP-layer input schema validation",
         "If Claude sends malformed arguments, errors are cryptic Python tracebacks rather than clean MCP error responses."],
    ]
    style_crit = [
        ("BACKGROUND",  (0,0), (-1,0), RED),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#FFCDD2")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT_RED, WHITE]),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTNAME",    (0,1), (0,-1), "Helvetica-Bold"),
    ]
    t = Table(
        [[Paragraph(c, BODY) for c in row] for row in crit_data],
        colWidths=[0.6*cm, 5.5*cm, 10.4*cm], repeatRows=1
    )
    t.setStyle(TableStyle(style_crit))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    story.append(sub_header("🟡 Moderate — Should Fix"))
    story.append(Spacer(1, 0.2*cm))

    mod_data = [
        ["#", "Issue", "Why It Matters"],
        ["6", "No claude_desktop_config.json template",
         "Users must manually create the Claude Desktop config. Should ship as a template in the repo root."],
        ["7", "Hardcoded OCR dummy data (tool1_file_reader.py lines 64/67/122)",
         "Falls back to a fake 'Rahul Sharma' claim when OCR fails. Silently poisons production results."],
        ["8", "Only 5 rows in policies.csv",
         "The structured retriever is meaningless at scale. Needs at minimum 50 seeded records."],
        ["9", "Chat router imports _load_vectorstore directly",
         "A private function called across module boundaries — breaks encapsulation and is fragile."],
        ["10", "CORS origins: '*' ships to production",
         "Fine for dev, dangerous for production. Deployment guide mentions fixing it but code never does."],
    ]
    style_mod = [
        ("BACKGROUND",  (0,0), (-1,0), AMBER),
        ("TEXTCOLOR",   (0,0), (-1,0), DARK_TEXT),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#FFF9C4")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT_AMB, WHITE]),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTNAME",    (0,1), (0,-1), "Helvetica-Bold"),
    ]
    t = Table(
        [[Paragraph(c, BODY) for c in row] for row in mod_data],
        colWidths=[0.6*cm, 5.5*cm, 10.4*cm], repeatRows=1
    )
    t.setStyle(TableStyle(style_mod))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    story.append(sub_header("🟢 Minor — Nice to Fix"))
    story.append(Spacer(1, 0.2*cm))
    minor_data = [
        ["#", "Issue"],
        ["11", "No rate limiting on Flask API — easy to abuse the expensive AI pipeline."],
        ["12", "No auth on /claims/process — unauthenticated access to the full pipeline."],
        ["13", "pip_out.txt committed to git — build artifacts shouldn't be in version control."],
        ["14", "No MCP integration test — tools are unit-tested but the handshake is never tested end-to-end."],
    ]
    t = Table(
        [[Paragraph(c, BODY) for c in row] for row in minor_data],
        colWidths=[0.6*cm, 16*cm], repeatRows=1
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), GREEN),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#C8E6C9")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#F1F8E9"), WHITE]),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
    ]))
    story.append(t)

    # ─── Section 3: Addons ─────────────────────────────────────────────────────
    story += section_header("3.  Addons to Make It a Perfect MCP 🚀")

    story.append(sub_header("Priority 1 — Protocol Completeness (Must Have)"))
    story.append(Spacer(1, 0.15*cm))

    addons_p1 = [
        ("Addon 1 — MCP Resources", [
            "Add @server.resource() definitions to mcp_server.py so Claude can read",
            "data without invoking a tool:",
            "",
            '@server.resource("past_records://list")',
            "def list_past_records() -> str:",
            '    return "\\n".join(d.name for d in PAST_RECORDS_DIR.iterdir() if d.is_dir())',
            "",
            '@server.resource("past_records://{record_id}/result")',
            "def get_past_record(record_id: str) -> str:",
            "    # finds the matching folder and returns result.json",
            "",
            '@server.resource("policy://{policy_id}")',
            "def get_policy(policy_id: str) -> str:",
            "    # looks up policies.csv and returns the row as JSON",
        ]),
        ("Addon 2 — MCP Prompt Templates", [
            "Add @server.prompt() registrations for Claude Desktop slash-commands:",
            "",
            '@server.prompt("evaluate_claim")',
            "def evaluate_claim_prompt(file_path: str) -> list:",
            '    return [{"role": "user", "content": f"Process this claim: {file_path}"}]',
            "",
            '@server.prompt("query_policy")',
            "def query_policy_prompt(treatment: str, plan: str) -> list:",
            '    return [{"role":"user","content":f"Policy on \'{treatment}\' for \'{plan}\' plan?"}]',
            "",
            '@server.prompt("review_past_claim")',
            "def review_past_claim_prompt(record_id: str) -> list:",
            '    return [{"role": "user", "content": f"Summarise past claim: {record_id}"}]',
        ]),
        ("Addon 3 — Fix server.run() Transport", [
            "Change the last line of mcp_server.py from:",
            "    server.run()",
            "To:",
            '    server.run(transport="stdio")',
        ]),
        ("Addon 4 — Base64 File Input for process_medical_claim", [
            "Add file_base64 and file_name parameters so Claude Desktop can pass",
            "file content directly without needing a local path:",
            "",
            "def process_claim_tool(",
            '    file_path: str = "",',
            '    file_base64: str = "",',
            '    file_name: str = "upload.pdf"',
            ") -> dict:",
            "    if file_base64:",
            "        tmp = Path(tempfile.mktemp(suffix=Path(file_name).suffix))",
            "        tmp.write_bytes(base64.b64decode(file_base64))",
            "        file_path = str(tmp)",
            "    return run_pipeline(file_path)",
        ]),
    ]

    for title, lines in addons_p1:
        story.append(KeepTogether([
            sub_header(title),
            code_block("\n".join(lines)),
            Spacer(1, 0.2*cm),
        ]))

    story.append(sub_header("Priority 2 — Robustness (Should Have)"))
    story.append(Spacer(1, 0.15*cm))

    p2_data = [
        ["Addon", "Description"],
        ["5 — claude_desktop_config.json",
         'Ship a template in repo root:\n{\n  "mcpServers": {\n    "claimcopilot": {\n      "command": "python",\n      "args": ["C:/PATH/backend/mcp_server.py"],\n      "env": { "OPENROUTER_API_KEY": "sk-or-..." }\n    }\n  }\n}'],
        ["6 — Remove hardcoded OCR dummy",
         "Replace every 'PATIENT NAME: Rahul Sharma...' string in tool1_file_reader.py with: raise RuntimeError('OCR failed — no text could be extracted')"],
        ["7 — tool6_claim_summarizer",
         "New MCP tool: takes FinalResponse dict → returns human-readable plain-text report for claims officers using the LLM."],
        ["8 — tool7_batch_processor",
         "New MCP tool: accepts a list of file paths/base64 blobs → processes all concurrently with ThreadPoolExecutor → returns list of results."],
        ["9 — Expand policies.csv",
         "Add minimum 50 policy records across Gold, Silver, Bronze tiers with varied coverage limits, waiting periods, and statuses."],
    ]
    story.append(table_with_style(
        [[Paragraph(c.replace("\n","<br/>"), BODY) for c in row] for row in p2_data],
        [4.5*cm, 12*cm], header_bg=TEAL
    ))
    story.append(Spacer(1, 0.4*cm))

    story.append(sub_header("Priority 3 — Production Grade (Nice to Have)"))
    story.append(Spacer(1, 0.15*cm))

    p3_data = [
        ["Addon", "Description"],
        ["10 — Replace CSV/JSON with SQLite",
         "Single persistent DB for policies, coverage_rules, and claim_archive eliminates pandas CSV reads on every request."],
        ["11 — Flask-Limiter",
         "Add rate limiting (30 req/min default) to prevent the expensive AI+OCR pipeline from being abused."],
        ["12 — MCP health_check tool",
         "New tool that verifies vector store, LLM connectivity, and CSV data at startup — returns {status, vector_store, llm} dict."],
        ["13 — Structured JSON logging",
         "Replace all print() calls with logging module + JSON formatter for production-grade observability."],
        ["14 — MCP progress notifications",
         "Emit intermediate step completions as MCP progress events during the 30–60 second pipeline run so Claude Desktop shows a progress indicator."],
        ["15 — MCP integration test",
         "Add tests/test_mcp_server.py: spawn mcp_server.py as subprocess, send initialize + tools/list over stdio, assert both tools are returned correctly."],
    ]
    story.append(table_with_style(
        [[Paragraph(c, BODY) for c in row] for row in p3_data],
        [4.5*cm, 12*cm], header_bg=NAVY
    ))

    # ─── Section 4: Scorecard ──────────────────────────────────────────────────
    story += section_header("4.  MCP Compliance Scorecard 📊")

    score_rows = [
        ("Tools", "✅ 2 tools registered with names/descriptions", "8/10"),
        ("Resources", "❌ No @server.resource() definitions at all", "0/10"),
        ("Prompts", "❌ No @server.prompt() templates at all", "0/10"),
        ("Stdio Transport", "✅ Correct stdio channel", "10/10"),
        ("Schema Validation", "⚠️ Pydantic only — no MCP-layer validation", "5/10"),
        ("Error Handling", "✅ Good try/except throughout pipeline", "8/10"),
        ("Observability", "⚠️ Logging exists but no structured format", "5/10"),
        ("Documentation", "⚠️ README exists but no Claude Desktop config", "5/10"),
        ("Test Coverage", "⚠️ Unit tests per tool — no MCP integration test", "6/10"),
        ("Production Ready", "⚠️ No auth, no rate limit, hardcoded fallbacks", "4/10"),
    ]
    story.append(score_table(score_rows))
    story.append(Spacer(1, 0.4*cm))

    # ─── Section 5: Minimum 6 changes ─────────────────────────────────────────
    story += section_header("5.  Minimum 6 Changes for a 'Perfect MCP' Label 🎯")
    story.append(body(
        "Complete these 6 items in order and your score jumps from <b>51 → ~85 / 100</b>. "
        "These are the foundational protocol requirements — everything else is polish."
    ))
    story.append(Spacer(1, 0.2*cm))

    min6_data = [
        ["#", "Change", "Expected Score Gain"],
        ["1", "Add @server.resource() definitions (past records list, individual records, policies)", "+15"],
        ["2", "Add @server.prompt() templates (evaluate_claim, query_policy, review_past_claim)", "+10"],
        ["3", 'Fix server.run(transport="stdio")', "+4"],
        ["4", "Add base64 file input to process_medical_claim", "+6"],
        ["5", "Ship claude_desktop_config.json template in repo root", "+4"],
        ["6", "Remove hardcoded OCR dummy data — raise proper errors instead", "+5"],
    ]
    t = Table(
        [[Paragraph(c, BODY) for c in row] for row in min6_data],
        colWidths=[0.6*cm, 13.5*cm, 2.4*cm], repeatRows=1
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#CFD8DC")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LIGHT_TEAL, WHITE]),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTNAME",    (0,1), (0,-1), "Helvetica-Bold"),
        ("ALIGN",       (2,1), (2,-1), "CENTER"),
        ("TEXTCOLOR",   (2,1), (2,-1), GREEN),
        ("FONTNAME",    (2,1), (2,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(body(
        "<i>Report generated by Antigravity AI on "
        + datetime.datetime.now().strftime("%d %B %Y at %H:%M")
        + ". For internal use only.</i>"
    ))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    print(f"[SUCCESS] PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
