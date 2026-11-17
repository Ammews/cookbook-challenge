"""One ingredient line of a recipe."""

from enum import StrEnum

from pydantic import Field

from cookbook.models.base import DomainModel, NonEmptyStr, Slug
from cookbook.models.quantity import Quantity
from cookbook.models.source import Source


class AnimalContent(StrEnum):
    """What, if anything, of animal origin the ingredient contains.

    The question is what it contains, not where it comes from: pesto is
    made from plants but contains cheese; salt is neither plant nor animal.
    """

    NONE = "none"
    MEAT = "meat"
    POULTRY = "poultry"
    FISH = "fish"
    DAIRY = "dairy"
    EGG = "egg"
    HONEY = "honey"
    GELATIN = "gelatin"
    OTHER_ANIMAL = "other_animal"
    UNCERTAIN = "uncertain"

    @property
    def is_animal(self) -> bool:
        return self not in (AnimalContent.NONE, AnimalContent.UNCERTAIN)


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
    animal: AnimalContent | None = Field(
        default=None,
        description="Animal content as classified by the model; None if not classified.",
    )
    source: Source
