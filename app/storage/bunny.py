import uuid
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile

from app.config import get_settings

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".avi"}

_REGION_HOSTS = {
    "de": "storage.bunnycdn.com",
    "uk": "uk.storage.bunnycdn.com",
    "se": "se.storage.bunnycdn.com",
    "ny": "ny.storage.bunnycdn.com",
    "la": "la.storage.bunnycdn.com",
    "sg": "sg.storage.bunnycdn.com",
    "syd": "syd.storage.bunnycdn.com",
    "jh": "jh.storage.bunnycdn.com",
}


def _storage_host(region: str) -> str:
    region = region.lower()
    return _REGION_HOSTS.get(region, f"{region}.storage.bunnycdn.com")


def _cdn_url(cdn_base: str, key: str) -> str:
    return f"{cdn_base.rstrip('/')}/{key}"


def _validate_ext(filename: str | None, allowed: set[str], default: str = ".jpg") -> str:
    ext = Path(filename or "").suffix.lower()
    if not ext:
        ext = default
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    return ext


async def upload_file(
    file: UploadFile,
    folder: str,
    *,
    allowed_ext: set[str] = ALLOWED_IMAGE_EXT,
    default_ext: str = ".jpg",
) -> str:
    settings = get_settings()
    if not settings.BUNNY_STORAGE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="BunnyCDN storage is not configured (BUNNY_STORAGE_API_KEY missing)",
        )

    ext = _validate_ext(file.filename, allowed_ext, default_ext)
    key = f"{folder.strip('/')}/{uuid.uuid4().hex}{ext}"
    content = await file.read()

    host = _storage_host(settings.BUNNY_STORAGE_REGION)
    upload_url = f"https://{host}/{settings.BUNNY_STORAGE_ZONE}/{key}"

    headers = {"AccessKey": settings.BUNNY_STORAGE_API_KEY}
    if file.content_type:
        headers["Content-Type"] = file.content_type

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.put(upload_url, content=content, headers=headers)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"BunnyCDN upload request failed: {exc}",
            ) from exc

    if response.status_code not in (200, 201):
        body = (response.text or "").strip()[:300]
        raise HTTPException(
            status_code=502,
            detail=(
                f"BunnyCDN upload failed ({response.status_code}): "
                f"{body or 'no response body'}"
            ),
        )

    return _cdn_url(settings.BUNNY_CDN_URL, key)


async def delete_file(url: str) -> None:
    """Delete a file from Bunny storage using its public CDN URL."""
    settings = get_settings()
    if not url or not settings.BUNNY_STORAGE_API_KEY:
        return

    cdn_base = settings.BUNNY_CDN_URL.rstrip("/")
    if not url.startswith(cdn_base):
        return

    key = url[len(cdn_base) :].lstrip("/")
    if not key:
        return

    host = _storage_host(settings.BUNNY_STORAGE_REGION)
    delete_url = f"https://{host}/{settings.BUNNY_STORAGE_ZONE}/{key}"
    headers = {"AccessKey": settings.BUNNY_STORAGE_API_KEY}

    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.delete(delete_url, headers=headers)
