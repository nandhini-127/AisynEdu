from datetime import timedelta
import pytest
from httpx import AsyncClient
from app.core.rate_limiter import login_rate_limiter
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_registration_validation(client: AsyncClient):
    # 1. Weak password - too short
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@edunex.ai",
            "name": "Short",
            "password": "short",
            "role": "student",
        },
    )
    assert res.status_code == 422

    # 2. Weak password - missing special character
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "nospecial@edunex.ai",
            "name": "No Special",
            "password": "Password123",
            "role": "student",
        },
    )
    assert res.status_code == 422

    # 3. Weak password - missing number
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "nonumber@edunex.ai",
            "name": "No Number",
            "password": "Password!",
            "role": "student",
        },
    )
    assert res.status_code == 422

    # 4. Valid registration
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "valid_student@edunex.ai",
            "name": "Valid Student",
            "password": "StrongPassword123!",
            "role": "student",
        },
    )
    assert res.status_code == 201
    assert res.json()["success"] is True
    assert res.json()["data"]["email"] == "valid_student@edunex.ai"


@pytest.mark.asyncio
async def test_login_and_rate_limiting(client: AsyncClient):
    login_rate_limiter.clear_all()

    # Register user
    email = "ratelimit_test@edunex.ai"
    password = "CorrectPassword123!"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "name": "Rate Limit Student",
            "password": password,
        },
    )

    # Failed login attempts
    for _ in range(5):
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword123!"},
        )
        assert res.status_code == 401

    # 6th attempt should be rate limited (429)
    res_limited = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res_limited.status_code == 429
    assert "Too many failed login attempts" in res_limited.json()["detail"]

    # Reset rate limiter
    login_rate_limiter.clear_all()

    # Login should now succeed with correct credentials
    res_success = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res_success.status_code == 200
    assert "access_token" in res_success.json()["data"]


@pytest.mark.asyncio
async def test_token_expiration_and_unauthorized_access(client: AsyncClient):
    # 1. Missing token
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401

    # 2. Malformed token
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"}
    )
    assert res.status_code == 401

    # 3. Expired token
    expired_token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        expires_delta=timedelta(seconds=-10),
    )
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_profile_update_and_change_password(client: AsyncClient):
    login_rate_limiter.clear_all()
    email = "profile_user@edunex.ai"
    password = "InitialPassword123!"

    # Register
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Initial Name", "password": password},
    )

    # Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    access_token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Update profile
    patch_res = await client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Name", "preferred_llm": "ollama"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["name"] == "Updated Name"
    assert patch_res.json()["data"]["preferred_llm"] == "ollama"

    # Change password - wrong current password
    fail_pw = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongCurrent123!",
            "new_password": "NewSecurePassword123!",
        },
        headers=headers,
    )
    assert fail_pw.status_code == 400

    # Change password - success
    new_password = "BrandNewPassword123!"
    success_pw = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": password,
            "new_password": new_password,
        },
        headers=headers,
    )
    assert success_pw.status_code == 200

    # Old password no longer works
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert old_login.status_code == 401

    # New password works
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_logout(client: AsyncClient):
    login_rate_limiter.clear_all()
    email = "refresh_user@edunex.ai"
    password = "SecurePassword123!"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Refresh User", "password": password},
    )

    # Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = login_res.json()["data"]
    initial_refresh = data["refresh_token"]

    # 1. Rotate token via /refresh
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()["data"]
    second_refresh = new_data["refresh_token"]
    assert second_refresh != initial_refresh

    # 2. Old refresh token cannot be reused
    reused_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert reused_res.status_code == 401

    # 3. Logout invalidates current refresh token
    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": second_refresh},
    )
    assert logout_res.status_code == 200

    # Revoked token cannot be refreshed after logout
    after_logout = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_role_based_access_control(client: AsyncClient):
    login_rate_limiter.clear_all()

    # Register student
    student_email = "student_rbac@edunex.ai"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": student_email,
            "name": "Student RBAC",
            "password": "Password123!",
            "role": "student",
        },
    )
    student_login = await client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": "Password123!"},
    )
    student_token = student_login.json()["data"]["access_token"]

    # Student cannot access Admin API
    student_admin_res = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert student_admin_res.status_code == 403

    # Register admin
    admin_email = "admin_rbac@edunex.ai"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": admin_email,
            "name": "Admin RBAC",
            "password": "AdminPassword123!",
            "role": "admin",
        },
    )
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPassword123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]

    # Admin CAN access Admin API
    admin_res = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert len(admin_res.json()["data"]) >= 2


@pytest.mark.asyncio
async def test_resource_ownership_isolation(client: AsyncClient):
    login_rate_limiter.clear_all()

    # User A
    user_a = {"email": "user_a@edunex.ai", "password": "Password123!", "name": "User A"}
    await client.post("/api/v1/auth/register", json=user_a)
    login_a = await client.post("/api/v1/auth/login", json=user_a)
    token_a = login_a.json()["data"]["access_token"]

    # User B
    user_b = {"email": "user_b@edunex.ai", "password": "Password123!", "name": "User B"}
    await client.post("/api/v1/auth/register", json=user_b)
    login_b = await client.post("/api/v1/auth/login", json=user_b)
    token_b = login_b.json()["data"]["access_token"]

    # User A creates a session
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={"subject": "Physics", "title": "Quantum Mechanics"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    session_id = sess_res.json()["data"]["id"]

    # User B tries to view User A's session messages -> 403 Forbidden
    unauthorized_view = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauthorized_view.status_code == 403

    # User B tries to post into User A's session -> 403 Forbidden
    unauthorized_post = await client.post(
        "/api/v1/chat/message",
        json={
            "session_id": session_id,
            "content": "Intruder message",
            "intent": "qa",
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauthorized_post.status_code == 403

