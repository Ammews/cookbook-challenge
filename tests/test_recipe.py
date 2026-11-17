import pytest
from pydantic import ValidationError

from cookbook.models import Recipe, Servings, Source, SourceStatus
from factories import ingredient, inferred, read, recipe, step, tool


def test_valid_recipe_builds():
    assert recipe().title == "Sauerbraten"


def test_duplicate_ingredient_ids_are_rejected():
    with pytest.raises(ValidationError, match="duplicate ingredient id"):
        recipe(ingredients=(ingredient("onion"), ingredient("onion")))


def test_duplicate_tool_ids_are_rejected():
    with pytest.raises(ValidationError, match="duplicate tool id"):
        recipe(tools=(tool("pot"), tool("pot")))


def test_step_cannot_use_an_ingredient_that_is_not_listed():
    with pytest.raises(ValidationError, match="step 1 ingredient refers to unknown id"):
        recipe(steps=(step(ingredient_ids=("bacon",)),))


def test_step_cannot_use_a_tool_that_is_not_listed():
    with pytest.raises(ValidationError, match="step 1 tool refers to unknown id"):
        recipe(steps=(step(tool_ids=("oven",)),))


def test_steps_must_be_numbered_in_sequence():
    with pytest.raises(ValidationError, match="step orders must be"):
        recipe(steps=(step(1), step(3)))


def test_ids_must_be_slugs():
    with pytest.raises(ValidationError):
        ingredient("Red Wine")


def test_tool_is_stated_only_when_read_from_the_text():
    assert tool().stated
    assert not tool("knife", source=inferred("onions are sliced")).stated


def test_inferred_servings_are_flagged():
    assert recipe().servings.inferred
    assert not Servings(value=4, source=read("für 4 Personen")).inferred


def test_missing_servings_cannot_have_a_value():
    with pytest.raises(ValidationError, match="cannot have a value"):
        Servings(value=4, source=Source(status=SourceStatus.MISSING))


def test_servings_need_a_value_unless_missing():
    with pytest.raises(ValidationError, match="need a value"):
        Servings(source=inferred())


def test_models_are_immutable():
    with pytest.raises(ValidationError):
        recipe().title = "Other"


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        recipe(calories=500)


def test_recipe_survives_a_json_round_trip():
    original = recipe()
    assert Recipe.model_validate_json(original.model_dump_json()) == original
