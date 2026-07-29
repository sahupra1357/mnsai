from fastapi import APIRouter

from app.api.routes import (
    blog,
    document_extractions,
    extractorg,
    extractorgpt,
    extractorts,
    items,
    login,
    oauth,
    private,
    profile_chat,
    profile_image,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(oauth.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(extractorg.router)
api_router.include_router(extractorgpt.router)
api_router.include_router(extractorts.router)
api_router.include_router(blog.router)
api_router.include_router(profile_chat.router)
api_router.include_router(profile_image.router)
api_router.include_router(document_extractions.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
