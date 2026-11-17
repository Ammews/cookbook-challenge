"""What a model call costs, so every run can report its price."""

from collections.abc import Iterable

from cookbook.models import LlmUsage

# USD per million tokens (input, output), from Anthropic's price list as of
# November 2026. Haiku 5.5 rates apply to prompts up to 100K tokens, far above
# what a recipe page needs. Update here when prices or the model change.
_PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


def cost_usd(usage: LlmUsage) -> float | None:
    """Cost of one call. Zero if it came from the cache, None if the model's price is unknown."""
    if usage.cached:
        return 0.0
    prices = _PRICES_PER_MTOK.get(usage.model)
    if prices is None:
        return None
    input_price, output_price = prices
    return (usage.input_tokens * input_price + usage.output_tokens * output_price) / 1_000_000


def total_cost_usd(usages: Iterable[LlmUsage]) -> float | None:
    """Sum of several calls. None if any of them has an unknown price."""
    costs = [cost_usd(u) for u in usages]
    if any(c is None for c in costs):
        return None
    return sum(costs)
