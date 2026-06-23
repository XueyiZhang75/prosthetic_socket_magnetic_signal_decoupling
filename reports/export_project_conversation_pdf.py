from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


HERE = Path(__file__).resolve().parent
MD_PATH = HERE / "PROJECT_CONVERSATION_EXPORT_20260603.md"
PDF_PATH = HERE / "PROJECT_CONVERSATION_EXPORT_20260603.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")


def register_fonts() -> str:
    font_name = "SimHei"
    pdfmetrics.registerFont(TTFont(font_name, str(FONT_PATH)))
    return font_name


def clean_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<font color='#2f5d7c'>\1</font>", text)
    text = text.replace(" <= ", " &lt;= ")
    return text


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    table_lines = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        table_lines.append(lines[i].strip())
        i += 1
    rows = []
    for idx, line in enumerate(table_lines):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if idx == 1 and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        rows.append(cells)
    return rows, i


def make_table(rows: list[list[str]], styles) -> Table:
    col_count = max(len(r) for r in rows)
    normalized = [r + [""] * (col_count - len(r)) for r in rows]
    data = [
        [
            Paragraph(clean_inline(cell), styles["TableCell"])
            for cell in row
        ]
        for row in normalized
    ]
    page_width = A4[0] - 34 * mm
    col_width = page_width / col_count
    table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8c4d0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), styles["TableCell"].fontName),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def build_styles(font_name: str):
    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=font_name,
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324d"),
            spaceAfter=10,
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=16,
            leading=21,
            textColor=colors.HexColor("#17324d"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#264b66"),
            spaceBefore=8,
            spaceAfter=5,
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#365d73"),
            spaceBefore=6,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.6,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.4,
            leading=13,
            leftIndent=12,
        ),
        "Code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName=font_name,
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor("#243746"),
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=7.1,
            leading=9,
        ),
    }
    return styles


def markdown_to_story(text: str, styles) -> list:
    lines = text.splitlines()
    story = []
    i = 0
    bullet_buffer = []
    code_buffer = []
    in_code = False

    def flush_bullets():
        nonlocal bullet_buffer
        if bullet_buffer:
            items = [
                ListItem(Paragraph(clean_inline(item), styles["Bullet"]))
                for item in bullet_buffer
            ]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=16))
            story.append(Spacer(1, 2 * mm))
            bullet_buffer = []

    def flush_code():
        nonlocal code_buffer
        if code_buffer:
            story.append(Preformatted("\n".join(code_buffer), styles["Code"]))
            story.append(Spacer(1, 2 * mm))
            code_buffer = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                in_code = False
                flush_code()
            else:
                flush_bullets()
                in_code = True
            i += 1
            continue

        if in_code:
            code_buffer.append(line)
            i += 1
            continue

        if not stripped:
            flush_bullets()
            i += 1
            continue

        if stripped.startswith("|"):
            flush_bullets()
            rows, next_i = parse_table(lines, i)
            story.append(make_table(rows, styles))
            story.append(Spacer(1, 3 * mm))
            i = next_i
            continue

        if stripped.startswith("- "):
            bullet_buffer.append(stripped[2:].strip())
            i += 1
            continue

        flush_bullets()
        if stripped.startswith("# "):
            story.append(Paragraph(clean_inline(stripped[2:]), styles["Title"]))
            story.append(Spacer(1, 4 * mm))
        elif stripped.startswith("## "):
            title = stripped[3:]
            if title.startswith("10. Seven-Slide"):
                story.append(PageBreak())
            story.append(Paragraph(clean_inline(title), styles["H1"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(clean_inline(stripped[4:]), styles["H2"]))
        elif stripped.startswith("#### "):
            story.append(Paragraph(clean_inline(stripped[5:]), styles["H3"]))
        else:
            story.append(Paragraph(clean_inline(stripped), styles["Body"]))
        i += 1

    flush_bullets()
    flush_code()
    return story


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("SimHei", 8)
    canvas.setFillColor(colors.HexColor("#687785"))
    canvas.drawRightString(
        A4[0] - 17 * mm,
        10 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def main() -> None:
    font_name = register_fonts()
    styles = build_styles(font_name)
    text = MD_PATH.read_text(encoding="utf-8")
    story = markdown_to_story(text, styles)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Project Conversation Export",
        author="Codex",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF written: reports/{PDF_PATH.name}")


if __name__ == "__main__":
    main()
