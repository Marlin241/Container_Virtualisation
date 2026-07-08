from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int = Field(ge=1)


class BookUpdate(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int = Field(ge=1)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    total_copies: int
    available_copies: int
    created_at: datetime


class AvailabilityUpdate(BaseModel):
    delta: int
