"""The recipe aggregate and the invariants that span its parts."""

from collections import Counter
from collections.abc import Iterable

from pydantic import Field, model_validator

from cookbook.models.base import DomainModel, NonEmptyStr
from cookbook.models.ingredient import Ingredient
from cookbook.models.source import Source, SourceStatus
from cookbook.models.step import Step
from cookbook.models.tool import Tool


class Servings(DomainModel):
    value: int | None = Field(default=None, ge=1)
    source: Source

    @model_validator(mode="after")
    def _missing_has_no_value(self) -> "Servings":
        if self.source.status is SourceStatus.MISSING and self.value is not None:
            raise ValueError("servings marked 'missing' cannot have a value")
        if self.source.status is not SourceStatus.MISSING and self.value is None:
            raise ValueError("servings need a value unless marked 'missing'")
        return self

    @property
    def inferred(self) -> bool:
        return self.source.status is SourceStatus.INFERRED


class ReviewWarning(DomainModel):
    """Something a human reviewer should look at before trusting the recipe."""

    message: NonEmptyStr
    target_id: str | None = Field(
        default=None, description="Id of the ingredient or tool concerned, if any."
    )


class Recipe(DomainModel):
    title: NonEmptyStr
    language: NonEmptyStr = Field(description='Language of the source, e.g. "de".')
    servings: Servings
    ingredients: tuple[Ingredient, ...]
    tools: tuple[Tool, ...] = ()
    steps: tuple[Step, ...]
    warnings: tuple[ReviewWarning, ...] = ()

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "Recipe":
        _require_unique((i.id for i in self.ingredients), "ingredient id")
        _require_unique((t.id for t in self.tools), "tool id")
        return self

    @model_validator(mode="after")
    def _steps_are_sequential(self) -> "Recipe":
        orders = [s.order for s in self.steps]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(f"step orders must be 1..{len(orders)} in sequence, got {orders}")
        return self

    @model_validator(mode="after")
    def _steps_reference_known_items(self) -> "Recipe":
        ingredient_ids = {i.id for i in self.ingredients}
        tool_ids = {t.id for t in self.tools}
        for step in self.steps:
            _require_known(step.ingredient_ids, ingredient_ids, f"step {step.order} ingredient")
            _require_known(step.tool_ids, tool_ids, f"step {step.order} tool")
        return self


def _require_unique(ids: Iterable[str], label: str) -> None:
    duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
    if duplicates:
        raise ValueError(f"duplicate {label}: {duplicates}")


def _require_known(ids: Iterable[str], known: set[str], label: str) -> None:
    unknown = sorted(set(ids) - known)
    if unknown:
        raise ValueError(f"{label} refers to unknown id: {unknown}")
