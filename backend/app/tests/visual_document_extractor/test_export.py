from __future__ import annotations

import uuid

from app.visual_document_extractor.export import document_content, page_content
from app.visual_document_extractor.models import (
    DocumentResult,
    ExtractedElement,
    PageResult,
    ParserSelection,
    SourceMetadata,
)


def test_tesseract_words_become_one_paragraph_without_metadata() -> None:
    page = PageResult(
        page_number=1,
        selected_parser=ParserSelection(
            name="tesseract",
            version="5",
            run_id=uuid.uuid4(),
            rationale="test",
        ),
        elements=[
            ExtractedElement(
                element_id="word-1",
                text="Hello",
                reading_order=0,
                confidence=0.91,
            ),
            ExtractedElement(
                element_id="word-2",
                text="world",
                reading_order=1,
                confidence=0.87,
            ),
        ],
    )

    assert page_content(page) == {
        "sections": [{"type": "paragraph", "text": "Hello world"}]
    }


def test_tesseract_visual_lines_become_dynamic_key_values() -> None:
    page = PageResult(
        page_number=1,
        selected_parser=ParserSelection(
            name="tesseract",
            version="5",
            run_id=uuid.uuid4(),
            rationale="test",
        ),
        elements=[
            ExtractedElement(
                element_id=f"word-{index}",
                text=text,
                reading_order=index,
                bounding_box={
                    "left": index * 60,
                    "top": 10,
                    "right": index * 60 + 50,
                    "bottom": 30,
                },
            )
            for index, text in enumerate(
                ["Currently", "Machine", "Learning", "Engineer", "at", "Quansight"]
            )
        ],
    )

    assert page_content(page) == {
        "sections": [
            {
                "type": "currently",
                "text": "Machine Learning Engineer at Quansight",
            }
        ]
    }


def test_tesseract_native_hierarchy_controls_sequence() -> None:
    page = PageResult(
        page_number=1,
        selected_parser=ParserSelection(
            name="tesseract",
            version="5",
            run_id=uuid.uuid4(),
            rationale="test",
        ),
        elements=[
            ExtractedElement(
                element_id="value",
                text="Engineer",
                reading_order=0,
                source_block_number=1,
                source_paragraph_number=1,
                source_line_number=1,
                source_word_number=2,
            ),
            ExtractedElement(
                element_id="label",
                text="Currently",
                reading_order=1,
                source_block_number=1,
                source_paragraph_number=1,
                source_line_number=1,
                source_word_number=1,
            ),
            ExtractedElement(
                element_id="summary",
                text="Builds reliable systems",
                reading_order=2,
                source_block_number=2,
                source_paragraph_number=1,
                source_line_number=1,
                source_word_number=1,
            ),
        ],
    )

    assert page_content(page) == {
        "sections": [
            {"type": "currently", "text": "Engineer"},
            {"type": "paragraph", "text": "Builds reliable systems"},
        ]
    }


def test_content_export_structures_tables_and_uses_reviewed_text() -> None:
    document = DocumentResult(
        owner_id=uuid.uuid4(),
        source=SourceMetadata(
            source_name="table.pdf",
            source_sha256="a" * 64,
            media_type="application/pdf",
            size_bytes=10,
            page_count=1,
        ),
        pages=[
            PageResult(
                page_number=1,
                elements=[
                    ExtractedElement(
                        element_id="heading",
                        type="heading",
                        text="Old heading",
                        reviewed_text="New heading",
                        reading_order=0,
                    ),
                    ExtractedElement(
                        element_id="table",
                        type="table",
                        text="Name | Amount\nWidget | 42",
                        reading_order=1,
                    ),
                ],
            )
        ],
    )

    assert document_content(document) == {
        "page_1": {
            "sections": [
                {"type": "heading", "text": "New heading"},
                {
                    "type": "table",
                    "rows": [["Name", "Amount"], ["Widget", "42"]],
                },
            ],
        }
    }


def test_content_export_uses_verified_semantic_content_without_metadata() -> None:
    page = PageResult(
        page_number=1,
        semantic_result={
            "mode": "verified_ai",
            "candidates": [],
            "verifications": [],
            "coverage": [],
            "final_content": {"currently": "Machine Learning Engineer"},
            "warnings": [],
        },
    )

    assert page_content(page) == {
        "currently": "Machine Learning Engineer"
    }
