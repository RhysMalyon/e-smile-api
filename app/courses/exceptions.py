from fastapi.responses import JSONResponse


async def course_exception_handler(_, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


class CourseNotFoundError(Exception):
    status_code = 404

    def __init__(self, message: str = "Course not found."):
        super().__init__(message)


class CourseAlreadyExistsError(Exception):
    status_code = 409

    def __init__(self, message: str = "A course with that name already exists."):
        super().__init__(message)
