def test_register_creates_user(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Awa Diop",
            "email": "awa@dit.sn",
            "password": "secret123",
            "role": "ETUDIANT",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "awa@dit.sn"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    payload = {
        "full_name": "Awa Diop",
        "email": "awa@dit.sn",
        "password": "secret123",
        "role": "ETUDIANT",
    }
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400


def test_login_success_returns_token(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Awa Diop",
            "email": "awa@dit.sn",
            "password": "secret123",
            "role": "ETUDIANT",
        },
    )
    response = client.post("/auth/login", json={"email": "awa@dit.sn", "password": "secret123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_rejected(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Awa Diop",
            "email": "awa@dit.sn",
            "password": "secret123",
            "role": "ETUDIANT",
        },
    )
    response = client.post("/auth/login", json={"email": "awa@dit.sn", "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_email_rejected(client):
    response = client.post("/auth/login", json={"email": "nobody@dit.sn", "password": "secret123"})
    assert response.status_code == 401
