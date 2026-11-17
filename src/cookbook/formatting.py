"""Human-readable amounts: 0.75 cup -> "¾ cup", 2.5 -> "2 ½"."""

from cookbook.models import Quantity, QuantityKind

_GLYPHS = {1 / 4: "¼", 1 / 3: "⅓", 1 / 2: "½", 2 / 3: "⅔", 3 / 4: "¾", 1 / 8: "⅛"}


def format_number(value: float) -> str:
    whole = int(value)
    rest = value - whole
    if rest < 0.01:
        return str(whole)
    for fraction, glyph in _GLYPHS.items():
        if abs(rest - fraction) < 0.01:
            return glyph if whole == 0 else f"{whole} {glyph}"
    if rest > 0.99:
        return str(whole + 1)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_amount(quantity: Quantity) -> str:
    if quantity.kind is QuantityKind.EXACT and quantity.value is not None:
        number = format_number(quantity.value)
        if quantity.max_value is not None:
            number = f"{number}–{format_number(quantity.max_value)}"
        return f"{number} {quantity.unit}".strip() if quantity.unit else number
    label = {
        QuantityKind.VAGUE: "some",
        QuantityKind.TO_TASTE: "to taste",
        QuantityKind.ABSENT: "amount not given",
    }[quantity.kind]
    return f"{label} ({quantity.raw})" if quantity.raw else label
