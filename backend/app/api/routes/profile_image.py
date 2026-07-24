"""Profile image endpoints — the headshot shown in the public profile hero.

Reads are public (the profile page is public); writes are superuser-only.
Uploads are validated by magic bytes rather than the client-supplied
content type, so a mislabelled or non-image file is rejected outright.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from app import crud
from app.api.deps import SessionDep, get_current_active_superuser
from app.models import Message, ProfileImageMeta, User

router = APIRouter(prefix="/profile", tags=["profile"])

# Only the slot the hero renders today; kept explicit so the URL space is fixed.
HEADSHOT_SLOT = "headshot"

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

# (magic-byte prefix, canonical content type). Checked against the file's real
# bytes — the browser-supplied content type is never trusted.
_MAGIC_PREFIXES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
]

ALLOWED_DESCRIPTION = "JPEG, PNG, or WebP"


def _sniff_content_type(data: bytes) -> str | None:
    """Return the canonical content type for `data`, or None if unrecognised."""
    for prefix, content_type in _MAGIC_PREFIXES:
        if data.startswith(prefix):
            return content_type
    # WebP: "RIFF" .... "WEBP"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("/image/meta", response_model=ProfileImageMeta)
def get_profile_image_meta(session: SessionDep) -> ProfileImageMeta:
    """Public: whether a headshot exists, and when it last changed.

    The profile page uses this to choose between the photo and the initials
    placeholder, and to cache-bust the image URL after an upload.
    """
    image = crud.get_profile_image(session=session, slot=HEADSHOT_SLOT)
    if image is None:
        return ProfileImageMeta(has_image=False)
    return ProfileImageMeta(
        has_image=True,
        content_type=image.content_type,
        updated_at=image.updated_at,
    )


@router.get(
    "/image",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}, 404: {"model": Message}},
)
def get_profile_image(session: SessionDep) -> Response:
    """Public: the raw headshot bytes."""
    image = crud.get_profile_image(session=session, slot=HEADSHOT_SLOT)
    if image is None:
        raise HTTPException(status_code=404, detail="No profile image set")
    return Response(
        content=image.data,
        media_type=image.content_type,
        headers={
            # Immutable per version: callers append ?v=<updated_at> from /meta.
            "Cache-Control": "public, max-age=300",
            "ETag": f'"{image.updated_at.isoformat()}"',
        },
    )


@router.post("/image", response_model=ProfileImageMeta)
async def upload_profile_image(
    session: SessionDep,
    file: UploadFile = File(...),
    _: User = Depends(get_current_active_superuser),
) -> ProfileImageMeta:
    """Superuser-only: replace the headshot."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB",
        )

    content_type = _sniff_content_type(data)
    if content_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format — use {ALLOWED_DESCRIPTION}",
        )

    image = crud.upsert_profile_image(
        session=session,
        slot=HEADSHOT_SLOT,
        data=data,
        content_type=content_type,
        filename=file.filename,
    )
    return ProfileImageMeta(
        has_image=True,
        content_type=image.content_type,
        updated_at=image.updated_at,
    )


@router.delete("/image", response_model=Message)
def delete_profile_image(
    session: SessionDep,
    _: User = Depends(get_current_active_superuser),
) -> Message:
    """Superuser-only: remove the headshot, reverting to the initials ring."""
    deleted = crud.delete_profile_image(session=session, slot=HEADSHOT_SLOT)
    if not deleted:
        raise HTTPException(status_code=404, detail="No profile image set")
    return Message(message="Profile image deleted")
