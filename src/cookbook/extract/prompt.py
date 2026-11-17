"""Prompts for the extraction model. Bump PROMPT_VERSION when they change."""

from cookbook.models import Document

PROMPT_VERSION = "4"

SYSTEM_PROMPT = """\
You turn the text of a document into a structured recipe. A program checks your answer \
against the document afterwards, so precision matters more than completeness.

What to extract
- Extract exactly one recipe. If the document holds several, extract the first complete one, \
set recipes_in_document to how many there are, and add a warning naming the ones you skipped.
- If the document is not a recipe (a shopping list, an article, a menu), set is_recipe to false \
and leave ingredients, tools and steps empty.
- Ignore sections that are not the recipe itself: notes, tips, variations, serving suggestions, \
lists of side dishes. Ingredients named only there are NOT ingredients.
- Text listed under "not running text" (labels inside drawings, headers, page numbers) is never \
evidence for an ingredient.

Ingredients
- One entry per ingredient. If an ingredient appears several times, keep one entry.
- Never invent an amount. If the text gives no number, use kind vague (some, a little), \
to_taste (seasoning, "as much as needed until ...") or absent (no amount at all), with value null.
- For exact amounts copy the number and the unit exactly as written ("½ l" is value 0.5, unit "l"). \
Do not convert units. For one amount written in several units, use the first one.
- For a range like "2–3" use value 2 and max_value 3.
- optional is true only when the text says the ingredient may be added or left out.
- is_intermediate is true for something the recipe itself makes and then uses (a marinade, \
pan juices, a dough made in an earlier step).

Animal content
- For every ingredient, set animal to what it contains of animal origin. The question is what it contains, not where it comes from.
- none: no animal product (vegetables, fruit, grains, nuts, plant oils, plant milks such as coconut or almond milk, mushrooms, salt, water, sugar, wine, vinegar).
- meat: meat of mammals and anything made from it (bacon, ham, sausage, lard, meat stock, meat juices).
- poultry: chicken, duck, turkey and anything made from them (chicken stock).
- fish: fish and seafood and anything made from them (anchovies, fish sauce, Worcestershire sauce).
- dairy: milk and anything made from it (butter, cream, cheese, yogurt, ghee, quark), and products that contain it (pesto with cheese, milk chocolate).
- egg: eggs and products that contain them (mayonnaise, egg noodles).
- honey, gelatin: as named.
- other_animal: any other animal product.
- uncertain: it depends on the brand or recipe and you cannot tell (bread, puff pastry, stock cubes).

Evidence
- evidence "read": you copy a quote, the shortest verbatim span of the document that mentions \
the item and its amount. Copy it character for character, including old spelling.
- evidence "inferred": not written but deduced; explain why in note.
- evidence "missing": not given at all.
- Servings: read them only if the text states them. If not, infer a plausible number from the \
amounts (for example how much meat a litre of marinade covers) with evidence "inferred" and the \
reasoning in note. Use "missing" only if nothing in the recipe allows an estimate.
- A field that does not apply is "" for text and 0 for numbers. Never mention this answer format \
in warnings.

Tools
- Appliances count as tools: an oven the text says to preheat, a blender, a mixer.
- stated true only if the text names the tool. Add implied tools (a knife to slice, a bowl to mix) \
with stated false and note naming the step that needs them.

Steps
- Keep the order of the document. One step per action or short group of actions.
- Write each step in the document's language, close to the original wording.
- quote: verbatim span of the document the step comes from.
- Link each step to the ingredient ids and tool ids it uses.
- Record durations and conditions ("if used after 8 days") where the text gives them.

Warnings
- Add a warning for anything a reviewer should check: words marked uncertain by the transcription, \
ambiguous amounts, recipes you skipped, anything you had to guess.
"""


def document_prompt(document: Document) -> str:
    parts = [f"Document: {document.name}"]
    for page in document.pages:
        parts.append(f"\n=== Page {page.number} (read by: {page.method.value}) ===\n{page.text}")
        if page.decoration_text:
            parts.append("Not running text on this page: " + " | ".join(page.decoration_text))
        if page.uncertain:
            parts.append("Words the transcription was unsure about: " + ", ".join(page.uncertain))
    parts.append("\nExtract the recipe.")
    return "\n".join(parts)


def correction_prompt(problems: list[str], previous_answer_json: str) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    return (
        "A program checked your previous answer against the document and found these problems:\n"
        f"{listed}\n\n"
        "Fix them and return the complete corrected answer. If a quote cannot be found, copy the "
        "exact words from the document, or mark the item inferred with a reason. If a number is not "
        "in the text, do not keep it.\n\n"
        f"Your previous answer:\n{previous_answer_json}"
    )
