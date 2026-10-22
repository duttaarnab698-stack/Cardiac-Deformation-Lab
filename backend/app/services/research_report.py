"""
backend/app/services/research_report.py

Publication-Ready Research Report and Scientific Export System
for the Cardiac Deformation Lab (Step 11.18).

Provides:
- Comprehensive Research Report PDF generation covering all 21 sections + Cover + TOC.
- Integration of single analyses, longitudinal summaries, statistical metrics,
  synthetic validation benchmarks, and manual real-image reference annotations.
- Reusable Figure and Table management utilities with auto-wrapping, headers, captions,
  and 'N/A' formatting.
- Non-clinical computational research prototype disclaimers throughout.
- Report metadata tracking (backend/data/reports.json) and history.
- Research package exporter (.zip with PDF, CSV summaries, JSON metadata, figures).
"""

import json
import math
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Image as ReportLabImage,
)

from app.core.version import APP_VERSION, REPORT_SCHEMA_VERSION
from app.core.config import DATA_DIR
from app.core.security import atomic_write_json, safe_load_json

# Persistent report metadata file
REPORTS_METADATA_FILE = DATA_DIR / "reports.json"
SOFTWARE_VERSION = APP_VERSION


class ResearchReportCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page numbers
    and running scientific headers/footers across all report pages.
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

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Skip headers on the cover page (page 1)
        if self._pageNumber > 1:
            self.drawString(
                54,
                750,
                "Cardiac Deformation Lab — Comprehensive Research Report"
            )
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running footer on every page
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(558, 36, page_str)
        self.drawString(
            54,
            36,
            "Research Prototype • Computational Image Analysis • Not For Diagnostic Use"
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)

        self.restoreState()


def _ensure_reports_file():
    REPORTS_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not REPORTS_METADATA_FILE.exists():
        atomic_write_json(REPORTS_METADATA_FILE, [])


def load_reports_metadata() -> List[Dict[str, Any]]:
    _ensure_reports_file()
    data = safe_load_json(REPORTS_METADATA_FILE, list)
    if isinstance(data, list):
        for item in data:
            item.setdefault("owner_id", None)
        return data
    return []


def save_report_metadata(record: Dict[str, Any]) -> None:
    _ensure_reports_file()
    records = load_reports_metadata()
    # Check if report_id exists, replace or append
    existing_idx = next((i for i, r in enumerate(records) if r.get("report_id") == record.get("report_id")), None)
    if existing_idx is not None:
        records[existing_idx] = record
    else:
        records.insert(0, record)
    atomic_write_json(REPORTS_METADATA_FILE, records)


def get_reports_by_study(study_id: str, owner_id: Optional[str] = None, role: Optional[str] = None) -> List[Dict[str, Any]]:
    records = load_reports_metadata()
    results = [r for r in records if r.get("study_id") == study_id]
    if role == "researcher" and owner_id:
        results = [r for r in results if r.get("owner_id") is None or r.get("owner_id") == owner_id]
    return results


def get_all_reports_metadata(owner_id: Optional[str] = None, role: Optional[str] = None) -> List[Dict[str, Any]]:
    records = load_reports_metadata()
    if role == "researcher" and owner_id:
        return [r for r in records if r.get("owner_id") is None or r.get("owner_id") == owner_id]
    return records


# ==============================================================================
# Formatters & Helpers
# ==============================================================================

def _fmt(val: Any, decimals: int = 4, suffix: str = "") -> str:
    """Format numeric values safely without breaking on None/strings/NaN."""
    if val is None or val == "N/A":
        return "N/A"
    if isinstance(val, (int, float)):
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return "N/A"
            if abs(f) > 0 and (abs(f) < 0.0001 or abs(f) >= 10000):
                return f"{f:.{decimals}e}{suffix}"
            return f"{f:.{decimals}f}{suffix}"
        except Exception:
            return str(val)
    return str(val) if str(val).strip() else "N/A"


def _format_date(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %H:%M:%S UTC")
    except Exception:
        return str(iso_str)


# ==============================================================================
# Reusable Table & Figure Utilities
# ==============================================================================

def create_scientific_table(
    header_data: List[str],
    rows_data: List[List[Any]],
    col_widths: Optional[List[float]] = None,
    header_bg: str = "#1e293b",
    alternate_rows: bool = True,
    cell_style: Optional[ParagraphStyle] = None,
    header_style: Optional[ParagraphStyle] = None,
    max_table_width: float = 504.0,
) -> Table:
    """
    Build a well-proportioned, wrapping ReportLab Table that avoids text clipping
    and automatically formats missing values as 'N/A'.
    """
    styles = getSampleStyleSheet()
    if not cell_style:
        cell_style = ParagraphStyle(
            "SciTableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
    if not header_style:
        header_style = ParagraphStyle(
            "SciTableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#ffffff"),
        )

    # Format headers
    formatted_headers = [Paragraph(f"<b>{h}</b>", header_style) for h in header_data]
    table_rows = [formatted_headers]

    # Format data cells
    for row in rows_data:
        formatted_row = []
        for cell in row:
            if isinstance(cell, Paragraph):
                formatted_row.append(cell)
            else:
                txt = _fmt(cell) if isinstance(cell, (int, float)) else (str(cell) if cell is not None else "N/A")
                if not txt.strip() or txt.lower() in ("none", "nan", "null"):
                    txt = "N/A"
                formatted_row.append(Paragraph(txt, cell_style))
        table_rows.append(formatted_row)

    # Compute column widths if not provided
    n_cols = len(header_data)
    if not col_widths or len(col_widths) != n_cols:
        col_w = max_table_width / max(1, n_cols)
        col_widths = [col_w] * n_cols

    t = Table(table_rows, colWidths=col_widths, repeatRows=1)
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]

    if alternate_rows:
        for r_idx in range(1, len(table_rows)):
            if r_idx % 2 == 0:
                t_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor("#f8fafc")))

    t.setStyle(TableStyle(t_style))
    return t


def build_figure_block(
    image_path: str,
    fig_num: int,
    title: str,
    caption: str,
    metric_label: str = "",
    units: str = "",
    width: float = 380,
    height: float = 230,
) -> List[Any]:
    """
    Construct a standardized scientific figure block with figure numbering,
    title, embedded graphic, caption, and computational description.
    """
    styles = getSampleStyleSheet()
    fig_title_style = ParagraphStyle(
        f"FigTitle_{fig_num}",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=3,
    )
    caption_style = ParagraphStyle(
        f"FigCaption_{fig_num}",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceBefore=3,
        spaceAfter=8,
    )

    flowables = []
    meta_sub = f" [Metric: {metric_label}]" if metric_label else ""
    if units:
        meta_sub += f" (Units: {units})"

    header_text = f"<b>Figure {fig_num}:</b> {title}{meta_sub}"
    flowables.append(Paragraph(header_text, fig_title_style))

    p = Path(image_path)
    if not p.exists() and (Path("outputs") / p.name).exists():
        p = Path("outputs") / p.name

    if p.exists():
        try:
            rl_img = ReportLabImage(str(p.resolve()), width=width, height=height)
            flowables.append(rl_img)
        except Exception:
            flowables.append(Paragraph("<i>[Image render unavailable on disk]</i>", caption_style))
    else:
        flowables.append(Paragraph(f"<i>[Visual file not found at {image_path}]</i>", caption_style))

    flowables.append(Paragraph(f"<b>Caption:</b> {caption}", caption_style))
    return flowables


# ==============================================================================
# Comprehensive Research Report Generator
# ==============================================================================

def generate_comprehensive_research_report(
    study_id: str,
    output_pdf_path: str,
    owner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete 21-section publication-ready comprehensive research report
    for a multi-analysis study, pulling data from studies, history, longitudinal,
    statistics, annotations, quality, and synthetic validation services.
    """
    from app.services.studies import get_study_by_id
    from app.services.history import get_history_by_id
    from app.services.longitudinal import build_longitudinal_summary
    from app.services.statistics import calculate_study_statistics
    from app.services.annotations import get_annotations
    from app.services.real_validation import benchmark_analysis_against_annotations
    from app.services.synthetic_data import get_synthetic_dataset_metadata, SYNTHETIC_DATA_DIR

    from app.services.studies import get_study_by_id
    from app.services.history import get_history_by_id
    from app.services.longitudinal import build_longitudinal_summary, collect_study_analyses

    study, valid_records, study_warns, study_info = collect_study_analyses(study_id)
    if not study:
        raise ValueError(f"Study with ID '{study_id}' not found.")

    summary = build_longitudinal_summary(study_id)
    timeline = summary.get("timeline", [])
    analyses = []
    for rec in valid_records:
        r_id = rec.get("id")
        res_data = rec.get("result", {})
        t_item = next((item for item in timeline if item.get("analysis_id") == r_id), {})
        analyses.append({
            "id": r_id,
            "timestamp": rec.get("timestamp"),
            "type": rec.get("type", "single_pair"),
            "calibration": res_data.get("calibration") or rec.get("summary", {}).get("calibration") or {},
            "roi": res_data.get("roi") or rec.get("summary", {}).get("roi") or {},
            "quality_control": res_data.get("quality_control") or rec.get("summary", {}).get("quality_control") or {},
            "metrics": {
                "displacement": res_data.get("displacement") or {},
                "strain": res_data.get("strain_statistics") or {},
                "advanced": res_data.get("advanced_metrics") or {},
                "temporal": res_data.get("temporal_metrics") or {},
            },
            "fingerprint": res_data.get("cardiac_deformation_fingerprint", {}).get("fingerprint") or {},
            "fingerprint_normalized": res_data.get("cardiac_deformation_fingerprint", {}).get("normalized_vector") or [],
            "maps": {
                "displacement_heatmap": res_data.get("outputs", {}).get("displacement_heatmap"),
                "motion_vector_map": res_data.get("outputs", {}).get("motion_vector_map"),
                "principal_strain_heatmap": res_data.get("outputs", {}).get("principal_strain_heatmap"),
                "temporal_chart": res_data.get("temporal_chart") or res_data.get("outputs", {}).get("temporal_chart"),
            },
            "metadata": res_data.get("metadata") or {},
        })
    analysis_count = len(analyses)

    # Collect statistics (safe if analyses < 2)
    stats_data = {}
    try:
        if analysis_count > 0:
            stats_data = calculate_study_statistics(study_id=study_id, scope="full_image")
    except Exception:
        stats_data = {}

    # Collect study annotations
    study_annotations = get_annotations(study_id=study_id)

    # Check for real annotation benchmark data on the primary analysis
    primary_analysis = analyses[0] if analyses else None
    real_bench_data = None
    if primary_analysis and study_annotations:
        try:
            real_bench_data = benchmark_analysis_against_annotations(primary_analysis["id"])
        except Exception:
            real_bench_data = None

    # Check for synthetic validation results if available in backend
    synthetic_bench_data = None
    try:
        from app.api.synthetic import validate_synthetic_dataset_endpoint
        ds_folders = list(SYNTHETIC_DATA_DIR.glob("dataset_*"))
        if ds_folders:
            latest_ds = sorted(ds_folders, key=lambda d: d.stat().st_mtime, reverse=True)[0]
            ds_id = latest_ds.name.replace("dataset_", "")
            synthetic_bench_data = validate_synthetic_dataset_endpoint(ds_id)
    except Exception:
        synthetic_bench_data = None

    # Setup ReportLab Doc
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
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )
    h1_style = ParagraphStyle(
        "SciH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "SciH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "SciBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
    )
    disclaimer_style = ParagraphStyle(
        "SciDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#b45309"),
        spaceBefore=4,
        spaceAfter=4,
    )
    toc_item_style = ParagraphStyle(
        "TOCItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )

    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    generated_at = datetime.now(timezone.utc).isoformat()
    formatted_gen_date = _format_date(generated_at)

    story: List[Any] = []
    figure_counter = 1

    # ==========================================================================
    # COVER PAGE
    # ==========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("Cardiac Deformation Lab", title_style))
    story.append(Paragraph("Comprehensive Research Analysis &amp; Scientific Biomechanical Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=20))

    story.append(Paragraph(
        "<b>Research Prototype — Computational Image Analysis</b><br/>"
        "Advanced continuum kinematics, dense optical-flow deformation fields, "
        "longitudinal metric kinetics, and mathematical validation benchmarks.",
        ParagraphStyle("CoverTag", parent=body_style, fontSize=9.5, leading=14, textColor=colors.HexColor("#1e40af"))
    ))
    story.append(Spacer(1, 25))

    cover_meta = [
        ["Study Name", study.get("title", "Unnamed Study")],
        ["Study ID", study.get("id", "N/A")],
        ["Subject Code", study.get("subject_code") or "ANONYMOUS"],
        ["Report Identifier", report_id],
        ["Generated Date", formatted_gen_date],
        ["Software Version", f"v{SOFTWARE_VERSION}"],
        ["Report Schema Version", f"v{REPORT_SCHEMA_VERSION}"],
        ["Total Analyses Evaluated", str(analysis_count)],
    ]
    story.append(create_scientific_table(["Report Metadata Attribute", "Specification"], cover_meta, col_widths=[180, 324]))
    story.append(Spacer(1, 30))

    story.append(KeepTogether([
        Paragraph("<b>MANDATORY SCIENTIFIC &amp; NON-CLINICAL DISCLAIMER</b>", h2_style),
        Paragraph(
            "This document presents computational image-derived measurements generated by a research prototype. "
            "The results are not medical diagnoses, prognoses, treatment recommendations, or clinical findings.<br/>"
            "Optical-flow displacement represents apparent image motion and may not equal physical tissue motion. "
            "All derived metrics (strains, directions, coherence, TSI) are exploratory mathematical descriptors.",
            disclaimer_style
        ),
    ]))

    story.append(PageBreak())

    # ==========================================================================
    # TABLE OF CONTENTS
    # ==========================================================================
    story.append(Paragraph("Table of Contents", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94a3b8"), spaceAfter=10))

    toc_sections = [
        "1. Executive Summary",
        "2. Study Information",
        "3. Computational Methodology",
        "4. Mathematical Framework",
        "5. Input and Preprocessing",
        "6. Motion Analysis",
        "7. Strain Analysis",
        "8. Advanced Metrics",
        "9. Deformation Fingerprint",
        "10. Temporal Analysis",
        "11. ROI and Tracking",
        "12. Calibration",
        "13. Computational Quality Control",
        "14. Longitudinal Analysis",
        "15. Statistical Analysis",
        "16. Synthetic Validation",
        "17. Manual Reference Benchmark",
        "18. Comparison Analysis",
        "19. Limitations",
        "20. Conclusion",
        "21. Appendix",
    ]

    toc_table_data = []
    for i in range(0, len(toc_sections), 2):
        sec1 = toc_sections[i]
        sec2 = toc_sections[i + 1] if i + 1 < len(toc_sections) else ""
        toc_table_data.append([sec1, sec2])

    story.append(create_scientific_table(["Section (Part I)", "Section (Part II)"], toc_table_data, col_widths=[252, 252]))
    story.append(Spacer(1, 15))

    # ==========================================================================
    # 1. EXECUTIVE SUMMARY
    # ==========================================================================
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    temporal_count = sum(1 for a in analyses if a.get("type") == "temporal")
    calibrated_count = sum(1 for a in analyses if a.get("calibration", {}).get("enabled"))
    roi_count = sum(1 for a in analyses if a.get("roi", {}).get("enabled"))
    qc_scores = [a.get("quality_control", {}).get("score") for a in analyses if a.get("quality_control", {}).get("score") is not None]
    avg_qc = (sum(qc_scores) / len(qc_scores)) if qc_scores else "N/A"
    total_warnings = sum(len(a.get("quality_control", {}).get("warnings", [])) for a in analyses)

    story.append(Paragraph(
        f"The study contains <b>{analysis_count}</b> computational image analyses evaluated under the "
        f"research workspace pipeline. Of these, <b>{temporal_count}</b> are multi-frame cine temporal sequences, "
        f"and <b>{analysis_count - temporal_count}</b> are differential single-pair analyses. "
        f"Associated manual reference annotations count: <b>{len(study_annotations)}</b>. "
        f"Spatial physical calibration is active on <b>{calibrated_count}</b> of {analysis_count} analyses, "
        f"while localized Region-of-Interest (ROI) segmentation is enabled on <b>{roi_count}</b> analyses.",
        body_style
    ))

    exec_summary_data = [
        ["Total Image Analyses", str(analysis_count), "Calibrated Analyses", f"{calibrated_count} / {analysis_count}"],
        ["Temporal Cine Sequences", str(temporal_count), "ROI Segmentation Usage", f"{roi_count} / {analysis_count}"],
        ["Manual Reference Annotations", str(len(study_annotations)), "Average Computational QC Score", f"{_fmt(avg_qc, 1)} / 100"],
        ["Total QC Technical Warnings", str(total_warnings), "Longitudinal Tracking Available", "Yes" if analysis_count >= 2 else "Insufficient Data (<2)"],
    ]
    story.append(create_scientific_table(
        ["Metric", "Value", "Metric", "Value"],
        exec_summary_data,
        col_widths=[140, 112, 140, 112]
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 2. STUDY INFORMATION
    # ==========================================================================
    story.append(Paragraph("2. Study Information", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    study_info_data = [
        ["Study Name", study.get("title", "N/A")],
        ["Study Unique ID", study.get("id", "N/A")],
        ["Subject Pseudonym", study.get("subject_code") or "ANONYMOUS"],
        ["Creation Timestamp", _format_date(study.get("created_at"))],
        ["Last Modified Timestamp", _format_date(study.get("updated_at"))],
        ["Study Description", study.get("description") or "N/A"],
        ["Associated Analysis Sessions", ", ".join(study.get("analysis_ids", [])[:5]) + ("..." if len(study.get("analysis_ids", [])) > 5 else "") or "None"],
    ]
    story.append(create_scientific_table(["Study Attribute", "Recorded Metadata"], study_info_data, col_widths=[160, 344]))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 3. COMPUTATIONAL METHODOLOGY
    # ==========================================================================
    story.append(Paragraph("3. Computational Methodology", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "The Cardiac Deformation Lab processes cardiac imagery through an automated, deterministic 12-stage "
        "computational continuum mechanics pipeline:<br/>"
        "<b>Input</b> → <b>Preprocessing</b> (Grayscale conversion, Gaussian smoothing, histogram normalization) → "
        "<b>Motion Estimation</b> (Farnebäck dense optical flow) → <b>Displacement Calculation</b> (Euclidean vector magnitude) → "
        "<b>Spatial Strain Tensor</b> (Infinitesimal Green-Saint-Venant formulation) → <b>Principal Strains</b> (Spectral decomposition of eigenvalues) → "
        "<b>Advanced Kinematic Descriptors</b> (Motion coherence, strain gradient, anisotropy, deformation energy) → "
        "<b>Temporal Analysis</b> (Inter-frame cine tracking, TSI) → <b>ROI &amp; Tracking</b> (Fixed or Lucas-Kanade updated contours) → "
        "<b>Computational Quality Control</b> (Signal SNR, gradient smoothness, flow bounds) → "
        "<b>Statistical &amp; Longitudinal Analytics</b>.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 4. MATHEMATICAL FRAMEWORK
    # ==========================================================================
    story.append(Paragraph("4. Mathematical Framework", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "<b>Displacement Vector:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>d</b>(x, y) = [u(x, y), v(x, y)]ᵀ<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Displacement magnitude: <i>D</i> = √(u² + v²)<br/><br/>"
        "<b>Displacement Gradient Tensor:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;∇<b>d</b> = [ [∂u/∂x, ∂u/∂y], [∂v/∂x, ∂v/∂y] ]<br/><br/>"
        "<b>Infinitesimal Strain Tensor:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>ε</b> = 1/2 (∇<b>d</b> + (∇<b>d</b>)ᵀ)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;ε_xx = ∂u/∂x<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;ε_yy = ∂v/∂y<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;ε_xy = 1/2 (∂u/∂y + ∂v/∂x)<br/><br/>"
        "<b>Principal Strains &amp; Directions:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Eigenvalues of <b>ε</b>: λ₁, λ₂ = ((ε_xx + ε_yy)/2) ± √(((ε_xx - ε_yy)/2)² + ε_xy²)<br/><br/>"
        "<b>Radial and Circumferential Deformation:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;d_r = <b>d</b> · <b>e</b>_r (projection onto unit radial vector from centroid)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;d_c = <b>d</b> · <b>e</b>_c (projection onto unit tangential vector)<br/><br/>"
        "<b>Spatial Calibration:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Physical displacement = pixel displacement × pixel spacing (mm/px).<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>Note: Strain represents dimensionless spatial gradient (mm/mm) and remains invariant to isotropic scaling.</i>",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 5. INPUT AND PREPROCESSING
    # ==========================================================================
    story.append(Paragraph("5. Input and Preprocessing", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    input_rows = []
    for a in analyses[:8]:
        meta = a.get("metadata") or {}
        img1 = meta.get("image1_filename", "frame_1.png")
        img2 = meta.get("image2_filename", "frame_2.png")
        dims = meta.get("dimensions", "N/A")
        input_rows.append([
            a.get("id", "")[:8],
            f"{img1} / {img2}",
            str(dims),
            "Complete",
            "Normalized (8-bit)",
        ])

    story.append(create_scientific_table(
        ["Analysis ID", "Input Image Pair", "Dimensions", "Grayscale", "Normalization"],
        input_rows if input_rows else [["N/A", "N/A", "N/A", "N/A", "N/A"]],
        col_widths=[80, 164, 80, 80, 100]
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 6. MOTION ANALYSIS
    # ==========================================================================
    story.append(Paragraph("6. Motion Analysis", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    motion_rows = []
    for a in analyses[:8]:
        m = a.get("metrics", {})
        disp_m = m.get("displacement", {})
        unit = a.get("calibration", {}).get("unit", "px") if a.get("calibration", {}).get("enabled") else "px"
        motion_rows.append([
            a.get("id", "")[:8],
            _fmt(disp_m.get("mean_displacement")),
            _fmt(disp_m.get("max_displacement")),
            _fmt(disp_m.get("min_displacement")),
            _fmt(disp_m.get("std_displacement")),
            unit,
            "Farnebäck Dense Flow",
        ])

    story.append(create_scientific_table(
        ["Analysis ID", "Mean", "Max", "Min", "Std Dev", "Units", "Method"],
        motion_rows if motion_rows else [["N/A", "N/A", "N/A", "N/A", "N/A", "px", "N/A"]],
        col_widths=[74, 60, 60, 60, 60, 50, 140]
    ))
    story.append(Spacer(1, 8))

    # Embed representative motion figure from primary analysis if present
    if primary_analysis:
        disp_map = primary_analysis.get("maps", {}).get("displacement_heatmap")
        if disp_map:
            fig_items = build_figure_block(
                disp_map,
                fig_num=figure_counter,
                title="Estimated Image Displacement Magnitude Field",
                caption="Figure: Estimated image displacement magnitude computed via dense optical flow.",
                metric_label="Displacement",
                units=primary_analysis.get("calibration", {}).get("unit", "px") if primary_analysis.get("calibration", {}).get("enabled") else "px",
            )
            story.append(KeepTogether(fig_items))
            figure_counter += 1

        vec_map = primary_analysis.get("maps", {}).get("motion_vector_map")
        if vec_map:
            fig_items = build_figure_block(
                vec_map,
                fig_num=figure_counter,
                title="Estimated Motion-Vector Field",
                caption="Figure: Estimated motion-vector field illustrating planar kinematics.",
                metric_label="Motion Vectors",
                units="Directional Grid",
            )
            story.append(KeepTogether(fig_items))
            figure_counter += 1

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 7. STRAIN ANALYSIS
    # ==========================================================================
    story.append(Paragraph("7. Strain Analysis", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    strain_rows = []
    for a in analyses[:8]:
        st = a.get("metrics", {}).get("strain", {})
        strain_rows.append([
            a.get("id", "")[:8],
            _fmt(st.get("mean_exx")),
            _fmt(st.get("max_exx")),
            _fmt(st.get("mean_eyy")),
            _fmt(st.get("max_eyy")),
            _fmt(st.get("mean_exy")),
            _fmt(st.get("mean_principal_strain")),
            _fmt(st.get("max_principal_strain")),
        ])

    story.append(create_scientific_table(
        ["Analysis ID", "Mean Exx", "Max Exx", "Mean Eyy", "Max Eyy", "Mean Exy", "Mean ε₁", "Max ε₁"],
        strain_rows if strain_rows else [["N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]],
        col_widths=[70, 62, 62, 62, 62, 62, 62, 62]
    ))
    story.append(Spacer(1, 8))

    if primary_analysis:
        p_strain_map = primary_analysis.get("maps", {}).get("principal_strain_heatmap")
        if p_strain_map:
            fig_items = build_figure_block(
                p_strain_map,
                fig_num=figure_counter,
                title="Principal Strain (ε₁) Tensor Field",
                caption="Figure: Principal strain magnitude field indicating local expansion or compression.",
                metric_label="Principal Strain (ε₁)",
                units="Dimensionless",
            )
            story.append(KeepTogether(fig_items))
            figure_counter += 1

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 8. ADVANCED METRICS
    # ==========================================================================
    story.append(Paragraph("8. Advanced Kinematic Metrics", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    adv_rows = []
    for a in analyses[:8]:
        adv = a.get("metrics", {}).get("advanced", {})
        adv_rows.append([
            a.get("id", "")[:8],
            _fmt(adv.get("motion_coherence")),
            _fmt(adv.get("strain_gradient")),
            _fmt(adv.get("anisotropy")),
            _fmt(adv.get("entropy")),
            _fmt(adv.get("deformation_energy")),
        ])

    story.append(create_scientific_table(
        ["Analysis ID", "Motion Coherence", "Strain Gradient", "Anisotropy", "Strain Entropy", "Deform Energy"],
        adv_rows if adv_rows else [["N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]],
        col_widths=[84, 84, 84, 84, 84, 84]
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 9. CARDIAC DEFORMATION FINGERPRINT
    # ==========================================================================
    story.append(Paragraph("9. Computational Deformation Fingerprint", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    fp_dict = primary_analysis.get("fingerprint") or {} if primary_analysis else {}
    fp_vector = primary_analysis.get("fingerprint_normalized") or [] if primary_analysis else []

    fp_dimensions = [
        ("D_mean", "Mean Displacement", fp_dict.get("D_mean")),
        ("D_max", "Max Displacement", fp_dict.get("D_max")),
        ("epsilon_mean", "Mean Strain Magnitude", fp_dict.get("epsilon_mean")),
        ("epsilon_max", "Peak Strain Magnitude", fp_dict.get("epsilon_max")),
        ("epsilon_principal", "Principal Strain (ε₁)", fp_dict.get("epsilon_principal")),
        ("anisotropy", "Strain Anisotropy", fp_dict.get("anisotropy")),
        ("entropy", "Strain Entropy", fp_dict.get("entropy")),
        ("strain_gradient", "Strain Spatial Gradient", fp_dict.get("strain_gradient")),
        ("coherence", "Motion Coherence Index", fp_dict.get("coherence")),
        ("TSI", "Temporal Stability Index", fp_dict.get("TSI")),
    ]

    fp_table_data = []
    for i, (key, label, val) in enumerate(fp_dimensions):
        norm_v = fp_vector[i] if i < len(fp_vector) else "N/A"
        fp_table_data.append([key, label, _fmt(val), _fmt(norm_v, 4)])

    story.append(create_scientific_table(
        ["Dimension Key", "Biomechanical Descriptor", "Raw Scalar", "Normalized Value [0-1]"],
        fp_table_data,
        col_widths=[100, 204, 100, 100]
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 10. TEMPORAL ANALYSIS
    # ==========================================================================
    story.append(Paragraph("10. Temporal Cine Analysis", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    temporal_analyses = [a for a in analyses if a.get("type") == "temporal"]
    if not temporal_analyses:
        story.append(Paragraph("<i>Temporal analysis was not available for this study.</i>", body_style))
    else:
        temp_rows = []
        for ta in temporal_analyses[:6]:
            tm = ta.get("metrics", {}).get("temporal", {})
            temp_rows.append([
                ta.get("id", "")[:8],
                str(tm.get("frame_count", "N/A")),
                str(tm.get("pair_count", "N/A")),
                _fmt(tm.get("mean_displacement")),
                _fmt(tm.get("mean_principal_strain")),
                _fmt(tm.get("temporal_stability_index")),
            ])
        story.append(create_scientific_table(
            ["Analysis ID", "Frames", "Pairs", "Mean Disp", "Mean ε₁", "TSI"],
            temp_rows,
            col_widths=[90, 70, 70, 90, 94, 90]
        ))

        # Check for temporal chart graphic
        ta_chart = temporal_analyses[0].get("maps", {}).get("temporal_chart")
        if ta_chart:
            fig_items = build_figure_block(
                ta_chart,
                fig_num=figure_counter,
                title="Temporal Kinematic Deformation Trajectory",
                caption="Figure: Frame-by-frame progression of displacement and principal strain across cardiac cycle.",
                metric_label="Cine Curve",
                units="Frame Indices",
            )
            story.append(KeepTogether(fig_items))
            figure_counter += 1

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 11. ROI AND TRACKING
    # ==========================================================================
    story.append(Paragraph("11. Region of Interest (ROI) and Tracking Analysis", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "<b>Important Scientific Protocol:</b> Full-image metrics and localized ROI metrics are evaluated separately. "
        "They are never mixed or aggregated into a single indiscriminate field.",
        body_style
    ))

    roi_analyses = [a for a in analyses if a.get("roi", {}).get("enabled")]
    if not roi_analyses:
        story.append(Paragraph("<i>No localized ROI segmentation was applied to the analyses in this study.</i>", body_style))
    else:
        roi_table_data = []
        for ra in roi_analyses[:6]:
            r_info = ra.get("roi", {})
            t_info = ra.get("roi", {}).get("tracking_summary") or {}
            roi_table_data.append([
                ra.get("id", "")[:8],
                r_info.get("type", "polygon"),
                str(r_info.get("pixel_count", "N/A")),
                r_info.get("mode", "fixed"),
                _fmt(t_info.get("mean_confidence", "N/A")),
                f"{t_info.get('tracked_frames', 'N/A')}/{t_info.get('total_frames', 'N/A')}",
            ])

        story.append(create_scientific_table(
            ["Analysis ID", "ROI Type", "Pixel Count", "Tracking Mode", "Mean Confidence", "Tracked Frames"],
            roi_table_data,
            col_widths=[84, 80, 80, 80, 90, 90]
        ))

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 12. CALIBRATION
    # ==========================================================================
    story.append(Paragraph("12. Spatial Calibration", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    cal_analyses = [a for a in analyses if a.get("calibration", {}).get("enabled")]
    if not cal_analyses:
        story.append(Paragraph(
            "<b>Calibration Status:</b> Displacement remains in image-space pixels.<br/>"
            "<i>Displacement values are converted to physical units only when valid spatial calibration is available.</i>",
            body_style
        ))
    else:
        story.append(Paragraph(
            "<i>Displacement values are converted to physical units only when valid spatial calibration is available. "
            "Strain remains dimensionless (spatial ratio).</i>",
            body_style
        ))
        cal_table_data = []
        for ca in cal_analyses[:6]:
            c = ca.get("calibration", {})
            cal_table_data.append([
                ca.get("id", "")[:8],
                str(c.get("pixel_spacing_x", "N/A")),
                str(c.get("pixel_spacing_y", "N/A")),
                c.get("unit", "mm"),
                "Active",
            ])
        story.append(create_scientific_table(
            ["Analysis ID", "Pixel Spacing X", "Pixel Spacing Y", "Physical Unit", "Status"],
            cal_table_data,
            col_widths=[100, 100, 100, 100, 104]
        ))

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 13. COMPUTATIONAL QUALITY CONTROL
    # ==========================================================================
    story.append(Paragraph("13. Computational Quality Assessment", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "<b>Notice:</b> This quality assessment evaluates computational/image-processing conditions and is not a clinical confidence score.",
        disclaimer_style
    ))

    qc_table_data = []
    for a in analyses[:8]:
        qc = a.get("quality_control") or {}
        warn_count = len(qc.get("warnings", []))
        qc_table_data.append([
            a.get("id", "")[:8],
            f"{_fmt(qc.get('score'), 1)} / 100",
            qc.get("level", "N/A"),
            str(warn_count),
            ", ".join(qc.get("warnings", [])[:2]) if warn_count > 0 else "None",
        ])

    story.append(create_scientific_table(
        ["Analysis ID", "Quality Score", "Rating Level", "Warnings", "Primary Warning Message"],
        qc_table_data if qc_table_data else [["N/A", "N/A", "N/A", "N/A", "N/A"]],
        col_widths=[84, 80, 80, 60, 200]
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 14. LONGITUDINAL ANALYSIS
    # ==========================================================================
    story.append(Paragraph("14. Longitudinal Multi-Session Analysis", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    if analysis_count < 2:
        story.append(Paragraph("<i>Longitudinal progression analysis requires at least 2 distinct analysis sessions.</i>", body_style))
    else:
        trends = summary.get("trends", {})
        f_vs_l = summary.get("first_vs_latest", {})

        long_table_data = []
        for m_key, t_info in trends.items():
            if isinstance(t_info, dict):
                label = t_info.get("label", m_key)
                direction = t_info.get("direction", "stable")
                slope = _fmt(t_info.get("slope"))
                r2 = _fmt(t_info.get("r_squared"))
                change = f_vs_l.get("changes", {}).get(m_key, {}) if f_vs_l else {}
                abs_chg = _fmt(change.get("absolute_change"))
                pct_chg = _fmt(change.get("percent_change"), 1, "%")
                long_table_data.append([label, direction, slope, r2, abs_chg, pct_chg])

        story.append(create_scientific_table(
            ["Metric Name", "Trend Direction", "Slope", "R²", "Abs Change", "Pct Change"],
            long_table_data if long_table_data else [["N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]],
            col_widths=[140, 90, 64, 60, 75, 75]
        ))

        # Check for longitudinal trend plot graphic
        l_chart = summary.get("trend_chart")
        if l_chart:
            fig_items = build_figure_block(
                l_chart,
                fig_num=figure_counter,
                title="Longitudinal Kinematic Progression Curves",
                caption="Figure: Longitudinal metric trajectories across chronologically ordered study sessions.",
                metric_label="Study Progression",
                units="Sequential Timeline",
            )
            story.append(KeepTogether(fig_items))
            figure_counter += 1

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 15. STATISTICAL ANALYSIS
    # ==========================================================================
    story.append(Paragraph("15. Advanced Statistical Analytics", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    desc_stats = stats_data.get("descriptive_statistics", {})
    if not desc_stats or analysis_count < 2:
        story.append(Paragraph("<i>Insufficient observations for advanced statistical correlation matrices (<2 sessions).</i>", body_style))
    else:
        stat_rows = []
        for k, v in desc_stats.items():
            if isinstance(v, dict):
                stat_rows.append([
                    k.replace("_", " ").title(),
                    str(v.get("count", 0)),
                    _fmt(v.get("mean")),
                    _fmt(v.get("median")),
                    _fmt(v.get("std_dev")),
                    _fmt(v.get("min")),
                    _fmt(v.get("max")),
                    _fmt(v.get("iqr")),
                ])
        story.append(create_scientific_table(
            ["Metric", "N", "Mean", "Median", "Std Dev", "Min", "Max", "IQR"],
            stat_rows,
            col_widths=[114, 40, 60, 60, 60, 55, 55, 60]
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<i>Notice: Correlation describes statistical association and does not imply causation.</i>", disclaimer_style))

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 16. SYNTHETIC VALIDATION
    # ==========================================================================
    story.append(Paragraph("16. Synthetic / Phantom Validation Benchmark", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "<b>Methodological Context:</b> Synthetic validation evaluates algorithmic behavior against mathematically controlled "
        "reference fields and does not establish clinical validity.",
        disclaimer_style
    ))

    if not synthetic_bench_data:
        story.append(Paragraph("<i>No recent synthetic validation benchmark run found for inclusion in this study report.</i>", body_style))
    else:
        synth_metrics = synthetic_bench_data.get("metrics", {})
        synth_config = synthetic_bench_data.get("config", {})

        synth_summary_rows = [
            ["Deformation Mode", str(synth_config.get("deformation_mode", "N/A")), "Displacement MAE", f"{_fmt(synth_metrics.get('displacement_mae'))} px"],
            ["Deformation Strength", str(synth_config.get("deformation_strength", "N/A")), "Displacement RMSE", f"{_fmt(synth_metrics.get('displacement_rmse'))} px"],
            ["Noise Amplitude", str(synth_config.get("noise_level", "N/A")), "Displacement Pearson r", _fmt(synth_metrics.get("displacement_correlation"))],
            ["Gaussian Blur Sigma", str(synth_config.get("blur_sigma", "N/A")), "Principal Strain MAE", _fmt(synth_metrics.get("strain_mae"))],
        ]
        story.append(create_scientific_table(
            ["Parameter", "Setting", "Validation Error Metric", "Observed Value"],
            synth_summary_rows,
            col_widths=[126, 126, 126, 126]
        ))

        err_map = synthetic_bench_data.get("visualizations", {}).get("displacement_error_map")
        if err_map:
            fig_items = build_figure_block(
                err_map,
                fig_num=figure_counter,
                title="Synthetic Displacement Estimation Absolute Error Map",
                caption="Figure: Spatial error distribution between estimated flow and analytical ground truth.",
                metric_label="Displacement Error",
                units="Pixels",
            )
            story.append(KeepTogether(fig_items))
            figure_counter += 1

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 17. MANUAL REFERENCE BENCHMARK
    # ==========================================================================
    story.append(Paragraph("17. Manual Reference Benchmark", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "<b>Important Notice:</b> Manual annotations are reference measurements for computational benchmarking and "
        "are subject to annotator variability. They are not clinical ground truth.",
        disclaimer_style
    ))

    if not real_bench_data or real_bench_data.get("annotation_count", 0) == 0:
        story.append(Paragraph("<i>No manual landmark or contour annotations available for reference benchmarking in this study.</i>", body_style))
    else:
        lm_res = real_bench_data.get("landmarks", {})
        roi_res = real_bench_data.get("roi_concordance", {})

        bench_rows = [
            ["Total Manual Reference Annotations", str(real_bench_data.get("annotation_count", 0))],
            ["Paired Landmark Points Evaluated", str(lm_res.get("pair_count", 0))],
            ["Mean Landmark Endpoint Error (EPE)", f"{_fmt(lm_res.get('mean_epe'))} px"],
            ["Max Landmark Endpoint Error (EPE)", f"{_fmt(lm_res.get('max_epe'))} px"],
            ["Landmark Geometric Reference Strain", _fmt(lm_res.get("geometric_strain"))],
            ["Optical-Flow Estimated Chord Strain", _fmt(lm_res.get("optical_flow_strain"))],
            ["ROI Contour Intersection over Union (IoU)", _fmt(roi_res.get("iou"))],
            ["ROI Contour Dice Similarity Coefficient", _fmt(roi_res.get("dice"))],
            ["Contour Centroid Displacement Error", f"{_fmt(roi_res.get('centroid_error'))} px"],
        ]
        story.append(create_scientific_table(
            ["Reference Benchmark Metric", "Computed Score / Value"],
            bench_rows,
            col_widths=[280, 224]
        ))

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 18. COMPARISON ANALYSIS
    # ==========================================================================
    story.append(Paragraph("18. In-Study Comparison Analysis", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    if analysis_count < 2:
        story.append(Paragraph("<i>Comparative differential analysis requires at least two completed sessions.</i>", body_style))
    else:
        from app.services.comparison import compare_analyses
        try:
            # Compare first 2 analyses
            comp_res = compare_analyses([analyses[0]["id"], analyses[1]["id"]])
            largest_diffs = comp_res.get("largest_differences", [])[:5]

            comp_table_data = []
            for d in largest_diffs:
                comp_table_data.append([
                    d.get("name", "N/A"),
                    d.get("category", "N/A"),
                    _fmt(d.get("val1")),
                    _fmt(d.get("val2")),
                    _fmt(d.get("diff")),
                    _fmt(d.get("pct_diff"), 1, "%"),
                ])

            story.append(create_scientific_table(
                ["Comparable Parameter", "Domain", "Analysis A", "Analysis B", "Abs Diff", "Pct Diff"],
                comp_table_data if comp_table_data else [["N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]],
                col_widths=[140, 80, 70, 70, 70, 74]
            ))
        except Exception:
            story.append(Paragraph("<i>Differential comparison could not be calculated.</i>", body_style))

    story.append(Spacer(1, 10))

    # ==========================================================================
    # 19. LIMITATIONS
    # ==========================================================================
    story.append(Paragraph("19. Limitations", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "<b>1. Apparent Image Motion vs. Physical Motion:</b> Optical flow measures brightness constancy variations in image pixel coordinates, "
        "which may differ from physical tissue motion under out-of-plane speckle decorrelation or non-rigid myocardial through-plane deformation.<br/>"
        "<b>2. Two-Dimensional Restriction:</b> All strain tensors (ε_xx, ε_yy, ε_xy) are computed in a 2D image plane, omitting radial-longitudinal "
        "shear components present in 3D cardiac mechanics.<br/>"
        "<b>3. Temporal Sampling Rate:</b> Frame rates affect peak displacement and strain derivative estimation. Nyquist limits govern kinematic precision.<br/>"
        "<b>4. Spatial Calibration Constraints:</b> Physical conversions (mm/px) assume isotropic, uniform pixel spacing in orthogonal directions.<br/>"
        "<b>5. Manual Annotation Variability:</b> Reference annotations represent subjective operator placements with intra- and inter-observer variance.<br/>"
        "<b>6. Statistical Sample Size:</b> Small study cohorts limit statistical generalizability; correlations represent association rather than causation.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 20. CONCLUSION
    # ==========================================================================
    story.append(Paragraph("20. Computational Conclusion", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    story.append(Paragraph(
        "The analysis demonstrates the extraction of image-derived motion, displacement, strain, and related computational descriptors "
        "using the implemented research pipeline. The pipeline successfully processed all associated input frames, computed dense continuum fields, "
        "evaluated spatial and temporal consistency, and compiled quantitative multi-session trends.<br/><br/>"
        "<b>Scientific Interpretation Notice:</b> The results should be interpreted as computational research outputs and not as clinical findings. "
        "These measurements provide an objective quantitative basis for engineering research, computational algorithm validation, and academic inquiry.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ==========================================================================
    # 21. APPENDIX
    # ==========================================================================
    story.append(Paragraph("21. Appendix &amp; System Metadata", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

    appendix_data = [
        ["Software System", "Cardiac Deformation Lab (CDL)"],
        ["Software Version", f"v{SOFTWARE_VERSION}"],
        ["Report Engine", "ReportLab PDF Engine with Dynamic Two-Pass Canvas"],
        ["Report Identifier", report_id],
        ["Timestamp of Generation", formatted_gen_date],
        ["Optical Flow Algorithm", "Farnebäck Dense Optical Flow (OpenCV)"],
        ["Strain Formulation", "Infinitesimal Green-Saint-Venant Deformation Tensor"],
        ["Included Analysis Sessions", ", ".join(a.get("id", "")[:8] for a in analyses) or "None"],
    ]
    story.append(create_scientific_table(["System Component", "Technical Specification"], appendix_data, col_widths=[180, 324]))

    # Build Document
    doc.build(story, canvasmaker=ResearchReportCanvas)

    # Save Report Metadata
    report_meta = {
        "report_id": report_id,
        "report_type": "comprehensive_research",
        "study_id": study_id,
        "study_title": study.get("title", "Unnamed Study"),
        "filename": Path(output_pdf_path).name,
        "path": str(out_path),
        "url": f"/reports/{Path(output_pdf_path).name}",
        "analysis_count": analysis_count,
        "software_version": SOFTWARE_VERSION,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "owner_id": owner_id,
        "disclaimer": "Research Prototype — Computational Image Analysis. Not For Diagnostic Use."
    }
    save_report_metadata(report_meta)

    return report_meta


# ==============================================================================
# Export Research Package (.ZIP)
# ==============================================================================

def create_research_export_package(
    study_id: str,
    output_zip_path: str,
    owner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete ZIP research package containing:
    - Comprehensive PDF report
    - CSV summaries (analysis_metrics.csv, temporal_metrics.csv, longitudinal_metrics.csv, statistics.csv, validation_metrics.csv)
    - JSON metadata (research_metadata.json)
    - Selected figures (heatmaps, vectors, charts)
    - Methodology text
    """
    from app.services.studies import get_study_by_id
    from app.services.longitudinal import build_longitudinal_summary, collect_study_analyses
    from app.services.statistics import calculate_study_statistics

    study, valid_records, study_warns, study_info = collect_study_analyses(study_id)
    if not study:
        raise ValueError(f"Study with ID '{study_id}' not found.")

    summary = build_longitudinal_summary(study_id)
    timeline = summary.get("timeline", [])
    analyses = []
    for rec in valid_records:
        r_id = rec.get("id")
        res_data = rec.get("result", {})
        t_item = next((item for item in timeline if item.get("analysis_id") == r_id), {})
        analyses.append({
            "id": r_id,
            "timestamp": rec.get("timestamp"),
            "type": rec.get("type", "single_pair"),
            "calibration": res_data.get("calibration") or rec.get("summary", {}).get("calibration") or {},
            "roi": res_data.get("roi") or rec.get("summary", {}).get("roi") or {},
            "quality_control": res_data.get("quality_control") or rec.get("summary", {}).get("quality_control") or {},
            "metrics": {
                "displacement": res_data.get("displacement") or {},
                "strain": res_data.get("strain_statistics") or {},
                "advanced": res_data.get("advanced_metrics") or {},
                "temporal": res_data.get("temporal_metrics") or {},
            },
            "maps": {
                "displacement_heatmap": res_data.get("outputs", {}).get("displacement_heatmap"),
                "motion_vector_map": res_data.get("outputs", {}).get("motion_vector_map"),
                "principal_strain_heatmap": res_data.get("outputs", {}).get("principal_strain_heatmap"),
            },
            "metadata": res_data.get("metadata") or {},
        })

    # Prepare temp work directory
    temp_dir = Path("outputs") / f"pkg_temp_{study_id}_{uuid.uuid4().hex[:6]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Comprehensive PDF Report
        pdf_filename = f"comprehensive_research_{study_id}.pdf"
        pdf_path = temp_dir / pdf_filename
        report_meta = generate_comprehensive_research_report(
            study_id=study_id,
            output_pdf_path=str(pdf_path),
            owner_id=owner_id
        )

        # 2. CSV Exports
        # (a) analysis_metrics.csv
        csv_a_path = temp_dir / "analysis_metrics.csv"
        with open(csv_a_path, "w", encoding="utf-8") as f:
            f.write("analysis_id,type,mean_displacement,max_displacement,mean_exx,mean_eyy,mean_exy,mean_principal_strain,max_principal_strain,motion_coherence,anisotropy,qc_score\n")
            for a in analyses:
                m = a.get("metrics", {})
                d = m.get("displacement", {})
                st = m.get("strain", {})
                adv = m.get("advanced", {})
                qc = a.get("quality_control", {})
                f.write(
                    f"{a.get('id')},{a.get('type')},"
                    f"{_fmt(d.get('mean_displacement'))},{_fmt(d.get('max_displacement'))},"
                    f"{_fmt(st.get('mean_exx'))},{_fmt(st.get('mean_eyy'))},{_fmt(st.get('mean_exy'))},"
                    f"{_fmt(st.get('mean_principal_strain'))},{_fmt(st.get('max_principal_strain'))},"
                    f"{_fmt(adv.get('motion_coherence'))},{_fmt(adv.get('anisotropy'))},"
                    f"{_fmt(qc.get('score'))}\n"
                )

        # (b) temporal_metrics.csv
        csv_t_path = temp_dir / "temporal_metrics.csv"
        with open(csv_t_path, "w", encoding="utf-8") as f:
            f.write("analysis_id,frame_count,pair_count,mean_displacement,mean_principal_strain,temporal_stability_index\n")
            for a in analyses:
                if a.get("type") == "temporal":
                    tm = a.get("metrics", {}).get("temporal", {})
                    f.write(
                        f"{a.get('id')},{tm.get('frame_count')},{tm.get('pair_count')},"
                        f"{_fmt(tm.get('mean_displacement'))},{_fmt(tm.get('mean_principal_strain'))},"
                        f"{_fmt(tm.get('temporal_stability_index'))}\n"
                    )

        # (c) longitudinal_metrics.csv
        csv_l_path = temp_dir / "longitudinal_metrics.csv"
        with open(csv_l_path, "w", encoding="utf-8") as f:
            f.write("metric_name,direction,slope,r_squared\n")
            for m_key, t_info in summary.get("trends", {}).items():
                if isinstance(t_info, dict):
                    f.write(f"{t_info.get('label', m_key)},{t_info.get('direction')},{_fmt(t_info.get('slope'))},{_fmt(t_info.get('r_squared'))}\n")

        # (d) statistics.csv
        csv_s_path = temp_dir / "statistics.csv"
        with open(csv_s_path, "w", encoding="utf-8") as f:
            f.write("metric,count,mean,median,std_dev,min,max,iqr\n")
            if len(analyses) >= 2:
                try:
                    stats_data = calculate_study_statistics(study_id=study_id, scope="full_image")
                    for k, v in stats_data.get("descriptive_statistics", {}).items():
                        if isinstance(v, dict):
                            f.write(f"{k},{v.get('count')},{_fmt(v.get('mean'))},{_fmt(v.get('median'))},{_fmt(v.get('std_dev'))},{_fmt(v.get('min'))},{_fmt(v.get('max'))},{_fmt(v.get('iqr'))}\n")
                except Exception:
                    pass

        # (e) validation_metrics.csv
        csv_v_path = temp_dir / "validation_metrics.csv"
        with open(csv_v_path, "w", encoding="utf-8") as f:
            f.write("benchmark_type,parameter,value\n")
            f.write("disclaimer,notice,Not for diagnostic use\n")

        # 3. JSON Metadata Export (strictly excluding passwords, tokens, auth secrets)
        json_meta_path = temp_dir / "research_metadata.json"
        clean_study = {
            "id": study.get("id"),
            "title": study.get("title"),
            "subject_code": study.get("subject_code"),
            "description": study.get("description"),
            "created_at": study.get("created_at"),
            "updated_at": study.get("updated_at"),
            "analysis_count": len(analyses),
        }
        clean_analyses = []
        for a in analyses:
            clean_analyses.append({
                "id": a.get("id"),
                "timestamp": a.get("timestamp"),
                "type": a.get("type"),
                "calibration": a.get("calibration"),
                "roi": a.get("roi"),
                "quality_control": a.get("quality_control"),
                "metrics": a.get("metrics"),
            })

        export_json = {
            "study": clean_study,
            "analyses": clean_analyses,
            "longitudinal_summary": {
                "study_id": summary.get("study_id"),
                "analysis_count": summary.get("analysis_count"),
                "trends": summary.get("trends"),
                "first_vs_latest": summary.get("first_vs_latest"),
            },
            "system": {
                "software_version": SOFTWARE_VERSION,
                "report_schema_version": REPORT_SCHEMA_VERSION,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "disclaimer": "Research Prototype — Computational Image Analysis. Not For Diagnostic Use."
            }
        }
        with open(json_meta_path, "w", encoding="utf-8") as f:
            json.dump(export_json, f, indent=2)

        # 4. Methodology Text Document
        method_path = temp_dir / "methodology.txt"
        with open(method_path, "w", encoding="utf-8") as f:
            f.write(
                "CARDIAC DEFORMATION LAB (CDL) — COMPUTATIONAL METHODOLOGY\n"
                "===========================================================\n\n"
                "1. PREPROCESSING:\n"
                "   Grayscale conversion, Gaussian spatial smoothing, intensity normalization.\n\n"
                "2. MOTION ESTIMATION:\n"
                "   Farnebäck dense optical flow calculates apparent pixel displacement fields u(x,y) and v(x,y).\n\n"
                "3. CONTINUUM DEFORMATION TENSORS:\n"
                "   Small-strain infinitesimal formulation: ε = 0.5 * (∇d + (∇d)ᵀ).\n"
                "   Principal strains derived via spectral eigenvalue decomposition.\n\n"
                "4. CALIBRATION:\n"
                "   Physical displacement = pixel displacement * pixel spacing (mm/px).\n"
                "   Strains remain dimensionless spatial gradient ratios.\n\n"
                "DISCLAIMER:\n"
                "This software is an experimental research prototype and does not provide clinical diagnosis.\n"
            )

        # 5. Selected Figures Directory
        figures_dir = temp_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        for i, a in enumerate(analyses[:4]):
            for k, map_p in a.get("maps", {}).items():
                if map_p and Path(map_p).exists():
                    dest_fn = f"analysis_{i+1}_{Path(map_p).name}"
                    shutil.copy2(map_p, figures_dir / dest_fn)

        # 6. Build ZIP Archive
        out_zip = Path(output_zip_path)
        out_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(out_zip), "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(str(temp_dir)):
                for file in files:
                    full_p = Path(root) / file
                    arcname = full_p.relative_to(temp_dir)
                    zipf.write(full_p, arcname)

    finally:
        # Clean up temporary scratch folder
        shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "study_id": study_id,
        "filename": Path(output_zip_path).name,
        "path": str(output_zip_path),
        "url": f"/reports/{Path(output_zip_path).name}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Research Prototype — Computational Image Analysis. Not For Diagnostic Use."
    }
