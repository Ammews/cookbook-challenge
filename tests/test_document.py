import pytest
from pydantic import ValidationError

from cookbook.models import Document, InputKind, LlmUsage, Page, ReadMethod
from cookbook.pricing import cost_usd, total_cost_usd


def page(number, text="text", method=ReadMethod.PLAIN_TEXT):
    return Page(number=number, text=text, method=method)


def pdf(*pages):
    return Document(name="r.pdf", kind=InputKind.PDF, pages=pages)


def test_full_text_joins_pages_so_sentences_can_cross_a_page_break():
    document = pdf(page(1, "so gießt man"), page(2, "es kalt darauf."))
    assert document.full_text == "so gießt man\n\nes kalt darauf."


def test_full_text_skips_blank_pages():
    assert pdf(page(1, "a"), page(2, " "), page(3, "b")).full_text == "a\n\nb"


def test_pages_must_be_numbered_in_sequence():
    with pytest.raises(ValidationError, match="page numbers must be"):
        pdf(page(1), page(3))


def test_document_needs_at_least_one_page():
    with pytest.raises(ValidationError):
        pdf()


def test_only_vision_pages_are_flagged_as_transcribed():
    assert page(1, method=ReadMethod.VISION).is_transcribed
    assert not page(1, method=ReadMethod.PDF_TEXT_LAYER).is_transcribed


def usage(model="claude-haiku-5-5", cached=False):
    return LlmUsage(
        model=model, input_tokens=1_000_000, output_tokens=1_000_000, seconds=1, cached=cached
    )


def test_cost_uses_the_price_table():
    assert cost_usd(usage()) == pytest.approx(0.60)


def test_cached_call_costs_nothing():
    assert cost_usd(usage(cached=True)) == 0


def test_unknown_model_has_unknown_cost_instead_of_a_guess():
    assert cost_usd(usage(model="some-future-model")) is None
    assert total_cost_usd([usage(), usage(model="some-future-model")]) is None


def test_total_cost_sums_calls():
    assert total_cost_usd([usage(), usage(), usage(cached=True)]) == pytest.approx(1.20)
