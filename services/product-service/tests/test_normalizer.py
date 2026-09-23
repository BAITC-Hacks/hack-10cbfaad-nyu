import pytest

from app.normalizer import (
    normalize_product,
    parse_breaking_capacity,
    parse_current,
    parse_poles,
    parse_voltage,
)


@pytest.mark.parametrize("raw", ["160А", "160 A", "160 а"])
def test_current_variants(raw):
    assert parse_current(raw) == 160


@pytest.mark.parametrize("raw", ["18кА", "18 kA", "18ka"])
def test_breaking_capacity_variants(raw):
    assert parse_breaking_capacity(raw) == 18


@pytest.mark.parametrize("raw", ["400В", "400 V", "400VAC"])
def test_voltage_variants(raw):
    assert parse_voltage(raw) == 400


@pytest.mark.parametrize("raw", ["3P", "3 полюса", "3ф"])
def test_poles_variants(raw):
    assert parse_poles(raw) == 3


def test_unknown_measure_is_none():
    assert parse_current("регулируемый") is None
    assert parse_voltage("до уточнения") is None


def test_fixture_conflict_is_explicit_and_raw_data_is_preserved(fixture_product):
    product = normalize_product(fixture_product)

    assert product["nominal_current_a"] is None
    assert product["breaking_capacity_ka"] == 18
    assert product["nominal_voltage_v"] == 400
    assert product["poles"] == 3
    assert product["has_conflicts"] is True
    warning = product["warnings"][0]
    assert warning["code"] == "CONFLICTING_FIELD_VALUES"
    assert warning["field"] == "specs.nominal_current_a"
    assert {entry["source"] for entry in warning["values"]} == {
        "name",
        "description",
        "properties.NOMINALNYY_TOK",
    }
    assert product["properties_raw"]["NOMINALNYY_TOK"] == "250 А"
    assert product["raw_payload"] == fixture_product

