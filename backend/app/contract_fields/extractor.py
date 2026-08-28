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
from .normalize import collapse_whitespace

MAX_ELEMENTS_FOR_PROVIDER = 120
MAX_ELEMENT_CHARS = 400

PROVIDER_UNAVAILABLE_WARNING = (
    "Field extraction ran deterministically only: the language model provider was "
    "unavailable. Values it might have found are blank and flagged for verification."
)


class FieldCandidate(BaseModel):
    """One proposal for one field, with the source it must be checked against.

    `values` is a list because a candidate may carry several source spans; every other
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
    "customer": (r"by and between", r"\bbetween\b", r"\bparties\b"),
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
    "customer": (r"parties",),
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
) -> tuple[int, int] | None:
    r"""The span of the label that starts earliest in the element.

    Tuple order is specificity order, not position order, so picking the first
    pattern that matches anywhere truncates the value: on "Termination: Termination
    for convenience on notice" the specific pattern matches at offset 13 and the
    value becomes "on notice".

    Earliest-start alone is not enough either. Two patterns can describe the *same*
    label with different extents — on "Automatic Renewal Terms: ..." the loose
    `auto…renew\w*` matches "Automatic Renewal" (0, 17) while `renewal\s+terms?`
    matches "Renewal Terms" (10, 23). Taking only the earliest stops mid-label and
    hands the remainder back as the value: `"Terms: ..."`, or a bare `"Terms:"` when
    the clause carries no value. So the span is **extended through any match that
    overlaps it and reaches further**, which consumes the label whole.

    Extension requires an overlap, so a later, disjoint match is never absorbed:
    "Termination" (0, 11) does not reach "Termination for convenience" (13, 40), and
    a value-shaped pattern sitting after the label — `\bnet\s+\d{1,3}\b` on
    "Payment Terms: Net 30" — stays outside the span and survives as the value.
    """

    matches = [match for pattern in patterns if (match := pattern.search(text))]
    if not matches:
        return None
    chosen = min(matches, key=lambda match: match.start())
    start, end = chosen.start(), chosen.end()
    extended = True
    while extended:
        extended = False
        for match in matches:
            if match.start() <= end < match.end():
                end = match.end()
                extended = True
    return start, end


def _text_of(element: ExtractedElement) -> str:
    return (element.reviewed_text or element.text).strip()


def _has_letters(text: str) -> bool:
    return bool(re.search(r"[^\W\d_]", text))


#: Any field's label written inline, i.e. followed by a separator. Built from the
#: anchored heading forms, so a value that merely mentions "termination" is not a
#: label — only "Termination Clause:" is.
_NEXT_LABEL_INLINE = re.compile(
    r"(?:(?<=\s)|(?<=^))(?:"
    + "|".join(
        pattern for patterns in _HEADINGS.values() for pattern in patterns if pattern
    )
    + r")\s*[:\-—–]",
    re.I,
)

#: The same, as a heading occupying its own line.
_NEXT_LABEL_LINE = re.compile(
    r"^[ \t]*(?:"
    + "|".join(
        pattern for patterns in _HEADINGS.values() for pattern in patterns if pattern
    )
    + r")[ \t]*$",
    re.I | re.MULTILINE,
)


def _cut_at_next_label(tail: str) -> str:
    """Truncate at the next field's label.

    One element does not mean one clause. A digital parser returns a whole block —
    "Governing Law: … \n Payment Terms: … \n Notice Period: …" — as a single
    element, and taking everything after the label made each field swallow every
    clause that followed it. (Word-level OCR hid this: there was never more than one
    clause in an element to run into.)

    Only a *labelled* boundary cuts, so prose that happens to contain "termination"
    survives while "Termination Clause:" ends the value.
    """

    cuts = [
        match.start()
        for match in (_NEXT_LABEL_INLINE.search(tail), _NEXT_LABEL_LINE.search(tail))
        if match is not None
    ]
    if not cuts:
        return tail
    cut = min(cuts)
    # A boundary at position 0 would mean the label was immediately followed by
    # another label; that leaves no value, which the caller already handles.
    return tail[:cut] if cut > 0 else tail


def _after_label(text: str, label: tuple[int, int]) -> str:
    """The text following a label span, up to the next label.

    The separating colon or dash is removed; the value stops where the next field's
    clause begins.
    """

    tail = text[label[1] :]
    tail = re.sub(r"^\s*[:\-—–]\s*", " ", tail)
    return _cut_at_next_label(tail).strip(" \t.;")


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


def _comparable_organization(name: str) -> str:
    """An organisation name reduced for comparison only — never for storage.

    Case, punctuation, and the corporate suffix are all things the same company is
    written with and without across one contract ("Acme Corp, Inc." in the preamble,
    "Acme Corp" in the signature block), so none of them may decide identity.
    """

    stripped = re.sub(r"[^\w\s]", " ", name.casefold())
    stripped = _ENTITY_AT_END.sub("", stripped)
    return collapse_whitespace(stripped).strip()


def is_home_organization(name: str) -> bool:
    """Whether this party is the organisation running the deployment.

    Matching is containment in either direction on the comparable form, so a
    configured "Acme Corp, Inc." recognises "Acme Corp" in the document and vice
    versa. An alias that is not configured is treated as the counterparty — the
    failure mode is a value a human can see and correct, never a silently dropped
    party.
    """

    target = _comparable_organization(name)
    if not target:
        return False
    for home in settings.CONTRACT_HOME_ORGANIZATIONS:
        candidate = _comparable_organization(home)
        if not candidate:
            continue
        if target == candidate or target in candidate or candidate in target:
            return True
    return False


def _strip_home_organization(body: str) -> str:
    """The preamble with the home organisation's name removed from either end.

    Returns a **contiguous** span of the original text — the side of the home name
    that is left — never a stitched-together string, because a value that is not a
    substring of its source element cannot be grounded.

    Empty when no configured name is found, when nothing is left, or when what is
    left still looks like the home organisation.
    """

    for home in settings.CONTRACT_HOME_ORGANIZATIONS:
        name = home.strip()
        if not name:
            continue
        # Longest form first, then without the corporate suffix: a contract that
        # says "Acme Corp" in the preamble and "Acme Corp, Inc." in the signature
        # block is one company, and only the configured spelling would match here.
        forms = [name]
        without_suffix = _ENTITY_AT_END.sub("", name).strip(" ,.;")
        if without_suffix and without_suffix.casefold() != name.casefold():
            forms.append(without_suffix)

        found = None
        for form in forms:
            # Allow punctuation and spacing drift, the same tolerance
            # `is_home_organization` applies.
            # `(?!\w)` rather than a trailing `\b`: the form may end in punctuation
            # ("Inc."), where `\b` asserts the wrong thing. Without it "Acme Corp"
            # matched inside "Acme Corporation" and left "oration and ..." behind.
            pattern = re.compile(
                r"\b"
                + r"[\s.,]*".join(re.escape(part) for part in form.split())
                + r"(?!\w)",
                re.I,
            )
            found = pattern.search(body)
            if found is not None:
                break
        if found is None:
            continue
        before = body[: found.start()]
        after = body[found.end() :]
        for side in (after, before):
            candidate = _CONJUNCTION_EDGE.sub("", side).strip(" ,;.&")
            if candidate and _has_letters(candidate):
                return candidate
    return ""


#: A leading or trailing "and"/"&" left behind once the home name is removed.
_CONJUNCTION_EDGE = re.compile(r"^\s*(?:and|&)\s+|\s+(?:and|&)\s*$", re.I)


def _customer_candidate(
    elements: list[ExtractedElement], page: int
) -> FieldCandidate | None:
    """The counterparty: the one party that is not the home organisation.

    This is where the schema got simpler. The old `parties` field had to delimit an
    arbitrary number of entities and hand them all on, which put the whole
    "how many parties are there" problem into the grounding path. A contract has a
    home side and an other side; the home side is configuration, so the answer is a
    single name and the ambiguity is gone.

    Exactly one survivor is required. Zero means every named party is the home
    organisation; more than one means the counterparty is genuinely ambiguous. Both
    return no candidate, so the field blanks and a human is asked — never a guess.
    """

    for element in elements:
        text = _text_of(element)
        match = _PARTY_PREAMBLE.search(text)
        if match is None:
            continue
        body = match.group("body")

        names = split_parties(body)
        others = [name for name in names if not is_home_organization(name)]
        if len(others) == 1:
            return FieldCandidate(
                field_key="customer",
                values=others,
                source_element_ids=[element.element_id],
                page_number=page,
                confidence=element.confidence,
            )

        # Splitting did not resolve it — an unrecognised corporate suffix leaves the
        # preamble as one string, and that string *contains* the home name, so it
        # reads as the home organisation and the field would blank.
        #
        # Knowing the home name gives a second route that does not need the split to
        # be right: find that name and take the text on the other side of it. The
        # result is still a contiguous span of the source, so it stays groundable.
        remainder = _strip_home_organization(body)
        if remainder and not is_home_organization(remainder):
            return FieldCandidate(
                field_key="customer",
                values=[remainder],
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


#: How far past a bare heading to look for its clause. Generous, because word-level
#: OCR spreads one clause over many elements; bounded, because a clause that never
#: terminates must not swallow the rest of the page.
_CLAUSE_LOOKAHEAD = 40


def _label_across_elements(
    definition: FieldDefinition,
    elements: list[ExtractedElement],
    page: int,
) -> FieldCandidate | None:
    r"""Second pass for documents whose *label* is split across elements.

    Word-level OCR emits "Notice" and "Period:" as separate elements, so no single
    element matches `notice\s+period` and the per-element scan finds no label at all —
    the field simply never gets a candidate. This joins a window of elements, finds
    the label in the joined text, and maps the value's character span back to the
    elements it came from so the citation stays honest.

    Runs only when the per-element scan found nothing, so paragraph-level documents —
    where one element already holds the whole clause — are unaffected.
    """

    patterns = LABEL_PATTERNS[definition.key]
    tokens = [
        (element.element_id, _text_of(element))
        for element in elements
        if _text_of(element)
    ]
    for start in range(len(tokens)):
        window = tokens[start : start + _CLAUSE_LOOKAHEAD]
        if len(window) < 2:
            break
        offsets: list[tuple[int, int]] = []
        cursor = 0
        for _, token_text in window:
            offsets.append((cursor, cursor + len(token_text)))
            cursor += len(token_text) + 1
        joined = " ".join(token_text for _, token_text in window)

        label = _earliest_label(joined, patterns)
        # The label must open this window; a label further in belongs to the window
        # that starts on it, and matching it here would swallow the preceding clause.
        if label is None or label[0] != 0:
            continue
        # A single element already carrying the whole label is the first pass's job.
        if label[1] <= offsets[0][1]:
            continue

        value_start = label[1]
        value_end = len(joined)
        # A new clause heading ends this one — but only once this clause has started.
        # The first word after "Termination Clause:" is "Termination", which reads as
        # a heading on its own; breaking there left "on written notice." as the value.
        started = False
        for position, (token_start, token_end) in enumerate(offsets):
            # `token_start`, not `token_end`: the label's last token overlaps the
            # value by its separator ("Clause:" ends one character past the label),
            # and letting it count as the first value word consumed `started` — so
            # the next word broke the loop and the value began mid-clause.
            if token_start < value_start:
                continue
            token_text = window[position][1]
            # Test the heading against the *joined remainder*, not the lone token:
            # headings are word-split too, so "Payment" on its own matches nothing
            # and the clause ran on through "Payment Terms: ... Notice Period: ..."
            # into the fields that followed it.
            if started and _starts_a_heading(joined[token_start:]):
                value_end = token_start
                break
            started = True
            if token_text.endswith((".", ";")):
                value_end = token_end
                break

        raw = joined[value_start:value_end]
        lead = re.match(r"^\s*[:\-—–]?\s*", raw)
        offset = lead.end() if lead is not None else 0
        value = raw[offset:].strip()
        if not value or not _has_letters(value):
            continue

        # Cite only the elements the value itself covers. Counting the separator in
        # made the label's own element a citation ("Law:" for "State of Delaware"),
        # and gate 1 rejects a value that does not account for everything it cites —
        # so an off-by-one-character span blanked a correctly extracted field.
        value_from = value_start + offset
        value_to = value_from + len(value)
        cited = [
            token_id
            for (token_id, _), (token_start, token_end) in zip(
                window, offsets, strict=True
            )
            if token_end > value_from and token_start < value_to
        ]
        if not cited:
            continue
        return FieldCandidate(
            field_key=definition.key,
            values=[value],
            source_element_ids=cited,
            page_number=page,
            confidence=None,
        )
    return None


def _starts_a_heading(text: str) -> bool:
    """Whether this element opens some field's clause — any field, not just ours."""

    return any(
        pattern.match(text)
        for patterns in HEADING_PATTERNS.values()
        for pattern in patterns
    )


def _verbatim_candidate(
    definition: FieldDefinition,
    elements: list[ExtractedElement],
    page: int,
    *,
    allow_follow_on: bool = True,
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
        # A bare heading: the clause is what follows it.
        #
        # This cannot assume one element per clause. Tesseract emits one element per
        # *word*, so both the label and its value arrive split: "Renewal", "Terms:",
        # "Automatic", "renewal", ... Taking the single next element then returned the
        # rest of the label as the value — the `"Terms:"` and `"Clause:"` defect.
        #
        # So: absorb any following element that is still part of the label, then
        # gather the clause until it ends.
        if not allow_follow_on:
            continue
        gathered: list[str] = []
        source_ids: list[str] = []
        prefix = text
        for following in elements[index + 1 : index + 1 + _CLAUSE_LOOKAHEAD]:
            body = _text_of(following)
            if not body:
                continue
            if not gathered:
                # Still completing the label? Re-read the label across the join and
                # see whether anything is left over. "Renewal" + "Terms:" yields no
                # tail, so "Terms:" is label, not value.
                joined = f"{prefix} {body}"
                joined_label = _earliest_label(joined, patterns)
                if joined_label is not None:
                    joined_tail = _after_label(joined, joined_label)
                    if not (joined_tail and _has_letters(joined_tail)):
                        prefix = joined
                        continue
            # A new clause heading ends this one, whichever field it announces.
            if gathered and _starts_a_heading(body):
                break
            if not _has_letters(body) and not gathered:
                continue
            gathered.append(body)
            source_ids.append(following.element_id)
            if body.endswith((".", ";")):
                break
        if gathered:
            return FieldCandidate(
                field_key=definition.key,
                # Joined verbatim, terminator included: the clause's own full stop is
                # part of the source text, and stripping it makes the value stop being
                # a faithful excerpt — grounding then scores it "not fully supported"
                # and blanks a value that was correct.
                values=[" ".join(gathered).strip()],
                source_element_ids=source_ids,
                page_number=page,
                confidence=element.confidence,
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
            elif key == "customer":
                found = _customer_candidate(elements, page.page_number)
            elif definition.value_format in (
                ValueFormat.DATE_DDMMYYYY,
                ValueFormat.CURRENCY_AMOUNT,
            ):
                found = _shaped_candidate(definition, elements, page.page_number)
            else:
                # Ordered by how much evidence sits in one place. A label and its
                # value in the same element is unambiguous; reading a label across
                # elements is next; following a bare heading to whatever comes after
                # is the weakest, and must not pre-empt the other two — a loose
                # value-shaped pattern ("\binvoice\b") matching mid-clause would
                # otherwise return the next word ("date.") as the whole answer.
                found = (
                    _verbatim_candidate(
                        definition, elements, page.page_number, allow_follow_on=False
                    )
                    or _label_across_elements(definition, elements, page.page_number)
                    or _verbatim_candidate(definition, elements, page.page_number)
                )
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
- `customer` is the counterparty: the single organisation the agreement is with,
  named exactly as the document names it. It is never the home organisation named
  below — if the only party in the contract is the home organisation, return an
  empty string rather than naming it.
- Every value must cite at least one element id it appears in.

Reply with JSON only: {"fields": {"<field_key>": {"value": "...", "element_ids":
["..."]}}}.
"""


def _system_prompt() -> str:
    """The prompt with the deployment's own organisation names filled in.

    Built per call rather than at import so a changed setting takes effect without a
    restart, and so tests can vary it.
    """

    names = [name for name in settings.CONTRACT_HOME_ORGANIZATIONS if name.strip()]
    home = "; ".join(names) if names else "(none configured)"
    return f"{_SYSTEM_PROMPT}\nHome organisation (never the customer): {home}\n"


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
            {"role": "system", "content": _system_prompt()},
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
