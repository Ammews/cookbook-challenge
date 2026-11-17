"""Turn a pipeline result into plain data the web page can show as is.

All wording and formatting decisions stay in Python (shared with the
Markdown output), so the page only lays things out and holds no recipe logic.
"""

from cookbook.formatting import format_amount
from cookbook.models import Recipe, Source, SourceStatus
from cookbook.output import render_markdown
from cookbook.pipeline import PipelineResult
from cookbook.pricing import total_cost_usd


def build_view(result: PipelineResult) -> dict:
    usage = result.usage
    first_run_cost = total_cost_usd(u.model_copy(update={"cached": False}) for u in usage)
    view = {
        "document": {
            "name": result.document.name,
            "pages": len(result.document.pages),
            "read_by": sorted({p.method.value for p in result.document.pages}),
        },
        "usage": {
            "models": sorted({u.model for u in usage}),
            "calls": len(usage),
            "cached_calls": sum(u.cached for u in usage),
            "input_tokens": sum(u.input_tokens for u in usage),
            "output_tokens": sum(u.output_tokens for u in usage),
            "seconds": round(sum(u.seconds for u in usage), 1),
            "cost_usd": first_run_cost,
        },
        "check": {
            "problems_found": list(result.extraction.problems_found),
            "problems_left": list(result.extraction.problems_left),
        },
        "is_recipe": result.extraction.is_recipe and result.recipe is not None,
        "recipes_in_document": result.extraction.recipes_in_document,
        "markdown": render_markdown(result),
    }
    if not view["is_recipe"]:
        return view

    recipe = result.recipe
    changes = result.manipulation.changes if result.manipulation else ()
    scaled = {c.target for c in changes if c.rule == "scale"}
    flagged = {c.target for c in changes if c.rule == "vegan" and c.after.startswith("unchanged")}
    view["recipe"] = {
        "title": recipe.title,
        "language": recipe.language,
        "servings": _servings(recipe),
        "ingredients": [
            {
                "amount": format_amount(i.quantity),
                "name": i.name_original,
                "english": i.name if i.name.lower() not in i.name_original.lower() else None,
                "preparation": (
                    i.preparation
                    if i.preparation and i.preparation.lower() not in i.name_original.lower()
                    else None
                ),
                "optional": i.optional,
                "intermediate": i.is_intermediate,
                "source": _source(i.source),
                "scaled": i.id in scaled,
                "vegan_check": i.id in flagged,
            }
            for i in recipe.ingredients
        ],
        "tools": [
            {"name": t.name, "stated": t.stated, "note": None if t.stated else t.source.note}
            for t in recipe.tools
        ],
        "steps": [
            {
                "order": s.order,
                "text": s.text,
                "condition": s.condition,
                "duration": s.duration.raw if s.duration else None,
                "uses": [_name(recipe, i) for i in s.ingredient_ids],
            }
            for s in recipe.steps
        ],
        "changes": [c.model_dump() for c in changes],
        "warnings": [w.message for w in recipe.warnings],
    }
    return view


def _servings(recipe: Recipe) -> dict:
    servings = recipe.servings
    return {"value": servings.value, "source": _source(servings.source)}


def _source(source: Source) -> dict:
    kind = {
        SourceStatus.READ: "read",
        SourceStatus.INFERRED: "guessed",
        SourceStatus.MISSING: "not given",
        SourceStatus.RULE: "changed",
    }[source.status]
    text = source.quote if source.status is SourceStatus.READ else source.note
    return {"kind": kind, "page": source.page, "text": text}


def _name(recipe: Recipe, ingredient_id: str) -> str:
    return next((i.name for i in recipe.ingredients if i.id == ingredient_id), ingredient_id)
