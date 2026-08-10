import logging
from typing import Any, List

from aiomysql import Connection, IntegrityError
import aiomysql
from pypika import FormatParameter, MySQLQuery, Table

from app.courses.schemas import (
    Course,
    PublicCourseResponse,
)

logger = logging.getLogger(__name__)

courses_table = Table("courses", schema="e-smile")


class CourseAlreadyExistsError(Exception):
    pass


class CourseNotFoundError(Exception):
    pass


async def create(conn: Connection, course_payload: dict[str, Any]) -> int:
    async with conn.cursor() as cur:
        columns = []
        values = []
        parameters = []

        for column, value in course_payload.items():
            columns.append(column)
            parameters.append(FormatParameter())
            values.append(value)

        query = MySQLQuery.into(courses_table).columns(*columns).insert(*parameters)

        sql_string = query.get_sql()

        logger.info(sql_string)

        try:
            await cur.execute(sql_string, tuple(values))
        except IntegrityError as exc:
            # Not Duplicate entry (1062)
            if exc.args[0] != 1062:
                raise

            logger.warning("Course already exists.")
            raise CourseAlreadyExistsError() from exc

        return cur.lastrowid


async def update_by_id(conn: Connection, id: int, update_course_payload: dict[str, Any]) -> int:
    # raise CourseNotFoundError if no rows updated
    async with conn.cursor() as cur:
        query = MySQLQuery.update(courses_table)

        values = []

        for column, value in update_course_payload.items():
            query = query.set(column, FormatParameter())
            values.append(value)

        query = query.where(courses_table.id == FormatParameter())
        values.append(id)

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, tuple(values))

        if cur.rowcount == 0:
            raise CourseNotFoundError("Could not find course.")

        return id


async def get_public_list(conn: Connection) -> List[PublicCourseResponse]:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(courses_table)
            .select(courses_table.name, courses_table.length, courses_table.price)
            .where(courses_table.is_active == 1)
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string)
        results = await cur.fetchall()

        return [PublicCourseResponse.model_validate(result) for result in results]


async def get_admin_list(conn: Connection) -> List[Course]:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = MySQLQuery.from_(courses_table).select(courses_table.star)

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string)
        results = await cur.fetchall()

        return [Course.model_validate(result) for result in results]


async def get_by_id(conn: Connection, id: int) -> Course:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(courses_table)
            .select(courses_table.star)
            .where(courses_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))
        result = await cur.fetchone()

        if result is None:
            raise CourseNotFoundError(f"Could not find course with ID {id}.")

        return Course.model_validate(result)
