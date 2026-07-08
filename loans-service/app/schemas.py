from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import LoanStatus


class LoanCreate(BaseModel):
    book_id: int


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    user_id: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: LoanStatus
