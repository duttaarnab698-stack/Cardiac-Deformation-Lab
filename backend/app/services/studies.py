"""
backend/app/services/studies.py

Study Management Service for Cardiac Deformation Lab.
Persists study metadata and associated analysis IDs in JSON format
at backend/data/studies.json using an atomic write strategy (temp file + rename).

IMPORTANT PRIVACY NOTICE:
This is an experimental research prototype and NOT a clinical information system.
Real patient names, phone numbers, Aadhaar, government IDs, or protected health
information (PHI) MUST NOT be stored. Use pseudonymous `subject_code` values
(e.g., SUBJ-001, ANONYMOUS-42).
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import DATA_DIR
from app.core.security import atomic_write_json, safe_load_json

STUDIES_FILE = DATA_DIR / "studies.json"


def _init_studies_file():
    """Ensure data/studies.json exists and contains a valid JSON array."""
    if not STUDIES_FILE.exists():
        _atomic_write([])


def _atomic_write(data: List[Dict[str, Any]]) -> None:
    """Safely write JSON array using atomic write."""
    atomic_write_json(STUDIES_FILE, data)


def _load_studies() -> List[Dict[str, Any]]:
    """Load studies from JSON file safely. Returns empty list if corrupt/missing."""
    _init_studies_file()
    data = safe_load_json(STUDIES_FILE, list)
    if isinstance(data, list):
        for s in data:
            s.setdefault("owner_id", None)
        return data
    return []


def get_studies(
    owner_id: Optional[str] = None,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve studies based on user role and ownership:
    - Admins: all studies (including legacy unassigned)
    - Reviewers: all studies (read-only review access)
    - Researchers: only their own studies
    - Unauthenticated (None): all studies (backward compatibility)
    """
    studies = _load_studies()
    if role == "admin" or role == "reviewer":
        filtered = studies
    elif role == "researcher" and owner_id:
        filtered = [s for s in studies if s.get("owner_id") == owner_id]
    else:
        filtered = studies

    # Sort newest first based on created_at or updated_at
    return sorted(filtered, key=lambda s: s.get("created_at", ""), reverse=True)


def get_study_by_id(study_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single study by unique ID."""
    studies = _load_studies()
    for s in studies:
        if s.get("id") == study_id:
            s.setdefault("owner_id", None)
            return s
    return None


def create_study(
    title: str,
    subject_code: Optional[str] = None,
    description: Optional[str] = None,
    owner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new study entry associated with an optional owner_id.
    """
    studies = _load_studies()

    now = datetime.now(timezone.utc).isoformat()
    new_study = {
        "id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
        "owner_id": owner_id,
        "title": title.strip() if title else "Untitled Study",
        "subject_code": subject_code.strip() if subject_code else "",
        "description": description.strip() if description else "",
        "analysis_ids": []
    }

    studies.insert(0, new_study)
    _atomic_write(studies)
    return new_study


def update_study(
    study_id: str,
    title: Optional[str] = None,
    subject_code: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update title, subject code, or description of an existing study."""
    studies = _load_studies()
    for s in studies:
        if s.get("id") == study_id:
            if title is not None:
                s["title"] = title.strip()
            if subject_code is not None:
                s["subject_code"] = subject_code.strip()
            if description is not None:
                s["description"] = description.strip()
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            _atomic_write(studies)
            return s
    return None


def delete_study(study_id: str) -> bool:
    """
    Delete a study record from studies.json.
    NOTE: Does NOT delete analysis history or reports!
    """
    studies = _load_studies()
    initial_len = len(studies)
    updated = [s for s in studies if s.get("id") != study_id]
    if len(updated) < initial_len:
        _atomic_write(updated)
        return True
    return False


def add_analysis_to_study(study_id: str, analysis_id: str) -> Optional[Dict[str, Any]]:
    """
    Associate an analysis ID with a study.
    Prevents duplicate analysis IDs within the same study.
    """
    studies = _load_studies()
    for s in studies:
        if s.get("id") == study_id:
            ids = s.setdefault("analysis_ids", [])
            if analysis_id not in ids:
                ids.append(analysis_id)
                s["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(studies)
            return s
    return None


def remove_analysis_from_study(study_id: str, analysis_id: str) -> Optional[Dict[str, Any]]:
    """
    Remove an analysis ID association from a study.
    Does NOT delete the analysis from global history!
    """
    studies = _load_studies()
    for s in studies:
        if s.get("id") == study_id:
            ids = s.setdefault("analysis_ids", [])
            if analysis_id in ids:
                ids.remove(analysis_id)
                s["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(studies)
            return s
    return None


def get_study_for_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Find which study (if any) contains the given analysis ID."""
    studies = _load_studies()
    for s in studies:
        if analysis_id in s.get("analysis_ids", []):
            return {
                "id": s["id"],
                "title": s["title"],
                "subject_code": s.get("subject_code", "")
            }
    return None

