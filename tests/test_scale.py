import pytest

from cookbook.manipulate import ManipulationError, ScaleServings, apply_rules
from cookbook.models import Duration, Quantity, QuantityKind, Servings, SourceStatus
from factories import exact, ingredient, inferred, read, recipe, step, tool


def litre(value, raw="½ l"):
    return Quantity(kind=QuantityKind.EXACT, value=value, unit="l", raw=raw)


def sauerbraten(servings=4, status="inferred"):
    source = inferred("1 l of marinade suits about 1 kg of meat") if status == "inferred" else read("für 4 Personen")
    return recipe(
        servings=Servings(value=servings, source=source),
        ingredients=(
            ingredient("vinegar", name_original="Essig", quantity=litre(0.5)),
            ingredient("onion", name_original="Zwiebeln", quantity=exact(4)),
            ingredient("egg", name_original="Eier", quantity=exact(1)),
            ingredient("salt", name_original="Salz", quantity=Quantity(kind=QuantityKind.TO_TASTE)),
            ingredient(
                "flour",
                name_original="flour",
                quantity=Quantity(kind=QuantityKind.EXACT, value=2, max_value=3, unit="cups", raw="2–3 cups"),
            ),
        ),
        steps=(step(ingredient_ids=("onion",), tool_ids=("pot",), duration=Duration(raw="eine Stunde", min_minutes=60, max_minutes=60)),),
    )


def by_id(result, id):
    return next(i for i in result.recipe.ingredients if i.id == id)


def test_liquids_scale_linearly():
    result = apply_rules(sauerbraten(), [ScaleServings(6)])
    assert by_id(result, "vinegar").quantity.value == 0.75


def test_counted_items_scale_and_round_to_whole_pieces():
    result = apply_rules(sauerbraten(), [ScaleServings(6)])
    assert by_id(result, "onion").quantity.value == 6
    assert by_id(result, "egg").quantity.value == 2  # 1.5 rounds to 2
    egg_change = next(c for c in result.changes if c.target == "egg")
    assert "rounded to whole pieces" in egg_change.reason


def test_counted_item_never_rounds_down_to_zero():
    result = apply_rules(sauerbraten(), [ScaleServings(1)])
    assert by_id(result, "egg").quantity.value == 1


def test_ranges_scale_at_both_ends():
    flour = by_id(apply_rules(sauerbraten(), [ScaleServings(6)]), "flour").quantity
    assert (flour.value, flour.max_value) == (3, 4.5)


def test_to_taste_amounts_are_left_alone_and_explained():
    result = apply_rules(sauerbraten(), [ScaleServings(6)])
    assert by_id(result, "salt").quantity.kind is QuantityKind.TO_TASTE
    note = next(c for c in result.changes if c.target == "amounts not given")
    assert "Salz" in note.before


def test_times_are_not_scaled_and_the_cook_is_told():
    result = apply_rules(sauerbraten(), [ScaleServings(6)])
    assert result.recipe.steps[0].duration.min_minutes == 60
    assert any(c.target == "times" for c in result.changes)


def test_big_change_warns_about_pot_size():
    assert any(c.target == "tools" for c in apply_rules(sauerbraten(), [ScaleServings(8)]).changes)
    assert not any(c.target == "tools" for c in apply_rules(sauerbraten(), [ScaleServings(5)]).changes)


def test_new_servings_say_they_come_from_a_rule_built_on_an_inference():
    servings = apply_rules(sauerbraten(), [ScaleServings(6)]).recipe.servings
    assert servings.value == 6
    assert servings.source.status is SourceStatus.RULE
    assert "inferred" in servings.source.note


def test_scaling_keeps_the_original_evidence_of_each_amount():
    vinegar = by_id(apply_rules(sauerbraten(), [ScaleServings(6)]), "vinegar")
    assert vinegar.source.status is SourceStatus.READ
    assert vinegar.quantity.raw == "½ l"


def test_same_servings_changes_nothing():
    result = apply_rules(sauerbraten(), [ScaleServings(4)])
    assert result.recipe == result.original
    assert result.changes == ()


def test_unknown_servings_need_an_assumption():
    unknown = recipe(servings=Servings(source=read("x").model_copy(update={"status": SourceStatus.MISSING, "quote": None})))
    with pytest.raises(ManipulationError, match="assume-servings"):
        apply_rules(unknown, [ScaleServings(6)])
    scaled = apply_rules(unknown, [ScaleServings(6, assume_base=3)]).recipe
    assert scaled.servings.value == 6
    assert "assumed by the user" in scaled.servings.source.note


def test_scaling_is_reproducible():
    first = apply_rules(sauerbraten(), [ScaleServings(6)])
    second = apply_rules(sauerbraten(), [ScaleServings(6)])
    assert first == second


def test_original_is_never_modified():
    original = sauerbraten()
    apply_rules(original, [ScaleServings(6)])
    assert original.ingredients[0].quantity.value == 0.5


def test_servings_must_be_positive():
    with pytest.raises(ManipulationError):
        ScaleServings(0)
