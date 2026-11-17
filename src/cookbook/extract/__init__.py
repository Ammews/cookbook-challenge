"""Stage 2: extract. Turns a Document into a Recipe whose values are checked against the text."""

from cookbook.config import Settings
from cookbook.extract.extractor import Extraction, Extractor
from cookbook.extract.model import (
    CachedExtractionModel,
    ClaudeExtractionModel,
    ExtractionError,
    ExtractionModel,
    ModelReply,
)

__all__ = [
    "CachedExtractionModel",
    "ClaudeExtractionModel",
    "Extraction",
    "ExtractionError",
    "ExtractionModel",
    "Extractor",
    "ModelReply",
    "build_extractor",
]


def build_extractor(settings: Settings) -> Extractor:
    claude = ClaudeExtractionModel(model=settings.extraction_model)
    return Extractor(
        CachedExtractionModel(claude, settings.cache_dir / "extractions", claude.cache_namespace)
    )
