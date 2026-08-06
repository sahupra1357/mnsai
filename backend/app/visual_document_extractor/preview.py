"""Deterministic, page-oriented preview rendering for untrusted documents.

Office conversion is deliberately an external process.  The configured binary is
invoked without a shell, with a bounded timeout and an isolated temporary profile.
Callers should additionally run the application in a sandbox/container with resource
limits; this module does not make LibreOffice a security boundary.
"""

from __future__ import annotations

import hashlib
import io
import os
import signal
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol


class PreviewErrorCode(str, Enum):
    UNAVAILABLE = "preview_unavailable"
    INVALID_PAGE = "invalid_page"
    CONVERSION_FAILED = "conversion_failed"
    CONVERSION_TIMEOUT = "conversion_timeout"
    RENDER_FAILED = "render_failed"


class PreviewError(RuntimeError):
    """An actionable preview failure safe to expose through the API."""

    def __init__(self, code: PreviewErrorCode, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


@dataclass(frozen=True, slots=True)
class PreviewArtifact:
    content: bytes
    media_type: str
    width: int
    height: int
    page_number: int
    source_sha256: str
    content_sha256: str


class PreviewArtifactCache(Protocol):
    """Minimal cache contract suitable for filesystem or object-store adapters."""

    def get(self, key: str) -> PreviewArtifact | None: ...

    def put(self, key: str, artifact: PreviewArtifact) -> None: ...


@dataclass(frozen=True, slots=True)
class PreviewConfig:
    dpi: int = 144
    office_binary: str | None = None
    office_timeout_seconds: float = 60
    max_output_pixels: int = 40_000_000
    max_concurrent_office: int = 1
    office_memory_bytes: int | None = 1024 * 1024 * 1024
    office_cpu_seconds: int | None = 60

    def __post_init__(self) -> None:
        if self.dpi < 36 or self.dpi > 600:
            raise ValueError("dpi must be between 36 and 600")
        if self.office_timeout_seconds <= 0:
            raise ValueError("office_timeout_seconds must be positive")
        if self.max_output_pixels < 1:
            raise ValueError("max_output_pixels must be positive")
        if self.max_concurrent_office < 1:
            raise ValueError("max_concurrent_office must be positive")


_PDF = "application/pdf"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_office_gates: dict[int, threading.BoundedSemaphore] = {}
_office_gates_lock = threading.Lock()


def _office_gate(size: int) -> threading.BoundedSemaphore:
    with _office_gates_lock:
        return _office_gates.setdefault(size, threading.BoundedSemaphore(size))


def preview_cache_key(
    source_sha256: str, media_type: str, page_number: int, *, dpi: int
) -> str:
    material = f"preview-v1:{source_sha256}:{media_type}:{page_number}:{dpi}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def render_preview(
    content: bytes,
    media_type: str,
    page_number: int,
    *,
    source_name: str = "source",
    source_sha256: str | None = None,
    config: PreviewConfig | None = None,
    cache: PreviewArtifactCache | None = None,
) -> PreviewArtifact:
    """Render one one-based page/frame to a stable PNG artifact."""

    if page_number < 1:
        raise PreviewError(PreviewErrorCode.INVALID_PAGE, "Page numbers start at 1.")
    active = config or PreviewConfig()
    source_digest = source_sha256 or hashlib.sha256(content).hexdigest()
    key = preview_cache_key(source_digest, media_type, page_number, dpi=active.dpi)
    if cache is not None:
        cached = cache.get(key)
        if cached is not None:
            return cached

    if media_type == _PDF:
        artifact = _render_pdf(
            content, page_number, source_digest=source_digest, config=active
        )
    elif media_type.startswith("image/"):
        artifact = _render_image(
            content, page_number, source_digest=source_digest, config=active
        )
    elif media_type in {_DOCX, _PPTX}:
        pdf = convert_office_to_pdf(
            content,
            source_name=source_name,
            media_type=media_type,
            config=active,
        )
        artifact = _render_pdf(
            pdf, page_number, source_digest=source_digest, config=active
        )
    else:
        raise PreviewError(
            PreviewErrorCode.UNAVAILABLE,
            f"Page previews are not supported for media type {media_type!r}.",
        )

    if cache is not None:
        cache.put(key, artifact)
    return artifact


def convert_office_to_pdf(
    content: bytes,
    *,
    source_name: str,
    media_type: str,
    config: PreviewConfig,
) -> bytes:
    """Convert DOCX/PPTX to PDF through a safely invoked LibreOffice process."""

    if media_type not in {_DOCX, _PPTX}:
        raise ValueError("Office conversion accepts only DOCX or PPTX")
    binary = config.office_binary
    if not binary:
        raise PreviewError(
            PreviewErrorCode.UNAVAILABLE,
            "Office preview is unavailable because a LibreOffice/soffice binary "
            "has not been configured.",
        )
    suffix = ".docx" if media_type == _DOCX else ".pptx"
    safe_stem = Path(source_name).stem or "source"
    safe_stem = "".join(c for c in safe_stem if c.isalnum() or c in "-_")[:80]
    safe_stem = safe_stem or "source"

    try:
        with tempfile.TemporaryDirectory(prefix="vde-preview-") as temp:
            work = Path(temp)
            source_path = work / f"{safe_stem}{suffix}"
            output_dir = work / "output"
            profile_dir = work / "profile"
            output_dir.mkdir()
            profile_dir.mkdir()
            source_path.write_bytes(content)
            command = [
                binary,
                "--headless",
                "--safe-mode",
                "--nologo",
                "--nodefault",
                "--nolockcheck",
                "--norestore",
                f"-env:UserInstallation={profile_dir.as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(source_path),
            ]
            completed = _run_office(command, config)
            expected = output_dir / f"{safe_stem}.pdf"
            if completed.returncode != 0 or not expected.is_file():
                raise PreviewError(
                    PreviewErrorCode.CONVERSION_FAILED,
                    "Office preview conversion failed. Verify the configured "
                    "converter and document, then try again.",
                )
            return expected.read_bytes()
    except FileNotFoundError:
        raise PreviewError(
            PreviewErrorCode.UNAVAILABLE,
            "Office preview is unavailable because the configured LibreOffice/"
            "soffice binary could not be started.",
        ) from None
    except subprocess.TimeoutExpired:
        raise PreviewError(
            PreviewErrorCode.CONVERSION_TIMEOUT,
            "Office preview conversion exceeded its configured time limit.",
        ) from None


def _run_office(
    command: list[str], config: PreviewConfig
) -> subprocess.CompletedProcess[bytes]:
    gate = _office_gate(config.max_concurrent_office)
    if not gate.acquire(timeout=config.office_timeout_seconds):
        raise subprocess.TimeoutExpired(command, config.office_timeout_seconds)
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_office_environment(),
            start_new_session=True,
            preexec_fn=_office_resource_limiter(config) if os.name == "posix" else None,
        )
        try:
            stdout, stderr = process.communicate(timeout=config.office_timeout_seconds)
        except subprocess.TimeoutExpired:
            if process.pid is not None and hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.communicate()
            raise
        return subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        gate.release()


def _office_resource_limiter(config: PreviewConfig):  # type: ignore[no-untyped-def]
    def apply_limits() -> None:
        try:
            import resource
        except ImportError:
            return
        if config.office_memory_bytes is not None and hasattr(resource, "RLIMIT_AS"):
            _, hard = resource.getrlimit(resource.RLIMIT_AS)
            requested = config.office_memory_bytes
            limit = (
                requested if hard == resource.RLIM_INFINITY else min(requested, hard)
            )
            try:
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
            except (OSError, ValueError):
                # RLIMIT_AS is not usable for every platform/runtime combination.
                # Container memory limits remain the outer production boundary.
                pass
        if config.office_cpu_seconds is not None and hasattr(resource, "RLIMIT_CPU"):
            cpu = max(1, config.office_cpu_seconds)
            _, hard = resource.getrlimit(resource.RLIMIT_CPU)
            limit = cpu if hard == resource.RLIM_INFINITY else min(cpu, hard)
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (limit, limit))
            except (OSError, ValueError):
                pass

    return apply_limits


def _office_environment() -> dict[str, str]:
    # Preserve executable lookup and locale only; do not forward secrets or HOME.
    environment: dict[str, str] = {"LC_ALL": "C", "LANG": "C"}
    path = os.environ.get("PATH")
    if path:
        environment["PATH"] = path
    return environment


def _render_pdf(
    content: bytes,
    page_number: int,
    *,
    source_digest: str,
    config: PreviewConfig,
) -> PreviewArtifact:
    try:
        import fitz  # type: ignore[import-untyped]

        document = fitz.open(stream=content, filetype="pdf")
        try:
            if page_number > document.page_count:
                raise PreviewError(
                    PreviewErrorCode.INVALID_PAGE,
                    f"Page {page_number} does not exist; the document has "
                    f"{document.page_count} pages.",
                )
            page = document.load_page(page_number - 1)
            scale = config.dpi / 72
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            _check_pixels(pixmap.width, pixmap.height, config)
            png = pixmap.tobytes("png")
            return _artifact(
                png, pixmap.width, pixmap.height, page_number, source_digest
            )
        finally:
            document.close()
    except PreviewError:
        raise
    except ImportError:
        raise PreviewError(
            PreviewErrorCode.UNAVAILABLE,
            "PDF preview is unavailable because PyMuPDF is not installed.",
        ) from None
    except Exception as error:
        raise PreviewError(
            PreviewErrorCode.RENDER_FAILED,
            f"The PDF page could not be rendered: {type(error).__name__}.",
        ) from None


def _render_image(
    content: bytes,
    page_number: int,
    *,
    source_digest: str,
    config: PreviewConfig,
) -> PreviewArtifact:
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(content)) as image:
            frames = getattr(image, "n_frames", 1)
            if page_number > frames:
                raise PreviewError(
                    PreviewErrorCode.INVALID_PAGE,
                    f"Page {page_number} does not exist; the image has {frames} frame(s).",
                )
            image.seek(page_number - 1)
            transposed = ImageOps.exif_transpose(image)
            if transposed is None:
                raise PreviewError(
                    PreviewErrorCode.RENDER_FAILED,
                    "The image orientation could not be normalized.",
                )
            rendered = transposed.convert("RGB")
            _check_pixels(rendered.width, rendered.height, config)
            output = io.BytesIO()
            rendered.save(
                output,
                format="PNG",
                optimize=False,
                compress_level=6,
                dpi=(config.dpi, config.dpi),
            )
            return _artifact(
                output.getvalue(),
                rendered.width,
                rendered.height,
                page_number,
                source_digest,
            )
    except PreviewError:
        raise
    except ImportError:
        raise PreviewError(
            PreviewErrorCode.UNAVAILABLE,
            "Image preview is unavailable because Pillow is not installed.",
        ) from None
    except Exception as error:
        raise PreviewError(
            PreviewErrorCode.RENDER_FAILED,
            f"The image page could not be rendered: {type(error).__name__}.",
        ) from None


def _check_pixels(width: int, height: int, config: PreviewConfig) -> None:
    if width * height > config.max_output_pixels:
        raise PreviewError(
            PreviewErrorCode.RENDER_FAILED,
            "The rendered preview would exceed the configured pixel limit.",
        )


def _artifact(
    png: bytes, width: int, height: int, page_number: int, source_digest: str
) -> PreviewArtifact:
    return PreviewArtifact(
        content=png,
        media_type="image/png",
        width=width,
        height=height,
        page_number=page_number,
        source_sha256=source_digest,
        content_sha256=hashlib.sha256(png).hexdigest(),
    )
