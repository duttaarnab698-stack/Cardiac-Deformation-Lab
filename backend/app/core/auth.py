"""
backend/app/core/auth.py

FastAPI Authentication and Access Control Dependencies for Cardiac Deformation Lab.
Provides dependency injection helpers:
- get_current_user_optional: Returns safe user or None without raising 401.
- get_current_user: Enforces valid authenticated user.
- require_authenticated_user: Alias for get_current_user.
- require_role: Role-based authorization gate.
- require_admin: Admin-only gate.
"""

from typing import Any, Callable, Dict, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.services.auth import (
    decode_access_token,
    get_user_by_id,
    to_safe_user
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False
)


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[Dict[str, Any]]:
    """
    Dependency that extracts the authenticated user if a valid Bearer token
    is provided. If no token or invalid token, returns None without raising an error.
    Used for endpoints that support both authenticated and legacy public access.
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        return None

    raw_user = get_user_by_id(user_id)
    if not raw_user or not raw_user.get("is_active", True):
        return None

    return to_safe_user(raw_user)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Dependency requiring a valid JWT access token.
    Raises 401 Unauthorized if missing, expired, or invalid.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    raw_user = get_user_by_id(user_id)
    if not raw_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not raw_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    return to_safe_user(raw_user)


# Convenient alias
require_authenticated_user = get_current_user


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Generate a dependency enforcing that the authenticated user
    possesses one of the allowed roles.
    """
    def _role_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles [{', '.join(allowed_roles)}]. Current role: '{user_role}'."
            )
        return current_user

    return _role_checker


def require_admin(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
) -> Dict[str, Any]:
    """Dependency enforcing admin-only access."""
    return current_user

