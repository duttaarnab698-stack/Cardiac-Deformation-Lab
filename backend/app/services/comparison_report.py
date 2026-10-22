"""
backend/app/services/comparison_report.py

PDF Comparison Report Generator for Cardiac Deformation Lab.
Produces high-quality, professional publication-style PDF reports
comparing quantitative measurements across 2 to 5 cardiac deformation analyses.
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
    """Two-pass canvas to dynamically inject total page count in footers."""

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
            self.drawString(54, 750, "Cardiac Deformation Lab — Multi-Analysis Quantitative Comparison")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(
            54,
            36,
            "Research Prototype • Quantitative Analysis Comparison • Not For Diagnostic Use"
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


def generate_comparison_report(
    comparison_data: Dict[str, Any],
    output_pdf_path: str,
    title: Optional[str] = None
) -> str:
    """
    Generate a publication-grade PDF comparison report.

    Parameters
    ----------
    comparison_data : dict
        Returned by compare_analyses(...)
    output_pdf_path : str
        Target filesystem path for the output PDF.
    title : str, optional
        Custom title or comparison label.

    Returns
    -------
    str
        Absolute path to the generated PDF.
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
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyText_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    disclaimer_style = ParagraphStyle(
        "DisclaimerText_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#b45309"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#ffffff"),
    )

    table_cell_style = ParagraphStyle(
        "TableCell_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # ── HEADER & TITLE ────────────────────────────────────────────────────────
    story.append(Paragraph("Cardiac Deformation Lab", title_style))
    story.append(
        Paragraph(
            "Quantitative Multi-Analysis Comparison &amp; Kinematic Variance Report",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=12))

    analyses = comparison_data.get("analyses") or []
    n = len(analyses)
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M:%S UTC")

    # ── METADATA & COMPATIBILITY TABLE ────────────────────────────────────────
    study_ctx = comparison_data.get("study_context") or {}
    cal_compat = comparison_data.get("calibration_compatibility") or {}
    roi_compat = comparison_data.get("roi_compatibility") or {}

    meta_rows = [
        [
            Paragraph("Analyses Compared:", table_cell_bold),
            Paragraph(f"<b>{n} Analyses</b>", table_cell_style),
            Paragraph("Generation Date:", table_cell_bold),
            Paragraph(now_str, table_cell_style),
        ],
        [
            Paragraph("Study Context:", table_cell_bold),
            Paragraph(study_ctx.get("message", "N/A"), table_cell_style),
            Paragraph("Calibration Compatibility:", table_cell_bold),
            Paragraph(cal_compat.get("badge", "N/A"), table_cell_style),
        ],
        [
            Paragraph("Analysis Region Scope:", table_cell_bold),
            Paragraph(roi_compat.get("badge", "N/A"), table_cell_style),
            Paragraph("Primary Motion Model:", table_cell_bold),
            Paragraph("Dense Farnebäck Optical Flow", table_cell_style),
        ],
    ]

    # Add row describing the compared analysis IDs and types
    for idx, a in enumerate(analyses, start=1):
        meta = a.get("metadata", {})
        cal_meta = meta.get("calibration", {})
        cal_desc = f"{cal_meta.get('pixel_spacing_x')} {cal_meta.get('unit', 'mm')}/px" if cal_meta.get("enabled") else "Pixels (px)"
        roi_meta = meta.get("roi", {})
        roi_desc = f"{roi_meta.get('mode', 'fixed').capitalize()} ({roi_meta.get('type')})" if roi_meta.get("enabled") else "Full Image"

        meta_rows.append([
            Paragraph(f"Analysis {idx} ({meta.get('type')}):", table_cell_bold),
            Paragraph(f"<code>{meta.get('id', '')[:12]}...</code> ({meta.get('timestamp', '')[:19]})", table_cell_style),
            Paragraph(f"Scope / Spacing {idx}:", table_cell_bold),
            Paragraph(f"{roi_desc} • {cal_desc}", table_cell_style),
        ])

    meta_table = Table(meta_rows, colWidths=[120, 132, 120, 132])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # Compatibility warnings if applicable
    warn_msgs = []
    if cal_compat.get("warning"):
        warn_msgs.append(f"<b>Calibration Notice:</b> {cal_compat['warning']}")
    if roi_compat.get("warning"):
        warn_msgs.append(f"<b>ROI Boundary Notice:</b> {roi_compat['warning']}")

    if warn_msgs:
        for w in warn_msgs:
            story.append(Paragraph(w, disclaimer_style))
        story.append(Spacer(1, 6))

    # ── LARGEST QUANTITATIVE DIFFERENCES (if 2 analyses) ──────────────────────
    largest_diffs = comparison_data.get("largest_differences") or []
    if largest_diffs and n == 2:
        story.append(Paragraph("1. Largest Quantitative Differences", h1_style))
        story.append(Paragraph(
            "Top computed metric variances between Analysis 1 (baseline) and Analysis 2. "
            "These differences reflect algorithmic optical-flow divergences; they do NOT indicate clinical significance.",
            body_style
        ))
        story.append(Spacer(1, 4))

        diff_rows = [
            [
                Paragraph("Metric Parameter", table_header_style),
                Paragraph("Category", table_header_style),
                Paragraph("Analysis 1", table_header_style),
                Paragraph("Analysis 2", table_header_style),
                Paragraph("Difference (Δ)", table_header_style),
                Paragraph("% Difference", table_header_style),
            ]
        ]

        for d in largest_diffs:
            pct_str = f"{d['pct_difference']:+.2f}%" if d.get("pct_difference") is not None else "N/A"
            diff_str = f"{d['difference']:+.4f} {d.get('unit', '')}" if d.get("difference") is not None else "N/A"
            diff_rows.append([
                Paragraph(d["metric_name"], table_cell_bold),
                Paragraph(d["category"], table_cell_style),
                Paragraph(_fmt(d["val1"]), table_cell_style),
                Paragraph(_fmt(d["val2"]), table_cell_style),
                Paragraph(diff_str, table_cell_style),
                Paragraph(pct_str, table_cell_bold),
            ])

        diff_table = Table(diff_rows, colWidths=[120, 100, 70, 70, 74, 70])
        diff_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(diff_table)
        story.append(Spacer(1, 10))

    # ── STRUCTURED QUANTITATIVE COMPARISON TABLES ─────────────────────────────
    category_tables = comparison_data.get("category_tables") or {}
    cat_order = [
        ("displacement", "2. Displacement Kinematics Comparison"),
        ("strain", "3. Small-Deformation Continuum Strain Comparison"),
        ("advanced", "4. Advanced Deformation Metrics Comparison"),
        ("cardiac", "5. Ventricular Geometric Deformation Comparison"),
        ("temporal", "6. Multi-Frame Temporal Trajectory Comparison"),
    ]

    for cat_key, cat_title in cat_order:
        rows = category_tables.get(cat_key) or []
        if not rows:
            continue

        story.append(Paragraph(cat_title, h1_style))

        if n == 2:
            # 2 Analyses layout: Metric | Unit | Analysis 1 | Analysis 2 | Diff | % Diff
            table_data = [
                [
                    Paragraph("Metric Parameter", table_header_style),
                    Paragraph("Unit", table_header_style),
                    Paragraph("Analysis 1", table_header_style),
                    Paragraph("Analysis 2", table_header_style),
                    Paragraph("Difference (Δ)", table_header_style),
                    Paragraph("% Difference", table_header_style),
                ]
            ]
            for r in rows:
                pct_str = f"{r['pct_difference']:+.2f}%" if r.get("pct_difference") is not None else "N/A"
                diff_str = f"{r['difference']:+.4f}" if r.get("difference") is not None else "N/A"
                table_data.append([
                    Paragraph(r["metric_name"], table_cell_bold),
                    Paragraph(r["unit"], table_cell_style),
                    Paragraph(_fmt(r["val1"]), table_cell_style),
                    Paragraph(_fmt(r["val2"]), table_cell_style),
                    Paragraph(diff_str, table_cell_style),
                    Paragraph(pct_str, table_cell_style),
                ])
            col_widths = [134, 70, 75, 75, 75, 75]
        else:
            # 3 to 5 Analyses layout: Metric | Unit | A1 | A2 | A3 [| A4 [| A5]]
            header = [
                Paragraph("Metric Parameter", table_header_style),
                Paragraph("Unit", table_header_style),
            ]
            for i in range(n):
                header.append(Paragraph(f"Analysis {i+1}", table_header_style))
            table_data = [header]

            col_avail = 504 - 144 - 60  # remaining width
            col_each = col_avail / n
            col_widths = [144, 60] + [col_each] * n

            for r in rows:
                row_cells = [
                    Paragraph(r["metric_name"], table_cell_bold),
                    Paragraph(r["unit"], table_cell_style),
                ]
                for v in r["values"]:
                    row_cells.append(Paragraph(_fmt(v), table_cell_style))
                table_data.append(row_cells)

        sec_table = Table(table_data, colWidths=col_widths)
        sec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(sec_table)
        story.append(Spacer(1, 8))

    # ── 10-D FINGERPRINT COMPARISON TABLE ─────────────────────────────────────
    fp_comp = comparison_data.get("fingerprint_comparison") or {}
    fp_series = fp_comp.get("series") or []
    if fp_series:
        story.append(Paragraph("7. Cardiac Deformation Fingerprint (10-D) Comparison", h1_style))
        fp_dims = [
            ("D_mean", "Mean Displacement (px)"),
            ("D_max", "Maximum Displacement (px)"),
            ("epsilon_mean", "Representative Mean Strain"),
            ("epsilon_max", "Representative Max Strain"),
            ("epsilon_principal", "Representative Principal Strain"),
            ("AI", "Strain Anisotropy Index"),
            ("H", "Strain Entropy"),
            ("G_epsilon", "Strain Gradient Magnitude"),
            ("C", "Motion Coherence"),
            ("TSI", "Temporal Stability Index"),
        ]

        fp_header = [Paragraph("Dimension Symbol", table_header_style), Paragraph("Canonical Descriptor", table_header_style)]
        for i in range(len(fp_series)):
            fp_header.append(Paragraph(f"Analysis {i+1}", table_header_style))
        fp_data_table = [fp_header]

        fp_col_avail = 504 - 100 - 154
        fp_col_each = fp_col_avail / len(fp_series)
        fp_col_widths = [100, 154] + [fp_col_each] * len(fp_series)

        for dim_key, dim_label in fp_dims:
            row_c = [Paragraph(f"<b>{dim_key}</b>", table_cell_bold), Paragraph(dim_label, table_cell_style)]
            for s in fp_series:
                v = s.get("dimensions", {}).get(dim_key)
                row_c.append(Paragraph(_fmt(v), table_cell_style))
            fp_data_table.append(row_c)

        fp_table = Table(fp_data_table, colWidths=fp_col_widths)
        fp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(fp_table)
        story.append(Spacer(1, 10))

    # ── SCIENTIFIC METHODOLOGY & LIMITATIONS DISCLAIMER ───────────────────────
    disclaimer_block = [
        Paragraph("8. Scientific Methodology &amp; Non-Diagnostic Protocol Disclaimer", h1_style),
        Paragraph(
            "<b>Comparison Methodology:</b> This comparative analysis compiles computed 2D continuum strain tensors, "
            "Farnebäck optical flow kinematics, and derivative scalar metrics calculated from pixel arrays. "
            "Differences across analyses reflect algorithmic variations in spatial gradients, regional displacement, "
            "or temporal stability.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>Important Limitations:</b> Image acquisition frame rates, acoustic window variations, contrast-to-noise ratio, "
            "spatial resolution, and Region of Interest (ROI) demarcation directly impact motion estimation. "
            "Uncalibrated analyses express displacement solely in image pixels (px). "
            "<b>This comparison summarizes quantitative image-analysis measurements and is NOT a clinical diagnostic assessment.</b> "
            "Quantitative differences do NOT imply pathological abnormality, clinical improvement, or disease classification.",
            disclaimer_style,
        ),
    ]
    story.append(KeepTogether(disclaimer_block))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    return str(out_path.resolve())

