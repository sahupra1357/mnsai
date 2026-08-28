"""Normalizers: valid input normalizes, ambiguous and garbage input goes blank.

Every normalizer is a total function — the tests below feed it `None`, ints, empty
strings, and nonsense, and none of them may raise.
"""

import pytest

from app.contract_fields.normalize import (
    normalize_currency,
    normalize_date,
    normalize_field_value,
    normalize_organization_name,
    normalize_verbatim,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("15/01/2026", "15/01/2026"),
        ("2026-01-15", "15/01/2026"),
        ("2026/01/15", "15/01/2026"),
        ("January 15, 2026", "15/01/2026"),
        ("Jan 15 2026", "15/01/2026"),
        ("15 January 2026", "15/01/2026"),
        ("the 15th day of January, 2026", "15/01/2026"),
        ("Effective as of the 1st day of March, 2026", "01/03/2026"),
        ("03/15/2026", "15/03/2026"),
        ("31.12.2026", "31/12/2026"),
    ],
)
def test_normalize_date_valid(raw: str, expected: str) -> None:
    assert normalize_date(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "01/02/2026",  # 1 February or 2 January? unknowable
        "05-06-2026",
        "15/01/26",  # two-digit year
        "from January 1, 2026 to March 1, 2026",  # two different dates
        "2026-02-30",  # looks like a date, is not one
        "within thirty (30) days of the Effective Date",
    ],
)
def test_normalize_date_ambiguous_is_blank(raw: str) -> None:
    assert normalize_date(raw) == ""


@pytest.mark.parametrize("raw", ["", "   ", "not a date", "TBD", None, 42, ["2026"]])
def test_normalize_date_garbage_is_blank(raw: object) -> None:
    assert normalize_date(raw) == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("USD 250000", "USD 250000.00"),
        ("USD 250,000.00", "USD 250000.00"),
        ("$250,000.00", "USD 250000.00"),
        ("$250000", "USD 250000.00"),
        ("250,000.00 USD", "USD 250000.00"),
        ("£1,500.50", "GBP 1500.50"),
        ("€1.234,56", "EUR 1234.56"),
        ("a total fee of USD 250,000.00 payable in arrears", "USD 250000.00"),
        ("USD 1,000,000", "USD 1000000.00"),
    ],
)
def test_normalize_currency_valid(raw: str, expected: str) -> None:
    assert normalize_currency(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$2 million", "USD 2000000.00"),
        ("$1.5 million", "USD 1500000.00"),
        ("$250k", "USD 250000.00"),
        ("EUR 3.2m", "EUR 3200000.00"),
        ("$2 billion", "USD 2000000000.00"),
        ("USD 2mm", "USD 2000000.00"),
        ("GBP 750 thousand", "GBP 750000.00"),
        ("2 million USD", "USD 2000000.00"),
        ("£1.25bn", "GBP 1250000000.00"),
    ],
)
def test_normalize_currency_expands_scale_words(raw: str, expected: str) -> None:
    # Silently dropping the scale — "$2 billion" -> "USD 2.00" — is the defect.
    assert normalize_currency(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "USD 1.500",  # 1500 or 1.5, depending on locale
        "USD 1.2345",  # not a representable amount
        "USD 100.00 in year one and USD 200.00 in year two",  # conflicting totals
        "250,000.00",  # no currency: cannot produce "<CURRENCY> <amount>"
        "250000",
        "XYZ 250,000",  # unknown currency code
        "USD 2 trillion",  # a magnitude we do not support: never dropped silently
        "INR 5 crore",
    ],
)
def test_normalize_currency_ambiguous_is_blank(raw: str) -> None:
    assert normalize_currency(raw) == ""


@pytest.mark.parametrize("raw", ["", "  ", "to be agreed", "N/A", None, 42, {}])
def test_normalize_currency_garbage_is_blank(raw: object) -> None:
    assert normalize_currency(raw) == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The normalizer NEVER splits or rewrites a legal name. Which organisation
        # is the customer is the extractor's decision — it is the party that is not
        # one of `settings.CONTRACT_HOME_ORGANIZATIONS`.
        ("Smith and Wesson", "Smith and Wesson"),
        ("Johnson and Johnson", "Johnson and Johnson"),
        ("Acme Corp, a Delaware corporation", "Acme Corp, a Delaware corporation"),
        ("Acme Corp and Northwind Ltd", "Acme Corp and Northwind Ltd"),
        ("Ben & Jerry's Homemade, Inc.", "Ben & Jerry's Homemade, Inc."),
        ("Northwind Ltd", "Northwind Ltd"),
        ("  Northwind   Ltd  ", "Northwind Ltd"),
        # A single-entry list is accepted as a courtesy to providers that wrap it.
        (["Northwind Ltd"], "Northwind Ltd"),
        (("Northwind Ltd",), "Northwind Ltd"),
    ],
)
def test_normalize_organization_name_never_splits_or_merges(
    raw: object, expected: str
) -> None:
    assert normalize_organization_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        ["Acme Corp", "Northwind Ltd"],
        ["Smith and Wesson", "Acme LLC"],
        ("Acme Corp", "Northwind Ltd", "Globex"),
    ],
)
def test_more_than_one_organisation_is_blank_not_a_guess(raw: object) -> None:
    """The field holds one counterparty. Several means the extractor did not resolve
    it, and picking one here would be a guess — blank raises it for a human."""

    assert normalize_organization_name(raw) == ""


def test_normalize_organization_name_keeps_every_parenthetical() -> None:
    # A parenthetical may be a defined term or may be part of the legal name; the
    # normalizer does not get to decide, and rewriting would break grounding.
    assert normalize_organization_name('Acme Corp ("Vendor")') == 'Acme Corp ("Vendor")'
    assert normalize_organization_name("Grupo Éxito, S.A. (Colombia)") == (
        "Grupo Éxito, S.A. (Colombia)"
    )
    assert normalize_organization_name(["Northwind Ltd (UK)"]) == "Northwind Ltd (UK)"


@pytest.mark.parametrize(
    "raw", ["", "   ", "123 456", ", ; ,", None, 42, ["Acme", 7], []]
)
def test_normalize_organization_name_garbage_is_blank(raw: object) -> None:
    assert normalize_organization_name(raw) == ""


def test_normalize_verbatim_trims_and_collapses() -> None:
    assert normalize_verbatim("  Master   Services\nAgreement  ") == (
        "Master Services Agreement"
    )
    assert normalize_verbatim("Net 30") == "Net 30"


@pytest.mark.parametrize("raw", ["", "   ", None, 42, ["Net 30"]])
def test_normalize_verbatim_garbage_is_blank(raw: object) -> None:
    assert normalize_verbatim(raw) == ""


def test_normalize_field_value_dispatches_on_the_catalogue_format() -> None:
    assert normalize_field_value("effective_date", "January 15, 2026") == "15/01/2026"
    assert normalize_field_value("contract_value", "$2 million") == "USD 2000000.00"
    assert normalize_field_value("customer", ["Northwind Ltd"]) == "Northwind Ltd"
    # Two organisations is unresolved, not a joined value.
    assert normalize_field_value("customer", ["Acme Corp", "Northwind Ltd"]) == ""
    assert normalize_field_value("governing_law", " State of  Delaware ") == (
        "State of Delaware"
    )


@pytest.mark.parametrize(
    ("field_key", "raw"),
    [
        ("effective_date", "01/02/2026"),
        ("term_end_date", "three years from the Effective Date"),
        ("contract_value", "an amount to be agreed"),
        ("not_a_field", "anything"),
        ("contract_title", None),
    ],
)
def test_normalize_field_value_is_blank_when_it_cannot_be_certain(
    field_key: str, raw: object
) -> None:
    assert normalize_field_value(field_key, raw) == ""
