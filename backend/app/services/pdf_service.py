"""
PDF Generation Service for AisynEdu.
Converts synthesized educational study notes, chapter summaries, and revision notes
into beautifully formatted, multi-page, print-ready PDF documents.
Preserves headings, lists, tables, callouts, and code blocks with professional typography
and dynamic page numbering ("Page X of Y").
"""
import io
import re
from datetime import datetime
from typing import List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page count ("Page X of Y"),
    running headers, and running footers across arbitrary document lengths.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.doc_title = "AisynEdu Study Notes"
        self.doc_subject = "General Education"

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_page_decorations(self, page_count: int):
        self.saveState()
        page_w, page_h = letter
        margin = 36  # 0.5 inch margins

        # Running Header (pages 2 and later)
        if self._pageNumber > 1:
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            header_text = f"AisynEdu  |  {self.doc_subject} — {self.doc_title}"
            if len(header_text) > 85:
                header_text = header_text[:82] + "..."
            self.drawString(margin, page_h - 28, header_text)

            # Header thin rule
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(margin, page_h - 32, page_w - margin, page_h - 32)

        # Running Footer (all pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer thin rule
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(margin, 36, page_w - margin, 36)

        # Footer text
        self.drawString(margin, 24, "AisynEdu • Learn. Connect. Evolve.  •  Document-Grounded Synthesis")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_w - margin, 24, page_str)

        self.restoreState()


class PDFService:
    """
    Transforms Markdown-formatted study notes into publication-quality PDF documents.
    """

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitizes text and escapes XML entities while preserving HTML tags for ReportLab."""
        if not text:
            return ""

        # Map common Unicode characters to ReportLab-safe ASCII or XML equivalents
        replacements = [
            ("—", " -- "),
            ("–", " - "),
            ("…", "..."),
            ("“", '"'),
            ("”", '"'),
            ("‘", "'"),
            ("’", "'"),
            ("→", " -> "),
            ("←", " <- "),
            ("↔", " <-> "),
            ("⇒", " => "),
            ("•", "&bull;"),
            ("≤", "&le;"),
            ("≥", "&ge;"),
            ("≠", "!="),
            ("≈", "~="),
            ("×", "x"),
            ("÷", "/"),
            ("±", "+/-"),
            ("°", " deg"),
            ("™", "(TM)"),
            ("©", "(C)"),
            ("®", "(R)"),
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
        ]

        # First escape ampersands that aren't already entities
        cleaned = text.replace("&", "&amp;")

        for orig, rep in replacements:
            if orig != "&":
                cleaned = cleaned.replace(orig, rep)

        return cleaned

    @classmethod
    def format_inline_markdown(cls, text: str) -> str:
        """Converts inline markdown syntax (bold, italic, code, math) into ReportLab XML markup."""
        # Clean entities first
        safe_text = cls.sanitize_text(text)

        # Re-allow safe ReportLab XML tags that we might generate
        # Bold: **text** or __text__
        safe_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe_text)
        safe_text = re.sub(r"__(.+?)__", r"<b>\1</b>", safe_text)

        # Italic: *text* or _text_
        safe_text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", safe_text)
        safe_text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", safe_text)

        # Inline code: `code`
        safe_text = re.sub(
            r"`(.+?)`",
            r'<font face="Courier" color="#1E293B"><b>\1</b></font>',
            safe_text,
        )

        # Inline math: $math$
        safe_text = re.sub(
            r"\$(.+?)\$",
            r'<font face="Helvetica-Oblique" color="#4338CA"><b>\1</b></font>',
            safe_text,
        )

        return safe_text

    @classmethod
    def generate_notes_pdf(
        cls,
        title: str,
        subject: str = "General Studies",
        content: str = "",
    ) -> bytes:
        """
        Parses Markdown study notes and compiles them into a complete PDF binary buffer.
        """
        buffer = io.BytesIO()

        # Page setup: Letter size with 36pt (0.5 inch) left/right, 44pt top/bottom margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=44,
            bottomMargin=44,
        )

        # Stylesheet setup
        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        primary_color = colors.HexColor("#1E1B4B")     # Deep indigo
        secondary_color = colors.HexColor("#4F46E5")   # Indigo-600
        dark_text = colors.HexColor("#0F172A")         # Slate-900
        body_text = colors.HexColor("#334155")         # Slate-700
        muted_text = colors.HexColor("#64748B")        # Slate-500

        # Custom Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=primary_color,
            spaceAfter=4,
        )

        meta_badge_style = ParagraphStyle(
            "MetaBadge",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=secondary_color,
            spaceAfter=6,
        )

        meta_info_style = ParagraphStyle(
            "MetaInfo",
            parent=normal,
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=muted_text,
            spaceAfter=8,
        )

        h1_style = ParagraphStyle(
            "SectionH1",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=5,
            keepWithNext=True,
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=secondary_color,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )

        h3_style = ParagraphStyle(
            "SectionH3",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=dark_text,
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "DocBody",
            parent=normal,
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=body_text,
            spaceAfter=5,
        )

        bullet_style = ParagraphStyle(
            "DocBullet",
            parent=normal,
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=body_text,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=3,
        )

        numbered_style = ParagraphStyle(
            "DocNumbered",
            parent=normal,
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=body_text,
            leftIndent=16,
            firstLineIndent=-12,
            spaceAfter=3,
        )

        callout_style = ParagraphStyle(
            "DocCallout",
            parent=normal,
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#312E81"),
        )

        code_style = ParagraphStyle(
            "DocCode",
            parent=normal,
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=normal,
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=body_text,
        )

        story = []

        # 1. Header Banner
        clean_title = title.strip() or "Synthesized Revision Notes"
        clean_subject = subject.strip() or "General Studies"
        now_str = datetime.now().strftime("%B %d, %Y")

        story.append(Paragraph(f"AISYNEDU  •  STUDY REVISION NOTES", meta_badge_style))
        story.append(Paragraph(cls.sanitize_text(clean_title), title_style))
        story.append(
            Paragraph(
                f"<b>Subject:</b> {cls.sanitize_text(clean_subject)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Generated:</b> {now_str} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Verified:</b> Multi-Agent Conceptual Synthesis",
                meta_info_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceBefore=2, spaceAfter=8))

        # 2. Content Parser
        lines = content.splitlines()
        i = 0
        total_lines = len(lines)
        printable_width = letter[0] - 72  # 612 - 72 = 540 pt

        while i < total_lines:
            line = lines[i].rstrip()
            stripped = line.strip()

            # Empty Line
            if not stripped:
                story.append(Spacer(1, 4))
                i += 1
                continue

            # Code Block ```
            if stripped.startswith("```"):
                code_lines = []
                i += 1
                while i < total_lines and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # Skip closing ```

                code_text = "\n".join(code_lines)
                if not code_text.strip():
                    code_text = "# [Empty code snippet]"

                # Render code in a styled table container with light slate background
                code_p = Preformatted(cls.sanitize_text(code_text), code_style)
                code_table = Table([[code_p]], colWidths=[printable_width])
                code_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ])
                )
                story.append(Spacer(1, 4))
                story.append(code_table)
                story.append(Spacer(1, 6))
                continue

            # Markdown Table | col1 | col2 |
            if stripped.startswith("|") and stripped.endswith("|") and i + 1 < total_lines and "|---" in lines[i + 1]:
                table_raw_rows = []
                while i < total_lines and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    row_line = lines[i].strip()
                    # Skip markdown table divider row |---|---|
                    if not re.match(r"^\|(\s*:?-+:?\s*\|)+$", row_line):
                        cols = [c.strip() for c in row_line.strip("|").split("|")]
                        table_raw_rows.append(cols)
                    i += 1

                if table_raw_rows:
                    num_cols = max(len(r) for r in table_raw_rows)
                    col_width = printable_width / max(num_cols, 1)
                    col_widths = [col_width] * num_cols

                    table_flowable_data = []
                    for row_idx, r in enumerate(table_raw_rows):
                        # Pad row if missing columns
                        padded_row = r + [""] * (num_cols - len(r))
                        formatted_row = []
                        for cell_text in padded_row:
                            is_header = (row_idx == 0)
                            p_style = table_header_style if is_header else table_cell_style
                            formatted_row.append(
                                Paragraph(cls.format_inline_markdown(cell_text), p_style)
                            )
                        table_flowable_data.append(formatted_row)

                    t = Table(table_flowable_data, colWidths=col_widths, repeatRows=1)
                    t_style = [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                    # Alternating row background
                    for r_idx in range(1, len(table_flowable_data)):
                        bg = colors.HexColor("#F8FAFC") if r_idx % 2 == 1 else colors.white
                        t_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), bg))

                    t.setStyle(TableStyle(t_style))
                    story.append(Spacer(1, 4))
                    story.append(t)
                    story.append(Spacer(1, 6))
                continue

            # Headings
            if stripped.startswith("#### "):
                h_text = cls.format_inline_markdown(stripped[5:].strip())
                story.append(Paragraph(h_text, h3_style))
                i += 1
                continue

            if stripped.startswith("### "):
                h_text = cls.format_inline_markdown(stripped[4:].strip())
                story.append(Paragraph(h_text, h3_style))
                i += 1
                continue

            if stripped.startswith("## "):
                h_text = cls.format_inline_markdown(stripped[3:].strip())
                story.append(Paragraph(h_text, h2_style))
                i += 1
                continue

            if stripped.startswith("# "):
                h_text = cls.format_inline_markdown(stripped[2:].strip())
                story.append(Paragraph(h_text, h1_style))
                i += 1
                continue

            # Blockquote / Callout (> text)
            if stripped.startswith(">"):
                quote_text = cls.format_inline_markdown(stripped.lstrip("> ").strip())
                q_p = Paragraph(f"<b>Key Takeaway:</b> {quote_text}", callout_style)
                callout_table = Table([[q_p]], colWidths=[printable_width])
                callout_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
                        ("LINEBEFORE", (0, 0), (0, -1), 3, secondary_color),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ])
                )
                story.append(Spacer(1, 4))
                story.append(callout_table)
                story.append(Spacer(1, 5))
                i += 1
                continue

            # Horizontal Rule (--- or ***)
            if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=6, spaceAfter=6))
                i += 1
                continue

            # Bullet List Items (- or * or •)
            if re.match(r"^[-*•]\s+", stripped):
                item_text = re.sub(r"^[-*•]\s+", "", stripped)
                formatted_item = cls.format_inline_markdown(item_text)
                story.append(Paragraph(f"&bull;&nbsp;&nbsp;{formatted_item}", bullet_style))
                i += 1
                continue

            # Numbered List Items (1. or 2.)
            m_num = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            if m_num:
                num = m_num.group(1)
                item_text = m_num.group(2)
                formatted_item = cls.format_inline_markdown(item_text)
                story.append(Paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{formatted_item}", numbered_style))
                i += 1
                continue

            # Standard Paragraph
            p_text = cls.format_inline_markdown(stripped)
            story.append(Paragraph(p_text, body_style))
            i += 1

        # Build document using NumberedCanvas
        def canvas_maker(*args, **kwargs):
            c = NumberedCanvas(*args, **kwargs)
            c.doc_title = clean_title
            c.doc_subject = clean_subject
            return c

        doc.build(story, canvasmaker=canvas_maker)
        return buffer.getvalue()

