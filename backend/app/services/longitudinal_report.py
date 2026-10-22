"""
backend/app/services/longitudinal_report.py

PDF Longitudinal Study Report Generator for Cardiac Deformation Lab.
Produces high-quality, professional publication-style PDF reports
summarizing longitudinal deformation kinetics, statistical trends,
first-vs-latest changes, calibration/ROI consistency, and computational quality.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
    Image as ReportLabImage,
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
            self.drawString(54, 750, "Cardiac Deformation Lab — Longitudinal Study Analysis")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(
            54,
            36,
            "Research Prototype • Longitudinal Metric Variation • Not For Clinical Diagnostic Use"
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


def _format_date(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return str(iso_str)[:19]


def _generate_trend_chart_image(timeline: List[Dict[str, Any]], output_img_path: str) -> Optional[str]:
    """Render a clean 2-subplot matplotlib line chart of displacement & strain trends."""
    if len(timeline) < 2:
        return None

    try:
        labels = []
        disp_vals = []
        strain_vals = []

        for i, item in enumerate(timeline):
            lbl = f"S{i+1}"
            ts = item.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    lbl = dt.strftime("%m/%d %H:%M")
                except Exception:
                    pass
            labels.append(lbl)

            m = item.get("metrics", {})
            d = m.get("mean_displacement")
            p = m.get("mean_principal_strain")
            disp_vals.append(d if d is not None else float("nan"))
            strain_vals.append(p if p is not None else float("nan"))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 3.0), dpi=150)
        fig.patch.set_facecolor("#ffffff")

        # Plot 1: Mean Displacement
        ax1.set_facecolor("#f8fafc")
        ax1.plot(range(len(labels)), disp_vals, marker="o", color="#2563eb", linewidth=2.0, markersize=5, label="Displacement (px)")
        ax1.set_title("Mean Displacement Trend (px)", fontsize=10, fontweight="bold", color="#1e293b", pad=8)
        ax1.set_xticks(range(len(labels)))
        ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=8, color="#475569")
        ax1.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
        ax1.tick_params(colors="#475569", labelsize=8)

        # Plot 2: Mean Principal Strain
        ax2.set_facecolor("#f8fafc")
        ax2.plot(range(len(labels)), strain_vals, marker="s", color="#10b981", linewidth=2.0, markersize=5, label="Principal Strain")
        ax2.set_title("Mean Principal Strain Trend", fontsize=10, fontweight="bold", color="#1e293b", pad=8)
        ax2.set_xticks(range(len(labels)))
        ax2.set_xticklabels(labels, rotation=30, ha="right", fontsize=8, color="#475569")
        ax2.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
        ax2.tick_params(colors="#475569", labelsize=8)

        plt.tight_layout()
        plt.savefig(output_img_path, format="png", bbox_inches="tight")
        plt.close(fig)
        return output_img_path
    except Exception:
        plt.close("all")
        return None


def generate_longitudinal_report(
    summary_data: Dict[str, Any],
    output_pdf_path: str
) -> str:
    """
    Generate a comprehensive longitudinal study PDF report.

    Parameters
    ----------
    summary_data : dict
        Returned by build_longitudinal_summary(...)
    output_pdf_path : str
        Target filesystem path for the output PDF.

    Returns
    -------
    str
        Absolute path to the created PDF.
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
        "LongitudinalTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "LongitudinalSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "LongitudinalH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=5,
    )

    body_style = ParagraphStyle(
        "LongitudinalBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    table_header_style = ParagraphStyle(
        "LongitudinalTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#ffffff"),
    )

    table_cell_style = ParagraphStyle(
        "LongitudinalTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "LongitudinalTableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    disclaimer_style = ParagraphStyle(
        "LongitudinalDisclaimer",
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
            "Longitudinal Multi-Session Study Analysis &amp; Kinematic Progression Summary",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

    # ── STUDY METADATA ────────────────────────────────────────────────────────
    study_id = summary_data.get("study_id", "Unknown")
    study_title = summary_data.get("study_title", "Untitled Study")
    subject_code = summary_data.get("subject_code") or "Not Specified"
    analysis_count = summary_data.get("analysis_count", 0)
    first_date = _format_date(summary_data.get("first_analysis_date"))
    latest_date = _format_date(summary_data.get("latest_analysis_date"))
    desc = summary_data.get("description") or "None documented."

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
            Paragraph("Baseline Date:", table_cell_bold),
            Paragraph(first_date, table_cell_style),
            Paragraph("Latest Date:", table_cell_bold),
            Paragraph(latest_date, table_cell_style),
        ],
        [
            Paragraph("Protocol Notes:", table_cell_bold),
            Paragraph(desc, table_cell_style),
            Paragraph("Generated At:", table_cell_bold),
            Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), table_cell_style),
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

    # ── 1. ANALYSIS TIMELINE TABLE ─────────────────────────────────────────────
    story.append(Paragraph("1. Longitudinal Analysis Session Timeline", h1_style))
    timeline = summary_data.get("timeline") or []

    if timeline:
        timeline_rows = [
            [
                Paragraph("Session / Date", table_header_style),
                Paragraph("Analysis ID", table_header_style),
                Paragraph("Type", table_header_style),
                Paragraph("Mean Disp (px)", table_header_style),
                Paragraph("Mean Strain", table_header_style),
                Paragraph("Principal Strain", table_header_style),
                Paragraph("QC Score", table_header_style),
            ]
        ]

        for i, item in enumerate(timeline):
            ts_str = _format_date(item.get("timestamp"))
            aid_short = (item.get("analysis_id") or "")[:8]
            atype = "Temporal" if item.get("type") == "temporal" else "Single Pair"
            m = item.get("metrics") or {}
            d_val = _fmt(m.get("mean_displacement"))
            s_val = _fmt(m.get("mean_strain"))
            p_val = _fmt(m.get("mean_principal_strain"))
            q_val = _fmt(m.get("quality_score"), decimals=0, suffix="/100")
            
            timeline_rows.append([
                Paragraph(f"<b>#{i+1}</b> • {ts_str}", table_cell_style),
                Paragraph(f"<code>{aid_short}</code>", table_cell_style),
                Paragraph(atype, table_cell_style),
                Paragraph(d_val, table_cell_style),
                Paragraph(s_val, table_cell_style),
                Paragraph(p_val, table_cell_style),
                Paragraph(q_val, table_cell_bold),
            ])

        tl_table = Table(timeline_rows, colWidths=[110, 60, 64, 75, 65, 75, 55])
        tl_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(tl_table)
    else:
        story.append(Paragraph("<i>No analysis sessions associated with this study.</i>", body_style))

    story.append(Spacer(1, 10))

    # ── TREND CHART IMAGE ─────────────────────────────────────────────────────
    chart_img_path = str(out_path.parent / f"temp_trend_chart_{study_id[:8]}.png")
    created_chart = _generate_trend_chart_image(timeline, chart_img_path)
    if created_chart and Path(created_chart).exists():
        story.append(KeepTogether([
            Paragraph("<b>Longitudinal Kinematic Trajectories:</b>", table_cell_bold),
            Spacer(1, 3),
            ReportLabImage(created_chart, width=504, height=178),
            Spacer(1, 10),
        ]))

    # ── 2. FIRST VS LATEST ANALYSIS COMPARISON ────────────────────────────────
    first_vs_latest = summary_data.get("first_vs_latest") or {}
    if first_vs_latest.get("available"):
        story.append(Paragraph("2. First vs. Latest Session Quantitative Delta", h1_style))
        f_metrics = first_vs_latest.get("metrics") or {}

        comp_rows = [
            [
                Paragraph("Deformation Metric", table_header_style),
                Paragraph("Baseline Value", table_header_style),
                Paragraph("Latest Value", table_header_style),
                Paragraph("Absolute Delta", table_header_style),
                Paragraph("Relative Change (%)", table_header_style),
                Paragraph("Trend Direction", table_header_style),
            ]
        ]

        for m_key, m_info in f_metrics.items():
            lbl = m_info.get("label", m_key)
            unit_s = f" {m_info.get('unit')}" if m_info.get("unit") else ""
            v1_s = _fmt(m_info.get("first_value"), suffix=unit_s)
            v2_s = _fmt(m_info.get("latest_value"), suffix=unit_s)
            delta_s = _fmt(m_info.get("absolute_change"), suffix=unit_s)
            pct = m_info.get("percentage_change")
            pct_s = f"{pct:+.1f}%" if pct is not None else "—"
            tr = m_info.get("trend", "insufficient_data")

            # Neutral styling for trend
            tr_color = "#2563eb" if tr == "increasing" else ("#7c3aed" if tr == "decreasing" else "#64748b")
            tr_text = f"<font color='{tr_color}'><b>{tr.capitalize()}</b></font>"

            comp_rows.append([
                Paragraph(lbl, table_cell_bold),
                Paragraph(v1_s, table_cell_style),
                Paragraph(v2_s, table_cell_style),
                Paragraph(delta_s, table_cell_style),
                Paragraph(pct_s, table_cell_style),
                Paragraph(tr_text, table_cell_style),
            ])

        comp_table = Table(comp_rows, colWidths=[124, 75, 75, 75, 80, 75])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 10))

    # ── 3. METRIC TREND SUMMARIES ─────────────────────────────────────────────
    trends = summary_data.get("trends") or {}
    if trends:
        story.append(Paragraph("3. Longitudinal Descriptive Statistics &amp; Trajectory Trends", h1_style))
        trend_rows = [
            [
                Paragraph("Tracked Metric", table_header_style),
                Paragraph("N (Obs)", table_header_style),
                Paragraph("Min", table_header_style),
                Paragraph("Max", table_header_style),
                Paragraph("Mean", table_header_style),
                Paragraph("Std Dev", table_header_style),
                Paragraph("Direction", table_header_style),
            ]
        ]

        for m_key, t_info in trends.items():
            if t_info.get("observation_count", 0) > 0:
                lbl = t_info.get("label", m_key)
                n_obs = str(t_info.get("observation_count", 0))
                min_s = _fmt(t_info.get("minimum"))
                max_s = _fmt(t_info.get("maximum"))
                mean_s = _fmt(t_info.get("mean"))
                std_s = _fmt(t_info.get("standard_deviation"))
                direction = t_info.get("trend_direction", "insufficient_data")

                dir_color = "#2563eb" if direction == "increasing" else ("#7c3aed" if direction == "decreasing" else "#64748b")
                dir_label = direction.replace("_", " ").capitalize()

                trend_rows.append([
                    Paragraph(lbl, table_cell_bold),
                    Paragraph(n_obs, table_cell_style),
                    Paragraph(min_s, table_cell_style),
                    Paragraph(max_s, table_cell_style),
                    Paragraph(mean_s, table_cell_style),
                    Paragraph(std_s, table_cell_style),
                    Paragraph(f"<font color='{dir_color}'><b>{dir_label}</b></font>", table_cell_style),
                ])

        t_table = Table(trend_rows, colWidths=[144, 45, 60, 60, 65, 65, 65])
        t_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_table)
        story.append(Spacer(1, 10))

    # ── 4. DATA QUALITY & PROTOCOL CONSISTENCY ────────────────────────────────
    story.append(Paragraph("4. Longitudinal Quality &amp; Protocol Consistency", h1_style))
    qc_sum = summary_data.get("quality_summary") or {}
    cal_sum = summary_data.get("calibration_consistency") or {}
    roi_sum = summary_data.get("roi_consistency") or {}

    avg_qc = qc_sum.get("average_score")
    avg_qc_str = f"{avg_qc:.1f} / 100" if avg_qc is not None else "Unassessed"

    proto_data = [
        [
            Paragraph("Mean QC Score:", table_cell_bold),
            Paragraph(f"<b>{avg_qc_str}</b>", table_cell_bold),
            Paragraph("Quality Tiers:", table_cell_bold),
            Paragraph(f"High: {qc_sum.get('high_count', 0)} | Mod: {qc_sum.get('moderate_count', 0)} | Low: {qc_sum.get('low_count', 0)}", table_cell_style),
        ],
        [
            Paragraph("Calibration:", table_cell_bold),
            Paragraph(f"<b>{cal_sum.get('status', 'none').upper()}</b>: {cal_sum.get('details', '')}", table_cell_style),
            Paragraph("ROI Scope:", table_cell_bold),
            Paragraph(f"<b>{roi_sum.get('status', 'none').upper()}</b>: {roi_sum.get('details', '')}", table_cell_style),
        ],
    ]
    proto_table = Table(proto_data, colWidths=[90, 162, 85, 167])
    proto_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(proto_table)
    story.append(Spacer(1, 8))

    # Warnings & Notices
    warns = summary_data.get("warnings") or []
    infos = summary_data.get("info") or []

    if warns:
        story.append(Paragraph("<b>Longitudinal Quality &amp; Compatibility Warnings:</b>", table_cell_bold))
        for w in warns:
            story.append(Paragraph(f"• <font color='#b45309'>{w}</font>", table_cell_style))
        story.append(Spacer(1, 6))

    if infos:
        story.append(Paragraph("<b>Informational Notes:</b>", table_cell_bold))
        for inf in infos:
            story.append(Paragraph(f"• {inf}", table_cell_style))
        story.append(Spacer(1, 8))

    # ── 5. METHODOLOGY & RESEARCH DISCLAIMER ──────────────────────────────────
    disclaimer_block = [
        Paragraph("5. Technical Interpretation &amp; Research Disclaimer", h1_style),
        Paragraph(
            "<b>Methodological Scope:</b> Longitudinal study analysis evaluates numerical trajectory variations "
            "in image-derived displacement fields, Green-Lagrange strain tensors, and kinematic coherence across "
            "multiple discrete analysis sessions. All trends represent algorithmic differences computed under classical continuum "
            "mechanics and dense Farnebäck optical flow.",
            body_style,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>RESEARCH ONLY — NO CLINICAL DIAGNOSTIC OR PROGRESSION ASSERTIONS:</b><br/>"
            "Longitudinal analysis describes computational changes in image-derived measurements across analysis sessions. "
            "It is not a clinical diagnosis or clinical progression assessment. "
            "Categorizations such as 'increasing', 'decreasing', or 'stable' denote mathematical differentials and "
            "must NOT be interpreted as cardiac recovery, clinical deterioration, or medical efficacy. "
            "This software is an experimental research prototype and must NOT be used as a medical diagnostic device.",
            disclaimer_style,
        ),
    ]
    story.append(KeepTogether(disclaimer_block))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)

    # Clean up temporary chart image
    if created_chart and Path(created_chart).exists():
        try:
            os.remove(created_chart)
        except Exception:
            pass

    return str(out_path.resolve())

