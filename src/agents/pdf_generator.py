import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas to add dynamic headers and footers with a running page count.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        
        # We enforce exactly 4 pages for our CAD report
        page_num = self._pageNumber
        
        # Color Palette
        primary_color = colors.HexColor("#0B2545")
        secondary_color = colors.HexColor("#134074")
        accent_color = colors.HexColor("#EE6C4D")
        neutral_light = colors.HexColor("#8DA9C4")
        border_color = colors.HexColor("#E2E8F0")

        # Header (Pages 2-4)
        if page_num > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(primary_color)
            self.drawString(54, 750, "GARUDA SENTINEL — INTELLIGENCE WORKSTATION")
            self.setFont("Helvetica", 8)
            self.setFillColor(secondary_color)
            self.drawRightString(558, 750, "CONFIDENTIAL // LAW ENFORCEMENT ONLY")
            
            # Header line
            self.setStrokeColor(border_color)
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Footer (All pages)
        self.setStrokeColor(border_color)
        self.setLineWidth(0.75)
        self.line(54, 50, 558, 50)

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(primary_color)
        self.drawString(54, 38, "DEPARTMENT OF FINANCIAL INTELLIGENCE & AUDIT")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(secondary_color)
        self.drawRightString(558, 38, f"Page {page_num} of {total_pages}")
        
        # Decorative border sidebar
        self.setStrokeColor(primary_color)
        self.setLineWidth(3)
        self.line(30, 30, 30, 762)
        
        self.setStrokeColor(accent_color)
        self.setLineWidth(1.5)
        self.line(35, 30, 35, 762)

        self.restoreState()


def safe_paragraph(text, style):
    """
    Safely instantiates a ReportLab Paragraph flowable.
    Autocorrects common malformed XML/HTML tags and escapes raw ampersands/brackets.
    Falls back to a stripped plain-text representation if parsing fails.
    """
    try:
        # Fix common LLM tag inversion: <b><i>content</b></i> -> <b><i>content</i></b>
        processed = re.sub(r'<b><i>(.*?)</b></i>', r'<b><i>\1</i></b>', text)
        processed = re.sub(r'<i><b>(.*?)</i></b>', r'<i><b>\1</b></i>', processed)
        # Escape any raw ampersand not part of a valid XML entity
        processed = re.sub(r'&(?![a-zA-Z0-9#]+;)', '&amp;', processed)
        return Paragraph(processed, style)
    except Exception:
        # Strip all tags and escape XML characters
        cleaned = re.sub(r'<[^>]+>', '', text)
        cleaned = cleaned.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        try:
            return Paragraph(cleaned, style)
        except Exception:
            return Paragraph("Content Parsing Error", style)

def parse_markdown_to_flowables(md_text, styles):
    """
    Parses basic markdown elements into ReportLab Flowables.
    Supports headings, lists, bold text, and tables.
    """
    flowables = []
    lines = md_text.split('\n')
    
    in_list = False
    in_table = False
    table_data = []

    primary_color = colors.HexColor("#0B2545")
    border_color = colors.HexColor("#CBD5E1")

    # Clean bold text wrapper
    def clean_text(t):
        t = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'\*(.*?)\*', r'<i>\1</i>', t)
        t = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', t)
        return t

    for line in lines:
        line_strip = line.strip()
        
        # Page Break
        if line_strip == "---" or "<!-- pagebreak -->" in line_strip:
            if in_table:
                # render table
                flowables.append(create_reportlab_table(table_data, border_color))
                in_table = False
                table_data = []
            flowables.append(PageBreak())
            continue

        # Table Parsing
        if line_strip.startswith('|'):
            if not in_table:
                in_table = True
                table_data = []
            
            # Skip delimiter rows
            if '---' in line_strip:
                continue
                
            parts = [clean_text(p.strip()) for p in line_strip.split('|')[1:-1]]
            table_data.append(parts)
            continue
        elif in_table:
            # Table ended
            flowables.append(create_reportlab_table(table_data, border_color))
            flowables.append(Spacer(1, 10))
            in_table = False
            table_data = []

        # Headings
        if line_strip.startswith('# '):
            title = clean_text(line_strip[2:])
            # Styled CAD Banner Heading
            banner_data = [[safe_paragraph(f"<font color='white'><b>{title.upper()}</b></font>", styles['BannerText'])]]
            banner_table = Table(banner_data, colWidths=[504])
            banner_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), primary_color),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            flowables.append(banner_table)
            flowables.append(Spacer(1, 12))
        elif line_strip.startswith('## '):
            title = clean_text(line_strip[3:])
            flowables.append(safe_paragraph(title, styles['Heading2']))
            flowables.append(Spacer(1, 8))
        elif line_strip.startswith('### '):
            title = clean_text(line_strip[4:])
            flowables.append(safe_paragraph(title, styles['Heading3']))
            flowables.append(Spacer(1, 6))

        # Bullet List Items
        elif line_strip.startswith('- ') or line_strip.startswith('* '):
            bullet_text = clean_text(line_strip[2:])
            flowables.append(safe_paragraph(f"&bull; {bullet_text}", styles['CustomBullet']))
            flowables.append(Spacer(1, 4))

        # Standard Paragraphs
        elif line_strip:
            p_text = clean_text(line_strip)
            flowables.append(safe_paragraph(p_text, styles['Normal']))
            flowables.append(Spacer(1, 8))
        else:
            flowables.append(Spacer(1, 6))

    # Catch remaining table
    if in_table and table_data:
        flowables.append(create_reportlab_table(table_data, border_color))

    return flowables

def create_reportlab_table(table_data, border_color):
    """Generates a highly styled ReportLab Table from markdown parsed rows."""
    if not table_data:
        return Spacer(1, 1)
        
    num_cols = len(table_data[0])
    col_width = 504.0 / num_cols
    
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )
    
    header_style = ParagraphStyle(
        'TableHeaderCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    
    formatted_data = []
    # Header row
    formatted_data.append([safe_paragraph(cell, header_style) for cell in table_data[0]])
    
    # Body rows
    for row in table_data[1:]:
        formatted_data.append([safe_paragraph(cell, cell_style) for cell in row])
        
    t = Table(formatted_data, colWidths=[col_width] * num_cols)
    
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0B2545")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
    ]
    
    # Alternating row colors
    for i in range(1, len(table_data)):
        bg = colors.HexColor("#F8FAFC") if i % 2 == 1 else colors.white
        t_style.append(('BACKGROUND', (0, i), (-1, i), bg))
        
    t.setStyle(TableStyle(t_style))
    return t


def generate_investigation_pdf(markdown_content: str, output_path: str):
    """
    Compiles a highly professional, 4-page CAD PDF report from Groq generated Markdown content.
    """
    # Enforce exact margin constraints
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    styles.add(ParagraphStyle(
        'BannerText',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.white
    ))
    
    styles['Normal'].textColor = colors.HexColor("#334155")
    styles['Normal'].fontSize = 9
    styles['Normal'].leading = 13
    
    styles['Heading2'].textColor = colors.HexColor("#0B2545")
    styles['Heading2'].fontSize = 11
    styles['Heading2'].leading = 15
    styles['Heading2'].fontName = 'Helvetica-Bold'
    
    styles['Heading3'].textColor = colors.HexColor("#EE6C4D")
    styles['Heading3'].fontSize = 9.5
    styles['Heading3'].leading = 13
    styles['Heading3'].fontName = 'Helvetica-Bold'

    styles.add(ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    ))

    # Parse md content into layout flowables
    flowables = parse_markdown_to_flowables(markdown_content, styles)
    
    # Build Document using NumberedCanvas
    doc.build(flowables, canvasmaker=NumberedCanvas)
