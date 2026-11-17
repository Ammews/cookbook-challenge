from cookbook.extract import Extraction
from cookbook.manipulate import MakeVegan, ScaleServings, apply_rules
from cookbook.models import Document, InputKind, LlmUsage, Page, Quantity, QuantityKind, ReadMethod, Servings
from cookbook.output import render_markdown
from cookbook.pipeline import PipelineResult
from factories import exact, ingredient, inferred, read, recipe, step

USAGE = LlmUsage(model="claude-haiku-5-5", input_tokens=1_000_000, output_tokens=0, seconds=2, cached=True)
DOCUMENT = Document(
    name="r.pdf", kind=InputKind.PDF, pages=(Page(number=1, text="x", method=ReadMethod.VISION, usage=USAGE),)
)


def sample():
    return recipe(
        servings=Servings(value=4, source=inferred("1 l marinade for 1 kg meat")),
        ingredients=(
            ingredient("onion", name="onion", name_original="Zwiebeln", quantity=exact(4)),
            ingredient("wine", name="red wine", name_original="Rotwein", quantity=Quantity(kind=QuantityKind.ABSENT)),
            ingredient("butter", name="butter", name_original="Butter", quantity=Quantity(kind=QuantityKind.ABSENT)),
            ingredient("apple", name="apple", name_original="Äpfel", optional=True,
                       quantity=Quantity(kind=QuantityKind.VAGUE, raw="einige"), source=read("einige Äpfel")),
        ),
        steps=(step(ingredient_ids=("onion", "butter"), tool_ids=("pot",)),),
    )


def result(rules=()):
    extracted = sample()
    extraction = Extraction(is_recipe=True, recipes_in_document=1, recipe=extracted, usage=())
    manipulation = apply_rules(extracted, rules) if rules else None
    return PipelineResult(document=DOCUMENT, extraction=extraction, manipulation=manipulation)


def test_every_ingredient_shows_where_it_came_from():
    page = render_markdown(result())
    assert "read, p. 1: “4 in Scheiben geschnittene Zwiebeln”" in page
    assert "some (einige)" in page
    assert "*[optional]*" in page


def test_guessed_servings_are_flagged_for_review():
    page = render_markdown(result())
    assert "**guessed**: 1 l marinade for 1 kg meat" in page
    assert "## Check before cooking" in page


def test_scaled_amounts_say_they_changed_and_keep_their_evidence():
    page = render_markdown(result([ScaleServings(6)]))
    assert "| 6 | Zwiebeln (onion) | **changed** (scaled); read" in page
    assert "## What changed against the original" in page


def test_vegan_check_is_not_reported_as_scaling():
    page = render_markdown(result([MakeVegan(), ScaleServings(6)]))
    wine_row = next(line for line in page.splitlines() if line.startswith("| amount not given | Rotwein"))
    assert "**check** (vegan" in wine_row
    assert "(scaled)" not in wine_row


def test_cost_is_shown_even_when_the_calls_came_from_the_cache():
    assert "cost: $0.1000" in render_markdown(result())


def test_not_a_recipe_says_so_and_invents_nothing():
    extraction = Extraction(is_recipe=False, recipes_in_document=0, recipe=None, usage=())
    page = render_markdown(PipelineResult(document=DOCUMENT, extraction=extraction))
    assert "not a recipe" in page
    assert "## Ingredients" not in page


def test_amount_text_is_not_repeated_when_it_says_the_same_thing():
    from cookbook.formatting import format_amount

    assert format_amount(Quantity(kind=QuantityKind.TO_TASTE, raw="to taste")) == "to taste"
    assert format_amount(Quantity(kind=QuantityKind.VAGUE, raw="einige")) == "some (einige)"


def test_converted_amounts_are_marked():
    from cookbook.manipulate import ConvertToMetric

    page = render_markdown(result([ScaleServings(6), ConvertToMetric()]))
    assert "**changed** (scaled)" in page
