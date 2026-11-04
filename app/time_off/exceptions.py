class TimeOffNotFoundError(Exception):
    status_code = 404

    def __init__(self, message: str = "Time off not found."):
        super().__init__(message)


class TimeOffRangeError(Exception):
    status_code = 422

    def __init__(self, message: str = "start_at must be before end_at."):
        super().__init__(message)


class TimeOffConflictError(Exception):
    status_code = 409

    def __init__(self, message: str = "Time off overlaps existing appointments."):
        super().__init__(message)
