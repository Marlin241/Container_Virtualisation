def test_create_book_requires_admin_role(client, auth_header):
    response = client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2},
        headers=auth_header(role="ETUDIANT"),
    )
    assert response.status_code == 403


def test_create_book_as_admin_succeeds(client, auth_header):
    response = client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["available_copies"] == 2


def test_create_book_duplicate_isbn_rejected(client, auth_header):
    payload = {"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2}
    client.post("/books", json=payload, headers=auth_header(role="PERSONNEL_ADMIN"))
    response = client.post("/books", json=payload, headers=auth_header(role="PERSONNEL_ADMIN"))
    assert response.status_code == 400


def test_list_books_returns_created_books(client, auth_header):
    client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    response = client.get("/books", headers=auth_header())
    assert response.status_code == 200
    assert len(response.json()) == 1
