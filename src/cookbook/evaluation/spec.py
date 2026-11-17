"""The shape of an evaluation case: what a correct extraction must satisfy.

A case does not hold a full "correct recipe". It holds a list of checks a
human can review one by one ("onion: exactly one ingredient, quantity 4";
"lemon juice must not appear: it is only in the notes"). That is faster to
review than a full JSON answer, and it tolerates harmless differences in
wording that a whole-object comparison would flag.
"""

from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from cookbook.models import QuantityKind, SourceStatus
from cookbook.models.base import DomainModel, NonEmptyStr

Matcher = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, to_lower=True)]


class AcceptedQuantity(DomainModel):
    """One acceptable reading of an amount, e.g. 225 g or 2 sticks of the same butter."""

    value: float = Field(gt=0)
    unit: str | list[str] | None = Field(
        default=None,
        description="Accepted spellings of the unit. None means the unit is not checked.",
    )


class QuantityCheck(DomainModel):
    kind_any: list[QuantityKind] = Field(
        default_factory=list, description="Accepted kinds. Empty means the kind is not checked."
    )
    accept: list[AcceptedQuantity] = Field(
        default_factory=list,
        description="Accepted value and unit pairs. Empty means the value is not checked.",
    )


class IngredientCheck(DomainModel):
    match: list[Matcher] = Field(
        min_length=1,
        description="An ingredient matches if its name or original name contains any of these.",
    )
    exclude: list[Matcher] = Field(
        default_factory=list,
        description='Names containing any of these do not match, e.g. "wasser" for "Essig".',
    )
    min_count: int = Field(default=1, ge=0)
    max_count: int = Field(
        default=1, ge=0, description="1 means the ingredient must not be duplicated."
    )
    quantity: QuantityCheck | None = None
    optional: bool | None = None
    intermediate: bool | None = None
    note: str | None = Field(default=None, description="Why this check exists, for the reviewer.")

    @model_validator(mode="after")
    def _count_range_is_ordered(self) -> "IngredientCheck":
        if self.min_count > self.max_count:
            raise ValueError("min_count cannot be greater than max_count")
        return self


class ToolCheck(DomainModel):
    match: list[Matcher] = Field(min_length=1)
    stated: bool | None = Field(
        default=None, description="True if the text names it, False if it is only implied."
    )


class ServingsCheck(DomainModel):
    status_any: list[SourceStatus] = Field(min_length=1)
    value: int | None = Field(default=None, description="Exact value required, if any.")
    min_value: int | None = Field(default=None, description="For inferred servings: plausible range.")
    max_value: int | None = None


class CountRange(DomainModel):
    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)


class Expectations(DomainModel):
    is_recipe: bool = True
    multiple_recipes: bool = Field(
        default=False,
        description="True if the document holds more than one recipe and the pipeline must say so.",
    )
    min_warnings: int = Field(
        default=0, ge=0, description="Hard inputs should produce at least this many review warnings."
    )
    servings: ServingsCheck | None = None
    ingredients: list[IngredientCheck] = Field(default_factory=list)
    absent_ingredients: list[Matcher] = Field(
        default_factory=list,
        description="Must not appear in any ingredient name: things only in notes, variations or drawings.",
    )
    ingredient_count: CountRange | None = None
    tools: list[ToolCheck] = Field(default_factory=list)
    step_count: CountRange | None = None


class CaseSpec(DomainModel):
    id: NonEmptyStr
    title: NonEmptyStr
    language: NonEmptyStr
    input: NonEmptyStr = Field(description="Input file, relative to the case folder.")
    input_in_repo: bool = Field(
        default=True, description="False for documents that may not be published (kept local)."
    )
    reference_transcription: str | None = Field(
        default=None, description="Human transcription of an image input, to measure reading errors."
    )
    source: NonEmptyStr
    license: NonEmptyStr
    reviewed: bool = Field(
        default=False,
        description="True once a human has checked every expectation against the source.",
    )
    traps: list[NonEmptyStr] = Field(default_factory=list)
    expect: Expectations
