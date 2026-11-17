"""The contract every manipulation follows, and how several are combined.

A rule is a pure function from a recipe to a new recipe plus the list of
changes it made. Rules never edit the recipe they receive (models are
frozen), never call a model, and never read the clock, so the same input
always gives the same output.
"""

from collections.abc import Sequence
from typing import Protocol

from cookbook.models import Change, Recipe
from cookbook.models.base import DomainModel


class ManipulationError(ValueError):
    """A rule cannot be applied to this recipe, for a reason the user can fix."""


class Rule(Protocol):
    name: str

    def apply(self, recipe: Recipe) -> tuple[Recipe, list[Change]]: ...


class ManipulationResult(DomainModel):
    original: Recipe
    recipe: Recipe
    changes: tuple[Change, ...]


def apply_rules(recipe: Recipe, rules: Sequence[Rule]) -> ManipulationResult:
    current, changes = recipe, []
    for rule in rules:
        current, made = rule.apply(current)
        changes.extend(made)
    return ManipulationResult(original=recipe, recipe=current, changes=tuple(changes))
