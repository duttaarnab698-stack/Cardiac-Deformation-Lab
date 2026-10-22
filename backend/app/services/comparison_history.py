"""
backend/app/services/comparison_history.py

Saved Comparisons Persistence Service for Cardiac Deformation Lab.
Persists saved comparison records in backend/data/comparisons.json
using atomic file writes (temporary file + rename).
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import DATA_DIR
from app.core.security import atomic_write_json, safe_load_json

COMPARISONS_FILE = DATA_DIR / "comparisons.json"


def _init_comparisons_file() -> None:
    """Ensure data/comparisons.json exists and contains a valid JSON array."""
    if not COMPARISONS_FILE.exists():
        _atomic_write([])


def _atomic_write(data: List[Dict[str, Any]]) -> None:
    """Safely write JSON array using atomic write."""
    atomic_write_json(COMPARISONS_FILE, data)


def _load_comparisons() -> List[Dict[str, Any]]:
    """Load comparisons from JSON file safely."""
    _init_comparisons_file()
    data = safe_load_json(COMPARISONS_FILE, list)
    if isinstance(data, list):
        return data
    return []


def get_all_comparisons(
    owner_id: Optional[str] = None,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve all saved comparisons (most recent first) filtered by researcher role."""
    comparisons = _load_comparisons()
    comparisons.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    if role == "researcher" and owner_id:
        return [c for c in comparisons if c.get("owner_id") is None or c.get("owner_id") == owner_id]
    return comparisons


def get_comparison_by_id(comparison_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific saved comparison by ID."""
    comparisons = _load_comparisons()
    for c in comparisons:
        if c.get("id") == comparison_id:
            c.setdefault("owner_id", None)
            return c
    return None


def save_comparison(
    analysis_ids: List[str],
    comparison_data: Dict[str, Any],
    title: Optional[str] = None,
    notes: Optional[str] = None,
    owner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a comparison record into comparisons.json without duplicating analysis history.
    """
    comparisons = _load_comparisons()
    comp_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    default_title = f"Comparison of {len(analysis_ids)} Analyses ({', '.join(aid[:6] for aid in analysis_ids)})"

    new_record = {
        "id": comp_id,
        "created_at": now_iso,
        "owner_id": owner_id,
        "title": (title.strip() if title and title.strip() else default_title),
        "notes": notes.strip() if notes else None,
        "analysis_ids": analysis_ids,
        "analysis_count": len(analysis_ids),
        "comparison": comparison_data
    }

    comparisons.insert(0, new_record)
    _atomic_write(comparisons)
    return new_record


def delete_comparison_by_id(comparison_id: str) -> bool:
    """Delete a saved comparison by ID. Returns True if deleted, False if not found."""
    comparisons = _load_comparisons()
    initial_len = len(comparisons)
    filtered = [c for c in comparisons if c.get("id") != comparison_id]
    if len(filtered) < initial_len:
        _atomic_write(filtered)
        return True
    return False

