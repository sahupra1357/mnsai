import uuid
from fastapi import APIRouter, HTTPException
from sqlmodel import Session

from app.api.deps import SessionDep, CurrentUser, get_current_active_superuser
from app import crud
from app.models import BlogPostCreate, BlogPostPublic, BlogPostsPublic, BlogPostUpdate, Message, User
from fastapi import Depends

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("/posts", response_model=BlogPostsPublic)
def list_posts(session: SessionDep, skip: int = 0, limit: int = 50):
    posts, count = crud.get_blog_posts(session=session, skip=skip, limit=limit, published_only=True)
    return BlogPostsPublic(data=posts, count=count)


@router.get("/posts/all", response_model=BlogPostsPublic)
def list_all_posts(
    session: SessionDep,
    _: User = Depends(get_current_active_superuser),
    skip: int = 0,
    limit: int = 100,
):
    posts, count = crud.get_blog_posts(session=session, skip=skip, limit=limit, published_only=False)
    return BlogPostsPublic(data=posts, count=count)


@router.get("/posts/{slug}", response_model=BlogPostPublic)
def get_post(slug: str, session: SessionDep):
    post = crud.get_blog_post_by_slug(session=session, slug=slug)
    if not post or not post.is_published:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts", response_model=BlogPostPublic)
def create_post(
    post_in: BlogPostCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_superuser),
):
    existing = crud.get_blog_post_by_slug(session=session, slug=post_in.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    return crud.create_blog_post(session=session, post_in=post_in, author_id=current_user.id)


@router.put("/posts/{slug}", response_model=BlogPostPublic)
def update_post(
    slug: str,
    post_in: BlogPostUpdate,
    session: SessionDep,
    _: User = Depends(get_current_active_superuser),
):
    post = crud.get_blog_post_by_slug(session=session, slug=slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return crud.update_blog_post(session=session, db_post=post, post_in=post_in)


@router.delete("/posts/{slug}", response_model=Message)
def delete_post(
    slug: str,
    session: SessionDep,
    _: User = Depends(get_current_active_superuser),
):
    post = crud.get_blog_post_by_slug(session=session, slug=slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    crud.delete_blog_post(session=session, post_id=post.id)
    return Message(message="Post deleted")
