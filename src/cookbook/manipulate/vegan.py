"""Make a recipe vegan, carried through to the steps.

Two jobs, split the way the rest of the pipeline is split:
- **Recognising** what an ingredient contains is a language task, so the
  extraction model does it (`Ingredient.animal`: none, dairy, egg, meat...).
- **Deciding** what to do is code: a substitution table in a data file
  (vegan_substitutions.yaml), searched only among the rows for that category.

When the table has no substitute, or the model could not tell, the
ingredient is kept and a warning says so. The rule never invents a
substitute and never lets an animal product through silently.

Ingredients without a classification (older data) fall back to matching
the table by name, which was the only method before categories existed.
"""

import re
from functools import cache
from pathlib import Path

import yaml
from pydantic import Field

from cookbook.models import (
    AnimalContent,
    Change,
    Ingredient,
    Quantity,
    QuantityKind,
    Recipe,
    ReviewWarning,
    Source,
    SourceStatus,
    Step,
)
from cookbook.models.base import DomainModel

_TABLE = Path(__file__).with_name("vegan_substitutions.yaml")


class Substitution(DomainModel):
    categories: list[AnimalContent] = Field(min_length=1)
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
        unresolved: list[tuple[Ingredient, str]] = []
        taken_ids = {i.id for i in recipe.ingredients}
        ingredients = []

        for ingredient in recipe.ingredients:
            substitution, problem = self._decide(ingredient)
            if substitution is None:
                ingredients.append(ingredient)
                if problem:
                    unresolved.append((ingredient, problem))
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

        def warn(ingredient: Ingredient, message: str, after: str, reason: str) -> None:
            if message in existing:
                return  # applying the rule again adds nothing
            warnings.append(ReviewWarning(message=message, target_id=ingredient.id))
            existing.add(message)
            changes.append(
                Change(rule=self.name, target=ingredient.id, before=ingredient.name_original, after=after, reason=reason)
            )

        if unresolved:
            names = ", ".join(i.name_original for i, _ in unresolved)
            summary = f"Not fully vegan: no vegan substitute is known for {names}. Choose one before cooking."
            if summary not in existing:
                warnings.append(ReviewWarning(message=summary))
                existing.add(summary)
        for ingredient, problem in unresolved:
            warn(ingredient, f"Vegan, {ingredient.name_original}: {problem}", "unchanged, no known substitute", problem)

        for ingredient in ingredients:
            check = self._check_for(ingredient)
            if check is not None:
                warn(
                    ingredient,
                    f"Vegan check, {ingredient.name_original}: {check.reason}",
                    "unchanged, check the label",
                    check.reason,
                )

        updated = recipe.model_copy(
            update={"ingredients": tuple(ingredients), "steps": tuple(steps), "warnings": tuple(warnings)}
        )
        return updated, changes

    def _decide(self, ingredient: Ingredient) -> tuple[Substitution | None, str | None]:
        """Return the substitution to apply, or a problem to report, or neither."""
        names = _names(ingredient)
        if _matches_any(names, self.table.already_vegan):
            return None, None
        category = ingredient.animal
        if category is None:  # not classified: match by name, as before categories existed
            return self._find(names, self.table.substitutions), None
        if category is AnimalContent.NONE:
            return None, None
        if category is AnimalContent.UNCERTAIN:
            return None, "could not tell whether it contains animal products (it depends on the brand or recipe)."
        rows = [s for s in self.table.substitutions if category in s.categories]
        substitution = self._find(names, rows)
        if substitution is None and ingredient.is_intermediate:
            # Made in the recipe from listed ingredients (a dough from the eggs, a
            # marinade): its animal content comes from those, which this rule already
            # handles, so a warning here would be a false alarm.
            return None, None
        if substitution is None:
            return None, f"contains {category.value.replace('_', ' ')}, and no vegan substitute is known for it."
        return substitution, None

    @staticmethod
    def _find(names: str, rows: list[Substitution]) -> Substitution | None:
        return next(
            (s for s in rows if _matches_any(names, s.match) and not _matches_any(names, s.exclude)),
            None,
        )

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
            "animal": AnimalContent.NONE if ingredient.animal is not None else None,
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
