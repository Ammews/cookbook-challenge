import pytest

from cookbook.manipulate import ConvertToMetric, MakeVegan, ScaleServings, apply_rules
from cookbook.manipulate.units import find_unit
from cookbook.models import Quantity, QuantityKind, Servings
from factories import exact, ingredient, read, recipe, step


def amount(value, unit, max_value=None):
    return Quantity(kind=QuantityKind.EXACT, value=value, max_value=max_value, unit=unit, raw=f"{value} {unit}")


def converted(value, unit, max_value=None):
    item = ingredient("x", name_original="x", quantity=amount(value, unit, max_value))
    dish = recipe(ingredients=(item,), steps=(step(ingredient_ids=(), tool_ids=()),), tools=())
    q = apply_rules(dish, [ConvertToMetric()]).recipe.ingredients[0].quantity
    return (q.value, q.unit) if q.max_value is None else (q.value, q.max_value, q.unit)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (0.75, "cup", (180, "ml")),
        (2.25, "cups", (540, "ml")),
        (0.75, "c", (180, "ml")),
        (1, "tsp", (5, "ml")),
        (0.5, "t", (2.5, "ml")),
        (2, "T", (30, "ml")),
        (1, "Esslöffel", (15, "ml")),
        (1, "Theelöffel", (5, "ml")),
        (0.5, "l", (500, "ml")),
        (1.2, "Liter", (1.2, "l")),
        (5, "oz", (142, "g")),
        (0.5, "pound", (227, "g")),
        (0.5, "lb", (227, "g")),
        (1, "Pfund", (500, "g")),
        (2, "Lot", (31, "g")),
        (2, "sticks", (226, "g")),
        (1, "xícara (chá)", (240, "ml")),
        (3, "colheres (chá)", (15, "ml")),
        (1, "colher (sopa)", (15, "ml")),
        (1, "copo (americano)", (190, "ml")),
        (1500, "g", (1.5, "kg")),
    ],
)
def test_common_units_convert_to_metric(value, unit, expected):
    assert converted(value, unit) == expected


def test_german_pound_is_not_the_english_pound():
    assert converted(1, "Pfund") != converted(1, "lb")


def test_teaspoon_and_tablespoon_abbreviations_are_case_sensitive():
    assert converted(1, "t") == (5, "ml")
    assert converted(1, "T") == (15, "ml")


def test_ranges_convert_at_both_ends():
    assert converted(2, "cups", max_value=3) == (480, 720, "ml")


def test_range_crossing_a_litre_stays_in_one_unit():
    assert converted(3, "cups", max_value=5) == (720, 1200, "ml")


@pytest.mark.parametrize("unit", ["Teeglas", "Stück", "pinch", "Bund", "colher", "copo"])
def test_units_without_a_standard_size_are_left_alone_and_reported(unit):
    item = ingredient("x", name_original="Olivenöl", quantity=amount(1, unit))
    result = apply_rules(recipe(ingredients=(item,), steps=(), tools=()), [ConvertToMetric()])
    assert result.recipe.ingredients[0].quantity.unit == unit
    note = next(c for c in result.changes if c.target == "units without a standard size")
    assert unit in note.before


def test_counted_and_unquantified_items_are_untouched():
    dish = recipe(
        ingredients=(
            ingredient("onion", quantity=exact(4)),
            ingredient("salt", name_original="Salz", quantity=Quantity(kind=QuantityKind.TO_TASTE)),
        ),
        steps=(step(ingredient_ids=("onion",), tool_ids=()),),
    )
    result = apply_rules(dish, [ConvertToMetric()])
    assert result.recipe == dish and result.changes == ()


def test_every_conversion_says_what_it_used():
    item = ingredient("flour", name_original="flour", quantity=amount(0.5, "lb"))
    change = apply_rules(recipe(ingredients=(item,), steps=(), tools=()), [ConvertToMetric()]).changes[0]
    assert (change.before, change.after, change.reason) == ("½ lb flour", "227 g flour", "1 lb = 453.6 g")


def test_metric_values_are_left_as_they_are():
    assert converted(250, "g") == (250, "g")


def test_conversion_is_idempotent():
    item = ingredient("flour", name_original="flour", quantity=amount(0.75, "cup"))
    once = apply_rules(recipe(ingredients=(item,), steps=(), tools=()), [ConvertToMetric()]).recipe
    twice = apply_rules(once, [ConvertToMetric()])
    assert twice.recipe == once and twice.changes == ()


def test_all_three_rules_combine():
    dish = recipe(
        servings=Servings(value=4, source=read("Servings: 4")),
        ingredients=(
            ingredient("butter", name="butter", name_original="Butter", quantity=amount(0.5, "lb")),
            ingredient("flour", name="flour", name_original="flour", quantity=amount(2, "cups")),
        ),
        steps=(step(ingredient_ids=("butter", "flour"), tool_ids=()),),
        tools=(),
    )
    result = apply_rules(dish, [MakeVegan(), ScaleServings(6), ConvertToMetric()]).recipe
    butter, flour = result.ingredients
    assert butter.name == "vegan butter" and (butter.quantity.value, butter.quantity.unit) == (340, "g")
    assert (flour.quantity.value, flour.quantity.unit) == (720, "ml")


def test_unknown_unit_lookup_returns_nothing():
    assert find_unit("Teeglas") is None
    assert find_unit(None) is None


def test_metric_amounts_are_written_as_decimals():
    from cookbook.formatting import format_amount

    assert format_amount(amount(2.5, "ml")) == "2.5 ml"
    assert format_amount(amount(1.2, "l")) == "1.2 l"
    assert format_amount(amount(0.5, "cup")) == "½ cup"
