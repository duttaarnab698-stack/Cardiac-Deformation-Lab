"""
backend/app/services/history.py

In-memory analysis history management service for Cardiac Deformation Lab.
Provides storage, retrieval, deletion, and summary extraction for:
- Single pair strain analyses (type: "single_pair")
- Multi-frame temporal sequence analyses (type: "temporal")

Records are kept in-memory for this research prototype without requiring
external database servers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import copy


# In-memory storage for history items (most recent first)
_ANALYSIS_HISTORY: List[Dict[str, Any]] = []


def _extract_summary(record_type: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key high-level scalar descriptors from an analysis result
    for lightweight display in history lists.
    """
    summary: Dict[str, Any] = {
        "mean_displacement": None,
        "max_displacement": None,
        "mean_principal_strain": None,
        "temporal_stability_index": None,
        "has_fingerprint": False,
        "calibration": {
            "enabled": False
        },
        "roi": {
            "enabled": False
        }
    }

    # Calibration presence check
    cal_obj = result.get("calibration")
    if cal_obj and isinstance(cal_obj, dict) and cal_obj.get("enabled"):
        summary["calibration"] = {
            "enabled": True,
            "pixel_spacing_x": cal_obj.get("pixel_spacing_x"),
            "pixel_spacing_y": cal_obj.get("pixel_spacing_y"),
            "unit": cal_obj.get("unit", "mm"),
        }

    # ROI presence check
    roi_obj = result.get("roi")
    if roi_obj and isinstance(roi_obj, dict) and roi_obj.get("enabled"):
        summary["roi"] = {
            "enabled": True,
            "type": roi_obj.get("type"),
            "mode": roi_obj.get("mode", "fixed"),
            "pixel_count": roi_obj.get("pixel_count"),
        }

    # ROI tracking summary check
    track_sum = result.get("tracking_summary") or (roi_obj and isinstance(roi_obj, dict) and roi_obj.get("tracking_summary"))
    if track_sum:
        summary["tracking_summary"] = track_sum
        if "roi" in summary:
            summary["roi"]["tracking_summary"] = track_sum

    # Fingerprint presence check
    fp_obj = result.get("cardiac_deformation_fingerprint")
    if fp_obj and isinstance(fp_obj, dict):
        summary["has_fingerprint"] = True
        fp_data = fp_obj.get("fingerprint") or {}
        if isinstance(fp_data, dict):
            summary["mean_displacement"] = fp_data.get("D_mean")
            summary["max_displacement"] = fp_data.get("D_max")
            summary["mean_principal_strain"] = fp_data.get("epsilon_principal")
            summary["temporal_stability_index"] = fp_data.get("TSI")

    # If displacement wasn't filled from fingerprint, check direct result keys
    if summary["mean_displacement"] is None:
        disp = result.get("displacement")
        if isinstance(disp, dict):
            summary["mean_displacement"] = disp.get("mean_displacement") or disp.get("mean")
            summary["max_displacement"] = disp.get("max_displacement") or disp.get("max")
        elif "mean_displacement" in result:
            summary["mean_displacement"] = result.get("mean_displacement")
            summary["max_displacement"] = result.get("max_displacement")

    # If calibrated physical space is available, also store in summary
    disp_obj = result.get("displacement")
    if isinstance(disp_obj, dict) and disp_obj.get("physical_space"):
        phys = disp_obj["physical_space"]
        summary["physical_displacement"] = {
            "mean": phys.get("mean_displacement"),
            "max": phys.get("max_displacement"),
            "unit": phys.get("unit", "mm"),
        }

    # If strain wasn't filled from fingerprint, check strain_statistics
    if summary["mean_principal_strain"] is None:
        strain_stats = result.get("strain_statistics")
        if isinstance(strain_stats, dict):
            p1 = strain_stats.get("principal_strain_1")
            if isinstance(p1, dict):
                summary["mean_principal_strain"] = p1.get("mean")
            elif "mean_principal_strain_1" in strain_stats:
                summary["mean_principal_strain"] = strain_stats.get("mean_principal_strain_1")

    # For temporal analyses, check temporal_stability or principal_strain_1 summary
    if record_type == "temporal" and summary["temporal_stability_index"] is None:
        p1 = result.get("principal_strain_1")
        if isinstance(p1, dict) and "summary" in p1:
            summary["temporal_stability_index"] = p1["summary"].get("temporal_stability_index")
            if summary["mean_principal_strain"] is None:
                summary["mean_principal_strain"] = p1["summary"].get("mean")

    # Quality Control summary
    qc_obj = result.get("quality_control")
    if qc_obj and isinstance(qc_obj, dict):
        summary["quality_control"] = {
            "score": qc_obj.get("score"),
            "level": qc_obj.get("level"),
            "warnings_count": len(qc_obj.get("warnings", [])),
        }
    else:
        summary["quality_control"] = None

    return summary


def save_analysis_result(
    result: Dict[str, Any],
    record_type: str = "single_pair",
    owner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save an analysis result dictionary into the in-memory history,
    associating it with an optional owner_id.
    """
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create safe deepcopy to avoid mutating source object
    safe_result = copy.deepcopy(result)
    summary = _extract_summary(record_type, safe_result)

    record = {
        "id": record_id,
        "timestamp": timestamp,
        "type": record_type,
        "owner_id": owner_id,
        "summary": summary,
        "result": safe_result,
    }

    # Prepend to history so newer items appear first
    _ANALYSIS_HISTORY.insert(0, record)
    return record


def get_all_history(
    owner_id: Optional[str] = None,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve analysis history items based on role and ownership:
    - Admins: see all history (including legacy)
    - Reviewers: see all history
    - Researchers: see their own history
    - Unauthenticated: return all (legacy compatibility)
    """
    if role == "admin" or role == "reviewer":
        return list(_ANALYSIS_HISTORY)
    elif role == "researcher" and owner_id:
        return [item for item in _ANALYSIS_HISTORY if item.get("owner_id") == owner_id]
    return list(_ANALYSIS_HISTORY)


def get_history_by_id(analysis_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific history record by ID.
    Ensures owner_id is safely defaulted for legacy records.
    """
    for item in _ANALYSIS_HISTORY:
        if item["id"] == analysis_id:
            item.setdefault("owner_id", None)
            return item
    return None


def delete_history_by_id(analysis_id: str) -> bool:
    """
    Delete a specific history record by ID. Returns True if deleted, False if not found.
    """
    global _ANALYSIS_HISTORY
    initial_len = len(_ANALYSIS_HISTORY)
    _ANALYSIS_HISTORY = [item for item in _ANALYSIS_HISTORY if item["id"] != analysis_id]
    return len(_ANALYSIS_HISTORY) < initial_len


def clear_all_history() -> int:
    """
    Delete all history records. Returns count of deleted records.
    """
    global _ANALYSIS_HISTORY
    count = len(_ANALYSIS_HISTORY)
    _ANALYSIS_HISTORY.clear()
    return count

