"""Geometry mapping in the Modal parser worker.

The worker used to flatten every parser to plain text, so elements reached the
viewer with no `bounding_box` and nothing was ever drawn over the page — which
is why boxes appeared locally (tesseract, word-level boxes) but never on a
deployment routing through Modal.

docling and paddleocr are not installed in this image, so the parsers themselves
are stubbed with objects shaped like their real output. What is under test is
the mapping: the bottom-left flip, the pairing of text with boxes, and the rule
that a box and its coordinate space are emitted together or not at all.
"""

from pathlib import Path
from typing import Any

import pytest

import modal_parser_worker as worker


class _Bbox:
    """docling's bounding box: l/t/r/b plus the origin they are measured from."""

    def __init__(
        self, left: float, top: float, right: float, bottom: float, origin: str
    ) -> None:
        self.l = left  # noqa: E741 - docling's own attribute name
        self.t = top
        self.r = right
        self.b = bottom
        self.coord_origin = origin


class _Prov:
    def __init__(self, page_no: int, bbox: _Bbox | None) -> None:
        self.page_no = page_no
        self.bbox = bbox


class _Item:
    def __init__(self, text: str, prov: list[_Prov] | None = None) -> None:
        self.text = text
        self.prov = prov or []


class _Size:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height


class _Document:
    def __init__(self, items: list[_Item], *, page_height: float = 792.0) -> None:
        self._items = items
        self.pages = {1: type("Page", (), {"size": _Size(612.0, page_height)})()}

    def iterate_items(self) -> list[tuple[_Item, int]]:
        return [(item, 0) for item in self._items]

    def export_to_markdown(self) -> str:
        return "\n".join(item.text for item in self._items)


def _install_docling(monkeypatch: pytest.MonkeyPatch, document: Any) -> None:
    """Stand a fake `docling.document_converter` in the import path."""
    import sys
    import types

    module = types.ModuleType("docling.document_converter")

    class _Converter:
        def convert(self, _path: Path) -> Any:
            return type("Result", (), {"document": document})()

    module.DocumentConverter = _Converter  # type: ignore[attr-defined]
    package = types.ModuleType("docling")
    package.document_converter = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docling", package)
    monkeypatch.setitem(sys.modules, "docling.document_converter", module)


# --------------------------------------------------------------------------
# docling
# --------------------------------------------------------------------------


def test_bottom_left_boxes_are_flipped_to_a_top_left_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A run near the head of the page: 92pt down from the top on a 792pt page.
    item = _Item("MASTER SERVICES AGREEMENT", [_Prov(1, _Bbox(72, 700, 400, 680, "BOTTOMLEFT"))])
    _install_docling(monkeypatch, _Document([item]))

    blocks = worker._docling(Path("ignored.pdf"))

    assert len(blocks) == 1
    assert blocks[0].text == "MASTER SERVICES AGREEMENT"
    assert blocks[0].box == (72.0, 92.0, 400.0, 112.0)
    assert blocks[0].space == (612.0, 792.0)


def test_top_left_boxes_are_passed_through_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _Item("Governing Law: State of Delaware", [_Prov(1, _Bbox(72, 100, 400, 120, "TOPLEFT"))])
    _install_docling(monkeypatch, _Document([item]))

    blocks = worker._docling(Path("ignored.pdf"))

    assert blocks[0].box == (72.0, 100.0, 400.0, 120.0)


def test_each_item_becomes_its_own_element(monkeypatch: pytest.MonkeyPatch) -> None:
    """The old implementation returned the whole document as one markdown blob,
    which is what made a single element swallow every labelled clause."""
    items = [
        _Item("Governing Law: State of Delaware", [_Prov(1, _Bbox(72, 700, 400, 680, "BOTTOMLEFT"))]),
        _Item("Payment Terms: Net 30", [_Prov(1, _Bbox(72, 670, 400, 650, "BOTTOMLEFT"))]),
    ]
    _install_docling(monkeypatch, _Document(items))

    blocks = worker._docling(Path("ignored.pdf"))

    assert [block.text for block in blocks] == [
        "Governing Law: State of Delaware",
        "Payment Terms: Net 30",
    ]
    assert all(block.box is not None for block in blocks)


def test_an_item_without_provenance_keeps_its_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_docling(monkeypatch, _Document([_Item("Unpositioned text", [])]))

    blocks = worker._docling(Path("ignored.pdf"))

    assert blocks[0].text == "Unpositioned text"
    assert blocks[0].box is None
    assert blocks[0].space is None


def test_an_unfamiliar_docling_build_falls_back_to_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Hostile(_Document):
        def iterate_items(self) -> list[tuple[_Item, int]]:
            raise AttributeError("iterate_items moved in this release")

    _install_docling(monkeypatch, _Hostile([_Item("Whole document text")]))

    blocks = worker._docling(Path("ignored.pdf"))

    # Text survives; only the geometry is lost.
    assert [block.text for block in blocks] == ["Whole document text"]
    assert blocks[0].box is None


def test_a_box_with_inverted_edges_is_dropped_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`BoundingBox` refuses unordered coordinates, and a validation error in
    the worker's output would sink the whole extraction, text included."""
    item = _Item("Reversed", [_Prov(1, _Bbox(400, 100, 72, 120, "TOPLEFT"))])
    _install_docling(monkeypatch, _Document([item]))

    blocks = worker._docling(Path("ignored.pdf"))

    assert blocks[0].text == "Reversed"
    assert blocks[0].box is None


# --------------------------------------------------------------------------
# paddleocr
# --------------------------------------------------------------------------


def test_paddle_axis_aligned_boxes_pair_with_their_text() -> None:
    raw = {
        "res": {
            "rec_texts": ["Invoice", "Total"],
            "rec_boxes": [[10, 20, 110, 40], [10, 60, 110, 80]],
        }
    }
    assert worker._paddle_geometry(raw) == [(10.0, 20.0, 110.0, 40.0), (10.0, 60.0, 110.0, 80.0)]


def test_paddle_polygons_reduce_to_their_extent() -> None:
    raw = {"res": {"rec_polys": [[[10, 20], [110, 22], [110, 40], [10, 38]]]}}
    assert worker._paddle_geometry(raw) == [(10.0, 20.0, 110.0, 40.0)]


def test_paddle_geometry_is_empty_when_nothing_is_reported() -> None:
    assert worker._paddle_geometry({"res": {"rec_texts": ["Invoice"]}}) == []


def test_a_malformed_paddle_box_yields_none_for_that_slot_only() -> None:
    """Text and boxes are matched by position, so a bad entry must hold its
    place rather than shift every later box onto the wrong words."""
    raw = {"res": {"rec_boxes": [[10, 20, 110, 40], "nonsense", [10, 60, 110, 80]]}}
    boxes = worker._paddle_geometry(raw)
    assert boxes[0] == (10.0, 20.0, 110.0, 40.0)
    assert boxes[1] is None
    assert boxes[2] == (10.0, 60.0, 110.0, 80.0)


# --------------------------------------------------------------------------
# The emitted element
# --------------------------------------------------------------------------


def test_geometry_reaches_the_element_payload() -> None:
    block = worker.Block("Governing Law", (72.0, 92.0, 400.0, 112.0), (612.0, 792.0))

    element = worker._element(1, "docling", 0, block)

    assert element["bounding_box"] == {
        "left": 72.0,
        "top": 92.0,
        "right": 400.0,
        "bottom": 112.0,
    }
    assert element["coordinate_space"] == {
        "width": 612.0,
        "height": 792.0,
        "origin": "top-left",
    }


def test_a_block_without_geometry_omits_both_keys() -> None:
    element = worker._element(1, "mineru", 0, worker.Block("Markdown text"))

    assert "bounding_box" not in element
    assert "coordinate_space" not in element
    assert element["text"] == "Markdown text"


def test_a_box_without_a_space_is_not_emitted_half_way() -> None:
    """Half a pair cannot be drawn and would only look like a bug downstream."""
    element = worker._element(1, "paddleocr", 0, worker.Block("Text", (1, 2, 3, 4), None))

    assert "bounding_box" not in element
    assert "coordinate_space" not in element


def test_the_emitted_element_validates_against_the_real_model() -> None:
    """The worker writes JSON that `AdapterResult` parses on the way back in, so
    a shape mismatch here would fail the whole job at the callback."""
    from app.visual_document_extractor.models import ExtractedElement

    block = worker.Block("Governing Law", (72.0, 92.0, 400.0, 112.0), (612.0, 792.0))
    element = ExtractedElement.model_validate(worker._element(1, "docling", 0, block))

    assert element.bounding_box is not None
    assert element.coordinate_space is not None
    assert element.coordinate_space.origin == "top-left"
