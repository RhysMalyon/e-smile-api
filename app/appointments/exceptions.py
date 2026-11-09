class AppointmentNotFoundError(Exception):
    status_code = 404

    def __init__(self, message: str = "Appointment not found."):
        super().__init__(message)


class InvalidSlotError(Exception):
    """The requested time can never be booked (outside hours, closed day, in the past)."""

    status_code = 422

    def __init__(self, message: str = "That time cannot be booked."):
        super().__init__(message)


class SlotUnavailableError(Exception):
    """The time is valid but taken, either by another appointment or by time off.

    Deliberately one message for both, so the public booking form doesn't reveal which.
    """

    status_code = 409

    def __init__(self, message: str = "That time is no longer available."):
        super().__init__(message)


class InvalidDateRangeError(Exception):
    status_code = 422

    def __init__(self, message: str = "Invalid date range."):
        super().__init__(message)
