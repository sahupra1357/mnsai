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
from typing import Any, NamedTuple


class Block(NamedTuple):
    """One extracted run of text, with its position on the page when the parser
    reports one.

    `box` is ``(left, top, right, bottom)`` and `space` is ``(width, height)``,
    both in the **same** units and both on a **top-left** origin. The units
    themselves do not matter — the viewer positions each box as a percentage of
    the coordinate space — but mixing units between the two would misplace every
    box, so a parser that cannot supply both leaves them `None` and the element
    is simply not drawable.
    """

    text: str
    box: tuple[float, float, float, float] | None = None
    space: tuple[float, float] | None = None


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


def _image_size(path: Path) -> tuple[float, float] | None:
    """Pixel dimensions of a raster source, which is the space paddle reports
    its boxes in. Returns None for PDFs and when Pillow is absent."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as image:
            width, height = image.size
    except Exception:
        return None
    return (float(width), float(height)) if width > 0 and height > 0 else None


def _paddle_geometry(raw: Any) -> list[tuple[float, float, float, float] | None]:
    """Per-recognition boxes, positionally aligned with `rec_texts`.

    paddle reports either axis-aligned `rec_boxes` or four-point `rec_polys`;
    a polygon is reduced to its extent. Anything unrecognised yields None for
    that slot so text and geometry stay in step.
    """
    payload = raw.get("res") if isinstance(raw, dict) and "res" in raw else raw
    if not isinstance(payload, dict):
        return []
    boxes = payload.get("rec_boxes")
    if isinstance(boxes, list) and boxes:
        return [_flat_box(entry) for entry in boxes]
    polygons = payload.get("rec_polys") or payload.get("dt_polys")
    if isinstance(polygons, list) and polygons:
        return [_polygon_box(entry) for entry in polygons]
    return []


def _flat_box(entry: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(entry, list | tuple) or len(entry) != 4:
        return None
    if not all(isinstance(value, int | float) for value in entry):
        return None
    left, top, right, bottom = (float(value) for value in entry)
    return _ordered_box(left, top, right, bottom)


def _polygon_box(entry: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(entry, list | tuple) or not entry:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for point in entry:
        if not isinstance(point, list | tuple) or len(point) != 2:
            return None
        x, y = point
        if not isinstance(x, int | float) or not isinstance(y, int | float):
            return None
        xs.append(float(x))
        ys.append(float(y))
    return _ordered_box(min(xs), min(ys), max(xs), max(ys))


def _paddle(path: Path, *, vl: bool) -> list[Block]:
    if vl:
        from paddleocr import PaddleOCRVL

        results = PaddleOCRVL().predict(str(path))
    else:
        from paddleocr import PaddleOCR

        results = PaddleOCR().predict(str(path))
    # Boxes are in image pixels, so without the image dimensions there is no
    # coordinate space to express them against and the text goes out bare.
    space = _image_size(path)
    blocks: list[Block] = []
    for result in results:
        raw = getattr(result, "json", None)
        if callable(raw):
            raw = raw()
        if raw is None and hasattr(result, "to_dict"):
            raw = result.to_dict()
        texts = _text_values(raw)
        boxes = _paddle_geometry(raw) if space else []
        for index, text in enumerate(texts):
            box = boxes[index] if index < len(boxes) else None
            blocks.append(Block(text, box, space if box else None))
    return blocks


def _docling_page_size(document: Any, page_no: Any) -> tuple[float, float] | None:
    """Page dimensions in the same units docling reports its boxes in."""
    pages = getattr(document, "pages", None)
    if not pages:
        return None
    page = None
    for key in (page_no, str(page_no)):
        try:
            page = pages[key]
        except (KeyError, TypeError, IndexError):
            continue
        if page is not None:
            break
    size = getattr(page, "size", None)
    width = getattr(size, "width", None)
    height = getattr(size, "height", None)
    if not isinstance(width, int | float) or not isinstance(height, int | float):
        return None
    if width <= 0 or height <= 0:
        return None
    return float(width), float(height)


def _docling_geometry(
    document: Any, item: Any
) -> tuple[tuple[float, float, float, float] | None, tuple[float, float] | None]:
    """Map one docling provenance entry onto a top-left-origin box.

    docling reports PDF boxes on a **bottom-left** origin (`t` is further up the
    page than `b`), which is upside down relative to what the viewer draws, so
    they are flipped against the page height. Every attribute is read
    defensively: the exact shape of `prov`/`bbox` has moved between docling
    releases, and geometry is a nice-to-have — losing it must never cost us the
    text.
    """
    provenance = list(getattr(item, "prov", None) or ())
    if not provenance:
        return None, None
    bbox = getattr(provenance[0], "bbox", None)
    page_no = getattr(provenance[0], "page_no", None)
    if bbox is None or page_no is None:
        return None, None
    size = _docling_page_size(document, page_no)
    if size is None:
        return None, None
    width, height = size

    # docling_core offers the conversion itself on recent versions; do it by
    # hand when it is absent or refuses.
    if "BOTTOM" in str(getattr(bbox, "coord_origin", "")).upper():
        converted = None
        to_top_left = getattr(bbox, "to_top_left_origin", None)
        if callable(to_top_left):
            try:
                converted = to_top_left(page_height=height)
            except Exception:
                converted = None
        if converted is not None:
            bbox = converted
        else:
            flipped = _corners(bbox)
            if flipped is None:
                return None, None
            left, top, right, bottom = flipped
            # Mirror the vertical axis: on a bottom-left origin `t` is the
            # distance from the foot of the page, so it becomes the smaller
            # number once measured from the head.
            return _ordered_box(left, height - top, right, height - bottom), size

    corners = _corners(bbox)
    if corners is None:
        return None, None
    left, top, right, bottom = corners
    return _ordered_box(left, top, right, bottom), size


def _corners(bbox: Any) -> tuple[float, float, float, float] | None:
    """docling's `l`/`t`/`r`/`b`, or None if any is missing or not a number."""
    values = [_coord(bbox, name) for name in ("l", "t", "r", "b")]
    if any(value is None for value in values):
        return None
    left, top, right, bottom = (float(value) for value in values)  # type: ignore[arg-type]
    return left, top, right, bottom


def _coord(bbox: Any, name: str) -> float | None:
    value = getattr(bbox, name, None)
    return float(value) if isinstance(value, int | float) else None


def _ordered_box(
    left: float, top: float, right: float, bottom: float
) -> tuple[float, float, float, float] | None:
    """Reject anything the `BoundingBox` model would refuse anyway — a box that
    fails validation upstream would sink the whole extraction, text included."""
    if right < left or bottom < top:
        return None
    return left, top, right, bottom


def _docling(path: Path) -> list[Block]:
    from docling.document_converter import DocumentConverter

    document = DocumentConverter().convert(path).document

    blocks: list[Block] = []
    try:
        for entry in document.iterate_items():
            item = entry[0] if isinstance(entry, tuple) else entry
            text = str(getattr(item, "text", "") or "").strip()
            if not text:
                continue
            box, space = _docling_geometry(document, item)
            blocks.append(Block(text, box, space))
    except Exception:
        # An unfamiliar docling build must not cost us the extraction; fall
        # through to the whole-document markdown this used to always return.
        blocks = []
    if blocks:
        return blocks

    markdown = document.export_to_markdown().strip()
    return [Block(markdown)] if markdown else []


def _cli_markdown(command: list[str], output: Path) -> list[Block]:
    completed = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=float(os.getenv("MODAL_PARSER_TIMEOUT_SECONDS", "900")),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("parser command failed")
    # mineru and marker hand back markdown files, which carry no coordinates at
    # all — these blocks are text-only by nature, not by omission.
    markdown = [
        path.read_text(errors="replace").strip() for path in output.rglob("*.md")
    ]
    return [Block(value) for value in markdown if value]


def _extract(parser: str, path: Path, output: Path) -> list[Block]:
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


def _element(page_number: Any, parser: str, index: int, block: Block) -> dict[str, Any]:
    """One `ExtractedElement`-shaped dict.

    `bounding_box` and `coordinate_space` are emitted together or not at all —
    the viewer needs both to place a box, and half a pair is worse than none.
    """
    element: dict[str, Any] = {
        "element_id": f"p{page_number}-{parser}-{index}",
        "type": "paragraph",
        "text": block.text,
        "reading_order": index,
        "confidence": None,
        "model_derived": parser == "paddleocr-vl",
    }
    if block.box is not None and block.space is not None:
        left, top, right, bottom = block.box
        width, height = block.space
        element["bounding_box"] = {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
        }
        element["coordinate_space"] = {
            "width": width,
            "height": height,
            "origin": "top-left",
        }
    return element


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
        blocks = _extract(parser, source, root / "output")
    elements = [
        _element(payload["page_number"], parser, index, block)
        for index, block in enumerate(blocks)
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
