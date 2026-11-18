"""The stress manifest is valid and every file it lists is in the repository."""

from pathlib import Path

from cookbook.evaluation.stress import StressRow, load_manifest, render_stress_report

FOLDER = Path(__file__).resolve().parent.parent / "evals" / "stress"


def test_manifest_lists_files_that_exist_with_a_source_and_licence():
    documents = load_manifest(FOLDER)
    assert len(documents) >= 50
    assert len({d.id for d in documents}) == len(documents)
    for document in documents:
        assert (FOLDER / document.file).is_file(), document.file
        assert document.source.startswith("https://") and document.license


def test_report_counts_outcomes_and_lists_errors():
    rows = [
        StressRow(id="a", type="card", language="en", status="recipe", title="Apple cake", recipes_in_document=1),
        StressRow(id="b", type="printed", language="de", status="not a recipe"),
        StressRow(id="c", type="handwritten", language="fr", status="error", error="TranscriptionError: refusal"),
    ]
    report = render_stress_report(rows, total=50)
    assert "3 of 50 documents run: **1 read as a recipe, 1 refused as not a recipe, 1 errors.**" in report
    assert "- **c**: TranscriptionError: refusal" in report
