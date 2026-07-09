from app import models
from app.security import hash_password
from tests.conftest import TestingSessionLocal


def register_and_login(client, role="ETUDIANT", email="user1@dit.sn"):
    client.post(
        "/auth/register",
        json={"full_name": "Test User", "email": email, "password": "secret123", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return response.json()["access_token"]


def create_admin_and_login(client, email="admin@dit.sn"):
    # PERSONNEL_ADMIN can't self-register via the public endpoint, so insert
    # the row directly and log in with the normal flow.
    db = TestingSessionLocal()
    db.add(
        models.User(
            full_name="Admin",
            email=email,
            password_hash=hash_password("secret123"),
            role=models.UserRole.PERSONNEL_ADMIN,
        )
    )
    db.commit()
    db.close()
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return response.json()["access_token"]


def test_read_me_returns_current_user(client):
    token = register_and_login(client)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "user1@dit.sn"


def test_read_me_without_token_rejected(client):
    response = client.get("/users/me")
    assert response.status_code == 403  # HTTPBearer rejects missing credentials


def test_read_user_by_id_allowed_for_self(client):
    token = register_and_login(client)
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    response = client.get(f"/users/{me['id']}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_read_user_by_id_forbidden_for_others(client):
    token_a = register_and_login(client, email="a@dit.sn")
    token_b = register_and_login(client, email="b@dit.sn")
    me_a = client.get("/users/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    response = client.get(f"/users/{me_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 403


def test_list_users_requires_admin_role(client):
    token = register_and_login(client, role="ETUDIANT", email="student@dit.sn")
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_list_users_allowed_for_admin(client):
    token = create_admin_and_login(client)
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_promote_requires_admin_role(client):
    token = register_and_login(client, role="ETUDIANT", email="student@dit.sn")
    other = register_and_login(client, role="ETUDIANT", email="other@dit.sn")
    other_id = client.get("/users/me", headers={"Authorization": f"Bearer {other}"}).json()["id"]
    response = client.patch(f"/users/{other_id}/promote", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_promote_as_admin_succeeds(client):
    admin_token = create_admin_and_login(client)
    user_token = register_and_login(client, role="ETUDIANT", email="student@dit.sn")
    user_id = client.get("/users/me", headers={"Authorization": f"Bearer {user_token}"}).json()["id"]

    response = client.patch(f"/users/{user_id}/promote", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "PERSONNEL_ADMIN"

    # Re-login to get a fresh token reflecting the new role, and confirm it works
    relogged = client.post("/auth/login", json={"email": "student@dit.sn", "password": "secret123"})
    new_token = relogged.json()["access_token"]
    list_response = client.get("/users", headers={"Authorization": f"Bearer {new_token}"})
    assert list_response.status_code == 200


def test_promote_unknown_user_returns_404(client):
    admin_token = create_admin_and_login(client)
    response = client.patch("/users/999/promote", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 404
