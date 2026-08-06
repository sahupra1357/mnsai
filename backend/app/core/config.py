import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:3000"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    MAX_EXTR_COUNT: int = 5
    MAX_CONCURRENT_PDF_CONVERSION: int = 4
    BATCH_SIZE: int = 1
    OPENAI_DEPLOYMENT_ID: str = "gpt-4o"
    OPENAI_API_KEY: str | None = None
    DOCUMENT_EXTRACTOR_MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    DOCUMENT_EXTRACTOR_MAX_PAGES: int = 100
    DOCUMENT_EXTRACTOR_MAX_RENDERED_PIXELS: int = 40_000_000
    DOCUMENT_EXTRACTOR_PARSER_TIMEOUT_SECONDS: float = 60.0
    DOCUMENT_EXTRACTOR_TRANSIENT_RETRIES: int = 1
    DOCUMENT_EXTRACTOR_ALTERNATE_ATTEMPTS: int = 2
    DOCUMENT_EXTRACTOR_VISION_ATTEMPTS: int = 3
    DOCUMENT_EXTRACTOR_VISION_ENABLED: bool = False
    DOCUMENT_EXTRACTOR_MINIMUM_CONFIDENCE: float = 0.80
    DOCUMENT_EXTRACTOR_MISTRAL_ENABLED: bool = False
    DOCUMENT_EXTRACTOR_MISTRAL_MODEL: str = "mistral-ocr-4-0"
    DOCUMENT_EXTRACTOR_MISTRAL_TIMEOUT_SECONDS: float = 60.0
    DOCUMENT_EXTRACTOR_OPENAI_VISION_ENABLED: bool = False
    DOCUMENT_EXTRACTOR_OPENAI_DEFAULT_MODEL: str = "gpt-5.6-terra"
    DOCUMENT_EXTRACTOR_OPENAI_ESCALATION_MODEL: str = "gpt-5.6-sol"
    DOCUMENT_EXTRACTOR_OPENAI_TIMEOUT_SECONDS: float = 60.0
    DOCUMENT_EXTRACTOR_MAX_PARSER_PROCESSES: int = 2
    DOCUMENT_EXTRACTOR_PARSER_CPU_SECONDS: int = 60
    DOCUMENT_EXTRACTOR_PARSER_MEMORY_MB: int = 2048
    DOCUMENT_EXTRACTOR_PREVIEW_DPI: int = 144
    DOCUMENT_EXTRACTOR_OFFICE_BINARY: str = "soffice"
    DOCUMENT_EXTRACTOR_OFFICE_TIMEOUT_SECONDS: float = 90.0
    DOCUMENT_EXTRACTOR_USE_DURABLE_STORE: bool = True
    DOCUMENT_EXTRACTOR_STORAGE_PROVIDER: Literal["r2", "postgres"] = "r2"
    DOCUMENT_EXTRACTOR_STORAGE_FALLBACK_TO_POSTGRES: bool = True
    DOCUMENT_EXTRACTOR_R2_ENDPOINT_URL: str | None = None
    DOCUMENT_EXTRACTOR_R2_BUCKET: str | None = None
    DOCUMENT_EXTRACTOR_R2_ACCESS_KEY_ID: str | None = None
    DOCUMENT_EXTRACTOR_R2_SECRET_ACCESS_KEY: str | None = None
    DOCUMENT_EXTRACTOR_R2_REGION: str = "auto"
    DOCUMENT_EXTRACTOR_R2_PREFIX: str = "visual-document-extractor"
    DOCUMENT_EXTRACTOR_R2_PRESIGN_SECONDS: int = 900
    DOCUMENT_EXTRACTOR_MODAL_ENABLED: bool = False
    DOCUMENT_EXTRACTOR_MODAL_ENDPOINT_URL: str | None = None
    DOCUMENT_EXTRACTOR_MODAL_KEY: str | None = None
    DOCUMENT_EXTRACTOR_MODAL_SECRET: str | None = None
    DOCUMENT_EXTRACTOR_PUBLIC_BASE_URL: str | None = None
    DOCUMENT_EXTRACTOR_MODAL_DISPATCH_TIMEOUT_SECONDS: float = 15.0
    DOCUMENT_EXTRACTOR_MODAL_PARSER_TIMEOUT_SECONDS: int = 900
    DOCUMENT_EXTRACTOR_MODAL_SOURCE_TOKEN_MINUTES: int = 60
    DOCUMENT_EXTRACTOR_MODAL_RESULT_TOKEN_MINUTES: int = 180
    DOCUMENT_EXTRACTOR_MODAL_SOURCE_MAX_USES: int = 3
    MISTRAL_API_KEY: str | None = None

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    # TODO: update type to EmailStr when sqlmodel supports it
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    # TODO: update type to EmailStr when sqlmodel supports it
    EMAIL_TEST_USER: str = "test@example.com"
    # TODO: update type to EmailStr when sqlmodel supports it
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore
