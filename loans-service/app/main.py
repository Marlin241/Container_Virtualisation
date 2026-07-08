from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import clients, models, schemas
from .database import Base, engine, get_db
from .deps import get_current_payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="loans-service", lifespan=lifespan)


@app.post("/loans", response_model=schemas.LoanOut, status_code=status.HTTP_201_CREATED)
def borrow_book(
    payload_body: schemas.LoanCreate,
    request: Request,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    auth_header = request.headers["authorization"]
    try:
        clients.update_book_availability(payload_body.book_id, -1, auth_header)
    except clients.BookNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    except clients.BookUnavailable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book not available")
    except clients.BooksServiceUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Books service unavailable")

    loan = models.Loan(book_id=payload_body.book_id, user_id=int(payload["sub"]))
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@app.patch("/loans/{loan_id}/return", response_model=schemas.LoanOut)
def return_book(
    loan_id: int,
    request: Request,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status == models.LoanStatus.RETOURNE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loan already returned")

    auth_header = request.headers["authorization"]
    try:
        clients.update_book_availability(loan.book_id, 1, auth_header)
    except clients.BooksServiceUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Books service unavailable")
    except (clients.BookNotFound, clients.BookUnavailable):
        pass

    loan.status = models.LoanStatus.RETOURNE
    loan.returned_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan


@app.get("/loans", response_model=list[schemas.LoanOut])
def list_loans(
    user_id: int | None = None,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    query = db.query(models.Loan)
    if payload.get("role") == "PERSONNEL_ADMIN":
        if user_id is not None:
            query = query.filter(models.Loan.user_id == user_id)
    else:
        query = query.filter(models.Loan.user_id == int(payload["sub"]))
    return query.all()
