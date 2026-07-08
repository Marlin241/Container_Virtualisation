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
