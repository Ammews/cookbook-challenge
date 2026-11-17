"""Convert amounts to metric (ml, l, g, kg), deterministically.

Units are matched as written, because the same letters mean different things:
- "t" is a teaspoon and "T" a tablespoon on American cards (case matters);
- a German "Pfund" is 500 g, an English pound 453.6 g;
- "colher (chá)" is a teaspoon and "colher (sopa)" a tablespoon.

Units with no standard size ("Teeglas", "Stück", "pinch") are left as they are
and reported, never guessed.

Apply this rule last: it rounds to whole millilitres and grams, so rounding
happens once, after scaling.
"""

import re
from dataclasses import dataclass

from cookbook.formatting import format_amount
from cookbook.models import Change, Ingredient, Quantity, QuantityKind, Recipe


@dataclass(frozen=True)
class _Unit:
    amount: float  # in ml or g
    dimension: str  # "volume" or "mass"
    note: str


_ML, _G = "volume", "mass"

# Case-sensitive spellings first (American cards: t = teaspoon, T = tablespoon).
_EXACT: dict[str, _Unit] = {
    "t": _Unit(5, _ML, "1 t (teaspoon) = 5 ml"),
    "T": _Unit(15, _ML, "1 T (tablespoon) = 15 ml"),
    "c": _Unit(240, _ML, "1 c (US cup) = 240 ml"),
}

# Lower-case spellings, after removing a trailing "s"/"es" and dots.
_UNITS: dict[str, _Unit] = {
    **{u: _Unit(1, _ML, "") for u in ("ml", "milliliter", "millilitre")},
    **{u: _Unit(10, _ML, "1 cl = 10 ml") for u in ("cl",)},
    **{u: _Unit(100, _ML, "1 dl = 100 ml") for u in ("dl",)},
    **{u: _Unit(1000, _ML, "1 l = 1000 ml") for u in ("l", "liter", "litre", "litro")},
    **{u: _Unit(5, _ML, "1 teaspoon = 5 ml") for u in ("tsp", "teaspoon", "tl", "teelöffel", "theelöffel")},
    **{u: _Unit(15, _ML, "1 tablespoon = 15 ml") for u in ("tbsp", "tablespoon", "el", "esslöffel", "eßlöffel")},
    **{u: _Unit(240, _ML, "1 US cup = 240 ml") for u in ("cup", "xícara")},
    **{u: _Unit(190, _ML, "1 copo americano = 190 ml") for u in ("copo americano",)},
    **{u: _Unit(29.57, _ML, "1 US fl oz = 29.57 ml") for u in ("fl oz", "fluid ounce")},
    **{u: _Unit(473, _ML, "1 US pint = 473 ml") for u in ("pint", "pt")},
    **{u: _Unit(1, _G, "") for u in ("g", "gram", "gramm", "grama", "gr")},
    **{u: _Unit(1000, _G, "1 kg = 1000 g") for u in ("kg", "kilogram", "kilogramm", "quilo")},
    **{u: _Unit(28.35, _G, "1 oz = 28.35 g") for u in ("oz", "ounce")},
    **{u: _Unit(453.6, _G, "1 lb = 453.6 g") for u in ("lb", "pound")},
    **{u: _Unit(500, _G, "1 Pfund (German) = 500 g") for u in ("pfund",)},
    **{u: _Unit(15.6, _G, "1 Lot (old German) ≈ 15.6 g") for u in ("lot", "loth")},
    **{u: _Unit(113, _G, "1 stick of butter = 113 g") for u in ("stick",)},
}

# Portuguese spoons: the bracket decides the size.
_SPOONS = {"chá": _Unit(5, _ML, "1 colher (chá) = 5 ml"), "sopa": _Unit(15, _ML, "1 colher (sopa) = 15 ml")}


def find_unit(unit: str | None) -> _Unit | None:
    if not unit:
        return None
    written = unit.strip()
    if written in _EXACT:
        return _EXACT[written]
    lowered = written.lower()
    if lowered.startswith("colher"):
        size = next((s for word, s in _SPOONS.items() if word in lowered), None)
        return size
    if lowered.startswith("xícara"):
        return _UNITS["xícara"]
    if lowered.startswith("copo"):
        return _UNITS["copo americano"] if "americano" in lowered else None
    key = re.sub(r"\(.*?\)", "", lowered).replace(".", "").strip()
    for candidate in (key, key.removesuffix("es"), key.removesuffix("s")):
        if candidate in _UNITS:
            return _UNITS[candidate]
    return None


def to_metric(value: float, unit: _Unit) -> tuple[float, str]:
    amount = value * unit.amount
    big, small = ("l", "ml") if unit.dimension == _ML else ("kg", "g")
    if amount >= 1000:
        return round(amount / 1000, 2), big
    return (round(amount, 1) if amount < 10 else float(round(amount))), small


class ConvertToMetric:
    name = "metric"

    def apply(self, recipe: Recipe) -> tuple[Recipe, list[Change]]:
        changes: list[Change] = []
        unknown: list[str] = []
        ingredients = []
        for ingredient in recipe.ingredients:
            converted, change = _convert(ingredient)
            ingredients.append(converted)
            if change:
                changes.append(change)
            elif _has_unknown_unit(ingredient):
                unknown.append(f"{ingredient.quantity.unit} ({ingredient.name_original})")
        if unknown:
            changes.append(
                Change(
                    rule=self.name,
                    target="units without a standard size",
                    before=", ".join(unknown),
                    after="unchanged",
                    reason="No standard metric equivalent, so they are kept as written rather than guessed.",
                )
            )
        return recipe.model_copy(update={"ingredients": tuple(ingredients)}), changes


def _convert(ingredient: Ingredient) -> tuple[Ingredient, Change | None]:
    quantity = ingredient.quantity
    unit = find_unit(quantity.unit) if quantity.kind is QuantityKind.EXACT else None
    if unit is None or quantity.value is None:
        return ingredient, None
    value, metric_unit = to_metric(quantity.value, unit)
    high = None
    if quantity.max_value is not None:
        high_value, high_unit = to_metric(quantity.max_value, unit)
        if high_unit != metric_unit:  # e.g. 900 ml – 1.2 l: express both in the small unit
            value, metric_unit = float(round(quantity.value * unit.amount)), ("ml" if unit.dimension == _ML else "g")
            high_value = float(round(quantity.max_value * unit.amount))
        high = high_value if high_value > value else None
    if metric_unit == quantity.unit and value == quantity.value:
        return ingredient, None
    converted = Quantity(kind=quantity.kind, value=value, max_value=high, unit=metric_unit, raw=quantity.raw)
    change = Change(
        rule="metric",
        target=ingredient.id,
        before=f"{format_amount(quantity)} {ingredient.name_original}",
        after=f"{format_amount(converted)} {ingredient.name_original}",
        reason=unit.note or "metric",
    )
    return ingredient.model_copy(update={"quantity": converted}), change


def _has_unknown_unit(ingredient: Ingredient) -> bool:
    quantity = ingredient.quantity
    return quantity.kind is QuantityKind.EXACT and quantity.unit is not None and find_unit(quantity.unit) is None
