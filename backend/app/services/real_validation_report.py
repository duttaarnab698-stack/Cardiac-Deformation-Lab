"""
backend/app/services/real_validation_report.py

Publication-grade PDF report generator for Real-Image Annotation Benchmarking
in the Cardiac Deformation Lab.

Uses ReportLab with dynamic NumberedCanvas (Page X of Y).
Renders:
- Analysis and annotation metadata
- Benchmark scorecard (Landmark EPE, Displacement MAE/RMSE, ROI IoU)
- Paired landmark motion table
- Geometric reference strain chord analysis
- Contour and ROI overlap metrics
- Prominent research prototype and subjective reference annotation disclaimers
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

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
    """Two-pass canvas for dynamic 'Page X of Y' numbering and running header/footer."""

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

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Cardiac Deformation Lab — Real-Image Reference Benchmark Report")
            self.drawRightString(612 - 54, 750, "RESEARCH BENCHMARK ONLY")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)

        # Running footer
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(612 - 54, 34, page_str)
        self.drawString(54, 34, "Manual Reference Benchmark — Subjective Annotations Do Not Establish Clinical Validity")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 612 - 54, 46)

        self.restoreState()


def generate_real_validation_report(
    benchmark_data: Dict[str, Any],
    analysis_record: Dict[str, Any],
    output_pdf_path: str
) -> str:
    """
    Build and save publication-grade PDF real-image annotation validation report.
    """
    out_path = Path(output_pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RValTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "RValSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        "RValH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "RValBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    disclaimer_style = ParagraphStyle(
        "RValDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#991b1b")
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Real-Image Reference Benchmark Report", title_style))
    story.append(Paragraph("Quantitative Concordance of Optical Flow with Manual Reference Annotations", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # Prominent Disclaimer Callout Box
    disclaimer_text = (
        "<b>RESEARCH BENCHMARK NOTICE:</b> Manual annotations are reference measurements for computational "
        "benchmarking and do not represent clinical ground truth. Annotations are subject to inter- and intra-observer "
        "variability. Image-derived displacement may represent apparent image motion rather than true anatomical tissue motion. "
        "This report is strictly for computational algorithm verification."
    )
    t_disc = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[504])
    t_disc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(t_disc)
    story.append(Spacer(1, 12))

    # Analysis & Annotation Context Table
    analysis_id = benchmark_data.get("analysis_id", "Unknown")
    meta_rows = [
        [
            Paragraph("<b>Analysis ID:</b>", body_style),
            Paragraph(f"<font name='Courier'>{analysis_id}</font>", body_style),
            Paragraph("<b>Annotation Count:</b>", body_style),
            Paragraph(str(benchmark_data.get("annotation_count", 0)), body_style)
        ],
        [
            Paragraph("<b>Image 1:</b>", body_style),
            Paragraph(str(analysis_record.get("image1_filename") or analysis_record.get("result", {}).get("image1") or analysis_record.get("image1") or "N/A"), body_style),
            Paragraph("<b>Image 2:</b>", body_style),
            Paragraph(str(analysis_record.get("image2_filename") or analysis_record.get("result", {}).get("image2") or analysis_record.get("image2") or "N/A"), body_style)
        ]
    ]

    score_info = benchmark_data.get("benchmark_score")
    if score_info:
        meta_rows.append([
            Paragraph("<b>Benchmark Score:</b>", body_style),
            Paragraph(f"<b>{score_info.get('score')}{score_info.get('scale')}</b> (Research Score)", body_style),
            Paragraph("<b>Formula:</b>", body_style),
            Paragraph(score_info.get("formula", ""), body_style)
        ])

    t_meta = Table(meta_rows, colWidths=[110, 142, 110, 142])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(Paragraph("Analysis & Reference Context", h2_style))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # Landmark & Displacement Metrics
    lm_data = benchmark_data.get("landmark_metrics")
    disp_data = benchmark_data.get("displacement_metrics")

    if lm_data and lm_data.get("pairs"):
        story.append(Paragraph("Paired Landmark Motion Comparison", h2_style))
        lm_table_data = [
            [
                Paragraph("<b>Landmark Label</b>", body_style),
                Paragraph("<b>Ref Disp (px)</b>", body_style),
                Paragraph("<b>Est Disp (px)</b>", body_style),
                Paragraph("<b>Endpoint Error (px)</b>", body_style),
                Paragraph("<b>Disp Difference</b>", body_style)
            ]
        ]

        def fmt_v(v):
            return f"{v:.2f}" if v is not None else "—"

        for p in lm_data["pairs"][:10]:
            ref_mag = p.get("reference_displacement", {}).get("magnitude")
            est_mag = p.get("estimated_displacement", {}).get("magnitude") if p.get("estimated_displacement") else None
            lm_table_data.append([
                Paragraph(p.get("landmark_label", "Landmark"), body_style),
                Paragraph(fmt_v(ref_mag), body_style),
                Paragraph(fmt_v(est_mag), body_style),
                Paragraph(fmt_v(p.get("endpoint_error")), body_style),
                Paragraph(fmt_v(p.get("displacement_error")), body_style)
            ])

        t_lm = Table(lm_table_data, colWidths=[130, 90, 90, 94, 100])
        t_lm.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        story.append(KeepTogether(t_lm))
        story.append(Spacer(1, 14))

    # Geometric Reference Strain
    strain_data = benchmark_data.get("strain_comparison")
    if strain_data and strain_data.get("segments"):
        story.append(Paragraph("Manual Geometric Reference Strain", h2_style))
        strain_table_data = [
            [
                Paragraph("<b>Segment</b>", body_style),
                Paragraph("<b>Initial L0 (px)</b>", body_style),
                Paragraph("<b>Final L1 (px)</b>", body_style),
                Paragraph("<b>Ref Strain (ε)</b>", body_style)
            ]
        ]
        for seg in strain_data["segments"]:
            strain_table_data.append([
                Paragraph(seg.get("segment", "Segment"), body_style),
                Paragraph(f"{seg.get('initial_length', 0):.2f}", body_style),
                Paragraph(f"{seg.get('final_length', 0):.2f}", body_style),
                Paragraph(f"{seg.get('reference_engineering_strain', 0):.4f}", body_style)
            ])

        t_strain = Table(strain_table_data, colWidths=[150, 110, 110, 134])
        t_strain.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        story.append(KeepTogether(t_strain))
        story.append(Spacer(1, 14))

    # Contour & ROI Metrics
    roi_d = benchmark_data.get("roi_metrics")
    if roi_d:
        story.append(Paragraph("ROI & Contour Boundary Concordance", h2_style))
        roi_table_data = [
            [
                Paragraph("<b>Metric</b>", body_style),
                Paragraph("<b>Observed Value</b>", body_style),
                Paragraph("<b>Interpretation</b>", body_style)
            ],
            [
                Paragraph("Intersection over Union (IoU)", body_style),
                Paragraph(f"<b>{roi_d.get('intersection_over_union', 0):.4f}</b>", body_style),
                Paragraph("Area overlap concordance [0, 1]", body_style)
            ],
            [
                Paragraph("Dice Coefficient", body_style),
                Paragraph(f"<b>{roi_d.get('dice_coefficient', 0):.4f}</b>", body_style),
                Paragraph("Harmonic overlap measure [0, 1]", body_style)
            ],
            [
                Paragraph("Centroid Distance", body_style),
                Paragraph(f"{roi_d.get('centroid_distance', 0):.2f} px", body_style),
                Paragraph("Distance between manual & ROI center", body_style)
            ]
        ]
        t_roi = Table(roi_table_data, colWidths=[180, 120, 204])
        t_roi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        story.append(KeepTogether(t_roi))
        story.append(Spacer(1, 14))

    # Limitations
    limitations_text = (
        "<b>Benchmarking Limitations:</b><br/>"
        "• Manual annotations reflect subjective operator judgment and contain intra-observer variance.<br/>"
        "• Landmark tracking error reflects apparent intensity motion rather than physical myocardial tissue tracking.<br/>"
        "• Engineering strain calculated from landmark chords is a 1D chord approximation and does not reflect full tensor mechanics.<br/>"
        "• Concordance scores measure algorithmic agreement with human labels and do not establish clinical validity."
    )
    t_lim = Table([[Paragraph(limitations_text, body_style)]], colWidths=[504])
    t_lim.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))
    story.append(KeepTogether(t_lim))

    doc.build(story, canvasmaker=NumberedCanvas)
    return str(out_path)
