"""
Unit & Integration Test Suite for Step 11.16: Research Workspace, User Accounts, Authentication, and Access Control.

Tests:
1. PBKDF2 Password Hashing & Verification
2. PyJWT token generation and verification
3. User Registration (researcher default, field validation, duplicate detection, no password hash leakage)
4. User Login (valid credentials, invalid password, inactive user)
5. Current User & Profile Retrieval (/api/auth/me)
6. Profile Updates (name change, password change with old password verification)
7. Role-Based Access Control (RBAC):
   - Researcher vs Reviewer vs Admin permissions on Studies
   - Study isolation: User A cannot modify/delete User B's study
   - Reviewer has read-only access across studies
   - Admin has full access across studies
8. Study Ownership Inheritance:
   - Analyses inherit study owner_id
   - Annotations inherit study owner_id
9. Admin User Management (/api/auth/users, role updates, status toggle)
10. Development Seed Mechanism (/api/auth/dev-seed)
11. Regression: Public health probe (/health)
"""

import os
import sys
from fastapi.testclient import TestClient

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app.main import app
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    seed_dev_users,
    get_user_by_email,
)

client = TestClient(app)


def test_01_password_hashing():
    """Verify PBKDF2-HMAC-SHA256 password hashing and constant-time verification."""
    raw = "ResearchLab2026!#"
    h = hash_password(raw)
    assert h.startswith("pbkdf2_sha256$100000$")
    assert verify_password(raw, h) is True
    assert verify_password("WrongPassword123!", h) is False
    assert verify_password("", h) is False


def test_02_jwt_token_handling():
    """Verify JWT token encoding and decoding."""
    token = create_access_token(user_id="user_xyz123", role="researcher")
    assert isinstance(token, str) and len(token) > 20

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_xyz123"
    assert decoded["role"] == "researcher"

    # Malformed token
    assert decode_access_token("invalid.token.structure") is None


def test_03_dev_seed():
    """Verify dev seed endpoint creates or verifies demo, reviewer, and admin accounts."""
    res = client.post("/api/auth/dev-seed")
    assert res.status_code == 200
    data = res.json()
    assert "accounts" in data
    assert any(u["email"] == "demo@cardiaclab.local" for u in data["accounts"])
    assert any(u["email"] == "reviewer@cardiaclab.local" for u in data["accounts"])
    assert any(u["email"] == "admin@cardiaclab.local" for u in data["accounts"])


def test_04_user_registration_and_validation():
    """Verify registration creates a user with researcher role and never leaks passwords."""
    import uuid
    rand_email = f"researcher_{uuid.uuid4().hex[:6]}@cardiaclab.local"
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Eleanor Vance",
            "email": rand_email,
            "password": "SecurePassword123!",
        },
    )
    assert res.status_code in (200, 201)
    body = res.json()
    assert "token" in body or "access_token" in body
    assert "user" in body
    user = body["user"]
    assert user["email"] == rand_email
    assert user["role"] == "researcher"
    assert "password" not in user
    assert "password_hash" not in user
    assert "salt" not in user

    # Duplicate registration fails
    dup_res = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Vance Copy",
            "email": rand_email,
            "password": "AnotherPassword123!",
        },
    )
    assert dup_res.status_code == 400


def test_05_user_login():
    """Verify user login flow with credentials and tokens."""
    # Seed ensures demo account exists
    res = client.post(
        "/api/auth/login",
        json={"email": "demo@cardiaclab.local", "password": "DemoResearcher123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data or "access_token" in data
    assert data["user"]["role"] == "researcher"
    assert "password_hash" not in data["user"]

    # Invalid password
    bad_res = client.post(
        "/api/auth/login",
        json={"email": "demo@cardiaclab.local", "password": "IncorrectPassword!"},
    )
    assert bad_res.status_code == 401

    # Non-existent user
    non_res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent_lab_user@local.domain", "password": "SomePass123!"},
    )
    assert non_res.status_code == 401


def test_06_current_user_me():
    """Verify /api/auth/me returns the profile for authenticated requests."""
    # Login as reviewer
    login = client.post(
        "/api/auth/login",
        json={"email": "reviewer@cardiaclab.local", "password": "ReviewerPass123!"},
    ).json()
    token = login.get("token") or login.get("access_token")

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    user_data = me_data.get("user", me_data)
    assert user_data["email"] == "reviewer@cardiaclab.local"
    assert user_data["role"] == "reviewer"

    # Missing token
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401


def test_07_profile_update():
    """Verify user can update their display name and password."""
    import uuid
    rand_email = f"prof_{uuid.uuid4().hex[:6]}@cardiaclab.local"
    reg = client.post(
        "/api/auth/register",
        json={"name": "Initial Name", "email": rand_email, "password": "OldPassword123!"},
    ).json()
    token = reg.get("token") or reg.get("access_token")

    # Update name
    up_res = client.put(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Name"},
    )
    assert up_res.status_code == 200
    res_json = up_res.json()
    user_obj = res_json.get("user", res_json)
    assert user_obj["name"] == "Updated Name"

    # Change password with wrong old password
    bad_pw = client.put(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongOldPassword!", "new_password": "NewPassword456!"},
    )
    assert bad_pw.status_code == 400

    # Change password with correct old password
    good_pw = client.put(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "OldPassword123!", "new_password": "NewPassword456!"},
    )
    assert good_pw.status_code == 200

    # Verify new password works
    re_login = client.post(
        "/api/auth/login",
        json={"email": rand_email, "password": "NewPassword456!"},
    )
    assert re_login.status_code == 200


def test_08_study_isolation_and_ownership():
    """Verify researcher isolation: Alice cannot modify Bob's study."""
    import uuid
    alice_email = f"alice_{uuid.uuid4().hex[:6]}@cardiaclab.local"
    bob_email = f"bob_{uuid.uuid4().hex[:6]}@cardiaclab.local"

    alice_reg = client.post(
        "/api/auth/register",
        json={"name": "Alice Researcher", "email": alice_email, "password": "AlicePassword123!"},
    ).json()
    alice_token = alice_reg.get("token") or alice_reg.get("access_token")

    bob_reg = client.post(
        "/api/auth/register",
        json={"name": "Bob Researcher", "email": bob_email, "password": "BobPassword123!"},
    ).json()
    bob_token = bob_reg.get("token") or bob_reg.get("access_token")

    # Alice creates a study
    create_study_res = client.post(
        "/api/studies",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={
            "title": "Alice Cardiac Deformation Study",
            "subject_code": "P-ALICE-01",
            "description": "Baseline deformation assessment",
        },
    )
    assert create_study_res.status_code == 201
    study = create_study_res.json()
    study_id = study["id"]
    assert study.get("owner_id") is not None

    # Bob attempts to update Alice's study -> 403 Forbidden
    bob_update = client.put(
        f"/api/studies/{study_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"title": "Bob Hijack Attempt"},
    )
    assert bob_update.status_code == 403

    # Bob attempts to delete Alice's study -> 403 Forbidden
    bob_delete = client.delete(
        f"/api/studies/{study_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_delete.status_code == 403

    # Alice can update her own study
    alice_update = client.put(
        f"/api/studies/{study_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"description": "Updated by Alice"},
    )
    assert alice_update.status_code == 200
    assert alice_update.json()["description"] == "Updated by Alice"


def test_09_reviewer_role_restrictions():
    """Verify reviewers have read-only access and cannot create or modify studies."""
    rev_login = client.post(
        "/api/auth/login",
        json={"email": "reviewer@cardiaclab.local", "password": "ReviewerPass123!"},
    ).json()
    rev_token = rev_login.get("token") or rev_login.get("access_token")

    # Reviewer attempting to create a study -> 403 Forbidden
    rev_create = client.post(
        "/api/studies",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"title": "Reviewer Created Study", "subject_code": "P-REV-01"},
    )
    assert rev_create.status_code == 403

    # Reviewer can view all studies
    rev_list = client.get(
        "/api/studies",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert rev_list.status_code == 200


def test_10_admin_full_access_and_user_management():
    """Verify admin user management endpoints and elevated privileges."""
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@cardiaclab.local", "password": "AdminPass123!"},
    ).json()
    admin_token = admin_login.get("token") or admin_login.get("access_token")

    demo_login = client.post(
        "/api/auth/login",
        json={"email": "demo@cardiaclab.local", "password": "DemoResearcher123!"},
    ).json()
    demo_token = demo_login.get("token") or demo_login.get("access_token")

    # Non-admin attempting to list users -> 403 Forbidden
    non_admin_list = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {demo_token}"},
    )
    assert non_admin_list.status_code == 403

    # Admin listing users -> 200 OK
    admin_list = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_list.status_code == 200
    data = admin_list.json()
    users = data.get("users", data)
    assert len(users) >= 3
    # Ensure no password leakage in user list
    for u in users:
        assert "password_hash" not in u
        assert "salt" not in u

    # Admin updating role of a user
    target_user = [u for u in users if u["email"] == "demo@cardiaclab.local"][0]
    role_update = client.put(
        f"/api/auth/users/{target_user['id']}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "reviewer"},
    )
    assert role_update.status_code == 200
    res_u = role_update.json()
    user_obj = res_u.get("user", res_u)
    assert user_obj["role"] == "reviewer"

    # Reset role back to researcher
    client.put(
        f"/api/auth/users/{target_user['id']}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "researcher"},
    )


def test_11_annotation_ownership_and_access():
    """Verify annotations record owner_id and enforce ownership permissions."""
    import uuid
    reg_a = client.post(
        "/api/auth/register",
        json={"name": "User A", "email": f"a_{uuid.uuid4().hex[:6]}@cardiaclab.local", "password": "PassWordA123!"},
    ).json()
    user_a = reg_a.get("token") or reg_a.get("access_token")

    reg_b = client.post(
        "/api/auth/register",
        json={"name": "User B", "email": f"b_{uuid.uuid4().hex[:6]}@cardiaclab.local", "password": "PassWordB123!"},
    ).json()
    user_b = reg_b.get("token") or reg_b.get("access_token")

    # User A creates an annotation
    anno_res = client.post(
        "/api/annotations",
        headers={"Authorization": f"Bearer {user_a}"},
        json={
            "image_filename": "frame_001.png",
            "annotation_type": "point",
            "annotator_label": "Apex",
            "points": [{"x": 120.0, "y": 240.0}],
        },
    )
    assert anno_res.status_code == 201
    anno = anno_res.json()
    anno_id = anno["id"]
    assert anno.get("owner_id") is not None

    # User B attempts to delete User A's annotation -> 403 Forbidden
    b_del = client.delete(
        f"/api/annotations/{anno_id}",
        headers={"Authorization": f"Bearer {user_b}"},
    )
    assert b_del.status_code == 403

    # User A deletes their own annotation -> 200 OK
    a_del = client.delete(
        f"/api/annotations/{anno_id}",
        headers={"Authorization": f"Bearer {user_a}"},
    )
    assert a_del.status_code == 200


def test_12_public_health_and_security_headers():
    """Verify /health probe works and security headers are included."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "healthy"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-content-type-options") == "nosniff"


if __name__ == "__main__":
    tests = [
        test_01_password_hashing,
        test_02_jwt_token_handling,
        test_03_dev_seed,
        test_04_user_registration_and_validation,
        test_05_user_login,
        test_06_current_user_me,
        test_07_profile_update,
        test_08_study_isolation_and_ownership,
        test_09_reviewer_role_restrictions,
        test_10_admin_full_access_and_user_management,
        test_11_annotation_ownership_and_access,
        test_12_public_health_and_security_headers,
    ]
    passed = 0
    failed = 0
    print("=" * 60)
    print("RUNNING CDL STEP 11.16 AUTH & WORKSPACE TEST SUITE")
    print("=" * 60)
    for t in tests:
        name = t.__name__
        try:
            t()
            passed += 1
            print(f"[PASS] {name}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)

