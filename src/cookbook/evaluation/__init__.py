"""Evaluation: check pipeline outcomes against hand-reviewed expectations."""

from cookbook.evaluation.checks import CheckResult, evaluate, normalise_unit
from cookbook.evaluation.dataset import Case, load_case, load_cases
from cookbook.evaluation.outcome import Outcome
from cookbook.evaluation.spec import CaseSpec, Expectations

__all__ = [
    "Case",
    "CaseSpec",
    "CheckResult",
    "Expectations",
    "Outcome",
    "evaluate",
    "load_case",
    "load_cases",
    "normalise_unit",
]
