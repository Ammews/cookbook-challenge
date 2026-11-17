"""The vegan rule when the extraction model has classified each ingredient.

Each case here failed with the name-only rule (see AI_LOG.md, session 8).
"""

import pytest

from cookbook.manipulate import MakeVegan, ScaleServings, apply_rules
from cookbook.manipulate.vegan import default_table
from cookbook.models import AnimalContent, Quantity, QuantityKind, Servings
from factories import exact, ingredient, read, recipe, step

A = AnimalContent


def item(name, original=None, animal=A.NONE, **overrides):
    id = "".join(c for c in name.split()[0].lower() if c.isalnum()) or "item"
    return ingredient(
        id, name=name, name_original=original or name, animal=animal,
        quantity=overrides.pop("quantity", Quantity(kind=QuantityKind.ABSENT)), **overrides,
    )


def vegan(*ingredients, steps=None):
    dish = recipe(
        ingredients=ingredients,
        steps=steps or (step(ingredient_ids=(), tool_ids=()),),
        tools=(),
    )
    return apply_rules(dish, [MakeVegan()])


def only(result):
    (single,) = result.recipe.ingredients
    return single


@pytest.mark.parametrize(
    ("name", "original"),
    [
        ("butternut squash", "butternut squash"),
        ("buttercup squash", "buttercup squash"),
        ("coconut milk", "Kokosmilch"),
        ("almond milk", "Mandelmilch"),
        ("beef tomato", "Fleischtomate"),
        ("hamburger buns", "hamburger buns"),
    ],
)
def test_ingredient_classified_as_no_animal_content_is_never_replaced(name, original):
    result = vegan(item(name, original, animal=A.NONE))
    assert only(result).name == name
    assert result.changes == ()


@pytest.mark.parametrize(
    ("name", "animal"),
    [
        ("pesto", A.DAIRY),
        ("mayonnaise", A.EGG),
        ("egg noodles", A.EGG),
        ("salami", A.MEAT),
        ("mortadella", A.MEAT),
        ("minced beef", A.MEAT),
        ("Worcestershire sauce", A.FISH),
        ("eggs, scrambled", A.EGG),
    ],
)
def test_animal_product_without_a_known_substitute_is_kept_and_warned(name, animal):
    result = vegan(item(name, animal=animal))
    assert only(result).name == name  # nothing invented
    messages = [w.message for w in result.recipe.warnings]
    assert any(m.startswith("Not fully vegan") and name in m for m in messages)
    assert any(f"contains {animal.value}" in m for m in messages)
    assert result.changes[0].after == "unchanged, no known substitute"


@pytest.mark.parametrize(
    ("name", "original", "animal", "expected"),
    [
        ("beef steak", "Bife de gado", A.MEAT, "seitan roast (or a whole celeriac)"),
        ("smoked pork loin", "Kassler", A.MEAT, "seitan roast (or a whole celeriac)"),
        ("quark", "Quark", A.DAIRY, None),  # dairy, but no row knows quark: warned, not guessed
        ("ghee", "Ghee", A.DAIRY, "vegan butter"),
        ("cream cheese", "Frischkäse", A.DAIRY, "plant-based cream cheese"),
        ("butter", "Butter", A.DAIRY, "vegan butter"),
        ("eggs", "Eier", A.EGG, "flax egg (1 tbsp ground flaxseed + 3 tbsp water per egg)"),
        ("anchovies", "Sardellen", A.FISH, "marinated smoked tofu"),
        ("chicken stock", "Hühnerbrühe", A.POULTRY, "vegetable stock with the pan juices of the vegan roast"),
    ],
)
def test_classified_animal_product_uses_the_rows_of_its_category(name, original, animal, expected):
    result = only(vegan(item(name, original, animal=animal)))
    assert result.name == (expected or name)


def test_category_limits_which_rows_can_match():
    # "milk chocolate" is dairy, but the milk row excludes chocolate: warned, not turned into oat milk
    result = vegan(item("milk chocolate", animal=A.DAIRY))
    assert only(result).name == "milk chocolate"
    assert any("Not fully vegan" in w.message for w in result.recipe.warnings)


def test_uncertain_ingredient_is_kept_and_warned():
    result = vegan(item("puff pastry", "Blätterteig", animal=A.UNCERTAIN))
    assert only(result).name == "puff pastry"
    assert any("could not tell" in w.message for w in result.recipe.warnings)


def test_intermediate_made_from_replaced_ingredients_is_not_a_false_alarm():
    result = vegan(
        item("eggs", "Eier", animal=A.EGG),
        item("dumpling dough", "dough", animal=A.EGG, is_intermediate=True),
    )
    assert [i.name for i in result.recipe.ingredients][1] == "dumpling dough"
    assert not any("Not fully vegan" in w.message for w in result.recipe.warnings)


def test_intermediate_with_its_own_row_is_still_replaced():
    result = vegan(item("pan juices", "Bratenfond", animal=A.MEAT, is_intermediate=True))
    assert "vegetable stock" in only(result).name


def test_substitute_is_marked_as_containing_nothing_animal():
    assert only(vegan(item("butter", animal=A.DAIRY))).animal is A.NONE


def test_warnings_are_not_repeated_when_the_rule_runs_twice():
    once = vegan(item("pesto", animal=A.DAIRY), item("butter", animal=A.DAIRY))
    twice = apply_rules(once.recipe, [MakeVegan()])
    assert twice.recipe == once.recipe
    assert twice.changes == ()


def test_classified_recipe_still_commutes_with_scaling():
    dish = recipe(
        servings=Servings(value=4, source=read("Servings: 4")),
        ingredients=(
            item("chicken", animal=A.POULTRY, quantity=exact(1)),
            item("butter", animal=A.DAIRY, quantity=exact(2, unit="tbsp", raw="2 tbsp")),
            item("pesto", animal=A.DAIRY),
        ),
        steps=(step(ingredient_ids=("chicken", "butter"), tool_ids=()),),
        tools=(),
    )
    a = apply_rules(dish, [MakeVegan(), ScaleServings(6)]).recipe
    b = apply_rules(dish, [ScaleServings(6), MakeVegan()]).recipe
    assert a == b


def test_steps_still_receive_the_substitution():
    result = vegan(
        item("butter", animal=A.DAIRY),
        steps=(step(text="Melt the butter.", ingredient_ids=("butter",), tool_ids=()),),
    )
    assert "[Vegan: use vegan butter instead of butter.]" in result.recipe.steps[0].text


def test_every_substitute_in_the_table_is_recognised_as_already_vegan():
    table = default_table()
    for row in table.substitutions:
        lowered = row.replace_with.lower()
        assert any(term in lowered for term in table.already_vegan), row.replace_with


def test_every_row_names_at_least_one_animal_category():
    for row in default_table().substitutions:
        assert all(c.is_animal for c in row.categories), row.replace_with
