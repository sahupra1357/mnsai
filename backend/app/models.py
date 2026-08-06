import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlalchemy import JSON, Column, LargeBinary
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    extrs: list["Extr"] = Relationship(back_populates="owner", cascade_delete=True)
    blog_posts: list["BlogPost"] = Relationship(
        back_populates="author", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# # ExtractionList
# class DOcExtraction(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     filename: str = Field(max_length=255)
#     owner_id: uuid.UUID = Field(
#         foreign_key="user.id", nullable=False, ondelete="CASCADE"
#     )
#     owner: User | None = Relationship(back_populates="extractions")


# ExtractionList
class ExtrBase(SQLModel):
    filename: str = Field(min_length=1, max_length=255)
    pagecount: int | None = Field(default=0)


class Extr(ExtrBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="extrs")


# Blog
class BlogPostBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    content: str
    tags: str | None = Field(default=None, max_length=500)
    is_published: bool = Field(default=False)


class BlogPostCreate(BlogPostBase):
    pass


class BlogPostUpdate(SQLModel):
    title: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    content: str | None = None
    tags: str | None = Field(default=None, max_length=500)
    is_published: bool | None = None


class BlogPost(BlogPostBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(max_length=255, unique=True, index=True)
    author_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    author: User | None = Relationship(back_populates="blog_posts")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BlogPostPublic(BlogPostBase):
    id: uuid.UUID
    author_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class BlogPostsPublic(SQLModel):
    data: list[BlogPostPublic]
    count: int


# Profile image (headshot shown in the public profile hero)
class ProfileImage(SQLModel, table=True):
    """Single-row-per-slot store for profile images.

    Bytes live in the database rather than on disk so the image survives
    container restarts without a mounted volume. Only one row per `slot`
    (currently just "headshot") is ever kept.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slot: str = Field(max_length=50, unique=True, index=True)
    content_type: str = Field(max_length=100)
    filename: str | None = Field(default=None, max_length=255)
    data: bytes
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileImageMeta(SQLModel):
    """Public metadata about the headshot — lets the page decide whether to
    render the photo or the initials placeholder, without fetching bytes."""

    has_image: bool
    content_type: str | None = None
    updated_at: datetime | None = None


class DocumentExtractionRecord(SQLModel, table=True):
    """Durable owner-scoped visual-document extraction and immutable source."""

    __tablename__ = "document_extraction"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    source_name: str = Field(max_length=255)
    source_sha256: str = Field(max_length=64, index=True)
    extraction_fingerprint: str | None = Field(default=None, max_length=64, index=True)
    media_type: str = Field(max_length=150)
    source_bytes: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    source_storage_provider: str = Field(
        default="postgres", max_length=20, nullable=False
    )
    source_object_key: str | None = Field(default=None, max_length=1024)
    normalized_result: dict = Field(sa_column=Column(JSON, nullable=False))
    revision: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class DocumentPreviewArtifactRecord(SQLModel, table=True):
    """Content-addressed page preview derived from an immutable source."""

    __tablename__ = "document_preview_artifact"

    cache_key: str = Field(primary_key=True, max_length=64)
    document_id: uuid.UUID = Field(
        foreign_key="document_extraction.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    page_number: int = Field(nullable=False)
    media_type: str = Field(max_length=100)
    width: int
    height: int
    source_sha256: str = Field(max_length=64)
    content_sha256: str = Field(max_length=64)
    content: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    storage_provider: str = Field(default="postgres", max_length=20, nullable=False)
    object_key: str | None = Field(default=None, max_length=1024)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class DocumentExtractionJobRecord(SQLModel, table=True):
    """Durable state for one asynchronous remote extraction attempt."""

    __tablename__ = "document_extraction_job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        foreign_key="document_extraction.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    attempt_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, nullable=False, unique=True
    )
    page_number: int = Field(nullable=False)
    status: str = Field(default="queued", max_length=30, nullable=False, index=True)
    operator_parser: str | None = Field(default=None, max_length=100)
    remote_call_id: str | None = Field(default=None, max_length=255)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: datetime | None = Field(default=None)


class DocumentJobTokenRecord(SQLModel, table=True):
    """Hashed, purpose-bound capability token for a remote job."""

    __tablename__ = "document_job_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    token_id: str = Field(max_length=40, nullable=False, unique=True, index=True)
    token_hash: str = Field(max_length=64, nullable=False, unique=True, index=True)
    job_id: uuid.UUID = Field(
        foreign_key="document_extraction_job.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    document_id: uuid.UUID = Field(
        foreign_key="document_extraction.id", nullable=False, ondelete="CASCADE"
    )
    purpose: str = Field(max_length=30, nullable=False)
    expires_at: datetime = Field(nullable=False)
    max_uses: int = Field(default=1, nullable=False)
    use_count: int = Field(default=0, nullable=False)
    revoked_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    last_failure_code: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class DocumentExtractionApiKeyRecord(SQLModel, table=True):
    """Revocable, owner-scoped credential for programmatic document uploads."""

    __tablename__ = "document_extraction_api_key"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    name: str = Field(max_length=100)
    key_prefix: str = Field(max_length=20, index=True)
    key_hash: str = Field(max_length=64, unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_used_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None, index=True)
