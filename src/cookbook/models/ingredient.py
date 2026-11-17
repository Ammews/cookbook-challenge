"""One ingredient line of a recipe."""

from pydantic import Field

from cookbook.models.base import DomainModel, NonEmptyStr, Slug
from cookbook.models.quantity import Quantity
from cookbook.models.source import Source


class Ingredient(DomainModel):
    id: Slug = Field(description='Stable id that steps refer to, e.g. "onion".')
    name: NonEmptyStr = Field(description='Normalised English name, e.g. "onion".')
    name_original: NonEmptyStr = Field(description='Name as written, e.g. "Zwiebeln".')
    quantity: Quantity
    preparation: str | None = Field(
        default=None, description='Preparation note, e.g. "in Scheiben geschnitten".'
    )
    optional: bool = False
    is_intermediate: bool = Field(
        default=False,
        description=(
            "True for something the recipe itself produces and reuses "
            "(e.g. the vinegar-water marinade), not something you buy."
        ),
    )
    source: Source
