def register_and_login(client, role="ETUDIANT", email="user1@dit.sn"):
    client.post(
        "/auth/register",
        json={"full_name": "Test User", "email": email, "password": "secret123", "role": role},
    )
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
    token = register_and_login(client, role="PERSONNEL_ADMIN", email="admin@dit.sn")
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
