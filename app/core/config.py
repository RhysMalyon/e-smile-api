from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    host: str
    port: str
    title: str
    version: str
    debug: bool = False


class CorsSettings(BaseModel):
    allowed_origins: list[str] = Field(default_factory=list)
    allowed_headers: list[str] = ["Content-Type", "Authorization"]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    expose_headers: list[str] = ["Content-Disposition"]


class DbSettings(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"
    collate: str = "utf8mb4_unicode_ci"
    ssl_verify: Optional[bool] = False
    ssl_ca: Optional[str] = None


class JwtSettings(BaseModel):
    public_key: str
    private_key: str
    private_key_passphrase: str
    access_token_secret: str
    refresh_token_secret: str

    @field_validator("public_key", "private_key", mode="before")
    @classmethod
    def unescape_newlines(cls, value):
        return value.replace("\\n", "\n")


class MailSettings(BaseModel):
    host: str
    service: str
    port: int
    user: str
    password: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_nested_delimiter="__")

    app: AppSettings
    cors: CorsSettings
    db: DbSettings
    jwt: JwtSettings
    mail: MailSettings


settings = Settings()
