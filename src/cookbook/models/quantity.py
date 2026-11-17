"""How much of an ingredient, including the cases where the recipe never says."""

from enum import StrEnum

from pydantic import Field, model_validator

from cookbook.models.base import DomainModel


class QuantityKind(StrEnum):
    EXACT = "exact"        # "½ l", "4"
    VAGUE = "vague"        # "einige", "etwas"
    TO_TASTE = "to_taste"  # salt, pepper, "soviel Zucker, daß ..."
    ABSENT = "absent"      # ingredient named with no amount at all


class Quantity(DomainModel):
    """An amount as written, plus a number only when the text gives one.

    `value` is allowed only for EXACT quantities. This is a guard against
    hallucination: the schema leaves no room to attach an invented number
    to "some apples" or to an unquantified piece of meat.
    """

    kind: QuantityKind
    value: float | None = Field(default=None, gt=0)
    unit: str | None = Field(
        default=None, description='Unit as written, e.g. "l", "g". None for countable items.'
    )
    raw: str = Field(
        default="", description='Amount exactly as written, e.g. "½ l", "einige".'
    )

    @model_validator(mode="after")
    def _value_only_when_exact(self) -> "Quantity":
        if self.kind is QuantityKind.EXACT and self.value is None:
            raise ValueError("an 'exact' quantity needs a numeric value")
        if self.kind is not QuantityKind.EXACT and self.value is not None:
            raise ValueError(f"a '{self.kind.value}' quantity cannot have a numeric value")
        if self.kind is not QuantityKind.EXACT and self.unit is not None:
            raise ValueError(f"a '{self.kind.value}' quantity cannot have a unit")
        return self

    @property
    def is_numeric(self) -> bool:
        return self.value is not None
