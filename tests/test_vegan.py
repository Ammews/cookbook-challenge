from cookbook.manipulate import MakeVegan, ScaleServings, apply_rules
from cookbook.models import Quantity, QuantityKind, Servings, SourceStatus
from factories import exact, ingredient, inferred, read, recipe, step


def absent():
    return Quantity(kind=QuantityKind.ABSENT)


def sauerbraten():
    return recipe(
        servings=Servings(value=4, source=inferred("1 l marinade for about 1 kg meat")),
        ingredients=(
            ingredient("beef", name="beef roast", name_original="Bratenstücke", quantity=absent()),
            ingredient("bacon", name="bacon", name_original="Speck", quantity=absent()),
            ingredient("butter", name="butter", name_original="Butter", quantity=absent()),
            ingredient("onion", name="onion", name_original="Zwiebeln", quantity=exact(4)),
            ingredient(
                "pan_juices", name="pan juices", name_original="Bratenfond", quantity=absent(), is_intermediate=True
            ),
            ingredient("red_wine", name="red wine", name_original="Rotwein", quantity=absent()),
            ingredient("sugar", name="sugar", name_original="Zucker", quantity=Quantity(kind=QuantityKind.TO_TASTE)),
            ingredient("egg", name="eggs", name_original="Eier", quantity=exact(2)),
        ),
        tools=(),
        steps=(
            step(1, text="Den Speck auslassen, Butter dazugeben, den Braten ins heiße Fett geben.",
                 ingredient_ids=("bacon", "butter", "beef"), tool_ids=()),
            step(2, text="Für die Soße schwitzt man den Bratenfond mit Mehl an.",
                 ingredient_ids=("pan_juices",), tool_ids=()),
            step(3, text="Man legt den Braten eine Stunde in die Soße.", ingredient_ids=(), tool_ids=()),
            step(4, text="Zwiebeln dazugeben.", ingredient_ids=("onion",), tool_ids=()),
        ),
    )


def names(result):
    return [i.name for i in result.recipe.ingredients]


def test_animal_products_are_replaced():
    result = apply_rules(sauerbraten(), [MakeVegan()])
    replaced = names(result)
    assert "seitan roast (or a whole celeriac)" in replaced
    assert "smoked tofu, diced" in replaced
    assert "vegan butter" in replaced
    assert any("flax egg" in n for n in replaced)
    assert not {"beef roast", "bacon", "butter", "eggs"} & set(replaced)


def test_intermediate_made_from_meat_is_replaced_too():
    result = apply_rules(sauerbraten(), [MakeVegan()])
    juices = next(i for i in result.recipe.ingredients if i.id == "vegan_pan_juices")
    assert juices.is_intermediate
    assert "vegetable stock" in juices.name


def test_vegetables_are_untouched():
    onion = next(i for i in apply_rules(sauerbraten(), [MakeVegan()]).recipe.ingredients if i.id == "onion")
    assert onion.name == "onion" and onion.source.status is SourceStatus.READ


def test_substitute_says_what_it_replaced_and_why():
    seitan = next(i for i in apply_rules(sauerbraten(), [MakeVegan()]).recipe.ingredients if i.id == "vegan_beef")
    assert seitan.source.status is SourceStatus.RULE
    assert "Bratenstücke" in seitan.source.note


def test_substitutions_carry_through_to_the_steps():
    steps = apply_rules(sauerbraten(), [MakeVegan()]).recipe.steps
    assert steps[0].ingredient_ids == ("vegan_bacon", "vegan_butter", "vegan_beef")
    assert "use seitan roast" in steps[0].text
    assert "Marinate seitan for 1–2 days at most" in steps[0].text


def test_step_that_only_mentions_the_meat_in_its_text_is_annotated():
    step3 = apply_rules(sauerbraten(), [MakeVegan()]).recipe.steps[2]
    assert "[Vegan:" in step3.text


def test_a_name_inside_a_longer_word_is_not_a_mention():
    step2 = apply_rules(sauerbraten(), [MakeVegan()]).recipe.steps[1]
    assert "Bratenfond" in step2.text
    assert "seitan roast" not in step2.text  # "Braten" must not match inside "Bratenfond"


def test_substitute_does_not_inherit_the_meat_preparation_note():
    meat = ingredient("beef", name="beef roast", name_original="Braten", quantity=absent(), preparation="fest")
    result = apply_rules(recipe(ingredients=(meat,), steps=(step(ingredient_ids=("beef",), tool_ids=()),), tools=()), [MakeVegan()])
    assert result.recipe.ingredients[0].preparation is None


def test_steps_without_animal_products_are_untouched():
    result = apply_rules(sauerbraten(), [MakeVegan()])
    assert result.recipe.steps[3] == sauerbraten().steps[3]


def test_doubtful_products_are_flagged_not_replaced():
    result = apply_rules(sauerbraten(), [MakeVegan()])
    assert "red wine" in names(result) and "sugar" in names(result)
    messages = [w.message for w in result.recipe.warnings]
    assert any("Rotwein" in m and "vegan" in m.lower() for m in messages)
    assert any("Zucker" in m for m in messages)


def test_every_substitution_is_recorded_as_a_change():
    changes = apply_rules(sauerbraten(), [MakeVegan()]).changes
    targets = {c.target for c in changes}
    assert {"beef", "bacon", "butter", "pan_juices", "egg", "step 1", "step 2", "step 3"} <= targets


def test_vegan_twice_is_the_same_as_once():
    once = apply_rules(sauerbraten(), [MakeVegan()])
    twice = apply_rules(once.recipe, [MakeVegan()])
    assert twice.recipe == once.recipe
    assert twice.changes == ()


def test_already_vegan_recipe_is_unchanged():
    hummus = recipe(ingredients=(ingredient("chickpea", name="chickpeas", name_original="dry chickpeas"),), steps=(step(ingredient_ids=("chickpea",), tool_ids=()),), tools=())
    result = apply_rules(hummus, [MakeVegan()])
    assert result.recipe == hummus and result.changes == ()


def test_words_that_only_contain_a_term_are_not_matched():
    safe = recipe(
        ingredients=(
            ingredient("rind", name="lemon rind", name_original="Zitronenschale"),
            ingredient("kraut", name="white cabbage", name_original="Weißkraut"),
            ingredient("pepper", name="roasted peppers", name_original="roasted peppers"),
            ingredient("pasta", name="fettuccine", name_original="fettuccine"),
        ),
        steps=(step(ingredient_ids=(), tool_ids=()),),
        tools=(),
    )
    assert apply_rules(safe, [MakeVegan()]).changes == ()


def test_order_of_vegan_and_scaling_does_not_matter():
    vegan_then_scale = apply_rules(sauerbraten(), [MakeVegan(), ScaleServings(6)])
    scale_then_vegan = apply_rules(sauerbraten(), [ScaleServings(6), MakeVegan()])
    assert vegan_then_scale.recipe == scale_then_vegan.recipe


def test_scaled_substitute_keeps_the_amount_logic():
    result = apply_rules(sauerbraten(), [MakeVegan(), ScaleServings(6)])
    flax = next(i for i in result.recipe.ingredients if i.id == "vegan_egg")
    assert flax.quantity.value == 3


def test_counted_meat_becomes_same_weight_instead_of_a_meaningless_count():
    chicken = ingredient("chicken", name="whole chicken", name_original="1 whole chicken", quantity=exact(1))
    dish = recipe(ingredients=(chicken,), steps=(step(ingredient_ids=("chicken",), tool_ids=()),), tools=())

    substitute = apply_rules(dish, [MakeVegan()]).recipe.ingredients[0]

    assert substitute.quantity.kind is QuantityKind.VAGUE
    assert substitute.quantity.raw == "same weight as the whole chicken it replaces"


def test_same_weight_substitution_still_commutes_with_scaling():
    chicken = ingredient("chicken", name="whole chicken", name_original="1 whole chicken", quantity=exact(1))
    dish = recipe(
        servings=Servings(value=4, source=read("Servings: 4")),
        ingredients=(chicken,), steps=(step(ingredient_ids=("chicken",), tool_ids=()),), tools=(),
    )
    a = apply_rules(dish, [MakeVegan(), ScaleServings(6)]).recipe
    b = apply_rules(dish, [ScaleServings(6), MakeVegan()]).recipe
    assert a == b
