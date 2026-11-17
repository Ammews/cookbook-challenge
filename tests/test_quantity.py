import pytest
from pydantic import ValidationError

from cookbook.models import Quantity, QuantityKind


def test_exact_quantity_keeps_value_unit_and_raw_text():
    quantity = Quantity(kind=QuantityKind.EXACT, value=0.5, unit="l", raw="½ l")
    assert (quantity.value, quantity.unit, quantity.raw) == (0.5, "l", "½ l")
    assert quantity.is_numeric


def test_exact_quantity_needs_a_number():
    with pytest.raises(ValidationError, match="needs a numeric value"):
        Quantity(kind=QuantityKind.EXACT, raw="½ l")


@pytest.mark.parametrize(
    "kind", [QuantityKind.VAGUE, QuantityKind.TO_TASTE, QuantityKind.ABSENT]
)
def test_non_exact_quantity_cannot_carry_an_invented_number(kind):
    with pytest.raises(ValidationError, match="cannot have a numeric value"):
        Quantity(kind=kind, value=3, raw="einige")


def test_non_exact_quantity_cannot_carry_a_unit():
    with pytest.raises(ValidationError, match="cannot have a unit"):
        Quantity(kind=QuantityKind.VAGUE, unit="g", raw="etwas")


def test_absent_quantity_is_valid_with_no_text_at_all():
    quantity = Quantity(kind=QuantityKind.ABSENT)
    assert not quantity.is_numeric and quantity.raw == ""


def test_value_must_be_positive():
    with pytest.raises(ValidationError):
        Quantity(kind=QuantityKind.EXACT, value=0, raw="0")
