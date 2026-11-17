"""Stage 4: render a pipeline result as a Markdown page a person can cook from.

Every ingredient line says where its value came from, so the cook can tell
what was read from the page, what was guessed, and what a rule changed.
"""

from cookbook.formatting import format_amount
from cookbook.models import Ingredient, Recipe, Source, SourceStatus
from cookbook.pipeline import PipelineResult
from cookbook.pricing import total_cost_usd

LEGEND = (
    "**Source column:** *read* = written in the document (with the page and the exact words); "
    "*guessed* = not written, deduced by the model, with its reasoning; "
    "*not given* = the document does not say; *changed* = set by a rule (scaling, vegan)."
)


def render_markdown(result: PipelineResult) -> str:
    if not result.extraction.is_recipe or result.recipe is None:
        return _not_a_recipe(result)

    recipe = result.recipe
    changes = result.manipulation.changes if result.manipulation else ()
    scaled_ids = {c.target for c in changes if c.rule == "scale"}
    flagged = {c.target: c.after for c in changes if c.rule == "vegan" and c.after.startswith("unchanged")}
    lines = [f"# {recipe.title}", "", _header(result), "", _servings(recipe), "", LEGEND, ""]

    lines += ["## Ingredients", "", "| Amount | Ingredient | Source |", "| --- | --- | --- |"]
    for ingredient in recipe.ingredients:
        lines.append(
            f"| {_cell(format_amount(ingredient.quantity))} "
            f"| {_cell(_ingredient_label(ingredient))} "
            f"| {_cell(_source_label(ingredient.source, ingredient.id in scaled_ids, ingredient.id in flagged))} |"
        )

    if recipe.tools:
        lines += ["", "## Tools", ""]
        for tool in recipe.tools:
            how = "named in the recipe" if tool.stated else f"implied: {tool.source.note}"
            lines.append(f"- {tool.name} ({how})")

    names = {i.id: i.name for i in recipe.ingredients}
    tools = {t.id: t.name for t in recipe.tools}
    lines += ["", "## Method", ""]
    for step in recipe.steps:
        lines.append(f"{step.order}. {_indent(step.text)}")
        details = []
        if step.condition:
            details.append(f"only if: {step.condition}")
        if step.duration:
            details.append(f"time: {step.duration.raw}")
        if step.ingredient_ids:
            details.append("uses: " + ", ".join(names.get(i, i) for i in step.ingredient_ids))
        if step.tool_ids:
            details.append("with: " + ", ".join(tools.get(t, t) for t in step.tool_ids))
        if details:
            lines.append(f"   *{'; '.join(details)}*")

    if result.manipulation and result.manipulation.changes:
        lines += ["", "## What changed against the original", "", "| Rule | What | Before | After | Why |", "| --- | --- | --- | --- | --- |"]
        for change in result.manipulation.changes:
            lines.append(
                f"| {change.rule} | {_cell(change.target)} | {_cell(change.before)} "
                f"| {_cell(change.after)} | {_cell(change.reason)} |"
            )

    review = _review_items(recipe)
    if review:
        lines += ["", "## Check before cooking", ""] + [f"- {item}" for item in review]

    return "\n".join(lines) + "\n"


def _header(result: PipelineResult) -> str:
    document = result.document
    methods = sorted({p.method.value for p in document.pages})
    usage = result.usage
    # Price every call as if it were made now: a cached call cost money the first time.
    first_run = total_cost_usd(u.model_copy(update={"cached": False}) for u in usage)
    seconds = sum(u.seconds for u in usage)
    models = sorted({u.model for u in usage})
    parts = [
        f"Source file: `{document.name}` ({len(document.pages)} page(s), read by {', '.join(methods)})",
        f"models: {', '.join(models) or 'none'}",
        f"{len(usage)} model call(s), {sum(u.input_tokens for u in usage)} tokens in / "
        f"{sum(u.output_tokens for u in usage)} out, {seconds:.0f} s",
        f"cost: {'unknown' if first_run is None else f'${first_run:.4f}'} (repeat runs are served from the cache for $0)",
    ]
    extraction = result.extraction
    if extraction.problems_found:
        parts.append(
            f"code check found {len(extraction.problems_found)} problem(s) in the first answer, "
            f"{len(extraction.problems_left)} left after correction"
        )
    return "*" + " · ".join(parts) + "*"


def _servings(recipe: Recipe) -> str:
    servings = recipe.servings
    if servings.value is None:
        return "**Serves:** not stated in the recipe."
    return f"**Serves:** {servings.value} ({_source_label(servings.source, False)})"


def _ingredient_label(ingredient: Ingredient) -> str:
    label = ingredient.name_original
    if ingredient.name.lower() not in ingredient.name_original.lower():
        label += f" ({ingredient.name})"
    if ingredient.preparation and ingredient.preparation.lower() not in label.lower():
        label += f", {ingredient.preparation}"
    tags = []
    if ingredient.optional:
        tags.append("optional")
    if ingredient.is_intermediate:
        tags.append("made in the recipe")
    return label + (f" *[{', '.join(tags)}]*" if tags else "")


def _source_label(source: Source, scaled: bool, flagged: bool = False) -> str:
    page = f", p. {source.page}" if source.page else ""
    if source.status is SourceStatus.READ:
        label = f"read{page}: “{source.quote}”"
    elif source.status is SourceStatus.INFERRED:
        label = f"**guessed**: {source.note}"
    elif source.status is SourceStatus.MISSING:
        label = "not given" + (f": {source.note}" if source.note else "")
    else:
        label = f"**changed**: {source.note}"
    if scaled and source.status is not SourceStatus.RULE:
        label = "**changed** (scaled); " + label
    if flagged:
        label = "**check** (vegan, see below); " + label
    return label


def _review_items(recipe: Recipe) -> list[str]:
    items = [w.message for w in recipe.warnings]
    guessed = [i.name_original for i in recipe.ingredients if i.source.status is SourceStatus.INFERRED]
    if guessed:
        items.append("Guessed, not read: " + ", ".join(guessed) + ".")
    if recipe.servings.source.status is SourceStatus.INFERRED:
        items.append(f"The number of servings is a guess: {recipe.servings.source.note}")
    return items


def _not_a_recipe(result: PipelineResult) -> str:
    return (
        f"# {result.document.name}\n\n{_header(result)}\n\n"
        "**This document is not a recipe.** Nothing was extracted, so nothing is invented.\n"
    )


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _indent(text: str) -> str:
    return text.replace("\n", "\n   ")
