from enum import StrEnum


class Permission(StrEnum):
    APPOINTMENTS_READ = "appointments:read"
    APPOINTMENTS_DELETE = "appointments:delete"
    COURSES_READ = "courses:read"
    COURSES_WRITE = "courses:write"
    COURSES_DELETE = "courses:delete"
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_DELETE = "customers:delete"
    HOLIDAYS_WRITE = "holidays:write"
    HOLIDAYS_DELETE = "holidays:delete"


class Role(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"


ROLE_PERMISSIONS = {
    Role.ADMIN: set(Permission),  # Always inherit all permissions
    Role.STAFF: {
        Permission.APPOINTMENTS_READ,
        Permission.COURSES_READ,
        Permission.CUSTOMERS_READ,
    },
}
