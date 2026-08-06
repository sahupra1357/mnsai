"""Content-only JSON projections for reviewer downloads."""

from __future__ import annotations

import re
from typing import Any

from .models import DocumentResult, ExtractedElement, PageResult
from .semantic import SemanticResult

_KNOWN_LABELS = {
    "address",
    "certifications",
    "currently",
    "education",
    "email",
    "experience",
    "github",
    "languages",
    "linkedin",
    "location",
    "name",
    "phone",
    "projects",
    "role",
    "skills",
    "summary",
    "title",
    "website",
}


def _text(element: ExtractedElement) -> str:
    return (element.reviewed_text or element.text).strip()


def _table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        cleaned = line.strip().strip("|")
        if not cleaned:
            continue
        cells = [
            cell.strip()
            for cell in re.split(r"\t+|\s*\|\s*|\s{2,}", cleaned)
            if cell.strip()
        ]
        rows.append(cells or [cleaned])
    return rows or [[text]]


def _key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "field"


def _same_visual_line(left: ExtractedElement, right: ExtractedElement) -> bool:
    if left.bounding_box is None or right.bounding_box is None:
        return False
    left_box, right_box = left.bounding_box, right.bounding_box
    overlap = min(left_box.bottom, right_box.bottom) - max(left_box.top, right_box.top)
    smaller_height = min(
        left_box.bottom - left_box.top, right_box.bottom - right_box.top
    )
    return smaller_height > 0 and overlap / smaller_height >= 0.5


def _tesseract_lines(elements: list[ExtractedElement]) -> list[str]:
    has_native_lines = any(
        element.source_line_number is not None for element in elements
    )
    if has_native_lines:
        grouped: dict[tuple[int, int, int], list[ExtractedElement]] = {}
        for element in elements:
            key = (
                element.source_block_number or 0,
                element.source_paragraph_number or 0,
                element.source_line_number or 0,
            )
            grouped.setdefault(key, []).append(element)
        return [
            " ".join(
                _text(word)
                for word in sorted(
                    words,
                    key=lambda item: (
                        item.source_word_number
                        if item.source_word_number is not None
                        else item.reading_order
                    ),
                )
                if _text(word)
            )
            for _, words in sorted(grouped.items())
        ]
    if elements and all(element.bounding_box is None for element in elements):
        return [" ".join(_text(element) for element in elements)]
    lines: list[list[ExtractedElement]] = []
    for element in elements:
        if not lines or not _same_visual_line(lines[-1][-1], element):
            lines.append([element])
        else:
            lines[-1].append(element)
    return [
        " ".join(
            _text(word)
            for word in sorted(
                line,
                key=lambda item: item.bounding_box.left
                if item.bounding_box
                else item.reading_order,
            )
        )
        for line in lines
        if any(_text(word) for word in line)
    ]


def _ordered_sections(lines: list[str]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    labels = "|".join(
        re.escape(label) for label in sorted(_KNOWN_LABELS, key=len, reverse=True)
    )
    known_prefix = re.compile(
        rf"^(?P<label>{labels})(?:\s*[:\-]\s*|\s+)(?P<value>.+)$",
        re.IGNORECASE,
    )
    pending_label: str | None = None

    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        if pending_label is not None:
            sections.append({"type": pending_label, "text": clean})
            pending_label = None
            continue
        colon_match = re.match(
            r"^(?P<label>[A-Za-z][A-Za-z0-9 /&_-]{0,40})\s*:\s*(?P<value>.+)$",
            clean,
        )
        prefix_match = known_prefix.match(clean)
        match = colon_match or prefix_match
        if match is not None:
            sections.append(
                {
                    "type": _key(match.group("label")),
                    "text": match.group("value").strip(),
                }
            )
            continue
        possible_label = _key(clean.rstrip(":"))
        if possible_label in _KNOWN_LABELS and len(clean.split()) <= 3:
            pending_label = possible_label
            continue
        sections.append({"type": "paragraph", "text": clean})

    if pending_label is not None:
        sections.append(
            {
                "type": "heading",
                "text": pending_label.replace("_", " ").title(),
            }
        )
    return {"sections": sections}


def _tesseract_paragraphs(elements: list[ExtractedElement]) -> list[str]:
    if not any(element.source_line_number is not None for element in elements):
        return _tesseract_lines(elements)
    paragraphs: dict[tuple[int, int], list[ExtractedElement]] = {}
    for element in elements:
        key = (
            element.source_block_number or 0,
            element.source_paragraph_number or 0,
        )
        paragraphs.setdefault(key, []).append(element)
    ordered: list[str] = []
    for _, words in sorted(paragraphs.items()):
        line_groups: dict[int, list[ExtractedElement]] = {}
        for word in words:
            line_groups.setdefault(word.source_line_number or 0, []).append(word)
        lines = [
            " ".join(
                _text(word)
                for word in sorted(
                    line_words,
                    key=lambda item: (
                        item.source_word_number
                        if item.source_word_number is not None
                        else item.reading_order
                    ),
                )
                if _text(word)
            )
            for _, line_words in sorted(line_groups.items())
        ]
        text = " ".join(line for line in lines if line).strip()
        if text:
            ordered.append(text)
    return ordered


def page_content(page: PageResult) -> dict[str, Any]:
    """Return extracted text grouped by semantic section, without provenance."""

    if page.semantic_result is not None:
        semantic = SemanticResult.model_validate(page.semantic_result)
        return semantic.final_content

    ordered = sorted(page.elements, key=lambda element: element.reading_order)
    sections: list[dict[str, Any]] = []
    tesseract_words: list[ExtractedElement] = []
    is_tesseract = (
        page.selected_parser is not None and page.selected_parser.name == "tesseract"
    )
    for element in ordered:
        text = _text(element)
        if not text:
            continue
        if is_tesseract and element.type == "paragraph":
            tesseract_words.append(element)
            continue
        if element.type in {"table", "table_cell"}:
            sections.append({"type": "table", "rows": _table_rows(text)})
            continue
        sections.append({"type": element.type, "text": text})

    if tesseract_words:
        return _ordered_sections(_tesseract_paragraphs(tesseract_words))
    return {"sections": sections}


def document_content(document: DocumentResult) -> dict[str, Any]:
    return {
        f"page_{page.page_number}": page_content(page)
        for page in sorted(document.pages, key=lambda item: item.page_number)
    }
