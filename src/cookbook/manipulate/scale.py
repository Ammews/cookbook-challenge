"""Change the number of servings.

Not everything scales linearly, so the rule decides per ingredient:
- exact amounts with a unit scale by the factor;
- counted items (eggs, onions) scale and are rounded to whole pieces;
- vague and to-taste amounts are left alone, with a note to adjust by taste;
- cooking and marinating times are not scaled (they depend on the size of
  each piece, not on how many people eat it), with a note to check doneness;
- if the amount changes a lot, the cook is told to check the pot size.
"""

from fractions import Fraction

from cookbook.formatting import format_amount, format_number
from cookbook.manipulate.rules import ManipulationError
from cookbook.models import Change, Ingredient, Quantity, QuantityKind, Recipe, Servings, Source, SourceStatus

_POT_WARNING_FACTOR = 1.5


class ScaleServings:
    name = "scale"

    def __init__(self, target: int, assume_base: int | None = None) -> None:
        if target < 1:
            raise ManipulationError("servings must be at least 1")
        self.target = target
        self.assume_base = assume_base

    def apply(self, recipe: Recipe) -> tuple[Recipe, list[Change]]:
        base = recipe.servings.value or self.assume_base
        if base is None:
            raise ManipulationError(
                "the recipe does not say how many people it serves, so it cannot be scaled; "
                "pass --assume-servings N to scale from an assumed number"
            )
        if base == self.target:
            return recipe, []
        factor = Fraction(self.target, base)

        changes: list[Change] = [self._servings_change(recipe, base)]
        ingredients = []
        unscaled = []
        for ingredient in recipe.ingredients:
            scaled, change = _scale(ingredient, factor)
            ingredients.append(scaled)
            if change:
                changes.append(change)
            elif ingredient.quantity.kind is not QuantityKind.EXACT:
                unscaled.append(ingredient.name_original)

        if unscaled:
            changes.append(
                Change(
                    rule=self.name,
                    target="amounts not given",
                    before=", ".join(unscaled),
                    after="unchanged",
                    reason="The recipe gives no number for these, so there is nothing to multiply. Adjust by taste.",
                )
            )
        if any(step.duration for step in recipe.steps):
            changes.append(
                Change(
                    rule=self.name,
                    target="times",
                    before="as written",
                    after="unchanged",
                    reason=(
                        "Cooking and marinating times depend on the size of each piece, not on the number of "
                        "people. A bigger roast needs longer: check doneness instead of the clock."
                    ),
                )
            )
        if recipe.tools and (factor >= _POT_WARNING_FACTOR or factor <= 1 / _POT_WARNING_FACTOR):
            changes.append(
                Change(
                    rule=self.name,
                    target="tools",
                    before=", ".join(t.name for t in recipe.tools),
                    after="check sizes",
                    reason=f"Amounts change by ×{format_number(float(factor))}; check that pots and pans still fit.",
                )
            )

        servings = Servings(
            value=self.target,
            source=Source(
                status=SourceStatus.RULE,
                note=f"scaled from {base} servings ({_origin(recipe, base, self.assume_base)})",
            ),
        )
        return recipe.model_copy(update={"servings": servings, "ingredients": tuple(ingredients)}), changes

    def _servings_change(self, recipe: Recipe, base: int) -> Change:
        return Change(
            rule=self.name,
            target="servings",
            before=str(base),
            after=str(self.target),
            reason=f"Requested {self.target} servings; the original serves {base} "
            f"({_origin(recipe, base, self.assume_base)}).",
        )


def _scale(ingredient: Ingredient, factor: Fraction) -> tuple[Ingredient, Change | None]:
    quantity = ingredient.quantity
    if quantity.kind is not QuantityKind.EXACT or quantity.value is None:
        return ingredient, None

    counted = quantity.unit is None
    value = _multiply(quantity.value, factor, counted)
    high = _multiply(quantity.max_value, factor, counted) if quantity.max_value else None
    if high is not None and high <= value:
        high = None
    scaled = Quantity(kind=quantity.kind, value=value, max_value=high, unit=quantity.unit, raw=quantity.raw)

    reason = f"×{format_number(float(factor))}"
    exact = float(quantity.value * factor)
    if counted and abs(value - exact) > 1e-9:
        reason += f" = {format_number(exact)}, rounded to whole pieces"
    new = ingredient.model_copy(update={"quantity": scaled})
    change = Change(
        rule="scale",
        target=ingredient.id,
        before=f"{format_amount(quantity)} {ingredient.name_original}",
        after=f"{format_amount(scaled)} {ingredient.name_original}",
        reason=reason,
    )
    return new, change


def _multiply(value: float, factor: Fraction, counted: bool) -> float:
    exact = Fraction(value).limit_denominator(1000) * factor
    if counted:
        return float(max(1, round(exact)))
    return round(float(exact), 3)


def _origin(recipe: Recipe, base: int, assumed: int | None) -> str:
    if recipe.servings.value is None and assumed is not None:
        return f"assumed by the user: {assumed}"
    status = recipe.servings.source.status
    if status is SourceStatus.INFERRED:
        return f"inferred, not stated: {recipe.servings.source.note}"
    if status is SourceStatus.RULE:
        return recipe.servings.source.note or "set by an earlier rule"
    return "stated in the recipe"
