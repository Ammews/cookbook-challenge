"""Compare one pipeline outcome against the expectations of its case.

Every check returns a result with a readable detail, so a failing run says
what was expected and what was found, not just "failed".
"""

import re
from collections.abc import Iterable

from cookbook.evaluation.outcome import Outcome
from cookbook.evaluation.spec import (
    AcceptedQuantity,
    CountRange,
    Expectations,
    IngredientCheck,
    QuantityCheck,
    ServingsCheck,
    ToolCheck,
)
from cookbook.models import Ingredient, Quantity, Recipe, Tool
from cookbook.models.base import DomainModel

_VALUE_TOLERANCE = 0.01  # 1 %, so 0.75 matches 3/4 written as 0.7500001


class CheckResult(DomainModel):
    name: str
    passed: bool
    detail: str


def evaluate(expect: Expectations, outcome: Outcome) -> list[CheckResult]:
    results = [
        _check(
            "is a recipe",
            outcome.is_recipe == expect.is_recipe,
            f"expected {expect.is_recipe}, got {outcome.is_recipe}",
        )
    ]
    if not expect.is_recipe or not outcome.is_recipe or outcome.recipe is None:
        if expect.is_recipe and outcome.recipe is None:
            results.append(_check("recipe extracted", False, "no recipe was produced"))
        return results

    recipe = outcome.recipe
    found_multiple = outcome.recipes_in_document > 1
    results.append(
        _check(
            "multiple recipes detected",
            found_multiple == expect.multiple_recipes,
            f"expected {expect.multiple_recipes}, "
            f"pipeline reported {outcome.recipes_in_document} recipe(s)",
        )
    )
    if expect.min_warnings:
        results.append(
            _check(
                "review warnings",
                len(recipe.warnings) >= expect.min_warnings,
                f"expected at least {expect.min_warnings}, got {len(recipe.warnings)}",
            )
        )
    if expect.servings:
        results.extend(_check_servings(expect.servings, recipe))
    for ingredient_check in expect.ingredients:
        results.extend(_check_ingredient(ingredient_check, recipe.ingredients))
    for name in expect.absent_ingredients:
        hits = [i for i in recipe.ingredients if name in _names(i)]
        results.append(
            _check(
                f"'{name}' absent",
                not hits,
                "not found" if not hits else f"found in: {', '.join(i.name_original for i in hits)}",
            )
        )
    if expect.ingredient_count:
        results.append(_check_count("ingredient count", expect.ingredient_count, len(recipe.ingredients)))
    for tool_check in expect.tools:
        results.append(_check_tool(tool_check, recipe.tools))
    if expect.step_count:
        results.append(_check_count("step count", expect.step_count, len(recipe.steps)))
    return results


def _check_servings(check: ServingsCheck, recipe: Recipe) -> list[CheckResult]:
    servings = recipe.servings
    results = [
        _check(
            "servings status",
            servings.source.status in check.status_any,
            f"expected one of {[s.value for s in check.status_any]}, got {servings.source.status.value}",
        )
    ]
    if check.value is not None:
        results.append(
            _check("servings value", servings.value == check.value, f"expected {check.value}, got {servings.value}")
        )
    if servings.value is not None and (check.min_value is not None or check.max_value is not None):
        low = check.min_value if check.min_value is not None else 1
        high = check.max_value if check.max_value is not None else servings.value
        results.append(
            _check(
                "servings plausible",
                low <= servings.value <= high,
                f"expected {low}..{high}, got {servings.value}",
            )
        )
    return results


def _check_ingredient(check: IngredientCheck, ingredients: Iterable[Ingredient]) -> list[CheckResult]:
    label = check.match[0]
    hits = [i for i in ingredients if _matches(i, check)]
    count_ok = check.min_count <= len(hits) <= check.max_count
    expected_count = (
        str(check.min_count) if check.min_count == check.max_count else f"{check.min_count}..{check.max_count}"
    )
    found = ", ".join(i.name_original for i in hits) or "none"
    results = [_check(f"{label}: count", count_ok, f"expected {expected_count}, found {len(hits)} ({found})")]
    if not hits:
        return results

    if check.quantity:
        ok = any(_quantity_ok(check.quantity, i.quantity) for i in hits)
        results.append(
            _check(f"{label}: quantity", ok, f"got {[_describe(i.quantity) for i in hits]}")
        )
    if check.optional is not None:
        ok = any(i.optional == check.optional for i in hits)
        results.append(_check(f"{label}: optional", ok, f"expected optional={check.optional}"))
    if check.intermediate is not None:
        ok = any(i.is_intermediate == check.intermediate for i in hits)
        results.append(_check(f"{label}: intermediate", ok, f"expected intermediate={check.intermediate}"))
    return results


def _check_tool(check: ToolCheck, tools: Iterable[Tool]) -> CheckResult:
    label = check.match[0]
    hits = [t for t in tools if any(m in _normalise(t.name) for m in check.match)]
    if not hits:
        return _check(f"tool {label}", False, "not found")
    if check.stated is not None and not any(t.stated == check.stated for t in hits):
        return _check(f"tool {label}", False, f"found, but expected stated={check.stated}")
    return _check(f"tool {label}", True, f"found: {', '.join(t.name for t in hits)}")


def _check_count(name: str, expected: CountRange, actual: int) -> CheckResult:
    ok = (expected.min is None or actual >= expected.min) and (expected.max is None or actual <= expected.max)
    return _check(name, ok, f"expected {expected.min}..{expected.max}, got {actual}")


def _quantity_ok(check: QuantityCheck, quantity: Quantity) -> bool:
    if check.kind_any and quantity.kind not in check.kind_any:
        return False
    if not check.accept:
        return True
    return any(_accepts(a, quantity) for a in check.accept)


def _accepts(accepted: AcceptedQuantity, quantity: Quantity) -> bool:
    if quantity.value is None:
        return False
    if abs(quantity.value - accepted.value) > _VALUE_TOLERANCE * max(1.0, accepted.value):
        return False
    if accepted.unit is None:
        return True
    spellings = [accepted.unit] if isinstance(accepted.unit, str) else accepted.unit
    return normalise_unit(quantity.unit) in {normalise_unit(s) for s in spellings}


def normalise_unit(unit: str | None) -> str:
    """Lower-case, drop notes in brackets and a trailing dot: "xícara (chá)" -> "xícara"."""
    if unit is None:
        return ""
    unit = re.sub(r"\(.*?\)", "", unit)
    return unit.strip().rstrip(".").strip().lower()


def _matches(ingredient: Ingredient, check: IngredientCheck) -> bool:
    names = _names(ingredient)
    return any(m in names for m in check.match) and not any(x in names for x in check.exclude)


def _names(ingredient: Ingredient) -> str:
    return _normalise(f"{ingredient.name} | {ingredient.name_original}")


def _normalise(text: str) -> str:
    return text.lower().replace("ſ", "s")


def _describe(quantity: Quantity) -> str:
    if quantity.value is None:
        return f"{quantity.kind.value} ({quantity.raw or 'no text'})"
    return f"{quantity.value:g} {quantity.unit or ''}".strip()


def _check(name: str, passed: bool, detail: str) -> CheckResult:
    return CheckResult(name=name, passed=passed, detail=detail)
