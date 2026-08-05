#!/usr/bin/env python3
"""
Erstellt das Pinterest-Wachstums-Workbook als PDF
mit Branding-Farben (Smaragdgrün/Gelb) und sauberer Typografie.
"""
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------- Farben (Pinterest-Branding) ----------
EMERALD = HexColor("#0E5A43")
EMERALD_DARK = HexColor("#0A4634")
EMERALD_SOFT = HexColor("#EAF4EF")
ANTHRACITE = HexColor("#2E2E33")
YELLOW = HexColor("#FFB300")
CREAM = HexColor("#F5F8F6")
GREY = HexColor("#555555")
WHITE = HexColor("#FFFFFF")

# ---------- Fonts ----------
import os
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuBold", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuOblique", os.path.join(FONT_DIR, "DejaVuSerif.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVuBold",
                              italic="DejaVuOblique", boldItalic="DejaVuBold")

# ---------- Styles ----------
def st(name, **kw):
    base = dict(fontName="DejaVu", fontSize=10, leading=15, textColor=ANTHRACITE,
                alignment=TA_LEFT, spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(name, **base)

S = {
    "title":    st("title", fontName="DejaVuBold", fontSize=24, leading=30, textColor=WHITE, alignment=TA_CENTER),
    "subtitle": st("subtitle", fontSize=12, leading=17, textColor=CREAM, alignment=TA_CENTER),
    "h1":       st("h1", fontName="DejaVuBold", fontSize=15, leading=20, textColor=EMERALD, spaceBefore=16, spaceAfter=8),
    "h2":       st("h2", fontName="DejaVuBold", fontSize=12, leading=17, textColor=EMERALD_DARK, spaceBefore=12, spaceAfter=6),
    "h3":       st("h3", fontName="DejaVuBold", fontSize=10.5, leading=15, textColor=ANTHRACITE, spaceBefore=8, spaceAfter=4),
    "body":     st("body", spaceAfter=8),
    "bullet":   st("bullet", leftIndent=14, bulletIndent=4, spaceAfter=4),
    "check":    st("check", leftIndent=16, bulletIndent=4, spaceAfter=4),
    "code":     st("code", fontName="DejaVu", fontSize=9, leading=13, textColor=EMERALD_DARK,
                   backColor=EMERALD_SOFT, leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=8),
    "table":    st("table", fontSize=9, leading=13),
    "small":    st("small", fontSize=8.5, leading=12, textColor=GREY),
}


def fmt(text):
    """Formatiert Markdown-Inline (**bold**, `code`) für Paragraph-HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font face="DejaVu" color="#0A4634"><b>\1</b></font>', text)
    return text

# ---------- Markdown-Mini-Parser (unsere Datei) ----------
def md_to_flowables(md_text):
    flow = []
    lines = md_text.split("\n")
    i = 0
    in_code = False
    code_buf = []
    table_rows = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        header = table_rows[0]
        data = [r for r in table_rows[1:] if r]
        t = Table([header] + data, colWidths=None, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), EMERALD),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVuBold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, EMERALD_SOFT]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        flow.append(t)
        flow.append(Spacer(1, 8))
        table_rows = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Codeblock
        if stripped.startswith("```"):
            if in_code:
                flow.append(Paragraph("<br/>".join(code_buf), S["code"]))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(stripped)
            i += 1
            continue

        # Tabellen
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                table_rows = []  # Trennzeile ignorieren
            else:
                table_rows.append([fmt(c) for c in cells])
            i += 1
            continue
        else:
            flush_table()

        # Überschriften
        if stripped.startswith("# "):
            flow.append(Paragraph(fmt(stripped[2:]), S["h1"]))
        elif stripped.startswith("## "):
            flow.append(Paragraph(fmt(stripped[3:]), S["h2"]))
        elif stripped.startswith("### "):
            flow.append(Paragraph(fmt(stripped[4:]), S["h3"]))
        # Checkliste
        elif stripped.startswith("- [ ]"):
            txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped[5:].strip())
            flow.append(Paragraph("☐ " + txt, S["check"]))
        # Liste
        elif stripped.startswith("- ") or stripped.startswith("* "):
            txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped[2:].strip())
            flow.append(Paragraph("• " + txt, S["bullet"]))
        elif stripped.startswith("1. ") or re.match(r"^\d+\.\s", stripped):
            flow.append(Paragraph("• " + fmt(re.sub(r"^\d+\.\s", "", stripped)), S["bullet"]))
        # Trennlinie
        elif re.fullmatch(r"[-*_]{3,}", stripped):
            flow.append(Spacer(1, 4))
        # leer
        elif not stripped:
            pass
        # normaler Text
        else:
            flow.append(Paragraph(fmt(stripped), S["body"]))
        i += 1

    flush_table()
    return flow

# ---------- PDF-Dokument ----------
def build_pdf(md_path, out_path):
    md_text = open(md_path, encoding="utf-8").read()

    # Titel- und Subtitelzeilen aus Markdown ziehen (erste "# " und danach)
    lines = md_text.split("\n")
    title = "Pinterest-Wachstums-Workbook"
    subtitle = "FranksFinanzcheck"
    for ln in lines:
        if ln.startswith("# "):
            title = ln[2:].strip()
        elif ln.startswith("**Ziel:**"):
            subtitle = ln.replace("**", "").strip()
            break

    doc = BaseDocTemplate(out_path, pagesize=A4,
                          leftMargin=18*mm, rightMargin=18*mm,
                          topMargin=16*mm, bottomMargin=16*mm,
                          title="Pinterest-Wachstums-Workbook – FranksFinanzcheck",
                          author="FranksFinanzcheck")

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")

    def header_footer(canvas, doc_):
        canvas.saveState()
        # Kopfzeile
        canvas.setFillColor(EMERALD)
        canvas.rect(0, A4[1] - 12*mm, A4[0], 12*mm, stroke=0, fill=1)
        canvas.setFillColor(YELLOW)
        canvas.rect(0, A4[1] - 12*mm, 4*mm, 12*mm, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont("DejaVuBold", 9)
        canvas.drawString(18*mm, A4[1] - 8.5*mm, "Pinterest-Wachstums-Workbook")
        canvas.setFont("DejaVu", 9)
        canvas.drawRightString(A4[0] - 18*mm, A4[1] - 8.5*mm, "FranksFinanzcheck")
        # Fußzeile
        canvas.setStrokeColor(HexColor("#CCCCCC"))
        canvas.setLineWidth(0.5)
        canvas.line(18*mm, 12*mm, A4[0] - 18*mm, 12*mm)
        canvas.setFillColor(GREY)
        canvas.setFont("DejaVu", 8)
        canvas.drawString(18*mm, 8*mm, "© 2026 FranksFinanzcheck – Pinterest-Wachstums-Workbook")
        canvas.drawRightString(A4[0] - 18*mm, 8*mm, f"Seite {canvas.getPageNumber()}")
        canvas.restoreState()

    template = PageTemplate(id="main", frames=[frame], onPage=header_footer)
    doc.addPageTemplates([template])

    # Titelseite-Elemente
    story = []
    story.append(Spacer(1, 30))
    story.append(Paragraph(title, S["title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("für " + subtitle, S["subtitle"]))
    story.append(Spacer(1, 20))
    # Gelber Trenn-Balken
    t = Table([[""]], colWidths=[60*mm], rowHeights=[3])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), YELLOW)]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Paragraph("Kostenlose Maßnahmen, um deinen Blog über Pinterest bekannter zu machen – "
                           "basierend auf deinem Pinterest-Masterplan (August 2026).", S["body"]))
    story.append(PageBreak())

    # Restlichen Markdown-Inhalt (ohne die erste Titelzeile)
    body_md = "\n".join(lines[1:])
    story.extend(md_to_flowables(body_md))

    doc.build(story)
    print(f"PDF erstellt: {out_path}")

if __name__ == "__main__":
    build_pdf("/home/user/check24-blog/PINTEREST-WACHSTUMS-WORKBOOK.md",
              "/home/user/check24-blog/Pinterest-Wachstums-Workbook.pdf")
