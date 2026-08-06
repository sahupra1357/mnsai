#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


def _text_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "content", "markdown", "rec_text", "rec_texts"}:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())
                elif isinstance(item, list):
                    values.extend(
                        str(part).strip() for part in item if str(part).strip()
                    )
            else:
                values.extend(_text_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_text_values(item))
    return values


def _paddle(path: Path, *, vl: bool) -> list[str]:
    if vl:
        from paddleocr import PaddleOCRVL

        results = PaddleOCRVL().predict(str(path))
    else:
        from paddleocr import PaddleOCR

        results = PaddleOCR().predict(str(path))
    values: list[str] = []
    for result in results:
        raw = getattr(result, "json", None)
        if callable(raw):
            raw = raw()
        if raw is None and hasattr(result, "to_dict"):
            raw = result.to_dict()
        values.extend(_text_values(raw))
    return values


def _docling(path: Path) -> list[str]:
    from docling.document_converter import DocumentConverter

    markdown = DocumentConverter().convert(path).document.export_to_markdown()
    return [markdown.strip()] if markdown.strip() else []


def _cli_markdown(command: list[str], output: Path) -> list[str]:
    completed = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=float(os.getenv("MODAL_PARSER_TIMEOUT_SECONDS", "900")),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("parser command failed")
    markdown = [
        path.read_text(errors="replace").strip() for path in output.rglob("*.md")
    ]
    return [value for value in markdown if value]


def _extract(parser: str, path: Path, output: Path) -> list[str]:
    if parser == "docling":
        return _docling(path)
    if parser == "paddleocr":
        return _paddle(path, vl=False)
    if parser == "paddleocr-vl":
        return _paddle(path, vl=True)
    if parser == "mineru":
        return _cli_markdown(
            ["mineru", "-p", str(path), "-o", str(output), "-b", "pipeline"], output
        )
    if parser == "marker":
        return _cli_markdown(
            [
                "marker_single",
                str(path),
                "--output_dir",
                str(output),
                "--output_format",
                "markdown",
            ],
            output,
        )
    raise RuntimeError("unsupported parser")


def main() -> int:
    payload = json.load(sys.stdin)
    parser = os.environ["MODAL_PARSER"]
    content = base64.b64decode(payload["content_b64"], validate=True)
    suffix_by_type = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/webp": ".webp",
    }
    with tempfile.TemporaryDirectory(prefix="modal-parser-") as directory:
        root = Path(directory)
        source = root / f"source{suffix_by_type.get(payload.get('media_type'), '.bin')}"
        source.write_bytes(content)
        texts = _extract(parser, source, root / "output")
    elements = [
        {
            "element_id": f"p{payload['page_number']}-{parser}-{index}",
            "type": "paragraph",
            "text": text,
            "reading_order": index,
            "confidence": None,
            "model_derived": parser == "paddleocr-vl",
        }
        for index, text in enumerate(texts)
    ]
    json.dump(
        {
            "attempt": {
                "parser": parser,
                "version": os.getenv("MODAL_PARSER_VERSION", "pinned-image"),
                "run_id": str(uuid.uuid4()),
                "status": "succeeded" if elements else "failed",
                "confidence": None,
                "error_code": None if elements else "empty_output",
                "error_message": None if elements else "Parser returned no text",
            },
            "elements": elements,
            "warnings": [],
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        parser = os.getenv("MODAL_PARSER", "modal-parser")
        exception_name = type(exc).__name__.lower()
        json.dump(
            {
                "attempt": {
                    "parser": parser,
                    "version": os.getenv("MODAL_PARSER_VERSION", "pinned-image"),
                    "run_id": str(uuid.uuid4()),
                    "status": "failed",
                    "confidence": None,
                    "error_code": f"parser_runtime_{exception_name}",
                    "error_message": (
                        f"{parser} failed during execution ({type(exc).__name__})"
                    ),
                    "retryable": False,
                },
                "elements": [],
                "warnings": [],
            },
            sys.stdout,
        )
        raise SystemExit(0) from None
