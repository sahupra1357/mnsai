from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .execution import IsolatedExecutionError
from .models import (
    AdapterResult,
    AttemptStatus,
    BoundingBox,
    CoordinateSpace,
    ExtractedElement,
    ExtractionAttempt,
    PageInput,
)


@dataclass(frozen=True)
class CommandExecutor:
    executable: str

    def __call__(self, page: PageInput) -> AdapterResult:
        page_payload = page.model_dump(mode="json", exclude={"content"})
        page_payload["content_b64"] = base64.b64encode(page.content).decode("ascii")
        completed = subprocess.run(
            [self.executable],
            input=json.dumps(page_payload).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            raise IsolatedExecutionError(
                "parser_command_failed", "Configured parser worker failed"
            )
        try:
            return AdapterResult.model_validate_json(completed.stdout)
        except ValueError as exc:
            raise IsolatedExecutionError(
                "invalid_adapter_output",
                "Configured parser worker returned invalid output",
            ) from exc


def configured_command_executor(
    environment_variable: str,
) -> Callable[[PageInput], AdapterResult] | None:
    """Return a pickleable JSON worker hook when explicitly configured."""
    command = os.environ.get(environment_variable)
    if not command:
        return None
    executable = shutil.which(command)
    return CommandExecutor(executable) if executable is not None else None


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def tesseract_version() -> str | None:
    executable = shutil.which("tesseract")
    if executable is None:
        return None
    completed = subprocess.run(
        [executable, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    first_line = completed.stdout.decode(errors="replace").splitlines()
    return first_line[0].removeprefix("tesseract ").strip() if first_line else None


def _image(page: PageInput) -> tuple[bytes, int, int]:
    if page.media_type == "application/pdf":
        try:
            import fitz  # type: ignore[import-untyped]
        except ImportError as exc:
            raise IsolatedExecutionError(
                "pdf_renderer_unavailable",
                "PDF rendering support is unavailable for Tesseract",
            ) from exc
        document = fitz.open(stream=page.content, filetype="pdf")
        try:
            page_index = page.page_number - 1
            if page_index < 0 or page_index >= document.page_count:
                raise IsolatedExecutionError("invalid_page", "PDF page is unavailable")
            pixmap = document[page_index].get_pixmap(dpi=200, alpha=False)
            return pixmap.tobytes("png"), pixmap.width, pixmap.height
        finally:
            document.close()
    try:
        from PIL import Image
    except ImportError as exc:
        raise IsolatedExecutionError(
            "image_decoder_unavailable",
            "Image decoding support is unavailable for Tesseract",
        ) from exc
    with Image.open(io.BytesIO(page.content)) as image:
        image.load()
        output = io.BytesIO()
        image.convert("RGB").save(output, format="PNG")
        return output.getvalue(), image.width, image.height


def tesseract_executor(page: PageInput) -> AdapterResult:
    executable = shutil.which("tesseract")
    if executable is None:
        raise IsolatedExecutionError(
            "adapter_unavailable", "Tesseract executable is not installed"
        )
    image_bytes, width, height = _image(page)
    with tempfile.TemporaryDirectory(prefix="visual-extractor-") as directory:
        image_path = Path(directory) / "page.png"
        image_path.write_bytes(image_bytes)
        completed = subprocess.run(
            [executable, str(image_path), "stdout", "tsv"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    if completed.returncode != 0:
        raise IsolatedExecutionError("tesseract_failed", "Tesseract extraction failed")
    lines = completed.stdout.decode("utf-8", errors="replace").splitlines()
    elements: list[ExtractedElement] = []
    confidences: list[float] = []
    space = CoordinateSpace(width=width, height=height)
    for line in lines[1:]:
        columns = line.split("\t", 11)
        if len(columns) != 12 or not columns[11].strip():
            continue
        try:
            block_number = int(columns[2])
            paragraph_number = int(columns[3])
            line_number = int(columns[4])
            word_number = int(columns[5])
            left, top, box_width, box_height = map(int, columns[6:10])
            raw_confidence = float(columns[10])
        except ValueError:
            continue
        confidence = raw_confidence / 100 if raw_confidence >= 0 else None
        if confidence is not None:
            confidences.append(confidence)
        elements.append(
            ExtractedElement(
                element_id=f"p{page.page_number}-tesseract-{len(elements)}",
                text=columns[11].strip(),
                bounding_box=BoundingBox(
                    left=left,
                    top=top,
                    right=left + box_width,
                    bottom=top + box_height,
                ),
                coordinate_space=space,
                reading_order=len(elements),
                confidence=confidence,
                confidence_source="tesseract",
                source_block_number=block_number,
                source_paragraph_number=paragraph_number,
                source_line_number=line_number,
                source_word_number=word_number,
            )
        )
    mean = sum(confidences) / len(confidences) if confidences else None
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser="tesseract",
            version="binary",
            status=AttemptStatus.SUCCEEDED if elements else AttemptStatus.FAILED,
            confidence=mean,
            error_code=None if elements else "empty_output",
            error_message=None if elements else "Tesseract returned no text",
        ),
        elements=elements,
    )
