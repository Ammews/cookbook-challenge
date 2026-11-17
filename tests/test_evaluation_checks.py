import pytest

from cookbook.evaluation import Expectations, Outcome, evaluate, normalise_unit
from cookbook.models import Quantity, QuantityKind, ReviewWarning, Servings, Source, SourceStatus
from factories import exact, ingredient, inferred, read, recipe, step, tool


def outcome(**recipe_fields):
    return Outcome(is_recipe=True, recipe=recipe(**recipe_fields))


def failed(results):
    return [r.name for r in results if not r.passed]


def expect(**fields):
    return Expectations.model_validate(fields)


def onion(**overrides):
    return ingredient("onion", **overrides)


def test_a_matching_recipe_passes_every_check():
    results = evaluate(
        expect(
            servings={"status_any": ["inferred"], "min_value": 2, "max_value": 6},
            ingredients=[{"match": ["onion"], "quantity": {"kind_any": ["exact"], "accept": [{"value": 4}]}}],
            ingredient_count={"min": 1, "max": 1},
            tools=[{"match": ["pot"], "stated": True}],
            step_count={"min": 1},
        ),
        outcome(),
    )
    assert failed(results) == []


def test_duplicated_ingredient_fails_the_count():
    results = evaluate(
        expect(ingredients=[{"match": ["onion", "zwiebel"]}]),
        outcome(ingredients=(onion(), ingredient("zwiebeln", name="zwiebeln"))),
    )
    assert failed(results) == ["onion: count"]


def test_missing_ingredient_fails_and_says_so():
    results = evaluate(expect(ingredients=[{"match": ["bacon"]}]), outcome())
    assert failed(results) == ["bacon: count"]
    assert "found 0" in results[-1].detail


def test_exclude_keeps_vinegar_apart_from_vinegar_water():
    vinegar = ingredient("vinegar", name_original="Essig")
    vinegar_water = ingredient("vinegar_water", name_original="Essigwasser", is_intermediate=True)
    results = evaluate(
        expect(
            ingredients=[
                {"match": ["essig"], "exclude": ["wasser"]},
                {"match": ["essigwasser"], "intermediate": True},
            ]
        ),
        outcome(ingredients=(vinegar, vinegar_water), steps=(step(),)),
    )
    assert failed(results) == []


def test_any_accepted_unit_spelling_passes():
    butter = ingredient(
        "butter", name_original="butter", quantity=exact(225, unit="g", raw="225 g")
    )
    check = {
        "match": ["butter"],
        "quantity": {"accept": [{"value": 2, "unit": ["stick", "sticks"]}, {"value": 225, "unit": "g"}]},
    }
    assert failed(evaluate(expect(ingredients=[check]), outcome(ingredients=(butter,), steps=(step(),)))) == []


def test_wrong_value_fails_the_quantity():
    results = evaluate(
        expect(ingredients=[{"match": ["onion"], "quantity": {"accept": [{"value": 6}]}}]), outcome()
    )
    assert failed(results) == ["onion: quantity"]


def test_invented_number_on_an_unquantified_ingredient_fails_the_kind():
    results = evaluate(
        expect(ingredients=[{"match": ["onion"], "quantity": {"kind_any": ["absent", "vague"]}}]), outcome()
    )
    assert failed(results) == ["onion: quantity"]


def test_optional_flag_is_checked():
    results = evaluate(expect(ingredients=[{"match": ["onion"], "optional": True}]), outcome())
    assert failed(results) == ["onion: optional"]


def test_ingredient_that_is_only_in_the_notes_must_be_absent():
    results = evaluate(
        expect(absent_ingredients=["lemon", "cinnamon"]),
        outcome(ingredients=(onion(), ingredient("lemon", name_original="lemon juice")), steps=(step(),)),
    )
    assert failed(results) == ["'lemon' absent"]
    assert "lemon juice" in [r for r in results if not r.passed][0].detail


def test_servings_status_and_value():
    stated = Servings(value=4, source=read("Servings: 4"))
    results = evaluate(
        expect(servings={"status_any": ["read"], "value": 10}), outcome(servings=stated)
    )
    assert failed(results) == ["servings value"]


def test_inferred_servings_outside_the_plausible_range_fail():
    wild_guess = Servings(value=20, source=inferred("guess"))
    results = evaluate(
        expect(servings={"status_any": ["inferred", "missing"], "min_value": 2, "max_value": 8}),
        outcome(servings=wild_guess),
    )
    assert failed(results) == ["servings plausible"]


def test_implied_tool_marked_as_stated_fails():
    results = evaluate(expect(tools=[{"match": ["pot"], "stated": False}]), outcome())
    assert failed(results) == ["tool pot"]


def test_counts_outside_the_range_fail():
    results = evaluate(
        expect(ingredient_count={"min": 2}, step_count={"max": 0}), outcome()
    )
    assert failed(results) == ["ingredient count", "step count"]


def test_document_with_several_recipes_must_be_flagged():
    results = evaluate(
        expect(multiple_recipes=True), Outcome(is_recipe=True, recipes_in_document=1, recipe=recipe())
    )
    assert failed(results) == ["multiple recipes detected"]


def test_hard_input_needs_review_warnings():
    results = evaluate(expect(min_warnings=1), outcome())
    assert failed(results) == ["review warnings"]
    warned = outcome(warnings=(ReviewWarning(message="three recipes on one page"),))
    assert failed(evaluate(expect(min_warnings=1), warned)) == []


def test_not_a_recipe_stops_after_the_first_check():
    results = evaluate(
        expect(is_recipe=False, ingredients=[{"match": ["onion"]}]), Outcome(is_recipe=False)
    )
    assert [r.name for r in results] == ["is a recipe"]
    assert results[0].passed


def test_inventing_a_recipe_from_a_non_recipe_fails():
    assert failed(evaluate(expect(is_recipe=False), outcome())) == ["is a recipe"]


def test_missing_recipe_for_a_recipe_input_fails():
    results = evaluate(expect(), Outcome(is_recipe=True, recipe=None))
    assert failed(results) == ["recipe extracted"]


@pytest.mark.parametrize(
    ("written", "normalised"),
    [("xícara (chá)", "xícara"), ("Tsp.", "tsp"), (" g ", "g"), (None, "")],
)
def test_unit_normalisation(written, normalised):
    assert normalise_unit(written) == normalised


def test_long_s_in_old_print_does_not_break_matching():
    old = ingredient("salt", name_original="Salʒ ſalz")
    assert failed(evaluate(expect(ingredients=[{"match": ["salz"]}]), outcome(ingredients=(old,), steps=(step(),)))) == []
