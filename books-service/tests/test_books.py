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


def create_sample_book(client, auth_header, isbn="111", title="Clean Code"):
    return client.post(
        "/books",
        json={"title": title, "author": "Robert C. Martin", "isbn": isbn, "total_copies": 2},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    ).json()


def test_search_books_by_title(client, auth_header):
    create_sample_book(client, auth_header)
    response = client.get("/books/search?title=clean", headers=auth_header())
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_books_no_match_returns_empty_list(client, auth_header):
    create_sample_book(client, auth_header)
    response = client.get("/books/search?title=nomatch", headers=auth_header())
    assert response.status_code == 200
    assert response.json() == []


def test_get_book_by_id(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.get(f"/books/{book['id']}", headers=auth_header())
    assert response.status_code == 200
    assert response.json()["isbn"] == "111"


def test_get_book_by_id_not_found(client, auth_header):
    response = client.get("/books/999", headers=auth_header())
    assert response.status_code == 404


def test_update_book_as_admin(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.put(
        f"/books/{book['id']}",
        json={"title": "Clean Code 2nd Ed", "author": "Robert C. Martin", "isbn": "111", "total_copies": 3},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Clean Code 2nd Ed"
    assert response.json()["available_copies"] == 3


def test_delete_book_as_admin(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.delete(f"/books/{book['id']}", headers=auth_header(role="PERSONNEL_ADMIN"))
    assert response.status_code == 204
    response = client.get(f"/books/{book['id']}", headers=auth_header())
    assert response.status_code == 404
