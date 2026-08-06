from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Course(BaseModel):
    id: int
    name: str
    length: int
    price: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PublicCourseResponse(BaseModel):
    name: str
    length: int
    price: int


class CreateCourseRequest(BaseModel):
    name: str = Field(max_length=100)
    length: int = Field(gt=0)
    price: int = Field(gt=0)
    is_active: bool = True


class UpdateCourseRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    length: Optional[int] = Field(default=None, gt=0)
    price: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None
