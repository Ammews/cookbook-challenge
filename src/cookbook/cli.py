"""Command line entry point: `cookbook ingest <file>`."""

import argparse
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from cookbook.config import Settings
from cookbook.ingest import TranscriptionError, UnsupportedInputError, build_ingestor
from cookbook.models import Document
from cookbook.pricing import total_cost_usd


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except FileNotFoundError as error:
        return _fail(f"file not found: {error.filename}")
    except (UnsupportedInputError, TranscriptionError) as error:
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

    ingest = commands.add_parser("ingest", help="read a PDF, image or text file into page texts")
    ingest.add_argument("file", type=Path)
    ingest.add_argument("--json", type=Path, metavar="PATH", help="also save the document as JSON")
    ingest.set_defaults(handler=_ingest)
    return parser


def _ingest(args: argparse.Namespace) -> int:
    document = build_ingestor(Settings.from_env()).ingest(args.file)
    print(_format_document(document))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nSaved to {args.json}")
    return 0


def _format_document(document: Document) -> str:
    lines = [f"{document.name}: {document.kind.value}, {len(document.pages)} page(s)"]
    for page in document.pages:
        lines.append(f"\n--- page {page.number} (read by: {page.method.value}) ---")
        lines.append(page.text or "(no text)")
        if page.decoration_text:
            lines.append(f"[not running text] {' | '.join(page.decoration_text)}")
        if page.uncertain:
            lines.append(f"[uncertain words] {', '.join(page.uncertain)}")
    lines.append("\n" + _format_usage(document))
    return "\n".join(lines)


def _format_usage(document: Document) -> str:
    usages = [p.usage for p in document.pages if p.usage is not None]
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
