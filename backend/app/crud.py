import secrets
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate, ExtrBase, Extr


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def get_or_create_oauth_user(*, session: Session, email: str, full_name: str | None) -> User:
    user = get_user_by_email(session=session, email=email)
    if user:
        return user
    db_user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(secrets.token_hex(32)),
        is_active=True,
        is_superuser=False,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

def create_extr(*, session: Session, extr_in: ExtrBase, owner_id: uuid.UUID) -> Extr:
    db_item = Item.model_validate(extr_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


from app.models import BlogPost, BlogPostCreate, BlogPostUpdate
from datetime import datetime


def get_blog_posts(
    *, session: Session, skip: int = 0, limit: int = 100, published_only: bool = True
) -> tuple[list[BlogPost], int]:
    statement = select(BlogPost)
    if published_only:
        statement = statement.where(BlogPost.is_published == True)  # noqa: E712
    statement = statement.order_by(BlogPost.created_at.desc())
    count_statement = select(BlogPost)
    if published_only:
        count_statement = count_statement.where(BlogPost.is_published == True)  # noqa: E712
    total = len(session.exec(count_statement).all())
    posts = session.exec(statement.offset(skip).limit(limit)).all()
    return list(posts), total


def get_blog_post_by_slug(*, session: Session, slug: str) -> BlogPost | None:
    return session.exec(select(BlogPost).where(BlogPost.slug == slug)).first()


def create_blog_post(
    *, session: Session, post_in: BlogPostCreate, author_id: uuid.UUID
) -> BlogPost:
    db_post = BlogPost.model_validate(post_in, update={"author_id": author_id})
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return db_post


def update_blog_post(
    *, session: Session, db_post: BlogPost, post_in: BlogPostUpdate
) -> BlogPost:
    post_data = post_in.model_dump(exclude_unset=True)
    post_data["updated_at"] = datetime.utcnow()
    db_post.sqlmodel_update(post_data)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return db_post


def delete_blog_post(*, session: Session, post_id: uuid.UUID) -> None:
    post = session.get(BlogPost, post_id)
    if post:
        session.delete(post)
        session.commit()