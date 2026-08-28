"""Grounding for proposed field values.

A thin wrapper over `visual_document_extractor.semantic` — `verify_candidate`,
`GroundingStatus`, and its sensitive-token pattern are **imported, never forked**.

Two gates, in order:

1. `verify_candidate`, unchanged. It answers the spec's *"is a normalization of"*
   clause by comparing a proposal against the **whole** cited text.
2. The **excerpt gate**, which answers the spec's other clause — a value that
   *"appears in ... the text of at least one source element"*. Gate 1 cannot accept a
   true excerpt of a longer element ("Net 30 days from invoice date" out of "Payment
   Terms: Net 30 days from invoice date" scores 0.25), so without this every verbatim
   field would be permanently blank.

Gate 2 is the weaker gate, so it is fenced. It accepts only a span that really is in
**one** element, and it refuses:

* anything `verify_candidate` rejected for a **sensitive mismatch** — a changed
  number, identifier, URL, or negation is a must-blank verdict under spec rule 3, and
  the check is re-applied scoped to the matched span rather than dropped;
* a splice across two elements — the haystack is one element at a time, never a join;
* an excerpt that leaves a negation behind in the clause it came from, counted by
  occurrence, so keeping one "not" cannot cover for dropping another;
* a date or an amount whose enclosing clause does not name its own field — the same
  discipline the deterministic extractor applies ("an unlabelled date or amount is a
  guess"), now applied to every candidate whatever proposed it;
* a bare label ("Governing Law") standing in for its own value.

An acceptance here is recorded as `NEEDS_REVIEW` with its real grounding score, so a
value that took the loosened path is visible as such in the provenance instead of
looking like a clean pass.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from app.visual_document_extractor.models import ExtractedElement

# `_SENSITIVE` is imported rather than re-implemented: it is the pattern whose
# verdict spec rule 3 treats as must-blank, and gate 2 re-applies it at span scope.
from app.visual_document_extractor.semantic import _SENSITIVE as SENSITIVE_TOKENS
from app.visual_document_extractor.semantic import (
    GroundingStatus,
    SemanticCandidate,
    verify_candidate,
)

from .catalogue import FIELD_BY_KEY, ValueFormat
from .extractor import HEADING_PATTERNS, LABEL_PATTERNS
from .normalize import collapse_whitespace

#: Verdicts from gate 1 whose value may be kept as-is.
ACCEPTED_STATUSES = frozenset(
    {GroundingStatus.GROUNDED, GroundingStatus.GROUNDED_WITH_NORMALIZATION}
)

#: Gate 1 verdicts that gate 2 may never override — a citation that does not resolve,
#: or a value spliced across elements. Neither can be rescued by re-reading one
#: element, so there is nothing for gate 2 to do.
#:
#: `REJECTED_SENSITIVE_MISMATCH` is deliberately **not** here. Gate 1 compares the
#: proposal against the *whole* cited element, so a numbered clause fails it for the
#: wrong reason: on "8. Governing Law: State of Delaware" the value drops the clause
#: number "8", gate 1 counts that as a changed number, and the field blanks — while
#: the identical unnumbered clause succeeds. On a realistically numbered contract that
#: blanked most of the schema.
#:
#: Blanking is still the answer when a number really did change; that judgement just
#: belongs at span scope, and gate 2 makes it: `excerpt_of_element` requires the value
#: to appear verbatim in one element, **re-applies the sensitive-token comparison to
#: the matched span**, requires every negation to survive, and requires a date or
#: amount to sit in a clause naming its field. A proposal that alters a number cannot
#: pass all four; a proposal that merely omits the clause number passes them all.
#: Listing the verdict here made that span-scoped re-check dead code for the one
#: verdict it was written for.
NEVER_OVERRIDABLE = frozenset(
    {
        GroundingStatus.REJECTED_INVALID_REFERENCE,
        GroundingStatus.REJECTED_OVERLAP,
    }
)

#: Fields whose value is only trustworthy when its clause names the field. A date or
#: an amount is otherwise just the nearest number, which is how a recital date
#: becomes a term end date.
LABEL_REQUIRED_FORMATS = frozenset(
    {ValueFormat.DATE_DDMMYYYY, ValueFormat.CURRENCY_AMOUNT}
)

# Dropping one of these turns a clause into its opposite or strips its carve-out.
_NEGATION = re.compile(
    r"\b(?:not|no|never|nor|none|neither|without|unless|except|excluding|"
    r"other\s+than|save\s+for|save\s+that|provided\s+that|subject\s+to)\b",
    re.I,
)

# A clause ends at a period, semicolon, or comma **followed by space**, so
# "USD 250,000.00" is never cut in half. A colon is deliberately *not* a boundary:
# it separates a label from its value ("Effective Date: 15 January 2026"), and the
# two belong to the same clause or the label requirement below could never be met.
_CLAUSE_BOUNDARY = re.compile(r"(?<=[.;,])\s+|\n+")


class GroundedValue(BaseModel):
    """One verdict: the value to keep (``""`` when rejected) and why."""

    model_config = ConfigDict(frozen=True)

    field_key: str
    value: str
    status: GroundingStatus
    score: float = Field(ge=0, le=1)
    source_element_ids: list[str] = Field(default_factory=list)
    detail: str | None = None
    accepted: bool = False


def _text_of(element: ExtractedElement) -> str:
    return (element.reviewed_text or element.text).strip()


def _negation_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for hit in _NEGATION.findall(text):
        marker = collapse_whitespace(hit).casefold()
        counts[marker] = counts.get(marker, 0) + 1
    return counts


def _span_pattern(value: str) -> re.Pattern[str] | None:
    """A whitespace-tolerant matcher for `value`, so a line break in the source does
    not hide an otherwise exact excerpt."""

    tokens = [re.escape(token) for token in collapse_whitespace(value).split()]
    if not tokens:
        return None
    return re.compile(r"\s+".join(tokens), re.I)


def _span_clause(haystack: str, start: int, end: int) -> str:
    """Every clause the span touches, joined.

    Used **only** for the date/amount label requirement, where clause scoping makes
    the gate stricter rather than looser: the label has to sit with the value, so a
    "termination date" mentioned three clauses before a recital date does not
    license it. The negation guard deliberately does not use this — there, narrowing
    the window would let a carve-out escape.
    """

    offset = 0
    region: list[str] = []
    for clause in _CLAUSE_BOUNDARY.split(haystack):
        clause_start = haystack.find(clause, offset)
        if clause_start < 0:
            clause_start = offset
        clause_end = clause_start + len(clause)
        offset = clause_end
        if start < clause_end and clause_start < end:
            region.append(clause)
    return " ".join(region) if region else haystack


def _negations_survive(span: str, element_text: str) -> bool:
    """Every negation in the element must survive into the excerpt.

    Counted over the **whole element**, not the clauses the span happens to touch.
    Clause scoping was inert for the way carve-outs are actually written: a comma
    puts "..., other than for cause" in a clause the span does not touch, so the
    same sentence flipped verdict on one comma. Counting occurrences (not a set)
    also stops a proposal that keeps one "not" from covering for dropping another.

    Stricter than clause scoping, and deliberately so: a stray "no" elsewhere in the
    element blanks the field and a human reads it off the source. Blank beats a guess.
    """

    span_negations = _negation_counts(span)
    return all(
        span_negations.get(marker, 0) >= count
        for marker, count in _negation_counts(element_text).items()
    )


def is_label_only(field_key: str, value: str) -> bool:
    """True when the proposal is nothing but the field's own heading.

    Checked against `HEADING_PATTERNS` — the anchored "this element announces the
    field" forms — never against the extractor's search patterns, several of which
    are *value* shapes ("Net 30", "automatic renewal") and would blank the real
    answer.
    """

    text = collapse_whitespace(value)
    if not text:
        return False
    for pattern in HEADING_PATTERNS.get(field_key, ()):
        match = pattern.match(text)
        if match is not None and match.end() >= len(text):
            return True
    return False


def _clause_names_the_field(field_key: str, region: str) -> bool:
    return any(pattern.search(region) for pattern in LABEL_PATTERNS.get(field_key, ()))


def excerpt_of_element(field_key: str, value: str, element_text: str) -> str | None:
    """Gate 2 against **one** element. Returns the matched source span, or None.

    The span is returned rather than the proposal, so a field documented as
    "verbatim, trimmed" keeps the document's own casing and spacing.
    """

    pattern = _span_pattern(value)
    if pattern is None or not element_text.strip():
        return None

    haystack = element_text
    match = pattern.search(haystack)
    if match is None:
        haystack = collapse_whitespace(element_text)
        match = pattern.search(haystack)
    if match is None:
        return None

    span = match.group(0)
    start, end = match.start(), match.end()

    # The sensitive check, re-applied at span scope rather than dropped. An exact
    # excerpt satisfies it trivially; a whitespace- or NFKC-driven difference in a
    # number does not.
    if SENSITIVE_TOKENS.findall(collapse_whitespace(span)) != SENSITIVE_TOKENS.findall(
        collapse_whitespace(value)
    ):
        return None

    if not _negations_survive(span, haystack):
        return None

    # A date or an amount must sit in a clause that names its own field.
    definition = FIELD_BY_KEY.get(field_key)
    if (
        definition is not None
        and definition.value_format in LABEL_REQUIRED_FORMATS
        and not _clause_names_the_field(field_key, _span_clause(haystack, start, end))
    ):
        return None

    return span.strip()


def ground_value(
    field_key: str,
    value: str,
    source_element_ids: list[str],
    elements: list[ExtractedElement],
    *,
    source_order: int = 0,
) -> GroundedValue:
    """Verify one proposed value against the elements it cites."""

    cited = list(dict.fromkeys(source_element_ids))
    if not value.strip() or not cited:
        return GroundedValue(
            field_key=field_key,
            value="",
            status=GroundingStatus.REJECTED_UNGROUNDED,
            score=0,
            source_element_ids=cited,
            detail="no value or no cited source",
        )

    # A heading is not an answer. Screened before gate 1, because an element that
    # *is* just the heading would otherwise pass gate 1 as an exact whole-element
    # match with score 1.0 — reachable whenever a candidate cites a bare heading.
    if is_label_only(field_key, value):
        return GroundedValue(
            field_key=field_key,
            value="",
            status=GroundingStatus.REJECTED_UNGROUNDED,
            score=0,
            source_element_ids=cited,
            detail="the value is only the field's own label",
        )

    verification = verify_candidate(
        SemanticCandidate(
            candidate_id=field_key,
            key=field_key,
            value=value,
            source_element_ids=cited,
            source_order=source_order,
        ),
        elements,
    )
    if verification.status in ACCEPTED_STATUSES:
        return GroundedValue(
            field_key=field_key,
            value=value,
            status=verification.status,
            score=verification.grounding_score,
            source_element_ids=cited,
            detail=verification.detail,
            accepted=True,
        )

    if verification.status not in NEVER_OVERRIDABLE:
        # Gate 2, one element at a time: a value spliced across two elements is in
        # neither of them, and "at least one source element" means one.
        by_id = {element.element_id: element for element in elements}
        for element_id in cited:
            element = by_id.get(element_id)
            if element is None:
                continue
            span = excerpt_of_element(field_key, value, _text_of(element))
            if span is None:
                continue
            return GroundedValue(
                field_key=field_key,
                value=span,
                status=GroundingStatus.NEEDS_REVIEW,
                score=verification.grounding_score,
                # Only the element the span actually came from.
                source_element_ids=[element_id],
                detail="verbatim excerpt of the cited source",
                accepted=True,
            )

    return GroundedValue(
        field_key=field_key,
        value="",
        status=verification.status,
        score=verification.grounding_score,
        source_element_ids=cited,
        detail=verification.detail,
    )
