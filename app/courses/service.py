import logging
from typing import List

from aiomysql import Connection

from app.courses.repository import create, get_by_id, get_admin_list, get_public_list, update_by_id
from app.courses.schemas import (
    Course,
    CreateCourseRequest,
    PublicCourseResponse,
    UpdateCourseRequest,
)

logger = logging.getLogger(__name__)


async def create_course(
    conn: Connection,
    request: CreateCourseRequest,
) -> Course:
    course_id = await create(
        conn,
        course_payload=request.model_dump(),
    )

    return await get_by_id(conn, id=course_id)


async def update_course(conn: Connection, id: int, request_body: UpdateCourseRequest) -> Course:
    update_course_payload = request_body.model_dump(exclude_unset=True)

    updated_course_id = await update_by_id(conn, id, update_course_payload)

    return await get_by_id(conn, id=updated_course_id)


async def get_courses_public(conn: Connection) -> List[PublicCourseResponse]:
    return await get_public_list(conn)


async def get_courses_admin(conn: Connection) -> List[Course]:
    return await get_admin_list(conn)


async def get_course_by_id(conn: Connection, id: int) -> Course:
    return await get_by_id(conn, id)
