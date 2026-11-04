import logging
from typing import List

from aiomysql import Connection
from fastapi import APIRouter, Depends, status

from app.auth.dependencies import require_permission
from app.core.dependencies import get_transaction
from app.core.permissions import Permission
from app.courses.schemas import (
    Course,
    CreateCourseRequest,
    PublicCourseResponse,
    UpdateCourseRequest,
)
from app.courses.service import (
    create_course as create_course_service,
    get_course_by_id as get_course_by_id_service,
    get_courses_admin as get_courses_admin_service,
    get_courses_public as get_courses_public_service,
    update_course as update_course_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    dependencies=[Depends(require_permission(permission=Permission.COURSES_WRITE))],
    response_model=Course,
    status_code=status.HTTP_201_CREATED,
)
async def create_course(request: CreateCourseRequest, conn: Connection = Depends(get_transaction)):
    return await create_course_service(conn, request)


@router.get("", response_model=List[PublicCourseResponse])
async def get_courses(conn: Connection = Depends(get_transaction)):
    return await get_courses_public_service(conn)


# Declared BEFORE /{course_id}, otherwise "admin" is parsed as an id and returns a 422.
@router.get(
    "/admin",
    dependencies=[Depends(require_permission(permission=Permission.COURSES_READ))],
    response_model=List[Course],
)
async def get_courses_admin(conn: Connection = Depends(get_transaction)):
    return await get_courses_admin_service(conn)


@router.get(
    "/{course_id}",
    dependencies=[Depends(require_permission(permission=Permission.COURSES_READ))],
    response_model=Course,
)
async def get_course(course_id: int, conn: Connection = Depends(get_transaction)):
    return await get_course_by_id_service(conn, course_id)


@router.patch(
    "/{course_id}",
    dependencies=[Depends(require_permission(permission=Permission.COURSES_WRITE))],
    response_model=Course,
)
async def update_course(
    course_id: int, request: UpdateCourseRequest, conn: Connection = Depends(get_transaction)
):
    return await update_course_service(conn, course_id, request)
