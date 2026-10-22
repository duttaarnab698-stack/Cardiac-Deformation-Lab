"""
backend/app/services/validation_report.py

Publication-grade PDF validation report generator for synthetic phantom benchmarks
in the Cardiac Deformation Lab.

Uses ReportLab with dynamic NumberedCanvas for page numbering (Page X of Y).
Renders:
- Dataset configuration and phantom geometry
- Quantitative ground-truth vs estimated error metrics
- Side-by-side visualization maps (GT, Estimated, Error)
- Robustness sweep summary if available
- Prominent research prototype and non-diagnostic disclaimers
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as PlatypusImage,
    KeepTogether,
    PageBreak,
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
            self.drawString(54, 750, "Cardiac Deformation Lab — Synthetic Validation Benchmark Report")
            self.drawRightString(612 - 54, 750, "RESEARCH BENCHMARK ONLY")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)

        # Running footer
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(612 - 54, 34, page_str)
        self.drawString(54, 34, "Mathematical Benchmark on Synthetic Phantom Data — Not a Clinical Diagnostic Device")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 612 - 54, 46)

        self.restoreState()


def generate_validation_report(
    validation_data: Dict[str, Any],
    output_pdf_path: str
) -> str:
    """
    Build and save publication-grade PDF validation report.
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

    # Custom styles
    title_style = ParagraphStyle(
        "ValTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "ValSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        "ValH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "ValBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    disclaimer_style = ParagraphStyle(
        "ValDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#991b1b")
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Synthetic Phantom Validation Benchmark", title_style))
    story.append(Paragraph("Quantitative Optical-Flow & Strain Accuracy Evaluation against Mathematical Ground Truth", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # Prominent Disclaimer Callout Box
    disclaimer_text = (
        "<b>RESEARCH BENCHMARK NOTICE:</b> This report evaluates algorithmic motion and strain estimation "
        "against an artificial synthetic phantom with known analytical ground truth. This synthetic experiment "
        "is strictly intended for algorithmic verification and software quality assurance. "
        "It does NOT establish clinical validity, diagnostic accuracy, or safety for human medical evaluation."
    )
    disclaimer_table = Table(
        [[Paragraph(disclaimer_text, disclaimer_style)]],
        colWidths=[504]
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 12))

    # Dataset Metadata Table
    dataset_id = validation_data.get("dataset_id", "Unknown")
    meta = validation_data.get("metadata", {})
    cfg = meta.get("config", {})

    meta_rows = [
        [
            Paragraph("<b>Dataset ID:</b>", body_style),
            Paragraph(f"<font name='Courier'>{dataset_id}</font>", body_style),
            Paragraph("<b>Deformation Mode:</b>", body_style),
            Paragraph(str(validation_data.get("deformation_mode", cfg.get("deformation_mode", "N/A"))).replace("_", " ").title(), body_style)
        ],
        [
            Paragraph("<b>Dimensions:</b>", body_style),
            Paragraph(f"{cfg.get('width', 256)} × {cfg.get('height', 256)} px", body_style),
            Paragraph("<b>Deformation Strength:</b>", body_style),
            Paragraph(str(cfg.get("deformation_strength", 0.05)), body_style)
        ],
        [
            Paragraph("<b>Myocardial Radii:</b>", body_style),
            Paragraph(f"R<sub>in</sub>={cfg.get('inner_radius', 45)} px, R<sub>out</sub>={cfg.get('outer_radius', 75)} px", body_style),
            Paragraph("<b>Noise / Blur:</b>", body_style),
            Paragraph(f"Noise σ={cfg.get('noise_level', 0.0)}, Blur σ={cfg.get('blur_sigma', 0.0)}", body_style)
        ]
    ]

    t_meta = Table(meta_rows, colWidths=[110, 142, 120, 132])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(Paragraph("Phantom & Dataset Configuration", h2_style))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # Quantitative Validation Metrics Table
    val = validation_data.get("validation", {})
    disp_m = val.get("displacement", {}).get("myocardium") or val.get("displacement", {}).get("full_image") or {}
    strain_m = val.get("strain", {}).get("myocardium") or val.get("strain", {}).get("full_image") or {}
    rad_m = val.get("radial") or {}
    circ_m = val.get("circumferential") or {}

    def fmt_val(v, unit=""):
        return f"{v:.4f} {unit}".strip() if v is not None else "N/A"

    metrics_rows = [
        [
            Paragraph("<b>Measurement Category</b>", body_style),
            Paragraph("<b>Mean Abs Error (MAE)</b>", body_style),
            Paragraph("<b>RMSE</b>", body_style),
            Paragraph("<b>Pearson Correlation (r)</b>", body_style),
            Paragraph("<b>Endpoint Error (Mean / Max)</b>", body_style)
        ],
        [
            Paragraph("<b>Displacement Field</b>", body_style),
            Paragraph(fmt_val(disp_m.get("mae"), "px"), body_style),
            Paragraph(fmt_val(disp_m.get("rmse"), "px"), body_style),
            Paragraph(fmt_val(disp_m.get("correlation")), body_style),
            Paragraph(f"{fmt_val(disp_m.get('mean_endpoint_error'), 'px')} / {fmt_val(disp_m.get('max_endpoint_error'), 'px')}", body_style)
        ],
        [
            Paragraph("<b>Principal Strain 1</b>", body_style),
            Paragraph(fmt_val(strain_m.get("mean_absolute_error")), body_style),
            Paragraph(fmt_val(strain_m.get("rmse")), body_style),
            Paragraph(fmt_val(strain_m.get("correlation")), body_style),
            Paragraph(f"Rel Err: {fmt_val(strain_m.get('relative_error'))}", body_style)
        ],
        [
            Paragraph("<b>Radial Deformation</b>", body_style),
            Paragraph(fmt_val(rad_m.get("mae")), body_style),
            Paragraph(fmt_val(rad_m.get("rmse")), body_style),
            Paragraph(fmt_val(rad_m.get("correlation")), body_style),
            Paragraph("—", body_style)
        ],
        [
            Paragraph("<b>Circumferential Deform.</b>", body_style),
            Paragraph(fmt_val(circ_m.get("mae")), body_style),
            Paragraph(fmt_val(circ_m.get("rmse")), body_style),
            Paragraph(fmt_val(circ_m.get("correlation")), body_style),
            Paragraph("—", body_style)
        ]
    ]

    t_metrics = Table(metrics_rows, colWidths=[140, 90, 80, 94, 100])
    t_metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(Paragraph("Quantitative Accuracy vs Ground Truth", h2_style))
    story.append(t_metrics)
    story.append(Spacer(1, 14))

    # Embedded Validation Visualizations
    vis = validation_data.get("visualizations", {})
    disp_vis = vis.get("displacement", {})
    strain_vis = vis.get("strain", {})

    base_dir = Path(".")
    def resolve_img(rel_url):
        if not rel_url:
            return None
        p = base_dir / rel_url.lstrip("/")
        return str(p) if p.exists() else None

    gt_disp_path = resolve_img(disp_vis.get("gt_url"))
    est_disp_path = resolve_img(disp_vis.get("est_url"))
    err_disp_path = resolve_img(disp_vis.get("error_url"))

    if gt_disp_path and est_disp_path and err_disp_path:
        story.append(Paragraph("Displacement Verification Maps", h2_style))
        img_w, img_h = 160, 160
        disp_imgs = [
            [
                Paragraph("<b>Ground Truth</b>", body_style),
                Paragraph("<b>Estimated</b>", body_style),
                Paragraph("<b>Absolute Error</b>", body_style)
            ],
            [
                PlatypusImage(gt_disp_path, width=img_w, height=img_h),
                PlatypusImage(est_disp_path, width=img_w, height=img_h),
                PlatypusImage(err_disp_path, width=img_w, height=img_h)
            ]
        ]
        t_disp_img = Table(disp_imgs, colWidths=[168, 168, 168])
        t_disp_img.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 2)
        ]))
        story.append(KeepTogether(t_disp_img))
        story.append(Spacer(1, 14))

    # Robustness Sweep Table (if available)
    robustness_rows = validation_data.get("robustness_sweep") or []
    if robustness_rows:
        story.append(Paragraph("Robustness Sweep Analysis", h2_style))
        rob_table_data = [
            [
                Paragraph("<b>Noise Level</b>", body_style),
                Paragraph("<b>Blur Sigma</b>", body_style),
                Paragraph("<b>Disp RMSE (px)</b>", body_style),
                Paragraph("<b>Disp Corr (r)</b>", body_style),
                Paragraph("<b>Strain RMSE</b>", body_style),
                Paragraph("<b>Strain Corr (r)</b>", body_style)
            ]
        ]
        for row in robustness_rows[:12]:
            rob_table_data.append([
                Paragraph(str(row.get("noise_level", 0)), body_style),
                Paragraph(str(row.get("blur_sigma", 0)), body_style),
                Paragraph(fmt_val(row.get("displacement_rmse")), body_style),
                Paragraph(fmt_val(row.get("displacement_correlation")), body_style),
                Paragraph(fmt_val(row.get("strain_rmse")), body_style),
                Paragraph(fmt_val(row.get("strain_correlation")), body_style)
            ])

        t_rob = Table(rob_table_data, colWidths=[80, 80, 85, 85, 85, 89])
        t_rob.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        story.append(KeepTogether(t_rob))
        story.append(Spacer(1, 14))

    # Scientific Limitations
    limitations_text = (
        "<b>Scientific Limitations:</b><br/>"
        "• Synthetic deformation is mathematically controlled via affine and coordinate transformations.<br/>"
        "• Synthetic texture is simplified and does not model speckle tracking ultrasound or MRI tagging physics.<br/>"
        "• Optical flow measures apparent intensity motion, which may degrade under out-of-plane cardiac motion.<br/>"
        "• Clinical imaging contains patient-specific anatomy, respiration, arrhythmias, and acoustic shadows.<br/>"
        "• This benchmark serves to verify mathematical consistency and numerical stability of algorithms."
    )
    t_lim = Table([[Paragraph(limitations_text, body_style)]], colWidths=[504])
    t_lim.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))
    story.append(KeepTogether(t_lim))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    return str(out_path)

