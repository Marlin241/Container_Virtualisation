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
