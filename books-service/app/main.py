from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .deps import get_current_payload, require_role


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="books-service", lifespan=lifespan)


@app.post("/books", response_model=schemas.BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: schemas.BookCreate,
    _: dict = Depends(require_role("PERSONNEL_ADMIN")),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Book).filter(models.Book.isbn == payload.isbn).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN already exists")
    book = models.Book(
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books", response_model=list[schemas.BookOut])
def list_books(_: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    return db.query(models.Book).all()


@app.get("/books/search", response_model=list[schemas.BookOut])
def search_books(
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
    _: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    query = db.query(models.Book)
    if title:
        query = query.filter(models.Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(models.Book.author.ilike(f"%{author}%"))
    if isbn:
        query = query.filter(models.Book.isbn == isbn)
    return query.all()


@app.get("/books/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, _: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=schemas.BookOut)
def update_book(
    book_id: int,
    payload: schemas.BookUpdate,
    _: dict = Depends(require_role("PERSONNEL_ADMIN")),
    db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    existing = db.query(models.Book).filter(models.Book.isbn == payload.isbn, models.Book.id != book_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN already exists")
    borrowed = book.total_copies - book.available_copies
    book.title = payload.title
    book.author = payload.author
    book.isbn = payload.isbn
    book.total_copies = payload.total_copies
    book.available_copies = max(payload.total_copies - borrowed, 0)
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    _: dict = Depends(require_role("PERSONNEL_ADMIN")),
    db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    db.delete(book)
    db.commit()


@app.patch("/books/{book_id}/availability", response_model=schemas.BookOut)
def update_availability(
    book_id: int,
    payload: schemas.AvailabilityUpdate,
    _: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    new_available = book.available_copies + payload.delta
    if new_available < 0 or new_available > book.total_copies:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book not available")
    book.available_copies = new_available
    db.commit()
    db.refresh(book)
    return book
