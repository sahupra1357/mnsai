"""Propose field values from content the visual extractor already produced.

This module never runs OCR. Its input is the normalized `elements` (and, when
present, the `semantic_result`) of a `DocumentResult`; its output is a candidate per
requested field, each citing the element ids it came from so `grounding.py` can
verify it.

Two sources, in this order:

1. **Deterministic** — label and shape matching over the elements. Always runs, needs
   no provider, and is what keeps the feature working when the LLM is unavailable.
2. **LLM-assisted** — an optional pass that fills fields the deterministic pass left
   empty. The key in `.env` currently returns 401, so every provider failure is
   caught and degrades to deterministic-only with a warning. It never raises, never
   500s, and **never logs the prompt or the provider's output.**

Delimiting the parties is this module's job, not the normalizer's: the normalizer
takes whatever it is handed as one party, so deciding that a preamble names two
entities happens here, against the source text.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.visual_document_extractor.models import DocumentResult, ExtractedElement

from .catalogue import FIELD_BY_KEY, FieldDefinition, ValueFormat

MAX_ELEMENTS_FOR_PROVIDER = 120
MAX_ELEMENT_CHARS = 400

PROVIDER_UNAVAILABLE_WARNING = (
    "Field extraction ran deterministically only: the language model provider was "
    "unavailable. Values it might have found are blank and flagged for verification."
)


class FieldCandidate(BaseModel):
    """One proposal for one field, with the source it must be checked against.

    `values` is a list because `parties` may resolve to several names; every other
    field carries exactly one. Each value is grounded independently.
    """

    model_config = ConfigDict(frozen=True)

    field_key: str
    values: list[str] = Field(min_length=1)
    source_element_ids: list[str] = Field(min_length=1)
    page_number: int = Field(ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    origin: Literal["deterministic", "llm"] = "deterministic"


class CandidateSet(BaseModel):
    """Everything the extraction pass produced, plus how it went."""

    candidates: dict[str, FieldCandidate] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    provider_available: bool = True


# --------------------------------------------------------------------------- #
# Shapes worth recognizing
# --------------------------------------------------------------------------- #

_DATE_TEXT = re.compile(
    r"\b(?:"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?[A-Za-z]{3,9},?\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"
    r")\b"
)
_MONEY_TEXT = re.compile(
    r"(?:USD|EUR|GBP|JPY|INR|CAD|AUD|CHF|SGD|US\$|\$|€|£|¥|₹)\s?\d[\d.,]*"
    r"(?:\s*(?:thousand|million|billion|mm|bn|[kmb])\b)?",
    re.I,
)
_ENTITY_SUFFIX = (
    r"(?:inc|llc|l\.l\.c|ltd|limited|co|corp|corporation|company|plc|lp|llp|gmbh|"
    r"ag|sa|s\.a|nv|n\.v|bv|b\.v|pte|pty|sarl|kft|kg|oy|ab|as|srl|spa|"
    r"trust|foundation|university|institute|partners|holdings|group)\.?"
)
_ENTITY_AT_END = re.compile(rf"(?:^|\W){_ENTITY_SUFFIX}\s*$", re.I)
_PARTY_PREAMBLE = re.compile(
    r"(?:by\s+and\s+between|between|among)\s+(?P<body>.+)", re.I
)
_PARTY_TAIL = re.compile(
    r"\s*(?:\((?:the\s+)?[\"“']?(?:parties|party)[\"”']?\)|"
    r"\b(?:whereas|recitals?|witnesseth|now,?\s+therefore)\b).*$",
    re.I,
)
_ALIAS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
_CONJUNCTION = re.compile(r"\s+(?:and|&)\s+", re.I)
_COMMA = re.compile(rf",(?!\s*{_ENTITY_SUFFIX}(?:\s|,|$))", re.I)

# Ordered label patterns per field. The first element that matches wins.
_LABELS: dict[str, tuple[str, ...]] = {
    "contract_title": (),
    "parties": (r"by and between", r"\bbetween\b", r"\bparties\b"),
    "effective_date": (
        r"effective\s+date",
        r"commencement\s+date",
        r"\bdated\s+as\s+of\b",
        r"\bmade\s+(?:and\s+entered\s+into\s+)?as\s+of\b",
        r"\beffective\s+as\s+of\b",
    ),
    "term_end_date": (
        r"expiration\s+date",
        r"expiry\s+date",
        r"termination\s+date",
        r"\bend\s+date\b",
        r"\bexpires?\s+on\b",
        r"\bterminates?\s+on\b",
        r"\buntil\b",
    ),
    "contract_value": (
        r"total\s+contract\s+value",
        r"contract\s+value",
        r"total\s+consideration",
        r"aggregate\s+(?:amount|fee|value)",
        r"total\s+(?:fee|amount|price)",
        r"\bconsideration\b",
        r"\bfee\b",
    ),
    "governing_law": (
        r"governing\s+law",
        r"choice\s+of\s+law",
        r"governed\s+by\s+(?:and\s+construed\s+in\s+accordance\s+with\s+)?the\s+laws\s+of",
        r"laws\s+of\s+the\s+(?:state|commonwealth)\s+of",
    ),
    "payment_terms": (
        r"payment\s+terms",
        r"payment\s+schedule",
        r"\bpayable\b",
        r"\bnet\s+\d{1,3}\b",
        r"\binvoice\b",
    ),
    "notice_period": (
        r"notice\s+period",
        r"\d{1,3}\s+days[’']?\s+(?:prior\s+)?written\s+notice",
        r"written\s+notice",
        r"\bprior\s+notice\b",
    ),
    "renewal_terms": (
        r"renewal\s+terms?",
        r"auto(?:matic)?[- ]?renew\w*",
        r"\brenew\w*\b",
    ),
    "termination_clause": (
        r"termination\s+(?:clause|for\s+cause|for\s+convenience)",
        r"\btermination\b",
        r"may\s+terminate",
        r"\bterminate\b",
    ),
}

# Heading forms only — the anchored "this element announces the field" shapes.
# Deliberately NOT the same set as `_LABELS`: several entries there are *value*
# shapes (`\bnet\s+\d{1,3}\b`, `auto(?:matic)?[- ]?renew\w*`) which are exactly
# what a value looks like, so treating them as labels would blank the real value.
_HEADINGS: dict[str, tuple[str, ...]] = {
    "contract_title": (),
    "parties": (r"parties",),
    "effective_date": (r"effective\s+date", r"commencement\s+date"),
    "term_end_date": (
        r"expiration\s+date",
        r"expiry\s+date",
        r"termination\s+date",
        r"end\s+date",
    ),
    "contract_value": (
        r"total\s+contract\s+value",
        r"contract\s+value",
        r"total\s+consideration",
        r"total\s+(?:fee|amount|price)",
        r"consideration",
    ),
    "governing_law": (r"governing\s+law", r"choice\s+of\s+law"),
    "payment_terms": (r"payment\s+terms", r"payment\s+schedule"),
    "notice_period": (r"notice\s+period",),
    "renewal_terms": (r"renewal\s+terms?",),
    "termination_clause": (r"termination(?:\s+clause)?",),
}

#: A heading only counts when it *opens* the element and is followed by a separator
#: or the end of it — so "Net 30" inside "Payment Terms: Net 30" is never a heading.
HEADING_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    key: tuple(
        re.compile(rf"^\s*(?:{pattern})\s*(?::|—|–|-|$)", re.I) for pattern in patterns
    )
    for key, patterns in _HEADINGS.items()
}

#: Compiled label patterns per field. `grounding.py` reuses these to require
#: that a date or an amount sits in a clause that actually names its field.
LABEL_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    key: tuple(re.compile(pattern, re.I) for pattern in patterns)
    for key, patterns in _LABELS.items()
}


def _earliest_label(
    text: str, patterns: tuple[re.Pattern[str], ...]
) -> re.Match[str] | None:
    """The label match that starts earliest in the element.

    Tuple order is specificity order, not position order, so picking the first
    pattern that matches anywhere truncates the value: on "Termination: Termination
    for convenience on notice" the specific pattern matches at offset 13 and the
    value becomes "on notice".
    """

    matches = [match for pattern in patterns if (match := pattern.search(text))]
    return min(matches, key=lambda match: match.start()) if matches else None


def _text_of(element: ExtractedElement) -> str:
    return (element.reviewed_text or element.text).strip()


def _has_letters(text: str) -> bool:
    return bool(re.search(r"[^\W\d_]", text))


def _after_label(text: str, match: re.Match[str]) -> str:
    """The text following a label, with a separating colon or dash removed."""

    tail = text[match.end() :]
    tail = re.sub(r"^\s*[:\-—–]\s*", " ", tail)
    return tail.strip(" \t.;")


# --------------------------------------------------------------------------- #
# Parties — delimiting them is this module's decision
# --------------------------------------------------------------------------- #


def _looks_like_entity(name: str) -> bool:
    return bool(_ENTITY_AT_END.search(name))


def split_parties(segment: str) -> list[str]:
    """Delimit the entities named in a preamble.

    A split is only made when it corroborates itself — every resulting part reads
    as a legal entity on its own. "Acme Corp and Northwind Ltd" is two parties;
    "Johnson and Johnson" is one, and stays one, because "Johnson" is not an entity
    name. Nothing here rewrites a name; it only decides where one ends.
    """

    body = _PARTY_TAIL.sub("", segment).strip(" ,;")
    if not body:
        return []
    parts = [part for part in re.split(r"[;\n]", body) if part.strip()]
    for splitter in (_CONJUNCTION, _COMMA):
        expanded: list[str] = []
        for part in parts:
            pieces = splitter.split(part)
            if len(pieces) > 1 and all(
                _looks_like_entity(_ALIAS.sub("", piece).strip(" ,;"))
                for piece in pieces
            ):
                expanded.extend(pieces)
            else:
                expanded.append(part)
        parts = expanded
    # Trailing "." is part of "Inc." / "Ltd." — never trimmed.
    names = [part.strip(" ,;") for part in parts]
    return [name for name in names if name and _has_letters(name)]


# --------------------------------------------------------------------------- #
# Deterministic pass
# --------------------------------------------------------------------------- #


def _title_candidate(
    elements: list[ExtractedElement], page: int
) -> FieldCandidate | None:
    headings = [
        element
        for element in elements
        if element.type == "heading" and _has_letters(_text_of(element))
    ]
    pool = headings or [
        element for element in elements if _has_letters(_text_of(element))
    ]
    for element in pool[:5]:
        text = _text_of(element)
        if 3 <= len(text) <= 200:
            return FieldCandidate(
                field_key="contract_title",
                values=[text],
                source_element_ids=[element.element_id],
                page_number=page,
                confidence=element.confidence,
            )
    return None


def _parties_candidate(
    elements: list[ExtractedElement], page: int
) -> FieldCandidate | None:
    for element in elements:
        text = _text_of(element)
        match = _PARTY_PREAMBLE.search(text)
        if match is None:
            continue
        names = split_parties(match.group("body"))
        if names:
            return FieldCandidate(
                field_key="parties",
                values=names,
                source_element_ids=[element.element_id],
                page_number=page,
                confidence=element.confidence,
            )
    return None


def _shaped_candidate(
    definition: FieldDefinition,
    elements: list[ExtractedElement],
    page: int,
) -> FieldCandidate | None:
    """A date or an amount: prefer a labelled element, then any element carrying
    the shape, and excerpt only the date/amount phrase so normalization has a
    clean input."""

    shape = (
        _DATE_TEXT
        if definition.value_format is ValueFormat.DATE_DDMMYYYY
        else _MONEY_TEXT
    )
    patterns = LABEL_PATTERNS[definition.key]

    for element in elements:
        text = _text_of(element)
        if not text:
            continue
        label = _earliest_label(text, patterns)
        if label is None:
            # An unlabelled date or amount is a guess: the only date on the page is
            # not necessarily *this* field's date, and a rate is not the total. A
            # field with no label stays blank and goes to a human.
            continue
        found = shape.search(_after_label(text, label)) or shape.search(text)
        if found is None:
            continue
        return FieldCandidate(
            field_key=definition.key,
            values=[found.group(0).strip()],
            source_element_ids=[element.element_id],
            page_number=page,
            confidence=element.confidence,
        )
    return None


def _verbatim_candidate(
    definition: FieldDefinition,
    elements: list[ExtractedElement],
    page: int,
) -> FieldCandidate | None:
    """A verbatim clause: the text after its label, or the element that follows a
    bare heading."""

    patterns = LABEL_PATTERNS[definition.key]
    for index, element in enumerate(elements):
        text = _text_of(element)
        if not text:
            continue
        label = _earliest_label(text, patterns)
        if label is None:
            continue
        tail = _after_label(text, label)
        if tail and _has_letters(tail):
            return FieldCandidate(
                field_key=definition.key,
                values=[tail],
                source_element_ids=[element.element_id],
                page_number=page,
                confidence=element.confidence,
            )
        # A bare heading: the clause is the element that follows it.
        for following in elements[index + 1 : index + 3]:
            body = _text_of(following)
            if body and _has_letters(body):
                return FieldCandidate(
                    field_key=definition.key,
                    values=[body],
                    source_element_ids=[following.element_id],
                    page_number=page,
                    confidence=following.confidence,
                )
    return None


def extract_deterministic(
    document: DocumentResult, field_keys: list[str]
) -> dict[str, FieldCandidate]:
    """Label and shape matching over the elements. No provider, never fails."""

    candidates: dict[str, FieldCandidate] = {}
    for page in document.pages:
        elements = sorted(page.elements, key=lambda item: item.reading_order)
        if not elements:
            continue
        for key in field_keys:
            if key in candidates:
                continue
            definition = FIELD_BY_KEY[key]
            found: FieldCandidate | None
            if key == "contract_title":
                found = (
                    _title_candidate(elements, page.page_number)
                    if page.page_number == 1
                    else None
                )
            elif key == "parties":
                found = _parties_candidate(elements, page.page_number)
            elif definition.value_format in (
                ValueFormat.DATE_DDMMYYYY,
                ValueFormat.CURRENCY_AMOUNT,
            ):
                found = _shaped_candidate(definition, elements, page.page_number)
            else:
                found = _verbatim_candidate(definition, elements, page.page_number)
            if found is not None:
                candidates[key] = found
    return candidates


# --------------------------------------------------------------------------- #
# LLM-assisted pass — optional, and never fatal
# --------------------------------------------------------------------------- #

_SYSTEM_PROMPT = """\
You extract specific fields from a contract. You are given the document's text as a
numbered list of elements. For each requested field, return the value together with
the ids of the elements it came from.

Hard rules:
- Copy the value from the element text. Never paraphrase, summarize, or infer a value
  that is not written in the document.
- If a field is not stated in the document, return an empty string for it. A blank is
  always correct; a plausible guess is a defect.
- `parties` is a list of the contracting entities, each named exactly as the document
  names them.
- Every value must cite at least one element id it appears in.

Reply with JSON only: {"fields": {"<field_key>": {"value": "...", "element_ids":
["..."]}}}. For `parties` use {"values": ["...", "..."], "element_ids": ["..."]}.
"""


def _provider_payload(
    document: DocumentResult, field_keys: list[str]
) -> tuple[str, dict[str, str]]:
    lines: list[str] = []
    pages: dict[str, str] = {}
    for page in document.pages:
        for element in sorted(page.elements, key=lambda item: item.reading_order):
            text = _text_of(element)
            if not text:
                continue
            pages[element.element_id] = str(page.page_number)
            lines.append(f"[{element.element_id}] {text[:MAX_ELEMENT_CHARS]}")
            if len(lines) >= MAX_ELEMENTS_FOR_PROVIDER:
                break
        if len(lines) >= MAX_ELEMENTS_FOR_PROVIDER:
            break
    wanted = "\n".join(
        f"- {key}: {FIELD_BY_KEY[key].description}" for key in field_keys
    )
    return f"Fields to extract:\n{wanted}\n\nDocument elements:\n" + "\n".join(
        lines
    ), pages


def _parse_provider_reply(
    payload: str, field_keys: list[str], pages: dict[str, str]
) -> dict[str, FieldCandidate]:
    parsed: Any = json.loads(payload)
    fields = parsed.get("fields") if isinstance(parsed, dict) else None
    if not isinstance(fields, dict):
        return {}
    candidates: dict[str, FieldCandidate] = {}
    for key in field_keys:
        entry = fields.get(key)
        if not isinstance(entry, dict):
            continue
        raw_values = entry.get("values") if "values" in entry else [entry.get("value")]
        values = [
            value.strip()
            for value in (raw_values or [])
            if isinstance(value, str) and value.strip()
        ]
        ids = [
            element_id
            for element_id in (entry.get("element_ids") or [])
            if isinstance(element_id, str) and element_id in pages
        ]
        if not values or not ids:
            continue
        candidates[key] = FieldCandidate(
            field_key=key,
            values=values,
            source_element_ids=list(dict.fromkeys(ids)),
            page_number=int(pages[ids[0]]),
            origin="llm",
        )
    return candidates


def extract_with_provider(
    document: DocumentResult, field_keys: list[str]
) -> dict[str, FieldCandidate]:
    """Ask the model for the fields the deterministic pass missed.

    Raises on any provider or parsing problem; the caller degrades to
    deterministic-only. Nothing from the prompt or the reply is ever logged or put
    into an exception message.
    """

    from openai import OpenAI

    prompt, pages = _provider_payload(document, field_keys)
    if not pages:
        return {}
    response = OpenAI().chat.completions.create(
        model=settings.OPENAI_DEPLOYMENT_ID,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        return {}
    return _parse_provider_reply(content, field_keys, pages)


def propose_candidates(
    document: DocumentResult,
    field_keys: list[str],
    *,
    use_provider: bool = True,
) -> CandidateSet:
    """Deterministic first, then the provider for whatever is still missing."""

    candidates = extract_deterministic(document, field_keys)
    warnings: list[str] = []
    provider_available = True

    missing = [key for key in field_keys if key not in candidates]
    if missing and use_provider:
        try:
            for key, candidate in extract_with_provider(document, missing).items():
                candidates.setdefault(key, candidate)
        except Exception:
            # Deliberately opaque: provider errors carry prompt fragments and keys.
            provider_available = False
            warnings.append(PROVIDER_UNAVAILABLE_WARNING)
    return CandidateSet(
        candidates=candidates,
        warnings=warnings,
        provider_available=provider_available,
    )
