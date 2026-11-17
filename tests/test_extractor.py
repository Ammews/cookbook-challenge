from cookbook.extract import Extractor, ModelReply
from cookbook.extract.schema import (
    WireExtraction,
    WireIngredient,
    WireQuantity,
    WireServings,
    WireStep,
    WireTool,
)
from cookbook.models import Document, InputKind, LlmUsage, Page, QuantityKind, ReadMethod, SourceStatus

TEXT = "Zum Einlegen kocht man ½ l Essig und 4 Zwiebeln im Topf. Dazu reicht man Brot."
DOCUMENT = Document(
    name="r.txt", kind=InputKind.TEXT, pages=(Page(number=1, text=TEXT, method=ReadMethod.PLAIN_TEXT),)
)


def quantity(kind="exact", value=0.0, unit="", raw=""):
    return WireQuantity(kind=kind, value=value, max_value=0, unit=unit, raw=raw)


def wire_ingredient(id="onion", quote="4 Zwiebeln", value=4.0, evidence="read", note="", kind="exact"):
    return WireIngredient(
        id=id, name=id, name_original="Zwiebeln", quantity=quantity(kind, value),
        preparation="", optional=False, is_intermediate=False, animal="none",
        evidence=evidence, page=1, quote=quote, note=note,
    )


def wire(ingredients=None, steps=None, is_recipe=True, servings=None, tools=None, recipes=1):
    return WireExtraction(
        is_recipe=is_recipe,
        recipes_in_document=recipes,
        title="Marinade",
        language="de",
        servings=servings or WireServings(value=4, evidence="inferred", page=0, quote="", note="1 l covers 1 kg"),
        ingredients=ingredients if ingredients is not None else [wire_ingredient()],
        tools=tools or [WireTool(id="pot", name="pot", stated=True, page=1, quote="im Topf", note="")],
        steps=steps if steps is not None else [
            WireStep(
                text="Zwiebeln kochen.", ingredient_ids=["onion"], tool_ids=["pot"], duration_raw="",
                duration_min_minutes=0, duration_max_minutes=0, condition="", page=1, quote="kocht man",
            )
        ],
        warnings=[],
    )


class ScriptedModel:
    """Returns the scripted answers in order and records the prompts it got."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def extract(self, messages):
        self.prompts.append(messages[-1]["content"])
        usage = LlmUsage(model="fake", input_tokens=10, output_tokens=5, seconds=0.1)
        return ModelReply(extraction=self.answers.pop(0), usage=usage)


def test_grounded_answer_is_accepted_in_one_call():
    model = ScriptedModel(wire())
    result = Extractor(model).extract(DOCUMENT)

    assert len(model.prompts) == 1
    assert result.problems_found == ()
    onion = result.recipe.ingredients[0]
    assert onion.source.status is SourceStatus.READ
    assert onion.quantity.value == 4


def test_invented_quote_triggers_one_correction_round():
    bad = wire([wire_ingredient(quote="5 große Zwiebeln", value=5)])
    model = ScriptedModel(bad, wire())

    result = Extractor(model).extract(DOCUMENT)

    assert len(model.prompts) == 2
    assert "not in the document" in model.prompts[1]
    assert result.problems_left == ()
    assert result.recipe.ingredients[0].quantity.value == 4
    assert len(result.usage) == 2


def test_problem_still_there_after_correction_is_demoted_and_warned():
    bad = wire([wire_ingredient(quote="5 große Zwiebeln", value=5)])
    result = Extractor(ScriptedModel(bad, bad)).extract(DOCUMENT)

    onion = result.recipe.ingredients[0]
    assert onion.source.status is SourceStatus.INFERRED
    assert "not in the document" in onion.source.note
    assert result.problems_left
    assert any("remained" in w.message for w in result.recipe.warnings)


def test_number_missing_from_its_own_quote_is_caught():
    lying = wire([wire_ingredient(quote="4 Zwiebeln", value=6)])
    result = Extractor(ScriptedModel(lying, lying)).extract(DOCUMENT)

    assert any("does not appear in its quote" in p for p in result.problems_found)
    assert result.recipe.ingredients[0].source.status is SourceStatus.INFERRED


def test_number_on_a_vague_amount_is_dropped():
    vague = wire([wire_ingredient(kind="vague", value=3)])
    result = Extractor(ScriptedModel(vague, vague)).extract(DOCUMENT)

    quantity = result.recipe.ingredients[0].quantity
    assert quantity.kind is QuantityKind.VAGUE
    assert quantity.value is None


def test_step_pointing_to_unknown_ingredient_is_a_problem_and_the_link_is_dropped():
    step = WireStep(
        text="Fleisch dazu.", ingredient_ids=["onion", "beef"], tool_ids=[], duration_raw="",
        duration_min_minutes=0, duration_max_minutes=0, condition="", page=1, quote="kocht man",
    )
    answer = wire(steps=[step])
    result = Extractor(ScriptedModel(answer, answer)).extract(DOCUMENT)

    assert any("'beef'" in p for p in result.problems_found)
    assert result.recipe.steps[0].ingredient_ids == ("onion",)


def test_not_a_recipe_yields_no_recipe():
    result = Extractor(ScriptedModel(wire(is_recipe=False, ingredients=[], steps=[]))).extract(DOCUMENT)

    assert not result.is_recipe
    assert result.recipe is None
    assert result.recipes_in_document == 0


def test_inferred_servings_keep_their_reasoning():
    result = Extractor(ScriptedModel(wire())).extract(DOCUMENT)

    servings = result.recipe.servings
    assert servings.inferred and servings.value == 4
    assert "1 l covers 1 kg" in servings.source.note


def test_stated_servings_without_the_number_in_the_quote_become_inferred():
    servings = WireServings(value=8, evidence="read", page=1, quote="Zum Einlegen", note="")
    result = Extractor(ScriptedModel(wire(servings=servings), wire(servings=servings))).extract(DOCUMENT)

    assert result.recipe.servings.source.status is SourceStatus.INFERRED


def test_ids_are_made_valid_and_unique():
    answer = wire(
        [
            wire_ingredient(id="Red Wine", quote="½ l Essig", value=0.5).model_copy(
                update={"name": "vinegar", "name_original": "Essig"}
            ),
            wire_ingredient(id="Red Wine"),
        ],
        steps=[],
    )
    result = Extractor(ScriptedModel(answer, answer)).extract(DOCUMENT)

    assert [i.id for i in result.recipe.ingredients] == ["red_wine", "red_wine_2"]


def test_implied_tool_is_inferred_and_stated_tool_is_read():
    tools = [
        WireTool(id="pot", name="pot", stated=True, page=1, quote="im Topf", note=""),
        WireTool(id="knife", name="knife", stated=False, page=0, quote="", note="onions are sliced"),
    ]
    result = Extractor(ScriptedModel(wire(tools=tools))).extract(DOCUMENT)

    pot, knife = result.recipe.tools
    assert pot.stated and pot.source.note is None
    assert not knife.stated and knife.source.note == "onions are sliced"


def named(id, name, original, kind="absent", value=0.0, raw="", quote="Zwiebeln", optional=False):
    return WireIngredient(
        id=id, name=name, name_original=original,
        quantity=WireQuantity(kind=kind, value=value, max_value=0, unit="", raw=raw),
        preparation="", optional=optional, is_intermediate=False, animal="none",
        evidence="read", page=1, quote=quote, note="",
    )


def test_ingredient_listed_twice_is_merged_and_reported():
    answer = wire(
        [
            named("raisins", "raisins", "Rosinen", quote="Zwiebeln"),
            named("raisins_again", "raisins", "Rosinen", quote="Zwiebeln"),
        ],
        steps=[],
    )
    recipe = Extractor(ScriptedModel(answer)).extract(DOCUMENT).recipe

    assert [i.name_original for i in recipe.ingredients] == ["Rosinen"]
    assert any("listed twice" in w.message for w in recipe.warnings)


def test_merge_keeps_the_most_precise_amount_and_repoints_steps():
    answer = wire(
        [
            named("salt", "salt", "Salt to taste", kind="to_taste"),
            named("salt_cooking", "salt", "salt", kind="exact", value=4, raw="4", quote="4 Zwiebeln"),
            wire_ingredient(),
        ],
        steps=[
            WireStep(
                text="Salzen.", ingredient_ids=["salt_cooking"], tool_ids=[], duration_raw="",
                duration_min_minutes=0, duration_max_minutes=0, condition="", page=1, quote="kocht man",
            )
        ],
    )
    recipe = Extractor(ScriptedModel(answer)).extract(DOCUMENT).recipe

    salt = recipe.ingredients[0]
    assert len(recipe.ingredients) == 2
    assert salt.quantity.value == 4
    assert recipe.steps[0].ingredient_ids == (salt.id,)


def test_merged_ingredient_is_optional_only_if_both_were():
    answer = wire(
        [named("a", "apple", "Äpfel", optional=True), named("b", "apple", "Apfel", optional=False)],
        steps=[],
    )
    recipe = Extractor(ScriptedModel(answer)).extract(DOCUMENT).recipe
    assert recipe.ingredients[0].optional is False


def test_different_ingredients_with_similar_names_are_not_merged():
    answer = wire(
        [named("currants", "currants", "Korinthen"), named("raisins", "raisins", "Rosinen")],
        steps=[],
    )
    assert len(Extractor(ScriptedModel(answer)).extract(DOCUMENT).recipe.ingredients) == 2


def test_animal_content_is_carried_into_the_recipe():
    from cookbook.models import AnimalContent

    pesto = named("pesto", "pesto", "pesto").model_copy(update={"animal": "dairy"})
    recipe = Extractor(ScriptedModel(wire([pesto], steps=[]))).extract(DOCUMENT).recipe
    assert recipe.ingredients[0].animal is AnimalContent.DAIRY
