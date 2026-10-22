"""
backend/app/services/report.py

Cardiac Deformation Lab PDF Report Generation Service.
Generates comprehensive technical and biomechanical deformation summaries
from single-pair or temporal cardiac strain analyses.

Includes:
- Analysis metadata & timing
- Displacement statistics
- Normal & shear strain tensors
- Principal strain fields
- Advanced metrics (Coherence, Gradient, Anisotropy, Entropy, Deformation Energy)
- Cardiac radial and circumferential deformation
- Temporal metrics (trajectory mean, variance, TSI)
- 10-D Cardiac Deformation Fingerprint table
- Embedded spatial heatmaps & vector maps
- Explicit research prototype disclaimer (no diagnostic / medical assertions)
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as ReportLabImage,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page numbers
    and header/footer rules.
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

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                54,
                750,
                "Cardiac Deformation Lab — Biomechanical Analysis Report"
            )
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(
            54,
            36,
            "Research Prototype • Image-Space Motion Analysis • Not For Diagnostic Use"
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)

        self.restoreState()


def _fmt(val: Any, decimals: int = 4, suffix: str = "") -> str:
    """Format numeric values safely without breaking on None/strings."""
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


def generate_analysis_report(
    history_record: Dict[str, Any],
    output_pdf_path: str
) -> str:
    """
    Generate a publication-grade PDF report from a stored history record.

    Parameters
    ----------
    history_record : dict
        Contains 'id', 'timestamp', 'type', 'result', and 'summary'.
    output_pdf_path : str
        Target file path for the output PDF.

    Returns
    -------
    str
        The absolute path to the generated PDF report.
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

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )

    disclaimer_style = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#b45309"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#ffffff"),
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    analysis_id = history_record.get("id", "Unknown")
    timestamp_raw = history_record.get("timestamp", "")
    record_type = history_record.get("type", "single_pair")
    result = history_record.get("result", {})

    try:
        dt = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        formatted_date = dt.strftime("%B %d, %Y at %H:%M:%S UTC")
    except Exception:
        formatted_date = timestamp_raw

    # ── HEADER & TITLE ────────────────────────────────────────────────────────
    story.append(Paragraph("Cardiac Deformation Lab", title_style))
    story.append(
        Paragraph(
            "Image-Based Cardiac Deformation Mapping &amp; Kinematic Strain Analysis",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=14))

    # ── METADATA TABLE ────────────────────────────────────────────────────────
    type_display = (
        "Multi-Frame Temporal Sequence Analysis"
        if record_type == "temporal"
        else "Single-Pair Differential Strain Analysis"
    )

    meta_data = [
        [
            Paragraph("Analysis ID:", table_cell_bold),
            Paragraph(analysis_id, table_cell_style),
            Paragraph("Analysis Type:", table_cell_bold),
            Paragraph(type_display, table_cell_style),
        ],
        [
            Paragraph("Execution Date:", table_cell_bold),
            Paragraph(formatted_date, table_cell_style),
            Paragraph("Motion Model:", table_cell_bold),
            Paragraph("Dense Farnebäck Optical Flow", table_cell_style),
        ],
    ]

    # Spatial Calibration Metadata
    cal_info = result.get("calibration") or history_record.get("summary", {}).get("calibration") or {}
    cal_enabled = bool(cal_info.get("enabled"))
    if cal_enabled:
        cal_str = f"Enabled: X={cal_info.get('pixel_spacing_x')} {cal_info.get('unit', 'mm')}/px, Y={cal_info.get('pixel_spacing_y')} {cal_info.get('unit', 'mm')}/px"
    else:
        cal_str = "Not provided; displacement values reported in image pixels (px)"

    meta_data.append([
        Paragraph("Spatial Calibration:", table_cell_bold),
        Paragraph(cal_str, table_cell_style),
        Paragraph("Calibration Status:", table_cell_bold),
        Paragraph("Spatially Calibrated" if cal_enabled else "Image-Space Only", table_cell_style),
    ])

    # Analysis Region (ROI) Metadata
    roi_info = result.get("roi") or history_record.get("summary", {}).get("roi") or {}
    roi_enabled = bool(roi_info.get("enabled"))
    is_tracked_roi = bool(roi_info.get("mode") == "tracked" or result.get("tracking_summary"))
    if roi_enabled:
        roi_type_str = str(roi_info.get("type", "Custom")).capitalize()
        roi_px = roi_info.get("pixel_count")
        mode_label = "Tracked ROI" if is_tracked_roi else "Fixed ROI"
        roi_display = f"{mode_label} ({roi_type_str})" + (f" • {roi_px} px" if roi_px else "")
        roi_status = f"{mode_label} ({roi_type_str})"
    else:
        roi_display = "Full Image (All image-space pixels evaluated)"
        roi_status = "Full Image"

    meta_data.append([
        Paragraph("Analysis Region:", table_cell_bold),
        Paragraph(roi_display, table_cell_style),
        Paragraph("Region Scope:", table_cell_bold),
        Paragraph(roi_status, table_cell_style),
    ])

    if record_type == "single_pair":
        img1 = result.get("image1", "N/A")
        img2 = result.get("image2", "N/A")
        meta_data.append([
            Paragraph("Reference Frame (ED):", table_cell_bold),
            Paragraph(img1, table_cell_style),
            Paragraph("Target Frame (ES):", table_cell_bold),
            Paragraph(img2, table_cell_style),
        ])
    else:
        frame_cnt = result.get("frame_count", "N/A")
        pair_cnt = result.get("pair_count", "N/A")
        meta_data.append([
            Paragraph("Frames Analyzed:", table_cell_bold),
            Paragraph(str(frame_cnt), table_cell_style),
            Paragraph("Consecutive Pairs:", table_cell_bold),
            Paragraph(str(pair_cnt), table_cell_style),
        ])

    meta_table = Table(meta_data, colWidths=[120, 132, 120, 132])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ── COMPUTATIONAL ANALYSIS QUALITY CONTROL ────────────────────────────────
    qc_data = result.get("quality_control")
    if qc_data and isinstance(qc_data, dict):
        story.append(Paragraph("Computational Analysis Quality", h1_style))
        story.append(Paragraph(
            "Evaluation of measurable computational properties (image quality, optical-flow stability, "
            "strain tensor validity, and region scope).",
            body_style
        ))

        qc_score = qc_data.get("score", "N/A")
        qc_level = qc_data.get("level", "N/A")
        level_color = "#10b981" if qc_level == "High" else ("#f59e0b" if qc_level == "Moderate" else "#ef4444")

        qc_summary_data = [
            [
                Paragraph("Quality Score:", table_cell_bold),
                Paragraph(f"<b>{qc_score} / 100</b>", table_cell_bold),
                Paragraph("Quality Level:", table_cell_bold),
                Paragraph(f"<font color='{level_color}'><b>{qc_level}</b></font>", table_cell_bold),
            ]
        ]
        qc_summary_table = Table(qc_summary_data, colWidths=[120, 132, 120, 132])
        qc_summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(qc_summary_table)
        story.append(Spacer(1, 8))

        # Component-wise quality scores
        comps = qc_data.get("components", {})
        if comps:
            comp_rows = [
                [
                    Paragraph("Quality Component", table_header_style),
                    Paragraph("Technical Status", table_header_style),
                    Paragraph("Component Score", table_header_style),
                    Paragraph("Weight", table_header_style),
                ]
            ]
            for c_key, c_info in comps.items():
                if isinstance(c_info, dict):
                    c_name = c_info.get("name", c_key)
                    c_status = c_info.get("status", "N/A")
                    c_sc = c_info.get("score")
                    sc_str = f"{c_sc} / 100" if c_sc is not None else "N/A"
                    w_pct = c_info.get("weight_pct")
                    w_str = f"{w_pct}%" if w_pct is not None else "—"
                    comp_rows.append([
                        Paragraph(c_name, table_cell_bold),
                        Paragraph(str(c_status), table_cell_style),
                        Paragraph(sc_str, table_cell_style),
                        Paragraph(w_str, table_cell_style),
                    ])
            comp_table = Table(comp_rows, colWidths=[180, 120, 104, 100])
            comp_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 8))

        # Quality Warnings
        qc_warns = qc_data.get("warnings", [])
        if qc_warns:
            story.append(Paragraph("<b>Analysis Quality Warnings:</b>", table_cell_bold))
            for w in qc_warns:
                story.append(Paragraph(f"• <font color='#b45309'>{w}</font>", table_cell_style))
            story.append(Spacer(1, 6))

        # Information notices
        qc_infos = qc_data.get("info", [])
        if qc_infos:
            story.append(Paragraph("<b>Informational Notices:</b>", table_cell_bold))
            for inf in qc_infos:
                story.append(Paragraph(f"• {inf}", table_cell_style))
            story.append(Spacer(1, 6))

        # Non-diagnostic disclaimer
        story.append(Paragraph(
            "<i>Notice: This quality assessment describes computational properties of the image-analysis pipeline. "
            "It is not a clinical confidence score or diagnostic assessment.</i>",
            disclaimer_style
        ))
        story.append(Spacer(1, 14))

    # ── 1. DISPLACEMENT ANALYSIS ──────────────────────────────────────────────
    disp = result.get("displacement") or {}
    fp_obj = result.get("cardiac_deformation_fingerprint", {}).get("fingerprint", {})

    story.append(Paragraph("1. Displacement &amp; Kinematic Motion", h1_style))

    # Check if physical calibration space is available
    phys_disp = disp.get("physical_space")
    if phys_disp:
        unit_str = phys_disp.get("unit", "mm")
        disp_rows = [
            [
                Paragraph("Metric Parameter", table_header_style),
                Paragraph("Pixel Units (px)", table_header_style),
                Paragraph(f"Physical Units ({unit_str})", table_header_style),
                Paragraph("Description", table_header_style),
            ],
            [
                Paragraph("Mean Displacement", table_cell_bold),
                Paragraph(_fmt(disp.get("mean_displacement") or fp_obj.get("D_mean"), suffix=" px"), table_cell_style),
                Paragraph(_fmt(phys_disp.get("mean_displacement"), suffix=f" {unit_str}"), table_cell_style),
                Paragraph("Average magnitude of displacement vector field", table_cell_style),
            ],
            [
                Paragraph("Maximum Displacement", table_cell_bold),
                Paragraph(_fmt(disp.get("max_displacement") or fp_obj.get("D_max"), suffix=" px"), table_cell_style),
                Paragraph(_fmt(phys_disp.get("max_displacement"), suffix=f" {unit_str}"), table_cell_style),
                Paragraph("Peak regional apparent motion amplitude", table_cell_style),
            ],
            [
                Paragraph("Minimum Displacement", table_cell_bold),
                Paragraph(_fmt(disp.get("min_displacement"), suffix=" px"), table_cell_style),
                Paragraph(_fmt(phys_disp.get("min_displacement"), suffix=f" {unit_str}"), table_cell_style),
                Paragraph("Lowest regional motion magnitude observed", table_cell_style),
            ],
            [
                Paragraph("Displacement Std. Dev.", table_cell_bold),
                Paragraph(_fmt(disp.get("std_displacement"), suffix=" px"), table_cell_style),
                Paragraph(_fmt(phys_disp.get("std_displacement"), suffix=f" {unit_str}"), table_cell_style),
                Paragraph("Spatial heterogeneity of tissue displacement", table_cell_style),
            ],
        ]
        disp_table = Table(disp_rows, colWidths=[130, 95, 95, 184])
    else:
        disp_rows = [
            [
                Paragraph("Metric Parameter", table_header_style),
                Paragraph("Value (Pixel Units)", table_header_style),
                Paragraph("Description", table_header_style),
            ],
            [
                Paragraph("Mean Displacement", table_cell_bold),
                Paragraph(_fmt(disp.get("mean_displacement") or fp_obj.get("D_mean"), suffix=" px"), table_cell_style),
                Paragraph("Average Euclidean magnitude of displacement vector field", table_cell_style),
            ],
            [
                Paragraph("Maximum Displacement", table_cell_bold),
                Paragraph(_fmt(disp.get("max_displacement") or fp_obj.get("D_max"), suffix=" px"), table_cell_style),
                Paragraph("Peak regional apparent motion amplitude across the field", table_cell_style),
            ],
            [
                Paragraph("Minimum Displacement", table_cell_bold),
                Paragraph(_fmt(disp.get("min_displacement"), suffix=" px"), table_cell_style),
                Paragraph("Lowest regional motion magnitude observed", table_cell_style),
            ],
            [
                Paragraph("Displacement Std. Dev.", table_cell_bold),
                Paragraph(_fmt(disp.get("std_displacement"), suffix=" px"), table_cell_style),
                Paragraph("Spatial heterogeneity of tissue displacement", table_cell_style),
            ],
        ]
        disp_table = Table(disp_rows, colWidths=[140, 110, 254])

    disp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(disp_table)
    story.append(Spacer(1, 10))

    # ── 2. STRAIN ANALYSIS ────────────────────────────────────────────────────
    strain_stats = result.get("strain_statistics") or {}
    p1_obj = strain_stats.get("principal_strain_1")
    p1 = p1_obj if isinstance(p1_obj, dict) else {}
    p2_obj = strain_stats.get("principal_strain_2")
    p2 = p2_obj if isinstance(p2_obj, dict) else {}

    story.append(Paragraph("2. Small-Deformation Strain Tensor & Principal Fields", h1_style))
    strain_rows = [
        [
            Paragraph("Strain Component", table_header_style),
            Paragraph("Mean", table_header_style),
            Paragraph("Min", table_header_style),
            Paragraph("Max", table_header_style),
            Paragraph("Std Dev", table_header_style),
        ],
        [
            Paragraph("Normal Exx (du/dx)", table_cell_bold),
            Paragraph(_fmt(strain_stats.get("mean_exx")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("min_exx")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("max_exx")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("std_exx")), table_cell_style),
        ],
        [
            Paragraph("Normal Eyy (dv/dy)", table_cell_bold),
            Paragraph(_fmt(strain_stats.get("mean_eyy")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("min_eyy")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("max_eyy")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("std_eyy")), table_cell_style),
        ],
        [
            Paragraph("Shear Exy (0.5*(du/dy+dv/dx))", table_cell_bold),
            Paragraph(_fmt(strain_stats.get("mean_exy")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("min_exy")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("max_exy")), table_cell_style),
            Paragraph(_fmt(strain_stats.get("std_exy")), table_cell_style),
        ],
        [
            Paragraph("Principal Strain 1 (Major)", table_cell_bold),
            Paragraph(_fmt(p1.get("mean") or strain_stats.get("mean_principal_strain_1") or strain_stats.get("mean_principal_strain") or fp_obj.get("epsilon_principal")), table_cell_style),
            Paragraph(_fmt(p1.get("min")), table_cell_style),
            Paragraph(_fmt(p1.get("max")), table_cell_style),
            Paragraph(_fmt(p1.get("std")), table_cell_style),
        ],
        [
            Paragraph("Principal Strain 2 (Minor)", table_cell_bold),
            Paragraph(_fmt(p2.get("mean") or strain_stats.get("mean_principal_strain_2")), table_cell_style),
            Paragraph(_fmt(p2.get("min")), table_cell_style),
            Paragraph(_fmt(p2.get("max")), table_cell_style),
            Paragraph(_fmt(p2.get("std")), table_cell_style),
        ],
    ]

    strain_table = Table(strain_rows, colWidths=[154, 87, 87, 87, 89])
    strain_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(strain_table)
    story.append(Spacer(1, 10))

    # ── 3. ADVANCED & CARDIAC GEOMETRIC DEFORMATION ───────────────────────────
    def _extract_metric_val(val: Any) -> Any:
        if isinstance(val, dict):
            return val.get("mean") if val.get("mean") is not None else val.get("value")
        return val

    adv = result.get("advanced_metrics") or {}
    cardiac_def = result.get("cardiac_deformation") or {}
    rad = cardiac_def.get("radial") or {}
    circ = cardiac_def.get("circumferential") or {}

    story.append(Paragraph("3. Advanced Deformation Metrics & Geometric Projection", h1_style))
    adv_rows = [
        [
            Paragraph("Metric Parameter", table_header_style),
            Paragraph("Observed Value", table_header_style),
            Paragraph("Physical / Mathematical Interpretation", table_header_style),
        ],
        [
            Paragraph("Motion Coherence", table_cell_bold),
            Paragraph(_fmt(_extract_metric_val(adv.get("motion_coherence")) or fp_obj.get("C")), table_cell_style),
            Paragraph("Cosine consistency of motion vectors within local 5x5 spatial kernels", table_cell_style),
        ],
        [
            Paragraph("Strain Gradient Magnitude", table_cell_bold),
            Paragraph(_fmt(_extract_metric_val(adv.get("strain_gradient")) or fp_obj.get("G_epsilon")), table_cell_style),
            Paragraph("Spatial rate of change of principal strain fields", table_cell_style),
        ],
        [
            Paragraph("Strain Anisotropy Index", table_cell_bold),
            Paragraph(_fmt(_extract_metric_val(adv.get("anisotropy")) or fp_obj.get("AI")), table_cell_style),
            Paragraph("Directional preference of tissue deformation (|e1 - e2| / (|e1| + |e2|))", table_cell_style),
        ],
        [
            Paragraph("Strain Entropy", table_cell_bold),
            Paragraph(_fmt(_extract_metric_val(adv.get("entropy")) or fp_obj.get("H")), table_cell_style),
            Paragraph("Shannon entropy describing dispersion of regional strain histograms", table_cell_style),
        ],
        [
            Paragraph("Deformation Energy", table_cell_bold),
            Paragraph(_fmt(_extract_metric_val(adv.get("deformation_energy"))), table_cell_style),
            Paragraph("Pseudo-elastic strain energy density surrogate (0.5 * Tr(eps * eps))", table_cell_style),
        ],
        [
            Paragraph("Radial Deformation (Mean)", table_cell_bold),
            Paragraph(_fmt(rad.get("mean")), table_cell_style),
            Paragraph("Motion projection along radial axes from ventricular centroid approximation", table_cell_style),
        ],
        [
            Paragraph("Circumferential Deformation (Mean)", table_cell_bold),
            Paragraph(_fmt(circ.get("mean")), table_cell_style),
            Paragraph("Motion projection orthogonal to radial vectors (tangential shortening)", table_cell_style),
        ],
    ]

    adv_table = Table(adv_rows, colWidths=[154, 90, 260])
    adv_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(adv_table)
    story.append(Spacer(1, 10))

    # ── 4. TEMPORAL METRICS (if available) ────────────────────────────────────
    temp_p1_raw = result.get("principal_strain_1")
    temp_p1 = (temp_p1_raw.get("summary") or {}) if isinstance(temp_p1_raw, dict) else {}
    if record_type == "temporal" or temp_p1:
        story.append(Paragraph("4. Multi-Frame Temporal Strain Trajectory", h1_style))
        temp_rows = [
            [
                Paragraph("Temporal Parameter", table_header_style),
                Paragraph("Value", table_header_style),
                Paragraph("Mathematical Definition", table_header_style),
            ],
            [
                Paragraph("Temporal Mean Principal Strain", table_cell_bold),
                Paragraph(_fmt(temp_p1.get("mean")), table_cell_style),
                Paragraph("Average principal strain magnitude across all consecutive frame pairs", table_cell_style),
            ],
            [
                Paragraph("Temporal Std Dev", table_cell_bold),
                Paragraph(_fmt(temp_p1.get("std")), table_cell_style),
                Paragraph("Standard deviation of frame-to-frame strain trajectory", table_cell_style),
            ],
            [
                Paragraph("Trajectory Range (Min - Max)", table_cell_bold),
                Paragraph(f"{_fmt(temp_p1.get('min'))} to {_fmt(temp_p1.get('max'))}", table_cell_style),
                Paragraph("Minimum and peak principal strain observed during cine sequence", table_cell_style),
            ],
            [
                Paragraph("Temporal Stability Index (TSI)", table_cell_bold),
                Paragraph(_fmt(temp_p1.get("temporal_stability_index") or fp_obj.get("TSI")), table_cell_style),
                Paragraph("Smoothness metric 1 / (1 + variance) measuring trajectory stability", table_cell_style),
            ],
        ]
        temp_table = Table(temp_rows, colWidths=[160, 100, 244])
        temp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(temp_table)
        story.append(Spacer(1, 10))

    # ── 4B. TRACKED ROI MOTION ANALYSIS (if applicable) ───────────────────────
    tracking_summary = result.get("tracking_summary") or history_record.get("summary", {}).get("tracking_summary")
    tracking_path = result.get("tracking_path") or []
    if tracking_summary:
        story.append(Paragraph("4B. Tracked Region of Interest (ROI) Motion Analysis", h1_style))

        # Position info
        init_pos_str = "N/A"
        final_pos_str = "N/A"
        net_disp_str = "N/A"
        if tracking_path and len(tracking_path) > 0:
            c0 = tracking_path[0].get("roi", {}).get("center", {})
            cN = tracking_path[-1].get("roi", {}).get("center", {})
            if "x" in c0 and "y" in c0:
                init_pos_str = f"({c0['x']:.1f}, {c0['y']:.1f}) px"
            if "x" in cN and "y" in cN:
                final_pos_str = f"({cN['x']:.1f}, {cN['y']:.1f}) px"
            if "x" in c0 and "y" in c0 and "x" in cN and "y" in cN:
                nd = math.sqrt((cN['x'] - c0['x'])**2 + (cN['y'] - c0['y'])**2)
                net_disp_str = f"{nd:.2f} px"

        track_rows = [
            [
                Paragraph("Tracking Parameter", table_header_style),
                Paragraph("Value", table_header_style),
                Paragraph("Description", table_header_style),
            ],
            [
                Paragraph("Initial ROI Center (Frame 1)", table_cell_bold),
                Paragraph(init_pos_str, table_cell_style),
                Paragraph("User-initialized centroid location in image coordinates", table_cell_style),
            ],
            [
                Paragraph("Terminal ROI Center (Frame N)", table_cell_bold),
                Paragraph(final_pos_str, table_cell_style),
                Paragraph("Final estimated centroid location after frame-to-frame translation", table_cell_style),
            ],
            [
                Paragraph("Net Center Displacement", table_cell_bold),
                Paragraph(net_disp_str, table_cell_style),
                Paragraph("Euclidean distance between initial and terminal ROI centroids", table_cell_style),
            ],
            [
                Paragraph("Mean Tracking Confidence", table_cell_bold),
                Paragraph(_fmt(tracking_summary.get("mean_confidence")), table_cell_style),
                Paragraph("Average tracking reliability score based on coherence, outlier retention, and coverage", table_cell_style),
            ],
            [
                Paragraph("Minimum Tracking Confidence", table_cell_bold),
                Paragraph(_fmt(tracking_summary.get("min_confidence")), table_cell_style),
                Paragraph("Lowest confidence observed during cine sequence", table_cell_style),
            ],
            [
                Paragraph("Tracking Success Rate", table_cell_bold),
                Paragraph(
                    f"{tracking_summary.get('successful_tracking_frames', 0)} / {tracking_summary.get('frame_count', 0)} frames "
                    f"({int(100 * tracking_summary.get('successful_tracking_frames', 0) / max(1, tracking_summary.get('frame_count', 1)))}%)",
                    table_cell_style
                ),
                Paragraph("Fraction of cine frames satisfying optical flow validity thresholds", table_cell_style),
            ],
        ]

        track_table = Table(track_rows, colWidths=[160, 100, 244])
        track_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(track_table)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "<b>Technical Limitation &amp; Non-Diagnostic Protocol:</b> ROI tracking employs rigid 2D translation via median optical "
            "flow without geometric contour warping or out-of-plane deformation compensation. It is an algorithmic estimation "
            "intended strictly for exploratory research visualization, not anatomical diagnosis.",
            disclaimer_style,
        ))
        story.append(Spacer(1, 10))

    # ── 5. CARDIAC DEFORMATION FINGERPRINT (10-D) ──────────────────────────────
    if fp_obj:
        story.append(Paragraph("5. Cardiac Deformation Fingerprint (10-Dimensional)", h1_style))
        fp_rows = [
            [
                Paragraph("Dimension Symbol", table_header_style),
                Paragraph("Canonical Name", table_header_style),
                Paragraph("Value", table_header_style),
            ],
            [Paragraph("D_mean", table_cell_bold), Paragraph("Mean Displacement", table_cell_style), Paragraph(_fmt(fp_obj.get("D_mean"), suffix=" px"), table_cell_style)],
            [Paragraph("D_max", table_cell_bold), Paragraph("Maximum Displacement", table_cell_style), Paragraph(_fmt(fp_obj.get("D_max"), suffix=" px"), table_cell_style)],
            [Paragraph("epsilon_mean", table_cell_bold), Paragraph("Representative Mean Strain", table_cell_style), Paragraph(_fmt(fp_obj.get("epsilon_mean")), table_cell_style)],
            [Paragraph("epsilon_max", table_cell_bold), Paragraph("Representative Max Strain", table_cell_style), Paragraph(_fmt(fp_obj.get("epsilon_max")), table_cell_style)],
            [Paragraph("epsilon_principal", table_cell_bold), Paragraph("Representative Principal Strain", table_cell_style), Paragraph(_fmt(fp_obj.get("epsilon_principal")), table_cell_style)],
            [Paragraph("AI", table_cell_bold), Paragraph("Strain Anisotropy Index", table_cell_style), Paragraph(_fmt(fp_obj.get("AI")), table_cell_style)],
            [Paragraph("H", table_cell_bold), Paragraph("Strain Entropy", table_cell_style), Paragraph(_fmt(fp_obj.get("H")), table_cell_style)],
            [Paragraph("G_epsilon", table_cell_bold), Paragraph("Strain Gradient Magnitude", table_cell_style), Paragraph(_fmt(fp_obj.get("G_epsilon")), table_cell_style)],
            [Paragraph("C", table_cell_bold), Paragraph("Motion Coherence", table_cell_style), Paragraph(_fmt(fp_obj.get("C")), table_cell_style)],
            [Paragraph("TSI", table_cell_bold), Paragraph("Temporal Stability Index", table_cell_style), Paragraph(_fmt(fp_obj.get("TSI")), table_cell_style)],
        ]
        fp_table = Table(fp_rows, colWidths=[120, 230, 154])
        fp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(fp_table)
        story.append(Spacer(1, 12))

    # ── 6. EMBEDDED VISUALIZATION MAPS ────────────────────────────────────────
    # Gather potential image output paths
    img_candidates = []
    outputs = result.get("outputs") or {}
    adv_outputs = result.get("advanced_outputs") or {}
    card_outputs = result.get("cardiac_deformation_outputs") or {}
    tracking_previews = result.get("tracking_previews") or {}

    map_mappings = [
        ("ROI Overlay Boundary", outputs.get("roi_overlay")),
        ("Displacement Heatmap", outputs.get("displacement_heatmap")),
        ("Motion Vector Map", outputs.get("motion_vector_map")),
        ("Principal Strain Heatmap", outputs.get("principal_strain_heatmap")),
        ("Principal Direction Map", outputs.get("principal_direction_map")),
        ("Radial Deformation Map", card_outputs.get("radial_map")),
        ("Circumferential Deformation", card_outputs.get("circumferential_map")),
        ("Motion Coherence Map", adv_outputs.get("motion_coherence_map")),
        ("Deformation Energy Map", adv_outputs.get("deformation_energy_map")),
        ("ROI Tracking Keyframe (Initial)", tracking_previews.get("first")),
        ("ROI Tracking Keyframe (Mid-Cycle)", tracking_previews.get("middle")),
        ("ROI Tracking Keyframe (Terminal)", tracking_previews.get("last")),
    ]

    for label, path_str in map_mappings:
        if path_str and Path(path_str).exists():
            img_candidates.append((label, Path(path_str).resolve()))

    if img_candidates:
        story.append(KeepTogether([
            Paragraph("6. Spatial Deformation Maps &amp; Motion Field Visualizations", h1_style),
            Paragraph(
                "Two-dimensional colormaps generated by OpenCV and matplotlib engines illustrating spatial gradients and vector trajectories.",
                body_style,
            ),
            Spacer(1, 8),
        ]))

        # Render in a 2-column grid
        img_table_data = []
        row = []
        for label, img_path in img_candidates:
            try:
                rl_img = ReportLabImage(str(img_path), width=235, height=160)
                cell = [
                    Paragraph(f"<b>{label}</b>", table_cell_style),
                    Spacer(1, 2),
                    rl_img,
                ]
                row.append(cell)
                if len(row) == 2:
                    img_table_data.append(row)
                    row = []
            except Exception:
                continue

        if row:
            # Odd number of images, fill second column with blank
            row.append([Paragraph("", table_cell_style)])
            img_table_data.append(row)

        if img_table_data:
            img_table = Table(img_table_data, colWidths=[250, 254])
            img_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(img_table)
            story.append(Spacer(1, 10))

    # ── 7. INTERPRETATION & RESEARCH PROTOCOL DISCLAIMER ──────────────────────
    disclaimer_block = [
        Paragraph("7. Technical Interpretation &amp; Research Prototype Disclaimer", h1_style),
        Paragraph(
            "<b>Methodological Scope:</b> The metrics, vector fields, and spatial colormaps detailed in this report "
            "represent apparent image-space deformation computed via Farnebäck dense optical flow and classical continuum "
            "strain tensor decomposition. Measurements are expressed in image coordinate units (pixels) and relative mathematical differentials.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>RESEARCH ONLY — NO CLINICAL DIAGNOSTIC ASSERTIONS:</b><br/>"
            "This software is an experimental computational research prototype. All values, including the Cardiac Deformation "
            "Fingerprint (10-D) and Temporal Stability Index (TSI), are algorithmic descriptors of pixel kinematics. "
            "This system does NOT provide medical diagnoses, clinical risk assessments, normal/abnormal classifications, "
            "or treatment recommendations. This report must NOT be used as a medical device or diagnostic decision-making instrument.",
            disclaimer_style,
        ),
    ]
    story.append(KeepTogether(disclaimer_block))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    return str(out_path.resolve())

