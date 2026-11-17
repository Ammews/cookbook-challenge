"""Make a recipe vegan with a substitution table, carried through to the steps.

The table lives in a data file (vegan_substitutions.yaml), so a cook or a
reviewer can read and extend it without touching code. Every substitution is
recorded as a change with its reason, and every step that used a replaced
ingredient gets a visible note, so nothing is swapped silently.
"""

import re
from functools import cache
from pathlib import Path

import yaml
from pydantic import Field

from cookbook.models import Change, Ingredient, Quantity, QuantityKind, Recipe, ReviewWarning, Source, SourceStatus, Step
from cookbook.models.base import DomainModel

_TABLE = Path(__file__).with_name("vegan_substitutions.yaml")


class Substitution(DomainModel):
    match: list[str]
    exclude: list[str] = Field(default_factory=list)
    replace_with: str
    reason: str
    step_note: str | None = None
    by_weight: bool = False


class Check(DomainModel):
    match: list[str]
    reason: str


class SubstitutionTable(DomainModel):
    already_vegan: list[str]
    substitutions: list[Substitution]
    checks: list[Check]


@cache
def default_table() -> SubstitutionTable:
    return SubstitutionTable.model_validate(yaml.safe_load(_TABLE.read_text(encoding="utf-8")))


class MakeVegan:
    name = "vegan"

    def __init__(self, table: SubstitutionTable | None = None) -> None:
        self.table = table or default_table()

    def apply(self, recipe: Recipe) -> tuple[Recipe, list[Change]]:
        changes: list[Change] = []
        replaced: dict[str, tuple[Ingredient, Ingredient, Substitution]] = {}
        taken_ids = {i.id for i in recipe.ingredients}
        ingredients = []

        for ingredient in recipe.ingredients:
            substitution = self._substitution_for(ingredient)
            if substitution is None:
                ingredients.append(ingredient)
                continue
            new = _replace(ingredient, substitution, taken_ids)
            taken_ids.add(new.id)
            replaced[ingredient.id] = (ingredient, new, substitution)
            ingredients.append(new)
            changes.append(
                Change(
                    rule=self.name,
                    target=ingredient.id,
                    before=ingredient.name_original,
                    after=new.name,
                    reason=substitution.reason,
                )
            )

        steps = []
        for step in recipe.steps:
            new_step, change = _carry_into_step(step, replaced)
            steps.append(new_step)
            if change:
                changes.append(change)

        warnings = list(recipe.warnings)
        existing = {w.message for w in warnings}
        for ingredient in ingredients:
            check = self._check_for(ingredient)
            if check is None:
                continue
            message = f"Vegan check, {ingredient.name_original}: {check.reason}"
            if message in existing:
                continue
            warnings.append(ReviewWarning(message=message, target_id=ingredient.id))
            existing.add(message)
            changes.append(
                Change(
                    rule=self.name,
                    target=ingredient.id,
                    before=ingredient.name_original,
                    after="unchanged, check the label",
                    reason=check.reason,
                )
            )

        updated = recipe.model_copy(
            update={"ingredients": tuple(ingredients), "steps": tuple(steps), "warnings": tuple(warnings)}
        )
        return updated, changes

    def _substitution_for(self, ingredient: Ingredient) -> Substitution | None:
        names = _names(ingredient)
        if _matches_any(names, self.table.already_vegan):
            return None
        for substitution in self.table.substitutions:
            if _matches_any(names, substitution.match) and not _matches_any(names, substitution.exclude):
                return substitution
        return None

    def _check_for(self, ingredient: Ingredient) -> Check | None:
        names = _names(ingredient)
        return next((c for c in self.table.checks if _matches_any(names, c.match)), None)


def _replace(ingredient: Ingredient, substitution: Substitution, taken_ids: set[str]) -> Ingredient:
    quantity = ingredient.quantity
    if substitution.by_weight and quantity.kind is QuantityKind.EXACT:
        # No number in the raw text, so the result is the same whether the
        # recipe was scaled before or after: the rules stay order-independent.
        quantity = Quantity(kind=QuantityKind.VAGUE, raw=f"same weight as the {ingredient.name} it replaces")
    return ingredient.model_copy(
        update={
            "quantity": quantity,
            "id": _free_id(f"vegan_{ingredient.id}", taken_ids),
            "name": substitution.replace_with,
            "name_original": substitution.replace_with,
            "preparation": None,  # "fest", "auslassen" described the meat, not the substitute
            "source": Source(
                status=SourceStatus.RULE,
                page=ingredient.source.page,
                quote=ingredient.source.quote,
                note=f"vegan substitute for '{ingredient.name_original}': {substitution.reason}",
            ),
        }
    )


def _carry_into_step(
    step: Step, replaced: dict[str, tuple[Ingredient, Ingredient, Substitution]]
) -> tuple[Step, Change | None]:
    hits = [
        entry
        for old_id, entry in replaced.items()
        if old_id in step.ingredient_ids or _mentions(step.text, entry[0], entry[2])
    ]
    if not hits:
        return step, None

    swaps = "; ".join(f"use {new.name} instead of {old.name_original}" for old, new, _ in hits)
    notes = " ".join(dict.fromkeys(s.step_note for _, _, s in hits if s.step_note))
    addition = f"[Vegan: {swaps}.{(' ' + notes) if notes else ''}]"
    ids = tuple(dict.fromkeys(replaced[i][1].id if i in replaced else i for i in step.ingredient_ids))
    new_step = step.model_copy(update={"text": f"{step.text}\n{addition}", "ingredient_ids": ids})
    change = Change(
        rule="vegan",
        target=f"step {step.order}",
        before=", ".join(old.name_original for old, _, _ in hits),
        after=", ".join(new.name for _, new, _ in hits),
        reason="Substitution carried into the method." + (f" {notes}" if notes else ""),
    )
    return new_step, change


def _mentions(text: str, ingredient: Ingredient, substitution: Substitution) -> bool:
    """Whole-word mention of the ingredient or one of its table terms.

    Whole words only: "den Braten" mentions the roast, "Bratenfond" does not.
    """
    lowered = text.lower().replace("ſ", "s")
    words = [ingredient.name_original.lower(), *(t.lower() for t in substitution.match)]
    return any(re.search(rf"(?<![^\W\d_]){re.escape(w)}(?![^\W\d_])", lowered) for w in words)


def _names(ingredient: Ingredient) -> str:
    return f"{ingredient.name} | {ingredient.name_original}".lower().replace("ſ", "s")


def _matches_any(text: str, terms: list[str]) -> bool:
    return any(re.search(r"(?<![^\W\d_])" + re.escape(term.lower()), text) for term in terms)


def _free_id(base: str, taken: set[str]) -> str:
    candidate, n = base[:60], 2
    while candidate in taken:
        candidate, n = f"{base[:57]}_{n}", n + 1
    return candidate
