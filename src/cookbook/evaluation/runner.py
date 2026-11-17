"""Run the pipeline over the evaluation set and report what passed."""

from difflib import SequenceMatcher

from pydantic import Field

from cookbook.evaluation.checks import CheckResult, evaluate
from cookbook.evaluation.dataset import Case
from cookbook.evaluation.outcome import Outcome
from cookbook.extract import Extractor
from cookbook.extract.grounding import normalise
from cookbook.ingest import Ingestor
from cookbook.models import LlmUsage
from cookbook.models.base import DomainModel
from cookbook.pricing import total_cost_usd


class CaseReport(DomainModel):
    case_id: str
    reviewed: bool
    skipped: str | None = None
    checks: tuple[CheckResult, ...] = ()
    transcription_similarity: float | None = Field(
        default=None, description="0..1, character similarity to the human reference transcription."
    )
    usage: tuple[LlmUsage, ...] = ()
    error: str | None = None

    @property
    def passed(self) -> int:
        return sum(c.passed for c in self.checks)


def run_case(case: Case, ingestor: Ingestor, extractor: Extractor) -> CaseReport:
    base = {"case_id": case.spec.id, "reviewed": case.spec.reviewed}
    if not case.input_available:
        return CaseReport(**base, skipped=f"input not present ({case.spec.input}); kept out of git")
    try:
        document = ingestor.ingest(case.input_path)
        extraction = extractor.extract(document)
    except Exception as error:  # a failing case must not stop the whole run
        return CaseReport(**base, error=f"{type(error).__name__}: {error}")

    outcome = Outcome(
        is_recipe=extraction.is_recipe,
        recipes_in_document=extraction.recipes_in_document,
        recipe=extraction.recipe,
    )
    similarity = None
    reference = case.reference_transcription
    if reference:
        similarity = SequenceMatcher(None, normalise(document.full_text), normalise(reference)).ratio()
    usage = tuple(p.usage for p in document.pages if p.usage) + extraction.usage
    return CaseReport(
        **base,
        checks=tuple(evaluate(case.spec.expect, outcome)),
        transcription_similarity=similarity,
        usage=usage,
    )


def render_report(reports: list[CaseReport]) -> str:
    ran = [r for r in reports if r.checks]
    total_checks = sum(len(r.checks) for r in ran)
    total_passed = sum(r.passed for r in ran)
    usage = [u for r in reports for u in r.usage]
    fresh = [u for u in usage if not u.cached]
    cost = total_cost_usd(fresh)
    lines = [
        "# Evaluation report",
        "",
        f"**{total_passed}/{total_checks} checks passed** across {len(ran)} case(s). "
        f"Model calls: {len(fresh)} new, {len(usage) - len(fresh)} cached; "
        f"cost of new calls: {'unknown' if cost is None else f'${cost:.4f}'}.",
        "",
        "Checks marked unreviewed were drafted by the coding agent and not yet confirmed by a person.",
        "",
        "| Case | Passed | Reviewed | Transcription vs reference | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for report in reports:
        if report.skipped or report.error:
            status = report.skipped or report.error
            lines.append(f"| {report.case_id} | – | {_yes(report.reviewed)} | – | {status} |")
            continue
        similarity = f"{report.transcription_similarity:.0%}" if report.transcription_similarity is not None else "–"
        lines.append(
            f"| {report.case_id} | {report.passed}/{len(report.checks)} | {_yes(report.reviewed)} | {similarity} | |"
        )
    for report in ran:
        failed = [c for c in report.checks if not c.passed]
        if failed:
            lines += ["", f"## {report.case_id}: failed checks", ""]
            lines += [f"- **{c.name}**: {c.detail}" for c in failed]
    return "\n".join(lines) + "\n"


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"
