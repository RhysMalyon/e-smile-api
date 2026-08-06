import logging
from typing import Any, List

from aiomysql import Connection
from pypika import Table

from app.courses.schemas import (
    Course,
    CreateCourseRequest,
    PublicCourseResponse,
    UpdateCourseRequest,
)

logger = logging.getLogger(__name__)

courses_table = Table("courses", schema="e-smile")


class CourseNotFoundError(Exception):
    pass


async def create(conn: Connection, course_payload: dict[str, Any]) -> int:
    pass


async def update_by_id(conn: Connection, id: int, update_course_payload: dict[str, Any]) -> int:
    # raise CourseNotFoundError if no rows updated
    pass


async def get_public_list(conn: Connection) -> List[PublicCourseResponse]:
    # Select name, length, price from courses_table where is_active = 1
    pass


async def get_admin_list(conn: Connection) -> List[Course]:
    # Select * from courses_table
    pass


async def get_by_id(conn: Connection, id: int) -> Course:
    # Select * from courses_table where id = id
    # raise CourseNotFoundError if no match
    pass
