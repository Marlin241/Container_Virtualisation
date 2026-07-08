import enum
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Enum, Integer

from .database import Base


class LoanStatus(str, enum.Enum):
    EN_COURS = "EN_COURS"
    RETOURNE = "RETOURNE"


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    borrowed_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    returned_at = Column(DateTime, nullable=True)
    status = Column(Enum(LoanStatus), nullable=False, default=LoanStatus.EN_COURS)
