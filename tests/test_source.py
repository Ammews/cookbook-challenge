import pytest
from pydantic import ValidationError

from cookbook.models import Source, SourceStatus


def test_read_value_must_carry_its_quote():
    with pytest.raises(ValidationError, match="must carry the quote"):
        Source(status=SourceStatus.READ, page=1)


def test_blank_quote_does_not_count_as_evidence():
    with pytest.raises(ValidationError, match="must carry the quote"):
        Source(status=SourceStatus.READ, quote="   ")


def test_inferred_value_must_explain_itself():
    with pytest.raises(ValidationError, match="must explain the reasoning"):
        Source(status=SourceStatus.INFERRED)


def test_inferred_value_may_cite_the_text_it_was_inferred_from():
    source = Source(status=SourceStatus.INFERRED, quote="abgetrockneten Braten", note="needs a cloth")
    assert source.is_guess


def test_missing_value_cannot_have_a_quote():
    with pytest.raises(ValidationError, match="cannot have a quote"):
        Source(status=SourceStatus.MISSING, quote="die festen Bratenstücke")


def test_only_read_values_are_not_guesses():
    assert not Source(status=SourceStatus.READ, quote="½ l Essig").is_guess
    assert Source(status=SourceStatus.MISSING).is_guess


def test_page_numbers_start_at_one():
    with pytest.raises(ValidationError):
        Source(status=SourceStatus.READ, quote="x", page=0)
