import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_auth_registration_and_login(client: AsyncClient):
    # 1. Register new user
    register_payload = {
        "email": "student_test@edunex.ai",
        "name": "Test Student",
        "password": "SecurePassword123!",
        "role": "student",
        "preferred_llm": "gemini",
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == "student_test@edunex.ai"

    # Duplicate registration should return 400
    dup_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 400

    # 2. Login
    login_payload = {
        "email": "student_test@edunex.ai",
        "password": "SecurePassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()["data"]
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Check /me with token
    me_res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "student_test@edunex.ai"


@pytest.mark.asyncio
async def test_chat_session_creation(client: AsyncClient):
    # Register & get auth token
    user_payload = {
        "email": "learner@edunex.ai",
        "name": "Learner One",
        "password": "ComplexPassword123!",
    }
    await client.post("/api/v1/auth/register", json=user_payload)
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    session_payload = {
        "subject": "Computer Science",
        "title": "Data Structures & Algorithms",
    }
    sess_res = await client.post(
        "/api/v1/chat/sessions", json=session_payload, headers=headers
    )
    assert sess_res.status_code == 201
    sess_data = sess_res.json()["data"]
    session_id = sess_data["id"]
    assert sess_data["subject"] == "Computer Science"

    # Send message in session
    msg_payload = {
        "session_id": session_id,
        "content": "Explain binary search trees.",
        "intent": "qa",
    }
    msg_res = await client.post(
        "/api/v1/chat/message", json=msg_payload, headers=headers
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["success"] is True

