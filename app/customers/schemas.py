from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class Customer(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    first_name_phonetic: str
    last_name_phonetic: str
    tel: str
    created_at: datetime
    updated_at: datetime


class CreateCustomerRequest(BaseModel):
    email: EmailStr = Field(max_length=64)
    first_name: str = Field(min_length=1, max_length=25)
    last_name: str = Field(min_length=1, max_length=25)
    first_name_phonetic: str = Field(min_length=1, max_length=50)
    last_name_phonetic: str = Field(min_length=1, max_length=50)
    tel: str = Field(min_length=1, max_length=16)


class UpdateCustomerRequest(BaseModel):
    email: Optional[EmailStr] = Field(default=None, max_length=64)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=25)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=25)
    first_name_phonetic: Optional[str] = Field(default=None, min_length=1, max_length=50)
    last_name_phonetic: Optional[str] = Field(default=None, min_length=1, max_length=50)
    tel: Optional[str] = Field(default=None, min_length=1, max_length=16)

    @model_validator(mode="after")
    def validate_not_empty(self):
        provided = self.model_dump(exclude_unset=True)

        if not provided:
            raise ValueError("At least one field must be provided")

        # Every column is NOT NULL, so an explicit `null` can never be applied.
        null_fields = [field for field, value in provided.items() if value is None]
        if null_fields:
            raise ValueError(f"Fields cannot be null: {', '.join(null_fields)}")

        return self
