"""The four stages wired together: ingest -> extract -> manipulate -> (output)."""

from collections.abc import Sequence
from pathlib import Path

from cookbook.extract import Extraction, Extractor
from cookbook.ingest import Ingestor
from cookbook.manipulate import ManipulationResult, Rule, apply_rules
from cookbook.models import Document, LlmUsage, Recipe
from cookbook.models.base import DomainModel


class PipelineResult(DomainModel):
    document: Document
    extraction: Extraction
    manipulation: ManipulationResult | None = None

    @property
    def recipe(self) -> Recipe | None:
        """The recipe after all rules, or the extracted one if no rule was applied."""
        if self.manipulation is not None:
            return self.manipulation.recipe
        return self.extraction.recipe

    @property
    def usage(self) -> list[LlmUsage]:
        pages = [p.usage for p in self.document.pages if p.usage is not None]
        return pages + list(self.extraction.usage)


def run_pipeline(
    path: Path, ingestor: Ingestor, extractor: Extractor, rules: Sequence[Rule] = ()
) -> PipelineResult:
    document = ingestor.ingest(path)
    extraction = extractor.extract(document)
    manipulation = None
    if rules and extraction.recipe is not None:
        manipulation = apply_rules(extraction.recipe, rules)
    return PipelineResult(document=document, extraction=extraction, manipulation=manipulation)
