from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.types import HourAlignedDatetime
from app.customers.schemas import CreateCustomerRequest


class Appointment(BaseModel):
    id: int
    course_id: int
    customer_id: Optional[int]
    date: datetime
    price_at_booking: int
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class PublicAppointmentResponse(BaseModel):
    """What the booking form gets back. No customer link, admin notes or timestamps."""

    id: int
    course_id: int
    date: datetime
    price_at_booking: int


class CreateAppointmentRequest(BaseModel):
    course_id: int = Field(gt=0)
    date: HourAlignedDatetime
    customer: CreateCustomerRequest
