"""Deployable Modal execution plane for visual-document parser workers.

The module remains importable without the optional ``modal`` package.  A deployment
installs Modal and configures one ``VISUAL_EXTRACTOR_*_WORKER`` executable per parser
image.  Each executable consumes the repository's JSON worker contract on stdin and
emits a normalized ``AdapterResult`` JSON object on stdout.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import uuid
from typing import Any

import httpx
from pydantic import ValidationError

from app.visual_document_extractor.modal_execution import ModalJobPayload
from app.visual_document_extractor.models import AdapterResult

try:  # Modal is intentionally optional in the Render/backend environment.
    import modal  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised by import smoke tests
    modal = None  # type: ignore[assignment]


_WORKER_ENV = {
    "docling": "VISUAL_EXTRACTOR_DOCLING_WORKER",
    "paddleocr": "VISUAL_EXTRACTOR_PADDLEOCR_WORKER",
    "paddleocr-vl": "VISUAL_EXTRACTOR_PADDLEOCR_VL_WORKER",
    "mineru": "VISUAL_EXTRACTOR_MINERU_WORKER",
    "marker": "VISUAL_EXTRACTOR_MARKER_WORKER",
}


class SafeWorkerError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fetch_source(payload: ModalJobPayload) -> bytes:
    try:
        response = httpx.get(
            payload.source.url,
            headers=(
                _bearer_headers(payload.source.authorization.token.get_secret_value())
                if payload.source.authorization is not None
                else {}
            ),
            timeout=min(payload.timeout_seconds, 300),
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise SafeWorkerError(
            "source_download_timeout", "Source download timed out", retryable=True
        ) from exc
    except httpx.HTTPError as exc:
        raise SafeWorkerError(
            "source_download_failed", "Source download failed", retryable=True
        ) from exc
    content = response.content
    digest = hashlib.sha256(content).hexdigest()
    if not hmac.compare_digest(digest, payload.source.sha256.lower()):
        raise SafeWorkerError(
            "source_checksum_mismatch", "Downloaded source checksum did not match"
        )
    return content


def _invoke_worker(payload: ModalJobPayload, source: bytes) -> AdapterResult:
    worker = os.getenv(_WORKER_ENV[payload.parser])
    if not worker:
        raise SafeWorkerError(
            "modal_parser_unavailable",
            f"Modal parser worker is not configured for {payload.parser}",
        )
    media_type = payload.source.media_type
    if media_type == "application/pdf":
        try:
            import fitz

            original = fitz.open(stream=source, filetype="pdf")
            selected = fitz.open()
            try:
                page_index = payload.source.page_number - 1
                if page_index < 0 or page_index >= original.page_count:
                    raise SafeWorkerError(
                        "invalid_page", "Requested page is unavailable"
                    )
                selected.insert_pdf(original, from_page=page_index, to_page=page_index)
                source = selected.tobytes()
            finally:
                selected.close()
                original.close()
        except SafeWorkerError:
            raise
        except Exception as exc:
            raise SafeWorkerError(
                "page_split_failed", "PDF page isolation failed"
            ) from exc
    page_payload = {
        "document_id": payload.document_id,
        "page_number": payload.source.page_number,
        "media_type": payload.source.media_type,
        "content_b64": base64.b64encode(source).decode("ascii"),
        "classification": "unknown",
        "timeout_seconds": payload.timeout_seconds,
        "operator_parser": payload.parser,
    }
    try:
        completed = subprocess.run(
            [worker],
            input=json.dumps(page_payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=payload.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SafeWorkerError(
            "modal_parser_timeout", "Modal parser worker timed out", retryable=True
        ) from exc
    except OSError as exc:
        raise SafeWorkerError(
            "modal_parser_unavailable", "Modal parser worker could not start"
        ) from exc
    if completed.returncode != 0:
        raise SafeWorkerError(
            "modal_parser_failed", "Modal parser worker failed", retryable=False
        )
    try:
        return AdapterResult.model_validate_json(completed.stdout)
    except (ValidationError, ValueError) as exc:
        raise SafeWorkerError(
            "modal_parser_invalid_output",
            "Modal parser worker returned invalid normalized output",
        ) from exc


def _callback(payload: ModalJobPayload, result: dict[str, Any]) -> None:
    try:
        response = httpx.post(
            payload.result_callback.url,
            headers=_bearer_headers(
                payload.result_callback.authorization.token.get_secret_value()
            ),
            json=result,
            timeout=min(payload.timeout_seconds, 60),
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SafeWorkerError(
            "result_callback_failed",
            "Extraction result callback failed",
            retryable=True,
        ) from exc


def process_job(raw_payload: dict[str, Any]) -> dict[str, str]:
    """Fetch, verify, execute, and report one idempotently identified attempt."""

    try:
        payload = ModalJobPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise SafeWorkerError(
            "invalid_job_payload", "Modal job payload is invalid"
        ) from exc
    try:
        source = _fetch_source(payload)
        extraction = _invoke_worker(payload, source)
        body: dict[str, Any] = {
            "job_id": payload.job_id,
            "document_id": payload.document_id,
            "attempt_id": payload.attempt_id,
            "status": "succeeded",
            "result": extraction.model_dump(mode="json"),
        }
    except SafeWorkerError as exc:
        body = {
            "job_id": payload.job_id,
            "document_id": payload.document_id,
            "attempt_id": payload.attempt_id,
            "status": "failed",
            "error": {
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
            },
        }
    _callback(payload, body)
    return {
        "job_id": payload.job_id,
        "attempt_id": payload.attempt_id,
        "status": body["status"],
    }


if modal is not None:  # pragma: no branch - evaluated in the Modal deployment image
    # Modal's file-based CLI resolves the conventional module-level ``app`` symbol.
    app = modal.App("visual-document-extractor")
    modal_app = app

    def _parser_image(
        parser: str,
        version: str,
        *packages: str,
        paddle_gpu: bool = False,
    ) -> Any:
        image = (
            modal.Image.debian_slim(python_version="3.12")
            .apt_install("libgl1", "libglib2.0-0")
            .pip_install(
                "httpx>=0.25,<1", "pydantic>=2,<3", "PyMuPDF==1.25.1", *packages
            )
        )
        if paddle_gpu:
            image = image.pip_install(
                "paddlepaddle-gpu==3.3.0",
                index_url="https://www.paddlepaddle.org.cn/packages/stable/cu126/",
            )
        return (
            image
            .add_local_python_source("app", copy=True)
            .add_local_file(
                "modal_parser_worker.py", "/opt/modal_parser_worker.py", copy=True
            )
            .run_commands("chmod 0555 /opt/modal_parser_worker.py")
            .env(
                {
                    "MODAL_PARSER": parser,
                    "MODAL_PARSER_VERSION": version,
                    _WORKER_ENV[parser]: "/opt/modal_parser_worker.py",
                }
            )
        )

    _base_image = (
        modal.Image.debian_slim(python_version="3.12")
        .pip_install("fastapi>=0.114,<1", "httpx>=0.25,<1", "pydantic>=2,<3")
        .add_local_python_source("app", copy=True)
    )
    docling_image = _parser_image("docling", "2.114.0", "docling==2.114.0")
    paddleocr_image = _parser_image(
        "paddleocr", "3.7.0", "paddleocr==3.7.0", paddle_gpu=True
    )
    paddleocr_vl_image = _parser_image(
        "paddleocr-vl",
        "3.7.0",
        "paddleocr[doc-parser]==3.7.0",
        paddle_gpu=True,
    )
    mineru_image = _parser_image("mineru", "3.4.4", "mineru[pipeline]==3.4.4")
    marker_image = _parser_image("marker", "2.0.0", "marker-pdf==2.0.0")

    @app.function(image=docling_image, timeout=3600)
    def docling_job(payload: dict[str, Any]) -> dict[str, str]:
        return process_job(payload)

    @app.function(image=paddleocr_image, timeout=3600, gpu="T4")
    def paddleocr_job(payload: dict[str, Any]) -> dict[str, str]:
        return process_job(payload)

    @app.function(image=paddleocr_vl_image, timeout=3600, gpu="L4")
    def paddleocr_vl_job(payload: dict[str, Any]) -> dict[str, str]:
        return process_job(payload)

    @app.function(image=mineru_image, timeout=3600, gpu="L4")
    def mineru_job(payload: dict[str, Any]) -> dict[str, str]:
        return process_job(payload)

    @app.function(image=marker_image, timeout=3600, gpu="L4")
    def marker_job(payload: dict[str, Any]) -> dict[str, str]:
        return process_job(payload)

    _FUNCTIONS = {
        "docling": docling_job,
        "paddleocr": paddleocr_job,
        "paddleocr-vl": paddleocr_vl_job,
        "mineru": mineru_job,
        "marker": marker_job,
    }

    @app.function(image=_base_image)
    @modal.fastapi_endpoint(method="POST", requires_proxy_auth=True)
    def submit(payload: dict[str, Any]) -> dict[str, str]:
        job = ModalJobPayload.model_validate(payload)
        call = _FUNCTIONS[job.parser].spawn(payload)
        return {
            "call_id": getattr(call, "object_id", str(uuid.uuid4())),
            "status": "accepted",
        }
else:
    app = None
    modal_app = None
