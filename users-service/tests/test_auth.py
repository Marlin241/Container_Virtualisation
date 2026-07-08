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
