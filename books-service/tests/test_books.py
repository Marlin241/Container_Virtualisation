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


def test_update_book_requires_admin_role(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.put(
        f"/books/{book['id']}",
        json={"title": "Updated Title", "author": "Robert C. Martin", "isbn": "111", "total_copies": 3},
        headers=auth_header(role="ETUDIANT"),
    )
    assert response.status_code == 403


def test_delete_book_requires_admin_role(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.delete(f"/books/{book['id']}", headers=auth_header(role="ETUDIANT"))
    assert response.status_code == 403


def test_update_book_duplicate_isbn_rejected(client, auth_header):
    book1 = create_sample_book(client, auth_header, isbn="111")
    create_sample_book(client, auth_header, isbn="222", title="Another Book")
    response = client.put(
        f"/books/{book1['id']}",
        json={"title": "Clean Code Updated", "author": "Robert C. Martin", "isbn": "222", "total_copies": 3},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    assert response.status_code == 400


def test_update_book_preserves_borrowed_copies(client, auth_header, db=None):
    from tests.conftest import TestingSessionLocal

    book = create_sample_book(client, auth_header, isbn="111", title="Clean Code")

    # Simulate borrowed copies by directly updating the DB
    db_session = TestingSessionLocal()
    try:
        from app.models import Book
        book_row = db_session.query(Book).filter(Book.id == book["id"]).first()
        # Simulate 1 borrowed copy: set available_copies to total_copies - 1
        book_row.available_copies = book["total_copies"] - 1
        db_session.commit()
    finally:
        db_session.close()

    # Update the book with a new total_copies value
    response = client.put(
        f"/books/{book['id']}",
        json={"title": "Clean Code 2nd Ed", "author": "Robert C. Martin", "isbn": "111", "total_copies": 5},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )

    assert response.status_code == 200
    updated_book = response.json()
    # With 1 borrowed copy and new total_copies=5, available should be 5 - 1 = 4
    assert updated_book["available_copies"] == 4
    assert updated_book["total_copies"] == 5


def test_decrement_availability_succeeds(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.patch(
        f"/books/{book['id']}/availability",
        json={"delta": -1},
        headers=auth_header(),
    )
    assert response.status_code == 200
    assert response.json()["available_copies"] == 1


def test_decrement_availability_below_zero_rejected(client, auth_header):
    book = create_sample_book(client, auth_header, isbn="222")
    client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    response = client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    assert response.status_code == 409


def test_increment_availability_succeeds(client, auth_header):
    book = create_sample_book(client, auth_header, isbn="333")
    client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    response = client.patch(f"/books/{book['id']}/availability", json={"delta": 1}, headers=auth_header())
    assert response.status_code == 200
    assert response.json()["available_copies"] == 2


def test_availability_update_unknown_book_returns_404(client, auth_header):
    response = client.patch("/books/999/availability", json={"delta": -1}, headers=auth_header())
    assert response.status_code == 404
