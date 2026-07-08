import os

import httpx

BOOKS_SERVICE_URL = os.getenv("BOOKS_SERVICE_URL", "http://books-service:8000")


class BookNotFound(Exception):
    pass


class BookUnavailable(Exception):
    pass


class BooksServiceUnavailable(Exception):
    pass


def update_book_availability(book_id: int, delta: int, auth_header: str) -> None:
    try:
        response = httpx.patch(
            f"{BOOKS_SERVICE_URL}/books/{book_id}/availability",
            json={"delta": delta},
            headers={"Authorization": auth_header},
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise BooksServiceUnavailable(str(exc)) from exc

    if response.status_code == 404:
        raise BookNotFound(f"Book {book_id} not found")
    if response.status_code == 409:
        raise BookUnavailable(f"Book {book_id} not available")
    response.raise_for_status()
