from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseModel(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"
    collate: str = "utf8mb4_unicode_ci"
    ssl_verify: Optional[bool] = False
    ssl_ca: Optional[str] = None


class MailModel(BaseModel):
    host: str
    service: str
    port: int
    user: str
    password: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_nested_delimiter="__"
    )

    db: DatabaseModel
    mail: MailModel


settings = Settings()
