"""Stage 2: document text -> structured recipe, checked against the document."""

from pydantic import Field

from cookbook.extract.mapper import find_problems, to_recipe
from cookbook.extract.model import ExtractionModel
from cookbook.extract.prompt import correction_prompt, document_prompt
from cookbook.models import Document, LlmUsage, Recipe, ReviewWarning
from cookbook.models.base import DomainModel


class Extraction(DomainModel):
    is_recipe: bool
    recipes_in_document: int = Field(ge=0)
    recipe: Recipe | None
    usage: tuple[LlmUsage, ...]
    problems_found: tuple[str, ...] = Field(
        default=(), description="What the code check found in the model's first answer."
    )
    problems_left: tuple[str, ...] = Field(
        default=(), description="What was still wrong after the correction round (then repaired as warnings)."
    )


class Extractor:
    """Ask the model, check the answer in code, ask once more with the problems, then repair.

    One correction round is enough in practice and keeps cost bounded. What
    is still wrong afterwards is not hidden: the mapper demotes it to
    "inferred" and adds a review warning.
    """

    def __init__(self, model: ExtractionModel, max_corrections: int = 1) -> None:
        self._model = model
        self._max_corrections = max_corrections

    def extract(self, document: Document) -> Extraction:
        text = document.full_text
        messages: list[dict] = [{"role": "user", "content": document_prompt(document)}]
        reply = self._model.extract(messages)
        usage = [reply.usage]
        first_problems = find_problems(reply.extraction, text)
        problems = first_problems

        for _ in range(self._max_corrections):
            if not problems:
                break
            correction = correction_prompt(problems, reply.extraction.model_dump_json())
            reply = self._model.extract(
                [{"role": "user", "content": messages[0]["content"] + "\n\n" + correction}]
            )
            usage.append(reply.usage)
            problems = find_problems(reply.extraction, text)

        wire = reply.extraction
        recipe = to_recipe(wire, text) if wire.is_recipe else None
        if recipe is not None and problems:
            recipe = recipe.model_copy(
                update={
                    "warnings": recipe.warnings
                    + (ReviewWarning(message=f"{len(problems)} problem(s) remained after the correction round."),)
                }
            )
        return Extraction(
            is_recipe=wire.is_recipe,
            recipes_in_document=max(0, wire.recipes_in_document) if wire.is_recipe else 0,
            recipe=recipe,
            usage=tuple(usage),
            problems_found=tuple(first_problems),
            problems_left=tuple(problems),
        )
