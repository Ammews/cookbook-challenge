"""Every committed case must load, and its files must be where it says."""

from pathlib import Path

import pytest

from cookbook.evaluation import load_cases

CASES_ROOT = Path(__file__).resolve().parent.parent / "evals" / "cases"
CASES = load_cases(CASES_ROOT)


def test_dataset_is_not_empty():
    assert len(CASES) >= 10


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.spec.id)
def test_case_input_is_present_unless_kept_local(case):
    if case.spec.input_in_repo:
        assert case.input_available, f"{case.input_path} is missing"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.spec.id)
def test_reference_transcription_exists_when_declared(case):
    if case.spec.reference_transcription:
        assert case.reference_transcription.strip()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.spec.id)
def test_every_case_names_its_source_and_traps(case):
    assert case.spec.source.startswith(("http", "local"))
    assert case.spec.traps, "say what the case tests, so a reviewer knows why it is here"
