"""Schema integrity and the ten-key assembler."""

from app.contract_fields.catalogue import (
    CANONICAL_FIELD_KEYS,
    DEFAULT_FIELD_KEYS,
    FIELD_BY_KEY,
    FIELD_CATALOGUE,
    FIELD_COUNT,
    NON_DEFAULT_FIELD_KEYS,
    ValueFormat,
    assemble_fields,
    requested_field_keys,
)

EXPECTED_KEYS = (
    "contract_title",
    "customer",
    "effective_date",
    "term_end_date",
    "contract_value",
    "governing_law",
    "payment_terms",
    "notice_period",
    "renewal_terms",
    "termination_clause",
)


def test_catalogue_defines_exactly_ten_unique_fields() -> None:
    assert len(FIELD_CATALOGUE) == 10
    assert FIELD_COUNT == 10
    assert len(set(CANONICAL_FIELD_KEYS)) == 10
    assert CANONICAL_FIELD_KEYS == EXPECTED_KEYS


def test_catalogue_splits_five_fixed_and_five_optional() -> None:
    assert len(DEFAULT_FIELD_KEYS) == 5
    assert len(NON_DEFAULT_FIELD_KEYS) == 5
    assert not set(DEFAULT_FIELD_KEYS) & set(NON_DEFAULT_FIELD_KEYS)
    # Fixed first, then optional — the order the JSON, the table, and the UI use.
    assert CANONICAL_FIELD_KEYS == DEFAULT_FIELD_KEYS + NON_DEFAULT_FIELD_KEYS


def test_every_definition_carries_the_full_contract() -> None:
    for definition in FIELD_CATALOGUE:
        assert definition.key
        assert definition.label
        assert len(definition.description) > 20
        assert isinstance(definition.value_format, ValueFormat)
        assert isinstance(definition.default_selected, bool)
        assert FIELD_BY_KEY[definition.key] is definition
    assert [d.key for d in FIELD_CATALOGUE if d.default_selected] == list(
        DEFAULT_FIELD_KEYS
    )


def test_requested_keys_are_exactly_the_selection() -> None:
    """Nothing is requested implicitly: the scope is the selection, no more."""

    assert requested_field_keys() == ()
    assert requested_field_keys([]) == ()
    assert requested_field_keys(DEFAULT_FIELD_KEYS) == DEFAULT_FIELD_KEYS
    assert requested_field_keys(NON_DEFAULT_FIELD_KEYS) == NON_DEFAULT_FIELD_KEYS
    assert requested_field_keys(CANONICAL_FIELD_KEYS) == CANONICAL_FIELD_KEYS
    # A single field is a complete, valid scope.
    assert requested_field_keys(["governing_law"]) == ("governing_law",)
    # Always canonical order, whatever order the caller passed.
    assert requested_field_keys(["payment_terms", "governing_law"]) == (
        "governing_law",
        "payment_terms",
    )
    # Total function: junk in the selection is ignored, never raised.
    assert requested_field_keys(["nope", "contract_title"]) == ("contract_title",)


def test_assembler_returns_the_same_ten_keys_for_a_single_field_selection() -> None:
    """One field selected still yields all ten keys — nine of them blank."""

    assembled = assemble_fields(
        {"contract_title": "Master Services Agreement"},
        requested_keys=requested_field_keys(["contract_title"]),
    )

    assert tuple(assembled) == CANONICAL_FIELD_KEYS
    assert assembled["contract_title"] == "Master Services Agreement"
    assert all(
        assembled[key] == "" for key in CANONICAL_FIELD_KEYS if key != "contract_title"
    )


def test_assembler_returns_the_same_ten_keys_for_a_partial_selection() -> None:
    selected = ["governing_law", "payment_terms"]
    assembled = assemble_fields(
        {
            "contract_title": "Master Services Agreement",
            "customer": "Northwind Ltd",
            "governing_law": "State of Delaware",
            "payment_terms": "Net 30",
        },
        requested_keys=requested_field_keys(selected),
    )

    assert tuple(assembled) == CANONICAL_FIELD_KEYS
    assert assembled["governing_law"] == "State of Delaware"
    assert assembled["payment_terms"] == "Net 30"
    # Extracted but not found, and never requested, look the same in the payload.
    assert assembled["term_end_date"] == ""
    assert assembled["notice_period"] == ""


def test_assembler_returns_the_same_ten_keys_when_all_ten_selected() -> None:
    assembled = assemble_fields(
        dict.fromkeys(CANONICAL_FIELD_KEYS, "value"),
        requested_keys=requested_field_keys(CANONICAL_FIELD_KEYS),
    )

    assert tuple(assembled) == CANONICAL_FIELD_KEYS
    assert all(value == "value" for value in assembled.values())


def test_assembler_key_set_never_varies_with_the_selection() -> None:
    selections = [
        ["governing_law"],
        list(DEFAULT_FIELD_KEYS),
        ["notice_period", "renewal_terms", "termination_clause"],
        list(NON_DEFAULT_FIELD_KEYS),
        list(CANONICAL_FIELD_KEYS),
    ]
    payloads = [
        assemble_fields(
            dict.fromkeys(CANONICAL_FIELD_KEYS, "x"),
            requested_keys=requested_field_keys(selection),
        )
        for selection in selections
    ]

    assert all(tuple(payload) == CANONICAL_FIELD_KEYS for payload in payloads)
    assert all(len(payload) == 10 for payload in payloads)


def test_assembler_blanks_values_for_unselected_fields() -> None:
    """Including a formerly-fixed key: nothing is exempt from the selection now."""

    assembled = assemble_fields(
        {"termination_clause": "leaked value", "contract_title": "leaked title"},
        requested_keys=requested_field_keys(["governing_law"]),
    )

    assert assembled["termination_clause"] == ""
    assert assembled["contract_title"] == ""


def test_assembler_never_emits_null_or_a_non_string() -> None:
    assembled = assemble_fields(
        {
            "contract_title": None,
            "customer": 42,
            "effective_date": ["15/01/2026"],
            # Whitespace is not a value: it must not satisfy a requested field.
            "contract_value": "   ",
        },
        requested_keys=CANONICAL_FIELD_KEYS,
    )

    assert tuple(assembled) == CANONICAL_FIELD_KEYS
    assert all(isinstance(value, str) for value in assembled.values())
    assert assembled["contract_title"] == ""
    assert assembled["customer"] == ""
    assert assembled["effective_date"] == ""
    assert assembled["contract_value"] == ""


def test_assembler_ignores_keys_outside_the_catalogue() -> None:
    assembled = assemble_fields(
        {"not_a_field": "x", "contract_title": "MSA"},
        requested_keys=CANONICAL_FIELD_KEYS,
    )

    assert tuple(assembled) == CANONICAL_FIELD_KEYS
    assert "not_a_field" not in assembled


def test_assembler_with_no_values_is_ten_blank_keys() -> None:
    assembled = assemble_fields()

    assert tuple(assembled) == CANONICAL_FIELD_KEYS
    assert all(value == "" for value in assembled.values())
