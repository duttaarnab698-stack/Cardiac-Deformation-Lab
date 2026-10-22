"""
backend/app/api/auth.py

API Router for User Authentication, Account Management, and Role Administration
in the Cardiac Deformation Lab Research Workspace.

Endpoints:
- POST /api/auth/register       : Register new research user account
- POST /api/auth/login          : Authenticate and obtain JWT access token
- GET  /api/auth/me             : Retrieve current authenticated user profile
- POST /api/auth/logout         : Logout confirmation
- PUT  /api/auth/profile        : Update name or password for current user
- GET  /api/auth/users          : List all users (Admin only)
- PUT  /api/auth/users/{id}/role: Update user role (Admin only)
- POST /api/auth/users/{id}/status: Activate / deactivate user (Admin only)
- POST /api/auth/dev-seed       : Development-only demo seed endpoint
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    to_safe_user,
    update_user_name,
    update_user_password,
    update_user_role,
    set_user_active_status,
    list_all_users,
    seed_dev_users,
    SUPPORTED_ROLES
)
from app.core.auth import (
    get_current_user,
    require_admin
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication & Workspace"]
)


# ---------------------------------------------------------------------------
# Pydantic Request / Response Models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Full name or research identifier")
    email: str = Field(..., description="Valid institutional or research email")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    role: Optional[str] = Field("researcher", description="Account role: researcher, reviewer, admin")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Updated display name")
    current_password: Optional[str] = Field(None, description="Current password for verification")
    new_password: Optional[str] = Field(None, min_length=8, description="New password (optional)")


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="New role: researcher, reviewer, admin")


class StatusUpdateRequest(BaseModel):
    is_active: bool = Field(..., description="True to activate, False to deactivate")


# ---------------------------------------------------------------------------
# Public Authentication Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_endpoint(payload: RegisterRequest):
    """
    Register a new research workspace user account.
    Default role is 'researcher'.
    """
    try:
        user = create_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=payload.role or "researcher"
        )
        token = create_access_token(user_id=user["id"], role=user.get("role", "researcher"))
        return {
            "message": "User registered successfully.",
            "user": user,
            "access_token": token,
            "token": token,
            "token_type": "bearer"
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(err)}"
        )


@router.post("/login")
def login_endpoint(payload: LoginRequest):
    """
    Authenticate user with email and password.
    Returns JWT bearer access token and safe user profile.
    """
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(user_id=user["id"], role=user.get("role", "researcher"))
    safe_user = to_safe_user(user)

    return {
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "user": safe_user,
        "message": f"Welcome back, {safe_user['name']}!"
    }


@router.post("/logout")
def logout_endpoint():
    """
    Logout endpoint. Client discards local JWT token.
    """
    return {
        "message": "Logged out successfully. Clear client token from storage."
    }


# ---------------------------------------------------------------------------
# Protected User Profile Endpoints
# ---------------------------------------------------------------------------

@router.get("/me")
def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve currently authenticated user profile.
    """
    return {
        **current_user,
        "user": current_user,
        "disclaimer": "Research workspace authentication. Not intended for clinical hospital deployment."
    }


@router.put("/profile")
def update_profile_endpoint(
    payload: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update display name or password for the currently authenticated user.
    """
    user_id = current_user["id"]
    updated_user = current_user

    # Name change
    if payload.name:
        try:
            res = update_user_name(user_id, payload.name)
            if res:
                updated_user = res
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

    # Password change
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=400,
                detail="Current password is required to set a new password."
            )
        try:
            success = update_user_password(
                user_id=user_id,
                current_password=payload.current_password,
                new_password=payload.new_password
            )
            if not success:
                raise HTTPException(status_code=400, detail="Password update failed.")
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

    return {
        "message": "Profile updated successfully.",
        "user": updated_user
    }


# ---------------------------------------------------------------------------
# Admin User Management Endpoints (Admin only)
# ---------------------------------------------------------------------------

@router.get("/users")
def list_users_endpoint(
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    List all registered workspace users (Admin only).
    """
    users = list_all_users()
    return {
        "total_users": len(users),
        "users": users
    }


@router.put("/users/{user_id}/role")
def update_user_role_endpoint(
    user_id: str,
    payload: RoleUpdateRequest,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Update role for a specific user (Admin only).
    """
    try:
        updated = update_user_role(user_id, payload.role)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found.")
        return {
            "message": f"User role updated to '{payload.role}'.",
            "user": updated
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.post("/users/{user_id}/status")
def update_user_status_endpoint(
    user_id: str,
    payload: StatusUpdateRequest,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Activate or deactivate a user account (Admin only).
    """
    updated = set_user_active_status(user_id, payload.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    action = "activated" if payload.is_active else "deactivated"
    return {
        "message": f"User account successfully {action}.",
        "user": updated
    }


# ---------------------------------------------------------------------------
# Development Seed Endpoint
# ---------------------------------------------------------------------------

@router.post("/dev-seed")
def dev_seed_endpoint():
    """
    Optional development-only seed mechanism.
    Only enabled when ENVIRONMENT=development.
    Creates demo researcher, reviewer, and admin accounts.
    """
    try:
        seeded = seed_dev_users()
        return {
            "message": "Development demo users seeded successfully.",
            "accounts": seeded,
            "notice": "Development only. Do not enable in production."
        }
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(perm_err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seed error: {str(err)}"
        )
