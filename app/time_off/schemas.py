from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator

from app.core.types import HourAlignedDatetime


class TimeOff(BaseModel):
    id: int
    start_at: datetime
    end_at: datetime
    created_at: datetime
    updated_at: datetime


class CreateTimeOffRequest(BaseModel):
    start_at: HourAlignedDatetime
    end_at: HourAlignedDatetime

    @model_validator(mode="after")
    def validate_start_before_end(self):
        if self.start_at >= self.end_at:
            raise ValueError("start_at must be before end_at")
        return self


class UpdateTimeOffRequest(BaseModel):
    start_at: Optional[HourAlignedDatetime] = None
    end_at: Optional[HourAlignedDatetime] = None

    @model_validator(mode="after")
    def validate_update(self):
        provided = self.model_dump(exclude_unset=True)

        if not provided:
            raise ValueError("At least one field must be provided")

        # Both columns are NOT NULL, so an explicit `null` can never be applied.
        if any(value is None for value in provided.values()):
            raise ValueError("start_at and end_at cannot be null")

        # With only one side provided, the check against the stored value happens in the service.
        if self.start_at and self.end_at and self.start_at >= self.end_at:
            raise ValueError("start_at must be before end_at")

        return self
