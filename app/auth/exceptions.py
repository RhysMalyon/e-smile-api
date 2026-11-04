class InvalidCredentialsError(Exception):
    status_code = 401


class InvalidRefreshTokenError(Exception):
    status_code = 401
