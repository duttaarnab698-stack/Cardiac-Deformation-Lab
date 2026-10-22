"""
backend/app/services/validation_history.py

Storage and retrieval of synthetic validation benchmark runs.
Persists lightweight benchmark metadata in backend/data/validation_history.json.
Isolated from patient studies and clinical analysis history.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VALIDATION_HISTORY_FILE = Path("data/validation_history.json")


def _ensure_file():
    VALIDATION_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not VALIDATION_HISTORY_FILE.exists():
        with open(VALIDATION_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def get_all_validation_history() -> List[Dict[str, Any]]:
    """Retrieve list of past validation benchmark runs."""
    _ensure_file()
    try:
        with open(VALIDATION_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception:
        return []


def save_validation_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Save a validation run record."""
    _ensure_file()
    history = get_all_validation_history()

    item_id = record.get("id") or str(uuid.uuid4())
    record["id"] = item_id
    if "timestamp" not in record:
        record["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Prepend newest
    history.insert(0, record)

    # Keep at most 100 historical benchmark records
    if len(history) > 100:
        history = history[:100]

    with open(VALIDATION_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return record


def get_validation_record_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single validation run record by ID."""
    history = get_all_validation_history()
    for item in history:
        if item.get("id") == record_id or item.get("dataset_id") == record_id:
            return item
    return None

