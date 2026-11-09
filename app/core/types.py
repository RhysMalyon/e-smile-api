from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator


def _validate_on_the_hour(value: datetime) -> datetime:
    if value.tzinfo is not None:
        raise ValueError("Datetime must not include a timezone")
    if value.minute or value.second or value.microsecond:
        raise ValueError("Datetime must be on the hour")
    return value


# Naive (no timezone) and on the hour, mirroring the DB CHECK constraints.
HourAlignedDatetime = Annotated[datetime, AfterValidator(_validate_on_the_hour)]
