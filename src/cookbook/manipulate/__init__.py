"""Stage 3: manipulate. Deterministic rules that return a new recipe and the changes they made."""

from cookbook.manipulate.rules import ManipulationError, ManipulationResult, Rule, apply_rules
from cookbook.manipulate.scale import ScaleServings
from cookbook.manipulate.units import ConvertToMetric
from cookbook.manipulate.vegan import MakeVegan

__all__ = [
    "ConvertToMetric",
    "MakeVegan",
    "ManipulationError",
    "ManipulationResult",
    "Rule",
    "ScaleServings",
    "apply_rules",
]
