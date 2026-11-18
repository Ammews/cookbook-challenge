"""Stress run: push many real documents through the pipeline and report what happened.

Unlike the evaluation set, these documents have no expected answers. The
report shows where the pipeline breaks or hesitates: errors, refusals,
several recipes on a page, guessed values, warnings, cost and time. Each
document's full output is saved so a person can read it next to the scan.
"""

import time
from pathlib import Path

import yaml
from pydantic import Field

from cookbook.extract import Extractor
from cookbook.ingest import Ingestor
from cookbook.manipulate import MakeVegan
from cookbook.models import AnimalContent, LlmUsage
from cookbook.models.base import DomainModel
from cookbook.output import write_outputs
from cookbook.pipeline import run_pipeline
from cookbook.pricing import total_cost_usd


class StressDocument(DomainModel):
    id: str
    type: str
    language: str
    note: str
    file: str
    source: str
    license: str


class StressRow(DomainModel):
    id: str
    type: str
    language: str
    status: str = Field(description="recipe, not a recipe, or error")
    read_by: str = ""
    pages: int = 0
    recipes_in_document: int = 0
    ingredients: int = 0
    steps: int = 0
    guessed: int = 0
    animal_uncertain: int = 0
    warnings: int = 0
    problems_found: int = 0
    problems_left: int = 0
    not_fully_vegan: bool = False
    title: str = ""
    error: str = ""
    seconds: float = 0
    usage: tuple[LlmUsage, ...] = ()


def load_manifest(folder: Path) -> list[StressDocument]:
    data = yaml.safe_load((folder / "manifest.yaml").read_text(encoding="utf-8"))
    return [StressDocument.model_validate({k: v for k, v in d.items() if k in StressDocument.model_fields}) for d in data]


def run_document(
    document: StressDocument, folder: Path, out: Path, ingestor: Ingestor, extractor: Extractor
) -> StressRow:
    base = {"id": document.id, "type": document.type, "language": document.language}
    started = time.perf_counter()
    try:
        result = run_pipeline(folder / document.file, ingestor, extractor, [MakeVegan()])
    except Exception as error:  # one bad document must not stop the run
        return StressRow(**base, status="error", error=f"{type(error).__name__}: {error}"[:300],
                         seconds=time.perf_counter() - started)
    write_outputs(result, out, document.id)

    extraction = result.extraction
    row = StressRow(
        **base,
        status="recipe" if extraction.is_recipe and extraction.recipe else "not a recipe",
        read_by=", ".join(sorted({p.method.value for p in result.document.pages})),
        pages=len(result.document.pages),
        recipes_in_document=extraction.recipes_in_document,
        problems_found=len(extraction.problems_found),
        problems_left=len(extraction.problems_left),
        seconds=time.perf_counter() - started,
        usage=tuple(result.usage),
    )
    recipe = extraction.recipe
    if recipe is None:
        return row
    final = result.recipe
    return row.model_copy(
        update={
            "title": recipe.title,
            "ingredients": len(recipe.ingredients),
            "steps": len(recipe.steps),
            "guessed": sum(i.source.is_guess for i in recipe.ingredients),
            "animal_uncertain": sum(i.animal is AnimalContent.UNCERTAIN for i in recipe.ingredients),
            "warnings": len(recipe.warnings),
            "not_fully_vegan": any(w.message.startswith("Not fully vegan") for w in final.warnings),
        }
    )


def render_stress_report(rows: list[StressRow], total: int) -> str:
    usage = [u for r in rows for u in r.usage]
    fresh = [u for u in usage if not u.cached]
    first_run = total_cost_usd(u.model_copy(update={"cached": False}) for u in usage)
    count = lambda status: sum(r.status == status for r in rows)
    lines = [
        "# Stress run",
        "",
        f"{len(rows)} of {total} documents run: **{count('recipe')} read as a recipe, "
        f"{count('not a recipe')} refused as not a recipe, {count('error')} errors.** "
        f"{sum(r.recipes_in_document > 1 for r in rows)} reported several recipes on the page. "
        f"Cost {'unknown' if first_run is None else f'${first_run:.3f}'} for the first run "
        f"({len(fresh)} new calls this time), {sum(r.seconds for r in rows):.0f} s in total.",
        "",
        "No expected answers here: read each output in `results/` next to its scan in `files/`.",
        "Every document is also run through the vegan rule, to see what it flags.",
        "",
        "| Document | Type | Lang | Read by | Result | Recipes | Ingr. | Steps | Guessed | Problems (found/left) | Warnings | Vegan | Time |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        result = r.status if r.status != "recipe" else (r.title or "recipe")[:40]
        vegan = "" if r.status != "recipe" else ("not fully" if r.not_fully_vegan else "ok")
        lines.append(
            f"| [{r.id}](results/{r.id}.md) | {r.type} | {r.language} | {r.read_by} | {result} | "
            f"{r.recipes_in_document or ''} | {r.ingredients or ''} | {r.steps or ''} | {r.guessed or ''} | "
            f"{r.problems_found}/{r.problems_left} | {r.warnings or ''} | {vegan} | {r.seconds:.0f} s |"
        )
    errors = [r for r in rows if r.status == "error"]
    if errors:
        lines += ["", "## Errors", ""] + [f"- **{r.id}**: {r.error}" for r in errors]
    return "\n".join(lines) + "\n"
