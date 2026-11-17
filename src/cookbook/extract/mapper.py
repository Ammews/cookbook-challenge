"""Turn the model's wire answer into domain objects, checking it against the document.

`find_problems` lists everything wrong with an answer, so it can be sent back
to the model. `to_recipe` always produces a valid recipe: whatever is still
wrong is repaired conservatively (an unsupported "read" becomes "inferred",
an invented number is dropped from the evidence) and reported as a warning,
so nothing wrong is ever presented as read from the page.
"""

import re

from cookbook.extract.grounding import number_supported, quote_in_text
from cookbook.extract.schema import WireExtraction, WireIngredient, WireQuantity, WireStep
from cookbook.models import (
    AnimalContent,
    Duration,
    Ingredient,
    Quantity,
    QuantityKind,
    Recipe,
    ReviewWarning,
    Servings,
    Source,
    SourceStatus,
    Step,
    Tool,
)


def find_problems(wire: WireExtraction, text: str) -> list[str]:
    """Everything a corrected answer should fix. Empty means the answer is grounded."""
    if not wire.is_recipe:
        return []
    problems: list[str] = []
    for item in wire.ingredients:
        problems += _evidence_problems(f"ingredient '{item.id}'", item.evidence, item.quote, item.note, text)
        problems += _quantity_problems(item, text)
    for tool in wire.tools:
        if tool.stated:
            problems += _evidence_problems(f"tool '{tool.id}'", "read", tool.quote, tool.note, text)
    for number, step in enumerate(wire.steps, start=1):
        if not quote_in_text(step.quote, text):
            problems.append(f"step {number}: quote {step.quote!r} is not in the document")
    servings = wire.servings
    problems += _evidence_problems("servings", servings.evidence, servings.quote, servings.note, text)
    if servings.evidence == "read" and servings.value > 0 and servings.quote:
        if not number_supported(servings.value, servings.quote):
            problems.append(f"servings: {servings.value} does not appear in its quote {servings.quote!r}")
    ids = {i.id for i in wire.ingredients}
    tool_ids = {t.id for t in wire.tools}
    for number, step in enumerate(wire.steps, start=1):
        for missing in sorted(set(step.ingredient_ids) - ids):
            problems.append(f"step {number} uses ingredient id '{missing}', which is not in the ingredient list")
        for missing in sorted(set(step.tool_ids) - tool_ids):
            problems.append(f"step {number} uses tool id '{missing}', which is not in the tool list")
    return problems


def to_recipe(wire: WireExtraction, text: str) -> Recipe:
    warnings = [ReviewWarning(message=w) for w in wire.warnings if w.strip()]
    kept, aliases = merge_duplicates(wire.ingredients, warnings)
    ingredient_ids = _unique_slugs([i.id or i.name for i in kept])
    tool_ids = _unique_slugs([t.id or t.name for t in wire.tools])
    ingredient_map = {w.id: new for w, new in zip(kept, ingredient_ids)}
    ingredient_map.update({dup: ingredient_map[target] for dup, target in aliases.items() if target in ingredient_map})
    tool_map = {w.id: new for w, new in zip(wire.tools, tool_ids)}

    ingredients = tuple(
        _ingredient(item, new_id, text, warnings) for item, new_id in zip(kept, ingredient_ids)
    )
    tools = tuple(
        Tool(
            id=new_id,
            name=tool.name or new_id,
            source=_source(
                f"tool '{new_id}'",
                "read" if tool.stated else "inferred",
                tool.page,
                tool.quote,
                None if tool.stated else (tool.note or "implied by the method"),
                text,
                warnings,
            ),
        )
        for tool, new_id in zip(wire.tools, tool_ids)
    )
    steps = tuple(
        _step(number, step, ingredient_map, tool_map, text, warnings)
        for number, step in enumerate(wire.steps, start=1)
    )
    return Recipe(
        title=wire.title.strip() or "Untitled recipe",
        language=wire.language.strip() or "unknown",
        servings=_servings(wire, text, warnings),
        ingredients=ingredients,
        tools=tools,
        steps=steps,
        warnings=tuple(warnings),
    )


# --- duplicates ------------------------------------------------------------

_KIND_RANK = {"exact": 0, "vague": 1, "to_taste": 2, "absent": 3}


def merge_duplicates(
    items: list[WireIngredient], warnings: list[ReviewWarning]
) -> tuple[list[WireIngredient], dict[str, str]]:
    """Merge ingredients that are the same thing listed twice.

    Two entries are the same ingredient when their original or English names
    are equal after normalising case, spacing and long s ("Salz" and "salz",
    "salt" and "Salt"). The entry with the most precise amount is kept (a
    number beats "to taste"); it is optional only if both were. Steps that
    used the dropped entry are pointed at the kept one, and a warning says
    what was merged, so nothing disappears silently.

    Returns the kept entries and a map from dropped id to kept id.
    """
    kept: list[WireIngredient] = []
    aliases: dict[str, str] = {}
    for item in items:
        match = next((k for k in kept if _same_ingredient(k, item)), None)
        if match is None:
            kept.append(item)
            continue
        best = min((match, item), key=lambda i: _KIND_RANK[i.quantity.kind])
        merged = best.model_copy(
            update={
                "id": match.id,
                "optional": match.optional and item.optional,
                "is_intermediate": match.is_intermediate or item.is_intermediate,
            }
        )
        kept[kept.index(match)] = merged
        if item.id != match.id:
            aliases[item.id] = match.id
        warnings.append(
            ReviewWarning(
                message=f"'{item.name_original}' was listed twice; merged into one ingredient "
                f"(kept the amount '{best.quantity.raw or best.quantity.kind}').",
                target_id=match.id,
            )
        )
    return kept, aliases


def _same_ingredient(a: WireIngredient, b: WireIngredient) -> bool:
    return bool(
        (_key(a.name_original) and _key(a.name_original) == _key(b.name_original))
        or (_key(a.name) and _key(a.name) == _key(b.name))
    )


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.lower().replace("ſ", "s")).strip()


# --- problems --------------------------------------------------------------


def _evidence_problems(label: str, evidence: str, quote: str | None, note: str | None, text: str) -> list[str]:
    if evidence == "read":
        if not quote or not quote.strip():
            return [f"{label}: marked read but has no quote"]
        if not quote_in_text(quote, text):
            return [f"{label}: quote {quote!r} is not in the document"]
    if evidence == "inferred" and not (note and note.strip()):
        return [f"{label}: marked inferred but gives no reason in note"]
    return []


def _quantity_problems(item: WireIngredient, text: str) -> list[str]:
    q = item.quantity
    label = f"ingredient '{item.id}'"
    if q.kind == "exact" and q.value <= 0:
        return [f"{label}: kind exact but no value"]
    if q.kind != "exact" and q.value > 0:
        return [f"{label}: kind {q.kind} cannot have a value; use exact or drop the number"]
    if q.kind == "exact" and item.evidence == "read" and item.quote:
        missing = [v for v in (q.value, q.max_value) if v > 0 and not number_supported(v, item.quote)]
        if missing:
            return [f"{label}: amount {missing} does not appear in its quote {item.quote!r}"]
    return []


# --- repair ----------------------------------------------------------------


def _ingredient(item: WireIngredient, new_id: str, text: str, warnings: list[ReviewWarning]) -> Ingredient:
    source = _source(
        f"ingredient '{new_id}'", item.evidence, item.page, item.quote, item.note, text, warnings
    )
    quantity = _quantity(item.quantity)
    if (
        quantity.value is not None
        and source.status is SourceStatus.READ
        and not all(number_supported(v, source.quote or "") for v in (quantity.value, quantity.max_value) if v)
    ):
        source = Source(
            status=SourceStatus.INFERRED,
            page=source.page,
            quote=source.quote,
            note=f"the amount {_amount(quantity)} is not written in the quoted text",
        )
        warnings.append(
            ReviewWarning(message=f"Amount of '{item.name_original}' is not in the text it cites; check it.", target_id=new_id)
        )
    return Ingredient(
        id=new_id,
        name=item.name.strip() or new_id,
        name_original=item.name_original.strip() or item.name.strip() or new_id,
        quantity=quantity,
        preparation=item.preparation.strip() or None,
        optional=item.optional,
        is_intermediate=item.is_intermediate,
        animal=AnimalContent(item.animal),
        source=source,
    )


def _quantity(q: WireQuantity) -> Quantity:
    unit = q.unit.strip() or None
    if q.kind == "exact" and q.value > 0:
        high = q.max_value if q.max_value > q.value else None
        return Quantity(kind=QuantityKind.EXACT, value=q.value, max_value=high, unit=unit, raw=q.raw)
    kind = QuantityKind(q.kind) if q.kind != "exact" else QuantityKind.VAGUE
    return Quantity(kind=kind, raw=q.raw)


def _source(
    label: str,
    evidence: str,
    page: int | None,
    quote: str | None,
    note: str | None,
    text: str,
    warnings: list[ReviewWarning],
) -> Source:
    page = page if page and page >= 1 else None
    quote = quote.strip() if quote and quote.strip() else None
    note = note.strip() if note and note.strip() else None
    if evidence == "read":
        if quote and quote_in_text(quote, text):
            return Source(status=SourceStatus.READ, page=page, quote=quote, note=note)
        warnings.append(ReviewWarning(message=f"{label}: the model cited text that is not in the document."))
        return Source(
            status=SourceStatus.INFERRED,
            page=page,
            note=f"model said it read this, but its quote {quote!r} is not in the document",
        )
    if evidence == "inferred":
        return Source(status=SourceStatus.INFERRED, page=page, quote=quote, note=note or "no reason given")
    return Source(status=SourceStatus.MISSING, page=page, note=note)


def _servings(wire: WireExtraction, text: str, warnings: list[ReviewWarning]) -> Servings:
    s = wire.servings
    if s.value < 1 or s.evidence == "missing":
        return Servings(source=Source(status=SourceStatus.MISSING, note=s.note or "the document does not say"))
    source = _source("servings", s.evidence, s.page, s.quote, s.note, text, warnings)
    if source.status is SourceStatus.READ and not number_supported(s.value, source.quote or ""):
        source = Source(status=SourceStatus.INFERRED, quote=source.quote, note="number not in the quoted text")
    return Servings(value=s.value, source=source)


def _step(
    number: int,
    step: WireStep,
    ingredient_map: dict[str, str],
    tool_map: dict[str, str],
    text: str,
    warnings: list[ReviewWarning],
) -> Step:
    source = _source(f"step {number}", "read", step.page, step.quote, None, text, warnings)
    return Step(
        order=number,
        text=step.text.strip() or step.quote,
        ingredient_ids=tuple(dict.fromkeys(ingredient_map[i] for i in step.ingredient_ids if i in ingredient_map)),
        tool_ids=tuple(dict.fromkeys(tool_map[t] for t in step.tool_ids if t in tool_map)),
        duration=_duration(step),
        condition=step.condition.strip() or None,
        source=source,
    )


def _duration(step: WireStep) -> Duration | None:
    if not step.duration_raw.strip():
        return None
    low, high = step.duration_min_minutes, step.duration_max_minutes
    low = low if low > 0 else None
    high = high if high > 0 else None
    if low is None or high is None:
        low = high = low or high
    if low is not None and low > high:
        low, high = high, low
    return Duration(raw=step.duration_raw.strip(), min_minutes=low, max_minutes=high)


def _unique_slugs(names: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for name in names:
        base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:50] or "item"
        if not base[0].isalpha():
            base = f"item_{base}"
        slug, n = base, 2
        while slug in seen:
            slug, n = f"{base}_{n}", n + 1
        seen.add(slug)
        result.append(slug)
    return result


def _amount(quantity: Quantity) -> str:
    high = f"–{quantity.max_value:g}" if quantity.max_value else ""
    return f"{quantity.value:g}{high} {quantity.unit or ''}".strip()
