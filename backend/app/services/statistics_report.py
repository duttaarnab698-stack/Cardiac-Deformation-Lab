"""
backend/app/services/statistics_report.py

PDF Research Statistics Report Generator for Cardiac Deformation Lab.
Produces high-quality, professional publication-style PDF reports
summarizing descriptive metrics, longitudinal change variability,
standardized differences, Pearson correlation matrices, and computational outliers.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically inject running header and total page count in footers."""

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

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Cardiac Deformation Lab — Advanced Research Statistics Report")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(
            54,
            36,
            "Research Prototype • Statistical Analytics • Not For Clinical Diagnostic Use"
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)

        self.restoreState()


def _fmt(val: Any, decimals: int = 4, suffix: str = "") -> str:
    """Safely format numbers with exponent or fixed decimal representation."""
    if val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        try:
            f = float(val)
            if abs(f) > 0 and (abs(f) < 0.0001 or abs(f) >= 10000):
                return f"{f:.{decimals}e}{suffix}"
            return f"{f:.{decimals}f}{suffix}"
        except Exception:
            return str(val)
    return str(val)


def generate_statistics_report(
    stats_data: Dict[str, Any],
    output_pdf_path: str
) -> str:
    """
    Generate a publication-grade PDF research statistics report.
    """
    out_path = Path(output_pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "StatsTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "StatsSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "StatsH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=5,
    )

    body_style = ParagraphStyle(
        "StatsBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    table_header_style = ParagraphStyle(
        "StatsTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#ffffff"),
    )

    table_cell_style = ParagraphStyle(
        "StatsTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "StatsTableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    disclaimer_style = ParagraphStyle(
        "StatsDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#b45309"),
    )

    story = []

    # ── HEADER & TITLE ────────────────────────────────────────────────────────
    story.append(Paragraph("Cardiac Deformation Lab", title_style))
    story.append(
        Paragraph(
            "Advanced Statistical &amp; Quantitative Analytics Report",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0891b2"), spaceAfter=12))

    # ── METADATA TABLE ────────────────────────────────────────────────────────
    study_id = stats_data.get("study_id", "Unknown")
    study_title = stats_data.get("study_title", "Untitled Study")
    subject_code = stats_data.get("subject_code") or "Not Specified"
    analysis_count = stats_data.get("analysis_count", 0)
    scope_str = "Region of Interest (ROI)" if stats_data.get("analysis_scope") == "roi" else "Full Image"
    total_outliers = stats_data.get("total_outliers_count", 0)

    meta_data = [
        [
            Paragraph("Study Title:", table_cell_bold),
            Paragraph(f"<b>{study_title}</b>", table_cell_bold),
            Paragraph("Subject Identifier:", table_cell_bold),
            Paragraph(subject_code, table_cell_style),
        ],
        [
            Paragraph("Study ID:", table_cell_bold),
            Paragraph(f"<code>{study_id}</code>", table_cell_style),
            Paragraph("Session Count:", table_cell_bold),
            Paragraph(f"<b>{analysis_count}</b> analyses", table_cell_style),
        ],
        [
            Paragraph("Analysis Scope:", table_cell_bold),
            Paragraph(f"<b>{scope_str}</b>", table_cell_bold),
            Paragraph("Detected Outliers:", table_cell_bold),
            Paragraph(f"{total_outliers} observations (1.5xIQR)", table_cell_style),
        ],
        [
            Paragraph("Report Date:", table_cell_bold),
            Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), table_cell_style),
            Paragraph("Computational Engine:", table_cell_bold),
            Paragraph("NumPy / Farnebäck Dense Flow", table_cell_style),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[105, 147, 110, 142])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # ── 1. DESCRIPTIVE STATISTICS TABLE ────────────────────────────────────────
    story.append(Paragraph("1. Descriptive Deformation Statistics (Univariate)", h1_style))
    desc_dict = stats_data.get("descriptive_statistics") or {}

    desc_rows = [
        [
            Paragraph("Metric", table_header_style),
            Paragraph("N", table_header_style),
            Paragraph("Mean", table_header_style),
            Paragraph("Median", table_header_style),
            Paragraph("Std Dev", table_header_style),
            Paragraph("Min", table_header_style),
            Paragraph("Max", table_header_style),
            Paragraph("P25", table_header_style),
            Paragraph("P75", table_header_style),
            Paragraph("IQR", table_header_style),
        ]
    ]

    for m_key, d in desc_dict.items():
        if d.get("count", 0) > 0:
            lbl = d.get("label", m_key)
            u = f" ({d.get('unit')})" if d.get("unit") else ""
            desc_rows.append([
                Paragraph(f"{lbl}{u}", table_cell_bold),
                Paragraph(str(d.get("count", 0)), table_cell_style),
                Paragraph(_fmt(d.get("mean")), table_cell_style),
                Paragraph(_fmt(d.get("median")), table_cell_style),
                Paragraph(_fmt(d.get("std")), table_cell_style),
                Paragraph(_fmt(d.get("min")), table_cell_style),
                Paragraph(_fmt(d.get("max")), table_cell_style),
                Paragraph(_fmt(d.get("p25")), table_cell_style),
                Paragraph(_fmt(d.get("p75")), table_cell_style),
                Paragraph(_fmt(d.get("iqr")), table_cell_style),
            ])

    desc_table = Table(desc_rows, colWidths=[120, 24, 45, 45, 45, 45, 45, 45, 45, 45])
    desc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e7490")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(desc_table)
    story.append(Spacer(1, 10))

    # ── 2. LONGITUDINAL CHANGE & STANDARDIZED DIFFERENCES ──────────────────────
    story.append(Paragraph("2. Longitudinal Change &amp; Standardized Differences", h1_style))
    chg_dict = stats_data.get("change_statistics") or {}

    chg_rows = [
        [
            Paragraph("Tracked Metric", table_header_style),
            Paragraph("First", table_header_style),
            Paragraph("Latest", table_header_style),
            Paragraph("Delta (Δ)", table_header_style),
            Paragraph("Rel Change", table_header_style),
            Paragraph("Std Diff (d)", table_header_style),
            Paragraph("Trend", table_header_style),
        ]
    ]

    for m_key, c in chg_dict.items():
        if c.get("observation_count", 0) > 0:
            lbl = c.get("label", m_key)
            u = f" {c.get('unit')}" if c.get("unit") else ""
            v1_s = _fmt(c.get("first_value"), suffix=u)
            v2_s = _fmt(c.get("latest_value"), suffix=u)
            del_s = _fmt(c.get("absolute_change"), suffix=u)
            pct = c.get("percentage_change")
            pct_s = f"{pct:+.1f}%" if pct is not None else "—"
            d_val = _fmt(c.get("standardized_difference"))
            tr = c.get("trend_direction", "insufficient_data")

            tr_color = "#0284c7" if tr == "increasing" else ("#7c3aed" if tr == "decreasing" else "#64748b")

            chg_rows.append([
                Paragraph(lbl, table_cell_bold),
                Paragraph(v1_s, table_cell_style),
                Paragraph(v2_s, table_cell_style),
                Paragraph(del_s, table_cell_style),
                Paragraph(pct_s, table_cell_style),
                Paragraph(d_val, table_cell_style),
                Paragraph(f"<font color='{tr_color}'><b>{tr.capitalize()}</b></font>", table_cell_style),
            ])

    chg_table = Table(chg_rows, colWidths=[134, 60, 60, 65, 65, 60, 60])
    chg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e7490")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(chg_table)
    story.append(Spacer(1, 10))

    # ── 3. METRIC CORRELATIONS ────────────────────────────────────────────────
    story.append(Paragraph("3. Metric Pearson Correlation Analysis", h1_style))
    corrs = stats_data.get("correlations") or []

    if corrs:
        corr_rows = [
            [
                Paragraph("Metric A", table_header_style),
                Paragraph("Metric B", table_header_style),
                Paragraph("Pearson r", table_header_style),
                Paragraph("N Pairs", table_header_style),
                Paragraph("Association Type", table_header_style),
            ]
        ]

        for p in corrs[:8]:  # Show top 8 strongest correlations
            r_val = p.get("correlation", 0.0)
            r_str = f"{r_val:+.4f}"
            assoc = "Positive Association" if r_val > 0.2 else ("Negative Association" if r_val < -0.2 else "Near Zero")
            corr_rows.append([
                Paragraph(p.get("label_x", p.get("metric_x")), table_cell_bold),
                Paragraph(p.get("label_y", p.get("metric_y")), table_cell_bold),
                Paragraph(r_str, table_cell_style),
                Paragraph(str(p.get("observation_count")), table_cell_style),
                Paragraph(assoc, table_cell_style),
            ])

        corr_table = Table(corr_rows, colWidths=[150, 150, 65, 45, 94])
        corr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e7490")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(corr_table)
        story.append(Paragraph("<i>Note: Correlation describes statistical association only and does not imply causation.</i>", body_style))
    else:
        story.append(Paragraph("<i>Insufficient paired observations (<3 sessions) for Pearson metric correlation.</i>", body_style))

    story.append(Spacer(1, 10))

    # ── 4. COMPUTATIONAL OUTLIER DETECTION (1.5xIQR) ───────────────────────────
    story.append(Paragraph("4. Computational Statistical Outliers (1.5×IQR)", h1_style))
    outliers_dict = stats_data.get("outliers") or {}
    all_outliers: List[Dict[str, Any]] = []
    for m_k, o_list in outliers_dict.items():
        all_outliers.extend(o_list)

    if all_outliers:
        out_rows = [
            [
                Paragraph("Session / Date", table_header_style),
                Paragraph("Metric", table_header_style),
                Paragraph("Observed Value", table_header_style),
                Paragraph("Normal Bounds [Q1-1.5IQR, Q3+1.5IQR]", table_header_style),
                Paragraph("QC Context", table_header_style),
            ]
        ]

        for o in all_outliers:
            ts_str = str(o.get("timestamp"))[:16]
            sess_str = f"S#{o.get('session_number')} ({ts_str})"
            val_s = f"<b>{_fmt(o.get('value'))}</b> {o.get('unit', '')}"
            bounds_s = f"[{_fmt(o.get('lower_bound'))}, {_fmt(o.get('upper_bound'))}]"
            qc_ctx = o.get("quality_context") or "Standard QC"

            out_rows.append([
                Paragraph(sess_str, table_cell_style),
                Paragraph(o.get("metric_label", o.get("metric_key")), table_cell_bold),
                Paragraph(val_s, table_cell_style),
                Paragraph(bounds_s, table_cell_style),
                Paragraph(qc_ctx, table_cell_style),
            ])

        out_table = Table(out_rows, colWidths=[105, 110, 80, 105, 104])
        out_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e7490")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(out_table)
    else:
        story.append(Paragraph("<i>No computational outliers identified using the 1.5×IQR boundary rule (or insufficient N < 4 observations).</i>", body_style))

    story.append(Spacer(1, 10))

    # ── 5. WARNINGS & PROTOCOL NOTICES ────────────────────────────────────────
    warns = stats_data.get("warnings") or []
    infos = stats_data.get("info") or []

    if warns or infos:
        story.append(Paragraph("5. Statistical Warnings &amp; Protocol Consistency", h1_style))
        for w in warns:
            story.append(Paragraph(f"• <font color='#b45309'><b>Warning:</b> {w}</font>", table_cell_style))
        for inf in infos:
            story.append(Paragraph(f"• <font color='#0284c7'><b>Note:</b> {inf}</font>", table_cell_style))
        story.append(Spacer(1, 8))

    # ── 6. METHODOLOGY & SCIENTIFIC DISCLAIMER ────────────────────────────────
    disclaimer_block = [
        Paragraph("6. Research Methodology &amp; Interpretation Disclaimer", h1_style),
        Paragraph(
            "<b>Computational Analytics Scope:</b> Descriptive parameters, consecutive change differentials, "
            "standardized computational differences (effect sizes), and Pearson correlation matrices reflect algorithmic "
            "evaluations of image-space deformation fields under classical continuum kinematics. "
            "Statistical outliers reflect mathematical dispersion (1.5×IQR) and do NOT indicate patient health or clinical abnormality.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>RESEARCH PROTOTYPE ONLY — NO CLINICAL DIAGNOSTIC ASSERTIONS:</b><br/>"
            "These statistics summarize computational image-derived measurements and should not be interpreted as clinical findings. "
            "This software does NOT provide medical diagnoses, prognosis, treatment monitoring, or clinical risk assessments. "
            "This document is intended strictly for mathematical and biomechanical research experimentation.",
            disclaimer_style,
        ),
    ]
    story.append(KeepTogether(disclaimer_block))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    return str(out_path.resolve())

