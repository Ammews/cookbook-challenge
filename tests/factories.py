"""Small builders so each test states only the field it cares about."""

from cookbook.models import (
    Ingredient,
    Quantity,
    QuantityKind,
    Recipe,
    Servings,
    Source,
    SourceStatus,
    Step,
    Tool,
)


def read(quote: str = "4 in Scheiben geschnittene Zwiebeln", page: int = 1) -> Source:
    return Source(status=SourceStatus.READ, page=page, quote=quote)


def inferred(note: str = "implied by the text") -> Source:
    return Source(status=SourceStatus.INFERRED, note=note)


def exact(value: float = 4, unit: str | None = None, raw: str = "4") -> Quantity:
    return Quantity(kind=QuantityKind.EXACT, value=value, unit=unit, raw=raw)


def ingredient(id: str = "onion", **overrides) -> Ingredient:
    fields = dict(
        id=id, name=id, name_original="Zwiebeln", quantity=exact(), source=read()
    )
    return Ingredient(**(fields | overrides))


def tool(id: str = "pot", **overrides) -> Tool:
    return Tool(**(dict(id=id, name=id, source=read("in den Topf geben")) | overrides))


def step(order: int = 1, **overrides) -> Step:
    fields = dict(order=order, text="Boil the marinade.", source=read("kocht man"))
    return Step(**(fields | overrides))


def recipe(**overrides) -> Recipe:
    fields = dict(
        title="Sauerbraten",
        language="de",
        servings=Servings(value=4, source=inferred("1 l of marinade suits about 1 kg of meat")),
        ingredients=(ingredient(),),
        tools=(tool(),),
        steps=(step(ingredient_ids=("onion",), tool_ids=("pot",)),),
    )
    return Recipe(**(fields | overrides))
