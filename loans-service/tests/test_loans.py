from unittest.mock import patch

from app import clients


def test_borrow_book_creates_loan(client, auth_header):
    with patch("app.main.clients.update_book_availability") as mock_update:
        mock_update.return_value = None
        response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    assert response.status_code == 201
    body = response.json()
    assert body["book_id"] == 1
    assert body["status"] == "EN_COURS"
    mock_update.assert_called_once()
    called_args = mock_update.call_args.args
    assert called_args[0] == 1
    assert called_args[1] == -1


def test_borrow_unavailable_book_returns_409(client, auth_header):
    with patch("app.main.clients.update_book_availability", side_effect=clients.BookUnavailable("no copies")):
        response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    assert response.status_code == 409


def test_borrow_unknown_book_returns_404(client, auth_header):
    with patch("app.main.clients.update_book_availability", side_effect=clients.BookNotFound("missing")):
        response = client.post("/loans", json={"book_id": 999}, headers=auth_header(user_id=1))
    assert response.status_code == 404


def test_borrow_when_books_service_down_returns_503(client, auth_header):
    with patch(
        "app.main.clients.update_book_availability",
        side_effect=clients.BooksServiceUnavailable("connection refused"),
    ):
        response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    assert response.status_code == 503


def test_return_book_marks_loan_returned(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        create_response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    loan_id = create_response.json()["id"]

    with patch("app.main.clients.update_book_availability"):
        response = client.patch(f"/loans/{loan_id}/return", headers=auth_header(user_id=1))
    assert response.status_code == 200
    assert response.json()["status"] == "RETOURNE"
    assert response.json()["returned_at"] is not None


def test_return_unknown_loan_returns_404(client, auth_header):
    response = client.patch("/loans/999/return", headers=auth_header(user_id=1))
    assert response.status_code == 404


def test_return_already_returned_loan_rejected(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        create_response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    loan_id = create_response.json()["id"]

    with patch("app.main.clients.update_book_availability"):
        client.patch(f"/loans/{loan_id}/return", headers=auth_header(user_id=1))
        response = client.patch(f"/loans/{loan_id}/return", headers=auth_header(user_id=1))
    assert response.status_code == 409


def test_list_loans_filters_by_user_for_non_admin(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
        client.post("/loans", json={"book_id": 2}, headers=auth_header(user_id=2))

    response = client.get("/loans", headers=auth_header(user_id=1))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == 1


def test_list_loans_admin_sees_all(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
        client.post("/loans", json={"book_id": 2}, headers=auth_header(user_id=2))

    response = client.get("/loans", headers=auth_header(user_id=99, role="PERSONNEL_ADMIN"))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_loans_admin_can_filter_by_user_id(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
        client.post("/loans", json={"book_id": 2}, headers=auth_header(user_id=2))

    response = client.get("/loans?user_id=2", headers=auth_header(user_id=99, role="PERSONNEL_ADMIN"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == 2
