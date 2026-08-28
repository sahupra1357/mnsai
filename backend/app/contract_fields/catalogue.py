"""The contract field catalogue — the single source of truth for the schema.

Exactly ten fields, **all of them selectable**. Five are selected by default
(``default_selected``) and five are not; the operator moves any of the ten in or out
of the requested set, from one field up to all ten. There is no undeselectable field —
what the operator leaves out is simply not extracted and comes back ``""``.
At least one field must be selected: an empty selection has nothing to extract.
Nothing else may define the schema — ``GET /fields``, the ten-key JSON contract, and
the ten table columns all derive from ``FIELD_CATALOGUE`` below, and the frontend
never keeps a second copy.

The ``description`` on each entry is the prompt-facing definition of the field, so
this is the file to tune when extraction quality needs work.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict


class ValueFormat(str, Enum):
    """How a field's value is normalized before it reaches the JSON and the table."""

    VERBATIM = "verbatim"
    ORGANIZATION_NAME = "organization_name"
    DATE_DDMMYYYY = "date_ddmmyyyy"
    CURRENCY_AMOUNT = "currency_amount"


class FieldDefinition(BaseModel):
    """One catalogue entry. Frozen — the schema is fixed at import time."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    description: str
    value_format: ValueFormat
    #: Whether this field starts in the operator's selection. A default is a starting
    #: point, never a lock — every field can be moved out of the selection.
    default_selected: bool


# The canonical order: the five default-selected fields, then the five that start
# unselected. This tuple fixes the order of the JSON keys, the table columns, and the
# UI list. Order is presentation only — it confers no privilege on the first five.
FIELD_CATALOGUE: tuple[FieldDefinition, ...] = (
    FieldDefinition(
        key="contract_title",
        label="Contract title",
        description=(
            "The title of the agreement exactly as written on the document, for "
            "example 'Master Services Agreement' or 'Mutual Non-Disclosure "
            "Agreement'. Usually the heading on the first page. Do not invent a "
            "title from the parties or the subject matter."
        ),
        value_format=ValueFormat.VERBATIM,
        default_selected=True,
    ),
    FieldDefinition(
        key="customer",
        label="Customer",
        description=(
            "The counterparty: the organisation this agreement is with, named as "
            "the document names it. Exactly one entity — the party that is **not** "
            "the organisation running this system, whose own names are configured "
            "in CONTRACT_HOME_ORGANIZATIONS and are never the answer. Exclude "
            "signatories, witnesses, notaries, and addresses. Do not include the "
            "recital preamble ('This Agreement is made by and between …'); start "
            "at the entity's own name, and return it exactly as written — the "
            "normalizer only collapses whitespace, it never rewrites a legal name."
        ),
        value_format=ValueFormat.ORGANIZATION_NAME,
        default_selected=True,
    ),
    FieldDefinition(
        key="effective_date",
        label="Effective date",
        description=(
            "The date the contract takes effect — the 'effective date', "
            "'commencement date', or the date stated in the opening paragraph. Not "
            "the signature date unless the document says they are the same."
        ),
        value_format=ValueFormat.DATE_DDMMYYYY,
        default_selected=True,
    ),
    FieldDefinition(
        key="term_end_date",
        label="Term end date",
        description=(
            "The date the term expires or the agreement ends — the 'expiration "
            "date', 'termination date', or end of the initial term. A relative term "
            "such as 'three years from the effective date' is not a date; leave it "
            "blank unless the document states the end date itself."
        ),
        value_format=ValueFormat.DATE_DDMMYYYY,
        default_selected=True,
    ),
    FieldDefinition(
        key="contract_value",
        label="Contract value",
        description=(
            "The total consideration payable under the contract, with its currency "
            "— a total contract value, fee, or aggregate amount. Do not sum line "
            "items yourself and do not use a rate, cap, or deposit as the total. "
            "Quote the amount and its currency as written, scale word included "
            "('USD 2 million'); the scale is expanded during normalization."
        ),
        value_format=ValueFormat.CURRENCY_AMOUNT,
        default_selected=True,
    ),
    FieldDefinition(
        key="governing_law",
        label="Governing law",
        description=(
            "The jurisdiction whose law governs the agreement, as stated in the "
            "governing-law or choice-of-law clause, for example 'State of Delaware' "
            "or 'England and Wales'."
        ),
        value_format=ValueFormat.VERBATIM,
        default_selected=False,
    ),
    FieldDefinition(
        key="payment_terms",
        label="Payment terms",
        description=(
            "The payment schedule or terms — for example 'Net 30 days from invoice "
            "date' or 'monthly in advance'. Quote the operative terms, not the whole "
            "payment article."
        ),
        value_format=ValueFormat.VERBATIM,
        default_selected=False,
    ),
    FieldDefinition(
        key="notice_period",
        label="Notice period",
        description=(
            "The notice a party must give to terminate or not renew, for example "
            "'90 days written notice'. The period itself, not the notice address."
        ),
        value_format=ValueFormat.VERBATIM,
        default_selected=False,
    ),
    FieldDefinition(
        key="renewal_terms",
        label="Renewal terms",
        description=(
            "How the agreement renews — automatic renewal, renewal term length, and "
            "any condition on renewing, for example 'automatically renews for "
            "successive one-year terms'."
        ),
        value_format=ValueFormat.VERBATIM,
        default_selected=False,
    ),
    FieldDefinition(
        key="termination_clause",
        label="Termination clause",
        description=(
            "The grounds and mechanics of termination — termination for convenience "
            "or for cause, cure periods, and what each party must do to terminate."
        ),
        value_format=ValueFormat.VERBATIM,
        default_selected=False,
    ),
)

#: Every catalogue key, in the canonical order. The JSON contract's key set.
CANONICAL_FIELD_KEYS: tuple[str, ...] = tuple(
    definition.key for definition in FIELD_CATALOGUE
)

#: The five fields the UI starts with in the selected list. A default only — each of
#: them can be moved out, and a selection that omits every one of them is valid.
DEFAULT_FIELD_KEYS: tuple[str, ...] = tuple(
    definition.key for definition in FIELD_CATALOGUE if definition.default_selected
)

#: The five fields the UI starts with unselected. Nothing else distinguishes them.
NON_DEFAULT_FIELD_KEYS: tuple[str, ...] = tuple(
    definition.key for definition in FIELD_CATALOGUE if not definition.default_selected
)

#: The JSON contract always carries this many keys, whatever the operator selected.
FIELD_COUNT: int = len(CANONICAL_FIELD_KEYS)

FIELD_BY_KEY: Mapping[str, FieldDefinition] = MappingProxyType(
    {definition.key: definition for definition in FIELD_CATALOGUE}
)


def _verify_catalogue() -> None:
    """Fail loudly at import time if the schema ever drifts from 5 + 5 = 10."""

    if len(set(CANONICAL_FIELD_KEYS)) != len(CANONICAL_FIELD_KEYS):
        raise RuntimeError("contract field catalogue contains duplicate keys")
    if len(CANONICAL_FIELD_KEYS) != 10:
        raise RuntimeError("contract field catalogue must define exactly 10 fields")
    if len(DEFAULT_FIELD_KEYS) != 5 or len(NON_DEFAULT_FIELD_KEYS) != 5:
        raise RuntimeError("contract field catalogue must be 5 default + 5 non-default")
    if CANONICAL_FIELD_KEYS != DEFAULT_FIELD_KEYS + NON_DEFAULT_FIELD_KEYS:
        raise RuntimeError(
            "default-selected fields must precede the rest in the catalogue"
        )


_verify_catalogue()


def is_catalogue_field(key: str) -> bool:
    return key in CANONICAL_FIELD_KEYS


def is_default_field(key: str) -> bool:
    return key in DEFAULT_FIELD_KEYS


def requested_field_keys(
    selected_fields: Iterable[str] | None = None,
) -> tuple[str, ...]:
    """The keys the operator actually asked for — exactly what they selected.

    Returned in canonical order. Unknown or duplicated entries are ignored here —
    rejecting them is the request model's job (``FieldSelection``), and this helper
    stays total so the failure rule can never blow up on bad input.

    A blank in one of these keys is a **failure**; a blank in any other key is the
    expected outcome of not being asked for. Nothing is added implicitly: a selection
    of one field means a failure scope of exactly one field.
    """

    selected = set(selected_fields or ())
    return tuple(key for key in CANONICAL_FIELD_KEYS if key in selected)


def assemble_fields(
    values: Mapping[str, object] | None = None,
    *,
    requested_keys: Iterable[str] | None = None,
) -> dict[str, str]:
    """Build the ten-key JSON payload.

    Always returns **the same ten keys in the same order**, whatever was passed in:
    keys absent from ``values`` — and keys carrying anything that is not a string —
    come back as ``""``. Never ``None``, never a missing key, never an extra key.

    When ``requested_keys`` is given, any key outside it is forced to ``""`` so a
    value proposed for a field the operator never selected can never leak into the
    payload. Omit it to assemble whatever was supplied.
    """

    allowed = None if requested_keys is None else set(requested_keys)
    source: Mapping[str, object] = values or {}
    assembled: dict[str, str] = {}
    for key in CANONICAL_FIELD_KEYS:
        if allowed is not None and key not in allowed:
            assembled[key] = ""
            continue
        value = source.get(key, "")
        # Blank means blank at the contract boundary too: a whitespace-only value is
        # not a value, and must never satisfy a requested field or reach the
        # NOT NULL DEFAULT '' column as spaces.
        assembled[key] = value if isinstance(value, str) and value.strip() else ""
    return assembled
