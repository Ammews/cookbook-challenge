"""Command line entry point.

    cookbook run <file> [--servings N] [--vegan] [--metric] [--out DIR]
    cookbook ingest <file>
    cookbook eval [--case ID]
    cookbook stress [id ...]
    cookbook web [--port 8000]
"""

import argparse
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from cookbook.config import Settings
from cookbook.evaluation import load_cases
from cookbook.evaluation.runner import render_report, run_case
from cookbook.extract import ExtractionError, build_extractor
from cookbook.ingest import TranscriptionError, UnsupportedInputError, build_ingestor
from cookbook.manipulate import ConvertToMetric, MakeVegan, ManipulationError, ScaleServings
from cookbook.models import Document
from cookbook.output import write_outputs
from cookbook.pipeline import run_pipeline
from cookbook.pricing import total_cost_usd

EVAL_ROOT = Path("evals/cases")
EVAL_REPORT = Path("evals/results/latest.md")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except FileNotFoundError as error:
        return _fail(f"file not found: {error.filename}")
    except (UnsupportedInputError, TranscriptionError, ExtractionError, ManipulationError) as error:
        return _fail(str(error))
    except anthropic.AuthenticationError:
        return _fail("the Anthropic API key was rejected; check ANTHROPIC_API_KEY in .env")
    except anthropic.APIConnectionError:
        return _fail("could not reach the Anthropic API; check your connection")
    except anthropic.APIStatusError as error:
        return _fail(f"Anthropic API error {error.status_code}: {error.message}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cookbook", description="AI-powered cookbook pipeline.")
    commands = parser.add_subparsers(required=True)

    run = commands.add_parser("run", help="turn a recipe file into an adjusted, cookable recipe")
    run.add_argument("file", type=Path)
    run.add_argument("--servings", type=int, help="scale to this many servings")
    run.add_argument("--assume-servings", type=int, help="servings of the original, if the recipe does not say")
    run.add_argument("--vegan", action="store_true", help="replace animal products")
    run.add_argument("--metric", action="store_true", help="convert amounts to ml, l, g, kg")
    run.add_argument("--out", type=Path, default=Path("out"), help="output folder (default: out)")
    run.add_argument("--name", help="output file name without extension")
    run.set_defaults(handler=_run)

    ingest = commands.add_parser("ingest", help="only read a PDF, image or text file into page texts")
    ingest.add_argument("file", type=Path)
    ingest.add_argument("--json", type=Path, metavar="PATH", help="also save the document as JSON")
    ingest.set_defaults(handler=_ingest)

    stress = commands.add_parser("stress", help="run real documents from evals/stress and report what happened")
    stress.add_argument("ids", nargs="*", help="document ids to run (default: all)")
    stress.set_defaults(handler=_stress)

    web = commands.add_parser("web", help="start the local web page (needs: uv sync --extra web)")
    web.add_argument("--port", type=int, default=8000)
    web.set_defaults(handler=_web)

    evaluate = commands.add_parser("eval", help="run the evaluation set and write a report")
    evaluate.add_argument("--case", help="run only this case id")
    evaluate.add_argument("--report", type=Path, default=EVAL_REPORT)
    evaluate.set_defaults(handler=_eval)
    return parser


def _run(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    rules = []
    if args.vegan:
        rules.append(MakeVegan())
    if args.servings:
        rules.append(ScaleServings(args.servings, assume_base=args.assume_servings))
    if args.metric:
        rules.append(ConvertToMetric())  # last, so rounding happens once
    result = run_pipeline(args.file, build_ingestor(settings), build_extractor(settings), rules)
    stem = args.name or _stem(args.file, args.servings, args.vegan, args.metric)
    markdown, data = write_outputs(result, args.out, stem)

    recipe = result.recipe
    if recipe is None:
        print(f"{args.file.name}: not a recipe; nothing extracted.")
    else:
        guessed = sum(i.source.is_guess for i in recipe.ingredients)
        print(
            f"{recipe.title}: {len(recipe.ingredients)} ingredients ({guessed} not read directly), "
            f"{len(recipe.steps)} steps, {len(recipe.warnings)} warning(s)"
        )
        if result.manipulation:
            print(f"Changes applied: {len(result.manipulation.changes)}")
    print(_usage_line(result.usage))
    print(f"Wrote {markdown} and {data}")
    return 0


def _ingest(args: argparse.Namespace) -> int:
    document = build_ingestor(Settings.from_env()).ingest(args.file)
    print(_format_document(document))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nSaved to {args.json}")
    return 0


def _eval(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    ingestor, extractor = build_ingestor(settings), build_extractor(settings)
    cases = [c for c in load_cases(EVAL_ROOT) if not args.case or c.spec.id == args.case]
    if not cases:
        return _fail(f"no case named {args.case!r}")
    reports = []
    for case in cases:
        print(f"running {case.spec.id} ...", flush=True)
        reports.append(run_case(case, ingestor, extractor))
    report = render_report(reports)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to {args.report}")
    return 0


def _stress(args: argparse.Namespace) -> int:
    from cookbook.evaluation.stress import load_manifest, render_stress_report, run_document

    folder = Path("evals/stress")
    documents = load_manifest(folder)
    chosen = [d for d in documents if not args.ids or d.id in args.ids]
    unknown = sorted(set(args.ids) - {d.id for d in documents})
    if unknown:
        return _fail(f"unknown document id(s): {', '.join(unknown)}")
    settings = Settings.from_env()
    ingestor, extractor = build_ingestor(settings), build_extractor(settings)
    rows = []
    for number, document in enumerate(chosen, start=1):
        print(f"[{number}/{len(chosen)}] {document.id} ...", flush=True)
        rows.append(run_document(document, folder, folder / "results", ingestor, extractor))
    report = render_stress_report(rows, total=len(documents))
    (folder / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


def _web(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from cookbook.web.app import create_app
    except ImportError:
        return _fail("the web page needs extra packages: run `uv sync --extra web` first")
    print(f"Open http://127.0.0.1:{args.port}")
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")
    return 0


def _stem(path: Path, servings: int | None, vegan: bool, metric: bool = False) -> str:
    parts = [path.stem.lower().replace(" ", "-")]
    if vegan:
        parts.append("vegan")
    if servings:
        parts.append(f"{servings}-servings")
    if metric:
        parts.append("metric")
    return "_".join(parts)


def _format_document(document: Document) -> str:
    lines = [f"{document.name}: {document.kind.value}, {len(document.pages)} page(s)"]
    for page in document.pages:
        lines.append(f"\n--- page {page.number} (read by: {page.method.value}) ---")
        lines.append(page.text or "(no text)")
        if page.decoration_text:
            lines.append(f"[not running text] {' | '.join(page.decoration_text)}")
        if page.uncertain:
            lines.append(f"[uncertain words] {', '.join(page.uncertain)}")
    usages = [p.usage for p in document.pages if p.usage is not None]
    lines.append("\n" + _usage_line(usages))
    return "\n".join(lines)


def _usage_line(usages) -> str:
    if not usages:
        return "Model calls: none (no LLM needed for this input)"
    fresh = [u for u in usages if not u.cached]
    cost = total_cost_usd(usages)
    cost_text = "unknown (model not in price table)" if cost is None else f"${cost:.5f}"
    return (
        f"Model calls: {len(fresh)} new, {len(usages) - len(fresh)} from cache | "
        f"tokens in/out: {sum(u.input_tokens for u in fresh)}/"
        f"{sum(u.output_tokens for u in fresh)} | "
        f"time: {sum(u.seconds for u in fresh):.1f}s | cost: {cost_text}"
    )


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
