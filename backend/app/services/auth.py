"""
backend/app/services/auth.py

Research Workspace User Accounts, Authentication, and Access Control Service
for the Cardiac Deformation Lab.

Provides:
- User model persistence in backend/data/users.json
- PBKDF2-HMAC-SHA256 secure password hashing and verification
- JWT access token generation and validation (PyJWT)
- Safe user representations (passwords NEVER exposed in responses, logs, or history)
- Role-based authorization: "researcher", "reviewer", "admin"
- Development demo seed mechanism
- Non-clinical research security disclaimers
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jwt

from app.core.config import (
    JWT_SECRET_KEY,
    JWT_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    ENVIRONMENT,
    DATA_DIR
)
from app.core.security import atomic_write_json, safe_load_json

USERS_FILE = DATA_DIR / "users.json"
SUPPORTED_ROLES = ("researcher", "reviewer", "admin")
DEFAULT_ROLE = "researcher"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Storage & JSON Management
# ---------------------------------------------------------------------------

def _ensure_users_file() -> None:
    """Ensure data/users.json exists and is initialized."""
    if not USERS_FILE.exists():
        atomic_write_json(USERS_FILE, [])


def _load_all_users() -> List[Dict[str, Any]]:
    """Safely load users from JSON file."""
    _ensure_users_file()
    data = safe_load_json(USERS_FILE, list)
    if isinstance(data, list):
        return data
    return []


def _save_all_users(users: List[Dict[str, Any]]) -> None:
    """Save users using crash-safe atomic write."""
    atomic_write_json(USERS_FILE, users)


# ---------------------------------------------------------------------------
# Password Security (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 100,000 iterations
    and a cryptographically random 16-byte salt.
    """
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    
    salt = secrets.token_hex(16)
    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash using
    constant-time string comparison to prevent timing side-channels.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        calc_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        return hmac.compare_digest(calc_bytes.hex(), expected_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT Authentication Tokens
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "cardiac-deformation-lab"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token. Returns None if expired or invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ---------------------------------------------------------------------------
# Safe User Model & Validation
# ---------------------------------------------------------------------------

def to_safe_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a user record into a safe dictionary that NEVER exposes
    the password_hash or sensitive internal fields.
    """
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "role": user.get("role", DEFAULT_ROLE),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at")
    }


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


# ---------------------------------------------------------------------------
# User Service Operations (CRUD)
# ---------------------------------------------------------------------------

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve raw user record by user ID."""
    users = _load_all_users()
    for u in users:
        if u.get("id") == user_id:
            return u
    return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve raw user record by email (case-insensitive)."""
    if not email:
        return None
    norm_email = email.strip().lower()
    users = _load_all_users()
    for u in users:
        if u.get("email", "").strip().lower() == norm_email:
            return u
    return None


def create_user(
    name: str,
    email: str,
    password: str,
    role: str = DEFAULT_ROLE
) -> Dict[str, Any]:
    """
    Register and persist a new user account.
    Returns safe user object.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Name cannot be empty.")

    email = (email or "").strip().lower()
    if not validate_email(email):
        raise ValueError("Invalid email format.")

    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    role = (role or DEFAULT_ROLE).lower().strip()
    if role not in SUPPORTED_ROLES:
        raise ValueError(f"Invalid role '{role}'. Supported roles: {', '.join(SUPPORTED_ROLES)}")

    if get_user_by_email(email) is not None:
        raise ValueError("An account with this email already exists.")

    user_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    hashed = hash_password(password)

    new_user = {
        "id": user_id,
        "name": name,
        "email": email,
        "password_hash": hashed,
        "role": role,
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso
    }

    users = _load_all_users()
    users.append(new_user)
    _save_all_users(users)

    return to_safe_user(new_user)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verify user credentials. Returns raw user record on success, None on failure.
    Checks that the user exists, is active, and password matches.
    """
    user = get_user_by_email(email)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


def update_user_name(user_id: str, new_name: str) -> Optional[Dict[str, Any]]:
    """Update user's display name."""
    clean_name = (new_name or "").strip()
    if not clean_name:
        raise ValueError("Name cannot be empty.")

    users = _load_all_users()
    for u in users:
        if u.get("id") == user_id:
            u["name"] = clean_name
            u["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_all_users(users)
            return to_safe_user(u)
    return None


def update_user_password(
    user_id: str,
    current_password: str,
    new_password: str
) -> bool:
    """Safely update user's password verifying current password."""
    if not new_password or len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters.")

    users = _load_all_users()
    for u in users:
        if u.get("id") == user_id:
            if not verify_password(current_password, u.get("password_hash", "")):
                raise ValueError("Current password is incorrect.")
            u["password_hash"] = hash_password(new_password)
            u["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_all_users(users)
            return True
    return False


def update_user_role(user_id: str, new_role: str) -> Optional[Dict[str, Any]]:
    """Admin function: change a user's role."""
    new_role = (new_role or "").lower().strip()
    if new_role not in SUPPORTED_ROLES:
        raise ValueError(f"Invalid role '{new_role}'. Supported roles: {', '.join(SUPPORTED_ROLES)}")

    users = _load_all_users()
    for u in users:
        if u.get("id") == user_id:
            u["role"] = new_role
            u["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_all_users(users)
            return to_safe_user(u)
    return None


def set_user_active_status(user_id: str, is_active: bool) -> Optional[Dict[str, Any]]:
    """Admin function: activate or deactivate a user account."""
    users = _load_all_users()
    for u in users:
        if u.get("id") == user_id:
            u["is_active"] = bool(is_active)
            u["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_all_users(users)
            return to_safe_user(u)
    return None


def list_all_users() -> List[Dict[str, Any]]:
    """Retrieve all users as safe dictionaries (Admin only)."""
    users = _load_all_users()
    return [to_safe_user(u) for u in sorted(users, key=lambda x: x.get("created_at", ""), reverse=True)]


# ---------------------------------------------------------------------------
# Development Seed Mechanism
# ---------------------------------------------------------------------------

def seed_dev_users() -> List[Dict[str, Any]]:
    """
    Seed initial development accounts for researcher, reviewer, and admin.
    ONLY permitted when ENVIRONMENT == 'development'.
    """
    if ENVIRONMENT != "development":
        raise PermissionError("Dev seed mechanism is strictly disabled outside development environment.")

    dev_accounts = [
        ("Demo Researcher", "demo@cardiaclab.local", "DemoResearcher123!", "researcher"),
        ("Clinical Reviewer", "reviewer@cardiaclab.local", "ReviewerPass123!", "reviewer"),
        ("System Administrator", "admin@cardiaclab.local", "AdminPass123!", "admin")
    ]

    seeded = []
    for name, email, pwd, role in dev_accounts:
        existing = get_user_by_email(email)
        if not existing:
            u = create_user(name=name, email=email, password=pwd, role=role)
            seeded.append({"email": email, "role": role, "default_password": pwd, "status": "created"})
        else:
            seeded.append({"email": email, "role": existing.get("role"), "status": "already_exists"})

    return seeded

