import pytest
from pydantic import ValidationError

from cookbook.models import Duration


def test_duration_can_be_text_only():
    assert Duration(raw="langsam").min_minutes is None


def test_duration_range_keeps_both_ends():
    duration = Duration(raw="1. oder 2. Tag", min_minutes=1440, max_minutes=2880)
    assert duration.max_minutes == 2880


def test_duration_needs_both_ends_or_neither():
    with pytest.raises(ValidationError, match="both min_minutes and max_minutes"):
        Duration(raw="eine Stunde", min_minutes=60)


def test_duration_range_must_be_ordered():
    with pytest.raises(ValidationError, match="cannot be greater"):
        Duration(raw="x", min_minutes=90, max_minutes=60)
