"""Total normalizers for the contract field values.

Every function here returns a ``str`` and **never raises**: anything it cannot parse
with certainty comes back as ``""``. Ambiguity is a failure, not an invitation to
guess — ``01/02/2026`` could be 1 February or 2 January, so it normalizes to ``""``
and the field is raised for human verification instead of being half-parsed.

Formats (confirmed by Pradeep, 2026-08-26):

* dates -> ``DD/MM/YYYY``;
* amounts -> ``"<CURRENCY> <amount>"`` with scale words **expanded**, so
  ``"$2 billion"`` is ``"USD 2000000000.00"`` and never ``"USD 2.00"``;
* parties -> taken exactly as the extractor delimited them, joined with ``"; "``.
  The normalizer **never splits**: "Smith and Wesson" is one party named "Smith and
  Wesson". How many parties a contract has is the extractor's decision in Phase 3,
  made from the source elements — there is nothing here left to get wrong.

*Consequence to respect:* a date is stored as ``DD/MM/YYYY`` **text**, so a SQL
``ORDER BY`` on a date column is lexical, not chronological. Nothing downstream may
offer or imply chronological sorting on these columns.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .catalogue import FIELD_BY_KEY, ValueFormat

_MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))

# YYYY-MM-DD / YYYY/MM/DD input — year first is never ambiguous to read.
_YEAR_FIRST_DATE = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
# D/M/YYYY or M/D/YYYY input — ambiguous unless one component is > 12.
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
# 15 January 2026
_DAY_MONTH_YEAR = re.compile(rf"\b(\d{{1,2}}) ({_MONTH_NAMES}) (\d{{4}})\b", re.I)
# January 15 2026
_MONTH_DAY_YEAR = re.compile(rf"\b({_MONTH_NAMES}) (\d{{1,2}}) (\d{{4}})\b", re.I)

_CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "US$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
}

_CURRENCY_CODES = frozenset(
    {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "INR",
        "CAD",
        "AUD",
        "NZD",
        "CHF",
        "SEK",
        "NOK",
        "DKK",
        "SGD",
        "HKD",
        "CNY",
        "ZAR",
        "AED",
        "MXN",
        "BRL",
        "PLN",
    }
)

# Scale words that are expanded into the amount. Dropping the scale silently is the
# defect this exists to prevent.
_SCALES: dict[str, Decimal] = {
    "k": Decimal(1_000),
    "thousand": Decimal(1_000),
    "m": Decimal(1_000_000),
    "mm": Decimal(1_000_000),
    "million": Decimal(1_000_000),
    "b": Decimal(1_000_000_000),
    "bn": Decimal(1_000_000_000),
    "billion": Decimal(1_000_000_000),
}

# Magnitude words we recognize as a scale but deliberately do not support. Matching
# them is what lets an unrecognized scale blank the value instead of quietly
# dropping it — an ordinary following word like "payable" is not a scale at all.
_UNSUPPORTED_SCALES = frozenset(
    {"t", "tn", "trillion", "quadrillion", "lakh", "lac", "cr", "crore"}
)

_SCALE_TOKENS = "|".join(
    sorted({*_SCALES, *_UNSUPPORTED_SCALES}, key=len, reverse=True)
)

# Deliberately loose: grab the whole numeric token and let `_decimal_amount` decide
# whether its grouping is unambiguous.
_AMOUNT = r"\d[\d.,]*"
_SYMBOLS = "|".join(re.escape(symbol) for symbol in _CURRENCY_SYMBOLS)
_CODES = "|".join(sorted(_CURRENCY_CODES))

# "USD 250,000.00" / "$250,000" / "$1.5 million" / "250,000.00 USD" / "2 million USD"
_CURRENCY_BEFORE = re.compile(
    rf"(?:(?P<code>{_CODES})|(?P<symbol>{_SYMBOLS}))\s*"
    rf"(?P<amount>{_AMOUNT})\s*(?P<scale>{_SCALE_TOKENS})?\b",
    re.I,
)
_CURRENCY_AFTER = re.compile(
    rf"(?P<amount>{_AMOUNT})\s*(?P<scale>{_SCALE_TOKENS})?\s*"
    rf"(?:(?P<code>{_CODES})|(?P<symbol>{_SYMBOLS}))\b",
    re.I,
)


def collapse_whitespace(raw: object) -> str:
    """NFKC-normalize, unify dashes, undo hyphenated line breaks, collapse spaces.

    Mirrors the tolerance of ``visual_document_extractor.semantic`` so a value that
    survives normalization here still matches its source element when it is grounded.
    """

    if not isinstance(raw, str):
        return ""
    value = unicodedata.normalize("NFKC", raw)
    value = value.replace("‐", "-").replace("‑", "-").replace("–", "-")
    value = re.sub(r"-\s*\n\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n\"'“”‘’")


def normalize_verbatim(raw: object) -> str:
    """Verbatim fields: the source text, trimmed and whitespace-collapsed."""

    return collapse_whitespace(raw)


def _build_date(year: int, month: int, day: int) -> str:
    """Format a real calendar date as ``DD/MM/YYYY``; ``""`` if it is not one."""

    try:
        value = date(year, month, day)
    except ValueError:
        return ""
    return f"{value.day:02d}/{value.month:02d}/{value.year:04d}"


def _numeric_date(first: int, second: int, year: int) -> str:
    """Resolve a D/M/YYYY vs M/D/YYYY pair, or refuse when it is ambiguous."""

    if first > 12 and second <= 12:
        return _build_date(year, second, first)
    if second > 12 and first <= 12:
        return _build_date(year, first, second)
    # Both plausible as a month: unknowable. Blank beats a coin flip.
    return ""


def normalize_date(raw: object) -> str:
    """Normalize a date to ``DD/MM/YYYY``; ``""`` when absent or ambiguous.

    The text may be a whole phrase ("effective as of the 15th day of January,
    2026" -> ``"15/01/2026"``). If it carries several different dates, a two-digit
    year, an impossible date, or a date that cannot be resolved without guessing,
    the result is ``""``.
    """

    text = collapse_whitespace(raw)
    if not text:
        return ""
    # "the 15th day of January, 2026" -> "15 January 2026"
    text = re.sub(r"(?i)\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text)
    text = re.sub(r"(?i)\bday\s+of\b", " ", text)
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text).strip()

    found: list[str] = []
    consumed: list[tuple[int, int]] = []

    def _overlaps(span: tuple[int, int]) -> bool:
        return any(span[0] < end and start < span[1] for start, end in consumed)

    for match in _DAY_MONTH_YEAR.finditer(text):
        consumed.append(match.span())
        found.append(
            _build_date(
                int(match.group(3)),
                _MONTHS[match.group(2).lower()],
                int(match.group(1)),
            )
        )
    for match in _MONTH_DAY_YEAR.finditer(text):
        if _overlaps(match.span()):
            continue
        consumed.append(match.span())
        found.append(
            _build_date(
                int(match.group(3)),
                _MONTHS[match.group(1).lower()],
                int(match.group(2)),
            )
        )
    for match in _YEAR_FIRST_DATE.finditer(text):
        if _overlaps(match.span()):
            continue
        consumed.append(match.span())
        found.append(
            _build_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        )
    for match in _NUMERIC_DATE.finditer(text):
        if _overlaps(match.span()):
            continue
        consumed.append(match.span())
        found.append(
            _numeric_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        )

    if not found or "" in found:
        # Nothing parseable, or something that looked like a date and was not.
        return ""
    if len(set(found)) != 1:
        return ""
    return found[0]


def _is_grouped(integer: str, group_sep: str) -> bool:
    """True when `integer` is a plain run of digits or correctly grouped thousands."""

    if group_sep not in integer:
        return bool(re.fullmatch(r"\d+", integer))
    head, *groups = integer.split(group_sep)
    return bool(re.fullmatch(r"\d{1,3}", head)) and all(
        re.fullmatch(r"\d{3}", group) for group in groups
    )


def _decimal_amount(raw: str) -> Decimal | None:
    """Parse a grouped amount into a `Decimal`, or ``None`` if it is ambiguous.

    Decimal throughout — a contract value must never round-trip through a binary
    float, where ``1.5 * 1_000_000`` is not the number anyone means.
    """

    text = raw.strip().rstrip(".,")
    if not text or not re.fullmatch(r"[\d.,]+", text):
        return None
    commas, dots = text.count(","), text.count(".")
    if commas and dots:
        # Both separators present: the rightmost is the decimal point, the other
        # groups thousands. "250,000.00" and "250.000,00" both resolve cleanly.
        decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
        group_sep = "." if decimal_sep == "," else ","
        integer, _, fraction = text.rpartition(decimal_sep)
        if not re.fullmatch(r"\d{1,2}", fraction) or not _is_grouped(
            integer, group_sep
        ):
            return None
        text = f"{integer.replace(group_sep, '')}.{fraction}"
    elif commas or dots:
        separator = "," if commas else "."
        head, *tail = text.split(separator)
        if all(re.fullmatch(r"\d{3}", part) for part in tail):
            if len(tail) == 1 and separator == "." and len(head) <= 3:
                # "1.500" is 1500 in one locale and 1.5 in another. Refuse.
                return None
            if not re.fullmatch(r"\d{1,3}", head):
                return None
            text = head + "".join(tail)
        elif (
            len(tail) == 1
            and re.fullmatch(r"\d{1,2}", tail[0])
            and re.fullmatch(r"\d+", head)
        ):
            text = f"{head}.{tail[0]}"
        else:
            return None
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", text):
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _currency_code(code: str | None, symbol: str | None) -> str:
    if code:
        upper = code.upper()
        return upper if upper in _CURRENCY_CODES else ""
    if symbol:
        return _CURRENCY_SYMBOLS.get(symbol.upper(), _CURRENCY_SYMBOLS.get(symbol, ""))
    return ""


def normalize_currency(raw: object) -> str:
    """Normalize a monetary amount to ``"<CURRENCY> <amount>"``.

    ``"$250,000.00"`` -> ``"USD 250000.00"``, and scale words are **expanded**:
    ``"$2 million"`` -> ``"USD 2000000.00"``, ``"$250k"`` -> ``"USD 250000.00"``,
    ``"EUR 3.2m"`` -> ``"EUR 3200000.00"``.

    Blank when the value cannot be stated exactly: a bare number with no currency,
    an unrecognized scale word, an ambiguously grouped amount, or two conflicting
    amounts in the same text. The warning names the raw text instead.
    """

    text = collapse_whitespace(raw)
    if not text:
        return ""
    found: list[str] = []
    consumed: list[tuple[int, int]] = []
    for pattern in (_CURRENCY_BEFORE, _CURRENCY_AFTER):
        for match in pattern.finditer(text):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in consumed):
                continue
            consumed.append(span)
            code = _currency_code(match.group("code"), match.group("symbol"))
            amount = _decimal_amount(match.group("amount"))
            if not code or amount is None:
                return ""
            scale_token = match.group("scale")
            if scale_token is not None:
                scale = _SCALES.get(scale_token.lower())
                if scale is None:
                    # A magnitude we do not support. Never drop it silently.
                    return ""
                amount *= scale
            quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            found.append(f"{code} {quantized}")
    if not found or len(set(found)) != 1:
        return ""
    return found[0]


def _organization_name(candidate: object) -> str:
    """One organisation name, cleaned: whitespace collapsed, separators trimmed.

    Never split, never merged, never rewritten, and no parenthetical dropped —
    "(Colombia)" may be part of the legal name, and rewriting the text would stop
    the value being a substring of its source element when it is grounded. ``""``
    only for something with no letters in it, which is never an organisation name.
    """

    name = collapse_whitespace(candidate).strip(" ,;")
    return name if re.search(r"[^\W\d_]", name) else ""


def normalize_organization_name(raw: object) -> str:
    """Normalize the counterparty's name — exactly one organisation.

    Accepts a string. A list is accepted only as a courtesy for a provider that
    returns one anyway: a single entry is used, and anything longer is ``""``
    rather than a guess about which of them is the customer. Choosing *which*
    organisation is the counterparty is the extractor's job — it is the side that
    is not one of ``settings.CONTRACT_HOME_ORGANIZATIONS`` — and it is deliberately
    not re-litigated here, so this stays a total, context-free function.

    ``"Acme Corp, a Delaware corporation"`` and ``'Acme Corp ("Vendor")'`` come
    back unchanged.
    """

    if isinstance(raw, list | tuple):
        # A malformed list is refused outright rather than filtered: a non-string
        # entry means the caller does not know what it is holding, and salvaging the
        # readable half of it would be a guess.
        if any(not isinstance(item, str) for item in raw):
            return ""
        names = [item for item in raw if _organization_name(item)]
        if len(names) != 1:
            return ""
        return _organization_name(names[0])
    if isinstance(raw, str):
        return _organization_name(raw)
    return ""


def normalize_field_value(field_key: str, raw: object) -> str:
    """Normalize ``raw`` the way ``field_key``'s catalogue entry says to.

    Total: an unknown key, or anything the field's normalizer refuses, is ``""``.
    """

    definition = FIELD_BY_KEY.get(field_key)
    if definition is None:
        return ""
    if definition.value_format is ValueFormat.DATE_DDMMYYYY:
        return normalize_date(raw)
    if definition.value_format is ValueFormat.CURRENCY_AMOUNT:
        return normalize_currency(raw)
    if definition.value_format is ValueFormat.ORGANIZATION_NAME:
        return normalize_organization_name(raw)
    return normalize_verbatim(raw)
